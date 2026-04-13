const API_BASE = '/api';

export async function fetchStats() {
  const res = await fetch(`${API_BASE}/dashboard/stats`);
  if (!res.ok) throw new Error('Failed to fetch stats');
  return res.json();
}

export async function fetchInventory() {
  const res = await fetch(`${API_BASE}/inventory`);
  if (!res.ok) throw new Error('Failed to fetch inventory');
  return res.json();
}

export async function fetchAlerts() {
  const res = await fetch(`${API_BASE}/alerts`);
  if (!res.ok) throw new Error('Failed to fetch alerts');
  return res.json();
}

export async function fetchProductDetails(id: string | number) {
  const res = await fetch(`${API_BASE}/product/${id}`);
  if (!res.ok) throw new Error('Failed to fetch product details');
  return res.json();
}

export async function addProduct(product: any) {
  const res = await fetch(`${API_BASE}/inventory`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(product)
  });
  if (!res.ok) throw new Error('Failed to add product');
  return res.json();
}

export async function updateProduct(id: number, product: any) {
  const res = await fetch(`${API_BASE}/inventory/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(product)
  });
  if (!res.ok) throw new Error('Failed to update product');
  return res.json();
}

export async function deleteProduct(id: number) {
  const res = await fetch(`${API_BASE}/inventory/${id}`, {
    method: 'DELETE'
  });
  if (!res.ok) throw new Error('Failed to delete product');
  return res.json();
}

export async function sendChatMessage(message: string) {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message })
  });
  if (!res.ok) throw new Error('Failed to send message');
  return res.json();
}
