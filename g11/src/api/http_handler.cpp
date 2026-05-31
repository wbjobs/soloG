#include "tsdb/api/http_handler.h"
#include "tsdb/utils/serializer.h"
#include "tsdb/utils/time_utils.h"
#include "tsdb/config/config.h"
#include "tsdb/websocket/data_subscription.h"
#include <json/json.h>
#include <sstream>
#include <algorithm>

namespace tsdb::api {

HttpHandler::HttpHandler(std::shared_ptr<storage::RocksDBEngine> engine,
                         std::shared_ptr<query::QueryEngine> queryEngine,
                         std::shared_ptr<index::TagIndex> tagIndex,
                         std::shared_ptr<downsampling::Downsampler> downsampler1m,
                         std::shared_ptr<downsampling::Downsampler> downsampler5m,
                         std::shared_ptr<downsampling::Downsampler> downsampler1h,
                         std::shared_ptr<rollup::RollupEngine> rollupEngine)
    : engine_(std::move(engine)),
      queryEngine_(std::move(queryEngine)),
      tagIndex_(std::move(tagIndex)),
      downsampler1m_(std::move(downsampler1m)),
      downsampler5m_(std::move(downsampler5m)),
      downsampler1h_(std::move(downsampler1h)),
      rollupEngine_(std::move(rollupEngine)) {}

std::optional<auth::UserInfo> HttpHandler::authenticate(const drogon::HttpRequestPtr& req) {
    if (!config::Config::instance().enableAuth()) {
        auth::UserInfo info;
        info.tenant = "default_tenant";
        info.userId = "anonymous";
        info.role = "admin";
        return info;
    }

    auto tokenOpt = auth::JwtAuth::extractTokenFromHeader(req);
    if (!tokenOpt) {
        return std::nullopt;
    }

    return auth::JwtAuth::validateToken(*tokenOpt);
}

void HttpHandler::handleLogin(const drogon::HttpRequestPtr& req,
                              std::function<void(const drogon::HttpResponsePtr&)>&& callback) {
    try {
        Json::Value json;
        Json::CharReaderBuilder reader;
        std::string errs;
        std::istringstream iss(req->body());
        if (!Json::parseFromStream(reader, iss, &json, &errs)) {
            callback(auth::JwtAuth::makeUnauthorizedResponse("Invalid JSON"));
            return;
        }

        std::string tenant = json["tenant"].asString();
        std::string username = json["username"].asString();
        std::string password = json["password"].asString();

        std::string token = auth::JwtAuth::generateToken(tenant, username, "user");

        Json::Value result;
        result["token"] = token;
        result["tenant"] = tenant;
        result["expires_in"] = config::Config::instance().jwtExpireHours() * 3600;

        Json::StreamWriterBuilder writer;
        auto resp = drogon::HttpResponse::newHttpResponse();
        resp->setStatusCode(drogon::HttpStatusCode::k200OK);
        resp->setBody(Json::writeString(writer, result));
        resp->setContentTypeCode(drogon::CT_APPLICATION_JSON);
        callback(resp);
    } catch (const std::exception& e) {
        callback(auth::JwtAuth::makeUnauthorizedResponse(std::string("Login failed: ") + e.what()));
    }
}

AggregationType HttpHandler::parseAggregation(const std::string& agg) {
    std::string lower = agg;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    if (lower == "avg") return AggregationType::AVG;
    if (lower == "max") return AggregationType::MAX;
    if (lower == "min") return AggregationType::MIN;
    if (lower == "sum") return AggregationType::SUM;
    if (lower == "count") return AggregationType::COUNT;
    return AggregationType::AVG;
}

DownsampleInterval HttpHandler::parseDownsample(const std::string& ds) {
    std::string lower = ds;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    if (lower == "raw" || lower == "0") return DownsampleInterval::RAW;
    if (lower == "1m" || lower == "min_1") return DownsampleInterval::MIN_1;
    if (lower == "5m" || lower == "min_5") return DownsampleInterval::MIN_5;
    if (lower == "1h" || lower == "hour_1") return DownsampleInterval::HOUR_1;
    return DownsampleInterval::RAW;
}

void HttpHandler::handleWrite(const drogon::HttpRequestPtr& req,
                              std::function<void(const drogon::HttpResponsePtr&)>&& callback) {
    auto userOpt = authenticate(req);
    if (!userOpt) {
        callback(auth::JwtAuth::makeUnauthorizedResponse("Missing or invalid authentication token"));
        return;
    }

    try {
        Json::Value json;
        Json::CharReaderBuilder reader;
        std::string errs;
        std::istringstream iss(req->body());
        if (!Json::parseFromStream(reader, iss, &json, &errs)) {
            auto resp = drogon::HttpResponse::newHttpResponse();
            resp->setStatusCode(drogon::HttpStatusCode::k400BadRequest);
            resp->setBody("{\"error\":\"Invalid JSON: " + errs + "\"}");
            resp->setContentTypeCode(drogon::CT_APPLICATION_JSON);
            callback(resp);
            return;
        }

        TenantId tenant = userOpt->tenant;
        Metric metric = json["metric"].asString();
        Tags tags;
        if (json.isMember("tags")) {
            for (auto it = json["tags"].begin(); it != json["tags"].end(); ++it) {
                tags[it.name()] = it->asString();
            }
        }

        Timestamp timestamp = json.isMember("timestamp") ? json["timestamp"].asInt64() : now();
        Value value = json["value"].asDouble();

        std::string seriesId = utils::Serializer::generateSeriesId(tenant, metric, tags);
        tagIndex_->indexSeries(tenant, metric, tags, seriesId);

        std::string key = utils::Serializer::serializeKey(tenant, metric, tags, timestamp);
        std::string val = utils::Serializer::serializeValue(value);
        engine_->put(key, val);

        downsampler1m_->addPoint(tenant, metric, tags, timestamp, value);
        downsampler5m_->addPoint(tenant, metric, tags, timestamp, value);
        downsampler1h_->addPoint(tenant, metric, tags, timestamp, value);

        if (rollupEngine_) {
            rollupEngine_->onDataWritten(tenant, metric, tags, timestamp, value);
        }

        websocket::DataSubscriptionManager::instance().onDataWritten(
            tenant, metric, tags, timestamp, value);

        Json::Value result;
        result["status"] = "success";
        result["series_id"] = seriesId;
        Json::StreamWriterBuilder writer;
        auto resp = drogon::HttpResponse::newHttpResponse();
        resp->setStatusCode(drogon::HttpStatusCode::k200OK);
        resp->setBody(Json::writeString(writer, result));
        resp->setContentTypeCode(drogon::CT_APPLICATION_JSON);
        callback(resp);
    } catch (const std::exception& e) {
        auto resp = drogon::HttpResponse::newHttpResponse();
        resp->setStatusCode(drogon::HttpStatusCode::k500InternalServerError);
        resp->setBody("{\"error\":\"" + std::string(e.what()) + "\"}");
        resp->setContentTypeCode(drogon::CT_APPLICATION_JSON);
        callback(resp);
    }
}

void HttpHandler::handleQuery(const drogon::HttpRequestPtr& req,
                              std::function<void(const drogon::HttpResponsePtr&)>&& callback) {
    auto userOpt = authenticate(req);
    if (!userOpt) {
        callback(auth::JwtAuth::makeUnauthorizedResponse("Missing or invalid authentication token"));
        return;
    }

    try {
        Json::Value json;
        Json::CharReaderBuilder reader;
        std::string errs;
        std::istringstream iss(req->body());
        if (!Json::parseFromStream(reader, iss, &json, &errs)) {
            auto resp = drogon::HttpResponse::newHttpResponse();
            resp->setStatusCode(drogon::HttpStatusCode::k400BadRequest);
            resp->setBody("{\"error\":\"Invalid JSON: " + errs + "\"}");
            resp->setContentTypeCode(drogon::CT_APPLICATION_JSON);
            callback(resp);
            return;
        }

        query::QueryRequest request;
        request.tenant = userOpt->tenant;
        request.metric = json["metric"].asString();
        
        if (json.isMember("tags")) {
            for (auto it = json["tags"].begin(); it != json["tags"].end(); ++it) {
                request.tags[it.name()] = it->asString();
            }
        }

        request.startTime = utils::TimeUtils::parseTimeString(json["start"].asString());
        request.endTime = utils::TimeUtils::parseTimeString(json["end"].asString());
        request.aggregation = parseAggregation(json.get("aggregation", "avg").asString());
        request.downsample = parseDownsample(json.get("downsample", "raw").asString());

        QueryResult result = queryEngine_->queryAggregated(request);

        Json::Value jsonResult;
        jsonResult["tenant"] = request.tenant;
        jsonResult["metric"] = request.metric;
        Json::Value points(Json::arrayValue);
        for (size_t i = 0; i < result.count(); ++i) {
            Json::Value point;
            point["timestamp"] = Json::Int64(result.timestamps[i]);
            point["value"] = result.values[i];
            points.append(point);
        }
        jsonResult["points"] = points;

        Json::StreamWriterBuilder writer;
        auto resp = drogon::HttpResponse::newHttpResponse();
        resp->setStatusCode(drogon::HttpStatusCode::k200OK);
        resp->setBody(Json::writeString(writer, jsonResult));
        resp->setContentTypeCode(drogon::CT_APPLICATION_JSON);
        callback(resp);
    } catch (const std::exception& e) {
        auto resp = drogon::HttpResponse::newHttpResponse();
        resp->setStatusCode(drogon::HttpStatusCode::k500InternalServerError);
        resp->setBody("{\"error\":\"" + std::string(e.what()) + "\"}");
        resp->setContentTypeCode(drogon::CT_APPLICATION_JSON);
        callback(resp);
    }
}

void HttpHandler::handleQueryRaw(const drogon::HttpRequestPtr& req,
                                 std::function<void(const drogon::HttpResponsePtr&)>&& callback) {
    auto userOpt = authenticate(req);
    if (!userOpt) {
        callback(auth::JwtAuth::makeUnauthorizedResponse("Missing or invalid authentication token"));
        return;
    }

    try {
        Json::Value json;
        Json::CharReaderBuilder reader;
        std::string errs;
        std::istringstream iss(req->body());
        if (!Json::parseFromStream(reader, iss, &json, &errs)) {
            auto resp = drogon::HttpResponse::newHttpResponse();
            resp->setStatusCode(drogon::HttpStatusCode::k400BadRequest);
            resp->setBody("{\"error\":\"Invalid JSON: " + errs + "\"}");
            resp->setContentTypeCode(drogon::CT_APPLICATION_JSON);
            callback(resp);
            return;
        }

        query::QueryRequest request;
        request.tenant = userOpt->tenant;
        request.metric = json["metric"].asString();
        
        if (json.isMember("tags")) {
            for (auto it = json["tags"].begin(); it != json["tags"].end(); ++it) {
                request.tags[it.name()] = it->asString();
            }
        }

        request.startTime = utils::TimeUtils::parseTimeString(json["start"].asString());
        request.endTime = utils::TimeUtils::parseTimeString(json["end"].asString());
        request.aggregation = AggregationType::AVG;
        request.downsample = DownsampleInterval::RAW;

        QueryResult result = queryEngine_->queryRaw(request);

        Json::Value jsonResult;
        jsonResult["tenant"] = request.tenant;
        jsonResult["metric"] = request.metric;
        Json::Value points(Json::arrayValue);
        for (size_t i = 0; i < result.count(); ++i) {
            Json::Value point;
            point["timestamp"] = Json::Int64(result.timestamps[i]);
            point["value"] = result.values[i];
            points.append(point);
        }
        jsonResult["points"] = points;

        Json::StreamWriterBuilder writer;
        auto resp = drogon::HttpResponse::newHttpResponse();
        resp->setStatusCode(drogon::HttpStatusCode::k200OK);
        resp->setBody(Json::writeString(writer, jsonResult));
        resp->setContentTypeCode(drogon::CT_APPLICATION_JSON);
        callback(resp);
    } catch (const std::exception& e) {
        auto resp = drogon::HttpResponse::newHttpResponse();
        resp->setStatusCode(drogon::HttpStatusCode::k500InternalServerError);
        resp->setBody("{\"error\":\"" + std::string(e.what()) + "\"}");
        resp->setContentTypeCode(drogon::CT_APPLICATION_JSON);
        callback(resp);
    }
}

void HttpHandler::handleCreateRollup(const drogon::HttpRequestPtr& req,
                                      std::function<void(const drogon::HttpResponsePtr&)>&& callback) {
    auto userOpt = authenticate(req);
    if (!userOpt) {
        callback(auth::JwtAuth::makeUnauthorizedResponse("Missing or invalid authentication token"));
        return;
    }

    try {
        Json::Value json;
        Json::CharReaderBuilder reader;
        std::string errs;
        std::istringstream iss(req->body());
        if (!Json::parseFromStream(reader, iss, &json, &errs)) {
            auto resp = drogon::HttpResponse::newHttpResponse();
            resp->setStatusCode(drogon::HttpStatusCode::k400BadRequest);
            resp->setBody("{\"error\":\"Invalid JSON\"}");
            callback(resp);
            return;
        }

        rollup::RollupConfig config;
        config.name = json["name"].asString();
        config.metric = json["metric"].asString();
        config.enabled = json.get("enabled", true).asBool();
        
        std::string intervalStr = json.get("interval", "1m").asString();
        config.interval = parseDownsample(intervalStr);
        
        if (json.isMember("tags")) {
            for (auto it = json["tags"].begin(); it != json["tags"].end(); ++it) {
                config.tags[it.name()] = it->asString();
            }
        }

        bool success = rollupEngine_->createRollup(config);

        Json::Value result;
        result["status"] = success ? "success" : "error";
        if (!success) {
            result["message"] = "Rollup already exists";
        }

        Json::StreamWriterBuilder writer;
        auto resp = drogon::HttpResponse::newHttpResponse();
        resp->setStatusCode(success ? drogon::HttpStatusCode::k200OK : drogon::HttpStatusCode::k400BadRequest);
        resp->setBody(Json::writeString(writer, result));
        resp->setContentTypeCode(drogon::CT_APPLICATION_JSON);
        callback(resp);
    } catch (const std::exception& e) {
        auto resp = drogon::HttpResponse::newHttpResponse();
        resp->setStatusCode(drogon::HttpStatusCode::k500InternalServerError);
        resp->setBody("{\"error\":\"" + std::string(e.what()) + "\"}");
        callback(resp);
    }
}

void HttpHandler::handleDeleteRollup(const drogon::HttpRequestPtr& req,
                                      std::function<void(const drogon::HttpResponsePtr&)>&& callback) {
    auto userOpt = authenticate(req);
    if (!userOpt) {
        callback(auth::JwtAuth::makeUnauthorizedResponse("Missing or invalid authentication token"));
        return;
    }

    try {
        std::string name = req->getParameter("name");
        bool success = rollupEngine_->deleteRollup(name);

        Json::Value result;
        result["status"] = success ? "success" : "error";
        
        Json::StreamWriterBuilder writer;
        auto resp = drogon::HttpResponse::newHttpResponse();
        resp->setStatusCode(success ? drogon::HttpStatusCode::k200OK : drogon::HttpStatusCode::k404NotFound);
        resp->setBody(Json::writeString(writer, result));
        resp->setContentTypeCode(drogon::CT_APPLICATION_JSON);
        callback(resp);
    } catch (const std::exception& e) {
        auto resp = drogon::HttpResponse::newHttpResponse();
        resp->setStatusCode(drogon::HttpStatusCode::k500InternalServerError);
        resp->setBody("{\"error\":\"" + std::string(e.what()) + "\"}");
        callback(resp);
    }
}

void HttpHandler::handleListRollups(const drogon::HttpRequestPtr& req,
                                     std::function<void(const drogon::HttpResponsePtr&)>&& callback) {
    auto userOpt = authenticate(req);
    if (!userOpt) {
        callback(auth::JwtAuth::makeUnauthorizedResponse("Missing or invalid authentication token"));
        return;
    }

    try {
        auto rollups = rollupEngine_->listRollups();

        Json::Value jsonResult;
        Json::Value rollupsArray(Json::arrayValue);
        for (const auto& r : rollups) {
            Json::Value item;
            item["name"] = r.name;
            item["metric"] = r.metric;
            item["enabled"] = r.enabled;
            item["interval"] = r.interval == DownsampleInterval::MIN_1 ? "1m" :
                              r.interval == DownsampleInterval::MIN_5 ? "5m" : "1h";
            Json::Value tags;
            for (const auto& [k, v] : r.tags) {
                tags[k] = v;
            }
            item["tags"] = tags;
            rollupsArray.append(item);
        }
        jsonResult["rollups"] = rollupsArray;

        Json::StreamWriterBuilder writer;
        auto resp = drogon::HttpResponse::newHttpResponse();
        resp->setStatusCode(drogon::HttpStatusCode::k200OK);
        resp->setBody(Json::writeString(writer, jsonResult));
        resp->setContentTypeCode(drogon::CT_APPLICATION_JSON);
        callback(resp);
    } catch (const std::exception& e) {
        auto resp = drogon::HttpResponse::newHttpResponse();
        resp->setStatusCode(drogon::HttpStatusCode::k500InternalServerError);
        resp->setBody("{\"error\":\"" + std::string(e.what()) + "\"}");
        callback(resp);
    }
}

void HttpHandler::handleQueryRollup(const drogon::HttpRequestPtr& req,
                                     std::function<void(const drogon::HttpResponsePtr&)>&& callback) {
    auto userOpt = authenticate(req);
    if (!userOpt) {
        callback(auth::JwtAuth::makeUnauthorizedResponse("Missing or invalid authentication token"));
        return;
    }

    try {
        std::string name = req->getParameter("name");

        Json::Value json;
        Json::CharReaderBuilder reader;
        std::string errs;
        std::istringstream iss(req->body());
        if (!Json::parseFromStream(reader, iss, &json, &errs)) {
            auto resp = drogon::HttpResponse::newHttpResponse();
            resp->setStatusCode(drogon::HttpStatusCode::k400BadRequest);
            resp->setBody("{\"error\":\"Invalid JSON\"}");
            callback(resp);
            return;
        }

        Timestamp startTime = std::stoll(json["start"].asString());
        Timestamp endTime = std::stoll(json["end"].asString());

        auto results = rollupEngine_->queryRollup(name, startTime, endTime);

        Json::Value jsonResult;
        Json::Value points(Json::arrayValue);
        for (const auto& r : results) {
            Json::Value point;
            point["timestamp"] = Json::Int64(r.timestamp);
            point["avg"] = r.avg;
            point["max"] = r.max;
            point["min"] = r.min;
            point["sum"] = r.sum;
            point["count"] = r.count;
            points.append(point);
        }
        jsonResult["name"] = name;
        jsonResult["points"] = points;

        Json::StreamWriterBuilder writer;
        auto resp = drogon::HttpResponse::newHttpResponse();
        resp->setStatusCode(drogon::HttpStatusCode::k200OK);
        resp->setBody(Json::writeString(writer, jsonResult));
        resp->setContentTypeCode(drogon::CT_APPLICATION_JSON);
        callback(resp);
    } catch (const std::exception& e) {
        auto resp = drogon::HttpResponse::newHttpResponse();
        resp->setStatusCode(drogon::HttpStatusCode::k500InternalServerError);
        resp->setBody("{\"error\":\"" + std::string(e.what()) + "\"}");
        callback(resp);
    }
}

void HttpHandler::registerRoutes(drogon::HttpAppFramework& app) {
    app.registerHandler("/api/v1/login",
        [this](const drogon::HttpRequestPtr& req,
               std::function<void(const drogon::HttpResponsePtr&)>&& callback) {
            handleLogin(req, std::move(callback));
        },
        {drogon::HttpMethod::Post});

    app.registerHandler("/api/v1/write",
        [this](const drogon::HttpRequestPtr& req,
               std::function<void(const drogon::HttpResponsePtr&)>&& callback) {
            handleWrite(req, std::move(callback));
        },
        {drogon::HttpMethod::Post});

    app.registerHandler("/api/v1/query",
        [this](const drogon::HttpRequestPtr& req,
               std::function<void(const drogon::HttpResponsePtr&)>&& callback) {
            handleQuery(req, std::move(callback));
        },
        {drogon::HttpMethod::Post});

    app.registerHandler("/api/v1/query_raw",
        [this](const drogon::HttpRequestPtr& req,
               std::function<void(const drogon::HttpResponsePtr&)>&& callback) {
            handleQueryRaw(req, std::move(callback));
        },
        {drogon::HttpMethod::Post});

    app.registerHandler("/api/v1/rollups",
        [this](const drogon::HttpRequestPtr& req,
               std::function<void(const drogon::HttpResponsePtr&)>&& callback) {
            handleListRollups(req, std::move(callback));
        },
        {drogon::HttpMethod::Get});

    app.registerHandler("/api/v1/rollups",
        [this](const drogon::HttpRequestPtr& req,
               std::function<void(const drogon::HttpResponsePtr&)>&& callback) {
            handleCreateRollup(req, std::move(callback));
        },
        {drogon::HttpMethod::Post});

    app.registerHandler("/api/v1/rollups/{name}",
        [this](const drogon::HttpRequestPtr& req,
               std::function<void(const drogon::HttpResponsePtr&)>&& callback) {
            handleDeleteRollup(req, std::move(callback));
        },
        {drogon::HttpMethod::Delete});

    app.registerHandler("/api/v1/rollups/{name}/query",
        [this](const drogon::HttpRequestPtr& req,
               std::function<void(const drogon::HttpResponsePtr&)>&& callback) {
            handleQueryRollup(req, std::move(callback));
        },
        {drogon::HttpMethod::Post});

    app.registerWebSocketHandler("/api/v1/ws/subscribe",
        [](const std::shared_ptr<drogon::WebSocketConnection>& conn,
           const std::string& message) {
            tsdb::websocket::DataSubscriptionManager::instance().handleMessage(conn, message);
        },
        [](const std::shared_ptr<drogon::WebSocketConnection>& conn) {
            tsdb::websocket::DataSubscriptionManager::instance().handleNewConnection(conn);
        },
        [](const std::shared_ptr<drogon::WebSocketConnection>& conn) {
            tsdb::websocket::DataSubscriptionManager::instance().handleClose(conn);
        });
}

}
