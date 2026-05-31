#include "tsdb/query/query_engine.h"
#include "tsdb/utils/serializer.h"
#include <algorithm>
#include <iostream>

namespace tsdb::query {

QueryEngine::QueryEngine(std::shared_ptr<storage::RocksDBEngine> engine,
                         std::shared_ptr<index::TagIndex> tagIndex,
                         std::shared_ptr<downsampling::Downsampler> downsampler1m,
                         std::shared_ptr<downsampling::Downsampler> downsampler5m,
                         std::shared_ptr<downsampling::Downsampler> downsampler1h)
    : engine_(std::move(engine)),
      tagIndex_(std::move(tagIndex)),
      downsampler1m_(std::move(downsampler1m)),
      downsampler5m_(std::move(downsampler5m)),
      downsampler1h_(std::move(downsampler1h)) {}

std::vector<DataPoint> QueryEngine::scanRawData(const TenantId& tenant,
                                                const Metric& metric,
                                                const Tags& tags,
                                                Timestamp startTime,
                                                Timestamp endTime) {
    std::vector<DataPoint> result;
    
    std::string prefix = utils::Serializer::makeDataPrefix(tenant, metric, tags);
    
    std::string startKey = prefix;
    uint64_t startTs = static_cast<uint64_t>(startTime);
    for (int i = 7; i >= 0; --i) {
        startKey += static_cast<char>((startTs >> (i * 8)) & 0xFF);
    }
    
    std::string endKey = prefix;
    uint64_t endTs = static_cast<uint64_t>(endTime);
    for (int i = 7; i >= 0; --i) {
        endKey += static_cast<char>((endTs >> (i * 8)) & 0xFF);
    }

    engine_->scanRange(startKey, endKey, [&](const std::string& key, const std::string& value) {
        Timestamp ts = 0;
        for (int i = 0; i < 8; ++i) {
            ts = (ts << 8) | static_cast<uint8_t>(key[key.size() - 8 + i]);
        }
        Value val = utils::Serializer::deserializeValue(value);
        result.push_back({ts, val});
        return true;
    });

    return result;
}

Value QueryEngine::applyAggregation(const Eigen::VectorXd& values, AggregationType type) {
    if (values.size() == 0) return 0;
    
    switch (type) {
        case AggregationType::AVG:
            return values.mean();
        case AggregationType::MAX:
            return values.maxCoeff();
        case AggregationType::MIN:
            return values.minCoeff();
        case AggregationType::SUM:
            return values.sum();
        case AggregationType::COUNT:
            return static_cast<Value>(values.size());
        default:
            return 0;
    }
}

QueryResult QueryEngine::queryRaw(const QueryRequest& request) {
    QueryResult result;
    
    auto points = scanRawData(request.tenant, request.metric,
                              request.tags, request.startTime, request.endTime);
    
    result.timestamps.reserve(points.size());
    result.values.reserve(points.size());
    
    for (const auto& p : points) {
        result.timestamps.push_back(p.timestamp);
        result.values.push_back(p.value);
    }
    
    return result;
}

QueryResult QueryEngine::queryAggregated(const QueryRequest& request) {
    QueryResult result;
    
    if (request.downsample == DownsampleInterval::RAW) {
        auto points = scanRawData(request.tenant, request.metric,
                                  request.tags, request.startTime, request.endTime);
        
        if (points.empty()) return result;

        Eigen::VectorXd values(points.size());
        for (size_t i = 0; i < points.size(); ++i) {
            values[i] = points[i].value;
        }
        
        result.timestamps.push_back(request.startTime);
        result.values.push_back(applyAggregation(values, request.aggregation));
        return result;
    }

    std::shared_ptr<downsampling::Downsampler> downsampler;
    switch (request.downsample) {
        case DownsampleInterval::MIN_1:
            downsampler = downsampler1m_;
            break;
        case DownsampleInterval::MIN_5:
            downsampler = downsampler5m_;
            break;
        case DownsampleInterval::HOUR_1:
            downsampler = downsampler1h_;
            break;
        default:
            return result;
    }

    auto buckets = downsampler->scanRange(request.tenant, request.metric,
                                          request.tags, request.startTime, request.endTime);

    result.timestamps.reserve(buckets.size());
    result.values.reserve(buckets.size());

    for (const auto& [ts, agg] : buckets) {
        result.timestamps.push_back(ts);
        
        Value val = 0;
        switch (request.aggregation) {
            case AggregationType::AVG:
                val = agg.avg();
                break;
            case AggregationType::MAX:
                val = agg.max;
                break;
            case AggregationType::MIN:
                val = agg.min;
                break;
            case AggregationType::SUM:
                val = agg.sum;
                break;
            case AggregationType::COUNT:
                val = agg.count;
                break;
        }
        result.values.push_back(val);
    }

    return result;
}

std::vector<QueryResult> QueryEngine::queryByTags(const QueryRequest& request) {
    std::vector<QueryResult> results;
    
    auto seriesIds = tagIndex_->findSeriesByTags(request.tenant, request.metric, request.tags);
    
    for (const auto& seriesId : seriesIds) {
        QueryRequest subRequest = request;
        QueryResult result = queryAggregated(subRequest);
        if (result.count() > 0) {
            results.push_back(std::move(result));
        }
    }
    
    return results;
}

}
