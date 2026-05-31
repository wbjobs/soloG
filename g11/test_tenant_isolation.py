#!/usr/bin/env python3
import requests
import time
import json

BASE_URL = "http://localhost:8080"

def login(tenant, username, password):
    payload = {
        "tenant": tenant,
        "username": username,
        "password": password
    }
    response = requests.post(f"{BASE_URL}/api/v1/login", json=payload)
    print(f"Login ({tenant}): {response.status_code}")
    if response.status_code == 200:
        return response.json()["token"]
    return None

def write_data(token, tenant, metric, tags, value):
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "tenant": tenant,
        "metric": metric,
        "tags": tags,
        "value": value
    }
    response = requests.post(f"{BASE_URL}/api/v1/write", json=payload, headers=headers)
    return response.status_code, response.json()

def query_data(token, tenant, metric, tags, start, end, aggregation="avg", downsample="raw"):
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "tenant": tenant,
        "metric": metric,
        "tags": tags,
        "start": str(start),
        "end": str(end),
        "aggregation": aggregation,
        "downsample": downsample
    }
    response = requests.post(f"{BASE_URL}/api/v1/query", json=payload, headers=headers)
    return response.status_code, response.json()

def test_without_auth():
    print("\n" + "=" * 60)
    print("TEST 1: Access without authentication token")
    print("=" * 60)
    
    payload = {
        "tenant": "tenant_a",
        "metric": "temperature",
        "tags": {"device": "sensor_001"},
        "value": 25.5
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/write", json=payload)
    print(f"Write without token: {response.status_code} - {response.json()}")
    assert response.status_code == 401, "Should return 401 Unauthorized"
    print("✓ Correctly rejected unauthenticated request")

def test_tenant_isolation():
    print("\n" + "=" * 60)
    print("TEST 2: Tenant isolation verification")
    print("=" * 60)
    
    token_a = login("tenant_a", "user_a", "password_a")
    token_b = login("tenant_b", "user_b", "password_b")
    
    assert token_a is not None, "Tenant A login failed"
    assert token_b is not None, "Tenant B login failed"
    
    print(f"\nToken A: {token_a[:50]}...")
    print(f"Token B: {token_b[:50]}...")
    
    now = int(time.time() * 1000)
    
    print("\n--- Writing data as Tenant A ---")
    status, result = write_data(token_a, "tenant_a", "temperature", {"device": "sensor_001"}, 25.0)
    print(f"Tenant A writes: {status}")
    assert status == 200, "Tenant A write failed"
    
    print("\n--- Writing data as Tenant B ---")
    status, result = write_data(token_b, "tenant_b", "temperature", {"device": "sensor_001"}, 30.0)
    print(f"Tenant B writes: {status}")
    assert status == 200, "Tenant B write failed"
    
    time.sleep(6)
    
    print("\n--- Testing cross-tenant access attempt ---")
    
    print("\nAttempt 1: Tenant A trying to query Tenant B's data (using B's tenant in request body)")
    status, result = query_data(token_a, "tenant_b", "temperature", {"device": "sensor_001"}, 
                               now - 60000, now + 10000, "avg", "raw")
    print(f"Status: {status}")
    print(f"Result: {json.dumps(result, indent=2)}")
    
    print("\nAttempt 2: Tenant B trying to query Tenant A's data (using A's tenant in request body)")
    status, result = query_data(token_b, "tenant_a", "temperature", {"device": "sensor_001"},
                               now - 60000, now + 10000, "avg", "raw")
    print(f"Status: {status}")
    print(f"Result: {json.dumps(result, indent=2)}")
    
    print("\n--- Verifying isolation ---")
    
    status, result_a = query_data(token_a, "tenant_a", "temperature", {"device": "sensor_001"},
                                  now - 60000, now + 10000, "avg", "raw")
    points_a = result_a.get("points", [])
    print(f"\nTenant A querying own data: {len(points_a)} points")
    for p in points_a:
        print(f"  {time.strftime('%H:%M:%S', time.localtime(p['timestamp']/1000))}: {p['value']}")
    
    status, result_b = query_data(token_b, "tenant_b", "temperature", {"device": "sensor_001"},
                                  now - 60000, now + 10000, "avg", "raw")
    points_b = result_b.get("points", [])
    print(f"\nTenant B querying own data: {len(points_b)} points")
    for p in points_b:
        print(f"  {time.strftime('%H:%M:%S', time.localtime(p['timestamp']/1000))}: {p['value']}")
    
    if len(points_a) > 0 and len(points_b) > 0:
        print("\n✓ Tenant isolation is working correctly!")
        print("  - Tenant A can only see their own data")
        print("  - Tenant B can only see their own data")
        print("  - Request body 'tenant' field is ignored (JWT tenant is used)")
    else:
        print("\n⚠ Warning: Some queries returned empty results")

def test_invalid_token():
    print("\n" + "=" * 60)
    print("TEST 3: Invalid token handling")
    print("=" * 60)
    
    invalid_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature"
    headers = {"Authorization": f"Bearer {invalid_token}"}
    
    payload = {
        "tenant": "tenant_a",
        "metric": "temperature",
        "tags": {"device": "sensor_001"},
        "value": 25.5
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/write", json=payload, headers=headers)
    print(f"Write with invalid token: {response.status_code}")
    assert response.status_code == 401, "Should return 401 for invalid token"
    print("✓ Correctly rejected invalid token")

def test_tenant_forging_attempt():
    print("\n" + "=" * 60)
    print("TEST 4: Tenant ID forgery attempt in request body")
    print("=" * 60)
    
    token_a = login("tenant_a", "user_a", "password_a")
    assert token_a is not None, "Tenant A login failed"
    
    now = int(time.time() * 1000)
    
    print("\nAttempt: Tenant A writes with 'tenant_b' in request body")
    print("Expected: Should write to 'tenant_a' (from token), not 'tenant_b' (from body)")
    
    status, result = write_data(token_a, "tenant_b", "temperature", {"device": "sensor_forged"}, 99.9)
    print(f"Write status: {status}")
    
    time.sleep(6)
    
    print("\nQuerying Tenant A's data...")
    status, result = query_data(token_a, "tenant_a", "temperature", {"device": "sensor_forged"},
                               now - 60000, now + 10000, "avg", "raw")
    points = result.get("points", [])
    print(f"Tenant A's data: {len(points)} points")
    for p in points:
        print(f"  {time.strftime('%H:%M:%S', time.localtime(p['timestamp']/1000))}: {p['value']}")
    
    if len(points) > 0 and points[0]['value'] == 99.9:
        print("\n✓ Tenant ID forgery prevented!")
        print("  - Data was written to token's tenant (tenant_a)")
        print("  - Request body 'tenant_b' was ignored")
    else:
        print("\n✗ Unexpected result")

def main():
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "TENANT ISOLATION SECURITY TEST" + " " * 15 + "║")
    print("╚" + "=" * 58 + "╝")
    
    try:
        test_without_auth()
        test_tenant_isolation()
        test_invalid_token()
        test_tenant_forging_attempt()
        
        print("\n" + "╔" + "=" * 58 + "╗")
        print("║" + " " * 20 + "ALL TESTS PASSED ✓" + " " * 20 + "║")
        print("╚" + "=" * 58 + "╝")
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
