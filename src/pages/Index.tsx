import { useState, useEffect } from "react";
import { Package, DollarSign, AlertTriangle, TrendingUp, ArrowUpRight, ArrowDownRight } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";
import { fetchStats, fetchInventory } from "@/lib/api";

const CHART_COLORS = [
  "hsl(217, 70%, 45%)",
  "hsl(162, 60%, 40%)",
  "hsl(38, 92%, 50%)",
  "hsl(280, 60%, 55%)",
  "hsl(0, 72%, 55%)",
];

type Stats = {
  totalProducts: number;
  totalValue: number;
  lowStock: number;
};

type InventoryItem = {
  product_id: number;
  category: string;
  price: number;
  stock_quantity: number;
};

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [inventory, setInventory] = useState<InventoryItem[]>([]);

  useEffect(() => {
    fetchStats().then(setStats).catch(console.error);
    fetchInventory().then(setInventory).catch(console.error);
  }, []);

  const totalUnits = inventory.reduce((s, p) => s + p.stock_quantity, 0);

  const categories = Array.from(new Set(inventory.map(p => p.category)));
  const categoryData = categories.map(c => {
    const productsInCat = inventory.filter(p => p.category === c);
    return {
      name: c,
      value: productsInCat.reduce((s, p) => s + p.price * p.stock_quantity, 0),
    };
  }).filter(c => c.value > 0);

  const pieData = categoryData.map(c => ({ name: c.name, value: Math.round(c.value) }));

  const statCards = [
    { label: "Total Products", value: stats?.totalProducts ?? 0, icon: Package, change: "+New", up: true },
    { label: "Total Value", value: `$${((stats?.totalValue ?? 0) / 1000).toFixed(1)}K`, icon: DollarSign, change: "Live", up: true },
    { label: "Low Stock Items", value: stats?.lowStock ?? 0, icon: AlertTriangle, change: `${stats?.lowStock ?? 0}`, up: false },
    { label: "Total Units", value: totalUnits.toLocaleString(), icon: TrendingUp, change: "Live", up: true },
  ];

  return (
    <div className="space-y-6 animate-slide-in">
      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((stat) => (
          <Card key={stat.label} className="glass-card stat-glow">
            <CardContent className="p-5">
              <div className="flex items-center justify-between mb-3">
                <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  <stat.icon className="w-5 h-5 text-primary" />
                </div>
                <span className={`flex items-center gap-0.5 text-xs font-medium ${stat.up ? "text-success" : "text-destructive"}`}>
                  {stat.up ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                  {stat.change}
                </span>
              </div>
              <p className="text-2xl font-bold text-foreground">{stat.value}</p>
              <p className="text-xs text-muted-foreground mt-1">{stat.label}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="glass-card lg:col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">Inventory Value by Category</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={categoryData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(220, 15%, 90%)" />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} angle={-35} textAnchor="end" height={60} />
                  <YAxis tick={{ fontSize: 11 }} tickFormatter={v => `$${(v / 1000).toFixed(0)}K`} />
                  <Tooltip formatter={(v: number) => [`$${v.toLocaleString()}`, "Value"]} />
                  <Bar dataKey="value" fill="hsl(217, 70%, 45%)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">Category Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={3} dataKey="value">
                    {pieData.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
                  </Pie>
                  <Tooltip formatter={(v: number) => `$${v.toLocaleString()}`} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
