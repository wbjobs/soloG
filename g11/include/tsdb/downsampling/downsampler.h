#pragma once

#include <memory>
#include <mutex>
#include <map>
#include <vector>
#include <Eigen/Dense>
#include "../types.h"
#include "../storage/rocksdb_engine.h"

namespace tsdb::downsampling {

struct AggregatedValue {
    Value sum;
    Value min;
    Value max;
    Value count;
    Value avg() const { return count > 0 ? sum / count : 0; }
};

class Downsampler {
public:
    Downsampler(std::shared_ptr<storage::RocksDBEngine> engine,
                DownsampleInterval interval);
    ~Downsampler() = default;

    void addPoint(const TenantId& tenant,
                  const Metric& metric,
                  const Tags& tags,
                  Timestamp timestamp,
                  Value value);

    void flush();

    AggregatedValue getAggregated(const TenantId& tenant,
                                  const Metric& metric,
                                  const Tags& tags,
                                  Timestamp startTime,
                                  Timestamp endTime);

    std::vector<std::pair<Timestamp, AggregatedValue>> scanRange(
        const TenantId& tenant,
        const Metric& metric,
        const Tags& tags,
        Timestamp startTime,
        Timestamp endTime);

private:
    std::string makeKey(const TenantId& tenant,
                        const Metric& metric,
                        const Tags& tags,
                        Timestamp bucket);

    std::shared_ptr<storage::RocksDBEngine> engine_;
    DownsampleInterval interval_;
    std::mutex mutex_;
    std::map<std::string, AggregatedValue> buffer_;
};

}
