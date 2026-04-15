import { useState, useEffect } from "react";
import { AlertTriangle, Package, Truck, Clock, DollarSign } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { fetchAlerts, placeOrder } from "@/lib/api";

type AlertItem = {
  product_id: number;
  product_name: string;
  category: string;
  brand: string;
  price: number;
  stock_quantity: number;
  warehouse_location: string;
  supplier: string;
}

export default function Alerts() {
  const [lowStock, setLowStock] = useState<AlertItem[]>([]);
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);
  const [showAllCategories, setShowAllCategories] = useState(false);

  const loadAlerts = () => {
    fetchAlerts().then(setLowStock).catch(console.error);
  };

  useEffect(() => {
    loadAlerts();
  }, []);

  const categories = Array.from(new Set(lowStock.map(p => p.category))).sort();
  const displayedCategories = showAllCategories ? categories : categories.slice(0, 5);

  const filtered = lowStock.filter(p => {
    if (categoryFilter && p.category !== categoryFilter) return false;
    return true;
  });

  const totalDeficitCost = filtered.reduce((s, p) => {
    // Assuming a generic reorder level of 10 for all alerts
    const deficit = Math.max(0, 10 - p.stock_quantity);
    return s + deficit * p.price;
  }, 0);

  const handleRestock = async (product: AlertItem) => {
    try {
      const reorder_level = 10;
      const deficit = Math.max(0, reorder_level - product.stock_quantity);
      const total_cost = deficit * product.price;

      await placeOrder({
        product_id: product.product_id,
        product_name: product.product_name,
        quantity: deficit,
        total_cost: total_cost
      });

      toast.success(`Purchase order generated for ${product.product_name}`);
      loadAlerts(); // Refresh list to reflect that we've initiated restock
    } catch (e) {
      toast.error("Failed to place restock order");
    }
  };

  return (
    <div className="space-y-6 animate-slide-in">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="glass-card border-warning/30">
          <CardContent className="p-5 flex items-center gap-4">
            <div className="w-10 h-10 rounded-lg bg-warning/10 flex items-center justify-center">
              <AlertTriangle className="w-5 h-5 text-warning" />
            </div>
            <div>
              <p className="text-2xl font-bold text-foreground">{filtered.length}</p>
              <p className="text-xs text-muted-foreground">Items Need Restocking</p>
            </div>
          </CardContent>
        </Card>
        <Card className="glass-card border-destructive/30">
          <CardContent className="p-5 flex items-center gap-4">
            <div className="w-10 h-10 rounded-lg bg-destructive/10 flex items-center justify-center">
              <Package className="w-5 h-5 text-destructive" />
            </div>
            <div>
              <p className="text-2xl font-bold text-foreground">{filtered.filter(p => p.stock_quantity === 0).length}</p>
              <p className="text-xs text-muted-foreground">Out of Stock</p>
            </div>
          </CardContent>
        </Card>
        <Card className="glass-card">
          <CardContent className="p-5 flex items-center gap-4">
            <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
              <DollarSign className="w-5 h-5 text-primary" />
            </div>
            <div>
              <p className="text-2xl font-bold text-foreground">${totalDeficitCost.toLocaleString(undefined, { maximumFractionDigits: 0 })}</p>
              <p className="text-xs text-muted-foreground">Est. Restock Cost</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      {categories.length > 0 && (
        <div className="flex flex-wrap gap-2 items-center bg-card/50 p-3 rounded-xl border border-border/50">
          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mr-2">Filter By:</span>
          {displayedCategories.map(c => (
            <button
              key={c}
              onClick={() => setCategoryFilter(c === categoryFilter ? null : c)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${categoryFilter === c ? "bg-primary text-primary-foreground shadow-lg shadow-primary/20" : "bg-card text-muted-foreground border border-border hover:bg-muted"}`}
            >
              {c}
            </button>
          ))}
          {categories.length > 5 && (
            <button
              onClick={() => setShowAllCategories(!showAllCategories)}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-muted text-muted-foreground hover:bg-muted/80 transition-colors"
            >
              {showAllCategories ? "Show Less" : `+${categories.length - 5} more`}
            </button>
          )}
        </div>
      )}

      {/* Alert Cards */}
      <div className="space-y-3">
        {filtered.sort((a, b) => a.stock_quantity - b.stock_quantity).map(p => {
          const reorder_level = 10;
          const deficit = Math.max(0, reorder_level - p.stock_quantity);
          const restockCost = deficit * p.price;
          const isOut = p.stock_quantity === 0;

          return (
            <Card key={p.product_id} className={`glass-card ${isOut ? "border-destructive/30" : "border-warning/30"}`}>
              <CardContent className="p-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <div className={`w-2 h-2 rounded-full mt-2 ${isOut ? "bg-destructive animate-pulse-soft" : "bg-warning"}`} />
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-semibold text-foreground">{p.product_name}</h3>
                        <Badge variant={isOut ? "destructive" : "secondary"} className={`text-xs ${!isOut ? "bg-warning/15 text-warning border-warning/20" : ""}`}>
                          {isOut ? "OUT OF STOCK" : "LOW STOCK"}
                        </Badge>
                      </div>
                      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                        <span className="font-mono">ID: {p.product_id}</span>
                        <span>{p.category}</span>
                        <span>${p.price.toFixed(2)} ea</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-6 text-sm ml-5 sm:ml-0">
                    <div className="flex gap-6">
                      <div className="text-center">
                        <p className={`font-bold font-mono ${isOut ? "text-destructive" : "text-warning"}`}>{p.stock_quantity}</p>
                        <p className="text-xs text-muted-foreground">Current</p>
                      </div>
                      <div className="text-center">
                        <p className="font-bold font-mono text-foreground">{reorder_level}</p>
                        <p className="text-xs text-muted-foreground">Reorder</p>
                      </div>
                      <div className="text-center">
                        <p className="font-bold font-mono text-primary">{deficit}</p>
                        <p className="text-xs text-muted-foreground">Deficit</p>
                      </div>
                    </div>
                    <Button onClick={() => handleRestock(p)} size="sm">
                      Restock
                    </Button>
                  </div>
                </div>

                <div className="mt-3 pt-3 border-t border-border/50 flex flex-wrap gap-x-6 gap-y-1 text-xs text-muted-foreground ml-5">
                  <span className="flex items-center gap-1"><Truck className="w-3 h-3" /> {p.supplier}</span>
                  <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> Standard lead time</span>
                  <span className="flex items-center gap-1"><DollarSign className="w-3 h-3" /> ${restockCost.toLocaleString(undefined, { maximumFractionDigits: 2 })} restock cost</span>
                </div>
              </CardContent>
            </Card>
          );
        })}
        {lowStock.length === 0 && (
          <div className="py-12 text-center text-sm text-muted-foreground">Everything is well stocked!</div>
        )}
      </div>
    </div>
  );
}
