#pragma once

#include <rocksdb/db.h>
#include <rocksdb/options.h>
#include <rocksdb/slice.h>
#include <memory>
#include <string>
#include <vector>
#include "../types.h"

namespace tsdb::storage {

class RocksDBEngine {
public:
    explicit RocksDBEngine(const std::string& dataDir);
    ~RocksDBEngine();

    bool put(const std::string& key, const std::string& value);
    bool get(const std::string& key, std::string* value);
    bool remove(const std::string& key);

    void scanRange(const std::string& start,
                   const std::string& end,
                   std::function<bool(const std::string&, const std::string&)> callback);

    void scanPrefix(const std::string& prefix,
                    std::function<bool(const std::string&, const std::string&)> callback);

    bool writeBatch(const std::vector<std::pair<std::string, std::string>>& kvPairs);

    rocksdb::DB* getDB() { return db_.get(); }

private:
    std::unique_ptr<rocksdb::DB> db_;
    rocksdb::Options options_;
};

}
