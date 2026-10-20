import { useState } from "react";
import { Link } from "react-router-dom";
import { CartesianGrid, Line, LineChart, Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, label, money, fmtDate } from "../api";
import { useAuth } from "../auth";
import { Button, Card, Badge, Field, Modal, inputCls, useFetch, Loading, ErrorBox, Empty, Notice, PageHeader, Kpi, useToast, tableCls as T } from "../components/ui";
import { useAction } from "./Workspace";

function Tbl({ heads, children }: any) {
  return <div className={T.wrap}><table className={T.table}><thead><tr>{heads.map((h: string) => <th key={h} className={T.th}>{h}</th>)}</tr></thead><tbody>{children}</tbody></table></div>;
}
const Td = ({ children, className = "" }: any) => <td className={`${T.td} ${className}`}>{children}</td>;
const fd = (e: any) => { e.preventDefault(); return new FormData(e.currentTarget); };
const Section = ({ title, children }: any) => <div className="mt-8"><h2 className="mb-3 text-lg font-medium text-forest">{title}</h2>{children}</div>;
const Gate = ({ items }: any) => { const e = items.find((i: any) => i.loading || i.error); return e ? (e.loading ? <Loading /> : <ErrorBox message={e.error} />) : null; };

/* ---------- Notifications ---------- */
export function Notifications() {
  const { data, error, loading, reload } = useFetch<any>("/notifications");
  const { run, busy } = useAction(reload);
  if (loading) return <Loading />; if (error) return <ErrorBox message={error} />;
  return (
    <div>
      <PageHeader title="Notifications" desc="Activity from offers, verification, deliveries, rewards, permissions and more."
        action={<Button variant="secondary" loading={busy} onClick={() => run("/notifications/read-all", undefined, "All marked as read")}>Mark all read</Button>} />
      {data.items.length === 0 ? <Empty>No notifications yet.</Empty> : (
        <div className="space-y-2">{data.items.map((n: any) => (
          <Card key={n.id} className={n.is_read ? "opacity-70" : "border-forest/40"}>
            <div className="flex items-center justify-between gap-3">
              <div><p className="text-sm">{n.message}</p><p className="text-xs text-slate-500">{label(n.kind)} · {fmtDate(n.created_at)}</p></div>
              {!n.is_read && <Button variant="secondary" onClick={() => run(`/notifications/${n.id}/read`, undefined, "Marked as read")}>Mark read</Button>}
            </div>
          </Card>))}</div>
      )}
    </div>
  );
}

