import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ADVISORS } from "../lib/game";
import { request } from "../lib/api";
import { editionStorageKey } from "../lib/edition";
import { researchApi, type ActualConversation, type CouncilConcept, type ResearchActionBody, type ResearchReport, type ResearchResult, type ResearchSession, type SteeringMode } from "../lib/research";
import type { CardAction, FarmCard, ResearchTarget } from "../lib/cards";
import { FrozenFactEvidence, QualitativeContextReferences } from "./AdvisorEvidence";
import { RecordFacts, ToolCard, type ToolAction } from "./ToolCard";
import "./IntegratedResearch.css";

type View = "sessions" | "overview" | "session" | "configure" | "context" | "discussion" | "proposal" | "calculate" | "challenge" | "results" | "history" | "actual" | "report";
type Summary = Awaited<ReturnType<typeof researchApi.list>>["sessions"][number];
type HistoryPage = { revisions: Array<{ revision: number; payload: Record<string, unknown> }>; next_cursor: number | null; origin: string; inference_triggered: false };
const policies = ["Lean", "Balanced", "Resilient"] as const;
const isRunning = (session: ResearchSession | null) => ["queued", "running", "cancellation_requested"].includes(String(session?.numerical_calculation_status));
const currentResult = (session: ResearchSession | null) => session?.results.find((result) => result.version === session.input_version);
const problem = (error: unknown) => error instanceof Error ? error.message : "The research request failed. Your drafts remain saved.";

function useDraft<T>(key: string, initial: T) {
  const [value, setValue] = useState<T>(() => { try { const saved = localStorage.getItem(editionStorageKey(key)); return saved == null ? initial : JSON.parse(saved) as T; } catch { return initial; } });
  useEffect(() => { try { localStorage.setItem(editionStorageKey(key), JSON.stringify(value)); } catch { /* best-effort draft persistence */ } }, [key, value]);
  return [value, setValue] as const;
}

