#pragma once

#include "../types.h"
#include <string>

namespace tsdb::utils {

class TimeUtils {
public:
    static Timestamp alignToInterval(Timestamp ts, DownsampleInterval interval);

    static Timestamp parseTimeString(const std::string& timeStr);

    static std::string formatTime(Timestamp ts);

    static int64_t intervalSeconds(DownsampleInterval interval);
};

}
