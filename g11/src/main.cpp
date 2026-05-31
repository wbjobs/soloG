#include <iostream>
#include <memory>
#include <thread>
#include <chrono>
#include <csignal>
#include <drogon/drogon.h>
#include "tsdb/config/config.h"
#include "tsdb/storage/rocksdb_engine.h"
#include "tsdb/index/tag_index.h"
#include "tsdb/downsampling/downsampler.h"
#include "tsdb/query/query_engine.h"
#include "tsdb/api/http_handler.h"
#include "tsdb/rollup/rollup_engine.h"

using namespace tsdb;

std::shared_ptr<downsampling::Downsampler> g_downsampler1m;
std::shared_ptr<downsampling::Downsampler> g_downsampler5m;
std::shared_ptr<downsampling::Downsampler> g_downsampler1h;
std::shared_ptr<rollup::RollupEngine> g_rollupEngine;

void signalHandler(int signal) {
    std::cout << "\nShutting down..." << std::endl;
    if (g_downsampler1m) g_downsampler1m->flush();
    if (g_downsampler5m) g_downsampler5m->flush();
    if (g_downsampler1h) g_downsampler1h->flush();
    if (g_rollupEngine) g_rollupEngine->flushAll();
    drogon::app().quit();
}

int main(int argc, char* argv[]) {
    try {
        auto& config = config::Config::instance();
        config.load(argc, argv);

        std::cout << "Initializing Time Series Database..." << std::endl;
        std::cout << "Data directory: " << config.dataDir() << std::endl;
        std::cout << "Auth enabled: " << (config.enableAuth() ? "yes" : "no") << std::endl;

        auto engine = std::make_shared<storage::RocksDBEngine>(config.dataDir());
        auto tagIndex = std::make_shared<index::TagIndex>(engine);
        
        g_downsampler1m = std::make_shared<downsampling::Downsampler>(engine, DownsampleInterval::MIN_1);
        g_downsampler5m = std::make_shared<downsampling::Downsampler>(engine, DownsampleInterval::MIN_5);
        g_downsampler1h = std::make_shared<downsampling::Downsampler>(engine, DownsampleInterval::HOUR_1);

        g_rollupEngine = std::make_shared<rollup::RollupEngine>(engine);

        auto queryEngine = std::make_shared<query::QueryEngine>(
            engine, tagIndex, g_downsampler1m, g_downsampler5m, g_downsampler1h);

        auto handler = std::make_shared<api::HttpHandler>(
            engine, queryEngine, tagIndex, g_downsampler1m, g_downsampler5m, g_downsampler1h, g_rollupEngine);

        std::thread flusher([]() {
            while (true) {
                std::this_thread::sleep_for(std::chrono::seconds(5));
                if (g_downsampler1m) g_downsampler1m->flush();
                if (g_downsampler5m) g_downsampler5m->flush();
                if (g_downsampler1h) g_downsampler1h->flush();
                if (g_rollupEngine) g_rollupEngine->flushAll();
            }
        });
        flusher.detach();

        signal(SIGINT, signalHandler);
#ifdef SIGTERM
        signal(SIGTERM, signalHandler);
#endif

        handler->registerRoutes(drogon::app());

        std::cout << "Starting HTTP server on " << config.host() << ":" << config.port() << std::endl;
        
        drogon::app()
            .setThreadNum(static_cast<int>(std::thread::hardware_concurrency()))
            .addListener(config.host(), config.port())
            .run();

    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }

    return 0;
}
