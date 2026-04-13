import { useState, useEffect } from "react";
import { Search, Plus, Edit2, Trash2, X } from "lucide-react";
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
  SheetFooter
} from "@/components/ui/sheet";
import { fetchInventory, addProduct, updateProduct, deleteProduct, fetchProductDetails } from "@/lib/api";
import { toast } from "sonner";

type Product = {
  product_id: number;
  product_name: string;
  category: string;
  brand: string;
  price: number;
  stock_quantity: number;
  warehouse_location: string;
  supplier: string;
  last_updated: string;
  description?: string;
}

const INITIAL_FORM_STATE = {
  product_name: "",
  category: "",
  brand: "",
  price: 0,
  stock_quantity: 0,
  warehouse_location: "",
  supplier: "",
  description: ""
};

export default function Products() {
  const [products, setProducts] = useState<Product[]>([]);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);
  const [isSheetOpen, setIsSheetOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [formData, setFormData] = useState(INITIAL_FORM_STATE);

  const loadProducts = () => {
    fetchInventory().then(setProducts).catch(console.error);
  };

  useEffect(() => {
    loadProducts();
  }, []);

  const handleEdit = async (id: number) => {
    try {
      const details = await fetchProductDetails(id);
      setFormData({
        product_name: details.product_name,
        category: details.category,
        brand: details.brand,
        price: details.price,
        stock_quantity: details.stock_quantity,
        warehouse_location: details.warehouse_location,
        supplier: details.supplier,
        description: details.description || ""
      });
      setEditingId(id);
      setIsSheetOpen(true);
    } catch (e) {
      toast.error("Failed to load product details");
    }
  };

  const handleDelete = async (id: number) => {
    if (confirm("Are you sure you want to delete this product?")) {
      try {
        await deleteProduct(id);
        toast.success("Product deleted successfully");
        loadProducts();
      } catch (e) {
        toast.error("Failed to delete product");
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
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
    } catch (e) {
      toast.error("An error occurred");
    }
  };

  const categories = Array.from(new Set(products.map(p => p.category)));

  const filtered = products.filter(p => {
    if (categoryFilter && p.category !== categoryFilter) return false;
    if (search) {
      const q = search.toLowerCase();
      return p.product_name.toLowerCase().includes(q) || (p.product_id.toString() === q);
    }
    return true;
  });

  return (
    <div className="space-y-4 animate-slide-in">
      {/* Filters & Actions */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
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

          {categories.map(c => (
            <button
              key={c}
              onClick={() => setCategoryFilter(c === categoryFilter ? null : c)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${categoryFilter === c ? "bg-primary text-primary-foreground" : "bg-secondary text-secondary-foreground hover:bg-muted"}`}
            >
              {c}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
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
                {filtered.map(p => {
                  const isLow = p.stock_quantity > 0 && p.stock_quantity < 10;
                  const isOut = p.stock_quantity === 0;
                  return (
                    <tr key={p.product_id} className="border-b border-border/50 hover:bg-muted/30 transition-colors">
                      <td className="px-4 py-3 font-mono text-xs text-muted-foreground">{p.product_id}</td>
                      <td className="px-4 py-3 font-medium text-foreground">{p.product_name}</td>
                      <td className="px-4 py-3 text-muted-foreground">{p.category}</td>
                      <td className="px-4 py-3 text-muted-foreground">{p.brand}</td>
                      <td className="px-4 py-3 text-right font-mono text-foreground">${p.price.toFixed(2)}</td>
                      <td className="px-4 py-3 text-right font-mono text-foreground">{p.stock_quantity}</td>
                      <td className="px-4 py-3">
                        <Badge variant={isOut ? "destructive" : isLow ? "secondary" : "default"} className={`text-xs ${!isOut && !isLow ? "bg-success/15 text-success border-success/20" : isLow ? "bg-warning/15 text-warning border-warning/20" : ""}`}>
                          {isOut ? "Out of Stock" : isLow ? "Low Stock" : "In Stock"}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <div className="flex items-center justify-center gap-2">
                          <button onClick={() => handleEdit(p.product_id)} className="p-1.5 rounded-md hover:bg-primary/10 text-primary transition-colors">
                            <Edit2 className="w-4 h-4" />
                          </button>
                          <button onClick={() => handleDelete(p.product_id)} className="p-1.5 rounded-md hover:bg-destructive/10 text-destructive transition-colors">
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
          {filtered.length === 0 && (
            <div className="py-12 text-center text-sm text-muted-foreground">No products found.</div>
          )}
        </CardContent>
      </Card>

      {/* Edit/Add Sheet */}
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
                value={formData.product_name}
                onChange={e => setFormData({ ...formData, product_name: e.target.value })}
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Category</label>
                <Input 
                  required 
                  value={formData.category}
                  onChange={e => setFormData({ ...formData, category: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Brand</label>
                <Input 
                  required 
                  value={formData.brand}
                  onChange={e => setFormData({ ...formData, brand: e.target.value })}
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
                  onChange={e => setFormData({ ...formData, price: parseFloat(e.target.value) })}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Quantity</label>
                <Input 
                  type="number" 
                  required 
                  value={formData.stock_quantity}
                  onChange={e => setFormData({ ...formData, stock_quantity: parseInt(e.target.value) })}
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Warehouse Location</label>
              <Input 
                value={formData.warehouse_location}
                onChange={e => setFormData({ ...formData, warehouse_location: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Supplier</label>
              <Input 
                value={formData.supplier}
                onChange={e => setFormData({ ...formData, supplier: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Description</label>
              <Textarea 
                className="h-24 resize-none"
                value={formData.description}
                onChange={e => setFormData({ ...formData, description: e.target.value })}
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
