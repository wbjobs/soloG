#include "tsdb/index/tag_index.h"
#include "tsdb/utils/serializer.h"

namespace tsdb::index {

TagIndex::TagIndex(std::shared_ptr<storage::RocksDBEngine> engine)
    : engine_(std::move(engine)) {}

bool TagIndex::indexSeries(const TenantId& tenant,
                           const Metric& metric,
                           const Tags& tags,
                           const std::string& seriesId) {
    std::string seriesKey = utils::Serializer::makeSeriesKey(tenant, metric, tags);
    std::string existing;
    if (engine_->get(seriesKey, &existing)) {
        return true;
    }

    std::vector<std::pair<std::string, std::string>> batch;
    batch.emplace_back(seriesKey, seriesId);

    for (const auto& [tagKey, tagValue] : tags) {
        std::string idxKey = utils::Serializer::makeIndexKey(
            tenant, metric, tagKey, tagValue, seriesId);
        batch.emplace_back(idxKey, "1");
    }

    return engine_->writeBatch(batch);
}

std::set<std::string> TagIndex::findSeriesByTags(const TenantId& tenant,
                                                 const Metric& metric,
                                                 const Tags& tags) {
    std::set<std::string> result;
    bool first = true;

    for (const auto& [tagKey, tagValue] : tags) {
        std::string prefix = "idx\0" + tenant + '\0' + metric + '\0' + tagKey + '\0' + tagValue + '\0';
        std::set<std::string> current;

        engine_->scanPrefix(prefix, [&current](const std::string& key, const std::string&) {
            size_t pos = key.find_last_of('\0');
            if (pos != std::string::npos) {
                current.insert(key.substr(pos + 1));
            }
            return true;
        });

        if (first) {
            result = std::move(current);
            first = false;
        } else {
            std::set<std::string> intersection;
            for (const auto& id : result) {
                if (current.count(id)) {
                    intersection.insert(id);
                }
            }
            result = std::move(intersection);
        }

        if (result.empty()) {
            break;
        }
    }

    return result;
}

std::vector<std::string> TagIndex::getAllSeries(const TenantId& tenant,
                                                const Metric& metric) {
    std::vector<std::string> result;
    std::string prefix = "series\0" + tenant + '\0' + metric + '\0';
    
    engine_->scanPrefix(prefix, [&result](const std::string&, const std::string& value) {
        result.push_back(value);
        return true;
    });

    return result;
}

bool TagIndex::removeSeries(const TenantId& tenant,
                            const Metric& metric,
                            const Tags& tags,
                            const std::string& seriesId) {
    std::string seriesKey = utils::Serializer::makeSeriesKey(tenant, metric, tags);
    engine_->remove(seriesKey);

    for (const auto& [tagKey, tagValue] : tags) {
        std::string idxKey = utils::Serializer::makeIndexKey(
            tenant, metric, tagKey, tagValue, seriesId);
        engine_->remove(idxKey);
    }

    return true;
}

}
