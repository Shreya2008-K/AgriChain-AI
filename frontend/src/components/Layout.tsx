import { useEffect, useState } from "react";
import { NavLink, Link, Outlet, useNavigate } from "react-router-dom";
import { LayoutDashboard, Sprout, Tag, FileText, Truck, ClipboardCheck, Store, LineChart, LogOut, Menu, X, Leaf, ShieldCheck, Users, Landmark, Umbrella, Package, Bell, BarChart3, FlaskConical } from "lucide-react";
import { api } from "../api";
import { useAuth } from "../auth";
import { Badge } from "./ui";
import { label } from "../api";

const DASH = { to: "/app", label: "Dashboard", icon: LayoutDashboard, end: true };
const OFFERS = { to: "/app/offers", label: "Offers", icon: Tag };
const AGR = { to: "/app/agreements", label: "Agreements", icon: FileText };
const DEL = { to: "/app/deliveries", label: "Deliveries", icon: Truck };
const BATCH = { to: "/app/batches", label: "Crop batches", icon: Sprout };
const SUST = { to: "/app/sustainability", label: "Sustainability", icon: Leaf };
const PERM = { to: "/app/permissions", label: "Data permissions", icon: ShieldCheck };
const COOP = { to: "/app/cooperative", label: "Cooperative", icon: Users };
const AGRO = { to: "/app/agronomy", label: "Agronomy", icon: FlaskConical };
const LEND = { to: "/app/lending", label: "Lending", icon: Landmark };
const INS = { to: "/app/insurance", label: "Insurance", icon: Umbrella };
const SUP = { to: "/app/suppliers", label: "Supplier products", icon: Package };
const NAV: any = {
  farmer: [DASH, BATCH, OFFERS, AGR, DEL, SUST, PERM, COOP, AGRO, LEND, INS, SUP],
  buyer: [DASH, { to: "/marketplace", label: "Marketplace", icon: Store }, OFFERS, AGR, DEL, SUP],
  quality_verifier: [DASH, { to: "/app/queue", label: "Verification queue", icon: ClipboardCheck }, SUST],
  transporter: [DASH, DEL],
  admin: [DASH, BATCH, OFFERS, AGR, DEL, { to: "/app/admin", label: "Administration", icon: ShieldCheck }],
  cooperative: [DASH, COOP], agronomist: [DASH, AGRO], supplier: [DASH, SUP],
  lender: [DASH, LEND, PERM], insurer: [DASH, INS, PERM],
};

export default function Layout() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const items = [...(NAV[user.role] || [DASH]), { to: "/analytics", label: "Market analytics", icon: BarChart3 }, { to: "/predict", label: "Price prediction", icon: LineChart }];

  useEffect(() => {
    const load = () => api("/notifications").then((r: any) => setUnread(r.unread)).catch(() => {});
    load();
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, []);

  const sidebar = (
    <nav className="flex h-full flex-col overflow-y-auto bg-forest text-white">
      <Link to="/" className="flex items-center gap-2 px-5 py-5 text-lg font-semibold"><Leaf className="h-5 w-5" /> AgriChain AI</Link>
      <div className="flex-1 space-y-1 px-3">
        {items.map((it: any) => (
          <NavLink key={it.to} to={it.to} end={it.end} onClick={() => setOpen(false)}
            className={({ isActive }) => `flex items-center gap-3 rounded-md px-3 py-2 text-sm ${isActive ? "bg-white/15 font-medium" : "text-white/80 hover:bg-white/10"}`}>
            <it.icon className="h-4 w-4" /> {it.label}
          </NavLink>
        ))}
      </div>
      <p className="px-5 py-4 text-xs text-white/60">Demonstration build. Ledger records are simulated.</p>
    </nav>
  );

  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-60 shrink-0 md:block">{sidebar}</aside>
      {open && (
        <div className="fixed inset-0 z-40 flex md:hidden">
          <div className="w-64">{sidebar}</div>
          <button className="flex-1 bg-black/40" onClick={() => setOpen(false)} aria-label="Close menu" />
        </div>
      )}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3">
          <button className="md:hidden" onClick={() => setOpen(!open)} aria-label="Menu">{open ? <X /> : <Menu />}</button>
          <div className="hidden md:block" />
          <div className="flex items-center gap-3">
            <Link to="/app/notifications" className="relative rounded-md p-2 text-slate-600 hover:bg-slate-100" aria-label="Notifications">
              <Bell className="h-4 w-4" />
              {unread > 0 && <span className="absolute -right-0.5 -top-0.5 rounded-full bg-amber-500 px-1.5 text-[10px] font-semibold text-white">{unread}</span>}
            </Link>
            <div className="hidden text-right text-sm leading-tight sm:block">
              <p className="font-medium">{user.name}</p>
              <p className="text-xs text-slate-500">{user.email}</p>
            </div>
            <Badge status="REGISTERED" text={label(user.role)} />
            <button onClick={async () => { await logout(); nav("/"); }} className="rounded-md p-2 text-slate-600 hover:bg-slate-100" aria-label="Log out">
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </header>
        <main className="flex-1 p-4 md:p-8"><Outlet /></main>
      </div>
    </div>
  );
}
