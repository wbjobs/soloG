#pragma once

#include <memory>
#include <string>
#include <map>
#include <mutex>
#include <vector>
#include "../types.h"
#include "../storage/rocksdb_engine.h"
#include "../downsampling/downsampler.h"

namespace tsdb::rollup {

struct RollupConfig {
    std::string name;
    Metric metric;
    Tags tags;
    DownsampleInterval interval;
    bool enabled;
};

struct RollupResult {
    std::string name;
    Metric metric;
    Tags tags;
    Timestamp timestamp;
    Value avg;
    Value max;
    Value min;
    Value sum;
    Value count;
};

class RollupEngine {
public:
    RollupEngine(std::shared_ptr<storage::RocksDBEngine> engine);
    ~RollupEngine() = default;

    bool createRollup(const RollupConfig& config);
    
    bool deleteRollup(const std::string& name);
    
    std::vector<RollupConfig> listRollups() const;
    
    void onDataWritten(const TenantId& tenant,
                       const Metric& metric,
                       const Tags& tags,
                       Timestamp timestamp,
                       Value value);
    
    std::vector<RollupResult> queryRollup(const std::string& name,
                                           Timestamp startTime,
                                           Timestamp endTime);
    
    void flushAll();

private:
    std::string makeKey(const std::string& rollupName, Timestamp bucket);
    
    std::shared_ptr<storage::RocksDBEngine> engine_;
    mutable std::mutex mutex_;
    std::map<std::string, RollupConfig> rollups_;
    std::map<std::string, std::map<std::string, downsampling::AggregatedValue>> buffer_;
};

}
