#pragma once

#include <cstdint>
#include <string>
#include <map>
#include <vector>
#include <chrono>

namespace tsdb {

using Timestamp = int64_t;
using TenantId = std::string;
using Metric = std::string;
using Tags = std::map<std::string, std::string>;
using Value = double;

struct DataPoint {
    Timestamp timestamp;
    Value value;
};

struct TimeSeries {
    TenantId tenant;
    Metric metric;
    Tags tags;
    std::vector<DataPoint> points;
};

enum class AggregationType {
    AVG,
    MAX,
    MIN,
    SUM,
    COUNT
};

enum class DownsampleInterval {
    RAW = 0,
    MIN_1 = 60,
    MIN_5 = 300,
    HOUR_1 = 3600
};

struct QueryResult {
    std::vector<Timestamp> timestamps;
    std::vector<Value> values;
    size_t count() const { return timestamps.size(); }
};

inline Timestamp now() {
    return std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::system_clock::now().time_since_epoch()
    ).count();
}

}
