import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  ClipboardCheck,
  FileUp,
  History,
  LoaderCircle,
  PencilLine,
  RotateCcw,
  Rows3,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState, type KeyboardEventHandler, type ReactNode, type TouchEventHandler } from "react";
import { api } from "../lib/api";
import type { Bed, FarmOrder } from "../lib/types";
import {
  farmerWorkflowApi,
  planningApi,
  rememberPlanningSession,
  rememberedPlanningSession,
  type FarmerImport,
  type FarmerProposal,
  type FarmerTask,
  type FarmerWorkflowState,
  type PlanningSession,
} from "../lib/planning";
import "./IntegratedRecords.css";

type View = "home" | "setup" | "imports" | "orders" | "beds" | "inventory" | "proposals" | "tasks" | "verify" | "history";
type Form = "farmImport" | "seed" | "upload" | "manual" | "candidate" | "approve" | "recovery" | "result" | "correction" | null;

const emptyWorkflow: FarmerWorkflowState = {
  version: "farmer-workflow-v1",
  phase: "planning",
  revision: 0,
  inbox: [],
  proposals: [],
  tasks: [],
  events: [],
  real_operations_enabled: false,
};

export function IntegratedRecords({ onClose, onOpenPlan }: { onClose: () => void; onOpenPlan?: () => void }) {
  const [session, setSession] = useState<PlanningSession | null>(null);
  const [workflow, setWorkflow] = useState(emptyWorkflow);
  const [view, setView] = useState<View>("home");
  const [form, setForm] = useState<Form>(null);
  const [index, setIndex] = useState(0);
  const [homeIndex, setHomeIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const touch = useRef<{ x: number; y: number } | null>(null);
  const refresh = useCallback(async () => {
    const flow = await farmerWorkflowApi.state();
    setWorkflow({ ...emptyWorkflow, ...flow });
    return flow;
  }, []);
  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      let current: PlanningSession | undefined;
      const remembered = rememberedPlanningSession();
      if (remembered) {
        try { current = await planningApi.get(remembered); } catch { /* use latest */ }
      }
      if (!current) current = (await planningApi.list()).sessions.find((item) => item.workflow === true);
      setSession(current || null);
      await refresh();
    } catch (caught) {
      setError(problem(caught, "Farm records could not be opened."));
    } finally { setLoading(false); }
  }, [refresh]);
  useEffect(() => { void load(); }, [load]);

  const cards = useMemo(() => {
    if (view === "imports") return workflow.inbox;
    if (view === "orders") return session?.farm.orders || [];
    if (view === "beds") return session?.farm.beds || [];
    if (view === "inventory") return Array.isArray(session?.farm.inventory) ? session.farm.inventory as Record<string, unknown>[] : [];
    if (view === "proposals") return workflow.proposals;
    if (view === "tasks") return workflow.tasks;
    if (view === "history") return workflow.events;
    return [];
  }, [view, workflow]);
  useEffect(() => setIndex((old) => Math.min(old, Math.max(0, cards.length - 1))), [cards.length]);
  const open = (next: View) => { setView(next); setIndex(0); setForm(null); setError(""); };
  const back = () => { if (form) setForm(null); else if (view !== "home") open("home"); else onClose(); };
  const run = async (action: () => Promise<unknown>, fallback: string) => {
    setBusy(true); setError("");
    try { await action(); await refresh(); const remembered = rememberedPlanningSession(); if (remembered) setSession(await planningApi.get(remembered)); setForm(null); }
    catch (caught) { setError(problem(caught, fallback)); }
    finally { setBusy(false); }
  };

  if (loading) return <Shell title="Records & work" onBack={onClose}><Empty icon={<LoaderCircle className="spin" />} text="Opening farm records…" /></Shell>;
  const candidate = view === "imports" ? workflow.inbox[index] : undefined;
  const proposal = view === "proposals" ? workflow.proposals[index] : undefined;
  const task = view === "tasks" ? workflow.tasks[index] : undefined;
  const event = view === "history" ? workflow.events[index] : undefined;
  const order = view === "orders" ? session?.farm.orders[index] : undefined;
  const bed = view === "beds" ? session?.farm.beds[index] : undefined;
  const inventory = view === "inventory" && Array.isArray(session?.farm.inventory) ? (session.farm.inventory as Record<string, unknown>[])[index] : undefined;
  return (
    <Shell title={title(view, form)} onBack={back} onKeyDown={(event) => {
      if ((event.target as HTMLElement).closest("input,textarea,select,button,a")) return;
      if (view === "home" && event.key === "ArrowRight" && homeIndex < homeItems(workflow, session).length - 1) { event.preventDefault(); setHomeIndex(homeIndex + 1); return; }
      if (view === "home" && event.key === "ArrowLeft" && homeIndex > 0) { event.preventDefault(); setHomeIndex(homeIndex - 1); return; }
      if (event.key === "ArrowRight" && index < cards.length - 1) { event.preventDefault(); setIndex(index + 1); }
      if (event.key === "ArrowLeft" && index > 0) { event.preventDefault(); setIndex(index - 1); }
    }} onTouchStart={(event) => { touch.current = { x: event.touches[0].clientX, y: event.touches[0].clientY }; }} onTouchEnd={(event) => {
      const from = touch.current; touch.current = null; if (!from || form) return;
      const dx = event.changedTouches[0].clientX - from.x, dy = event.changedTouches[0].clientY - from.y;
      if (Math.abs(dx) > 65 && Math.abs(dx) > Math.abs(dy) * 1.5) { if (view === "home") setHomeIndex((old) => Math.max(0, Math.min(homeItems(workflow, session).length - 1, old + (dx < 0 ? 1 : -1)))); else setIndex((old) => Math.max(0, Math.min(cards.length - 1, old + (dx < 0 ? 1 : -1)))); }
    }}>
      <p className="ir-context">Sandbox farm · real operations disabled</p>
      {error && <div className="ir-error" role="alert"><AlertTriangle />{error}</div>}
      {view === "home" && <Home workflow={workflow} session={session} index={homeIndex} setIndex={setHomeIndex} open={open} />}
      {view === "setup" && !form && <Card eyebrow="Validated farm setup" title="Choose the source for a new farm version" status="review required"><p>Import a complete validated farm document or explicitly load the project-authored synthetic fixture. Either choice creates a separate workflow session and preserves older sessions.</p><p className="ir-note">A rendered farm view is not an import template. Use a complete document matching the backend farm schema.</p></Card>}
      {view !== "home" && !form && cards.length > 0 && (
        <nav className="ir-pager" aria-label={`${title(view, null)} cards`}>
          <button disabled={index === 0} onClick={() => setIndex(index - 1)}><ArrowLeft /> Previous</button>
          <span>{label(view)} {index + 1} of {cards.length}</span>
          <button disabled={index === cards.length - 1} onClick={() => setIndex(index + 1)}>Next <ArrowRight /></button>
        </nav>
      )}
      {view !== "home" && view !== "setup" && view !== "verify" && !form && cards.length === 0 && <Empty icon={<Rows3 />} text={`No ${label(view).toLowerCase()} records are available.`} />}
      {candidate && !form && <CandidateCard item={candidate} />}
      {proposal && !form && <ProposalCard item={proposal} session={session} />}
      {task && !form && <TaskCard item={task} />}
      {event && !form && <EventCard item={event} />}
      {order && !form && <OrderCard item={order} />}
      {bed && !form && <BedCard item={bed} />}
      {inventory && !form && <InventoryCard item={inventory} />}
      {view === "verify" && !form && <VerifyCard session={session} tasks={workflow.tasks} onOpenPlan={onOpenPlan} />}
      {form === "farmImport" && <FarmImportForm busy={busy} submit={(farm) => run(async () => { await api.importFarm(farm); const next = await planningApi.create("Imported farm workflow", true); rememberPlanningSession(next.id); setSession(next); }, "The validated farm import could not be committed. Your reviewed JSON is unchanged.")} />}
      {form === "seed" && <SeedReview busy={busy} submit={() => run(async () => { await api.importSeed(); const next = await planningApi.create("Synthetic demo workflow", true); rememberPlanningSession(next.id); setSession(next); }, "The synthetic demo could not be loaded.")} />}
      {form === "upload" && <UploadForm busy={busy} submit={(file) => run(async () => {
        const kind = file.type.startsWith("image/") ? "photo_observation" : /\.(csv|xlsx|xls)$/i.test(file.name) ? "accounting_export" : "document_extraction";
        await farmerWorkflowApi.upload(file, kind);
      }, "The candidate could not be uploaded. Draft and file selection are unchanged.")} />}
      {form === "manual" && session && <ManualForm session={session} busy={busy} submit={(name, row) => run(() => farmerWorkflowApi.manualImport(name, [row]), "The manual candidate could not be saved. Your draft is unchanged.")} />}
      {form === "candidate" && candidate && <CandidateReview item={candidate} busy={busy} decide={(decision, note) => run(() => farmerWorkflowApi.reviewImport(candidate.candidate_id, decision, "farmer", note), "The review decision could not be saved. Please check the candidate and retry.")} />}
      {form === "approve" && proposal && <ApprovalReview item={proposal} busy={busy} approve={() => run(() => farmerWorkflowApi.approve(proposal), "This proposal could not be approved. Refresh and review its current revision.")} />}
      {form === "recovery" && proposal && <RecoveryReview item={proposal} busy={busy} create={() => run(() => farmerWorkflowApi.inverseProposal(proposal), "The recovery proposal could not be created. Refresh and review the eligible revision.")} />}
      {form === "result" && task && <ResultForm task={task} photos={workflow.inbox.filter((item) => item.status === "confirmed" && item.source_kind === "photo_observation")} busy={busy} submit={(values) => run(() => farmerWorkflowApi.taskResult(task, values.status, task.unit ? values.quantity : null, task.action === "delivery" ? values.rejected : null, values.note, values.checks, values.photo || null), "The reported result could not be saved. Your draft is unchanged.")} />}
      {form === "correction" && task && <CorrectionForm task={task} busy={busy} submit={(value, reason, field = "actual_quantity") => run(() => farmerWorkflowApi.correctTask(task, field, value, reason), "The correction could not be saved. Your draft is unchanged.")} />}
      <div className="ir-actions" aria-label="Card actions">
        <button onClick={back}><ArrowLeft /> Back</button>
        {view === "home" && !form && <button className="is-primary" onClick={() => open(homeItems(workflow, session)[homeIndex].view)}>Open</button>}
        {view === "setup" && !form && <button className="is-primary" onClick={() => setForm("farmImport")}><FileUp /> Review farm JSON</button>}
        {view === "setup" && !form && <button onClick={() => setForm("seed")}><Rows3 /> Review demo load</button>}
        {view === "imports" && !form && candidate?.status === "candidate" && <button className="is-primary" onClick={() => setForm("candidate")}><ClipboardCheck /> Review candidate</button>}
        {view === "imports" && !form && <button onClick={() => setForm("upload")}><FileUp /> Add candidate</button>}
        {view === "imports" && !form && !candidate && <button className="is-primary" onClick={() => setForm("manual")}><PencilLine /> Manual record</button>}
        {view === "imports" && form === "upload" && <button onClick={() => setForm("manual")}><PencilLine /> Manual instead</button>}
        {view === "proposals" && !form && proposal?.status === "applied" && <button className="is-primary" onClick={() => setForm("approve")}><CheckCircle2 /> Review approval</button>}
        {view === "proposals" && !form && proposal?.undo?.available && <button onClick={() => setForm("recovery")}><RotateCcw /> Review recovery</button>}
        {view === "tasks" && !form && task && ["pending", "in_progress"].includes(task.status) && <button className="is-primary" onClick={() => setForm("result")}><ClipboardCheck /> Record result</button>}
        {view === "tasks" && !form && task && task.event_revision > 0 && <button onClick={() => setForm("correction")}><RotateCcw /> Correct record</button>}
        {view === "tasks" && !form && task?.status === "recovery_required" && onOpenPlan && <button onClick={onOpenPlan}><RotateCcw /> Replan future work</button>}
      </div>
    </Shell>
  );
}

