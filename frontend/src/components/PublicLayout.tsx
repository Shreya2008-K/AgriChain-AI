import { Link, Outlet } from "react-router-dom";
import { Leaf } from "lucide-react";
import { useAuth } from "../auth";
import { Button } from "./ui";

export default function PublicLayout() {
  const { user } = useAuth();
  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <Link to="/" className="flex items-center gap-2 text-lg font-semibold text-forest"><Leaf className="h-5 w-5" /> AgriChain AI</Link>
          <nav className="flex items-center gap-4 text-sm">
            <Link to="/marketplace" className="hover:text-forest">Marketplace</Link>
            <Link to="/analytics" className="hover:text-forest">Analytics</Link>
            <Link to="/predict" className="hover:text-forest">Price prediction</Link>
            {user ? (
              <Link to="/app"><Button>Open workspace</Button></Link>
            ) : (
              <>
                <Link to="/login" className="hover:text-forest">Log in</Link>
                <Link to="/register"><Button>Get started</Button></Link>
              </>
            )}
          </nav>
        </div>
      </header>
      <main className="flex-1"><Outlet /></main>
      <footer className="border-t border-slate-200 bg-white py-6 text-center text-xs text-slate-500">
        AgriChain AI is a student demonstration project. Ledger entries are simulated, prices come from synthetic demo data, and no real payments are made.
      </footer>
    </div>
  );
}
