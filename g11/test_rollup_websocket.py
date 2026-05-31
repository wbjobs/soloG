#!/usr/bin/env python3
import requests
import time
import json
import threading
import websocket

BASE_URL = "http://localhost:8080"
WS_URL = "ws://localhost:8080/api/v1/ws/subscribe"

def login(tenant, username, password):
    payload = {
        "tenant": tenant,
        "username": username,
        "password": password
    }
    response = requests.post(f"{BASE_URL}/api/v1/login", json=payload)
    if response.status_code == 200:
        return response.json()["token"]
    return None

def test_rollup():
    print("\n" + "=" * 60)
    print("TEST 1: Rollup Pre-aggregation")
    print("=" * 60)
    
    token = login("tenant_a", "user_a", "password_a")
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n1. Creating rollup 'temp_factory_a_1m'...")
    rollup_config = {
        "name": "temp_factory_a_1m",
        "metric": "temperature",
        "tags": {"location": "factory_a"},
        "interval": "1m",
        "enabled": True
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/rollups", json=rollup_config, headers=headers)
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    
    print("\n2. Listing all rollups...")
    response = requests.get(f"{BASE_URL}/api/v1/rollups", headers=headers)
    print(f"   Status: {response.status_code}")
    rollups = response.json().get("rollups", [])
    for r in rollups:
        print(f"   - {r['name']}: {r['metric']} @ {r['interval']}")
    
    print("\n3. Writing 10 data points...")
    now = int(time.time() * 1000)
    for i in range(10):
        ts = now + i * 1000
        payload = {
            "tenant": "tenant_a",
            "metric": "temperature",
            "tags": {"device": f"sensor_{i%3}", "location": "factory_a"},
            "value": 20.0 + i * 0.5,
            "timestamp": ts
        }
        response = requests.post(f"{BASE_URL}/api/v1/write", json=payload, headers=headers)
        if i == 0:
            print(f"   First write: {response.status_code}")
    
    print("   Waiting for flush...")
    time.sleep(8)
    
    print("\n4. Querying rollup data...")
    query_payload = {
        "start": str(now - 60000),
        "end": str(now + 60000)
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/rollups/temp_factory_a_1m/query",
        json=query_payload,
        headers=headers
    )
    print(f"   Status: {response.status_code}")
    result = response.json()
    print(f"   Rollup points: {len(result.get('points', []))}")
    for p in result.get('points', []):
        print(f"   Time: {time.strftime('%H:%M:%S', time.localtime(p['timestamp']/1000))}")
        print(f"     avg={p['avg']:.2f}, max={p['max']:.2f}, min={p['min']:.2f}")
        print(f"     sum={p['sum']:.2f}, count={p['count']}")
    
    return token

def test_websocket(token):
    print("\n" + "=" * 60)
    print("TEST 2: WebSocket Real-time Subscription")
    print("=" * 60)
    
    received_messages = []
    ws_connected = threading.Event()
    
    def on_message(ws, message):
        data = json.loads(message)
        print(f"\n   ← Received: {data.get('type')}", end="")
        if data.get('type') == 'data':
            print(f" - {data['metric']}: {data['value']} @ {time.strftime('%H:%M:%S', time.localtime(data['timestamp']/1000))}")
        else:
            print(f" - {data}")
        received_messages.append(data)
    
    def on_open(ws):
        print("   WebSocket connected!")
        ws_connected.set()
        
        subscribe_msg = {
            "action": "subscribe",
            "token": token,
            "tenant": "tenant_a",
            "metric": "temperature",
            "tags": {"location": "factory_a"}
        }
        print(f"   → Sending subscribe: {subscribe_msg['metric']}")
        ws.send(json.dumps(subscribe_msg))
    
    def on_error(ws, error):
        print(f"   WebSocket error: {error}")
    
    def on_close(ws, close_status_code, close_msg):
        print(f"   WebSocket closed: {close_status_code}")
    
    print("\n1. Connecting to WebSocket...")
    ws = websocket.WebSocketApp(
        WS_URL,
        on_message=on_message,
        on_open=on_open,
        on_error=on_error,
        on_close=on_close
    )
    
    ws_thread = threading.Thread(target=ws.run_forever, daemon=True)
    ws_thread.start()
    
    print("   Waiting for connection...")
    time.sleep(2)
    
    print("\n2. Writing data points (should trigger WebSocket push)...")
    headers = {"Authorization": f"Bearer {token}"}
    now = int(time.time() * 1000)
    
    for i in range(5):
        payload = {
            "tenant": "tenant_a",
            "metric": "temperature",
            "tags": {"device": "sensor_ws", "location": "factory_a"},
            "value": 25.0 + i,
            "timestamp": now + i * 1000
        }
        response = requests.post(f"{BASE_URL}/api/v1/write", json=payload, headers=headers)
        print(f"   Wrote point {i+1}: {response.status_code}")
        time.sleep(0.5)
    
    print("\n3. Waiting for WebSocket messages...")
    time.sleep(2)
    
    print(f"\n   Total messages received: {len(received_messages)}")
    data_msgs = [m for m in received_messages if m.get('type') == 'data']
    print(f"   Data messages: {len(data_msgs)}")
    
    if len(data_msgs) > 0:
        print("   ✓ WebSocket real-time push is working!")
    else:
        print("   ⚠ No data messages received")
    
    print("\n4. Closing WebSocket...")
    ws.close()
    time.sleep(1)

def test_rollup_delete(token):
    print("\n" + "=" * 60)
    print("TEST 3: Rollup Deletion")
    print("=" * 60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n1. Deleting rollup 'temp_factory_a_1m'...")
    response = requests.delete(f"{BASE_URL}/api/v1/rollups/temp_factory_a_1m", headers=headers)
    print(f"   Status: {response.status_code}")
    
    print("\n2. Listing rollups after deletion...")
    response = requests.get(f"{BASE_URL}/api/v1/rollups", headers=headers)
    rollups = response.json().get("rollups", [])
    print(f"   Remaining rollups: {len(rollups)}")

def main():
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 12 + "ROLLUP & WEBSOCKET FEATURE TEST" + " " * 12 + "║")
    print("╚" + "=" * 58 + "╝")
    
    try:
        token = test_rollup()
        test_websocket(token)
        test_rollup_delete(token)
        
        print("\n" + "╔" + "=" * 58 + "╗")
        print("║" + " " * 20 + "ALL TESTS COMPLETED" + " " * 20 + "║")
        print("╚" + "=" * 58 + "╝")
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
