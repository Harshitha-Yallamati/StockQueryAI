import { useState, useEffect } from "react";
import { Search, Plus, Edit2, Trash2 } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetFooter,
} from "@/components/ui/sheet";
import { addProduct, deleteProduct, fetchInventory, fetchProductDetails, updateProduct } from "@/lib/api";
import type { Product } from "@/lib/types";
import { toast } from "sonner";


type ProductFormData = Omit<Product, "id" | "last_updated">;

const INITIAL_FORM_STATE: ProductFormData = {
  name: "",
  category: "",
  brand: "",
  price: 0,
  quantity: 0,
  warehouse_location: "",
  supplier: "",
  description: "",
};


export default function Products() {
  const [products, setProducts] = useState<Product[]>([]);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);
  const [isSheetOpen, setIsSheetOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [formData, setFormData] = useState<ProductFormData>(INITIAL_FORM_STATE);
  const [showAllCategories, setShowAllCategories] = useState(false);

  const loadProducts = () => {
    fetchInventory().then(setProducts).catch(() => {
      toast.error("Failed to load products");
    });
  };

  useEffect(() => {
    loadProducts();
  }, []);

  const handleEdit = async (id: number) => {
    try {
      const details = await fetchProductDetails(id);
      setFormData({
        name: details.name,
        category: details.category,
        brand: details.brand,
        price: details.price,
        quantity: details.quantity,
        warehouse_location: details.warehouse_location,
        supplier: details.supplier,
        description: details.description,
      });
      setEditingId(id);
      setIsSheetOpen(true);
    } catch {
      toast.error("Failed to load product details");
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Are you sure you want to delete this product?")) {
      return;
    }

    try {
      await deleteProduct(id);
      toast.success("Product deleted successfully");
      loadProducts();
    } catch {
      toast.error("Failed to delete product");
    }
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    try {
      if (editingId) {
        await updateProduct(editingId, formData);
        toast.success("Product updated successfully");
      } else {
        await addProduct(formData);
        toast.success("Product added successfully");
      }
      setIsSheetOpen(false);
      setFormData(INITIAL_FORM_STATE);
      setEditingId(null);
      loadProducts();
    } catch {
      toast.error("An error occurred");
    }
  };

  const categories = Array.from(new Set(products.map(product => product.category))).sort();
  const displayedCategories = showAllCategories ? categories : categories.slice(0, 5);

  const filteredProducts = products.filter(product => {
    if (categoryFilter && product.category !== categoryFilter) return false;
    if (search) {
      const query = search.toLowerCase();
      return product.name.toLowerCase().includes(query) || product.id.toString() === query;
    }
    return true;
  });

  return (
    <div className="space-y-4 animate-slide-in">
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            value={search}
            onChange={event => setSearch(event.target.value)}
            placeholder="Search products..."
            className="w-full pl-9 pr-4 py-2.5 rounded-lg border border-input bg-card text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
        <div className="flex gap-2 flex-wrap items-center">
          <button
            onClick={() => {
              setFormData(INITIAL_FORM_STATE);
              setEditingId(null);
              setIsSheetOpen(true);
            }}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors flex items-center gap-2"
          >
            <Plus className="w-4 h-4" /> Add Product
          </button>

          <div className="h-6 w-[1px] bg-border mx-1 hidden sm:block" />

          {displayedCategories.map(category => (
            <button
              key={category}
              onClick={() => setCategoryFilter(category === categoryFilter ? null : category)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${categoryFilter === category ? "bg-primary text-primary-foreground" : "bg-secondary text-secondary-foreground hover:bg-muted"}`}
            >
              {category}
            </button>
          ))}

          {categories.length > 5 && (
            <button
              onClick={() => setShowAllCategories(!showAllCategories)}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-muted hover:bg-muted/80 text-muted-foreground transition-colors"
            >
              {showAllCategories ? "Show Less" : `+${categories.length - 5} more`}
            </button>
          )}
        </div>
      </div>

      <Card className="glass-card overflow-hidden">
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/50">
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">ID</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Product</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Category</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Brand</th>
                  <th className="text-right px-4 py-3 font-medium text-muted-foreground">Price</th>
                  <th className="text-right px-4 py-3 font-medium text-muted-foreground">Stock</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Status</th>
                  <th className="text-center px-4 py-3 font-medium text-muted-foreground">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredProducts.map(product => {
                  const isLow = product.quantity > 0 && product.quantity < 10;
                  const isOut = product.quantity === 0;
                  return (
                    <tr key={product.id} className="border-b border-border/50 hover:bg-muted/30 transition-colors">
                      <td className="px-4 py-3 font-mono text-xs text-muted-foreground">{product.id}</td>
                      <td className="px-4 py-3 font-medium text-foreground">{product.name}</td>
                      <td className="px-4 py-3 text-muted-foreground">{product.category}</td>
                      <td className="px-4 py-3 text-muted-foreground">{product.brand}</td>
                      <td className="px-4 py-3 text-right font-mono text-foreground">${product.price.toFixed(2)}</td>
                      <td className="px-4 py-3 text-right font-mono text-foreground">{product.quantity}</td>
                      <td className="px-4 py-3">
                        <Badge
                          variant={isOut ? "destructive" : isLow ? "secondary" : "default"}
                          className={`text-xs ${!isOut && !isLow ? "bg-success/15 text-success border-success/20" : isLow ? "bg-warning/15 text-warning border-warning/20" : ""}`}
                        >
                          {isOut ? "Out of Stock" : isLow ? "Low Stock" : "In Stock"}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <div className="flex items-center justify-center gap-2">
                          <button onClick={() => handleEdit(product.id)} className="p-1.5 rounded-md hover:bg-primary/10 text-primary transition-colors">
                            <Edit2 className="w-4 h-4" />
                          </button>
                          <button onClick={() => handleDelete(product.id)} className="p-1.5 rounded-md hover:bg-destructive/10 text-destructive transition-colors">
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {filteredProducts.length === 0 && (
            <div className="py-12 text-center text-sm text-muted-foreground">No products found.</div>
          )}
        </CardContent>
      </Card>

      <Sheet open={isSheetOpen} onOpenChange={setIsSheetOpen}>
        <SheetContent className="sm:max-w-md overflow-y-auto">
          <SheetHeader>
            <SheetTitle>{editingId ? "Edit Product" : "Add New Product"}</SheetTitle>
            <SheetDescription>
              {editingId ? "Update the product details below." : "Enter the details for the new product."}
            </SheetDescription>
          </SheetHeader>

          <form onSubmit={handleSubmit} className="space-y-4 py-6">
            <div className="space-y-2">
              <label className="text-sm font-medium">Product Name</label>
              <Input
                required
                value={formData.name}
                onChange={event => setFormData({ ...formData, name: event.target.value })}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Category</label>
                <Input
                  required
                  value={formData.category}
                  onChange={event => setFormData({ ...formData, category: event.target.value })}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Brand</label>
                <Input
                  required
                  value={formData.brand}
                  onChange={event => setFormData({ ...formData, brand: event.target.value })}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Price ($)</label>
                <Input
                  type="number"
                  step="0.01"
                  required
                  value={formData.price}
                  onChange={event => setFormData({ ...formData, price: Number(event.target.value || 0) })}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Quantity</label>
                <Input
                  type="number"
                  required
                  value={formData.quantity}
                  onChange={event => setFormData({ ...formData, quantity: Number(event.target.value || 0) })}
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Warehouse Location</label>
              <Input
                value={formData.warehouse_location}
                onChange={event => setFormData({ ...formData, warehouse_location: event.target.value })}
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Supplier</label>
              <Input
                value={formData.supplier}
                onChange={event => setFormData({ ...formData, supplier: event.target.value })}
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Description</label>
              <Textarea
                className="h-24 resize-none"
                value={formData.description}
                onChange={event => setFormData({ ...formData, description: event.target.value })}
              />
            </div>

            <SheetFooter className="pt-4">
              <Button type="button" variant="outline" onClick={() => setIsSheetOpen(false)}>Cancel</Button>
              <Button type="submit">{editingId ? "Save Changes" : "Add Product"}</Button>
            </SheetFooter>
          </form>
        </SheetContent>
      </Sheet>
    </div>
  );
}
