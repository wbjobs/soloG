#pragma once

#include <memory>
#include <string>
#include <vector>
#include <set>
#include <map>
#include "../types.h"
#include "../storage/rocksdb_engine.h"

namespace tsdb::index {

class TagIndex {
public:
    explicit TagIndex(std::shared_ptr<storage::RocksDBEngine> engine);
    ~TagIndex() = default;

    bool indexSeries(const TenantId& tenant,
                     const Metric& metric,
                     const Tags& tags,
                     const std::string& seriesId);

    std::set<std::string> findSeriesByTags(const TenantId& tenant,
                                           const Metric& metric,
                                           const Tags& tags);

    std::vector<std::string> getAllSeries(const TenantId& tenant,
                                          const Metric& metric);

    bool removeSeries(const TenantId& tenant,
                      const Metric& metric,
                      const Tags& tags,
                      const std::string& seriesId);

private:
    std::shared_ptr<storage::RocksDBEngine> engine_;
};

}
