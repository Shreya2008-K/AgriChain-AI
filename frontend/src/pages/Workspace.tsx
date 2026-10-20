import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, label, money, fmtDate } from "../api";
import { useAuth } from "../auth";
import { Button, Card, Badge, Field, Modal, inputCls, useFetch, Loading, ErrorBox, Empty, Notice, Timeline, PageHeader, Kpi, useToast, tableCls as T } from "../components/ui";

const count = (a: any[], f: (x: any) => boolean) => a.filter(f).length;

export function useAction(done: () => void) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const run = async (path: string, body?: any, msg = "Done") => {
    setBusy(true);
    try { await api(path, { method: "POST", body }); toast.success(msg); done(); return true; }
    catch (e: any) { toast.error(e.message); return false; } finally { setBusy(false); }
  };
  return { run, busy };
}

/* ---------------- Dashboards ---------------- */
export function Dashboard() {
  const { user } = useAuth();
  if (user.role === "farmer" || user.role === "admin") return <FarmerAdminDash />;
  if (user.role === "buyer") return <BuyerDash />;
  if (user.role === "quality_verifier") return <VerifierDash />;
  if (user.role === "transporter") return <TransporterDash />;
  const HOME: any = {
    cooperative: ["/app/cooperative", "Review membership requests from farmers."],
    agronomist: ["/app/agronomy", "Respond to field cases with observations and recommendations."],
    supplier: ["/app/suppliers", "Manage your product listings."],
    lender: ["/app/lending", "Review loan applications and shared farm reports."],
    insurer: ["/app/insurance", "Issue policies and review claims."],
  };
  const h = HOME[user.role];
  return (
    <div>
      <PageHeader title={`${label(user.role)} workspace`} desc={`Welcome, ${user.name}.`} action={h && <Link to={h[0]}><Button>Open workspace</Button></Link>} />
      <Card><p className="text-sm text-slate-600">{h ? h[1] : "Use the sidebar to get started."}</p></Card>
    </div>
  );
}

function FarmerAdminDash() {
  const { user } = useAuth();
  const b = useFetch<any[]>("/batches"), o = useFetch<any[]>("/offers"), a = useFetch<any[]>("/agreements");
  if (b.loading || o.loading || a.loading) return <Loading />;
  const err = b.error || o.error || a.error;
  if (err) return <ErrorBox message={err} />;
  const batches = b.data!, offers = o.data!, ags = a.data!;
  const byStatus: any = {}; batches.forEach((x) => (byStatus[x.status] = (byStatus[x.status] || 0) + 1));
  const chart = Object.entries(byStatus).map(([s, n]) => ({ status: label(s), count: n }));
  const available = batches.filter((x) => x.status === "LISTED").reduce((s, x) => s + (x.available_quantity || 0), 0);
  const pending = offers.filter((x) => x.status === "PENDING");
  return (
    <div>
      <PageHeader title={`Welcome, ${user.name}`} desc={user.role === "admin" ? "System-wide view of batches, offers and agreements." : "Your crop batches, offers and sales."}
        action={user.role === "farmer" && <Link to="/app/batches"><Button>Manage batches</Button></Link>} />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi label="Active batches" value={count(batches, (x) => !["SOLD", "QUALITY_REJECTED"].includes(x.status))} />
        <Kpi label="Quantity on sale" value={available} hint="Units still available in listed batches" />
        <Kpi label="Pending offers" value={pending.length} />
        <Kpi label="Agreements" value={ags.length} hint="Payments are simulated" />
      </div>
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card>
          <h2 className="mb-3 font-medium">Batches by status</h2>
          {chart.length === 0 ? <Empty>No batches yet.</Empty> : (
            <div className="h-56"><ResponsiveContainer width="100%" height="100%">
              <BarChart data={chart}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="status" tick={{ fontSize: 11 }} interval={0} /><YAxis allowDecimals={false} label={{ value: "Batches", angle: -90, position: "insideLeft", fontSize: 11 }} /><Tooltip /><Bar dataKey="count" fill="#1e4d36" /></BarChart>
            </ResponsiveContainer></div>
          )}
        </Card>
        <Card>
          <div className="mb-3 flex items-center justify-between"><h2 className="font-medium">Pending offers</h2><Link className="text-sm text-forest underline" to="/app/offers">View all</Link></div>
          {pending.length === 0 ? <Empty>No pending offers.</Empty> : pending.slice(0, 5).map((x) => (
            <div key={x.id} className="flex items-center justify-between border-t border-slate-100 py-2 text-sm first:border-0">
              <span className="capitalize">{x.crop} · {x.quantity} {x.unit}</span><span>{money(x.price_per_unit)}/{x.unit}</span>
            </div>
          ))}
        </Card>
      </div>
    </div>
  );
}

