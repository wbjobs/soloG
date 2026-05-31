#pragma once

#include <memory>
#include <optional>
#include <drogon/drogon.h>
#include "../types.h"
#include "../storage/rocksdb_engine.h"
#include "../query/query_engine.h"
#include "../downsampling/downsampler.h"
#include "../index/tag_index.h"
#include "../auth/jwt_auth.h"
#include "../rollup/rollup_engine.h"

namespace tsdb::api {

class HttpHandler {
public:
    HttpHandler(std::shared_ptr<storage::RocksDBEngine> engine,
                std::shared_ptr<query::QueryEngine> queryEngine,
                std::shared_ptr<index::TagIndex> tagIndex,
                std::shared_ptr<downsampling::Downsampler> downsampler1m,
                std::shared_ptr<downsampling::Downsampler> downsampler5m,
                std::shared_ptr<downsampling::Downsampler> downsampler1h,
                std::shared_ptr<rollup::RollupEngine> rollupEngine);

    void registerRoutes(drogon::HttpAppFramework& app);

private:
    std::optional<auth::UserInfo> authenticate(const drogon::HttpRequestPtr& req);

    void handleWrite(const drogon::HttpRequestPtr& req,
                     std::function<void(const drogon::HttpResponsePtr&)>&& callback);

    void handleQuery(const drogon::HttpRequestPtr& req,
                     std::function<void(const drogon::HttpResponsePtr&)>&& callback);

    void handleQueryRaw(const drogon::HttpRequestPtr& req,
                        std::function<void(const drogon::HttpResponsePtr&)>&& callback);

    void handleLogin(const drogon::HttpRequestPtr& req,
                     std::function<void(const drogon::HttpResponsePtr&)>&& callback);

    void handleCreateRollup(const drogon::HttpRequestPtr& req,
                            std::function<void(const drogon::HttpResponsePtr&)>&& callback);

    void handleDeleteRollup(const drogon::HttpRequestPtr& req,
                            std::function<void(const drogon::HttpResponsePtr&)>&& callback);

    void handleListRollups(const drogon::HttpRequestPtr& req,
                           std::function<void(const drogon::HttpResponsePtr&)>&& callback);

    void handleQueryRollup(const drogon::HttpRequestPtr& req,
                           std::function<void(const drogon::HttpResponsePtr&)>&& callback);

    std::shared_ptr<storage::RocksDBEngine> engine_;
    std::shared_ptr<query::QueryEngine> queryEngine_;
    std::shared_ptr<index::TagIndex> tagIndex_;
    std::shared_ptr<downsampling::Downsampler> downsampler1m_;
    std::shared_ptr<downsampling::Downsampler> downsampler5m_;
    std::shared_ptr<downsampling::Downsampler> downsampler1h_;
    std::shared_ptr<rollup::RollupEngine> rollupEngine_;

    AggregationType parseAggregation(const std::string& agg);
    DownsampleInterval parseDownsample(const std::string& ds);
};

}
