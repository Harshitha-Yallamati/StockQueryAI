import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { LayoutDashboard, MessageSquare, Package, AlertTriangle, Menu, X, Brain } from "lucide-react";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/chat", icon: MessageSquare, label: "AI Chat" },
  { to: "/products", icon: Package, label: "Products" },
  { to: "/alerts", icon: AlertTriangle, label: "Alerts" },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);

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
          <div className="w-9 h-9 rounded-lg bg-primary flex items-center justify-center">
            <Brain className="w-5 h-5 text-primary-foreground" />
          </div>
          <div>
            <h1 className="text-sm font-semibold text-sidebar-accent-foreground">StockQuery AI</h1>
            <p className="text-xs text-sidebar-foreground">Inventory Intelligence</p>
          </div>
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

        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-sidebar-border">
          <div className="px-3 py-2 rounded-lg bg-sidebar-accent">
            <p className="text-xs font-medium text-sidebar-accent-foreground">AI Agent Active</p>
            <p className="text-xs text-sidebar-foreground mt-0.5">Ready for queries</p>
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
