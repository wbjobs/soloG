#pragma once

#include <memory>
#include <string>
#include <map>
#include <set>
#include <mutex>
#include <drogon/drogon.h>
#include "../types.h"
#include "../auth/jwt_auth.h"

namespace tsdb::websocket {

struct Subscription {
    std::string subscriptionId;
    TenantId tenant;
    Metric metric;
    Tags tags;
    std::weak_ptr<drogon::WebSocketConnection> connection;
};

class DataSubscriptionManager {
public:
    static DataSubscriptionManager& instance();

    std::string subscribe(const TenantId& tenant,
                          const Metric& metric,
                          const Tags& tags,
                          std::shared_ptr<drogon::WebSocketConnection> connection);

    void unsubscribe(const std::string& subscriptionId);

    void onDataWritten(const TenantId& tenant,
                       const Metric& metric,
                       const Tags& tags,
                       Timestamp timestamp,
                       Value value);

    void handleNewConnection(std::shared_ptr<drogon::WebSocketConnection> connection);

    void handleMessage(std::shared_ptr<drogon::WebSocketConnection> connection,
                       const std::string& message);

    void handleClose(std::shared_ptr<drogon::WebSocketConnection> connection);

private:
    DataSubscriptionManager() = default;
    ~DataSubscriptionManager() = default;

    std::string generateId();

    mutable std::mutex mutex_;
    std::map<std::string, Subscription> subscriptions_;
    std::map<std::string, std::set<std::string>> connectionSubscriptions_;
    std::map<std::string, std::map<std::string, std::set<std::string>>> metricSubscriptions_;
};

}
