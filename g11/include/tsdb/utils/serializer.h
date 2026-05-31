#pragma once

#include <string>
#include <vector>
#include <cstring>
#include "../types.h"

namespace tsdb::utils {

class Serializer {
public:
    static std::string serializeKey(const TenantId& tenant,
                                    const Metric& metric,
                                    const Tags& tags,
                                    Timestamp timestamp);

    static std::string serializeValue(Value value);

    static Value deserializeValue(const std::string& data);

    static std::string serializeTags(const Tags& tags);

    static Tags deserializeTags(const std::string& data);

    static std::string makeDataPrefix(const TenantId& tenant,
                                      const Metric& metric,
                                      const Tags& tags);

    static std::string makeIndexKey(const TenantId& tenant,
                                    const Metric& metric,
                                    const std::string& tagKey,
                                    const std::string& tagValue,
                                    const std::string& seriesId);

    static std::string makeSeriesKey(const TenantId& tenant,
                                     const Metric& metric,
                                     const Tags& tags);

    static std::string generateSeriesId(const TenantId& tenant,
                                        const Metric& metric,
                                        const Tags& tags);
};

}
