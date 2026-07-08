/* ===========================================================
   BALAGERU RESTAURANT — admin dashboard logic
   Real JWT auth + Flask API (see js/api.js) instead of a demo
   client-side password check.
   =========================================================== */

const STATUS_FLOW = ['new','preparing','ready','completed'];
const STATUS_LABEL = {new:'New', preparing:'Preparing', ready:'Ready', completed:'Completed'};

let currentUser = null;
let ordersPollTimer = null;

/* ---------- Auth ---------- */
async function tryLogin(){
  const username = document.getElementById('gateUser').value.trim();
  const password = document.getElementById('gatePass').value;
  const errEl = document.getElementById('gateError');
  errEl.style.display = 'none';

  if(!username || !password){
    errEl.textContent = 'Enter a username and password.';
    errEl.style.display = 'block';
    return;
  }

  try{
    currentUser = await Api.login(username, password);
    enterDashboard();
  }catch(e){
    errEl.textContent = e.message || 'Incorrect username or password.';
    errEl.style.display = 'block';
  }
}

async function tryFirstTimeSetup(){
  // Bootstraps the very first owner account when no staff exist yet.
  const full_name = document.getElementById('setupName').value.trim();
  const username = document.getElementById('setupUser').value.trim();
  const password = document.getElementById('setupPass').value;
  const errEl = document.getElementById('setupError');
  errEl.style.display = 'none';

  if(!full_name || !username || password.length < 8){
    errEl.textContent = 'Full name, username, and an 8+ character password are required.';
    errEl.style.display = 'block';
    return;
  }

  try{
    await Api.registerFirstOwner({ full_name, username, password });
    currentUser = await Api.login(username, password);
    enterDashboard();
  }catch(e){
    errEl.textContent = e.message;
    errEl.style.display = 'block';
  }
}

function logout(){
  Api.logout();
  clearInterval(ordersPollTimer);
  location.reload();
}

async function enterDashboard(){
  document.getElementById('gate').classList.add('hidden');
  document.getElementById('setupGate').classList.add('hidden');
  document.getElementById('shell').classList.remove('hidden');
  document.getElementById('whoami').textContent = currentUser.full_name + ' · ' + currentUser.role;
  applyRolePermissions();
  await renderOrders();
  await renderMenuManager();
  await renderTables();
  ordersPollTimer = setInterval(()=>{
    if(document.getElementById('panel-orders').classList.contains('active')) renderOrders();
  }, 6000);
}

function applyRolePermissions(){
  // Menu & Tables management are restricted server-side too (403 if attempted);
  // hide the entry points for roles that can't use them, for a cleaner UI.
  const canManage = ['owner','manager'].includes(currentUser.role);
  document.querySelectorAll('[data-requires="manager"]').forEach(el=>{
    el.style.display = canManage ? '' : 'none';
  });
}

window.addEventListener('DOMContentLoaded', async ()=>{
  document.getElementById('gatePass').addEventListener('keydown', e=>{ if(e.key==='Enter') tryLogin(); });
  document.getElementById('setupPass').addEventListener('keydown', e=>{ if(e.key==='Enter') tryFirstTimeSetup(); });

  const token = getToken();
  if(token){
    try{
      currentUser = await Api.me();
      enterDashboard();
      return;
    }catch(e){
      clearSession(); // token expired/invalid
    }
  }

  // No valid session — figure out whether this is first-time setup
  // (no staff accounts exist yet) or a normal login.
  try{
    await apiRequest('/api/menu'); // cheap public call just to confirm the API is reachable
  }catch(e){
    document.getElementById('gateError').textContent = e.message;
    document.getElementById('gateError').style.display = 'block';
  }
});

/* ---------- Panels ---------- */
function showPanel(name){
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
  document.getElementById('panel-'+name).classList.add('active');
  document.querySelectorAll('.side-link').forEach(l=>l.classList.toggle('active', l.dataset.panel===name));
  if(name==='orders') renderOrders();
  if(name==='reports') renderReports();
}

/* ===========================================================
   ORDERS
   =========================================================== */
async function renderOrders(){
  let orders;
  try{
    orders = await Api.getOrders();
  }catch(e){
    showToast('Could not load orders: ' + e.message);
    return;
  }

  const counts = {new:0,preparing:0,ready:0,completed:0};
  let revenue = 0;
  orders.forEach(o=>{ if(counts[o.status]!==undefined) counts[o.status]++; revenue += o.total; });

  document.getElementById('orderStats').innerHTML = `
    <div class="astat"><div class="num">${orders.length}</div><div class="lbl">Total orders</div></div>
    <div class="astat"><div class="num">${counts.new}</div><div class="lbl">New</div></div>
    <div class="astat"><div class="num">${counts.preparing}</div><div class="lbl">Preparing</div></div>
    <div class="astat"><div class="num">${counts.ready}</div><div class="lbl">Ready</div></div>
    <div class="astat"><div class="num">${fmtMoney(revenue)}</div><div class="lbl">Total sales</div></div>
  `;

  const board = document.getElementById('board');
  board.innerHTML = STATUS_FLOW.map(status=>{
    const colOrders = orders.filter(o=>o.status===status);
    return `
      <div class="board-col">
        <h3><span>${STATUS_LABEL[status]}</span><span>${colOrders.length}</span></h3>
        ${colOrders.length===0
          ? `<div class="board-empty">No orders</div>`
          : colOrders.map(o=>orderCardHTML(o)).join('')}
      </div>
    `;
  }).join('');
}