function BuyerDash() {
  const o = useFetch<any[]>("/offers"), a = useFetch<any[]>("/agreements"), d = useFetch<any[]>("/deliveries");
  if (o.loading || a.loading || d.loading) return <Loading />;
  const err = o.error || a.error || d.error; if (err) return <ErrorBox message={err} />;
  return (
    <div>
      <PageHeader title="Buyer dashboard" desc="Your offers, agreements and deliveries." action={<Link to="/marketplace"><Button>Browse marketplace</Button></Link>} />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi label="Pending offers" value={count(o.data!, (x) => x.status === "PENDING")} />
        <Kpi label="Accepted offers" value={count(o.data!, (x) => x.status === "ACCEPTED")} />
        <Kpi label="Agreements" value={a.data!.length} hint="Payments are simulated" />
        <Kpi label="Deliveries in progress" value={count(d.data!, (x) => x.status !== "DELIVERED")} />
      </div>
      <Card className="mt-6">
        <h2 className="mb-3 font-medium">Recent agreements</h2>
        {a.data!.length === 0 ? <Empty>No agreements yet. Make an offer on a listing.</Empty> : a.data!.slice(0, 5).map((x) => (
          <div key={x.id} className="flex items-center justify-between border-t border-slate-100 py-2 text-sm first:border-0">
            <span className="capitalize">#{x.id} · {x.crop} · {x.quantity} {x.unit}</span><Badge status={x.delivery_status} />
          </div>
        ))}
      </Card>
    </div>
  );
}

function VerifierDash() {
  const q = useFetch<any[]>("/verification/queue");
  if (q.loading) return <Loading />; if (q.error) return <ErrorBox message={q.error} />;
  return (
    <div>
      <PageHeader title="Quality verifier dashboard" desc="Review submitted batches." action={<Link to="/app/queue"><Button>Open queue</Button></Link>} />
      <div className="grid gap-4 sm:grid-cols-2"><Kpi label="Batches awaiting review" value={q.data!.length} /></div>
    </div>
  );
}

function TransporterDash() {
  const { user } = useAuth();
  const d = useFetch<any[]>("/deliveries");
  if (d.loading) return <Loading />; if (d.error) return <ErrorBox message={d.error} />;
  const rows = d.data!;
  return (
    <div>
      <PageHeader title="Transporter dashboard" desc="Available and assigned deliveries." action={<Link to="/app/deliveries"><Button>Open deliveries</Button></Link>} />
      <div className="grid gap-4 sm:grid-cols-3">
        <Kpi label="Unclaimed deliveries" value={count(rows, (x) => !x.transporter_id)} />
        <Kpi label="My active deliveries" value={count(rows, (x) => x.transporter_id === user.id && x.status !== "DELIVERED")} />
        <Kpi label="Delivered by me" value={count(rows, (x) => x.transporter_id === user.id && x.status === "DELIVERED")} />
      </div>
    </div>
  );
}

/* ---------------- Batches ---------------- */
const CROPS = ["rice", "wheat", "tomato", "maize"], REGIONS = ["tamil_nadu", "karnataka", "punjab"];

