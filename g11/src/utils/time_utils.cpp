#include "tsdb/utils/time_utils.h"
#include <sstream>
#include <iomanip>
#include <ctime>
#include <stdexcept>

namespace tsdb::utils {

Timestamp TimeUtils::alignToInterval(Timestamp ts, DownsampleInterval interval) {
    int64_t seconds = intervalSeconds(interval);
    if (seconds <= 0) return ts;
    int64_t ts_sec = ts / 1000;
    int64_t aligned = (ts_sec / seconds) * seconds;
    return aligned * 1000;
}

Timestamp TimeUtils::parseTimeString(const std::string& timeStr) {
    if (timeStr.empty()) {
        throw std::invalid_argument("Empty time string");
    }

    size_t pos;
    long long num = std::stoll(timeStr, &pos);
    if (pos == timeStr.size()) {
        return num;
    }

    std::tm tm = {};
    std::istringstream iss(timeStr);
    iss >> std::get_time(&tm, "%Y-%m-%dT%H:%M:%S");
    if (iss.fail()) {
        iss.clear();
        iss.seekg(0);
        iss >> std::get_time(&tm, "%Y-%m-%d %H:%M:%S");
    }
    if (!iss.fail()) {
        std::time_t t = std::mktime(&tm);
        return static_cast<Timestamp>(t) * 1000;
    }

    throw std::invalid_argument("Cannot parse time: " + timeStr);
}

std::string TimeUtils::formatTime(Timestamp ts) {
    std::time_t t = static_cast<std::time_t>(ts / 1000);
    std::tm tm;
#ifdef _WIN32
    localtime_s(&tm, &t);
#else
    localtime_r(&t, &tm);
#endif
    std::ostringstream oss;
    oss << std::put_time(&tm, "%Y-%m-%dT%H:%M:%S");
    return oss.str();
}

int64_t TimeUtils::intervalSeconds(DownsampleInterval interval) {
    return static_cast<int64_t>(interval);
}

}
