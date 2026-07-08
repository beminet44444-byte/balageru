/* ===========================================================
   BALAGERU RESTAURANT — customer ordering logic
   Talks to the Flask API (see js/api.js) instead of localStorage.
   =========================================================== */

let menu = [];
let cart = []; // {id, name, price, emoji, qty}
let activeCat = 'All';
let orderMode = 'dine_in'; // 'dine_in' | 'pickup'
let selectedTable = null; // resolved table NUMBER (never the raw QR token)

async function init(){
  document.getElementById('year').textContent = new Date().getFullYear();
  document.getElementById('ticketRight').textContent = new Date().toLocaleDateString(undefined,{weekday:'short', month:'short', day:'numeric'});

  await loadMenu();
  updateCartUI();

  // Arriving via a table QR code looks like index.html?t=<token>.
  // We resolve the opaque token server-side rather than trusting a raw
  // table number in the URL, so guests can't just type ?table=5.
  const params = new URLSearchParams(location.search);
  const qrToken = params.get('t');
  if(qrToken){
    try{
      const resolved = await Api.resolveTable(qrToken);
      selectedTable = resolved.table_number;
      setOrderMode('dine_in', /*fromQr*/ true);
      showToast('Table ' + selectedTable + ' detected — you\'re set to dine-in.');
    }catch(e){
      showToast('That table code is not recognized — please ask staff.');
      setOrderMode('pickup');
    }
  } else {
    setOrderMode('pickup');
  }
}
window.addEventListener('DOMContentLoaded', init);

/* ---------- Menu loading & rendering ---------- */
async function loadMenu(){
  const grid = document.getElementById('menuGrid');
  grid.innerHTML = `<p style="color:#9a9182">Loading the menu…</p>`;
  try{
    menu = await Api.getMenu();
    buildTabs();
    renderMenu();
  }catch(e){
    grid.innerHTML = `<p style="color:#a13a2a">Couldn't load the menu: ${e.message}</p>`;
  }
}

function buildTabs(){
  const cats = ['All', ...new Set(menu.map(i=>i.category))];
  const tabsEl = document.getElementById('tabs');
  tabsEl.innerHTML = cats.map(c =>
    `<button class="tab${c===activeCat?' active':''}" data-cat="${c}" onclick="selectCat('${c}')">${c}</button>`
  ).join('');
}

function selectCat(cat){
  activeCat = cat;
  document.querySelectorAll('.tab').forEach(t=>t.classList.toggle('active', t.dataset.cat===cat));
  renderMenu();
}

function renderMenu(){
  const grid = document.getElementById('menuGrid');
  const items = menu.filter(i => activeCat==='All' || i.category===activeCat);
  if(items.length===0){
    grid.innerHTML = `<p style="color:#9a9182">Nothing here right now — check back soon.</p>`;
    return;
  }
  grid.innerHTML = items.map(item => `
    <div class="item-card ${item.is_available===false?'unavailable':''}">
      <div class="item-top">
        <span class="item-num">${item.item_code}</span>
        <span class="item-emoji">${item.emoji}</span>
      </div>
      <h4>${item.name}${item.is_popular ? ' <span title="Popular">⭐</span>' : ''}</h4>
      <p class="item-desc">${item.description || ''}</p>
      <div class="item-bottom">
        ${item.is_available===false
          ? `<span class="sold-out-tag">Sold out</span>`
          : `<span class="item-price">${fmtMoney(item.price)}</span>`}
        <button class="add-btn" onclick="addToCart(${item.id})" ${item.is_available===false?'disabled':''}>+</button>
      </div>
    </div>
  `).join('');
}

/* ---------- Order mode / table ---------- */
function tryManualDineIn(){
  if(selectedTable){
    setOrderMode('dine_in', true);
  } else {
    showToast('Please scan the QR code on your table to order dine-in.');
  }
}

function setOrderMode(mode, fromQr){
  orderMode = mode;
  document.getElementById('modeDineBtn').classList.toggle('active', mode==='dine_in');
  document.getElementById('modePickupBtn').classList.toggle('active', mode==='pickup');
  const tableField = document.getElementById('tableField');
  if(mode === 'dine_in'){
    tableField.style.display = 'block';
    if(fromQr){
      tableField.innerHTML = `<label>Table</label><p style="margin:0;font-family:var(--mono);font-size:1rem">Table ${selectedTable}</p>`;
    }
  } else {
    tableField.style.display = 'none';
    selectedTable = null;
  }
  document.getElementById('ticketId').textContent =
    mode==='dine_in' ? ('TABLE ' + (selectedTable||'— ask staff to scan —')) : 'PICKUP ORDER';
}

/* ---------- Cart ---------- */
function addToCart(id){
  const item = menu.find(i=>i.id===id);
  if(!item || item.is_available===false) return;
  const line = cart.find(l=>l.id===id);
  if(line){ line.qty++; }
  else { cart.push({id:item.id, name:item.name, price:item.price, emoji:item.emoji, qty:1}); }
  updateCartUI();
  showToast(item.name + ' added to your order');
}

