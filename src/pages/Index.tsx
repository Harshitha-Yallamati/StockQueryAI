import { useState, useEffect } from "react";
import { Package, DollarSign, AlertTriangle, TrendingUp, ArrowUpRight, ArrowDownRight } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/contexts/AuthContext";
import { fetchStats, fetchInventory } from "@/lib/api";
import type { DashboardStats, Product } from "@/lib/types";


const CHART_COLORS = [
  "hsl(217, 70%, 45%)",
  "hsl(162, 60%, 40%)",
  "hsl(38, 92%, 50%)",
  "hsl(280, 60%, 55%)",
  "hsl(0, 72%, 55%)",
];


export default function Dashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [inventory, setInventory] = useState<Product[]>([]);

  useEffect(() => {
    fetchStats().then(setStats).catch(console.error);
    fetchInventory().then(setInventory).catch(console.error);
  }, []);

  const totalUnits = inventory.reduce((sum, product) => sum + product.quantity, 0);

  const categories = Array.from(new Set(inventory.map(product => product.category)));
  const allCategoryData = categories
    .map(category => {
      const productsInCategory = inventory.filter(product => product.category === category);
      return {
        name: category,
        value: productsInCategory.reduce((sum, product) => sum + product.price * product.quantity, 0),
      };
    })
    .filter(category => category.value > 0)
    .sort((left, right) => right.value - left.value);

  const topCategories = allCategoryData.slice(0, 10);
  const pieData =
    allCategoryData.length > 8
      ? [
          ...allCategoryData.slice(0, 7).map(category => ({ name: category.name, value: Math.round(category.value) })),
          {
            name: "Others",
            value: Math.round(allCategoryData.slice(7).reduce((sum, category) => sum + category.value, 0)),
          },
        ]
      : allCategoryData.map(category => ({ name: category.name, value: Math.round(category.value) }));

  const statCards = [
    { label: "Total Products", value: stats?.totalProducts ?? 0, icon: Package, change: "Live", up: true },
    { label: "Inventory Value", value: `$${(stats?.totalValue ?? 0).toLocaleString()}`, icon: DollarSign, change: "Current", up: true },
    { label: "Low Stock Items", value: stats?.lowStock ?? 0, icon: AlertTriangle, change: `${stats?.lowStock ?? 0} Alerts`, up: false },
    { label: "Total Units", value: totalUnits.toLocaleString(), icon: TrendingUp, change: "Active", up: true },
  ];

  return (
    <div className="space-y-6 animate-slide-in">
      <Card className="glass-card bg-primary/5 border-primary/20">
        <CardContent className="p-6 flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-foreground">Welcome back, {user?.name || user?.email || "User"}!</h2>
            <p className="text-sm text-muted-foreground mt-1">Here&apos;s what&apos;s happening with your inventory today.</p>
          </div>
          <div className="hidden sm:block">
            <div className="w-14 h-14 rounded-full bg-primary/10 flex items-center justify-center border border-primary/20 shadow-sm overflow-hidden">
              {user?.picture ? (
                <img src={user.picture} alt="Profile" className="w-full h-full object-cover" />
              ) : (
                <span className="text-primary font-bold text-xl">
                  {(user?.name ? user.name[0] : user?.email?.[0] || "U").toUpperCase()}
                </span>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map(stat => (
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

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="glass-card lg:col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Top 10 Categories by Value</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={topCategories} margin={{ top: 5, right: 30, left: 10, bottom: 40 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(220, 15%, 90%)" />
                  <XAxis dataKey="name" tick={{ fontSize: 10 }} angle={-30} textAnchor="end" height={60} interval={0} />
                  <YAxis tick={{ fontSize: 11 }} tickFormatter={value => `$${(value / 1000).toFixed(0)}K`} />
                  <Tooltip formatter={(value: number) => [`$${value.toLocaleString()}`, "Estimated Value"]} cursor={{ fill: "hsl(var(--primary) / 0.05)" }} />
                  <Bar dataKey="value" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Inventory Breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={pieData} cx="50%" cy="50%" innerRadius={60} outerRadius={85} paddingAngle={2} dataKey="value">
                    {pieData.map((_, index) => <Cell key={index} fill={CHART_COLORS[index % CHART_COLORS.length]} stroke="transparent" />)}
                  </Pie>
                  <Tooltip formatter={(value: number) => `$${value.toLocaleString()}`} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