export function Batches() {
  const { user } = useAuth();
  const { data, error, loading, reload } = useFetch<any[]>("/batches");
  const [q, setQ] = useState(""); const [st, setSt] = useState("");
  const [modal, setModal] = useState<any>(null);
  const { run, busy } = useAction(() => { setModal(null); reload(); });
  const isFarmer = user.role === "farmer";
  if (loading) return <Loading />; if (error) return <ErrorBox message={error} />;
  const rows = data!.filter((b) => (!q || b.crop.includes(q.toLowerCase())) && (!st || b.status === st));
  const statuses = Array.from(new Set(data!.map((b) => b.status)));

  const form = (e: any) => { e.preventDefault(); return new FormData(e.currentTarget); };

  return (
    <div>
      <PageHeader title="Crop batches" desc="Register batches and move them through harvest, verification and listing."
        action={isFarmer && <Button onClick={() => setModal({ type: "create" })}>New batch</Button>} />
      <div className="mb-4 flex flex-wrap gap-3">
        <input className={`${inputCls} max-w-xs`} placeholder="Search crop" value={q} onChange={(e) => setQ(e.target.value)} />
        <select className={`${inputCls} max-w-xs`} value={st} onChange={(e) => setSt(e.target.value)}>
          <option value="">All statuses</option>{statuses.map((s: any) => <option key={s} value={s}>{label(s)}</option>)}
        </select>
      </div>
      {rows.length === 0 ? <Empty>{data!.length ? "No batches match your filters." : "No batches yet."}</Empty> : (
        <div className={T.wrap}><table className={T.table}>
          <thead><tr>{["ID", "Crop", "Region", "Quantity", "Status", "Actions"].map((h) => <th key={h} className={T.th}>{h}</th>)}</tr></thead>
          <tbody>{rows.map((b) => (
            <tr key={b.id}>
              <td className={T.td}>#{b.id}</td>
              <td className={`${T.td} capitalize`}>{b.crop}{b.variety ? ` (${b.variety})` : ""}</td>
              <td className={T.td}>{label(b.region)}</td>
              <td className={T.td}>{b.quantity} {b.unit}{b.available_quantity != null && b.status === "LISTED" ? ` (${b.available_quantity} left)` : ""}</td>
              <td className={T.td}><Badge status={b.status} /></td>
              <td className={`${T.td} space-x-2 whitespace-nowrap`}>
                <Link className="text-forest underline" to={`/app/batches/${b.id}`}>Provenance</Link>
                {isFarmer && b.status === "REGISTERED" && <Button variant="secondary" onClick={() => setModal({ type: "harvest", b })}>Record harvest</Button>}
                {isFarmer && b.status === "HARVEST_RECORDED" && <Button variant="secondary" loading={busy} onClick={() => run(`/batches/${b.id}/submit-verification`, undefined, "Submitted for verification")}>Submit for verification</Button>}
                {isFarmer && b.status === "QUALITY_VERIFIED" && <Button onClick={() => setModal({ type: "list", b })}>List for sale</Button>}
              </td>
            </tr>))}</tbody></table></div>
      )}

      {modal?.type === "create" && (
        <Modal title="Register a crop batch" onClose={() => setModal(null)}>
          <form className="space-y-3" onSubmit={(e) => { const f = form(e); run("/batches", { crop: f.get("crop"), variety: f.get("variety") || null, quantity: Number(f.get("quantity")), unit: f.get("unit"), expected_price: Number(f.get("price") || 0), region: f.get("region") }, "Batch registered"); }}>
            <Field label="Crop"><input name="crop" list="crops" required minLength={2} className={inputCls} /><datalist id="crops">{CROPS.map((c) => <option key={c} value={c} />)}</datalist></Field>
            <Field label="Variety (optional)"><input name="variety" className={inputCls} /></Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Quantity"><input name="quantity" type="number" min="0.01" step="any" required className={inputCls} /></Field>
              <Field label="Unit"><input name="unit" defaultValue="quintal" required className={inputCls} /></Field>
            </div>
            <Field label="Expected price per unit (₹)"><input name="price" type="number" min="0" step="any" className={inputCls} /></Field>
            <Field label="Region" help="Used for marketplace filtering"><input name="region" list="regions" required minLength={2} className={inputCls} /><datalist id="regions">{REGIONS.map((c) => <option key={c} value={c} />)}</datalist></Field>
            <Button type="submit" loading={busy} className="w-full">Register batch</Button>
          </form>
        </Modal>)}
      {modal?.type === "harvest" && (
        <Modal title={`Record harvest for batch #${modal.b.id}`} onClose={() => setModal(null)}>
          <form className="space-y-3" onSubmit={(e) => { const f = form(e); run(`/batches/${modal.b.id}/harvest`, { harvest_date: f.get("date"), note: f.get("note") || "" }, "Harvest recorded"); }}>
            <Field label="Harvest date"><input name="date" type="date" required className={inputCls} /></Field>
            <Field label="Note (optional)"><input name="note" maxLength={500} className={inputCls} /></Field>
            <Button type="submit" loading={busy} className="w-full">Save harvest</Button>
          </form>
        </Modal>)}
      {modal?.type === "list" && (
        <Modal title={`List batch #${modal.b.id} for sale`} onClose={() => setModal(null)}>
          <form className="space-y-3" onSubmit={(e) => { const f = form(e); run(`/batches/${modal.b.id}/list`, { asking_price: Number(f.get("price")) }, "Batch listed on the marketplace"); }}>
            <Field label={`Asking price per ${modal.b.unit} (₹)`}><input name="price" type="number" min="0.01" step="any" defaultValue={modal.b.expected_price || ""} required className={inputCls} /></Field>
            <Button type="submit" loading={busy} className="w-full">Publish listing</Button>
          </form>
        </Modal>)}
    </div>
  );
}