function Shell({ title, onBack, children, ...events }: { title: string; onBack: () => void; children: ReactNode; onKeyDown?: KeyboardEventHandler<HTMLElement>; onTouchStart?: TouchEventHandler<HTMLElement>; onTouchEnd?: TouchEventHandler<HTMLElement> }) {
  return <section className="integrated-records" tabIndex={0} {...events}><header><div><small>Records &amp; work</small><h2>{title}</h2></div></header>{children}</section>;
}
function homeItems(workflow: FarmerWorkflowState, session: PlanningSession | null): Array<{ view: View; name: string; detail: string; count: number }> { return [
  { view: "setup", name: "Farm setup", detail: "Review a complete farm JSON document or the synthetic demo before creating a new version.", count: 2 },
  { view: "imports", name: "Farm records", detail: "Import accounting, documents or photos; review every candidate explicitly.", count: workflow.inbox.length },
  { view: "orders", name: "Confirmed orders", detail: "Browse dated commitments with stable record identities.", count: session?.farm.orders.length || 0 },
  { view: "beds", name: "Growing spaces", detail: "Inspect bed identity, system, crop and reported stage.", count: session?.farm.beds.length || 0 },
  { view: "inventory", name: "Inventory", detail: "Inspect reported lots and quantities separately from projections.", count: Array.isArray(session?.farm.inventory) ? session.farm.inventory.length : 0 },
  { view: "proposals", name: "Proposal approvals", detail: "Inspect revision-bound calculations before creating simulated tasks.", count: workflow.proposals.length },
  { view: "tasks", name: "Tasks & results", detail: "Record reported outcomes, corrections and recovery triggers.", count: workflow.tasks.length },
  { view: "verify", name: "Verify & recover", detail: "Compare farmer-reported outcomes with the saved plan, then explicitly replan future work.", count: workflow.tasks.filter(item => item.event_revision > 0).length },
  { view: "history", name: "Workflow history", detail: "Read the complete saved event sequence without recalculation.", count: workflow.events.length },
]; }
function Home({ workflow, session, index, setIndex }: { workflow: FarmerWorkflowState; session: PlanningSession | null; index: number; setIndex: (value: number) => void; open: (view: View) => void }) { const items = homeItems(workflow, session), item = items[index]; return <><nav className="ir-pager" aria-label="Records and work categories"><button disabled={index === 0} onClick={() => setIndex(index - 1)}><ArrowLeft /> Previous</button><span>Records &amp; work {index + 1} of {items.length}</span><button disabled={index === items.length - 1} onClick={() => setIndex(index + 1)}>Next <ArrowRight /></button></nav><article className="ir-card"><div className="ir-card__heading"><div><small>Records &amp; work</small><h3>{item.name}</h3></div><span>{item.count}</span></div><p>{item.detail}</p>{!session && item.view !== "setup" && <p className="ir-note">No planning session is active.</p>}</article></>; }
function CandidateCard({ item }: { item: FarmerImport }) { const source = `/api/v1/farm-workflow/imports/${encodeURIComponent(item.candidate_id)}/source`; return <Card eyebrow={item.source_kind.replaceAll("_", " ")} title={item.source_name} status={item.status}><dl><Fact k="Record identity" v={item.candidate_id} /><Fact k="Authority" v={String(item.authority || "review candidate")} /><Fact k="Planning use" v={item.status === "candidate" ? "Inactive until reviewed" : item.planning_eligible ? "Eligible reviewed evidence" : "Observation only"} /><Fact k="Extracted rows" v={String(item.rows?.length || 0)} /></dl>{!!item.warnings?.length && <div className="ir-warning"><strong>Warnings</strong><ul>{item.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></div>}<Rows rows={item.rows || []} /><div className="ir-source-actions"><a href={source} target="_blank" rel="noreferrer">Inspect source</a><a href={`${source}/download`} download>Download source</a></div></Card>; }
function CandidateReview({ item, busy, decide }: { item: FarmerImport; busy: boolean; decide: (decision: "confirm" | "reject", note?: string) => void }) { const [note, setNote] = useState(""); return <Card eyebrow="Explicit review" title={item.source_name} status="candidate"><p>Confirm only the extracted fields you have reviewed. Photos and documents remain observations and never gain yield authority.</p><Rows rows={item.rows || []} /><label>Review note (optional)<textarea value={note} onChange={(event) => setNote(event.target.value)} /></label><div className="ir-inline-actions"><button disabled={busy} onClick={() => decide("reject", note)}>Reject candidate</button><button className="is-primary" disabled={busy} onClick={() => decide("confirm", note)}>Confirm reviewed fields</button></div></Card>; }
function ProposalCard({ item, session }: { item: FarmerProposal; session: PlanningSession | null }) { const stale = session && item.session_id === session.id && item.base_revision > session.revision; return <Card eyebrow={`Proposal revision ${item.proposal_revision}`} title={String(item.selected_strategy_id || item.id)} status={item.status}><p>Base session revision {item.base_revision}. Approval creates simulation tasks only.</p>{stale && <p className="ir-warning">The proposal refers to a newer revision than the loaded session.</p>}<Metrics values={item.recalculated_metrics || item.calculated_metrics} />{item.inverse_of_proposal_id && <p>Recovery inverse of {item.inverse_of_proposal_id}.</p>}</Card>; }
function ApprovalReview({ item, busy, approve }: { item: FarmerProposal; busy: boolean; approve: () => void }) { return <Card eyebrow="Approval review" title={`Proposal revision ${item.proposal_revision}`} status={item.status}><p>This explicit approval is bound to proposal {item.id} and creates simulated actions. It does not authorize real farm operations.</p><Metrics values={item.recalculated_metrics || item.calculated_metrics} />{item.metric_deltas && <><strong>Signed changes after recalculation</strong><Metrics values={item.metric_deltas} /></>}<button className="is-primary ir-submit" disabled={busy} onClick={approve}>{busy ? <LoaderCircle className="spin" /> : <CheckCircle2 />} Approve revision &amp; create tasks</button></Card>; }
function RecoveryReview({ item, busy, create }: { item: FarmerProposal; busy: boolean; create: () => void }) { return <Card eyebrow="Recovery review" title={`Inverse proposal for revision ${item.proposal_revision}`} status="not created"><p>This creates a new proposal against eligible session revision {item.undo?.expected_session_revision ?? "not supplied"}. It keeps the original proposal, event history and executed work; only future work can change.</p>{item.metric_deltas && <Metrics values={item.metric_deltas} />}<button className="is-primary ir-submit" disabled={busy || !item.undo?.available} onClick={create}>{busy ? <LoaderCircle className="spin" /> : <RotateCcw />} Create recovery proposal</button></Card>; }
function TaskCard({ item }: { item: FarmerTask }) { return <Card eyebrow={`Due ${civil(item.due_date)}`} title={`${item.action.replaceAll("_", " ")} · ${item.crop_id || "farm task"}`} status={item.status}><dl><Fact k="Location" v={String(item.location || "Not specified")} /><Fact k="Planned" v={item.planned_quantity == null ? "No quantity" : `${item.planned_quantity} ${item.unit || ""}`} /><Fact k="Reported" v={item.actual_quantity == null ? "Not reported" : `${item.actual_quantity} ${item.unit || ""}`} /></dl>{item.recovery?.required && <p className="ir-warning"><strong>Recovery required.</strong> {item.recovery.reason || "Record the outcome; completed work remains in the ledger and only future work may be replanned."}</p>}<ul>{item.checklist.map((entry) => <li key={entry}>{entry}</li>)}</ul><small>Event revision {item.event_revision}</small></Card>; }
function EventCard({ item }: { item: Record<string, unknown> }) { return <Card eyebrow={civil(String(item.occurred_at || item.created_at || item.timestamp || item.date || ""))} title={String(item.event_type || item.type || item.action || "Saved workflow event")} status={String(item.status || "recorded")}><dl>{Object.entries(item).filter(([key]) => !["event_type", "type", "action", "status"].includes(key)).slice(0, 12).map(([key, value]) => <Fact key={key} k={key.replaceAll("_", " ")} v={display(value)} />)}</dl><p className="ir-note">Saved replay only. Opening this card performs no calculation or inference.</p></Card>; }
function OrderCard({ item }: { item: FarmOrder }) { return <Card eyebrow={`Order · ${item.id}`} title={`${item.crop_id.replaceAll("_", " ")} commitment`} status="confirmed"><dl><Fact k="Stable record ID" v={item.id} /><Fact k="Due date" v={civil(item.due_date)} /><Fact k="Booked quantity" v={`${item.quantity_kg} kg`} /><Fact k="Booked price" v={`SGD ${item.price_sgd_per_kg}/kg`} /></dl><p className="ir-note">This is a confirmed record. Forecast demand and projected delivery remain separate.</p></Card>; }
function BedCard({ item }: { item: Bed }) { return <Card eyebrow={`Growing space · ${item.id}`} title={item.name} status={item.stage}><dl><Fact k="Stable record ID" v={item.id} /><Fact k="System" v={item.system.replaceAll("_", " ")} /><Fact k="Area" v={`${item.area_m2} m²`} /><Fact k="Reported crop" v={item.crop_id?.replaceAll("_", " ") || "None"} /><Fact k="Batch ID" v={item.batch_id || "None"} /></dl><p className="ir-note">The reported stage is a farm record; future allocations are projections.</p></Card>; }
function InventoryCard({ item }: { item: Record<string, unknown> }) { const id = String(item.id || item.lot_id || item.batch_id || "identity unavailable"); return <Card eyebrow={`Inventory lot · ${id}`} title={String(item.crop_id || item.name || "Reported inventory").replaceAll("_", " ")} status={String(item.status || "reported")}><dl><Fact k="Stable record ID" v={id} /><Fact k="Reported quantity" v={`${display(item.quantity_kg ?? item.quantity)} ${String(item.unit || "kg")}`} /><Fact k="Recorded date" v={civil(String(item.harvested_date || item.recorded_at || item.date || ""))} /><Fact k="Expiry" v={civil(String(item.expires_on || item.expiry_date || ""))} /><Fact k="Origin" v={display(item.origin || item.source)} /></dl><p className="ir-note">Reported inventory is shown as recorded and is not a projected harvest.</p></Card>; }
function VerifyCard({ session, tasks, onOpenPlan }: { session: PlanningSession | null; tasks: FarmerTask[]; onOpenPlan?: () => void }) { const report = session?.reported_forecast as { metrics?: Record<string, number | null>; basis?: string; source_result_id?: string; recovery_required?: boolean; independently_verified?: boolean } | undefined, recovery = tasks.filter(item => item.status === "recovery_required"); const metrics = report?.metrics || {}; const selected = Object.fromEntries(["booked_delivered_kg", "booked_shortfall_kg", "rejected_kg", "margin_sgd"].filter(key => key in metrics).map(key => [key, metrics[key]])); return <Card eyebrow="Farmer-reported outcome" title="Verify recorded work and future impact" status={report?.recovery_required ? "recovery required" : report ? "recorded" : "awaiting result"}>{report ? <><p>Server-derived projection from farmer-reported task events. It is not independently verified.</p><Metrics values={selected} /><dl><Fact k="Outcome basis" v={String(report.basis || "user reported projection").replaceAll("_", " ")} /><Fact k="Source result" v={String(report.source_result_id || "Not supplied")} /></dl></> : <p>No reported forecast is available yet. Record a task result before comparing outcome changes.</p>}<p>Completed work and prior events remain recorded. Recovery may change future simulation work only and must start from the current session revision.</p>{recovery.map(item => <p className="ir-warning" key={item.id}><strong>{item.id}</strong> · {item.recovery?.reason || "Reported result requires recovery."}</p>)}{onOpenPlan && recovery.length > 0 && <button className="is-primary" onClick={onOpenPlan}>Review future-only plan</button>}</Card>; }

function FarmImportForm({ busy, submit }: { busy: boolean; submit: (farm: unknown) => void }) { const [json, setJson] = usePersistentState("v15-farm-json-draft", ""), [preview, setPreview] = useState<Record<string, unknown> | null>(null), [parseError, setParseError] = useState(""); const review = () => { try { const parsed: unknown = JSON.parse(json); const farm = typeof parsed === "object" && parsed !== null && "farm" in parsed ? (parsed as { farm: unknown }).farm : parsed; if (!farm || typeof farm !== "object" || Array.isArray(farm)) throw new Error("The JSON must contain one farm object."); if (new Blob([json]).size > 1_000_000) throw new Error("Farm JSON must be under 1 MB."); setPreview(farm as Record<string, unknown>); setParseError(""); } catch (caught) { setPreview(null); setParseError(problem(caught, "The JSON could not be parsed.")); } }; return <Card eyebrow="Validated farm setup" title={preview ? "Review farm import" : "Paste farm JSON"} status={preview ? "review required" : "draft"}>{!preview ? <><p>Paste the complete farm object, or an object with a <code>farm</code> field. Parsing creates a local preview and does not import anything.</p><Field label="Farm JSON"><textarea className="ir-json" value={json} onChange={(event) => setJson(event.target.value)} spellCheck={false} /></Field>{parseError && <p className="ir-error" role="alert">{parseError}</p>}<button className="is-primary ir-submit" disabled={!json.trim()} onClick={review}>Review parsed farm</button></> : <><p>Confirm this exact parsed object. The backend performs authoritative schema validation and creates a new farm version only after this action.</p><dl><Fact k="Farm ID" v={display(preview.id)} /><Fact k="Name" v={display(preview.name)} /><Fact k="Version" v={display(preview.version)} /><Fact k="Orders" v={Array.isArray(preview.orders) ? String(preview.orders.length) : "Missing"} /><Fact k="Beds" v={Array.isArray(preview.beds) ? String(preview.beds.length) : "Missing"} /><Fact k="Data origin" v={display(preview.data_mode)} /></dl><div className="ir-inline-actions"><button disabled={busy} onClick={() => setPreview(null)}>Edit JSON</button><button className="is-primary" disabled={busy} onClick={() => submit(preview)}>Confirm validated import</button></div></>}</Card>; }
function SeedReview({ busy, submit }: { busy: boolean; submit: () => void }) { return <Card eyebrow="Farm setup review" title="Load synthetic demo" status="not loaded"><p>This requests the backend’s versioned synthetic demonstration fixture. It replaces the active sandbox farm only after explicit confirmation; it does not copy lesson state.</p><dl><Fact k="Fixture" v="synthetic_demo" /><Fact k="Origin" v="Project-authored synthetic records" /><Fact k="Operations" v="Simulation only" /></dl><button className="is-primary ir-submit" disabled={busy} onClick={submit}>Confirm demo load</button></Card>; }

function UploadForm({ busy, submit }: { busy: boolean; submit: (file: File) => void }) { const [file, setFile] = useState<File | null>(null); return <Card eyebrow="New review candidate" title="Import a farm record" status="unsaved"><p>CSV and spreadsheets are accounting candidates. Documents and photos are observations. Every upload needs a separate review.</p><label>Candidate file<input type="file" accept=".csv,.xlsx,.xls,.doc,.docx,.pdf,image/*" onChange={(event) => setFile(event.target.files?.[0] || null)} /></label><button className="is-primary ir-submit" disabled={!file || busy} onClick={() => file && submit(file)}>{busy ? <LoaderCircle className="spin" /> : <FileUp />} Upload candidate</button></Card>; }
function ManualForm({ session, busy, submit }: { session: PlanningSession; busy: boolean; submit: (name: string, row: Record<string, unknown>) => void }) { const [name, setName] = usePersistentState("v15-manual-name", "Farmer manual record"), [date, setDate] = usePersistentState("v15-manual-date", session.farm.planning_date), [kind, setKind] = usePersistentState("v15-manual-kind", "expense"), [reference, setReference] = usePersistentState("v15-manual-reference", `manual-${Date.now()}`), [target, setTarget] = usePersistentState("v15-manual-target", ""), [description, setDescription] = usePersistentState("v15-manual-description", ""), [amount, setAmount] = usePersistentState("v15-manual-amount", ""); const valid = name.trim() && date && reference.trim() && amount !== "" && (kind !== "correction" || target.trim()); return <Card eyebrow="Manual entry" title="Create an unverified candidate" status="unsaved"><p>The record stays inactive until it is reviewed on its own candidate card.</p><div className="ir-form-grid"><Field label="Source name"><input value={name} onChange={(e) => setName(e.target.value)} /></Field><Field label="Record date"><input type="date" value={date} onChange={(e) => setDate(e.target.value)} /></Field><Field label="Record kind"><select value={kind} onChange={(e) => setKind(e.target.value)}><option value="expense">Expense</option><option value="sale">Sale</option><option value="correction">Correction</option></select></Field><Field label="Record reference"><input value={reference} onChange={(e) => setReference(e.target.value)} /></Field>{kind === "correction" && <Field label="Target transaction reference"><input value={target} onChange={(e) => setTarget(e.target.value)} /></Field>}<Field label="Description (optional)"><input value={description} onChange={(e) => setDescription(e.target.value)} /></Field><Field label={kind === "correction" ? "Signed correction amount (SGD)" : "Amount (SGD)"}><input type="number" min={kind === "correction" ? undefined : "0"} step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} /></Field></div>{kind === "correction" && <p className="ir-note">Use a signed delta and target one distinct reviewed sale or expense reference.</p>}<button className="is-primary ir-submit" disabled={!valid || busy} onClick={() => submit(name.trim(), { date, kind, reference: reference.trim(), corrects_reference: kind === "correction" ? target.trim() : undefined, description: description.trim(), amount, currency: "SGD", provenance: "farmer_manual_unverified" })}>Create review candidate</button></Card>; }
function ResultForm({ task, photos, busy, submit }: { task: FarmerTask; photos: FarmerImport[]; busy: boolean; submit: (v: { status: "completed" | "failed"; quantity: number; rejected: number; note: string; checks: string[]; photo: string }) => void }) { const [status, setStatus] = usePersistentState<"completed" | "failed">(`v15-result-${task.id}-status`, "completed"), [quantity, setQuantity] = usePersistentState(`v15-result-${task.id}-quantity`, Number(task.actual_quantity ?? task.planned_quantity ?? 0)), [rejected, setRejected] = usePersistentState(`v15-result-${task.id}-rejected`, 0), [note, setNote] = usePersistentState(`v15-result-${task.id}-note`, ""), [checks, setChecks] = usePersistentState<string[]>(`v15-result-${task.id}-checks`, []), [photo, setPhoto] = usePersistentState(`v15-result-${task.id}-photo`, ""); return <Card eyebrow="Farmer-reported result" title={task.action.replaceAll("_", " ")} status="unsaved"><p>Reported values remain distinct from projections. A failed result can trigger recovery while retaining executed work.</p><Field label="Result"><select value={status} onChange={(e) => setStatus(e.target.value as typeof status)}><option value="completed">Completed</option><option value="failed">Blocked or failed</option></select></Field>{task.unit && <Field label={`Actual quantity (${task.unit})`}><input type="number" min="0" step="0.01" value={quantity} onChange={(e) => setQuantity(Number(e.target.value))} /></Field>}{task.action === "delivery" && <Field label="Rejected quantity (kg)"><input type="number" min="0" step="0.01" value={rejected} onChange={(e) => setRejected(Number(e.target.value))} /></Field>}<fieldset><legend>Checklist completed</legend>{task.checklist.map((entry) => <label key={entry}><input type="checkbox" checked={checks.includes(entry)} onChange={(e) => setChecks((old) => e.target.checked ? [...old, entry] : old.filter((value) => value !== entry))} /> {entry}</label>)}</fieldset>{photos.length > 0 && <Field label="Reviewed task photo"><select value={photo} onChange={(e) => setPhoto(e.target.value)}><option value="">No photo</option>{photos.map((item) => <option key={item.candidate_id} value={item.candidate_id}>{item.source_name}</option>)}</select></Field>}<Field label="Farmer note"><textarea required value={note} onChange={(e) => setNote(e.target.value)} /></Field><button className="is-primary ir-submit" disabled={!note.trim() || busy} onClick={() => submit({ status, quantity, rejected, note: note.trim(), checks, photo })}>Review &amp; save reported result</button></Card>; }
function CorrectionForm({ task, busy, submit }: { task: FarmerTask; busy: boolean; submit: (value: number | string | null, reason: string, field?: string) => void }) { const [field, setField] = usePersistentState(`v15-correction-${task.id}-field`, "actual_quantity"), [value, setValue] = usePersistentState(`v15-correction-${task.id}-value`, String(task.actual_quantity ?? "")), [reason, setReason] = usePersistentState(`v15-correction-${task.id}-reason`, ""); const numeric = field === "actual_quantity" || field === "rejected_quantity"; const corrected: number | string | null = field === "photo_reference" && !value ? null : numeric ? Number(value) : value; return <Card eyebrow={`Correction from event revision ${task.event_revision}`} title="Correct a reported field" status="unsaved"><p>The prior event remains in history. Saving adds an auditable field-specific correction.</p><Field label="Field"><select value={field} onChange={(event) => { setField(event.target.value); setValue(event.target.value === "actual_quantity" ? String(task.actual_quantity ?? "") : event.target.value === "rejected_quantity" ? String(task.rejected_quantity ?? 0) : event.target.value === "result_note" ? String(task.result_note || "") : event.target.value === "status" ? String(task.status) : ""); }}><option value="actual_quantity">Actual quantity</option><option value="rejected_quantity">Rejected quantity</option><option value="result_note">Result note</option><option value="status">Result status</option><option value="photo_reference">Photo reference</option></select></Field><Field label="Corrected value">{field === "status" ? <select value={value} onChange={(e) => setValue(e.target.value)}><option value="completed">Completed</option><option value="failed">Failed</option><option value="recovery_required">Recovery required</option></select> : <input type={numeric ? "number" : "text"} min={numeric ? "0" : undefined} step={numeric ? "0.01" : undefined} value={value} onChange={(e) => setValue(e.target.value)} />}</Field><Field label="Reason"><input value={reason} onChange={(e) => setReason(e.target.value)} /></Field><button className="is-primary ir-submit" disabled={!reason.trim() || (numeric && (!value || Number(value) < 0)) || busy} onClick={() => submit(corrected, reason.trim(), field)}>Review &amp; save correction</button></Card>; }

