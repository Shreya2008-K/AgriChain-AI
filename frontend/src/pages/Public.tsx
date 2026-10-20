import { useState } from "react";
import { Link, useNavigate, useParams, useLocation } from "react-router-dom";
import { ShieldCheck, LineChart, Sprout, Search } from "lucide-react";
import { api, label, money, fmtDate } from "../api";
import { useAuth } from "../auth";
import { Button, Card, Badge, Field, inputCls, useFetch, Loading, ErrorBox, Empty, Notice, Timeline, PageHeader, useToast } from "../components/ui";

export function Landing() {
  return (
    <div>
      <section className="bg-forest text-white">
        <div className="mx-auto max-w-6xl px-4 py-20">
          <h1 className="max-w-2xl text-4xl font-semibold leading-tight">Sell and source crops with a traceable history from farm to market.</h1>
          <p className="mt-4 max-w-xl text-white/80">
            AgriChain AI connects farmers and buyers directly, records each step of a crop batch's journey, and offers an indicative price estimate to inform negotiation.
          </p>
          <div className="mt-8 flex gap-3">
            <Link to="/marketplace"><Button variant="secondary">Explore Marketplace</Button></Link>
            <Link to="/register"><Button className="bg-leaf hover:bg-leaf/90">Get Started</Button></Link>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-14">
        <h2 className="text-2xl font-semibold text-forest">How it works</h2>
        <div className="mt-6 grid gap-4 md:grid-cols-4">
          {[["1. Register", "A farmer registers a crop batch and records the harvest."], ["2. Verify", "A quality verifier reviews the batch and approves or rejects it with a reason."],
            ["3. Trade", "Approved batches are listed. Buyers inspect the history and make offers."], ["4. Deliver", "Accepted offers become agreements. Transporters record custody until delivery."]].map(([t, d]) => (
            <Card key={t}><p className="font-medium text-forest">{t}</p><p className="mt-2 text-sm text-slate-600">{d}</p></Card>
          ))}
        </div>
      </section>

      <section className="mx-auto grid max-w-6xl gap-4 px-4 pb-14 md:grid-cols-3">
        <Card><ShieldCheck className="h-5 w-5 text-forest" /><h3 className="mt-2 font-medium">Traceability</h3>
          <p className="mt-1 text-sm text-slate-600">Every lifecycle event gets a hashed ledger entry. In this build the ledger is a local simulator, clearly labelled. A ledger entry shows that a change was recorded; it does not prove a crop claim is physically true.</p></Card>
        <Card><LineChart className="h-5 w-5 text-forest" /><h3 className="mt-2 font-medium">Price estimates</h3>
          <p className="mt-1 text-sm text-slate-600">A machine-learning model gives an indicative price and an uncertainty range. It is trained on synthetic demonstration data, not live market prices.</p></Card>
        <Card><Sprout className="h-5 w-5 text-forest" /><h3 className="mt-2 font-medium">What is built so far</h3>
          <p className="mt-1 text-sm text-slate-600">Working workflows exist for farmers, buyers, quality verifiers and transporters. Other roles (cooperative, agronomist, supplier, lender, insurer) and sustainability features are planned, not yet built.</p></Card>
      </section>
    </div>
  );
}

