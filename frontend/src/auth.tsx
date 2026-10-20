import { createContext, useContext, useEffect, useState } from "react";
import { api, getToken, setToken } from "./api";

const Ctx = createContext<any>(null);

export function AuthProvider({ children }: any) {
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(!!getToken());

  useEffect(() => {
    if (!getToken()) { setLoading(false); return; }
    api("/auth/me").then(setUser).catch(() => setToken(null)).finally(() => setLoading(false));
  }, []);

  const finish = (r: any) => { setToken(r.access_token); setUser(r.user); return r.user; };
  const login = async (email: string, password: string) => finish(await api("/auth/login", { body: { email, password } }));
  const register = async (body: any) => finish(await api("/auth/register", { body }));
  const logout = async () => {
    try { await api("/auth/logout", { method: "POST" }); } catch { /* token is discarded regardless */ }
    setToken(null); setUser(null);
  };
  return <Ctx.Provider value={{ user, loading, login, register, logout }}>{children}</Ctx.Provider>;
}
export const useAuth = () => useContext(Ctx);
