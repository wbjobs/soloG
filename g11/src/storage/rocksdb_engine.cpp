#include "tsdb/storage/rocksdb_engine.h"
#include <rocksdb/write_batch.h>
#include <stdexcept>
#include <iostream>

namespace tsdb::storage {

RocksDBEngine::RocksDBEngine(const std::string& dataDir) {
    options_.create_if_missing = true;
    options_.error_if_exists = false;
    options_.increase_parallelism(std::thread::hardware_concurrency());
    options_.OptimizeLevelStyleCompaction();

    rocksdb::DB* db = nullptr;
    rocksdb::Status status = rocksdb::DB::Open(options_, dataDir, &db);
    if (!status.ok()) {
        throw std::runtime_error("Failed to open RocksDB: " + status.ToString());
    }
    db_.reset(db);
}

RocksDBEngine::~RocksDBEngine() {
    if (db_) {
        db_.reset();
    }
}

bool RocksDBEngine::put(const std::string& key, const std::string& value) {
    rocksdb::Status s = db_->Put(rocksdb::WriteOptions(), key, value);
    return s.ok();
}

bool RocksDBEngine::get(const std::string& key, std::string* value) {
    rocksdb::Status s = db_->Get(rocksdb::ReadOptions(), key, value);
    return s.ok();
}

bool RocksDBEngine::remove(const std::string& key) {
    rocksdb::Status s = db_->Delete(rocksdb::WriteOptions(), key);
    return s.ok();
}

void RocksDBEngine::scanRange(const std::string& start,
                              const std::string& end,
                              std::function<bool(const std::string&, const std::string&)> callback) {
    rocksdb::ReadOptions options;
    std::unique_ptr<rocksdb::Iterator> it(db_->NewIterator(options));
    
    for (it->Seek(start); it->Valid() && it->key().ToString() < end; it->Next()) {
        if (!callback(it->key().ToString(), it->value().ToString())) {
            break;
        }
    }
}

void RocksDBEngine::scanPrefix(const std::string& prefix,
                               std::function<bool(const std::string&, const std::string&)> callback) {
    std::string end = prefix;
    if (!end.empty()) {
        end.back() += 1;
    }
    scanRange(prefix, end, callback);
}

bool RocksDBEngine::writeBatch(const std::vector<std::pair<std::string, std::string>>& kvPairs) {
    rocksdb::WriteBatch batch;
    for (const auto& [k, v] : kvPairs) {
        batch.Put(k, v);
    }
    rocksdb::Status s = db_->Write(rocksdb::WriteOptions(), &batch);
    return s.ok();
}

}
