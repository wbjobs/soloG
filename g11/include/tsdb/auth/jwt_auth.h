#pragma once

#include <string>
#include <optional>
#include <drogon/drogon.h>
#include "../types.h"

namespace tsdb::auth {

struct UserInfo {
    TenantId tenant;
    std::string userId;
    std::string role;
};

class JwtAuth {
public:
    static std::optional<UserInfo> validateToken(const std::string& token);

    static std::string generateToken(const TenantId& tenant,
                                     const std::string& userId,
                                     const std::string& role);

    static drogon::HttpResponsePtr makeUnauthorizedResponse(const std::string& message);

    static std::optional<std::string> extractTokenFromHeader(const drogon::HttpRequestPtr& req);
};

}
