/* ===========================================================
   BALAGERU RESTAURANT — API client
   Talks to the Flask + MySQL backend instead of localStorage.
   Set window.API_BASE in each HTML page before this script loads.
   =========================================================== */

const API_BASE = window.API_BASE || "http://localhost:5000";

const AUTH_TOKEN_KEY = "bg_token";
const AUTH_USER_KEY = "bg_user";

function getToken(){ return localStorage.getItem(AUTH_TOKEN_KEY); }
function getStoredUser(){
  try{ return JSON.parse(localStorage.getItem(AUTH_USER_KEY) || "null"); }
  catch(e){ return null; }
}
function setSession(token, user){
  localStorage.setItem(AUTH_TOKEN_KEY, token);
  localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user));
}
function clearSession(){
  localStorage.removeItem(AUTH_TOKEN_KEY);
  localStorage.removeItem(AUTH_USER_KEY);
}

/**
 * Core request helper. Throws an Error with a readable message on failure,
 * so callers can catch it and show a toast rather than dying silently.
 */
async function apiRequest(path, { method = "GET", body, auth = false } = {}){
  const headers = { "Content-Type": "application/json" };
  if(auth){
    const token = getToken();
    if(token) headers["Authorization"] = "Bearer " + token;
  }

  let res;
  try{
    res = await fetch(API_BASE + path, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  }catch(networkErr){
    throw new Error("Can't reach the server. Is the backend running at " + API_BASE + "?");
  }

  let data = null;
  try{ data = await res.json(); }catch(e){ /* empty body, fine for some responses */ }

  if(!res.ok){
    const message = (data && (data.error || data.msg)) || ("Request failed (" + res.status + ")");
    const err = new Error(message);
    err.status = res.status;
    throw err;
  }
  return data;
}

/* ---------- Auth ---------- */
const Api = {
  async login(username, password){
    const data = await apiRequest("/api/auth/login", { method: "POST", body: { username, password } });
    setSession(data.access_token, data.user);
    return data.user;
  },
  async registerFirstOwner(payload){
    return apiRequest("/api/auth/register", { method: "POST", body: payload });
  },
  async registerStaff(payload){
    return apiRequest("/api/auth/register", { method: "POST", body: payload, auth: true });
  },
  async me(){
    return apiRequest("/api/auth/me", { auth: true });
  },
  async staffList(){
    return apiRequest("/api/auth/staff", { auth: true });
  },
  logout(){ clearSession(); },

  /* ---------- Menu ---------- */
  async getMenu(){
    return apiRequest("/api/menu");
  },
  async createMenuItem(payload){
    return apiRequest("/api/menu/items", { method: "POST", body: payload, auth: true });
  },
  async updateMenuItem(id, payload){
    return apiRequest("/api/menu/items/" + id, { method: "PUT", body: payload, auth: true });
  },
  async toggleAvailability(id){
    return apiRequest("/api/menu/items/" + id + "/availability", { method: "PATCH", body: {}, auth: true });
  },
  async deleteMenuItem(id){
    return apiRequest("/api/menu/items/" + id, { method: "DELETE", auth: true });
  },

  /* ---------- Tables ---------- */
  async getTables(){
    return apiRequest("/api/tables", { auth: true });
  },
  async addTable(table_number, seats){
    return apiRequest("/api/tables", { method: "POST", body: { table_number, seats }, auth: true });
  },
  async removeTable(id){
    return apiRequest("/api/tables/" + id, { method: "DELETE", auth: true });
  },
  async resolveTable(token){
    return apiRequest("/api/tables/resolve/" + token);
  },

  /* ---------- Orders ---------- */
  async createOrder(payload){
    return apiRequest("/api/orders", { method: "POST", body: payload });
  },
  async getOrders(status){
    const qs = status ? ("?status=" + encodeURIComponent(status)) : "";
    return apiRequest("/api/orders" + qs, { auth: true });
  },
  async updateOrderStatus(id, status){
    return apiRequest("/api/orders/" + id + "/status", { method: "PATCH", body: { status }, auth: true });
  },
  async reportSummary(){
    return apiRequest("/api/orders/reports/summary", { auth: true });
  },
};

/* ---------- Small formatting helpers (unchanged from before) ---------- */
function fmtMoney(n){
  return "$" + Number(n).toFixed(2);
}
function timeAgo(isoOrMs){
  const ts = typeof isoOrMs === "number" ? isoOrMs : new Date(isoOrMs + "Z").getTime();
  const diff = Math.floor((Date.now() - ts) / 1000);
  if(diff < 60) return diff + "s ago";
  if(diff < 3600) return Math.floor(diff / 60) + "m ago";
  return Math.floor(diff / 3600) + "h ago";
}
