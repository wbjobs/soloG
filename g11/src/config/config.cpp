#include "tsdb/config/config.h"
#include <iostream>
#include <cstdlib>

namespace tsdb::config {

Config& Config::instance() {
    static Config instance;
    return instance;
}

void Config::load(int argc, char* argv[]) {
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--data-dir" && i + 1 < argc) {
            dataDir_ = argv[++i];
        } else if (arg == "--port" && i + 1 < argc) {
            port_ = std::stoi(argv[++i]);
        } else if (arg == "--host" && i + 1 < argc) {
            host_ = argv[++i];
        } else if (arg == "--jwt-secret" && i + 1 < argc) {
            jwtSecret_ = argv[++i];
        } else if (arg == "--jwt-expire-hours" && i + 1 < argc) {
            jwtExpireHours_ = std::stoi(argv[++i]);
        } else if (arg == "--no-auth") {
            enableAuth_ = false;
        }
    }

    const char* envSecret = std::getenv("TSDB_JWT_SECRET");
    if (envSecret) {
        jwtSecret_ = envSecret;
    }

    if (enableAuth_ && jwtSecret_ == "tsdb_default_secret_key_change_in_production") {
        std::cout << "WARNING: Using default JWT secret! This is insecure in production." << std::endl;
        std::cout << "Set --jwt-secret or TSDB_JWT_SECRET environment variable." << std::endl;
    }
}

}
