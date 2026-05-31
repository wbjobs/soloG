#pragma once

#include <memory>
#include <vector>
#include <string>
#include <Eigen/Dense>
#include "../types.h"
#include "../storage/rocksdb_engine.h"
#include "../downsampling/downsampler.h"
#include "../index/tag_index.h"

namespace tsdb::query {

struct QueryRequest {
    TenantId tenant;
    Metric metric;
    Tags tags;
    Timestamp startTime;
    Timestamp endTime;
    AggregationType aggregation;
    DownsampleInterval downsample;
};

class QueryEngine {
public:
    QueryEngine(std::shared_ptr<storage::RocksDBEngine> engine,
                std::shared_ptr<index::TagIndex> tagIndex,
                std::shared_ptr<downsampling::Downsampler> downsampler1m,
                std::shared_ptr<downsampling::Downsampler> downsampler5m,
                std::shared_ptr<downsampling::Downsampler> downsampler1h);
    
    ~QueryEngine() = default;

    QueryResult queryRaw(const QueryRequest& request);

    QueryResult queryAggregated(const QueryRequest& request);

    std::vector<QueryResult> queryByTags(const QueryRequest& request);

private:
    std::vector<DataPoint> scanRawData(const TenantId& tenant,
                                       const Metric& metric,
                                       const Tags& tags,
                                       Timestamp startTime,
                                       Timestamp endTime);

    Value applyAggregation(const Eigen::VectorXd& values, AggregationType type);

    std::shared_ptr<storage::RocksDBEngine> engine_;
    std::shared_ptr<index::TagIndex> tagIndex_;
    std::shared_ptr<downsampling::Downsampler> downsampler1m_;
    std::shared_ptr<downsampling::Downsampler> downsampler5m_;
    std::shared_ptr<downsampling::Downsampler> downsampler1h_;
};

}
