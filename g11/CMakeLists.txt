cmake_minimum_required(VERSION 3.14)
project(TimeSeriesDB VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)

find_package(Drogon REQUIRED)
find_package(RocksDB REQUIRED)
find_package(Eigen3 REQUIRED)
find_package(PkgConfig REQUIRED)
find_package(OpenSSL REQUIRED)
pkg_check_modules(JSONCPP REQUIRED jsoncpp)

include_directories(
    ${CMAKE_SOURCE_DIR}/include
    ${Drogon_INCLUDE_DIRS}
    ${RocksDB_INCLUDE_DIRS}
    ${EIGEN3_INCLUDE_DIR}
    ${JSONCPP_INCLUDE_DIRS}
    ${OPENSSL_INCLUDE_DIR}
)

set(SOURCES
    src/main.cpp
    src/storage/rocksdb_engine.cpp
    src/index/tag_index.cpp
    src/downsampling/downsampler.cpp
    src/query/query_engine.cpp
    src/api/http_handler.cpp
    src/utils/serializer.cpp
    src/utils/time_utils.cpp
    src/config/config.cpp
    src/auth/jwt_auth.cpp
    src/rollup/rollup_engine.cpp
    src/websocket/data_subscription.cpp
)

add_executable(tsdb ${SOURCES})

target_link_libraries(tsdb
    Drogon::Drogon
    RocksDB::rocksdb
    Eigen3::Eigen
    ${JSONCPP_LIBRARIES}
    OpenSSL::SSL
    OpenSSL::Crypto
)
