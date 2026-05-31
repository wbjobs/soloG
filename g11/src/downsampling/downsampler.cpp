#include "tsdb/downsampling/downsampler.h"
#include "tsdb/utils/serializer.h"
#include "tsdb/utils/time_utils.h"
#include <sstream>

namespace tsdb::downsampling {

Downsampler::Downsampler(std::shared_ptr<storage::RocksDBEngine> engine,
                         DownsampleInterval interval)
    : engine_(std::move(engine)), interval_(interval) {}

std::string Downsampler::makeKey(const TenantId& tenant,
                                 const Metric& metric,
                                 const Tags& tags,
                                 Timestamp bucket) {
    std::string result;
    result += "ds\0";
    result += std::to_string(static_cast<int>(interval_));
    result += '\0';
    result += tenant;
    result += '\0';
    result += metric;
    result += '\0';
    result += utils::Serializer::serializeTags(tags);
    result += '\0';
    
    uint64_t ts = static_cast<uint64_t>(bucket);
    for (int i = 7; i >= 0; --i) {
        result += static_cast<char>((ts >> (i * 8)) & 0xFF);
    }
    return result;
}

void Downsampler::addPoint(const TenantId& tenant,
                           const Metric& metric,
                           const Tags& tags,
                           Timestamp timestamp,
                           Value value) {
    Timestamp bucket = utils::TimeUtils::alignToInterval(timestamp, interval_);
    std::string key = makeKey(tenant, metric, tags, bucket);

    std::lock_guard<std::mutex> lock(mutex_);
    auto it = buffer_.find(key);
    if (it == buffer_.end()) {
        AggregatedValue agg{value, value, value, 1.0};
        buffer_[key] = agg;
    } else {
        it->second.sum += value;
        it->second.min = std::min(it->second.min, value);
        it->second.max = std::max(it->second.max, value);
        it->second.count += 1;
    }
}

void Downsampler::flush() {
    std::vector<std::pair<std::string, std::string>> batch;
    
    {
        std::lock_guard<std::mutex> lock(mutex_);
        for (const auto& [key, agg] : buffer_) {
            std::ostringstream oss;
            oss.precision(17);
            oss << agg.sum << ' ' << agg.min << ' ' << agg.max << ' ' << agg.count;
            batch.emplace_back(key, oss.str());
        }
        buffer_.clear();
    }

    if (!batch.empty()) {
        engine_->writeBatch(batch);
    }
}

AggregatedValue Downsampler::getAggregated(const TenantId& tenant,
                                           const Metric& metric,
                                           const Tags& tags,
                                           Timestamp startTime,
                                           Timestamp endTime) {
    auto points = scanRange(tenant, metric, tags, startTime, endTime);
    
    AggregatedValue result{0, 0, 0, 0};
    if (points.empty()) return result;

    result.min = points[0].second.min;
    result.max = points[0].second.max;

    for (const auto& [ts, agg] : points) {
        result.sum += agg.sum;
        result.count += agg.count;
        result.min = std::min(result.min, agg.min);
        result.max = std::max(result.max, agg.max);
    }

    return result;
}

std::vector<std::pair<Timestamp, AggregatedValue>> Downsampler::scanRange(
    const TenantId& tenant,
    const Metric& metric,
    const Tags& tags,
    Timestamp startTime,
    Timestamp endTime) {
    
    std::vector<std::pair<Timestamp, AggregatedValue>> result;
    
    Timestamp startBucket = utils::TimeUtils::alignToInterval(startTime, interval_);
    Timestamp endBucket = utils::TimeUtils::alignToInterval(endTime, interval_);
    
    std::string prefix = "ds\0" + std::to_string(static_cast<int>(interval_)) + '\0' +
                         tenant + '\0' + metric + '\0' +
                         utils::Serializer::serializeTags(tags) + '\0';
    
    std::string startKey = prefix;
    uint64_t startTs = static_cast<uint64_t>(startBucket);
    for (int i = 7; i >= 0; --i) {
        startKey += static_cast<char>((startTs >> (i * 8)) & 0xFF);
    }
    
    std::string endKey = prefix;
    uint64_t endTs = static_cast<uint64_t>(endBucket + 1);
    for (int i = 7; i >= 0; --i) {
        endKey += static_cast<char>((endTs >> (i * 8)) & 0xFF);
    }

    engine_->scanRange(startKey, endKey, [&](const std::string& key, const std::string& value) {
        Timestamp bucket = 0;
        for (int i = 0; i < 8; ++i) {
            bucket = (bucket << 8) | static_cast<uint8_t>(key[key.size() - 8 + i]);
        }

        AggregatedValue agg;
        std::istringstream iss(value);
        iss >> agg.sum >> agg.min >> agg.max >> agg.count;

        result.emplace_back(bucket, agg);
        return true;
    });

    return result;
}

}
