import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { Loader2, X, CheckCircle2, AlertCircle } from "lucide-react";
import { api, label, fmtDate } from "../api";

export const inputCls =
  "w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm focus:border-forest focus:outline-none focus:ring-1 focus:ring-forest";

export function Button({ variant = "primary", loading = false, className = "", children, ...rest }: any) {
  const v: any = {
    primary: "bg-forest text-white hover:bg-forest-700",
    secondary: "bg-white text-forest border border-forest/30 hover:bg-forest-50",
    danger: "bg-red-600 text-white hover:bg-red-700",
  };
  return (
    <button {...rest} disabled={loading || rest.disabled}
      className={`inline-flex items-center justify-center gap-2 rounded-md px-3.5 py-2 text-sm font-medium transition disabled:opacity-60 ${v[variant]} ${className}`}>
      {loading && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  );
}

const TONES: any = {
  green: "bg-emerald-50 text-emerald-800 ring-emerald-200", amber: "bg-amber-50 text-amber-800 ring-amber-200",
  red: "bg-red-50 text-red-800 ring-red-200", grey: "bg-slate-100 text-slate-700 ring-slate-200",
};
const STATUS_TONE: any = {
  LISTED: "green", QUALITY_VERIFIED: "green", ACCEPTED: "green", DELIVERED: "green", COMPLETED: "green", SOLD: "green",
  OFFER_ACCEPTED: "green", PENDING: "amber", QUALITY_PENDING: "amber", HARVEST_RECORDED: "amber", ACTIVE: "amber",
  PICKED_UP: "amber", IN_TRANSIT: "amber", SIMULATED: "amber", REGISTERED: "grey", WITHDRAWN: "grey",
  REJECTED: "red", QUALITY_REJECTED: "red",
};
export function Badge({ status, text }: any) {
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${TONES[STATUS_TONE[status] || "grey"]}`}>
      {text || label(status)}
    </span>
  );
}

export const Card = ({ children, className = "" }: any) => (
  <div className={`rounded-lg border border-slate-200 bg-white p-5 shadow-sm ${className}`}>{children}</div>
);

export function PageHeader({ title, desc, action }: any) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 className="text-2xl font-semibold text-forest">{title}</h1>
        {desc && <p className="mt-1 text-sm text-slate-600">{desc}</p>}
      </div>
      {action}
    </div>
  );
}

export function Kpi({ label: l, value, hint }: any) {
  return (
    <Card>
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{l}</p>
      <p className="mt-2 text-2xl font-semibold text-ink">{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </Card>
  );
}

export const Loading = () => (
  <div className="space-y-3" aria-busy="true">
    <div className="h-6 w-1/3 animate-pulse rounded bg-slate-200" />
    <div className="h-24 animate-pulse rounded bg-slate-200" />
    <div className="h-24 animate-pulse rounded bg-slate-200" />
  </div>
);
export const ErrorBox = ({ message }: any) => (
  <div className="flex items-start gap-2 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
    <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /> <span>{message}</span>
  </div>
);
export const Empty = ({ children }: any) => (
  <div className="rounded-lg border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">{children}</div>
);
export const Notice = ({ children }: any) => (
  <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">{children}</div>
);

export function Field({ label: l, help, children }: any) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-slate-700">{l}</span>
      {children}
      {help && <span className="mt-1 block text-xs text-slate-500">{help}</span>}
    </label>
  );
}

export function Modal({ title, onClose, children }: any) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal="true">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-forest">{title}</h2>
          <button onClick={onClose} aria-label="Close"><X className="h-5 w-5 text-slate-500" /></button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function Timeline({ events }: any) {
  return (
    <ol className="ml-3 space-y-5 border-l border-forest/25">
      {events.map((e: any, i: number) => (
        <li key={i} className="relative ml-5">
          <span className="absolute -ml-[26px] mt-1.5 h-2.5 w-2.5 rounded-full bg-forest" />
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium">{label(e.event_type || e.to_status)}</span>
            <Badge status={e.ledger_status} text={`${label(e.ledger_status)} ledger entry`} />
          </div>
          {e.note && <p className="text-sm text-slate-600">{e.note}</p>}
          <p className="text-xs text-slate-500">
            {fmtDate(e.created_at)} · {label(e.actor_role)} · <code className="break-all">{e.transaction_ref}</code>
          </p>
        </li>
      ))}
    </ol>
  );
}

export function useFetch<T = any>(path: string | null, deps: any[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(path !== null);
  const [n, setN] = useState(0);
  useEffect(() => {
    if (path === null) { setLoading(false); return; }
    let on = true;
    setLoading(true);
    api<T>(path).then((d) => { if (on) { setData(d); setError(null); } })
      .catch((e) => { if (on) setError(e.message); })
      .finally(() => { if (on) setLoading(false); });
    return () => { on = false; };
  }, [path, n, ...deps]);
  return { data, error, loading, reload: () => setN((x) => x + 1) };
}

const ToastCtx = createContext<any>(null);
export function ToastProvider({ children }: any) {
  const [items, setItems] = useState<any[]>([]);
  const push = useCallback((kind: string, msg: string) => {
    const id = Date.now() + Math.random();
    setItems((x) => [...x, { id, kind, msg }]);
    setTimeout(() => setItems((x) => x.filter((i) => i.id !== id)), 4500);
  }, []);
  const value = useMemo(() => ({ success: (m: string) => push("ok", m), error: (m: string) => push("err", m) }), [push]);
  return (
    <ToastCtx.Provider value={value}>
      {children}
      <div className="fixed bottom-4 right-4 z-[60] space-y-2">
        {items.map((t) => (
          <div key={t.id} className={`flex max-w-sm items-start gap-2 rounded-md px-4 py-3 text-sm text-white shadow-lg ${t.kind === "ok" ? "bg-forest" : "bg-red-600"}`}>
            {t.kind === "ok" ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" /> : <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />}
            {t.msg}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}
export const useToast = () => useContext(ToastCtx);

export const tableCls = { wrap: "overflow-x-auto rounded-lg border border-slate-200 bg-white", table: "w-full text-left text-sm",
  th: "bg-slate-50 px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-slate-500", td: "border-t border-slate-100 px-4 py-3 align-middle" };