function changeQty(id, delta){
  const line = cart.find(l=>l.id===id);
  if(!line) return;
  line.qty += delta;
  if(line.qty<=0) cart = cart.filter(l=>l.id!==id);
  updateCartUI();
}

function removeLine(id){
  cart = cart.filter(l=>l.id!==id);
  updateCartUI();
}

function cartTotal(){
  return cart.reduce((sum,l)=>sum + l.price*l.qty, 0);
}
function cartCount(){
  return cart.reduce((sum,l)=>sum + l.qty, 0);
}

function updateCartUI(){
  const count = cartCount();
  document.getElementById('cartCount').textContent = count;
  document.getElementById('ticketCartCount').textContent = count;
  renderDrawer();
}

function renderDrawer(){
  const body = document.getElementById('drawerBody');
  const foot = document.getElementById('drawerFoot');

  if(cart.length===0){
    body.innerHTML = `<div class="drawer-empty">🧾<br>Your cart is empty.<br>Add something from the menu.</div>`;
    foot.innerHTML = '';
    return;
  }

  body.innerHTML = cart.map(l => `
    <div class="cart-line">
      <span class="emoji">${l.emoji}</span>
      <div class="info">
        <h5>${l.name}</h5>
        <div class="meta">${fmtMoney(l.price)} each</div>
        <div class="qty-ctrl">
          <button onclick="changeQty(${l.id},-1)">−</button>
          <span>${l.qty}</span>
          <button onclick="changeQty(${l.id},1)">+</button>
        </div>
        <button class="remove-line" onclick="removeLine(${l.id})">Remove</button>
      </div>
      <span class="line-price">${fmtMoney(l.price*l.qty)}</span>
    </div>
  `).join('');

  const subtotal = cartTotal();
  const estTax = subtotal * 0.15;
  foot.innerHTML = `
    <div class="total-row"><span>Subtotal</span><span>${fmtMoney(subtotal)}</span></div>
    <div class="total-row"><span>Tax (15%, estimated)</span><span>${fmtMoney(estTax)}</span></div>
    <div class="total-row grand"><span>Total</span><span>${fmtMoney(subtotal+estTax)}</span></div>
    <div class="checkout-form" id="checkoutForm">
      <input type="text" id="custName" placeholder="Name for the order">
      <input type="tel" id="custPhone" placeholder="Phone (for pickup updates)">
      <textarea id="custNote" placeholder="Notes for the kitchen (optional)" rows="2"></textarea>
    </div>
    <button class="btn btn-primary btn-block" style="margin-top:12px" onclick="submitOrder()" id="submitOrderBtn">Send order to kitchen</button>
  `;
}

function openCart(){
  document.getElementById('overlay').classList.add('open');
  document.getElementById('drawer').classList.add('open');
}
function closeCart(){
  document.getElementById('overlay').classList.remove('open');
  document.getElementById('drawer').classList.remove('open');
}

/* ---------- Checkout ---------- */
async function submitOrder(){
  if(cart.length===0) return;
  if(orderMode==='dine_in' && !selectedTable){
    showToast('Scan your table\'s QR code, or switch to Pickup');
    return;
  }

  const btn = document.getElementById('submitOrderBtn');
  btn.disabled = true;
  btn.textContent = 'Sending…';

  const payload = {
    mode: orderMode,
    table_number: orderMode==='dine_in' ? selectedTable : undefined,
    customer_name: document.getElementById('custName').value.trim() || 'Guest',
    customer_phone: document.getElementById('custPhone').value.trim(),
    note: document.getElementById('custNote').value.trim(),
    items: cart.map(l=>({menu_item_id: l.id, quantity: l.qty})),
  };

  try{
    const order = await Api.createOrder(payload);
    showConfirmation(order);
    cart = [];
    updateCartUI();
  }catch(e){
    showToast('Could not send order: ' + e.message);
    btn.disabled = false;
    btn.textContent = 'Send order to kitchen';
  }
}

function showConfirmation(order){
  const body = document.getElementById('drawerBody');
  const foot = document.getElementById('drawerFoot');
  foot.innerHTML = '';
  body.innerHTML = `
    <div class="confirm-view">
      <div class="confirm-ticket">
        <p class="eyebrow" style="text-align:center;margin-bottom:6px">Order sent to kitchen</p>
        <div class="big-num">${order.order_number}</div>
        <div class="row"><span>Mode</span><span>${order.mode==='dine_in' ? 'Dine-in — Table '+order.table_number : 'Pickup'}</span></div>
        <div class="row"><span>Name</span><span>${order.customer_name}</span></div>
        <div class="row"><span>Items</span><span>${order.items.reduce((s,i)=>s+i.quantity,0)}</span></div>
        <div class="row"><span>Tax</span><span>${fmtMoney(order.tax)}</span></div>
        <div class="row"><span>Total</span><span>${fmtMoney(order.total)}</span></div>
        <div class="row" style="border-bottom:none"><span>Status</span><span>${order.status}</span></div>
      </div>
      <button class="btn btn-ghost" style="margin-top:20px" onclick="closeCart()">Keep browsing</button>
    </div>
  `;
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
