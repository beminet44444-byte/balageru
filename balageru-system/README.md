# Balageru Restaurant — Restaurant Management System

**Phase 1: a real Flask backend with JWT authentication, storing data in
plain JSON files instead of a database.** The customer site and staff
dashboard design is unchanged — they're wired to a real API so orders, menu
changes, and staff accounts are shared across every device, not stuck in one
browser's storage. There's no database server to install: the "database" is
just a handful of human-readable `.json` files.

```
balageru-system/
├── frontend/         customer site + staff dashboard (HTML/CSS/JS, unchanged design)
├── backend/           Flask REST API, JSON file storage
└── docker-compose.yml one-command local/production-style stack
```

---

## Why JSON files instead of a database

- **Nothing to install.** No MySQL/Postgres server, no connection strings to
  get right, no separate service to keep running.
- **Human-readable and inspectable.** Open `backend/data/orders.json` in any
  text editor and read exactly what's there.
- **Easy to back up.** The entire restaurant's data is a folder you can zip,
  copy, or version — no `mysqldump` needed.
- **The tradeoff, honestly:** this is the right choice for a single small
  restaurant on modest traffic. It is not built for high concurrency or
  multiple servers. See **"When to graduate to a real database"** below for
  exactly where that line is and what changes when you cross it.

## How it works

Each "table" is a JSON file holding a list of records:

```
backend/data/
├── users.json         staff accounts (bcrypt-hashed passwords)
├── categories.json     menu category order
├── menu_items.json     the menu
├── tables.json          dine-in tables + QR tokens
├── orders.json          every order, with items embedded directly
└── counters.json        auto-incrementing IDs
```

Every write goes through `backend/storage/__init__.py`, which:
- Takes an **OS-level exclusive lock** (`fcntl.flock`) before any read-modify-write,
  so two requests can't corrupt a file by writing at the same time — this works
  across threads *and* across separate processes (e.g. multiple gunicorn workers),
  not just within one.
- Writes to a temp file and renames it into place, so a crash mid-write never
  leaves a half-written JSON file behind.
- Orders store their line items **embedded directly** in the order record
  (no separate "order_items" file to join) — a natural fit for JSON, and it
  means an order's data is self-contained even if the menu changes later.

## What's implemented in this phase

- **Authentication** — JWT-based staff login, bcrypt password hashing, role-based
  access control (`owner`, `manager`, `cashier`, `chef`, `waiter`, `driver`, `accountant`).
- **Menu API** — public browse endpoints for the customer site; protected
  create/edit/delete/availability-toggle endpoints for managers and owners.
- **Orders API** — customers place orders with no login required; staff see a
  live order board and move orders through New → Preparing → Ready → Completed.
- **Tables & secure QR ordering** — each table gets an opaque QR token (not a
  guessable number). Scanning it resolves server-side to the real table.
- **Reports** — total orders, revenue, average order value, best sellers.
- **Docker** — `docker-compose.yml` runs the API + the static frontend behind
  nginx with one command; a Docker volume keeps the JSON data across restarts.

## What's *not* in this phase yet (see Roadmap below)

Kitchen Display System, Cashier POS, payments (Chapa/Telebirr/CBE Birr/Stripe/PayPal),
inventory, delivery/GPS tracking, customer accounts/loyalty, SMS/push notifications,
and a full analytics/export dashboard are **not built yet** — deferred so this
phase could be a real, tested foundation rather than dozens of half-finished files.

---

## Running it locally (fastest: Docker)

Requires Docker and Docker Compose.

```bash
cd balageru-system
docker compose up -d --build

# first run only: creates backend/data/*.json and loads the 27-item menu + 8 tables
docker compose exec backend python seed.py
```

- Customer site: http://localhost:8080
- Staff dashboard: http://localhost:8080/admin.html
- API: http://localhost:5000/api/health

On the staff dashboard, click **"Create the owner account →"** the first time
(the very first account created is automatically the owner).

## Running it without Docker

```bash
cd backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: set JWT_SECRET_KEY to a long random string, e.g.
#   python -c "import secrets; print(secrets.token_hex(32))"

python seed.py                    # creates backend/data/*.json + loads the menu
python app.py                     # runs on http://localhost:5000
```

For production, don't use `python app.py` (Flask's dev server) — use gunicorn,
which is what the included `Dockerfile` does.

The frontend is static — no build step:

```bash
cd frontend
python3 -m http.server 8080
```

If frontend and backend are deployed to different hosts, update
`window.API_BASE` at the top of `<head>` in both `index.html` and
`admin.html` to point at your backend's real URL.

## Backing up and inspecting data