function orderCardHTML(o){
  const nextIdx = STATUS_FLOW.indexOf(o.status)+1;
  const nextStatus = STATUS_FLOW[nextIdx];
  return `
    <div class="order-card">
      <div class="oc-top">
        <span class="oc-num">${o.order_number}</span>
        <span class="oc-time">${timeAgo(o.created_at)}</span>
      </div>
      <div class="oc-mode">${o.mode==='dine_in' ? '🍽 Table '+o.table_number : (o.mode==='pickup' ? '🥡 Pickup' : '🚗 Delivery')} — ${o.customer_name}</div>
      <ul>${o.items.map(i=>`<li>${i.quantity}× ${i.item_name}</li>`).join('')}</ul>
      ${o.note ? `<div class="oc-note">Note: ${o.note}</div>` : ''}
      <div class="oc-total">${fmtMoney(o.total)}</div>
      <div class="oc-actions">
        ${nextStatus ? `<button class="btn btn-sm btn-primary" onclick="advanceOrder(${o.id}, '${nextStatus}')">Mark ${STATUS_LABEL[nextStatus]}</button>` : ''}
        ${o.status!=='completed' ? `<button class="btn btn-sm btn-ghost" onclick="cancelOrder(${o.id})">Cancel</button>` : ''}
      </div>
    </div>
  `;
}

async function advanceOrder(id, status){
  try{
    await Api.updateOrderStatus(id, status);
    renderOrders();
    showToast('Order marked ' + STATUS_LABEL[status]);
  }catch(e){
    showToast('Could not update order: ' + e.message);
  }
}

async function cancelOrder(id){
  if(!confirm('Cancel this order?')) return;
  try{
    await Api.updateOrderStatus(id, 'cancelled');
    renderOrders();
  }catch(e){
    showToast('Could not cancel order: ' + e.message);
  }
}

/* ===========================================================
   MENU MANAGEMENT
   =========================================================== */
let menuCache = [];

async function renderMenuManager(){
  try{
    menuCache = await Api.getMenu();
  }catch(e){
    showToast('Could not load menu: ' + e.message);
    return;
  }

  document.getElementById('mmCount').textContent = menuCache.length;

  const cats = [...new Set(menuCache.map(i=>i.category))];
  document.getElementById('catList').innerHTML = cats.map(c=>`<option value="${c}">`).join('');

  const tbody = document.getElementById('menuTableBody');
  tbody.innerHTML = menuCache.map(i=>`
    <tr>
      <td><strong>${i.emoji} ${i.name}</strong></td>
      <td>${i.category}</td>
      <td>${fmtMoney(i.price)}</td>
      <td><span class="avail-tag ${i.is_available!==false?'on':'off'}">${i.is_available!==false?'Available':'Sold out'}</span></td>
      <td>
        <div class="row-actions">
          <button class="icon-btn" title="Edit" onclick="editMenuItem(${i.id})">✎</button>
          <button class="icon-btn" title="Toggle availability" onclick="toggleAvailability(${i.id})">⇄</button>
          <button class="icon-btn" title="Delete" onclick="deleteMenuItem(${i.id})">🗑</button>
        </div>
      </td>
    </tr>
  `).join('');
}

async function saveMenuItem(){
  const idField = document.getElementById('mmId').value;
  const name = document.getElementById('mmName').value.trim();
  const category = document.getElementById('mmCat').value.trim() || 'Mains';
  const price = parseFloat(document.getElementById('mmPrice').value);
  const description = document.getElementById('mmDesc').value.trim();
  const emoji = document.getElementById('mmEmoji').value.trim() || '🍽️';
  const is_available = document.getElementById('mmAvail').value === 'true';

  if(!name || isNaN(price)){
    showToast('Name and price are required');
    return;
  }

  const payload = { name, category, price, description, emoji, is_available };

  try{
    if(idField){
      await Api.updateMenuItem(idField, payload);
    } else {
      await Api.createMenuItem(payload);
    }
    await renderMenuManager();
    resetMenuForm();
    showToast('Menu saved');
  }catch(e){
    showToast('Could not save item: ' + e.message);
  }
}

function editMenuItem(id){
  const item = menuCache.find(i=>i.id===id);
  if(!item) return;
  document.getElementById('mmId').value = item.id;
  document.getElementById('mmName').value = item.name;
  document.getElementById('mmCat').value = item.category;
  document.getElementById('mmPrice').value = item.price;
  document.getElementById('mmDesc').value = item.description || '';
  document.getElementById('mmEmoji').value = item.emoji;
  document.getElementById('mmAvail').value = String(item.is_available !== false);
  document.getElementById('mmFormTitle').textContent = 'Edit menu item';
  document.getElementById('mmSaveBtn').textContent = 'Save changes';
  document.getElementById('mmCancelBtn').classList.remove('hidden');
  window.scrollTo({top:0,behavior:'smooth'});
}