export function BatchDetail() {
  const { id } = useParams();
  const b = useFetch<any>(`/batches/${id}`), p = useFetch<any>(`/batches/${id}/provenance`);
  if (b.loading || p.loading) return <Loading />;
  if (b.error || p.error) return <ErrorBox message={b.error || p.error} />;
  const x = b.data;
  return (
    <div>
      <PageHeader title={`Batch #${x.id}: ${label(x.crop)}`} desc="Lifecycle and ledger history." action={<Badge status={x.status} />} />
      <div className="grid gap-6 lg:grid-cols-3">
        <Card>
          <dl className="space-y-2 text-sm">
            <div><dt className="text-slate-500">Quantity</dt><dd>{x.quantity} {x.unit}</dd></div>
            <div><dt className="text-slate-500">Region</dt><dd>{label(x.region)}</dd></div>
            <div><dt className="text-slate-500">Harvest date</dt><dd>{x.harvest_date || "—"}</dd></div>
            <div><dt className="text-slate-500">Asking price</dt><dd>{x.asking_price ? money(x.asking_price) : "—"}</dd></div>
            {x.rejection_reason && <div><dt className="text-slate-500">Rejection reason</dt><dd className="text-red-700">{x.rejection_reason}</dd></div>}
          </dl>
        </Card>
        <Card className="lg:col-span-2">
          <div className="mb-4"><Notice>{p.data.notice}</Notice></div>
          <Timeline events={p.data.events} />
        </Card>
      </div>
    </div>
  );
}

