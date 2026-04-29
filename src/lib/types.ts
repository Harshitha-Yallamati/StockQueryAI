// Migration note: frontend product types use only the normalized schema keys.
export interface Product {
  id: number;
  name: string;
  quantity: number;
  price: number;
  category: string;
  brand: string;
  supplier: string;
  warehouse_location: string;
  description: string;
  last_updated: string;
}

export interface Order {
  id: number;
  product_id: number;
  name: string;
  quantity: number;
  total_cost: number;
  status: string;
  order_date: string;
}

export interface DashboardStats {
  totalProducts: number;
  totalValue: number;
  lowStock: number;
}

export interface ToolTrace {
  callId: string;
  name: string;
  status: "running" | "success" | "error";
  summary: string;
  arguments?: Record<string, unknown>;
  result?: unknown;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  status?: string;
  toolCalls?: ToolTrace[];
}