function resetMenuForm(){
  document.getElementById('mmId').value = '';
  document.getElementById('mmName').value = '';
  document.getElementById('mmCat').value = '';
  document.getElementById('mmPrice').value = '';
  document.getElementById('mmDesc').value = '';
  document.getElementById('mmEmoji').value = '';
  document.getElementById('mmAvail').value = 'true';
  document.getElementById('mmFormTitle').textContent = 'Add a menu item';
  document.getElementById('mmSaveBtn').textContent = 'Add item';
  document.getElementById('mmCancelBtn').classList.add('hidden');
}

async function toggleAvailability(id){
  try{
    await Api.toggleAvailability(id);
    renderMenuManager();
  }catch(e){
    showToast('Could not update item: ' + e.message);
  }
}

async function deleteMenuItem(id){
  if(!confirm('Remove this item from the menu?')) return;
  try{
    await Api.deleteMenuItem(id);
    renderMenuManager();
  }catch(e){
    showToast('Could not delete item: ' + e.message);
  }
}

/* ===========================================================
   TABLES & QR
   =========================================================== */
async function renderTables(){
  let tables;
  try{
    tables = await Api.getTables();
  }catch(e){
    showToast('Could not load tables: ' + e.message);
    return;
  }

  const grid = document.getElementById('qrGrid');
  const baseUrl = location.href.replace(/admin\.html.*$/, 'index.html');

  grid.innerHTML = tables.map(t=>`
    <div class="qr-card">
      <div class="qr-num">TABLE ${t.table_number}</div>
      <div class="qr-box" id="qr-${t.id}"></div>
      <div class="qr-link">${baseUrl}?t=${t.qr_token}</div>
      <div style="display:flex;gap:6px;justify-content:center">
        <button class="btn btn-sm btn-ghost" onclick="printTable(${t.table_number}, '${t.qr_token}')">Print</button>
        <button class="btn btn-sm btn-ghost" onclick="removeTable(${t.id})">Remove</button>
      </div>
    </div>
  `).join('');

  tables.forEach(t=>{
    const el = document.getElementById('qr-'+t.id);
    if(el && window.QRCode){
      el.innerHTML='';
      new QRCode(el, {text: baseUrl+'?t='+t.qr_token, width:120, height:120});
    }
  });
}

async function addTable(){
  const num = parseInt(document.getElementById('newTableNum').value,10);
  if(!num || num<1){ showToast('Enter a valid table number'); return; }
  try{
    await Api.addTable(num, 4);
    document.getElementById('newTableNum').value='';
    renderTables();
  }catch(e){
    showToast('Could not add table: ' + e.message);
  }
}

async function removeTable(id){
  if(!confirm('Remove this table?')) return;
  try{
    await Api.removeTable(id);
    renderTables();
  }catch(e){
    showToast('Could not remove table: ' + e.message);
  }
}

function printTable(num, token){
  const w = window.open('', '_blank', 'width=420,height=560');
  const baseUrl = location.href.replace(/admin\.html.*$/, 'index.html');
  w.document.write(`
    <html><head><title>Table ${num} QR</title></head>
    <body style="font-family:sans-serif;text-align:center;padding:40px">
      <h1>Table ${num}</h1>
      <p>Scan to order</p>
      <div id="p"></div>
      <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"><\/script>
      <script>new QRCode(document.getElementById('p'), {text:"${baseUrl}?t=${token}", width:220, height:220});
      setTimeout(()=>window.print(), 400);<\/script>
    </body></html>
  `);
  w.document.close();
}

/* ===========================================================
   REPORTS
   =========================================================== */
async function renderReports(){
  let summary;
  try{
    summary = await Api.reportSummary();
  }catch(e){
    showToast('Could not load reports: ' + e.message);
    return;
  }

  document.getElementById('reportStats').innerHTML = `
    <div class="astat"><div class="num">${summary.total_orders}</div><div class="lbl">Orders placed</div></div>
    <div class="astat"><div class="num">${fmtMoney(summary.total_revenue)}</div><div class="lbl">Total sales</div></div>
    <div class="astat"><div class="num">${fmtMoney(summary.average_order_value)}</div><div class="lbl">Average order</div></div>
  `;

  const tbody = document.getElementById('bestSellersBody');
  tbody.innerHTML = summary.best_sellers.length ? summary.best_sellers.map(d=>`
    <tr><td>${d.name}</td><td>—</td><td>${d.quantity}</td><td>${fmtMoney(d.revenue)}</td></tr>
  `).join('') : `<tr><td colspan="4" style="text-align:center;color:#9a9182">No sales yet</td></tr>`;
}

/* ---------- Toast ---------- */
let toastTimer;
function showToast(msg){
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(()=>t.classList.remove('show'), 2600);
}
