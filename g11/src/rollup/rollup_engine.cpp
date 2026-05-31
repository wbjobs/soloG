#include "tsdb/rollup/rollup_engine.h"
#include "tsdb/utils/serializer.h"
#include "tsdb/utils/time_utils.h"
#include <sstream>
#include <iostream>

namespace tsdb::rollup {

RollupEngine::RollupEngine(std::shared_ptr<storage::RocksDBEngine> engine)
    : engine_(std::move(engine)) {}

std::string RollupEngine::makeKey(const std::string& rollupName, Timestamp bucket) {
    std::string key;
    key += "rollup\0";
    key += rollupName;
    key += '\0';
    
    uint64_t ts = static_cast<uint64_t>(bucket);
    for (int i = 7; i >= 0; --i) {
        key += static_cast<char>((ts >> (i * 8)) & 0xFF);
    }
    return key;
}

bool RollupEngine::createRollup(const RollupConfig& config) {
    std::lock_guard<std::mutex> lock(mutex_);
    
    std::string configKey = "rollup_config\0" + config.name;
    std::string existing;
    if (engine_->get(configKey, &existing)) {
        return false;
    }
    
    std::ostringstream oss;
    oss << config.metric << '\0'
        << utils::Serializer::serializeTags(config.tags) << '\0'
        << static_cast<int>(config.interval) << '\0'
        << (config.enabled ? "1" : "0");
    
    if (!engine_->put(configKey, oss.str())) {
        return false;
    }
    
    rollups_[config.name] = config;
    return true;
}

bool RollupEngine::deleteRollup(const std::string& name) {
    std::lock_guard<std::mutex> lock(mutex_);
    
    std::string configKey = "rollup_config\0" + name;
    if (!engine_->remove(configKey)) {
        return false;
    }
    
    rollups_.erase(name);
    buffer_.erase(name);
    
    std::string prefix = "rollup\0" + name + '\0';
    std::vector<std::string> keysToDelete;
    engine_->scanPrefix(prefix, [&keysToDelete](const std::string& key, const std::string&) {
        keysToDelete.push_back(key);
        return true;
    });
    
    for (const auto& key : keysToDelete) {
        engine_->remove(key);
    }
    
    return true;
}

std::vector<RollupConfig> RollupEngine::listRollups() const {
    std::lock_guard<std::mutex> lock(mutex_);
    std::vector<RollupConfig> result;
    for (const auto& [name, config] : rollups_) {
        result.push_back(config);
    }
    return result;
}

void RollupEngine::onDataWritten(const TenantId& tenant,
                                 const Metric& metric,
                                 const Tags& tags,
                                 Timestamp timestamp,
                                 Value value) {
    std::lock_guard<std::mutex> lock(mutex_);
    
    for (const auto& [name, config] : rollups_) {
        if (!config.enabled) continue;
        if (config.metric != metric) continue;
        
        bool tagsMatch = true;
        for (const auto& [k, v] : config.tags) {
            auto it = tags.find(k);
            if (it == tags.end() || it->second != v) {
                tagsMatch = false;
                break;
            }
        }
        if (!tagsMatch) continue;
        
        Timestamp bucket = utils::TimeUtils::alignToInterval(timestamp, config.interval);
        std::string bucketKey = std::to_string(bucket);
        
        auto& bucketBuffer = buffer_[name];
        auto it = bucketBuffer.find(bucketKey);
        if (it == bucketBuffer.end()) {
            downsampling::AggregatedValue agg{value, value, value, 1.0};
            bucketBuffer[bucketKey] = agg;
        } else {
            it->second.sum += value;
            it->second.min = std::min(it->second.min, value);
            it->second.max = std::max(it->second.max, value);
            it->second.count += 1;
        }
    }
}

void RollupEngine::flushAll() {
    std::vector<std::pair<std::string, std::string>> batch;
    
    {
        std::lock_guard<std::mutex> lock(mutex_);
        
        for (const auto& [rollupName, bucketData] : buffer_) {
            for (const auto& [bucketKey, agg] : bucketData) {
                Timestamp bucket = std::stoll(bucketKey);
                std::string key = makeKey(rollupName, bucket);
                
                std::ostringstream oss;
                oss.precision(17);
                oss << agg.sum << ' ' << agg.min << ' ' << agg.max << ' ' << agg.count;
                
                batch.emplace_back(key, oss.str());
            }
        }
        buffer_.clear();
    }
    
    if (!batch.empty()) {
        engine_->writeBatch(batch);
    }
}

std::vector<RollupResult> RollupEngine::queryRollup(const std::string& name,
                                                     Timestamp startTime,
                                                     Timestamp endTime) {
    std::vector<RollupResult> result;
    
    RollupConfig config;
    {
        std::lock_guard<std::mutex> lock(mutex_);
        auto it = rollups_.find(name);
        if (it == rollups_.end()) {
            return result;
        }
        config = it->second;
    }
    
    Timestamp startBucket = utils::TimeUtils::alignToInterval(startTime, config.interval);
    Timestamp endBucket = utils::TimeUtils::alignToInterval(endTime, config.interval);
    
    std::string prefix = "rollup\0" + name + '\0';
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
        
        downsampling::AggregatedValue agg;
        std::istringstream iss(value);
        iss >> agg.sum >> agg.min >> agg.max >> agg.count;
        
        RollupResult r;
        r.name = name;
        r.metric = config.metric;
        r.tags = config.tags;
        r.timestamp = bucket;
        r.avg = agg.avg();
        r.max = agg.max;
        r.min = agg.min;
        r.sum = agg.sum;
        r.count = agg.count;
        
        result.push_back(std::move(r));
        return true;
    });
    
    return result;
}

}
