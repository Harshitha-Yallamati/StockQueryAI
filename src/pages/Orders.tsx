import { useState, useEffect } from "react";
import { ShoppingCart, Clock, CheckCircle2, ArrowRight } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { fetchOrders, updateOrderStatus } from "@/lib/api";
import type { Order } from "@/lib/types";


export default function Orders() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const loadOrders = async () => {
    try {
      const data = await fetchOrders();
      setOrders(data);
    } catch {
      toast.error("Failed to load orders");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void loadOrders();
  }, []);

  const handleMarkArrived = async (id: number) => {
    try {
      await updateOrderStatus(id, "Arrived");
      toast.success("Order marked as arrived. Inventory updated!");
      await loadOrders();
    } catch {
      toast.error("Failed to update order status");
    }
  };

  const pendingCount = orders.filter(order => order.status === "Pending").length;
  const totalSpend = orders.reduce((sum, order) => sum + order.total_cost, 0);

  return (
    <div className="space-y-6 animate-slide-in">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Card className="glass-card">
          <CardContent className="p-5 flex items-center gap-4">
            <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
              <Clock className="w-5 h-5 text-primary" />
            </div>
            <div>
              <p className="text-2xl font-bold text-foreground">{pendingCount}</p>
              <p className="text-xs text-muted-foreground">Pending Shipments</p>
            </div>
          </CardContent>
        </Card>
        <Card className="glass-card">
          <CardContent className="p-5 flex items-center gap-4">
            <div className="w-10 h-10 rounded-lg bg-success/10 flex items-center justify-center">
              <CheckCircle2 className="w-5 h-5 text-success" />
            </div>
            <div>
              <p className="text-2xl font-bold text-foreground">${totalSpend.toLocaleString()}</p>
              <p className="text-xs text-muted-foreground">Total Restock Spend</p>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="glass-card overflow-hidden">
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/50">
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Order ID</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Product</th>
                  <th className="text-right px-4 py-3 font-medium text-muted-foreground">Qty</th>
                  <th className="text-right px-4 py-3 font-medium text-muted-foreground">Cost</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Date</th>
                  <th className="text-center px-4 py-3 font-medium text-muted-foreground">Status</th>
                  <th className="text-right px-4 py-3 font-medium text-muted-foreground">Action</th>
                </tr>
              </thead>
              <tbody>
                {orders.map(order => (
                  <tr key={order.id} className="border-b border-border/50 hover:bg-muted/30 transition-colors">
                    <td className="px-4 py-3 font-mono text-xs text-muted-foreground">#{order.id}</td>
                    <td className="px-4 py-3 font-medium text-foreground">{order.name}</td>
                    <td className="px-4 py-3 text-right font-mono">{order.quantity}</td>
                    <td className="px-4 py-3 text-right font-mono">${order.total_cost.toFixed(2)}</td>
                    <td className="px-4 py-3 text-muted-foreground text-xs">
                      {new Date(order.order_date).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <Badge
                        variant={order.status === "Pending" ? "secondary" : "outline"}
                        className={order.status === "Pending" ? "bg-warning/15 text-warning border-warning/20" : "bg-success/15 text-success border-success/20"}
                      >
                        {order.status.toUpperCase()}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-right">
                      {order.status === "Pending" && (
                        <Button
                          size="sm"
                          variant="ghost"
                          className="text-xs text-primary hover:bg-primary/10"
                          onClick={() => handleMarkArrived(order.id)}
                        >
                          Mark Arrived <ArrowRight className="w-3 h-3 ml-1" />
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {orders.length === 0 && !isLoading && (
            <div className="py-12 text-center">
              <ShoppingCart className="w-12 h-12 text-muted-foreground/20 mx-auto mb-3" />
              <p className="text-sm text-muted-foreground">No restock orders found.</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
