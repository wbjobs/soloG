#pragma once

#include <string>
#include <memory>

namespace tsdb::config {

class Config {
public:
    static Config& instance();

    void load(int argc, char* argv[]);

    const std::string& dataDir() const { return dataDir_; }
    const std::string& host() const { return host_; }
    int port() const { return port_; }
    const std::string& jwtSecret() const { return jwtSecret_; }
    int jwtExpireHours() const { return jwtExpireHours_; }
    bool enableAuth() const { return enableAuth_; }

private:
    Config() = default;
    ~Config() = default;

    std::string dataDir_ = "./tsdb_data";
    std::string host_ = "0.0.0.0";
    int port_ = 8080;
    std::string jwtSecret_ = "tsdb_default_secret_key_change_in_production";
    int jwtExpireHours_ = 24;
    bool enableAuth_ = true;
};

}
