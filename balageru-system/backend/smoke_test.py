import os
os.environ["DATA_DIR"] = "./test_data"
os.environ["JWT_SECRET_KEY"] = "test-secret"

from app import create_app

app = create_app()
client = app.test_client()

def show(label, resp):
    print(f"\n--- {label} [{resp.status_code}] ---")
    print(resp.get_json())
    return resp.get_json()

# 1. Public: browse menu
r = client.get("/api/menu")
menu = show("GET /api/menu", r)
assert r.status_code == 200 and len(menu) == 27

# 2. Register bootstrap owner (first user -> auto owner)
r = client.post("/api/auth/register", json={
    "full_name": "Tefera Alemu", "username": "owner1",
    "password": "supersecret123", "email": "owner@balageru.com"
})
show("POST /api/auth/register (bootstrap owner)", r)
assert r.status_code == 201

# 3. Login
r = client.post("/api/auth/login", json={"username": "owner1", "password": "supersecret123"})
data = show("POST /api/auth/login", r)
assert r.status_code == 200
token = data["access_token"]
auth_header = {"Authorization": f"Bearer {token}"}

# 4. Staff creates a second staff account (waiter)
r = client.post("/api/auth/register", json={
    "full_name": "Sara Bekele", "username": "waiter1",
    "password": "waiterpass123", "role": "waiter"
}, headers=auth_header)
show("POST /api/auth/register (waiter, by owner)", r)
assert r.status_code == 201

# 5. Public: place a dine-in order for table 3
r = client.post("/api/orders", json={
    "mode": "dine_in",
    "table_number": 3,
    "customer_name": "Walk-in guest",
    "items": [
        {"menu_item_id": 4, "quantity": 2},   # Doro Wat
        {"menu_item_id": 24, "quantity": 2},  # Buna
    ]
})
order = show("POST /api/orders (customer, table 3)", r)
assert r.status_code == 201
assert order["status"] == "new"
assert order["total"] > 0
order_id = order["id"]

# 6. Staff: view order board
r = client.get("/api/orders", headers=auth_header)
orders = show("GET /api/orders (staff board)", r)
assert r.status_code == 200 and len(orders) == 1

# 7. Staff: advance order status
r = client.patch(f"/api/orders/{order_id}/status", json={"status": "preparing"}, headers=auth_header)
show("PATCH /api/orders/<id>/status -> preparing", r)
assert r.status_code == 200

# 8. Unauthenticated attempt to view orders should fail
r = client.get("/api/orders")
show("GET /api/orders (no auth, expect 401)", r)
assert r.status_code == 401

# 9. Reports summary
r = client.get("/api/orders/reports/summary", headers=auth_header)
show("GET /api/orders/reports/summary", r)
assert r.status_code == 200

# 10. QR resolve
r = client.get("/api/tables", headers=auth_header)
tables = show("GET /api/tables", r)
token_for_t1 = next(t["qr_token"] for t in tables if t["table_number"] == 1)
r = client.get(f"/api/tables/resolve/{token_for_t1}")
show("GET /api/tables/resolve/<token>", r)
assert r.status_code == 200

# 11. Data actually persisted to JSON files on disk
import json
with open("test_data/orders.json") as f:
    saved_orders = json.load(f)
assert len(saved_orders) == 1
assert saved_orders[0]["order_number"] == order["order_number"]
print("\n--- Verified orders.json on disk contains the order ---")

print("\n\n✅ ALL SMOKE TESTS PASSED (JSON file storage)")