/* ---------- Sustainability ---------- */
export function Sustainability() {
  const { user } = useAuth(); const farmer = user.role === "farmer";
  const rules = useFetch<any>("/sustainability/rules");
  const farms = useFetch<any[]>(farmer ? "/sustainability/farms" : null);
  const claims = useFetch<any[]>("/sustainability/claims");
  const rewards = useFetch<any[]>(farmer ? "/sustainability/rewards" : null);
  const report = useFetch<any>(farmer ? "/sustainability/report" : null);
  const [modal, setModal] = useState<any>(null);
  const { run, busy } = useAction(() => { setModal(null); farms.reload(); claims.reload(); rewards.reload(); report.reload(); });
  const g = Gate({ items: [rules, claims, ...(farmer ? [farms, rewards, report] : [])] }); if (g) return g;
  return (
    <div>
      <PageHeader title="Sustainability and rewards" desc="Submit evidence-backed claims. Verified claims earn points under transparent rules."
        action={farmer && <div className="flex gap-2"><Button variant="secondary" onClick={() => setModal({ t: "farm" })}>Add farm</Button><Button onClick={() => setModal({ t: "claim" })} disabled={!farms.data!.length}>Submit claim</Button></div>} />
      <Notice>{rules.data.note}</Notice>
      <Section title="Reward rules">
        <Tbl heads={["Claim type", "Calculation", "Evidence required"]}>
          {Object.entries(rules.data.rules).map(([k, r]: any) => <tr key={k}><Td>{r.label}</Td><Td>{r.method}</Td><Td>{r.evidence}</Td></tr>)}
        </Tbl>
      </Section>
      {farmer && <Section title="My farms">{farms.data!.length === 0 ? <Empty>Add a farm profile before submitting claims.</Empty> :
        <Tbl heads={["Farm", "Region", "Area (acres)", "Practices"]}>{farms.data!.map((f) => <tr key={f.id}><Td>{f.name}</Td><Td>{label(f.region)}</Td><Td>{f.area_acres}</Td><Td>{f.practices || "—"}</Td></tr>)}</Tbl>}</Section>}
      <Section title="Claims">
        {claims.data!.length === 0 ? <Empty>No claims yet.</Empty> : (
          <Tbl heads={["ID", "Farm", "Type", "Amount", "Evidence", "Status", "Reward", "Actions"]}>
            {claims.data!.map((c) => (
              <tr key={c.id}>
                <Td>#{c.id}</Td><Td>{c.farm}</Td><Td>{label(c.claim_type)}</Td><Td>{c.amount || "—"}</Td><Td className="max-w-[180px] truncate">{c.evidence_ref}</Td>
                <Td><Badge status={c.status === "SUBMITTED" ? "PENDING" : c.status === "VERIFIED" ? "ACCEPTED" : "REJECTED"} text={label(c.status)} />{c.review_notes && <p className="text-xs text-slate-500">{c.review_notes}</p>}</Td>
                <Td>{c.reward_points != null ? `${c.reward_points} pts` : "—"}</Td>
                <Td className="space-x-2 whitespace-nowrap">{!farmer && c.status === "SUBMITTED" && <><Button onClick={() => setModal({ t: "review", c, approve: true })}>Approve</Button><Button variant="danger" onClick={() => setModal({ t: "review", c, approve: false })}>Reject</Button></>}</Td>
              </tr>))}
          </Tbl>)}
      </Section>
      {farmer && <>
        <Section title="Reward history">{rewards.data!.length === 0 ? <Empty>No rewards yet. They are issued when a claim is verified.</Empty> :
          <Tbl heads={["Claim", "Points", "Calculation", "Ledger reference"]}>{rewards.data!.map((r) => <tr key={r.id}><Td>#{r.claim_id}</Td><Td>{r.points}</Td><Td>{r.rule}</Td><Td><Badge status="SIMULATED" /> <code className="text-xs">{r.transaction_ref}</code></Td></tr>)}</Tbl>}</Section>
        <Section title="Report preview">
          <Card><dl className="grid gap-3 text-sm sm:grid-cols-3">
            <div><dt className="text-slate-500">Verified claims</dt><dd className="text-xl font-semibold">{report.data.verified_claims}</dd></div>
            <div><dt className="text-slate-500">Total points</dt><dd className="text-xl font-semibold">{report.data.total_points}</dd></div>
            <div><dt className="text-slate-500">Calculated</dt><dd>{fmtDate(report.data.calculation_date)}</dd></div>
          </dl>
          <p className="mt-3 text-xs text-slate-500">Sources: {report.data.data_sources}. Assumptions: {report.data.assumptions}.</p>
          {report.data.missing_data.length > 0 && <p className="mt-1 text-xs text-amber-700">Missing data: {report.data.missing_data.join("; ")}</p>}
          <p className="mt-1 text-xs text-slate-500">{report.data.limitations}</p></Card>
        </Section></>}

      {modal?.t === "farm" && <Modal title="Add a farm" onClose={() => setModal(null)}><form className="space-y-3" onSubmit={(e) => { const f = fd(e); run("/sustainability/farms", { name: f.get("name"), region: f.get("region"), area_acres: Number(f.get("area") || 0), practices: f.get("practices") || "" }, "Farm added"); }}>
        <Field label="Farm name"><input name="name" required minLength={2} className={inputCls} /></Field>
        <Field label="Region" help="District or state level only. Exact location is not stored."><input name="region" required minLength={2} className={inputCls} /></Field>
        <Field label="Area (acres)"><input name="area" type="number" min="0" step="any" className={inputCls} /></Field>
        <Field label="Farming practices"><input name="practices" className={inputCls} /></Field>
        <Button type="submit" loading={busy} className="w-full">Save farm</Button></form></Modal>}
      {modal?.t === "claim" && <Modal title="Submit a sustainability claim" onClose={() => setModal(null)}><form className="space-y-3" onSubmit={(e) => { const f = fd(e); run("/sustainability/claims", { farm_id: Number(f.get("farm")), claim_type: f.get("type"), amount: Number(f.get("amount") || 0), description: f.get("description") || "", evidence_ref: f.get("evidence") }, "Claim submitted for review"); }}>
        <Field label="Farm"><select name="farm" className={inputCls}>{farms.data!.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}</select></Field>
        <Field label="Claim type"><select name="type" className={inputCls}>{Object.entries(rules.data.rules).map(([k, r]: any) => <option key={k} value={k}>{r.label}</option>)}</select></Field>
        <Field label="Amount" help="Litres saved (required for water saving)"><input name="amount" type="number" min="0" step="any" className={inputCls} /></Field>
        <Field label="Description"><input name="description" className={inputCls} /></Field>
        <Field label="Evidence reference" help="Reference to an irrigation log, soil report or photo (required)"><input name="evidence" required minLength={3} className={inputCls} /></Field>
        <Button type="submit" loading={busy} className="w-full">Submit claim</Button></form></Modal>}
      {modal?.t === "review" && <Modal title={`${modal.approve ? "Approve" : "Reject"} claim #${modal.c.id}`} onClose={() => setModal(null)}><form className="space-y-3" onSubmit={(e) => { const f = fd(e); run(`/sustainability/claims/${modal.c.id}/review`, { approve: modal.approve, notes: (f.get("notes") as string) || null }, modal.approve ? "Claim verified and reward issued" : "Claim rejected"); }}>
        <Field label={modal.approve ? "Notes (optional)" : "Reason for rejection"}><textarea name="notes" rows={3} required={!modal.approve} className={inputCls} /></Field>
        <Button type="submit" variant={modal.approve ? "primary" : "danger"} loading={busy} className="w-full">Confirm</Button></form></Modal>}
    </div>
  );
}

/* ---------- Data permissions ---------- */
export function Permissions() {
  const { user } = useAuth(); const farmer = user.role === "farmer"; const toast = useToast();
  const list = useFetch<any[]>("/permissions");
  const lenders = useFetch<any[]>(farmer ? "/directory/lender" : null), insurers = useFetch<any[]>(farmer ? "/directory/insurer" : null);
  const [modal, setModal] = useState(false); const [report, setReport] = useState<any>(null);
  const { run, busy } = useAction(() => { setModal(false); list.reload(); });
  const g = Gate({ items: [list, ...(farmer ? [lenders, insurers] : [])] }); if (g) return g;
  const view = async (id: number) => { try { setReport(await api(`/permissions/report/${id}`)); } catch (e: any) { toast.error(e.message); } };
  const recipients = farmer ? [...lenders.data!, ...insurers.data!] : [];
  return (
    <div>
      <PageHeader title="Data permissions" desc={farmer ? "Choose who can see your farm report, why, and for how long." : "Farm reports shared with you."}
        action={farmer && <Button onClick={() => setModal(true)}>Share farm report</Button>} />
      <Notice>Revoking stops all future access. Information already viewed or copied before revocation cannot be recalled.</Notice>
      <div className="mt-4">{list.data!.length === 0 ? <Empty>{farmer ? "You have not shared your report with anyone." : "No reports have been shared with you."}</Empty> : (
        <Tbl heads={[farmer ? "Shared with" : "Farmer", "Purpose", "Status", "Expires", "Actions"]}>
          {list.data!.map((p) => (
            <tr key={p.id}><Td>{farmer ? `${p.grantee_name} (${label(p.grantee_role)})` : p.owner_name}</Td><Td>{p.purpose}</Td>
              <Td><Badge status={p.status === "ACTIVE" ? "ACCEPTED" : "REJECTED"} text={label(p.status)} /></Td><Td>{p.expires_at ? fmtDate(p.expires_at) : "No expiry"}</Td>
              <Td className="space-x-2">
                {farmer && p.status === "ACTIVE" && <Button variant="danger" loading={busy} onClick={() => window.confirm("Revoke access? Future access will be denied; anything already viewed cannot be recalled.") && run(`/permissions/${p.id}/revoke`, undefined, "Access revoked")}>Revoke</Button>}
                {!farmer && p.status === "ACTIVE" && <Button variant="secondary" onClick={() => view(p.owner_id)}>View report</Button>}
              </Td></tr>))}
        </Tbl>)}</div>
      {modal && <Modal title="Share farm report" onClose={() => setModal(false)}><form className="space-y-3" onSubmit={(e) => { const f = fd(e); run("/permissions", { grantee_email: f.get("email"), purpose: f.get("purpose"), days: f.get("days") ? Number(f.get("days")) : null }, "Report shared"); }}>
        <Field label="Recipient" help="Lenders and insurers registered on the platform"><select name="email" className={inputCls}>{recipients.map((r) => <option key={r.id} value={r.email}>{r.name} · {r.email}</option>)}</select></Field>
        <Field label="Purpose"><input name="purpose" required minLength={3} className={inputCls} /></Field>
        <Field label="Expires after (days, optional)"><input name="days" type="number" min="1" max="365" className={inputCls} /></Field>
        <Button type="submit" loading={busy} className="w-full">Share</Button></form></Modal>}
      {report && <Modal title={`Farm report: ${report.farmer}`} onClose={() => setReport(null)}>
        <div className="space-y-2 text-sm">
          {report.farms.map((f: any, i: number) => <p key={i}>{f.name} · {label(f.region)} · {f.area_acres} acres · {f.practices || "no practices recorded"}</p>)}
          <p>Batches: {Object.entries(report.batches_by_status).map(([k, v]) => `${label(k)} ${v}`).join(", ") || "none"}</p>
          <p>Verified sustainability claims: {report.verified_sustainability_claims} · Reward points: {report.reward_points}</p>
          <p className="text-xs text-slate-500">{report.note}</p></div></Modal>}
    </div>
  );
}

/* ---------- Cooperative ---------- */
export function Cooperative() {
  const { user } = useAuth(); const farmer = user.role === "farmer";
  const members = useFetch<any[]>("/cooperatives/members"), coops = useFetch<any[]>(farmer ? "/directory/cooperative" : null);
  const { run, busy } = useAction(members.reload);
  const g = Gate({ items: [members, ...(farmer ? [coops] : [])] }); if (g) return g;
  return (
    <div>
      <PageHeader title="Cooperative" desc={farmer ? "Request membership and track decisions." : "Review farmer membership requests."} />
      {farmer && <Section title="Cooperatives">{coops.data!.length === 0 ? <Empty>No cooperatives registered.</Empty> : coops.data!.map((c) => (
        <Card key={c.id} className="mb-2"><div className="flex items-center justify-between"><span>{c.name}</span><Button variant="secondary" loading={busy} onClick={() => run("/cooperatives/join", { coop_id: c.id }, "Membership requested")}>Request to join</Button></div></Card>))}</Section>}
      <Section title="Memberships">{members.data!.length === 0 ? <Empty>No membership records yet.</Empty> : (
        <Tbl heads={["Cooperative", "Farmer", "Status", "Requested", "Actions"]}>{members.data!.map((m) => (
          <tr key={m.id}><Td>{m.coop_name}</Td><Td>{m.farmer_name}</Td><Td><Badge status={m.status === "APPROVED" ? "ACCEPTED" : m.status} text={label(m.status)} /></Td><Td>{fmtDate(m.created_at)}</Td>
            <Td className="space-x-2">{user.role === "cooperative" && m.status === "PENDING" && <><Button loading={busy} onClick={() => run(`/cooperatives/members/${m.id}/decision`, { approve: true }, "Member approved")}>Approve</Button><Button variant="danger" loading={busy} onClick={() => run(`/cooperatives/members/${m.id}/decision`, { approve: false }, "Request rejected")}>Reject</Button></>}</Td></tr>))}</Tbl>)}</Section>
      <p className="mt-6 text-xs text-slate-500">Group listings and bulk sales are not built yet.</p>
    </div>
  );
}

/* ---------- Agronomy ---------- */
function CaseDetail({ id, agro, done }: any) {
  const { data, error, loading, reload } = useFetch<any>(`/agronomy/cases/${id}`);
  const { run, busy } = useAction(() => { reload(); done(); });
  if (loading) return <Loading />; if (error) return <ErrorBox message={error} />;
  return (
    <div className="space-y-3 text-sm">
      {data.notes.length === 0 ? <p>No notes yet.</p> : data.notes.map((n: any, i: number) => <p key={i}><b>{label(n.kind)}</b> · {n.author} · {fmtDate(n.created_at)}<br />{n.text}</p>)}
      {data.status === "OPEN" && <form className="flex flex-wrap gap-2" onSubmit={(e) => { const f = fd(e); run(`/agronomy/cases/${id}/notes`, { text: f.get("text"), kind: f.get("kind") || "OBSERVATION" }, "Note added"); (e.target as any).reset(); }}>
        <input name="text" required placeholder="Add a note" className={`${inputCls} flex-1`} />
        {agro && <select name="kind" className={`${inputCls} w-auto`}><option value="OBSERVATION">Observation</option><option value="RECOMMENDATION">Recommendation</option></select>}
        <Button type="submit" loading={busy}>Add</Button>
        {agro && <Button type="button" variant="secondary" onClick={() => window.confirm("Close this case?") && run(`/agronomy/cases/${id}/close`, undefined, "Case closed")}>Close case</Button>}</form>}
    </div>
  );
}
export function Agronomy() {
  const { user } = useAuth(); const farmer = user.role === "farmer";
  const cases = useFetch<any[]>("/agronomy/cases"), agros = useFetch<any[]>(farmer ? "/directory/agronomist" : null);
  const [open, setOpen] = useState<number | null>(null); const [modal, setModal] = useState(false);
  const { run, busy } = useAction(() => { setModal(false); cases.reload(); });
  const g = Gate({ items: [cases, ...(farmer ? [agros] : [])] }); if (g) return g;
  return (
    <div>
      <PageHeader title="Agronomy cases" desc="Field observations and recommendations." action={farmer && <Button onClick={() => setModal(true)}>Open a case</Button>} />
      {cases.data!.length === 0 ? <Empty>No cases yet.</Empty> : cases.data!.map((c) => (
        <Card key={c.id} className="mb-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div><p className="font-medium">#{c.id} · {c.topic}</p><p className="text-xs text-slate-500">Farmer {c.farmer_name} · Agronomist {c.agronomist_name}</p></div>
            <div className="flex items-center gap-2"><Badge status={c.status === "OPEN" ? "PENDING" : "COMPLETED"} text={label(c.status)} /><Button variant="secondary" onClick={() => setOpen(open === c.id ? null : c.id)}>{open === c.id ? "Hide" : "Open"}</Button></div>
          </div>
          {open === c.id && <div className="mt-4 border-t border-slate-100 pt-4"><CaseDetail id={c.id} agro={!farmer} done={cases.reload} /></div>}
        </Card>))}
      {modal && <Modal title="Open an agronomy case" onClose={() => setModal(false)}><form className="space-y-3" onSubmit={(e) => { const f = fd(e); run("/agronomy/cases", { agronomist_id: Number(f.get("agro")), topic: f.get("topic") }, "Case opened"); }}>
        <Field label="Agronomist"><select name="agro" className={inputCls}>{agros.data!.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}</select></Field>
        <Field label="Topic"><input name="topic" required minLength={3} className={inputCls} /></Field>
        <Button type="submit" loading={busy} className="w-full">Open case</Button></form></Modal>}
    </div>
  );
}

/* ---------- Suppliers ---------- */
export function Suppliers() {
  const { user } = useAuth();
  const { data, error, loading, reload } = useFetch<any[]>("/suppliers/products");
  const [modal, setModal] = useState(false);
  const { run, busy } = useAction(() => { setModal(false); reload(); });
  const g = Gate({ items: [{ data, error, loading }] }); if (g) return g;
  const sup = user.role === "supplier";
  return (
    <div>
      <PageHeader title="Supplier products" desc="Agricultural inputs listed by suppliers." action={sup && <Button onClick={() => setModal(true)}>Add product</Button>} />
      <div className="mb-4"><Notice>Authenticity notes are supplier-declared and have not been independently verified.</Notice></div>
      {data!.length === 0 ? <Empty>No products listed.</Empty> : (
        <Tbl heads={["Product", "Category", "Price", "Supplier", "Authenticity", ""]}>{data!.map((p) => (
          <tr key={p.id}><Td>{p.name}</Td><Td>{label(p.category)}</Td><Td>{money(p.price)} / {p.unit}</Td><Td>{p.supplier}</Td><Td className="text-xs">{p.authenticity_note}</Td>
            <Td>{sup && p.supplier_id === user.id && <Button variant="danger" loading={busy} onClick={() => window.confirm("Delete this product?") && run(`/suppliers/products/${p.id}`, undefined, "Product deleted")}>Delete</Button>}</Td></tr>))}</Tbl>)}
      {modal && <Modal title="Add a product" onClose={() => setModal(false)}><form className="space-y-3" onSubmit={(e) => { const f = fd(e); run("/suppliers/products", { name: f.get("name"), category: f.get("category"), price: Number(f.get("price")), unit: f.get("unit") }, "Product added"); }}>
        <Field label="Name"><input name="name" required minLength={2} className={inputCls} /></Field>
        <Field label="Category"><input name="category" list="cats" required minLength={2} className={inputCls} /><datalist id="cats"><option value="seed" /><option value="fertiliser" /><option value="pesticide" /><option value="equipment" /></datalist></Field>
        <div className="grid grid-cols-2 gap-3"><Field label="Price (₹)"><input name="price" type="number" min="0.01" step="any" required className={inputCls} /></Field><Field label="Unit"><input name="unit" defaultValue="kg" required className={inputCls} /></Field></div>
        <Button type="submit" loading={busy} className="w-full">Add product</Button></form></Modal>}
    </div>
  );
}

/* ---------- Lending ---------- */
export function Lending() {
  const { user } = useAuth(); const farmer = user.role === "farmer";
  const apps = useFetch<any[]>("/lending/applications"), lenders = useFetch<any[]>(farmer ? "/directory/lender" : null);
  const [modal, setModal] = useState<any>(null);
  const { run, busy } = useAction(() => { setModal(null); apps.reload(); });
  const g = Gate({ items: [apps, ...(farmer ? [lenders] : [])] }); if (g) return g;
  return (
    <div>
      <PageHeader title="Loan applications" desc={farmer ? "Apply to a lender and track decisions." : "Applications addressed to you. Farm reports require the farmer's permission."}
        action={farmer && <Button onClick={() => setModal({ t: "apply" })}>New application</Button>} />
      {!farmer && <div className="mb-4"><Notice>To see a farmer's report, use Data permissions. Access exists only while the farmer's permission is active.</Notice></div>}
      {apps.data!.length === 0 ? <Empty>No applications yet.</Empty> : (
        <Tbl heads={["ID", farmer ? "Lender" : "Farmer", "Amount", "Purpose", "Status", "Actions"]}>{apps.data!.map((a) => (
          <tr key={a.id}><Td>#{a.id}</Td><Td>{farmer ? a.lender_name : a.farmer_name}</Td><Td>{money(a.amount)}</Td><Td>{a.purpose}</Td>
            <Td><Badge status={a.status === "SUBMITTED" ? "PENDING" : a.status === "APPROVED" ? "ACCEPTED" : "REJECTED"} text={label(a.status)} />{a.decision_notes && <p className="text-xs text-slate-500">{a.decision_notes}</p>}</Td>
            <Td className="space-x-2">{!farmer && a.status === "SUBMITTED" && <><Button onClick={() => setModal({ t: "decide", a, approve: true })}>Approve</Button><Button variant="danger" onClick={() => setModal({ t: "decide", a, approve: false })}>Reject</Button></>}</Td></tr>))}</Tbl>)}
      {modal?.t === "apply" && <Modal title="Loan application" onClose={() => setModal(null)}><form className="space-y-3" onSubmit={(e) => { const f = fd(e); run("/lending/applications", { lender_id: Number(f.get("lender")), amount: Number(f.get("amount")), purpose: f.get("purpose") }, "Application submitted"); }}>
        <Field label="Lender"><select name="lender" className={inputCls}>{lenders.data!.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}</select></Field>
        <Field label="Amount (₹)"><input name="amount" type="number" min="1" step="any" required className={inputCls} /></Field>
        <Field label="Purpose"><input name="purpose" required minLength={3} className={inputCls} /></Field>
        <Notice>No money is transferred by this application. Repayment schedules are not built yet.</Notice>
        <Button type="submit" loading={busy} className="w-full">Submit</Button></form></Modal>}
      {modal?.t === "decide" && <Modal title={`${modal.approve ? "Approve" : "Reject"} application #${modal.a.id}`} onClose={() => setModal(null)}><form className="space-y-3" onSubmit={(e) => { const f = fd(e); run(`/lending/applications/${modal.a.id}/decision`, { approve: modal.approve, notes: (f.get("notes") as string) || null }, "Decision recorded"); }}>
        <Field label={modal.approve ? "Notes (optional)" : "Reason"}><textarea name="notes" rows={3} required={!modal.approve} className={inputCls} /></Field>
        <Button type="submit" variant={modal.approve ? "primary" : "danger"} loading={busy} className="w-full">Confirm</Button></form></Modal>}
    </div>
  );
}

/* ---------- Insurance ---------- */
export function Insurance() {
  const { user } = useAuth(); const farmer = user.role === "farmer";
  const pol = useFetch<any[]>("/insurance/policies"), cl = useFetch<any[]>("/insurance/claims");
  const [modal, setModal] = useState<any>(null);
  const { run, busy } = useAction(() => { setModal(null); pol.reload(); cl.reload(); });
  const g = Gate({ items: [pol, cl] }); if (g) return g;
  return (
    <div>
      <PageHeader title="Insurance" desc={farmer ? "Your policies and claims." : "Issue policies and review claims."}
        action={farmer ? <Button onClick={() => setModal({ t: "claim" })} disabled={!pol.data!.length}>File a claim</Button> : <Button onClick={() => setModal({ t: "policy" })}>Issue policy</Button>} />
      <Notice>No payment integration is configured. Approving a claim records a decision only; no payout is made.</Notice>
      <Section title="Policies">{pol.data!.length === 0 ? <Empty>No policies yet.</Empty> : (
        <Tbl heads={["ID", farmer ? "Insurer" : "Farmer", "Crop", "Coverage", "Terms", "Status"]}>{pol.data!.map((p) => <tr key={p.id}><Td>#{p.id}</Td><Td>{farmer ? p.insurer_name : p.farmer_name}</Td><Td className="capitalize">{p.crop}</Td><Td>{money(p.coverage_amount)}</Td><Td>{p.terms || "—"}</Td><Td><Badge status="ACCEPTED" text={label(p.status)} /></Td></tr>)}</Tbl>)}</Section>
      <Section title="Claims">{cl.data!.length === 0 ? <Empty>No claims yet.</Empty> : (
        <Tbl heads={["ID", "Policy", "Description", "Status", "Payout", "Actions"]}>{cl.data!.map((c) => (
          <tr key={c.id}><Td>#{c.id}</Td><Td>#{c.policy_id} · {c.crop}</Td><Td>{c.description}</Td>
            <Td><Badge status={c.status === "SUBMITTED" ? "PENDING" : c.status === "APPROVED" ? "ACCEPTED" : "REJECTED"} text={label(c.status)} />{c.decision_notes && <p className="text-xs text-slate-500">{c.decision_notes}</p>}</Td>
            <Td>{label(c.payout_status)}</Td>
            <Td className="space-x-2">{!farmer && c.status === "SUBMITTED" && <><Button onClick={() => setModal({ t: "decide", c, approve: true })}>Approve</Button><Button variant="danger" onClick={() => setModal({ t: "decide", c, approve: false })}>Reject</Button></>}</Td></tr>))}</Tbl>)}</Section>
      {modal?.t === "policy" && <Modal title="Issue a policy" onClose={() => setModal(null)}><form className="space-y-3" onSubmit={(e) => { const f = fd(e); run("/insurance/policies", { farmer_email: f.get("email"), crop: f.get("crop"), coverage_amount: Number(f.get("coverage")), terms: f.get("terms") || "" }, "Policy issued"); }}>
        <Field label="Farmer email"><input name="email" type="email" required className={inputCls} /></Field>
        <Field label="Crop"><input name="crop" required minLength={2} className={inputCls} /></Field>
        <Field label="Coverage (₹)"><input name="coverage" type="number" min="1" step="any" required className={inputCls} /></Field>
        <Field label="Terms"><input name="terms" className={inputCls} /></Field>
        <Button type="submit" loading={busy} className="w-full">Issue policy</Button></form></Modal>}
      {modal?.t === "claim" && <Modal title="File a claim" onClose={() => setModal(null)}><form className="space-y-3" onSubmit={(e) => { const f = fd(e); run("/insurance/claims", { policy_id: Number(f.get("policy")), description: f.get("description"), evidence_ref: f.get("evidence") || "" }, "Claim filed"); }}>
        <Field label="Policy"><select name="policy" className={inputCls}>{pol.data!.map((p) => <option key={p.id} value={p.id}>#{p.id} · {p.crop}</option>)}</select></Field>
        <Field label="What happened?"><input name="description" required minLength={3} className={inputCls} /></Field>
        <Field label="Evidence reference"><input name="evidence" className={inputCls} /></Field>
        <Button type="submit" loading={busy} className="w-full">File claim</Button></form></Modal>}
      {modal?.t === "decide" && <Modal title={`${modal.approve ? "Approve" : "Reject"} claim #${modal.c.id}`} onClose={() => setModal(null)}><form className="space-y-3" onSubmit={(e) => { const f = fd(e); run(`/insurance/claims/${modal.c.id}/decision`, { approve: modal.approve, notes: (f.get("notes") as string) || null }, "Decision recorded"); }}>
        <Field label={modal.approve ? "Notes (optional)" : "Reason"}><textarea name="notes" rows={3} required={!modal.approve} className={inputCls} /></Field>
        <Button type="submit" variant={modal.approve ? "primary" : "danger"} loading={busy} className="w-full">Confirm</Button></form></Modal>}
    </div>
  );
}

/* ---------- Administration ---------- */
export function Admin() {
  const users = useFetch<any[]>("/admin/users"), audit = useFetch<any[]>("/admin/audit");
  const { user: me } = useAuth();
  const { run, busy } = useAction(() => { users.reload(); audit.reload(); });
  const g = Gate({ items: [users, audit] }); if (g) return g;
  return (
    <div>
      <PageHeader title="Administration" desc="Account management and audit trail. Private farm data is not shown here." />
      <div className="grid gap-4 sm:grid-cols-3"><Kpi label="Accounts" value={users.data!.length} /><Kpi label="Active" value={users.data!.filter((u) => u.is_active).length} /><Kpi label="Audit events (latest)" value={audit.data!.length} /></div>
      <Section title="Users"><Tbl heads={["Name", "Email", "Role", "Status", "Actions"]}>{users.data!.map((u) => (
        <tr key={u.id}><Td>{u.name}</Td><Td>{u.email}</Td><Td>{label(u.role)}</Td><Td><Badge status={u.is_active ? "ACCEPTED" : "REJECTED"} text={u.is_active ? "Active" : "Disabled"} /></Td>
          <Td>{u.id !== me.id && <Button variant={u.is_active ? "danger" : "secondary"} loading={busy} onClick={() => window.confirm(`${u.is_active ? "Disable" : "Enable"} ${u.email}?`) && run(`/admin/users/${u.id}/status`, { is_active: !u.is_active }, "Account updated")}>{u.is_active ? "Disable" : "Enable"}</Button>}</Td></tr>))}</Tbl></Section>
      <Section title="Audit log"><Tbl heads={["When", "Actor", "Action", "Entity", "Detail"]}>{audit.data!.map((a) => <tr key={a.id}><Td>{fmtDate(a.created_at)}</Td><Td>{a.actor_id ?? "—"}</Td><Td>{label(a.action)}</Td><Td>{a.entity} {a.entity_id ?? ""}</Td><Td className="max-w-[240px] truncate">{a.detail}</Td></tr>)}</Tbl></Section>
    </div>
  );
}

/* ---------- Public analytics ---------- */
export function Analytics() {
  const market = useFetch<any>("/analytics/market"), opts = useFetch<any>("/predictions/options");
  const [crop, setCrop] = useState("rice"); const [region, setRegion] = useState("tamil_nadu");
  const prices = useFetch<any>(`/analytics/prices?crop=${crop}&region=${region}`);
  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <PageHeader title="Market analytics" desc="Listings from this application's database, plus a clearly labelled synthetic price history." />
      <Card>
        <h2 className="mb-1 font-medium">Average asking price by crop (live listings)</h2>
        <p className="mb-3 text-xs text-slate-500">{market.data?.source}</p>
        {market.loading ? <Loading /> : market.error ? <ErrorBox message={market.error} /> : market.data.crops.length === 0 ? <Empty>No active listings.</Empty> : (
          <div className="h-64"><ResponsiveContainer width="100%" height="100%"><BarChart data={market.data.crops}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="crop" /><YAxis label={{ value: "₹ per unit", angle: -90, position: "insideLeft", fontSize: 11 }} /><Tooltip /><Bar dataKey="avg_asking_price" name="Avg asking price" fill="#1e4d36" /></BarChart></ResponsiveContainer></div>)}
        {market.data?.crops?.length > 0 && <p className="mt-3 text-sm text-slate-600">{market.data.crops.map((c: any) => `${label(c.crop)}: ${c.listings} listing(s), ${c.available_quantity} units available`).join(" · ")}</p>}
      </Card>
      <Card className="mt-6">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2"><h2 className="font-medium">Price history</h2><Badge status="SIMULATED" text="Synthetic demo data" /></div>
        {opts.data && <div className="mb-3 flex gap-3">
          <select className={`${inputCls} max-w-[160px]`} value={crop} onChange={(e) => setCrop(e.target.value)}>{opts.data.crops.map((c: string) => <option key={c} value={c}>{label(c)}</option>)}</select>
          <select className={`${inputCls} max-w-[180px]`} value={region} onChange={(e) => setRegion(e.target.value)}>{opts.data.regions.map((c: string) => <option key={c} value={c}>{label(c)}</option>)}</select></div>}
        {prices.loading ? <Loading /> : prices.error ? <ErrorBox message={prices.error} /> : (<>
          <div className="h-64"><ResponsiveContainer width="100%" height="100%"><LineChart data={prices.data.history}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="month_index" label={{ value: "Month of series", position: "insideBottom", offset: -2, fontSize: 11 }} /><YAxis domain={["auto", "auto"]} label={{ value: prices.data.unit, angle: -90, position: "insideLeft", fontSize: 11 }} /><Tooltip /><Line type="monotone" dataKey="price" name="Price" stroke="#1e4d36" dot={false} /></LineChart></ResponsiveContainer></div>
          <p className="mt-2 text-xs text-slate-500">{prices.data.note} Source: {prices.data.data_source}.</p></>)}
      </Card>
      <p className="mt-4 text-xs text-slate-500">Live market-price feeds are not connected. <Link className="underline" to="/predict">Try the price estimator</Link>.</p>
    </div>
  );
}
