const byId = (id) => document.getElementById(id);
const params = new URLSearchParams(location.search);
const sellerView = params.get("view") === "seller";
const store = /^[a-z0-9-]{1,48}$/.test(params.get("store") || "") ? params.get("store") : "demo";
const navSuffix = store === "demo" ? "" : `&store=${store}`;
byId("shop-link").href = store === "demo" ? "/" : `/?store=${store}`;
byId("seller-link").href = `/?view=seller${navSuffix}`;
byId(sellerView ? "seller-link" : "shop-link").setAttribute("aria-current", "page");
byId("shop").hidden = sellerView;
byId("seller").hidden = !sellerView;
const currency = (amount) => `PKR ${Number(amount).toLocaleString("en-PK")}`;
let token = "";
let busy = false;
let threadId;
let customerId;
if (!sellerView) {
  customerId = localStorage.getItem("bazaarcart-customer") || crypto.randomUUID();
  localStorage.setItem("bazaarcart-customer", customerId);
  threadId = crypto.randomUUID();
}

async function api(path, options = {}) {
  const response = await fetch(`/api${path}`, {
    ...options,
    headers: {"X-Store": store, ...(options.headers || {})},
    signal: AbortSignal.timeout(25000),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = typeof body?.detail === "string" ? body.detail : "";
    throw new Error(detail || `Request failed (${response.status}). Try again.`);
  }
  return response.json();
}

function element(tag, content) {
  const node = document.createElement(tag);
  node.textContent = content;
  return node;
}

function addMessage(text, fromUser) {
  const log = byId("messages");
  const entry = element("p", text);
  if (fromUser) entry.className = "you";
  log.append(entry);
  log.scrollTop = log.scrollHeight;
}

async function send(message) {
  if (busy) return;
  busy = true;
  const controls = document.querySelectorAll("#shop button");
  controls.forEach((control) => { control.disabled = true; });
  addMessage(message, true);
  try {
    const data = await api("/chat", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({user_id: customerId, thread_id: threadId, message}),
    });
    addMessage(data.reply, false);
    byId("confirm").hidden = !data.reply.includes("reply 'confirm order'") &&
      (byId("confirm").hidden || /Total:|cancelled|cart is empty|stock changed/.test(data.reply));
    if (data.tool_calls.some((call) => call.name === "place_order")) await loadCatalog();
  } catch (error) {
    addMessage(error.message, false);
  } finally {
    busy = false;
    controls.forEach((control) => { control.disabled = false; });
  }
}

async function loadCatalog() {
  byId("catalog-status").textContent = "Loading catalog...";
  try {
    const products = await api("/catalog");
    byId("catalog-status").textContent = products.length ? "" : "No products are in stock.";
    byId("products").replaceChildren(...products.map((product) => {
      const card = element("article", "");
      card.className = "product";
      const button = element("button", "Add to cart");
      button.type = "button";
      button.onclick = () => send(`Add 1 ${product.sku} to my cart`);
      card.append(element("h3", product.name), element("p", `${product.color} / ${product.size}`),
        element("strong", currency(product.price)), document.createElement("br"), button);
      return card;
    }));
  } catch (error) {
    byId("catalog-status").textContent = error.message;
  }
}

function fillTable(id, rows) {
  byId(id).replaceChildren(...rows.map((values) => {
    const tr = document.createElement("tr");
    tr.append(...values.map((value) => element("td", value)));
    return tr;
  }));
}

function sellerHeaders() { return {"Authorization": `Bearer ${token}`}; }

async function loadSeller() {
  const data = await api("/seller/dashboard", {headers: sellerHeaders()});
  byId("order-count").textContent = data.sales.order_count;
  byId("sales-total").textContent = currency(data.sales.total);
  fillTable("inventory", data.products.map((p) => [p.sku, p.name, p.size, currency(p.price), p.stock]));
  fillTable("orders", data.orders.map((o) => [
    o.id.slice(0, 8), new Date(o.created_at).toLocaleString(),
    o.items.map((item) => `${item.quantity} x ${item.name}`).join(", "), currency(o.total),
  ]));
  byId("seller-data").hidden = false;
}

if (sellerView) {
  byId("seller-auth").onsubmit = async (event) => {
    event.preventDefault();
    token = byId("token").value.trim();
    byId("token").value = "";
    byId("seller-data").hidden = true;
    try {
      await loadSeller();
      byId("seller-status").textContent = "";
    } catch (error) {
      token = "";
      byId("seller-status").textContent = error.message;
    }
  };
  byId("upload").onsubmit = async (event) => {
    event.preventDefault();
    const file = byId("csv").files[0];
    if (file.size > 90000) {
      byId("seller-status").textContent = "CSV must be 90 KB or smaller.";
      return;
    }
    const submit = event.currentTarget.querySelector("button");
    submit.disabled = true;
    try {
      const response = await api("/seller/catalog", {
        method: "POST", headers: {...sellerHeaders(), "Content-Type": "application/json"},
        body: JSON.stringify(await file.text()),
      });
      await loadSeller();
      byId("seller-status").textContent = `Updated ${response.updated} products.`;
      byId("csv").value = "";
    } catch (error) {
      byId("seller-status").textContent = error.message;
    } finally {
      submit.disabled = false;
    }
  };
} else {
  byId("chat").onsubmit = (event) => {
    event.preventDefault();
    const input = byId("message");
    const message = input.value.trim();
    if (!busy && message) {
      input.value = "";
      send(message);
    }
  };
  byId("cart").onclick = () => send("Show my cart");
  byId("checkout").onclick = () => send("I want to check out");
  byId("confirm").onclick = () => send("confirm order");
  byId("new-chat").onclick = () => {
    threadId = crypto.randomUUID();
    byId("messages").replaceChildren();
    byId("confirm").hidden = true;
  };
  loadCatalog();
}
