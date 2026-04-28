import type { DashboardStats, Order, Product } from "@/lib/types";

const API_ROOT = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";
const API_BASE = `${API_ROOT}/api`;

async function fetchJson<T>(
  input: RequestInfo | URL,
  init: RequestInit,
  fallbackMessage: string,
): Promise<T> {
  const response = await fetch(input, init);
  if (!response.ok) {
    throw new Error(await extractErrorMessage(response, fallbackMessage));
  }
  return response.json() as Promise<T>;
}

async function extractErrorMessage(response: Response, fallbackMessage: string): Promise<string> {
  try {
    const payload = await response.json();
    if (typeof payload?.detail === "string") {
      return payload.detail;
    }
    if (payload?.detail?.message) {
      return payload.detail.message;
    }
  } catch {
    return fallbackMessage;
  }
  return fallbackMessage;
}

export async function fetchStats() {
  return fetchJson<DashboardStats>(`${API_BASE}/dashboard/stats`, {}, "Failed to fetch stats");
}

export async function fetchInventory() {
  return fetchJson<Product[]>(`${API_BASE}/products`, {}, "Failed to fetch inventory");
}

export async function fetchAlerts() {
  return fetchJson<Product[]>(`${API_BASE}/alerts`, {}, "Failed to fetch alerts");
}

export async function fetchProductDetails(id: string | number) {
  return fetchJson<Product>(`${API_BASE}/products/${id}`, {}, "Failed to fetch product details");
}

export async function addProduct(product: Partial<Product>) {
  return fetchJson<Product>(
    `${API_BASE}/products`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(product),
    },
    "Failed to add product",
  );
}

export async function updateProduct(id: number, product: Partial<Product>) {
  return fetchJson<Product>(
    `${API_BASE}/products/${id}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(product),
    },
    "Failed to update product",
  );
}

export async function deleteProduct(id: number) {
  return fetchJson<{ status: string; id: number }>(
    `${API_BASE}/products/${id}`,
    { method: "DELETE" },
    "Failed to delete product",
  );
}

export async function sendChatMessage(message: string, userId?: string) {
  const headers = new Headers({
    "Content-Type": "application/json",
    "Accept": "text/event-stream",
  });
  if (userId) {
    headers.set("X-User-ID", userId);
  }

  const response = await fetch(`${API_BASE}/chat/stream`, {
    method: "POST",
    headers,
    body: JSON.stringify({ question: message }),
  });

  if (!response.ok) {
    throw new Error(await extractErrorMessage(response, "Failed to reach AI Agent"));
  }

  return response;
}

export async function clearChatSession(userId?: string) {
  const headers = new Headers();
  if (userId) {
    headers.set("X-User-ID", userId);
  }

  return fetchJson<{ status: string; session_id: string }>(
    `${API_BASE}/chat/session`,
    {
      method: "DELETE",
      headers,
    },
    "Failed to clear chat session",
  );
}

export async function fetchOrders() {
  return fetchJson<Order[]>(`${API_BASE}/orders`, {}, "Failed to fetch orders");
}

export async function placeOrder(order: { product_id: number; quantity: number }) {
  return fetchJson<Order>(
    `${API_BASE}/orders`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(order),
    },
    "Failed to place order",
  );
}

export async function updateOrderStatus(id: number, status: string) {
  return fetchJson<Order>(
    `${API_BASE}/orders/${id}/status`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    },
    "Failed to update order status",
  );
}
