#include "tsdb/utils/serializer.h"
#include <sstream>
#include <functional>

namespace tsdb::utils {

std::string Serializer::serializeKey(const TenantId& tenant,
                                     const Metric& metric,
                                     const Tags& tags,
                                     Timestamp timestamp) {
    std::string result;
    result.reserve(tenant.size() + metric.size() + 16 + tags.size() * 16);
    
    result += tenant;
    result += '\0';
    result += metric;
    result += '\0';
    result += serializeTags(tags);
    result += '\0';
    
    uint64_t ts = static_cast<uint64_t>(timestamp);
    for (int i = 7; i >= 0; --i) {
        result += static_cast<char>((ts >> (i * 8)) & 0xFF);
    }
    
    return result;
}

std::string Serializer::serializeValue(Value value) {
    std::string result(sizeof(Value), '\0');
    std::memcpy(result.data(), &value, sizeof(Value));
    return result;
}

Value Serializer::deserializeValue(const std::string& data) {
    Value value;
    std::memcpy(&value, data.data(), sizeof(Value));
    return value;
}

std::string Serializer::serializeTags(const Tags& tags) {
    std::ostringstream oss;
    bool first = true;
    for (const auto& [k, v] : tags) {
        if (!first) oss << ',';
        oss << k << '=' << v;
        first = false;
    }
    return oss.str();
}

Tags Serializer::deserializeTags(const std::string& data) {
    Tags tags;
    std::istringstream iss(data);
    std::string pair;
    while (std::getline(iss, pair, ',')) {
        auto pos = pair.find('=');
        if (pos != std::string::npos) {
            tags[pair.substr(0, pos)] = pair.substr(pos + 1);
        }
    }
    return tags;
}

std::string Serializer::makeDataPrefix(const TenantId& tenant,
                                       const Metric& metric,
                                       const Tags& tags) {
    std::string result;
    result += tenant;
    result += '\0';
    result += metric;
    result += '\0';
    result += serializeTags(tags);
    result += '\0';
    return result;
}

std::string Serializer::makeIndexKey(const TenantId& tenant,
                                     const Metric& metric,
                                     const std::string& tagKey,
                                     const std::string& tagValue,
                                     const std::string& seriesId) {
    std::string result;
    result += "idx\0";
    result += tenant;
    result += '\0';
    result += metric;
    result += '\0';
    result += tagKey;
    result += '\0';
    result += tagValue;
    result += '\0';
    result += seriesId;
    return result;
}

std::string Serializer::makeSeriesKey(const TenantId& tenant,
                                      const Metric& metric,
                                      const Tags& tags) {
    std::string result;
    result += "series\0";
    result += tenant;
    result += '\0';
    result += metric;
    result += '\0';
    result += serializeTags(tags);
    return result;
}

std::string Serializer::generateSeriesId(const TenantId& tenant,
                                         const Metric& metric,
                                         const Tags& tags) {
    std::string key = makeSeriesKey(tenant, metric, tags);
    std::hash<std::string> hasher;
    return std::to_string(hasher(key));
}

}