export default function IntegratedResearch({ onClose, initialTarget = "overview" }: { onClose: () => void; initialTarget?: ResearchTarget }) {
  const [view, setView] = useState<View>("sessions"), [index, setIndex] = useState(0), [busy, setBusy] = useState(false), [error, setError] = useState("");
  const [sessions, setSessions] = useState<Summary[]>([]), [session, setSession] = useState<ResearchSession | null>(null), [report, setReport] = useState<ResearchReport | null>(null);
  const [history, setHistory] = useState<HistoryPage["revisions"]>([]), [historyCursor, setHistoryCursor] = useState<number | null>(null);
  const [concept, setConcept] = useDraft<CouncilConcept>("research-concept", "sheet"), [steering, setSteering] = useDraft<SteeringMode>("research-steering", "continuous");
  const [selectionMode, setSelectionMode] = useDraft<"chips" | "cards">("research-selection", "chips"), [animation, setAnimation] = useDraft<"static" | "transition">("research-animation", "static");
  const [draft, setDraft] = useDraft("research-message-draft", ""), [advisor, setAdvisor] = useDraft("research-advisor", "Planner");
  const [operation, setOperation] = useDraft<"reserve_bed" | "order_status" | "labour">("research-operation", "reserve_bed");
  const [bed, setBed] = useDraft("research-bed", "bed-04"), [order, setOrder] = useDraft("research-order", "research-extra-order"), [start, setStart] = useDraft("research-start", ""), [end, setEnd] = useDraft("research-end", ""), [labour, setLabour] = useDraft("research-labour", 75), [confirmed, setConfirmed] = useDraft("research-confirmed", false);
  const [challenge, setChallenge] = useDraft("research-challenge", "This crop is indoors; explain why outdoor rainfall affects its yield."), [resolution, setResolution] = useDraft<"evidence" | "corrected" | "unresolved" | "reject">("research-resolution", "corrected"), [policy, setPolicy] = useDraft<(typeof policies)[number]>("research-policy", "Balanced");
  const [actualAdvisor, setActualAdvisor] = useDraft("research-actual-advisor", "asha"), [actualPrompt, setActualPrompt] = useDraft("research-actual-prompt", "Explain the current same-policy trade-off using this frozen result."), [actualId, setActualId] = useState(""), [actual, setActual] = useState<ActualConversation | null>(null);
  const [actualBindings, setActualBindings] = useDraft<Record<string, string>>("research-actual-bindings", {}), [actualNeedsRefresh, setActualNeedsRefresh] = useState(false), [acceptedPrompt, setAcceptedPrompt] = useState("");
  const current = useRef<ResearchSession | null>(null);
  const menuOrigin = useRef<{ index: number; scroll: number; focus: HTMLElement | null }>({ index: 0, scroll: 0, focus: null });
  const update = useCallback((next: ResearchSession) => { if (current.current?.id === next.id && next.revision < current.current.revision) return; current.current = next; setSession(next); setError(""); }, []);
  const act = async (run: () => Promise<void>) => { if (busy) return; setBusy(true); setError(""); try { await run(); } catch (caught) { const failure = caught as Error & { status?: number }; const message = problem(caught); setError(message); if (session && (failure.status == null || failure.status === 409 || failure.status >= 500)) try { update(await researchApi.get(session.id)); setError(`${message} Server state was refreshed before another action.`); } catch { /* retain original error and draft */ } } finally { setBusy(false); } };
  const refreshList = async () => setSessions((await researchApi.list()).sessions);
  useEffect(() => { void act(refreshList); }, []);
  useEffect(() => { if (!session || !isRunning(session)) return; const timer = window.setInterval(() => void researchApi.get(session.id).then(update).catch(() => {}), 1800); return () => window.clearInterval(timer); }, [session?.id, session?.revision, session?.numerical_calculation_status, update]);
  useEffect(() => { if (!actualId || !["QUEUED", "RUNNING"].includes(String(actual?.last_request_status).toUpperCase())) return; const timer = window.setInterval(() => void researchApi.getActual(actualId).then(setActual).catch((caught) => setError(problem(caught))), 1600); return () => window.clearInterval(timer); }, [actualId, actual?.last_request_status]);
  const actualBindingKey = session ? `${session.id}:${session.input_version}:${actualAdvisor}` : "";
  useEffect(() => { const id = actualBindingKey ? actualBindings[actualBindingKey] : ""; setActualId(id || ""); setActual(null); setActualNeedsRefresh(false); setAcceptedPrompt(""); if (id) void researchApi.getActual(id).then((saved) => { setActual(saved); const last = [...saved.messages].reverse().find((message) => message.speaker === "user"); if (last) setAcceptedPrompt(last.content); }).catch((caught) => { setActualNeedsRefresh(true); setError(problem(caught)); }); }, [actualBindingKey, actualBindings]);
  useEffect(() => { if (!session || start) return; const raw = session.farm as typeof session.farm & { batches?: Array<Record<string, unknown>> }; const batch = (raw.batches || []).find((row) => row.bed_id === bed); const base = new Date(`${String(batch?.harvest_date || session.farm.planning_date || session.farm.cutoff).slice(0, 10)}T00:00:00Z`); base.setUTCDate(base.getUTCDate() + 3); const last = new Date(`${String(session.farm.planning_date || session.farm.cutoff).slice(0, 10)}T00:00:00Z`); last.setUTCDate(last.getUTCDate() + Number(session.farm.horizon_days) - 1); setStart(base.toISOString().slice(0, 10)); setEnd(last.toISOString().slice(0, 10)); }, [session, bed, start, setStart, setEnd]);

  const send = (body: Omit<ResearchActionBody, "revision">) => session && act(async () => update(await researchApi.act(session.id, { ...body, revision: session.revision } as ResearchActionBody)));
  const targetView = (target: ResearchTarget): View => target === "overview" ? "overview" : target;
  const enterStudy = async (next: ResearchSession) => {
    update(next); setIndex(0);
    if (initialTarget === "history") {
      const page = await request<HistoryPage>(`/council-research/${encodeURIComponent(next.id)}/history?after=-1&limit=20`);
      setHistory(page.revisions); setHistoryCursor(page.next_cursor);
    }
    setView(targetView(initialTarget));
  };
  const openSession = (id: string) => void act(async () => enterStudy(await researchApi.get(id)));
  const create = () => void act(async () => { const next = await researchApi.create(concept, steering); await enterStudy(next); await refreshList(); });
  const rememberMenuOrigin = () => { menuOrigin.current = { index, scroll: window.scrollY, focus: document.activeElement as HTMLElement }; };
  const openHistory = () => session && void act(async () => { rememberMenuOrigin(); const page = await request<HistoryPage>(`/council-research/${encodeURIComponent(session.id)}/history?after=-1&limit=20`); setHistory(page.revisions); setHistoryCursor(page.next_cursor); setIndex(0); setView("history"); });
  const loadMoreHistory = () => session && historyCursor !== null && void act(async () => { const page = await request<HistoryPage>(`/council-research/${encodeURIComponent(session.id)}/history?after=${historyCursor}&limit=20`); setHistory((currentHistory) => [...currentHistory, ...page.revisions]); setHistoryCursor(page.next_cursor); });
  const back = () => { setError(""); if (view === "sessions") onClose(); else if (view === "overview") { setIndex(0); setView("sessions"); void refreshList(); } else { const origin = menuOrigin.current; setView("overview"); setIndex(0); requestAnimationFrame(() => { (origin.focus?.isConnected ? origin.focus : document.querySelector<HTMLElement>(".integrated-tool__card"))?.focus({ preventScroll: true }); window.scrollTo(0, origin.scroll); }); } };

  const menu = ["Presentation", "Frozen context", "Discussion", "Reviewed proposal", "Calculation", "Challenge", "Results", "Revision history", "Actual adviser", "Research report"];
  let title = "Saved Council research", count = Math.max(1, sessions.length), body: React.ReactNode = sessions[index] ? <><h3>Study created {new Date(sessions[index].created_at).toLocaleString()}</h3><RecordFacts value={sessions[index]}/><p>Opening is read-only and does not calculate or invoke a provider.</p></> : <p>No saved research sessions. Start a fresh isolated study.</p>;
  let primary: ToolAction | undefined = sessions[index] ? { label: "Open saved study", run: () => openSession(sessions[index].id) } : { label: "Start study", run: create };
  let secondary: ToolAction | undefined = { label: "New study", run: create };

  if (view === "overview" && session) {
    title = `Council research v${session.input_version}`; count = 0;
    const jumps: Array<{ label: string; view: View; note: string }> = [
      { label: "Frozen context", view: "context", note: "Choose exact farm records for the discussion." },
      { label: "Scripted discussion", view: "discussion", note: "Read the full local transcript and add a bounded turn." },
      { label: "Review an edit", view: "proposal", note: "Draft and explicitly apply one typed research change." },
      { label: "Calculate", view: "calculate", note: "Run the local numerical planner for this version." },
      { label: "Challenge evidence", view: "challenge", note: "Record whether evidence corrected or left a claim unresolved." },
      { label: "Compare results", view: "results", note: "Inspect frozen strategies before choosing a simulation-only result." },
      { label: "Revision history", view: "history", note: "Replay recorded revisions without inference." },
      { label: "Ask a specialist", view: "actual", note: "An explicit provider action about one completed frozen result." },
      { label: "Research report", view: "report", note: "Read bundled documents, sources and review screenshots." },
    ];
    const openJump = (target: View) => {
      rememberMenuOrigin(); setIndex(0);
      if (target === "history") { openHistory(); return; }
      setView(target);
    };
    body = <div className="ix-overview"><p className="ix-lede">A saved Council study is an isolated research workspace. Its edits and chosen result remain simulation-only and never operate the farm.</p><ol className="ix-path"><li>Select frozen records and discuss the question.</li><li>Review any proposed input change before applying it.</li><li>Calculate locally, challenge assumptions, then compare saved results.</li><li>Optionally ask one specialist through an explicit provider action.</li></ol><div className="ix-jump-grid">{jumps.map((jump) => <button type="button" key={jump.view} onClick={() => openJump(jump.view)}><strong>{jump.label}</strong><span>{jump.note}</span></button>)}</div><p>Planning Council review of an ordinary farm proposal lives under Knowledge. This study keeps a separate frozen research history.</p></div>;
    primary = { label: "Open guided card deck", run: () => { setIndex(0); setView("session"); } }; secondary = undefined;
  } else if (view === "session") {
    title = session ? `Research v${session.input_version}` : "Research session"; count = menu.length; body = <><h3>{menu[index]}</h3><p>{["Compare interaction settings without changing numerical inputs.", "Select exact frozen beds, orders, batches or crops.", "Use the bounded scripted discussion and inspect its complete transcript.", "Create, review, apply or discard one typed research edit.", "Run, cancel or retry the local numerical planner.", "Challenge an assumption and explicitly record its evidence status.", "Inspect every saved version and choose an eligible simulation-only result.", "Replay append-only research revisions and their recorded events without inference.", "Explicitly ask DeepSeek about one frozen completed research version.", "Read the supplied research documents, sources and review screenshots."][index]}</p><RecordFacts value={{ revision: session?.revision, input_version: session?.input_version, calculation: session?.numerical_calculation_status, chosen: session?.chosen, operational_execution: session?.operational_execution }}/></>;
    primary = { label: `Open ${menu[index]}`, run: index === 7 ? openHistory : () => { const target = (["configure", "context", "discussion", "proposal", "calculate", "challenge", "results", "history", "actual", "report"] as View[])[index]; rememberMenuOrigin(); setIndex(0); setView(target); } }; secondary = undefined;
  } else if (view === "configure") {
    title = "Research presentation"; count = 0; body = <div className="ix-form"><p>Draft settings — not saved until the action below.</p><label>Layout<select value={concept} onChange={(event) => setConcept(event.target.value as CouncilConcept)}><option value="inline">Inline council</option><option value="sheet">Council sheet</option><option value="cards">Adviser cards</option></select></label><label>Participation<select value={steering} onChange={(event) => setSteering(event.target.value as SteeringMode)}><option value="continuous">Continuous steering</option><option value="checkpoints">Intervention checkpoints</option></select></label><label>Context display<select value={selectionMode} onChange={(event) => setSelectionMode(event.target.value as "chips" | "cards")}><option value="chips">Removable chips</option><option value="cards">Context cards</option></select></label><label>Change display<select value={animation} onChange={(event) => setAnimation(event.target.value as "static" | "transition")}><option value="static">Static before / after</option><option value="transition">Restrained transition</option></select></label><p>Saving presentation settings does not alter planner inputs.</p></div>; primary = { label: "Save presentation settings", run: () => send({ action: "configure", concept, steering, selection_mode: selectionMode, animation }) }; secondary = undefined;
  } else if (view === "context" && session) {
    const raw = session.farm as typeof session.farm & { batches?: Array<Record<string, unknown>>; recipes?: Array<Record<string, unknown>> }; const refs = [...session.farm.beds.map((row) => ({ ref: `bed:${row.id}`, label: `Bed · ${row.name}` })), ...session.farm.orders.map((row) => ({ ref: `order:${row.id}`, label: `Order · ${row.crop_id} · ${row.due_date}` })), ...(raw.batches || []).map((row) => ({ ref: `batch:${row.id}`, label: `Batch · ${row.id}` })), ...(raw.recipes || []).map((row) => ({ ref: `crop:${row.crop_id}`, label: `Crop · ${String(row.crop_id).replaceAll("_", " ")}` }))];
    title = "Frozen research context"; count = Math.max(1, refs.length); const item = refs[index]; body = item ? <><h3>{item.label}</h3><p>{item.ref}</p><p>{session.selected_refs.includes(item.ref) ? "Selected for the next scripted message." : "Available in this frozen research snapshot."}</p></> : <p>No context records.</p>; primary = item ? { label: session.selected_refs.includes(item.ref) ? "Remove selection" : "Select context", run: () => send({ action: "select", refs: session.selected_refs.includes(item.ref) ? session.selected_refs.filter((ref) => ref !== item.ref) : [...session.selected_refs, item.ref] }) } : undefined; secondary = undefined;
  } else if (view === "discussion" && session) {
    title = "Scripted Council transcript"; count = 0; body = <><p>Scripted dialogue and local calculation make zero provider calls. References are selected records, not factual conclusions.</p><div className="ix-transcript">{session.messages.map((message) => <article key={message.id}><header><b>{message.speaker}</b><span>{message.kind} · v{message.input_version}</span></header><p>{message.text}</p>{message.refs.length > 0 && <small>{message.refs.join(" · ")}</small>}</article>)}</div><div className="ix-form"><label>Address<select value={advisor} onChange={(event) => setAdvisor(event.target.value)}>{["Demand", "Weather", "Market", "Production", "Supply Chain", "Profit", "Planner"].map((role) => <option key={role}>{role}</option>)}</select></label><label>Saved draft<textarea value={draft} maxLength={1000} onChange={(event) => setDraft(event.target.value)} /></label></div></>; primary = { label: "Send scripted message", disabled: !draft.trim() || (session.steering === "checkpoints" && session.pending_turns.length > 0), run: () => send({ action: "say", text: draft.trim(), advisor }) }; secondary = session.pending_turns.length ? { label: session.steering === "checkpoints" ? "Show next turn" : "Stop queued turns", run: () => send({ action: session.steering === "checkpoints" ? "next" : "stop" }) } : undefined;
  } else if (view === "proposal" && session) {
    title = session.proposal ? "Review proposed edit" : "Prepare research edit"; count = 0; body = session.proposal ? <><p>Preview — not applied. Confirming creates a new frozen research input version and preserves earlier results.</p><RecordFacts value={session.proposal}/>{session.proposal.operation === "reserve_bed" && <div className="ix-form"><label>Start<input type="date" value={start} onChange={(event) => setStart(event.target.value)} /></label><label>End<input type="date" value={end} onChange={(event) => setEnd(event.target.value)} /></label></div>}</> : <div className="ix-form"><label>Edit type<select value={operation} onChange={(event) => setOperation(event.target.value as typeof operation)}><option value="reserve_bed">Reserve a bed</option><option value="order_status">Change order confirmation</option><option value="labour">Change labour ceiling</option></select></label>{operation === "reserve_bed" && <><label>Bed<select value={bed} onChange={(event) => { setBed(event.target.value); setStart(""); }} >{session.farm.beds.map((row) => <option key={row.id} value={row.id}>{row.name} · {row.id}</option>)}</select></label><label>Start<input type="date" value={start} onChange={(event) => setStart(event.target.value)} /></label><label>End<input type="date" value={end} onChange={(event) => setEnd(event.target.value)} /></label></>}{operation === "order_status" && <><label>Order<select value={order} onChange={(event) => setOrder(event.target.value)}>{session.farm.orders.map((row) => <option key={row.id} value={row.id}>{row.crop_id} · {row.due_date}</option>)}</select></label><label>State<select value={confirmed ? "confirmed" : "unconfirmed"} onChange={(event) => setConfirmed(event.target.value === "confirmed")}><option value="unconfirmed">Unconfirmed</option><option value="confirmed">Confirmed</option></select></label></>}{operation === "labour" && <label>Labour allowance (%)<input type="number" min="50" max="100" value={labour} onChange={(event) => setLabour(Number(event.target.value))} /></label>}</div>;
    primary = session.proposal ? { label: "Apply reviewed edit", run: () => send({ action: "apply", ...(session.proposal?.operation === "reserve_bed" ? { start_date: start, end_date: end } : {}) }) } : { label: "Review proposal", disabled: operation === "reserve_bed" && (!start || !end), run: () => send({ action: "propose", operation, ...(operation === "reserve_bed" ? { bed_id: bed, start_date: start, end_date: end } : operation === "order_status" ? { order_id: order, confirmed } : { labour_percent: labour }) }) }; secondary = session.proposal ? { label: "Discard proposal", run: () => send({ action: "discard" }) } : undefined;
  } else if (view === "calculate" && session) {
    const result = currentResult(session); title = "Local research calculation"; count = 0; body = <><p>Version {session.input_version} · {session.numerical_calculation_status}. The planner runs locally and does not invoke an adviser.</p><RecordFacts value={result || session.inputs}/></>; primary = isRunning(session) ? { label: "Refresh status", run: () => void act(async () => update(await researchApi.get(session.id))) } : result?.status === "FAILED" || result?.status === "CANCELLED" ? { label: "Retry calculation", run: () => send({ action: "retry_calculation" }) } : { label: result?.status === "COMPLETED" ? "Recalculate version" : "Calculate version", run: () => send({ action: "run" }) }; secondary = isRunning(session) ? { label: "Cancel calculation", run: () => send({ action: "cancel_calculation" }) } : undefined;
  } else if (view === "challenge" && session) {
    title = "Challenge and resolution"; count = 0; body = <div className="ix-form">{session.challenge ? <><RecordFacts value={session.challenge}/><label>Resolution<select value={resolution} onChange={(event) => setResolution(event.target.value as typeof resolution)}><option value="evidence">Inspect evidence only</option><option value="corrected">Corrected by evidence</option><option value="unresolved">Keep unresolved</option><option value="reject">Reject recommendation</option></select></label><p>Evidence inspection alone does not resolve a challenge. Unsupported challenges cannot be chosen.</p></> : <label>Challenge draft<textarea value={challenge} maxLength={1000} onChange={(event) => setChallenge(event.target.value)} /></label>}</div>; primary = session.challenge ? { label: "Record resolution", run: () => send({ action: "resolve", resolution }) } : { label: "Open challenge", disabled: !challenge.trim(), run: () => send({ action: "challenge", text: challenge.trim() }) }; secondary = undefined;
  } else if (view === "results" && session) {
    const results = session.results, result = results[index], strategy = result?.calculation?.strategies.find((row) => row.name === policy); title = result ? `Saved result v${result.version}` : "Saved results"; count = Math.max(1, results.length); body = result ? <><p>{result.status} · frozen {result.input_hash}</p><label>Policy<select value={policy} onChange={(event) => setPolicy(event.target.value as typeof policy)}>{policies.map((item) => <option key={item}>{item}</option>)}</select></label><RecordFacts value={strategy || result}/><p>{result.version === session.input_version ? "Current research version." : "Historical read-only result; it cannot be chosen as current."}</p></> : <p>No saved result. Calculate the current version first.</p>; primary = result ? { label: "Choose simulation-only result", disabled: result.version !== session.input_version || result.status !== "COMPLETED" || strategy?.status !== "FEASIBLE" || !!strategy?.violations.length || (!!session.challenge && session.challenge.status !== "corrected"), run: () => send({ action: "choose", policy, result_version: result.version }) } : undefined; secondary = undefined;
  } else if (view === "history") {
    const revision = history[index]; title = revision ? `Recorded revision ${revision.revision}` : "Research revision history"; count = Math.max(1, history.length); body = revision ? <><p>Recorded server revision · read-only replay · zero inference.</p><RecordFacts value={revision.payload}/></> : <p>No recorded revisions were returned.</p>; primary = historyCursor !== null ? { label: "Load next history page", run: loadMoreHistory } : undefined; secondary = undefined;
  } else if (view === "actual" && session) {
    title = "Actual adviser · frozen research"; count = 0; const completed = currentResult(session)?.status === "COMPLETED"; body = <><p>This separate, explicit action sends one question about frozen research version {session.input_version}. Browsing the session and transcript makes no provider call.</p><div className="ix-form"><label>Specialist<select value={actualAdvisor} onChange={(event) => setActualAdvisor(event.target.value)}>{ADVISORS.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.role}</option>)}</select></label><label>Saved question draft<textarea value={actualPrompt} maxLength={1000} onChange={(event) => setActualPrompt(event.target.value)} /></label></div>{actual && <section className="ix-actual"><RecordFacts value={{ snapshot_ref: actual.snapshot_ref, status: actual.last_request_status }}/>{actual.messages.map((message) => <article key={message.id}><header><b>{message.speaker_name || message.speaker}</b><span>{message.validation_status || message.evidence_status}</span></header><p>{message.content}</p><FrozenFactEvidence factRefs={message.fact_refs} renderedFacts={message.rendered_facts} catalogue={actual.typed_facts} validationStatus={message.validation_status} evidenceStatus={message.evidence_status}/><QualitativeContextReferences refs={message.tool_refs} toolResults={actual.tool_results}/></article>)}</section>}</>; primary = actualNeedsRefresh && actualId ? { label: "Refresh accepted submission", run: () => void act(async () => { const saved = await researchApi.getActual(actualId); setActual(saved); setActualNeedsRefresh(false); }) } : { label: actualId ? acceptedPrompt && actualPrompt.trim() === acceptedPrompt ? "Question accepted" : "Submit explicit question" : "Create frozen discussion", disabled: !completed || (actualId ? !actualPrompt.trim() || (acceptedPrompt !== "" && actualPrompt.trim() === acceptedPrompt) : false), run: () => void act(async () => { if (!actualId) { const created = await researchApi.createActual(session.id, session.input_version, actualAdvisor); setActualId(created.id); const nextBindings = { ...actualBindings, [actualBindingKey]: created.id }; try { localStorage.setItem(editionStorageKey("research-actual-bindings"), JSON.stringify(nextBindings)); } catch { /* best effort */ } setActualBindings(nextBindings); try { setActual(await researchApi.getActual(created.id)); } catch (caught) { setActualNeedsRefresh(true); throw caught; } } else { const submitted = actualPrompt.trim(); await researchApi.sendActual(actualId, submitted); setAcceptedPrompt(submitted); try { setActual(await researchApi.getActual(actualId)); } catch (caught) { setActualNeedsRefresh(true); throw caught; } } }) }; secondary = actualId ? { label: "Start new discussion", run: () => { setActualBindings((saved) => { const next = { ...saved }; delete next[actualBindingKey]; return next; }); setActualId(""); setActual(null); setAcceptedPrompt(""); setActualNeedsRefresh(false); } } : undefined;
  } else if (view === "report") {
    const documents = report?.documents || []; title = report?.title || "Research and reviews"; count = Math.max(1, documents.length); const document = documents[index]; body = report ? <>{document ? <details open><summary>{document.title}</summary><pre className="ix-document">{document.markdown}</pre></details> : <p>No bundled documents.</p>}<h3>Research sources</h3><ul>{report.sources.map((source) => <li key={source.url}><a href={source.url} target="_blank" rel="noreferrer">{source.title}</a></li>)}</ul><h3>Review screenshots</h3><ul>{report.screenshots.map((shot) => <li key={shot.url}><a href={shot.url} target="_blank" rel="noreferrer">{shot.title}</a></li>)}</ul></> : <p>Load the supplied research synthesis, audits, recommendations, sources and review screenshots.</p>; primary = report ? undefined : { label: "Load research report", run: () => void act(async () => setReport(await researchApi.report())) }; secondary = undefined;
  }

  const previous = count > 1 && index > 0 ? () => setIndex((value) => value - 1) : undefined;
  const next = count > 1 && index < count - 1 ? () => setIndex((value) => value + 1) : undefined;
  const displayedResult = view === "results" ? session?.results[index] : currentResult(session);
  const displayedRevision = view === "history" ? history[index] : undefined;
  const snapshotRef = view === "actual" ? actual?.snapshot_ref : null;
  const mutationViews = new Set<View>(["configure", "context", "discussion", "proposal", "calculate", "challenge", "results", "actual"]);
  const bindAction = (action: ToolAction | undefined, suffix: string): CardAction | null => action ? {
    id: `${view}-${suffix}-${action.label.toLowerCase().replaceAll(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")}`,
    label: action.label,
    eligible: !action.disabled && !busy,
    authority: mutationViews.has(view) && !/^(open|load|refresh|question accepted|start new discussion)/i.test(action.label) ? "server_mutation" : "local_navigation",
    eligibilitySource: view === "calculate" || view === "results" || (view === "proposal" && !!session?.proposal) || (view === "challenge" && !!session?.challenge) ? "server" : "local",
    ...(action.disabled || busy ? { disabledReason: busy ? "A server request is already in progress." : action.disabledReason || "The recorded server state or required input makes this action unavailable." } : {}),
  } : null;
  const actionBindings = [{ id: `${view}-back`, label: "Back", eligible: true, authority: "local_navigation", eligibilitySource: "local" } as CardAction, bindAction(primary, "primary"), bindAction(secondary, "secondary")].filter((item): item is CardAction => item !== null);
  const entity = view === "sessions"
    ? { id: sessions[index]?.id || "research-session-index", kind: sessions[index] ? "research_session" : "research_session_index" }
    : view === "results" && displayedResult
      ? { id: `${session?.id}:result:${displayedResult.version}`, kind: "research_result" }
      : view === "history" && displayedRevision
        ? { id: `${session?.id}:revision:${displayedRevision.revision}`, kind: "research_revision" }
        : view === "actual" && actualId
          ? { id: actualId, kind: "conversation" }
          : view === "report"
            ? { id: "council-research-report", kind: "research_report" }
            : { id: session?.id || "research-session", kind: "research_session" };
  const reportProvenance = view === "report" && report ? [...report.sources.map((source) => source.url), ...report.screenshots.map((shot) => shot.url)] : [];
  const researchCard: FarmCard = {
    id: `research:${view}:${entity.id}:${index}`,
    entityId: entity.id,
    entityKind: entity.kind,
    title,
    provenance: reportProvenance.length ? reportProvenance : view === "actual" && actualId ? [actualId] : displayedResult?.input_hash ? [displayedResult.input_hash] : [],
    binding: {
      sessionId: view === "sessions" || view === "report" ? null : session?.id || null,
      inputHash: displayedResult?.input_hash || null,
      revision: view === "history" ? displayedRevision?.revision ?? null : view === "sessions" || view === "report" ? null : session?.revision ?? null,
      resultId: null,
      snapshotId: typeof snapshotRef === "string" ? snapshotRef : snapshotRef && typeof snapshotRef.id === "string" ? snapshotRef.id : null,
    },
    boardTargets: session ? [...new Set([
      ...session.selected_refs.filter((ref) => ref.startsWith("bed:")).map((ref) => ref.slice(4)),
      ...(session.proposal?.bed_id ? [session.proposal.bed_id] : []),
    ])] : [],
    actions: actionBindings,
    outcomeBasis: view === "results" || view === "calculate" ? "projection" : null,
  };
  return <ToolCard card={researchCard} title={title} onBack={back} primary={primary} secondary={secondary} previous={previous} next={next} position={count > 1 ? `${index + 1} of ${count}` : undefined} busy={busy} error={error}>{body}</ToolCard>;
}