/* ---------------- Offers & agreements ---------------- */
export function Offers() {
  const { user } = useAuth();
  const { data, error, loading, reload } = useFetch<any[]>("/offers");
  const { run, busy } = useAction(reload);
  if (loading) return <Loading />; if (error) return <ErrorBox message={error} />;
  const farmer = user.role === "farmer", buyer = user.role === "buyer";
  return (
    <div>
      <PageHeader title="Offers" desc={farmer ? "Offers from buyers on your listed batches." : "Offers you have made."} />
      {data!.length === 0 ? <Empty>No offers yet.</Empty> : (
        <div className={T.wrap}><table className={T.table}>
          <thead><tr>{["ID", "Crop", "Quantity", "Price/unit", "Total", "Status", "Made", "Actions"].map((h) => <th key={h} className={T.th}>{h}</th>)}</tr></thead>
          <tbody>{data!.map((o) => (
            <tr key={o.id}>
              <td className={T.td}>#{o.id}</td><td className={`${T.td} capitalize`}>{o.crop}</td>
              <td className={T.td}>{o.quantity} {o.unit}</td><td className={T.td}>{money(o.price_per_unit)}</td>
              <td className={T.td}>{money(o.quantity * o.price_per_unit)}</td><td className={T.td}><Badge status={o.status} /></td>
              <td className={T.td}>{fmtDate(o.created_at)}</td>
              <td className={`${T.td} space-x-2 whitespace-nowrap`}>
                {farmer && o.status === "PENDING" && (<>
                  <Button loading={busy} onClick={() => window.confirm(`Accept this offer? This reserves ${o.quantity} ${o.unit} and creates an agreement (payment simulated).`) && run(`/offers/${o.id}/accept`, undefined, "Offer accepted. Agreement and delivery created.")}>Accept</Button>
                  <Button variant="danger" loading={busy} onClick={() => window.confirm("Reject this offer?") && run(`/offers/${o.id}/reject`, {}, "Offer rejected")}>Reject</Button>
                </>)}
                {buyer && o.status === "PENDING" && <Button variant="secondary" loading={busy} onClick={() => window.confirm("Withdraw this offer?") && run(`/offers/${o.id}/withdraw`, undefined, "Offer withdrawn")}>Withdraw</Button>}
              </td>
            </tr>))}</tbody></table></div>
      )}
    </div>
  );
}

export function Agreements() {
  const { data, error, loading } = useFetch<any[]>("/agreements");
  if (loading) return <Loading />; if (error) return <ErrorBox message={error} />;
  return (
    <div>
      <PageHeader title="Agreements" desc="Created when a farmer accepts an offer." />
      <div className="mb-4"><Notice>Payments are simulated. No money is collected or transferred.</Notice></div>
      {data!.length === 0 ? <Empty>No agreements yet.</Empty> : (
        <div className={T.wrap}><table className={T.table}>
          <thead><tr>{["ID", "Crop", "Quantity", "Price/unit", "Total", "Status", "Delivery"].map((h) => <th key={h} className={T.th}>{h}</th>)}</tr></thead>
          <tbody>{data!.map((a) => (
            <tr key={a.id}>
              <td className={T.td}>#{a.id}</td><td className={`${T.td} capitalize`}>{a.crop}</td><td className={T.td}>{a.quantity} {a.unit}</td>
              <td className={T.td}>{money(a.price_per_unit)}</td><td className={T.td}>{money(a.total_price)}</td>
              <td className={T.td}><Badge status={a.status} /></td><td className={T.td}><Badge status={a.delivery_status} /></td>
            </tr>))}</tbody></table></div>
      )}
    </div>
  );
}

/* ---------------- Deliveries ---------------- */
const NEXT: any = { PENDING: "PICKED_UP", PICKED_UP: "IN_TRANSIT", IN_TRANSIT: "DELIVERED" };

function Custody({ id }: any) {
  const { data, error, loading } = useFetch<any>(`/deliveries/${id}/custody`);
  if (loading) return <Loading />; if (error) return <ErrorBox message={error} />;
  return (
    <div className="space-y-2 text-sm">
      <p className="text-xs text-slate-500">{data.note}</p>
      {data.events.length === 0 ? <p>No custody events yet.</p> : data.events.map((e: any, i: number) => (
        <p key={i}>{label(e.event)} · {label(e.actor_role)} · {fmtDate(e.created_at)}{e.note && e.note !== e.event ? ` · ${e.note}` : ""}</p>
      ))}
    </div>
  );
}