```bash
# Back up everything
cp -r backend/data backend/data-backup-$(date +%F)

# Look at today's orders directly
cat backend/data/orders.json | python3 -m json.tool
```

---

## When to graduate to a real database

JSON files are genuinely fine for one restaurant location running on one
server. Move to a real database (PostgreSQL/MySQL) when any of these becomes
true:

- You're running **more than one backend server** (JSON files on one disk
  aren't shared across machines).
- Order volume gets high enough that the single global file lock becomes a
  bottleneck (unlikely for one restaurant's foot traffic, but real at
  multi-location scale).
- You need proper relational queries/reporting across large history (JSON
  files are fine for hundreds to low thousands of orders; scanning a huge
  file for every report gets slow eventually).
- You need transactions spanning multiple related writes with rollback.

Because every route already goes through the small `storage` module
(`get_all`, `get_by_id`, `insert`, `update`, `delete`, `find`, `find_one`,
`next_id`), swapping in a real database later means rewriting that one file
— the route logic in `backend/routes/*.py` stays the same.

## Architecture notes

- **Auth**: JWT access tokens (8-hour expiry), bcrypt password hashing
  (12 rounds), role-based route protection via `@roles_required(...)` in
  `backend/middleware/auth_middleware.py`.
- **QR security**: table QR codes encode a random opaque token
  (`secrets.token_urlsafe(12)`), resolved server-side via
  `GET /api/tables/resolve/<token>`. The customer site never trusts a raw
  table number from the URL.
- **Order pricing**: tax is calculated server-side (`TAX_RATE` in
  `backend/routes/order_routes.py`, currently 15%) so a tampered client
  request can't under-report the total.
- **Menu snapshots**: each order item stores its name and price *at the time
  of the order*, so changing a menu price later doesn't rewrite historical
  order totals.
- **Polling, not push (yet)**: the staff order board refreshes every 6 seconds
  via polling. Phase 2 adds Flask-SocketIO for instant push updates.

## API reference (unchanged from the database version — same contract)

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/api/health` | none | health check |
| POST | `/api/auth/register` | none (bootstrap) / owner+manager after | create a staff account |
| POST | `/api/auth/login` | none | staff login → JWT |
| GET | `/api/auth/me` | any staff | current user |
| GET | `/api/auth/staff` | owner/manager | list staff |
| GET | `/api/menu` | none | browse menu |
| GET | `/api/menu/categories` | none | list categories |
| POST | `/api/menu/items` | owner/manager | create menu item |
| PUT | `/api/menu/items/<id>` | owner/manager | edit menu item |
| PATCH | `/api/menu/items/<id>/availability` | owner/manager/chef | toggle sold-out |
| DELETE | `/api/menu/items/<id>` | owner/manager | delete menu item |
| GET | `/api/tables` | any staff | list tables + QR tokens |
| POST | `/api/tables` | owner/manager | add a table |
| DELETE | `/api/tables/<id>` | owner/manager | remove a table |
| PATCH | `/api/tables/<id>/status` | owner/manager/waiter | available/occupied/reserved/cleaning |
| GET | `/api/tables/resolve/<qr_token>` | none | resolve a scanned QR code |
| POST | `/api/orders` | none | place an order (customer) |
| GET | `/api/orders` | any staff | order board (`?status=new` optional) |
| GET | `/api/orders/<id>` | any staff | single order |
| PATCH | `/api/orders/<id>/status` | owner/manager/chef/waiter/cashier | advance/cancel an order |
| GET | `/api/orders/reports/summary` | owner/manager/accountant | sales summary + best sellers |

Because the API contract didn't change, **the frontend needed zero changes**
when switching from MySQL to JSON files — only `backend/storage/__init__.py`
and the route internals changed.

---

## Roadmap (the rest of the ERP)

- **Phase 2 — Live operations**: Flask-SocketIO realtime order push, Kitchen
  Display System (queues, timers, alarms, color coding, fullscreen mode).
- **Phase 3 — Money**: Cashier POS, one payment gateway wired end-to-end first
  (Chapa/Telebirr/CBE Birr are the realistic priority for an Ethiopian
  restaurant), coupons, invoices/receipt PDFs.
- **Phase 4 — Back office**: inventory & auto stock deduction, employee
  roles/permissions/attendance/payroll, a real analytics dashboard.
- **Phase 5 — Growth**: customer accounts, favorites, reviews & ratings,
  loyalty points, delivery tracking with maps, notifications.
- **Phase 6 — Hardening & ship**: CSRF protection, rate limiting, audit logs,
  session timeout policy, PWA/offline support.

Tell me which phase to build next.