export function MarketList() {
  const [crop, setCrop] = useState(""); const [region, setRegion] = useState(""); const [max, setMax] = useState("");
  const [query, setQuery] = useState("");
  const { data, error, loading } = useFetch<any[]>(`/marketplace${query}`);
  const apply = (e: any) => {
    e.preventDefault();
    const p = new URLSearchParams();
    if (crop.trim()) p.set("crop", crop.trim()); if (region.trim()) p.set("region", region.trim()); if (max) p.set("max_price", max);
    setQuery(p.toString() ? "?" + p.toString() : "");
  };
  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <PageHeader title="Crop marketplace" desc="Verified batches listed for sale. Browsing is open; making an offer requires a buyer account." />
      <form onSubmit={apply} className="mb-6 grid gap-3 rounded-lg border border-slate-200 bg-white p-4 md:grid-cols-4">
        <input className={inputCls} placeholder="Crop (e.g. rice)" value={crop} onChange={(e) => setCrop(e.target.value)} />
        <input className={inputCls} placeholder="Region (e.g. tamil_nadu)" value={region} onChange={(e) => setRegion(e.target.value)} />
        <input className={inputCls} type="number" min="0" placeholder="Max price per unit (₹)" value={max} onChange={(e) => setMax(e.target.value)} />
        <Button type="submit"><Search className="h-4 w-4" /> Apply filters</Button>
      </form>
      {loading ? <Loading /> : error ? <ErrorBox message={error} /> : !data?.length ? <Empty>No listings match these filters.</Empty> : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.map((b) => (
            <Link key={b.id} to={`/marketplace/${b.id}`}>
              <Card className="h-full transition hover:border-forest/40">
                <div className="flex items-center justify-between"><h3 className="text-lg font-medium capitalize">{b.crop}</h3><Badge status="LISTED" text="Quality reviewed" /></div>
                <p className="text-sm text-slate-500">{b.variety || "Variety not stated"} · {label(b.region)}</p>
                <p className="mt-3 text-xl font-semibold text-forest">{money(b.asking_price)} <span className="text-xs font-normal text-slate-500">per {b.unit}</span></p>
                <p className="mt-1 text-sm text-slate-600">{b.available_quantity} {b.unit} available</p>
                <p className="mt-1 text-xs text-slate-500">Farmer: {b.farmer}</p>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export function MarketDetail() {
  const { id } = useParams(); const { user } = useAuth(); const nav = useNavigate(); const toast = useToast();
  const { data: b, error, loading, reload } = useFetch<any>(`/marketplace/${id}`);
  const [busy, setBusy] = useState(false);
  if (loading) return <div className="mx-auto max-w-4xl px-4 py-10"><Loading /></div>;
  if (error) return <div className="mx-auto max-w-4xl px-4 py-10"><ErrorBox message={error} /></div>;

  const submit = async (e: any) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setBusy(true);
    try {
      await api("/offers", { body: { batch_id: b.id, quantity: Number(f.get("quantity")), price_per_unit: Number(f.get("price")) } });
      toast.success("Offer submitted. The farmer will review it.");
      nav("/app/offers");
    } catch (err: any) { toast.error(err.message); reload(); } finally { setBusy(false); }
  };

  return (
    <div className="mx-auto grid max-w-5xl gap-6 px-4 py-10 md:grid-cols-5">
      <div className="space-y-6 md:col-span-3">
        <Card>
          <h1 className="text-2xl font-semibold capitalize text-forest">{b.crop} <span className="text-base font-normal text-slate-500">{b.variety}</span></h1>
          <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
            <div><dt className="text-slate-500">Region</dt><dd>{label(b.region)}</dd></div>
            <div><dt className="text-slate-500">Harvest date</dt><dd>{b.harvest_date || "—"}</dd></div>
            <div><dt className="text-slate-500">Available</dt><dd>{b.available_quantity} of {b.quantity} {b.unit}</dd></div>
            <div><dt className="text-slate-500">Asking price</dt><dd>{money(b.asking_price)} per {b.unit}</dd></div>
            <div><dt className="text-slate-500">Farmer</dt><dd>{b.farmer}</dd></div>
          </dl>
        </Card>
        <Card>
          <h2 className="mb-3 text-lg font-medium">Provenance</h2>
          <div className="mb-4"><Notice>{b.notice}</Notice></div>
          <Timeline events={b.provenance} />
        </Card>
      </div>
      <div className="md:col-span-2">
        <Card>
          <h2 className="mb-3 text-lg font-medium">Make an offer</h2>
          {!user ? (
            <p className="text-sm text-slate-600">Please <Link className="text-forest underline" to="/login" state={{ from: `/marketplace/${b.id}` }}>log in</Link> as a buyer to make an offer.</p>
          ) : user.role !== "buyer" ? (
            <p className="text-sm text-slate-600">Only buyer accounts can make offers. You are signed in as {label(user.role)}.</p>
          ) : (
            <form onSubmit={submit} className="space-y-4">
              <Field label={`Quantity (${b.unit})`} help={`Up to ${b.available_quantity}`}><input name="quantity" required type="number" min="0.01" max={b.available_quantity} step="any" className={inputCls} /></Field>
              <Field label={`Price per ${b.unit} (₹)`}><input name="price" required type="number" min="0.01" step="any" defaultValue={b.asking_price} className={inputCls} /></Field>
              <Notice>Simulated purchase: no real payment is collected.</Notice>
              <Button type="submit" loading={busy} className="w-full">Submit offer</Button>
            </form>
          )}
        </Card>
      </div>
    </div>
  );
}

export function Predict() {
  const opts = useFetch<any>("/predictions/options");
  const [res, setRes] = useState<any>(null); const [err, setErr] = useState<string | null>(null); const [busy, setBusy] = useState(false);
  if (opts.loading) return <div className="mx-auto max-w-4xl px-4 py-10"><Loading /></div>;
  if (opts.error) return <div className="mx-auto max-w-4xl px-4 py-10"><ErrorBox message={opts.error} /></div>;
  const o = opts.data;

  const submit = async (e: any) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setBusy(true); setErr(null);
    try {
      const r = await api("/predictions", { body: { crop: f.get("crop"), region: f.get("region"), month: Number(f.get("month")), supply: Number(f.get("supply")), horizon_months: Number(f.get("horizon")) } });
      setRes({ ...r, crop: f.get("crop"), region: f.get("region") });
    } catch (e2: any) { setErr(e2.message); setRes(null); } finally { setBusy(false); }
  };

  return (
    <div className="mx-auto grid max-w-5xl gap-6 px-4 py-10 md:grid-cols-2">
      <div>
        <PageHeader title="Price prediction" desc="Indicative estimate from a baseline model." />
        <Card>
          <form onSubmit={submit} className="space-y-4">
            <Field label="Crop"><select name="crop" className={inputCls}>{o.crops.map((c: string) => <option key={c} value={c}>{label(c)}</option>)}</select></Field>
            <Field label="Region"><select name="region" className={inputCls}>{o.regions.map((c: string) => <option key={c} value={c}>{label(c)}</option>)}</select></Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Target month (1-12)"><input name="month" type="number" min="1" max="12" defaultValue="6" required className={inputCls} /></Field>
              <Field label="Horizon (months)" help="1-12"><input name="horizon" type="number" min="1" max="12" defaultValue="1" required className={inputCls} /></Field>
            </div>
            <Field label="Expected supply (quintals)"><input name="supply" type="number" min="1" step="any" defaultValue="1000" required className={inputCls} /></Field>
            <Button type="submit" loading={busy} className="w-full">Estimate price</Button>
          </form>
        </Card>
      </div>
      <div className="space-y-4 md:pt-[72px]">
        {err && <ErrorBox message={err} />}
        {res ? (
          <Card>
            <div className="flex items-center justify-between"><p className="text-sm text-slate-500 capitalize">{res.crop} · {label(res.region)}</p><Badge status="SIMULATED" text="Synthetic demo data" /></div>
            <p className="mt-2 text-3xl font-semibold text-forest">{money(res.predicted_price)} <span className="text-sm font-normal text-slate-500">per {res.unit.replace("INR/", "")}</span></p>
            <p className="mt-2 text-sm">Estimated range (80%): <b>{money(res.range_80pct[0])}</b> – <b>{money(res.range_80pct[1])}</b></p>
            <p className="mt-1 text-xs text-slate-500">{res.range_method}</p>
            <p className="mt-3 text-xs text-slate-500">Data source: {res.data_source} · Holdout mean absolute error: {money(res.model_mae)}</p>
            <div className="mt-3"><Notice>{res.limitations} This is a demonstration, not a market forecast.</Notice></div>
          </Card>
        ) : !err && <Empty>Submit the form to see an estimate.</Empty>}
        <p className="text-xs text-slate-500">Evaluation: time-based holdout of {o.evaluation.holdout_rows} rows, mean absolute error {money(o.evaluation.mae)}. Source: {o.data_source}.</p>
      </div>
    </div>
  );
}

export function Login() {
  const { login } = useAuth(); const nav = useNavigate(); const loc: any = useLocation();
  const [busy, setBusy] = useState(false); const [err, setErr] = useState<string | null>(null);
  const [email, setEmail] = useState(""); const [password, setPassword] = useState("");
  const submit = async (e: any) => {
    e.preventDefault(); setBusy(true); setErr(null);
    try { await login(email, password); nav(loc.state?.from || "/app"); }
    catch (e2: any) { setErr(e2.message); } finally { setBusy(false); }
  };
  return (
    <div className="mx-auto max-w-md px-4 py-12">
      <Card>
        <h1 className="mb-4 text-xl font-semibold text-forest">Log in</h1>
        <form onSubmit={submit} className="space-y-4">
          <Field label="Email"><input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className={inputCls} /></Field>
          <Field label="Password"><input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} className={inputCls} /></Field>
          {err && <ErrorBox message={err} />}
          <Button type="submit" loading={busy} className="w-full">Log in</Button>
        </form>
        <p className="mt-4 text-sm text-slate-600">No account? <Link className="text-forest underline" to="/register">Register</Link></p>
      </Card>
      {import.meta.env.DEV && (
        <Card className="mt-4">
          <p className="text-xs font-medium uppercase text-slate-500">Local demo accounts (development only)</p>
          <p className="mt-1 text-xs text-slate-500">These only fill the form. Each account is still authenticated by the backend. Password: Demo@12345</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {["farmer", "buyer", "quality_verifier", "transporter", "admin"].map((r) => (
              <button key={r} type="button" className="rounded-md border border-slate-300 px-2 py-1 text-xs hover:bg-slate-50"
                onClick={() => { setEmail(`${r}@demo.agrichain.test`); setPassword("Demo@12345"); }}>{label(r)}</button>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

export function Register() {
  const { register } = useAuth(); const nav = useNavigate();
  const [busy, setBusy] = useState(false); const [err, setErr] = useState<string | null>(null);
  const roles = ["farmer", "buyer", "quality_verifier", "transporter", "cooperative", "agronomist", "supplier", "lender", "insurer"];
  const submit = async (e: any) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setBusy(true); setErr(null);
    try { await register({ name: f.get("name"), email: f.get("email"), password: f.get("password"), role: f.get("role") }); nav("/app"); }
    catch (e2: any) { setErr(e2.message); } finally { setBusy(false); }
  };
  return (
    <div className="mx-auto max-w-md px-4 py-12">
      <Card>
        <h1 className="mb-4 text-xl font-semibold text-forest">Create an account</h1>
        <form onSubmit={submit} className="space-y-4">
          <Field label="Full name"><input name="name" required minLength={2} className={inputCls} /></Field>
          <Field label="Email"><input name="email" type="email" required className={inputCls} /></Field>
          <Field label="Password" help="At least 8 characters"><input name="password" type="password" required minLength={8} className={inputCls} /></Field>
          <Field label="I am a" help="Workflows are currently built for farmers, buyers, quality verifiers and transporters.">
            <select name="role" className={inputCls}>{roles.map((r) => <option key={r} value={r}>{label(r)}</option>)}</select>
          </Field>
          {err && <ErrorBox message={err} />}
          <Button type="submit" loading={busy} className="w-full">Create account</Button>
        </form>
        <p className="mt-4 text-sm text-slate-600">Already registered? <Link className="text-forest underline" to="/login">Log in</Link></p>
      </Card>
    </div>
  );
}
