#!/usr/bin/env python3
import requests
import time
import json

BASE_URL = "http://localhost:8080"

def write_data(tenant, metric, tags, value, timestamp=None):
    if timestamp is None:
        timestamp = int(time.time() * 1000)
    
    payload = {
        "tenant": tenant,
        "metric": metric,
        "tags": tags,
        "value": value,
        "timestamp": timestamp
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/write", json=payload)
    print(f"Write: {response.status_code} - {response.json()}")
    return response.json()

def query_data(tenant, metric, tags, start, end, aggregation="avg", downsample="raw"):
    payload = {
        "tenant": tenant,
        "metric": metric,
        "tags": tags,
        "start": str(start),
        "end": str(end),
        "aggregation": aggregation,
        "downsample": downsample
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/query", json=payload)
    print(f"Query: {response.status_code}")
    return response.json()

def query_raw(tenant, metric, tags, start, end):
    payload = {
        "tenant": tenant,
        "metric": metric,
        "tags": tags,
        "start": str(start),
        "end": str(end)
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/query_raw", json=payload)
    print(f"Query Raw: {response.status_code}")
    return response.json()

def main():
    tenant = "iot_tenant_001"
    metric = "temperature"
    tags = {"device": "sensor_001", "location": "factory_a"}
    
    print("=" * 60)
    print("Testing Time Series Database API")
    print("=" * 60)
    
    now = int(time.time() * 1000)
    
    print("\n1. Writing test data points...")
    for i in range(10):
        ts = now - (10 - i) * 1000
        value = 25.0 + i * 0.5
        write_data(tenant, metric, tags, value, ts)
        time.sleep(0.1)
    
    print("\n2. Querying raw data...")
    result = query_raw(tenant, metric, tags, now - 20000, now + 1000)
    print(f"Got {len(result.get('points', []))} raw points")
    for p in result.get('points', []):
        print(f"  {time.strftime('%H:%M:%S', time.localtime(p['timestamp']/1000))}: {p['value']}")
    
    print("\n3. Querying with 1min downsample and avg aggregation...")
    result = query_data(tenant, metric, tags, now - 20000, now + 1000, 
                       aggregation="avg", downsample="1m")
    print(f"Got {len(result.get('points', []))} aggregated points")
    for p in result.get('points', []):
        print(f"  {time.strftime('%H:%M:%S', time.localtime(p['timestamp']/1000))}: {p['value']:.2f}")
    
    print("\n4. Testing different aggregations...")
    for agg in ["avg", "max", "min", "sum", "count"]:
        result = query_data(tenant, metric, tags, now - 20000, now + 1000,
                           aggregation=agg, downsample="raw")
        val = result.get('points', [{}])[0].get('value', 0)
        print(f"  {agg}: {val:.2f}")
    
    print("\n5. Testing multi-tenant isolation...")
    tenant2 = "iot_tenant_002"
    write_data(tenant2, metric, {"device": "sensor_002"}, 30.0, now)
    
    result1 = query_raw(tenant, metric, tags, now - 1000, now + 1000)
    result2 = query_raw(tenant2, metric, {"device": "sensor_002"}, now - 1000, now + 1000)
    print(f"  Tenant 1 points: {len(result1.get('points', []))}")
    print(f"  Tenant 2 points: {len(result2.get('points', []))}")
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()
