import { Link, useLocation } from "react-router-dom";
import { LayoutDashboard, MessageSquare, Package, AlertTriangle, Menu, X, LogOut, ShoppingCart } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "./ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "./ui/avatar";
import { useState } from "react";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/chat", icon: MessageSquare, label: "AI Chat" },
  { to: "/products", icon: Package, label: "Products" },
  { to: "/orders", icon: ShoppingCart, label: "Orders" },
  { to: "/alerts", icon: AlertTriangle, label: "Alerts" },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const { user, logout } = useAuth();

  const userInitials = user?.name
    ? user.name.split(' ').map(n => n[0]).join('').toUpperCase()
    : user?.email?.[0].toUpperCase() || "U";

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className={`
        fixed inset-y-0 left-0 z-50 w-64 bg-sidebar border-r border-sidebar-border
        transform transition-transform duration-200 ease-in-out
        lg:relative lg:translate-x-0
        ${mobileOpen ? "translate-x-0" : "-translate-x-full"}
      `}>
        <div className="flex items-center gap-3 px-6 py-5 border-b border-sidebar-border">
          <Link to="/" className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center p-1 border border-primary/20">
              <img src="/logo.svg" alt="StockQuery AI" className="w-full h-full object-contain" />
            </div>
            <div>
              <h1 className="text-sm font-semibold text-sidebar-accent-foreground">StockQuery AI</h1>
              <p className="text-xs text-sidebar-foreground">Inventory Intelligence</p>
            </div>
          </Link>
        </div>

        <nav className="p-3 space-y-1">
          {navItems.map(({ to, icon: Icon, label }) => {
            const active = location.pathname === to;
            return (
              <Link
                key={to}
                to={to}
                onClick={() => setMobileOpen(false)}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  active
                    ? "bg-sidebar-accent text-sidebar-primary"
                    : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                }`}
              >
                <Icon className="w-4.5 h-4.5" />
                {label}
              </Link>
            );
          })}
        </nav>

        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-sidebar-border bg-sidebar/50 backdrop-blur-sm">
          <div className="flex items-center gap-3 px-3 py-2">
            <Avatar className="h-9 w-9 border border-sidebar-border ring-2 ring-primary/10">
              <AvatarImage src={`https://avatar.vercel.sh/${user?.email}`} />
              <AvatarFallback className="bg-primary/10 text-primary text-xs font-bold">
                {userInitials}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-sidebar-accent-foreground truncate">
                {user?.name || "User Account"}
              </p>
              <p className="text-[10px] text-sidebar-foreground truncate uppercase tracking-wider">
                Authorized Access
              </p>
            </div>
            <Button 
              variant="ghost" 
              size="icon" 
              onClick={() => logout()}
              className="h-8 w-8 text-sidebar-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
              title="Logout"
            >
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </aside>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 bg-foreground/20 backdrop-blur-sm lg:hidden" onClick={() => setMobileOpen(false)} />
      )}

      {/* Main content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        <header className="flex items-center gap-3 px-4 py-3 border-b border-border bg-card lg:px-6">
          <button onClick={() => setMobileOpen(true)} className="lg:hidden p-1.5 rounded-md hover:bg-muted">
            <Menu className="w-5 h-5" />
          </button>
          <h2 className="text-sm font-semibold text-foreground">
            {navItems.find(n => n.to === location.pathname)?.label ?? "StockQuery AI"}
          </h2>
        </header>
        <div className="flex-1 overflow-auto p-4 lg:p-6">
          {children}
        </div>
      </main>
    </div>
  );
}
