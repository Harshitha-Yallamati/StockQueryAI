import Database from 'better-sqlite3';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const dbPath = path.join(__dirname, 'inventory.db');
const db = new Database(dbPath);

// Initialize Tables
db.exec(`
  CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    google_id TEXT,
    name TEXT
  );

  CREATE TABLE IF NOT EXISTS inventory (
    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    brand TEXT,
    price REAL NOT NULL,
    stock_quantity INTEGER NOT NULL,
    warehouse_location TEXT,
    supplier TEXT,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE IF NOT EXISTS product_details (
    product_id INTEGER PRIMARY KEY,
    description TEXT,
    specifications TEXT,
    ratings REAL,
    expiry_date TEXT,
    FOREIGN KEY (product_id) REFERENCES inventory(product_id)
  );

  CREATE TABLE IF NOT EXISTS sales_transactions (
    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    quantity_sold INTEGER NOT NULL,
    date DATETIME DEFAULT CURRENT_TIMESTAMP,
    revenue REAL NOT NULL,
    FOREIGN KEY (product_id) REFERENCES inventory(product_id)
  );

  CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_name TEXT NOT NULL,
    delivery_time INTEGER,
    reliability_score REAL
  );
`);

console.log('Database initialized successfully.');

// Seed Data
const insertSupplier = db.prepare('INSERT INTO suppliers (supplier_name, delivery_time, reliability_score) VALUES (?, ?, ?)');
const insertProduct = db.prepare('INSERT INTO inventory (product_name, category, brand, price, stock_quantity, warehouse_location, supplier) VALUES (?, ?, ?, ?, ?, ?, ?)');
const insertDetails = db.prepare('INSERT INTO product_details (product_id, description, specifications, ratings, expiry_date) VALUES (?, ?, ?, ?, ?)');

const suppliers = [
  ['Apple Inc.', 7, 4.9],
  ['Samsung Direct', 10, 4.7],
  ['TechSupply Co.', 3, 4.5],
  ['PeripheralPro', 5, 4.2],
  ['AccessoryWorld', 7, 4.0],
  ['AudioTech Ltd.', 4, 4.6],
  ['GameStation Supply', 8, 4.4],
  ['NetGear Pro', 6, 4.3]
];

db.transaction(() => {
  for (const s of suppliers) insertSupplier.run(...s);

  const products = [
    ['iPhone 15 Pro', 'Electronics', 'Apple', 999.99, 45, 'Aisle 1, Shelf A', 'Apple Inc.'],
    ['Samsung Galaxy S24', 'Electronics', 'Samsung', 849.99, 32, 'Aisle 1, Shelf B', 'Samsung Direct'],
    ['MacBook Air M3', 'Electronics', 'Apple', 1299.00, 18, 'Aisle 2, Shelf A', 'Apple Inc.'],
    ['Wireless Mouse', 'Accessories', 'Logitech', 29.99, 5, 'Aisle 5, Shelf C', 'PeripheralPro'],
    ['USB-C Cable', 'Accessories', 'Generic', 14.99, 12, 'Aisle 5, Shelf D', 'TechSupply Co.'],
    ['AirPods Pro 2', 'Audio', 'Apple', 249.00, 55, 'Aisle 3, Shelf A', 'Apple Inc.'],
    ['Sony WH-1000XM5', 'Audio', 'Sony', 349.99, 28, 'Aisle 3, Shelf B', 'AudioTech Ltd.'],
    ['PlayStation 5', 'Gaming', 'Sony', 499.99, 12, 'Aisle 7, Shelf A', 'GameStation Supply']
  ];

  products.forEach((p, idx) => {
    const info = insertProduct.run(...p);
    insertDetails.run(
      info.lastInsertRowid,
      `${p[0]} - High performance device with state-of-the-art features.`,
      'Weight: 200g, Dimensions: 150x70x8mm',
      4.8,
      null
    );
  });
})();

console.log('Seed data inserted successfully.');
db.close();
