import { useState, useEffect } from "react";
import { AlertTriangle, Package, Truck, Clock, DollarSign } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { fetchAlerts, placeOrder } from "@/lib/api";
import type { Product } from "@/lib/types";


export default function Alerts() {
  const [lowStock, setLowStock] = useState<Product[]>([]);
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);
  const [showAllCategories, setShowAllCategories] = useState(false);

  const loadAlerts = () => {
    fetchAlerts().then(setLowStock).catch(() => {
      toast.error("Failed to load alerts");
    });
  };

  useEffect(() => {
    loadAlerts();
  }, []);

  const categories = Array.from(new Set(lowStock.map(product => product.category))).sort();
  const displayedCategories = showAllCategories ? categories : categories.slice(0, 5);

  const filtered = lowStock.filter(product => {
    if (categoryFilter && product.category !== categoryFilter) return false;
    return true;
  });

  const totalDeficitCost = filtered.reduce((sum, product) => {
    const deficit = Math.max(0, 10 - product.quantity);
    return sum + deficit * product.price;
  }, 0);

  const handleRestock = async (product: Product) => {
    try {
      const reorderLevel = 10;
      const deficit = Math.max(0, reorderLevel - product.quantity);

      if (deficit === 0) {
        toast.info(`${product.name} is already at the reorder level`);
        return;
      }

      await placeOrder({
        product_id: product.id,
        quantity: deficit,
      });

      toast.success(`Purchase order generated for ${product.name}`);
      loadAlerts();
    } catch {
      toast.error("Failed to place restock order");
    }
  };

  return (
    <div className="space-y-6 animate-slide-in">
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
              <p className="text-2xl font-bold text-foreground">{filtered.filter(product => product.quantity === 0).length}</p>
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

      {categories.length > 0 && (
        <div className="flex flex-wrap gap-2 items-center bg-card/50 p-3 rounded-xl border border-border/50">
          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mr-2">Filter By:</span>
          {displayedCategories.map(category => (
            <button
              key={category}
              onClick={() => setCategoryFilter(category === categoryFilter ? null : category)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${categoryFilter === category ? "bg-primary text-primary-foreground shadow-lg shadow-primary/20" : "bg-card text-muted-foreground border border-border hover:bg-muted"}`}
            >
              {category}
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

      <div className="space-y-3">
        {filtered.sort((left, right) => left.quantity - right.quantity).map(product => {
          const reorderLevel = 10;
          const deficit = Math.max(0, reorderLevel - product.quantity);
          const restockCost = deficit * product.price;
          const isOut = product.quantity === 0;

          return (
            <Card key={product.id} className={`glass-card ${isOut ? "border-destructive/30" : "border-warning/30"}`}>
              <CardContent className="p-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <div className={`w-2 h-2 rounded-full mt-2 ${isOut ? "bg-destructive animate-pulse-soft" : "bg-warning"}`} />
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-semibold text-foreground">{product.name}</h3>
                        <Badge variant={isOut ? "destructive" : "secondary"} className={`text-xs ${!isOut ? "bg-warning/15 text-warning border-warning/20" : ""}`}>
                          {isOut ? "OUT OF STOCK" : "LOW STOCK"}
                        </Badge>
                      </div>
                      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                        <span className="font-mono">ID: {product.id}</span>
                        <span>{product.category}</span>
                        <span>${product.price.toFixed(2)} ea</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-6 text-sm ml-5 sm:ml-0">
                    <div className="flex gap-6">
                      <div className="text-center">
                        <p className={`font-bold font-mono ${isOut ? "text-destructive" : "text-warning"}`}>{product.quantity}</p>
                        <p className="text-xs text-muted-foreground">Current</p>
                      </div>
                      <div className="text-center">
                        <p className="font-bold font-mono text-foreground">{reorderLevel}</p>
                        <p className="text-xs text-muted-foreground">Reorder</p>
                      </div>
                      <div className="text-center">
                        <p className="font-bold font-mono text-primary">{deficit}</p>
                        <p className="text-xs text-muted-foreground">Deficit</p>
                      </div>
                    </div>
                    <Button onClick={() => handleRestock(product)} size="sm">
                      Restock
                    </Button>
                  </div>
                </div>

                <div className="mt-3 pt-3 border-t border-border/50 flex flex-wrap gap-x-6 gap-y-1 text-xs text-muted-foreground ml-5">
                  <span className="flex items-center gap-1"><Truck className="w-3 h-3" /> {product.supplier}</span>
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
