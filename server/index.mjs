import express from 'express';
import cors from 'cors';
import Database from 'better-sqlite3';
import session from 'express-session';
import bcrypt from 'bcryptjs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const dbPath = path.join(__dirname, 'inventory.db');
const db = new Database(dbPath);

const app = express();
const PORT = process.env.PORT || 3001;

app.use(cors({ origin: 'http://localhost:8080', credentials: true }));
app.use(express.json());
app.use(session({
  secret: 'stockquery-secret-key',
  resave: false,
  saveUninitialized: false,
  cookie: { secure: false, maxAge: 24 * 60 * 60 * 1000 }
}));

// --- Middleware ---
const isAuthenticated = (req, res, next) => {
  if (req.session.userId) return next();
  res.status(401).json({ error: 'Unauthorized' });
};

// --- Auth Routes ---
app.post('/api/auth/signup', (req, res) => {
  const { email, password, name } = req.body;
  
  const existingUser = db.prepare('SELECT * FROM users WHERE email = ?').get(email);
  if (existingUser) {
    return res.status(400).json({ error: 'User already exists' });
  }

  try {
    const hash = bcrypt.hashSync(password, 10);
    const result = db.prepare('INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)')
      .run(email, hash, name || email.split('@')[0]);
    
    req.session.userId = result.lastInsertRowid;
    res.status(201).json({ id: result.lastInsertRowid, email, name: name || email.split('@')[0] });
  } catch (err) {
    res.status(500).json({ error: 'Failed to create user' });
  }
});

app.post('/api/auth/login', (req, res) => {
  const { email, password } = req.body;
  const user = db.prepare('SELECT * FROM users WHERE email = ?').get(email);
  
  if (user && user.password_hash && bcrypt.compareSync(password, user.password_hash)) {
    req.session.userId = user.id;
    return res.json({ id: user.id, email: user.email, name: user.name });
  }
  
  res.status(401).json({ error: 'Invalid email or password' });
});

app.post('/api/auth/google', (req, res) => {
  const { googleId, email, name, picture } = req.body;
  let user = db.prepare('SELECT * FROM users WHERE google_id = ? OR email = ?').get(googleId, email);
  
  if (!user) {
    const result = db.prepare('INSERT INTO users (email, google_id, name) VALUES (?, ?, ?)')
      .run(email, googleId, name);
    user = { id: result.lastInsertRowid, email, name };
  } else if (!user.google_id) {
    // Link existing email-based account to Google
    db.prepare('UPDATE users SET google_id = ?, name = ? WHERE id = ?').run(googleId, name, user.id);
    user.google_id = googleId;
    user.name = name;
  }
  
  req.session.userId = user.id;
  res.json({ ...user, picture });
});

app.get('/api/auth/me', (req, res) => {
  if (!req.session.userId) return res.status(401).json({ error: 'Not logged in' });
  const user = db.prepare('SELECT id, email, name FROM users WHERE id = ?').get(req.session.userId);
  res.json(user);
});

app.post('/api/auth/logout', (req, res) => {
  req.session.destroy();
  res.json({ message: 'Logged out' });
});

// --- Inventory Tools (The "Tools" requested by user) ---

function query_inventory_db(sql, params = []) {
  try {
    const stmt = db.prepare(sql);
    return stmt.all(...params);
  } catch (err) {
    console.error('SQL Error:', err);
    return { error: err.message };
  }
}

function get_product_details(sku_or_id) {
  const product = db.prepare('SELECT * FROM inventory WHERE product_id = ? OR product_name LIKE ?').get(sku_or_id, `%${sku_or_id}%`);
  if (!product) return null;
  const details = db.prepare('SELECT * FROM product_details WHERE product_id = ?').get(product.product_id);
  return { ...product, ...details };
}

// --- API Endpoints ---

app.get('/api/inventory', isAuthenticated, (req, res) => {
  const items = db.prepare('SELECT * FROM inventory').all();
  res.json(items);
});

