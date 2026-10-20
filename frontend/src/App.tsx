import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./auth";
import Layout from "./components/Layout";
import PublicLayout from "./components/PublicLayout";
import { Loading } from "./components/ui";
import { Landing, MarketList, MarketDetail, Predict, Login, Register } from "./pages/Public";
import { Dashboard, Batches, BatchDetail, Offers, Agreements, Deliveries, Queue } from "./pages/Workspace";
import { Notifications, Sustainability, Permissions, Cooperative, Agronomy, Suppliers, Lending, Insurance, Admin, Analytics } from "./pages/More";

function Protected({ children }: any) {
  const { user, loading } = useAuth();
  const loc = useLocation();
  if (loading) return <div className="p-8"><Loading /></div>;
  if (!user) return <Navigate to="/login" state={{ from: loc.pathname }} replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route path="/" element={<Landing />} />
        <Route path="/marketplace" element={<MarketList />} />
        <Route path="/marketplace/:id" element={<MarketDetail />} />
        <Route path="/predict" element={<Predict />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
      </Route>
      <Route path="/app" element={<Protected><Layout /></Protected>}>
        <Route index element={<Dashboard />} />
        <Route path="batches" element={<Batches />} />
        <Route path="batches/:id" element={<BatchDetail />} />
        <Route path="offers" element={<Offers />} />
        <Route path="agreements" element={<Agreements />} />
        <Route path="deliveries" element={<Deliveries />} />
        <Route path="queue" element={<Queue />} />
        <Route path="notifications" element={<Notifications />} />
        <Route path="sustainability" element={<Sustainability />} />
        <Route path="permissions" element={<Permissions />} />
        <Route path="cooperative" element={<Cooperative />} />
        <Route path="agronomy" element={<Agronomy />} />
        <Route path="suppliers" element={<Suppliers />} />
        <Route path="lending" element={<Lending />} />
        <Route path="insurance" element={<Insurance />} />
        <Route path="admin" element={<Admin />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