export function Deliveries() {
  const { user } = useAuth();
  const { data, error, loading, reload } = useFetch<any[]>("/deliveries");
  const { run, busy } = useAction(reload);
  const [open, setOpen] = useState<number | null>(null);
  if (loading) return <Loading />; if (error) return <ErrorBox message={error} />;
  return (
    <div>
      <PageHeader title="Deliveries" desc="Pickup, transit and delivery status with custody history." />
      <div className="mb-4"><Notice>Status changes are recorded by the transporter. Live GPS tracking is not integrated.</Notice></div>
      {data!.length === 0 ? <Empty>No deliveries yet. They are created when an offer is accepted.</Empty> : (
        <div className="space-y-3">{data!.map((d) => {
          const mine = d.transporter_id === user.id, next = NEXT[d.status];
          return (
            <Card key={d.id}>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="font-medium capitalize">Delivery #{d.id} · {d.crop} · {d.quantity} {d.unit}</p>
                  <p className="text-xs text-slate-500">Agreement #{d.agreement_id} · Region {label(d.region)} · {d.transporter_id ? (mine ? "Assigned to you" : "Assigned") : "Unclaimed"}</p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge status={d.status} />
                  {user.role === "transporter" && !d.transporter_id && <Button loading={busy} onClick={() => run(`/deliveries/${d.id}/claim`, undefined, "Delivery claimed")}>Claim</Button>}
                  {user.role === "transporter" && mine && next && <Button loading={busy} onClick={() => window.confirm(`Mark as ${label(next)}?`) && run(`/deliveries/${d.id}/update`, { status: next, note: "" }, `Marked ${label(next)}`)}>Mark {label(next).toLowerCase()}</Button>}
                  <Button variant="secondary" onClick={() => setOpen(open === d.id ? null : d.id)}>Custody</Button>
                </div>
              </div>
              {open === d.id && <div className="mt-4 border-t border-slate-100 pt-4"><Custody id={d.id} /></div>}
            </Card>);
        })}</div>
      )}
    </div>
  );
}

/* ---------------- Verification queue ---------------- */
export function Queue() {
  const { data, error, loading, reload } = useFetch<any[]>("/verification/queue");
  const [modal, setModal] = useState<any>(null);
  const { run, busy } = useAction(() => { setModal(null); reload(); });
  if (loading) return <Loading />; if (error) return <ErrorBox message={error} />;
  return (
    <div>
      <PageHeader title="Verification queue" desc="Batches submitted for quality review. Every decision is audited and recorded in provenance." />
      {data!.length === 0 ? <Empty>The queue is empty.</Empty> : (
        <div className={T.wrap}><table className={T.table}>
          <thead><tr>{["ID", "Crop", "Region", "Quantity", "Harvest date", "Actions"].map((h) => <th key={h} className={T.th}>{h}</th>)}</tr></thead>
          <tbody>{data!.map((b) => (
            <tr key={b.id}>
              <td className={T.td}>#{b.id}</td><td className={`${T.td} capitalize`}>{b.crop}</td><td className={T.td}>{label(b.region)}</td>
              <td className={T.td}>{b.quantity} {b.unit}</td><td className={T.td}>{b.harvest_date || "—"}</td>
              <td className={`${T.td} space-x-2 whitespace-nowrap`}>
                <Link className="text-forest underline" to={`/app/batches/${b.id}`}>Details</Link>
                <Button onClick={() => setModal({ b, approve: true })}>Approve</Button>
                <Button variant="danger" onClick={() => setModal({ b, approve: false })}>Reject</Button>
              </td>
            </tr>))}</tbody></table></div>
      )}
      {modal && (
        <Modal title={`${modal.approve ? "Approve" : "Reject"} batch #${modal.b.id}`} onClose={() => setModal(null)}>
          <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); const f = new FormData(e.currentTarget); run(`/verification/${modal.b.id}/decision`, { approve: modal.approve, reason: (f.get("reason") as string) || null }, modal.approve ? "Batch approved" : "Batch rejected"); }}>
            <Field label={modal.approve ? "Note (optional)" : "Reason for rejection"} help={modal.approve ? undefined : "Required. The farmer will see this reason."}>
              <textarea name="reason" required={!modal.approve} maxLength={500} rows={3} className={inputCls} />
            </Field>
            <Button type="submit" variant={modal.approve ? "primary" : "danger"} loading={busy} className="w-full">{modal.approve ? "Confirm approval" : "Confirm rejection"}</Button>
          </form>
        </Modal>)}
    </div>
  );
}