app.post('/api/inventory', isAuthenticated, (req, res) => {
  const { product_name, category, brand, price, stock_quantity, warehouse_location, supplier, description } = req.body;
  try {
    const info = db.prepare(`
      INSERT INTO inventory (product_name, category, brand, price, stock_quantity, warehouse_location, supplier)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `).run(product_name, category, brand, price, stock_quantity, warehouse_location, supplier);
    
    db.prepare(`
      INSERT INTO product_details (product_id, description)
      VALUES (?, ?)
    `).run(info.lastInsertRowid, description || `${product_name} - New product entry.`);
    
    res.status(201).json({ id: info.lastInsertRowid, product_name });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.put('/api/inventory/:id', isAuthenticated, (req, res) => {
  const { product_name, category, brand, price, stock_quantity, warehouse_location, supplier, description } = req.body;
  try {
    db.prepare(`
      UPDATE inventory 
      SET product_name=?, category=?, brand=?, price=?, stock_quantity=?, warehouse_location=?, supplier=?, last_updated=CURRENT_TIMESTAMP
      WHERE product_id=?
    `).run(product_name, category, brand, price, stock_quantity, warehouse_location, supplier, req.params.id);
    
    db.prepare(`
      UPDATE product_details SET description=? WHERE product_id=?
    `).run(description, req.params.id);
    
    res.json({ message: 'Product updated' });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.delete('/api/inventory/:id', isAuthenticated, (req, res) => {
  try {
    db.prepare('DELETE FROM product_details WHERE product_id=?').run(req.params.id);
    db.prepare('DELETE FROM inventory WHERE product_id=?').run(req.params.id);
    res.json({ message: 'Product deleted' });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/product/:id', isAuthenticated, (req, res) => {
  const details = get_product_details(req.params.id);
  if (!details) return res.status(404).json({ error: 'Product not found' });
  res.json(details);
});

app.get('/api/dashboard/stats', isAuthenticated, (req, res) => {
  const totalProducts = db.prepare('SELECT COUNT(*) as count FROM inventory').get().count;
  const totalValue = db.prepare('SELECT SUM(price * stock_quantity) as total FROM inventory').get().total;
  const lowStock = db.prepare('SELECT COUNT(*) as count FROM inventory WHERE stock_quantity < 10').get().count;
  
  res.json({ totalProducts, totalValue, lowStock });
});

app.get('/api/alerts', isAuthenticated, (req, res) => {
  const alerts = db.prepare('SELECT * FROM inventory WHERE stock_quantity < 10').all();
  res.json(alerts);
});

// --- Enhanced Agentic Simulation ---

app.post('/api/chat', isAuthenticated, async (req, res) => {
  const { message } = req.body;
  const q = message.toLowerCase();
  
  let response = "";
  let tool_results = [];
  let thought = "I should analyze the user's query to determine which inventory tool to use.";

  if (q.includes("stock") && (q.includes("low") || q.includes("below") || q.includes("level"))) {
    thought = "The user is asking about low stock items. I'll query the inventory for items with quantity less than 10.";
    const results = query_inventory_db("SELECT product_name, stock_quantity, warehouse_location FROM inventory WHERE stock_quantity < 10");
    tool_results.push({ tool: 'get_low_stock_report', output: results });
    response = results.length > 0 
      ? `I found **${results.length} items** that are currently low on stock. You might want to check the Alerts page for restock options.`
      : "Great news! All items currently meet the minimum stock thresholds.";
  } 
  else if (q.includes("stock") || q.includes("available") || q.includes("inventory")) {
    thought = "The user wants a general overview of available stock. I'll fetch all items with positive stock counts.";
    const results = query_inventory_db("SELECT product_name, stock_quantity, category FROM inventory WHERE stock_quantity > 0");
    tool_results.push({ tool: 'query_inventory_db', output: results });
    response = `I've analyzed the inventory. There are **${results.length} different product lines** with active stock. Total units across all categories: ${results.reduce((s, r) => s + r.stock_quantity, 0)}.`;
  } 
  else if (q.includes("details") || q.includes("tell me about") || q.includes("who is") || q.includes("what is")) {
    const productName = q.replace(/.*(about|is|who is) /, "").replace(/ details.*/, "").trim();
    thought = `The user is asking for specifics on "${productName}". I'll search for this product in the inventory and details tables.`;
    const details = get_product_details(productName);
    tool_results.push({ tool: 'get_product_details', output: details });
    if (details) {
      response = `Here is what I found for **${details.product_name}**:\n- **Price**: $${details.price}\n- **Current Stock**: ${details.stock_quantity}\n- **Location**: ${details.warehouse_location}\n- **Wait time**: Supplying from ${details.supplier}.\n\n*Description*: ${details.description}`;
    } else {
      response = `I couldn't find any product matching "${productName}". Could you please double-check the name or ID?`;
    }
  } 
  else {
    thought = "I'm not sure which tool to use for this specific query. I'll provide a helpful guide on what I can do.";
    response = "I'm your StockQuery AI agent. I can help you with:\n- Checking **low stock** alerts\n- Summarizing **current inventory** levels\n- Providing **detailed specifications** for any product\n\nWhat would you like to know?";
  }

  res.json({ response, tool_results, thought });
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
