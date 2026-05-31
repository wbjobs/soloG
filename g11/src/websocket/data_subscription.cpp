#include "tsdb/websocket/data_subscription.h"
#include "tsdb/config/config.h"
#include "tsdb/utils/serializer.h"
#include <json/json.h>
#include <sstream>
#include <random>

namespace tsdb::websocket {

DataSubscriptionManager& DataSubscriptionManager::instance() {
    static DataSubscriptionManager instance;
    return instance;
}

std::string DataSubscriptionManager::generateId() {
    static std::random_device rd;
    static std::mt19937 gen(rd());
    static std::uniform_int_distribution<> dis(0, 15);
    
    std::string id = "sub_";
    const char* hex = "0123456789abcdef";
    for (int i = 0; i < 16; ++i) {
        id += hex[dis(gen)];
    }
    return id;
}

std::string DataSubscriptionManager::subscribe(const TenantId& tenant,
                                               const Metric& metric,
                                               const Tags& tags,
                                               std::shared_ptr<drogon::WebSocketConnection> connection) {
    std::lock_guard<std::mutex> lock(mutex_);
    
    std::string subId = generateId();
    Subscription sub{subId, tenant, metric, tags, connection};
    
    subscriptions_[subId] = sub;
    
    std::string connId = std::to_string(reinterpret_cast<uintptr_t>(connection.get()));
    connectionSubscriptions_[connId].insert(subId);
    
    std::string metricKey = tenant + '\0' + metric;
    metricSubscriptions_[metricKey][utils::Serializer::serializeTags(tags)].insert(subId);
    
    return subId;
}

void DataSubscriptionManager::unsubscribe(const std::string& subscriptionId) {
    std::lock_guard<std::mutex> lock(mutex_);
    
    auto it = subscriptions_.find(subscriptionId);
    if (it == subscriptions_.end()) return;
    
    const Subscription& sub = it->second;
    auto conn = sub.connection.lock();
    if (conn) {
        std::string connId = std::to_string(reinterpret_cast<uintptr_t>(conn.get()));
        connectionSubscriptions_[connId].erase(subscriptionId);
    }
    
    std::string metricKey = sub.tenant + '\0' + sub.metric;
    std::string tagsKey = utils::Serializer::serializeTags(sub.tags);
    metricSubscriptions_[metricKey][tagsKey].erase(subscriptionId);
    
    subscriptions_.erase(it);
}

void DataSubscriptionManager::onDataWritten(const TenantId& tenant,
                                            const Metric& metric,
                                            const Tags& tags,
                                            Timestamp timestamp,
                                            Value value) {
    std::lock_guard<std::mutex> lock(mutex_);
    
    std::string metricKey = tenant + '\0' + metric;
    auto metricIt = metricSubscriptions_.find(metricKey);
    if (metricIt == metricSubscriptions_.end()) return;
    
    std::set<std::string> matchedSubs;
    for (const auto& [tagsKey, subs] : metricIt->second) {
        Tags subTags = utils::Serializer::deserializeTags(tagsKey);
        
        bool tagsMatch = true;
        for (const auto& [k, v] : subTags) {
            auto it = tags.find(k);
            if (it == tags.end() || it->second != v) {
                tagsMatch = false;
                break;
            }
        }
        
        if (tagsMatch) {
            for (const auto& subId : subs) {
                matchedSubs.insert(subId);
            }
        }
    }
    
    if (matchedSubs.empty()) return;
    
    Json::Value payload;
    payload["type"] = "data";
    payload["tenant"] = tenant;
    payload["metric"] = metric;
    Json::Value jsonTags;
    for (const auto& [k, v] : tags) {
        jsonTags[k] = v;
    }
    payload["tags"] = jsonTags;
    payload["timestamp"] = Json::Int64(timestamp);
    payload["value"] = value;
    
    Json::StreamWriterBuilder writer;
    std::string message = Json::writeString(writer, payload);
    
    for (const auto& subId : matchedSubs) {
        auto subIt = subscriptions_.find(subId);
        if (subIt == subscriptions_.end()) continue;
        
        auto conn = subIt->second.connection.lock();
        if (conn && conn->connected()) {
            conn->send(message);
        }
    }
}

void DataSubscriptionManager::handleNewConnection(std::shared_ptr<drogon::WebSocketConnection> connection) {
    Json::Value welcome;
    welcome["type"] = "welcome";
    welcome["message"] = "Connected to TSDB real-time data stream";
    
    Json::StreamWriterBuilder writer;
    connection->send(Json::writeString(writer, welcome));
}

void DataSubscriptionManager::handleMessage(std::shared_ptr<drogon::WebSocketConnection> connection,
                                            const std::string& message) {
    Json::Value json;
    Json::CharReaderBuilder reader;
    std::string errs;
    std::istringstream iss(message);
    if (!Json::parseFromStream(reader, iss, &json, &errs)) {
        Json::Value error;
        error["type"] = "error";
        error["message"] = "Invalid JSON";
        Json::StreamWriterBuilder writer;
        connection->send(Json::writeString(writer, error));
        return;
    }
    
    std::string action = json.get("action", "").asString();
    
    if (config::Config::instance().enableAuth()) {
        std::string token = json.get("token", "").asString();
        auto userOpt = auth::JwtAuth::validateToken(token);
        if (!userOpt) {
            Json::Value error;
            error["type"] = "error";
            error["message"] = "Invalid or missing authentication token";
            Json::StreamWriterBuilder writer;
            connection->send(Json::writeString(writer, error));
            return;
        }
    }
    
    if (action == "subscribe") {
        TenantId tenant = json.get("tenant", "").asString();
        Metric metric = json.get("metric", "").asString();
        Tags tags;
        if (json.isMember("tags")) {
            for (auto it = json["tags"].begin(); it != json["tags"].end(); ++it) {
                tags[it.name()] = it->asString();
            }
        }
        
        std::string subId = subscribe(tenant, metric, tags, connection);
        
        Json::Value response;
        response["type"] = "subscribed";
        response["subscription_id"] = subId;
        response["tenant"] = tenant;
        response["metric"] = metric;
        Json::Value jsonTags;
        for (const auto& [k, v] : tags) {
            jsonTags[k] = v;
        }
        response["tags"] = jsonTags;
        
        Json::StreamWriterBuilder writer;
        connection->send(Json::writeString(writer, response));
        
    } else if (action == "unsubscribe") {
        std::string subId = json.get("subscription_id", "").asString();
        unsubscribe(subId);
        
        Json::Value response;
        response["type"] = "unsubscribed";
        response["subscription_id"] = subId;
        
        Json::StreamWriterBuilder writer;
        connection->send(Json::writeString(writer, response));
        
    } else {
        Json::Value error;
        error["type"] = "error";
        error["message"] = "Unknown action: " + action;
        Json::StreamWriterBuilder writer;
        connection->send(Json::writeString(writer, error));
    }
}

void DataSubscriptionManager::handleClose(std::shared_ptr<drogon::WebSocketConnection> connection) {
    std::lock_guard<std::mutex> lock(mutex_);
    
    std::string connId = std::to_string(reinterpret_cast<uintptr_t>(connection.get()));
    auto it = connectionSubscriptions_.find(connId);
    if (it == connectionSubscriptions_.end()) return;
    
    std::vector<std::string> subsToRemove(it->second.begin(), it->second.end());
    connectionSubscriptions_.erase(it);
    
    for (const auto& subId : subsToRemove) {
        subscriptions_.erase(subId);
    }
}

}