function Card({ eyebrow, title, status, children }: { eyebrow: string; title: string; status: string; children: ReactNode }) { return <article className="ir-card"><div className="ir-card__heading"><div><small>{eyebrow}</small><h3>{title}</h3></div><span>{status.replaceAll("_", " ")}</span></div>{children}</article>; }
function Empty({ icon, text }: { icon: ReactNode; text: string }) { return <div className="ir-empty">{icon}<p>{text}</p></div>; }
function Fact({ k, v }: { k: string; v: string }) { return <div><dt>{k}</dt><dd>{v}</dd></div>; }
function Field({ label, children }: { label: string; children: ReactNode }) { return <label>{label}{children}</label>; }
function Rows({ rows }: { rows: Record<string, unknown>[] }) { if (!rows.length) return <p className="ir-note">No structured rows were extracted. Review metadata and warnings before deciding.</p>; return <details><summary>Inspect extracted fields</summary>{rows.map((row, i) => <dl className="ir-row" key={i}>{Object.entries(row).map(([key, value]) => <Fact key={key} k={key.replaceAll("_", " ")} v={display(value)} />)}</dl>)}</details>; }
function Metrics({ values }: { values: Record<string, number | null> }) { return <dl className="ir-metrics">{Object.entries(values).map(([key, value]) => <Fact key={key} k={key.replaceAll("_", " ")} v={value == null ? "Unavailable" : Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 })} />)}</dl>; }
function title(view: View, form: Form) { if (form === "farmImport") return "Review farm JSON"; if (form === "seed") return "Review demo load"; if (form === "upload") return "Import candidate"; if (form === "manual") return "Manual record"; if (form === "candidate") return "Review candidate"; if (form === "approve") return "Review approval"; if (form === "recovery") return "Review recovery"; if (form === "result") return "Record task result"; if (form === "correction") return "Correct task record"; return ({ home: "Records & work", setup: "Farm setup", imports: "Farm records", orders: "Confirmed orders", beds: "Growing spaces", inventory: "Inventory", proposals: "Proposal approvals", tasks: "Tasks & results", verify: "Verify & recover", history: "Workflow history" } as const)[view]; }
function label(view: View) { return ({ setup: "Setup", imports: "Record", orders: "Order", beds: "Bed", inventory: "Lot", proposals: "Proposal", tasks: "Task", verify: "Outcome", history: "Event", home: "Card" } as const)[view]; }
function display(value: unknown): string { if (value == null || value === "") return "Not supplied"; if (typeof value === "object") return JSON.stringify(value); return String(value); }
function civil(value: string) { if (!value) return "Date not recorded"; return value.slice(0, 10); }
function problem(error: unknown, fallback: string) { return error instanceof Error && error.message ? error.message : fallback; }
function usePersistentState<T>(key: string, initial: T) { const [value, setValue] = useState<T>(() => { try { const saved = localStorage.getItem(key); return saved == null ? initial : JSON.parse(saved) as T; } catch { return initial; } }); useEffect(() => { try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* draft persistence is best effort */ } }, [key, value]); return [value, setValue] as const; }
