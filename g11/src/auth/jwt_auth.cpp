#include "tsdb/auth/jwt_auth.h"
#include "tsdb/config/config.h"
#include <openssl/hmac.h>
#include <openssl/sha.h>
#include <json/json.h>
#include <sstream>
#include <chrono>
#include <cstring>

namespace tsdb::auth {

static std::string base64Encode(const unsigned char* data, size_t len) {
    static const char* table = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    std::string encoded;
    encoded.reserve(((len + 2) / 3) * 4);
    
    size_t i = 0;
    while (i < len) {
        unsigned char octet_a = i < len ? data[i++] : 0;
        unsigned char octet_b = i < len ? data[i++] : 0;
        unsigned char octet_c = i < len ? data[i++] : 0;
        
        uint32_t triple = (octet_a << 16) | (octet_b << 8) | octet_c;
        
        encoded.push_back(table[(triple >> 18) & 0x3F]);
        encoded.push_back(table[(triple >> 12) & 0x3F]);
        encoded.push_back(table[(triple >> 6) & 0x3F]);
        encoded.push_back(table[triple & 0x3F]);
    }
    
    if (len % 3 == 1) {
        encoded[encoded.size() - 1] = '=';
        encoded[encoded.size() - 2] = '=';
    } else if (len % 3 == 2) {
        encoded[encoded.size() - 1] = '=';
    }
    
    for (char& c : encoded) {
        if (c == '+') c = '-';
        else if (c == '/') c = '_';
    }
    
    return encoded;
}

static std::string base64UrlEncode(const std::string& input) {
    return base64Encode(reinterpret_cast<const unsigned char*>(input.data()), input.size());
}

static std::string hmacSha256(const std::string& key, const std::string& data) {
    unsigned char digest[SHA256_DIGEST_LENGTH];
    unsigned int digestLen = SHA256_DIGEST_LENGTH;
    
    HMAC(EVP_sha256(), key.c_str(), static_cast<int>(key.size()),
         reinterpret_cast<const unsigned char*>(data.c_str()), data.size(),
         digest, &digestLen);
    
    return base64Encode(digest, digestLen);
}

static std::string toJsonString(const Json::Value& value) {
    Json::StreamWriterBuilder writer;
    return Json::writeString(writer, value);
}

static Json::Value parseJson(const std::string& input) {
    std::string standard = input;
    for (char& c : standard) {
        if (c == '-') c = '+';
        else if (c == '_') c = '/';
    }
    while (standard.size() % 4 != 0) {
        standard += '=';
    }
    
    std::string decoded;
    decoded.reserve(standard.size() * 3 / 4);
    
    static const int table[256] = {
        -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
        -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
        -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,62,-1,-1,-1,63,
        52,53,54,55,56,57,58,59,60,61,-1,-1,-1,-1,-1,-1,
        -1,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,
        15,16,17,18,19,20,21,22,23,24,25,-1,-1,-1,-1,-1,
        -1,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,
        41,42,43,44,45,46,47,48,49,50,51,-1,-1,-1,-1,-1
    };
    
    uint32_t buffer = 0;
    int bitsCollected = 0;
    
    for (char c : standard) {
        if (c == '=') break;
        int val = table[static_cast<unsigned char>(c)];
        if (val < 0) continue;
        
        buffer = (buffer << 6) | val;
        bitsCollected += 6;
        
        if (bitsCollected >= 8) {
            bitsCollected -= 8;
            decoded.push_back(static_cast<char>((buffer >> bitsCollected) & 0xFF));
        }
    }
    
    Json::Value json;
    Json::CharReaderBuilder reader;
    std::istringstream iss(decoded);
    std::string errs;
    Json::parseFromStream(reader, iss, &json, &errs);
    return json;
}

std::optional<UserInfo> JwtAuth::validateToken(const std::string& token) {
    size_t dot1 = token.find('.');
    size_t dot2 = token.find('.', dot1 + 1);
    
    if (dot1 == std::string::npos || dot2 == std::string::npos) {
        return std::nullopt;
    }
    
    std::string headerB64 = token.substr(0, dot1);
    std::string payloadB64 = token.substr(dot1 + 1, dot2 - dot1 - 1);
    std::string signature = token.substr(dot2 + 1);
    
    std::string signingInput = headerB64 + "." + payloadB64;
    const std::string& secret = config::Config::instance().jwtSecret();
    std::string expectedSignature = hmacSha256(secret, signingInput);
    
    if (signature != expectedSignature) {
        return std::nullopt;
    }
    
    Json::Value payload = parseJson(payloadB64);
    
    if (payload.isMember("exp")) {
        int64_t exp = payload["exp"].asInt64();
        int64_t now = std::chrono::duration_cast<std::chrono::seconds>(
            std::chrono::system_clock::now().time_since_epoch()
        ).count();
        if (now > exp) {
            return std::nullopt;
        }
    }
    
    if (!payload.isMember("tenant") || !payload.isMember("sub")) {
        return std::nullopt;
    }
    
    UserInfo info;
    info.tenant = payload["tenant"].asString();
    info.userId = payload["sub"].asString();
    info.role = payload.get("role", "user").asString();
    
    return info;
}

std::string JwtAuth::generateToken(const TenantId& tenant,
                                   const std::string& userId,
                                   const std::string& role) {
    Json::Value header;
    header["alg"] = "HS256";
    header["typ"] = "JWT";
    
    Json::Value payload;
    payload["tenant"] = tenant;
    payload["sub"] = userId;
    payload["role"] = role;
    
    auto now = std::chrono::system_clock::now();
    int64_t iat = std::chrono::duration_cast<std::chrono::seconds>(
        now.time_since_epoch()
    ).count();
    int64_t exp = iat + config::Config::instance().jwtExpireHours() * 3600;
    
    payload["iat"] = Json::Int64(iat);
    payload["exp"] = Json::Int64(exp);
    
    std::string headerB64 = base64UrlEncode(toJsonString(header));
    std::string payloadB64 = base64UrlEncode(toJsonString(payload));
    std::string signingInput = headerB64 + "." + payloadB64;
    
    const std::string& secret = config::Config::instance().jwtSecret();
    std::string signature = hmacSha256(secret, signingInput);
    
    return signingInput + "." + signature;
}

drogon::HttpResponsePtr JwtAuth::makeUnauthorizedResponse(const std::string& message) {
    auto resp = drogon::HttpResponse::newHttpResponse();
    resp->setStatusCode(drogon::HttpStatusCode::k401Unauthorized);
    Json::Value json;
    json["error"] = message;
    Json::StreamWriterBuilder writer;
    resp->setBody(Json::writeString(writer, json));
    resp->setContentTypeCode(drogon::CT_APPLICATION_JSON);
    return resp;
}

std::optional<std::string> JwtAuth::extractTokenFromHeader(const drogon::HttpRequestPtr& req) {
    std::string authHeader = req->getHeader("Authorization");
    if (authHeader.empty()) {
        return std::nullopt;
    }
    
    if (authHeader.substr(0, 7) == "Bearer ") {
        return authHeader.substr(7);
    }
    
    return authHeader;
}

}
