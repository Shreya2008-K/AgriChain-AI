// Backend URL comes from VITE_API_URL. The localhost fallback applies to `vite dev` only, never to production builds.
const BASE = ((import.meta.env.VITE_API_URL as string | undefined) ||
  (import.meta.env.DEV ? "http://127.0.0.1:8000" : "")).replace(/\/$/, "");
export const API_CONFIGURED = BASE !== "";
const TOKEN_KEY = "agrichain_token";
export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (t: string | null) => (t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY));

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) { super(message); this.status = status; }
}

function formatDetail(detail: any): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => `${(d.loc || []).slice(1).join(".")}: ${d.msg}`).join("; ");
  return "Request failed";
}

export async function api<T = any>(path: string, opts: { method?: string; body?: any } = {}): Promise<T> {
  if (!API_CONFIGURED) throw new ApiError("VITE_API_URL is not configured for this build", 0);
  const headers: Record<string, string> = {};
  const t = getToken();
  if (t) headers.Authorization = `Bearer ${t}`;
  const hasBody = opts.body !== undefined;
  if (hasBody) headers["Content-Type"] = "application/json";
  let res: Response;
  try {
    res = await fetch(`${BASE}/api/v1${path}`, {
      method: opts.method || (hasBody ? "POST" : "GET"), headers, body: hasBody ? JSON.stringify(opts.body) : undefined,
    });
  } catch {
    throw new ApiError("Cannot reach the server. Is the backend running?", 0);
  }
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(formatDetail(data?.detail), res.status);
  return data as T;
}

export const money = (n: number) => "₹" + Number(n ?? 0).toLocaleString("en-IN");
export const label = (s: string) => (s || "").toLowerCase().replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
export const fmtDate = (s?: string) => {
  if (!s) return "—";
  const iso = /[zZ]$|[+-]\d\d:?\d\d$/.test(s) ? s : s + "Z"; // backend timestamps are UTC
  return new Date(iso).toLocaleString();
};
