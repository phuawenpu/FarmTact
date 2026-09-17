import { useCallback, useEffect, useMemo, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";
import { api } from "../lib/api";
import { ADVISORS, type Advisor, type Conversation } from "../lib/game";
import { farmerWorkflowApi, planningApi, rememberedPlanningSession, type FarmerAssumptions, type FarmerProposal, type PlanningSession } from "../lib/planning";
import type { Bootstrap, Crop, EvidenceRecord, Source } from "../lib/types";
import { AdvisorEvidence, FrozenFactEvidence } from "./AdvisorEvidence";
import { RecordFacts } from "./ToolCard";
import BoundCard from "./BoundCard";
import type { FarmCard } from "../lib/cards";
import "./IntegratedKnowledge.css";

type Card =
  | { kind: "crop"; id: string; crop: Crop }
  | { kind: "source"; id: string; source: Source }
  | { kind: "advisor"; id: string; advisor: Advisor }
  | { kind: "threads"; id: "saved-threads" }
  | { kind: "council"; id: "planning-council" };

const terminal = new Set(["COMPLETED", "FAILED", "CANCELLED", "WITHHELD", "BLOCKED", "PARTIAL"]);
const words = (value: unknown) => String(value ?? "Not recorded").replaceAll("_", " ");
const date = (value: unknown) => {
  if (!value) return "Not recorded";
  const parsed = new Date(String(value));
  return Number.isNaN(parsed.getTime()) ? String(value) : parsed.toLocaleString("en-SG", { dateStyle: "medium", timeStyle: String(value).length > 10 ? "short" : undefined });
};
const errorText = (error: unknown, fallback: string) => error instanceof Error ? error.message : fallback;
const editableAssumptions = (session: PlanningSession | null): FarmerAssumptions => {
  const saved = (session?.assumptions || {}) as Partial<FarmerAssumptions>;
  return {
    tentative_orders: saved.tentative_orders || [],
    future_demand: saved.future_demand || [],
    seasonal: saved.seasonal || [],
    order_changes: saved.order_changes || [],
    reservations: saved.reservations || [],
    ...(saved.capacity ? { capacity: saved.capacity } : {}),
  };
};

export function IntegratedKnowledge({ onClose }: { onClose: () => void }) {
  const [bootstrap, setBootstrap] = useState<Bootstrap | null>(null);
  const [session, setSession] = useState<PlanningSession | null>(null);
  const [threads, setThreads] = useState<Conversation[]>([]);
  const [index, setIndex] = useState(0);
  const [cropDetail, setCropDetail] = useState<Crop | null>(null);
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [selectedThread, setSelectedThread] = useState("");
  const [questions, setQuestions] = useState<Record<string, string>>(() => { try { return JSON.parse(localStorage.getItem("farmtact-v15-knowledge-drafts") || "{}"); } catch { return {}; } });
  const [mode, setMode] = useState<"direct" | "invite" | "council">("direct");
  const [inviteAdvisor, setInviteAdvisor] = useState("asha"), [replyTo, setReplyTo] = useState("");
  const [focusKey, setFocusKey] = useState(""), [conversationFocus, setConversationFocus] = useState("");
  const [bindings, setBindings] = useState<Record<string, string>>(() => { try { return JSON.parse(localStorage.getItem("farmtact-v15-knowledge-bindings") || "{}"); } catch { return {}; } });
  const [proposalMessage, setProposalMessage] = useState(""), [proposal, setProposal] = useState<FarmerProposal | null>(null);
  const [assumptionsDraft, setAssumptionsDraft] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [needsRefresh, setNeedsRefresh] = useState(false);
  const pointer = useRef<number | null>(null);
  const mutation = useRef(false);

  const load = useCallback(async () => {
    setBusy("Opening knowledge records"); setError("");
    try {
      const [base, listed, saved] = await Promise.all([api.bootstrap(), planningApi.list(), api.conversations()]);
      let current: PlanningSession | undefined;
      const remembered = rememberedPlanningSession();
      if (remembered) try { current = await planningApi.get(remembered); } catch { /* use current ordinary session */ }
      current ||= listed.sessions.find((item) => item.workflow === true) || listed.sessions[0];
      setBootstrap(base); setSession(current || null); setThreads(saved);
    } catch (caught) { setError(errorText(caught, "Knowledge records could not be opened.")); }
    finally { setBusy(""); }
  }, []);
  useEffect(() => { void load(); }, [load]);

  const sourceCards = useMemo<Source[]>(() => bootstrap?.sources.length ? bootstrap.sources : [{
    id: "source-registry-empty", name: "Public source registry", status: "unavailable", observed_at: null,
    retrieved_at: "", freshness: "no source snapshot loaded",
    origin: "public", execution_mode: bootstrap?.capabilities.execution_mode || "unavailable",
    summary: "No public source snapshot is loaded in this workspace. Advisers must remain partial or abstain when their answer requires one.",
    availability_status: "missing", licence_state: "not reviewed",
  }], [bootstrap]);
  const cards = useMemo<Card[]>(() => bootstrap ? [
    ...bootstrap.crops.map((crop): Card => ({ kind: "crop", id: `crop-${crop.id}`, crop })),
    ...sourceCards.map((source): Card => ({ kind: "source", id: `source-${source.id}`, source })),
    ...ADVISORS.map((advisor): Card => ({ kind: "advisor", id: `agent-${advisor.id}`, advisor })),
    { kind: "threads", id: "saved-threads" }, { kind: "council", id: "planning-council" },
  ] : [], [bootstrap, sourceCards]);
  const activeIndex = Math.min(index, Math.max(cards.length - 1, 0));
  const active = cards[activeIndex];

  useEffect(() => {
    setConversation(null); setConversationFocus(""); setNeedsRefresh(false); setSelectedThread(""); setMode("direct"); setReplyTo(""); setProposalMessage(""); setProposal(null); setError("");
    if (active?.kind !== "crop") { setCropDetail(null); return; }
    let cancelled = false;
    setBusy("Loading crop evidence");
    void api.crop(active.crop.id).then((value) => { if (!cancelled) setCropDetail(value); })
      .catch((caught) => { if (!cancelled) setError(errorText(caught, "Crop evidence is unavailable.")); })
      .finally(() => { if (!cancelled) setBusy(""); });
    return () => { cancelled = true; };
  }, [active?.id]);
  useEffect(() => { try { localStorage.setItem("farmtact-v15-knowledge-drafts", JSON.stringify(questions)); } catch { /* draft persistence is best effort */ } }, [questions]);
  useEffect(() => { try { localStorage.setItem("farmtact-v15-knowledge-bindings", JSON.stringify(bindings)); } catch { /* binding persistence is best effort */ } }, [bindings]);

  const activeBindingKey = active?.kind === "advisor" && session ? `${session.id}:${active.advisor.id}:${focusKey || "planning"}` : "";
  useEffect(() => {
    const id = activeBindingKey && bindings[activeBindingKey];
    if (!id || conversation) return;
    let cancelled = false;
    void api.conversation(id).then((saved) => { if (!cancelled) { setConversation(saved); setConversationFocus(focusKey); } }).catch(() => {});
    return () => { cancelled = true; };
  }, [activeBindingKey, bindings, conversation, focusKey]);

  useEffect(() => {
    const status = String(conversation?.last_request_status || "").toUpperCase();
    if (!conversation?.id || !["QUEUED", "RUNNING"].includes(status)) return;
    const timer = window.setInterval(() => void api.conversation(conversation.id).then(setConversation).catch(() => {}), 1600);
    return () => window.clearInterval(timer);
  }, [conversation?.id, conversation?.last_request_status]);

  useEffect(() => {
    if (!session?.job || !["QUEUED", "RUNNING"].includes(session.job.status)) return;
    const timer = window.setInterval(() => void planningApi.get(session.id).then(setSession).catch(() => {}), 1600);
    return () => window.clearInterval(timer);
  }, [session?.id, session?.job?.id, session?.job?.status]);

  const move = (amount: number) => setIndex((value) => Math.max(0, Math.min(cards.length - 1, value + amount)));
  const keyboard = (event: KeyboardEvent<HTMLElement>) => {
    if ((event.target as HTMLElement).closest("button,a,input,textarea,select,summary")) return;
    if (event.key === "ArrowLeft") { event.preventDefault(); move(-1); }
    if (event.key === "ArrowRight") { event.preventDefault(); move(1); }
  };
  const pointerUp = (event: PointerEvent<HTMLElement>) => {
    if (pointer.current === null) return;
    const delta = event.clientX - pointer.current; pointer.current = null;
    if (Math.abs(delta) > 48) move(delta < 0 ? 1 : -1);
  };
  const mutate = async (label: string, operation: () => Promise<void>) => {
    if (mutation.current) return;
    mutation.current = true; setBusy(label); setError("");
    try { await operation(); } catch (caught) { setError(errorText(caught, `${label} failed. Your draft is retained.`)); }
    finally { mutation.current = false; setBusy(""); }
  };

  const ask = (advisor: Advisor) => {
    const text = (questions[advisor.id] || "").trim();
    if (!session || !text) return;
    void mutate("Submitting explicit adviser question", async () => {
      const bindingKey = `${session.id}:${advisor.id}:${focusKey || "planning"}`;
      let current = conversation;
      let id = current?.id || bindings[bindingKey];
      if (id && !current) { current = await api.conversation(id); setConversation(current); }
      if (!id) { const separator = focusKey.indexOf(":"); const entity_kind = separator < 0 ? "" : focusKey.slice(0, separator), entity_id = separator < 0 ? "" : focusKey.slice(separator + 1); const created = await api.createConversation({ advisor: advisor.id, snapshot_kind: "planning", snapshot_id: session.id,
        ...(entity_kind && entity_id ? { focus: { card_id: `${entity_kind}-${entity_id}`, entity_kind, entity_id } } : {}) }); id = created.id; const nextBindings = { ...bindings, [bindingKey]: created.id }; try { localStorage.setItem("farmtact-v15-knowledge-bindings", JSON.stringify(nextBindings)); } catch { /* best effort */ } setBindings(nextBindings); setConversation({ id: created.id, messages: [], last_request_status: created.status }); setConversationFocus(focusKey); }
      if (mode === "invite") await api.inviteAdvisor(id, { advisor: inviteAdvisor, question: text, reply_to: replyTo });
      else if (mode === "council") await api.conveneCouncil(id, { question: text, ...(replyTo ? { reply_to: replyTo } : {}) });
      else await api.sendConversationMessage(id, { content: text, ...(replyTo ? { reply_to: replyTo } : {}) });
      setQuestions((saved) => ({ ...saved, [advisor.id]: "" })); setNeedsRefresh(true);
      setConversation(await api.conversation(id)); setNeedsRefresh(false);
      setThreads(await api.conversations());
    });
  };
  const refreshConversation = () => conversation && void mutate("Refreshing accepted submission", async () => { setConversation(await api.conversation(conversation.id)); setNeedsRefresh(false); });
  const replay = (id: string) => void mutate("Loading saved transcript", async () => {
    setConversation(await api.conversationReplay(id)); setSelectedThread(id);
  });
  const reviewCouncil = () => session && void mutate("Requesting Council review", async () => {
    setSession(await planningApi.review(session.id, session.revision));
  });
  const createReviewedProposal = () => session && conversation && proposalMessage && void mutate("Creating reviewed planning proposal", async () => {
    const assumptions = JSON.parse(assumptionsDraft) as FarmerAssumptions;
    const strategy = session.selected_strategy_id || session.result?.strategies?.[0]?.id;
    if (!strategy) throw new Error("Calculate a strategy before preparing a planning proposal.");
    setProposal(await farmerWorkflowApi.createProposal(session, strategy, assumptions, [], { conversation_id: conversation.id, message_id: proposalMessage }));
  });
  const applyReviewedProposal = () => proposal && void mutate("Applying reviewed proposal", async () => {
    setProposal(await farmerWorkflowApi.applyProposal(proposal));
    if (session) setSession(await planningApi.get(session.id));
  });

  if (!bootstrap || !active) return <section className="ik-state" aria-live="polite"><h2>{error || "Opening knowledge and evidence…"}</h2>{error && <button onClick={() => void load()}>Try again</button>}</section>;
  const messages = conversation?.messages || [];
  const evidence = (cropDetail?.evidence || []) as EvidenceRecord[];
  const councilStatus = String(session?.review?.status || session?.job?.status || "not requested");
  const question = active.kind === "advisor" ? questions[active.advisor.id] || "" : "";
  const actionableMessages = conversation?.messages.filter((message) => message.speaker !== "user") || [];
  const contextual = active.kind === "advisor" && conversation && focusKey !== conversationFocus ? { label: "Start new focused thread", disabled: false, run: () => { if (activeBindingKey) setBindings((saved) => { const next = { ...saved }; delete next[activeBindingKey]; return next; }); setConversation(null); setConversationFocus(""); setReplyTo(""); } }
    : active.kind === "advisor" && needsRefresh ? { label: "Refresh accepted submission", disabled: false, run: refreshConversation }
    : active.kind === "advisor" ? {
    label: mode === "invite" ? "Invite specialist" : mode === "council" ? "Convene Council" : "Submit question",
    disabled: !question.trim() || !session || (mode === "invite" && (!conversation || !replyTo)), run: () => ask(active.advisor),
  } : active.kind === "threads" ? proposal ? { label: proposal.status === "draft" ? "Apply reviewed proposal" : "Proposal saved", disabled: proposal.status !== "draft", run: applyReviewedProposal }
    : proposalMessage ? { label: "Create reviewed proposal", disabled: !assumptionsDraft.trim(), run: createReviewedProposal }
    : { label: "Open read-only replay", disabled: !selectedThread, run: () => replay(selectedThread) }
    : active.kind === "council" ? { label: "Review with Council", disabled: !session?.result?.strategies?.length || ["QUEUED", "RUNNING"].includes(session.job?.status || "") || !!session.review?.findings?.length, run: reviewCouncil } : null;
  const entity = active.kind === "crop" ? { id: active.crop.id, kind: "crop" } : active.kind === "source" ? { id: active.source.id, kind: "source" } : active.kind === "advisor" ? { id: active.advisor.id, kind: "advisor" } : active.kind === "threads" ? { id: conversation?.id || active.id, kind: conversation ? "conversation" : "conversation_index" } : { id: session?.id || active.id, kind: "planning_council" };
  const snapshotRef = conversation?.snapshot_ref;
  const provenance = active.kind === "source" ? [active.source.url || active.source.id] : active.kind === "crop" ? active.crop.evidence_ids || [] : conversation ? [conversation.id] : [];
  const knowledgeCard: FarmCard = {
    id: active.id, entityId: entity.id, entityKind: entity.kind,
    title: active.kind === "crop" ? active.crop.label : active.kind === "source" ? active.source.name : active.kind === "advisor" ? active.advisor.name : active.kind === "threads" ? "Saved adviser transcripts" : "Planning Council review",
    provenance,
    binding: { sessionId: session?.id || null, inputHash: typeof session?.input_hash === "string" ? session.input_hash : null, revision: session?.revision ?? null, resultId: typeof session?.result_id === "string" ? session.result_id : null, snapshotId: typeof snapshotRef === "string" ? snapshotRef : snapshotRef && typeof snapshotRef.id === "string" ? snapshotRef.id : null },
    boardTargets: active.kind === "crop" ? (session?.farm?.beds || []).filter((bed) => (bed as typeof bed & { crop_id?: string }).crop_id === active.crop.id).map((bed) => bed.id) : [], outcomeBasis: active.kind === "council" ? "projection" : null,
    actions: contextual ? [{ id: contextual.label.toLowerCase().replaceAll(" ", "-"), label: contextual.label, eligible: !contextual.disabled, authority: /submit|invite|council|proposal|apply|review/i.test(contextual.label) ? "server_mutation" : "local_navigation", eligibilitySource: active.kind === "threads" && proposal ? "server" : "local", ...(contextual.disabled ? { disabledReason: "Current server state or required input makes this action unavailable." } : {}) }] : [],
  };

  return <section className="ik-shell" tabIndex={-1} onKeyDown={keyboard}>
    <header className="ik-header"><div><span>Farm tools › Knowledge &amp; evidence</span><h1>Inspect the facts. Ask deliberately.</h1></div><button onClick={onClose}>Close</button></header>
    {error && <div className="ik-error" role="alert"><span>{error}</span><button onClick={() => setError("")}>Dismiss</button></div>}
    <div className="ik-deck" onPointerDown={(event) => { pointer.current = event.clientX; }} onPointerUp={pointerUp}>
      <BoundCard card={knowledgeCard} className="ik-card" aria-live="polite" aria-label={`Knowledge card ${activeIndex + 1} of ${cards.length}`}>
        {active.kind === "crop" && <CropCard crop={cropDetail || active.crop} evidence={evidence} />}
        {active.kind === "source" && <SourceCard source={active.source} />}
        {active.kind === "advisor" && <AdvisorCard advisor={active.advisor} conversation={conversation} question={question} setQuestion={(value) => setQuestions((current) => ({ ...current, [active.advisor.id]: value }))} mode={mode} setMode={setMode} inviteAdvisor={inviteAdvisor} setInviteAdvisor={setInviteAdvisor} replyTo={replyTo} setReplyTo={setReplyTo} replyOptions={actionableMessages} focusKey={focusKey} setFocusKey={setFocusKey} session={session} />}
        {active.kind === "threads" && <ThreadsCard threads={threads} selected={selectedThread} setSelected={setSelectedThread} conversation={conversation} proposalMessage={proposalMessage} setProposalMessage={(id) => { setProposalMessage(id); setProposal(null); setAssumptionsDraft(JSON.stringify(editableAssumptions(session), null, 2)); }} assumptionsDraft={assumptionsDraft} setAssumptionsDraft={setAssumptionsDraft} proposal={proposal} />}
        {active.kind === "council" && <CouncilCard session={session} status={councilStatus} />}
      </BoundCard>
    </div>
    <nav className="ik-actions" aria-label="Knowledge card actions"><button onClick={() => move(-1)} disabled={activeIndex === 0}>Previous</button>{contextual ? <button className="is-primary" disabled={contextual.disabled || !!busy} onClick={contextual.run}>{contextual.label}</button> : <span>{activeIndex + 1} / {cards.length}</span>}<button onClick={() => move(1)} disabled={activeIndex === cards.length - 1}>Next</button></nav>
    {busy && <p className="ik-status" role="status">{busy}…</p>}
  </section>;
}

function CropCard({ crop, evidence }: { crop: Crop; evidence: EvidenceRecord[] }) {
  return <><span className="ik-kicker">Crop profile · representative art</span><div className="ik-title-row"><img src={`/art/crops/${crop.id}-growing.svg`} alt="" onError={(event) => { event.currentTarget.hidden = true; }} /><div><h2>{crop.label}</h2><p>{crop.harvested_part ? `Harvested part: ${crop.harvested_part}.` : "Harvested part not recorded."}</p></div></div>
    <dl className="ik-facts"><Fact label="Cycle" value={crop.recipe ? `${crop.recipe.cycle_days} days` : "No supported planning recipe"}/><Fact label="Nursery" value={crop.recipe ? `${crop.recipe.nursery_days} days` : "Not modelled"}/><Fact label="Recipe status" value={crop.recipe?.validation_status || "Unsupported"}/></dl>
    <p className="ik-boundary">Recipe values are planning assumptions, not a real-farm growth guarantee. Unsupported states must not be shown as harvest-ready.</p>
    {!!crop.warnings?.length && <ul>{crop.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>}
    <section className="ik-evidence"><h3>Evidence and limitations</h3>{evidence.length ? evidence.map((item) => <details key={item.evidence_id}><summary>{item.title || item.evidence_id}</summary><p>{item.finding || "No finding recorded."}</p><p><b>Scope:</b> {item.scope || "Not recorded"}</p><p><b>Limit:</b> {item.limit || "Not recorded"}</p><small>{words(item.access_review_status)} · {item.year || "year not recorded"}</small>{item.source_url && <a href={item.source_url} target="_blank" rel="noreferrer">Inspect source ↗</a>}</details>) : <p>No evidence records were returned for this profile.</p>}</section></>;
}

function SourceCard({ source }: { source: Source }) {
  const stale = /stale|missing|unavailable|registry/.test(`${source.status} ${source.freshness} ${source.availability_status}`.toLowerCase());
  return <><span className="ik-kicker">Source record · {source.origin}</span><h2>{source.name}</h2><p>{source.summary}</p><div className={`ik-source-state ${stale ? "is-limited" : ""}`}>{stale ? "Limited or stale source" : "Available source"}</div>
    <dl className="ik-facts"><Fact label="Observed" value={date(source.observed_at)}/><Fact label="Retrieved" value={date(source.retrieved_at)}/><Fact label="Freshness" value={words(source.freshness)}/><Fact label="Status" value={words(source.availability_status || source.status)}/><Fact label="Units" value={Array.isArray(source.unit) ? source.unit.join(", ") : source.unit || "Not recorded"}/><Fact label="Licence" value={words(source.licence_state)}/></dl>
    {source.coverage && <details><summary>Coverage details</summary><pre>{JSON.stringify(source.coverage, null, 2)}</pre></details>}{source.url && <a className="ik-link" href={source.url} target="_blank" rel="noreferrer">Inspect public source ↗</a>}
    <p className="ik-boundary">Source availability and freshness are separate from whether an adviser interpretation is valid.</p></>;
}

function AdvisorCard({ advisor, conversation, question, setQuestion, mode, setMode, inviteAdvisor, setInviteAdvisor, replyTo, setReplyTo, replyOptions, focusKey, setFocusKey, session }: { advisor: Advisor; conversation: Conversation | null; question: string; setQuestion: (value: string) => void; mode: "direct" | "invite" | "council"; setMode: (value: "direct" | "invite" | "council") => void; inviteAdvisor: string; setInviteAdvisor: (value: string) => void; replyTo: string; setReplyTo: (value: string) => void; replyOptions: Conversation["messages"]; focusKey: string; setFocusKey: (value: string) => void; session: PlanningSession | null }) {
  return <><span className="ik-kicker">Specialist · explicit provider submission</span><div className="ik-title-row"><img src={`/art/advisors/${advisor.id}.svg`} alt=""/><div><h2>{advisor.name} · {advisor.role}</h2><p>{advisor.focus}</p></div></div>
    <div className="ik-composer"><label>Frozen focus<select value={focusKey} onChange={(event) => setFocusKey(event.target.value)}><option value="">Whole planning result</option>{session?.farm?.orders?.map((item) => <option key={`order:${item.id}`} value={`order:${item.id}`}>Order · {item.id} · {item.crop_id}</option>)}{session?.farm?.beds?.map((item) => <option key={`bed:${item.id}`} value={`bed:${item.id}`}>Bed · {item.name}</option>)}{session?.result?.strategies?.map((item) => <option key={`strategy:${item.id}`} value={`strategy:${item.id}`}>Strategy · {item.name}</option>)}</select></label>{conversation && <p>Current thread keeps its original frozen focus. Changing this selection requires the explicit new-thread action below.</p>}<label>Discussion action<select value={mode} onChange={(event) => setMode(event.target.value as typeof mode)}><option value="direct">Ask this specialist</option><option value="invite">Invite another specialist</option><option value="council">Convene full Council</option></select></label>{mode === "invite" && <label>Invited specialist<select value={inviteAdvisor} onChange={(event) => setInviteAdvisor(event.target.value)}>{ADVISORS.filter((item) => item.id !== advisor.id).map((item) => <option key={item.id} value={item.id}>{item.name} · {item.role}</option>)}</select></label>}{mode !== "direct" && <label>Reply to saved specialist finding<select value={replyTo} onChange={(event) => setReplyTo(event.target.value)}><option value="">Select a finding</option>{replyOptions.map((message) => <option key={message.id} value={message.id}>{message.speaker_name || words(message.speaker)} · {message.content.slice(0, 70)}</option>)}</select></label>}<label>Question about the frozen planning session<textarea value={question} maxLength={1000} onChange={(event) => setQuestion(event.target.value)} placeholder={advisor.prompt}/></label></div>
    <p className="ik-boundary">Opening this card makes no inference call. Submit sends the question through the existing validated gateway; it cannot change farm state.</p>
    {conversation && <Transcript conversation={conversation}/>}</>;
}

function ThreadsCard({ threads, selected, setSelected, conversation, proposalMessage, setProposalMessage, assumptionsDraft, setAssumptionsDraft, proposal }: { threads: Conversation[]; selected: string; setSelected: (id: string) => void; conversation: Conversation | null; proposalMessage: string; setProposalMessage: (id: string) => void; assumptionsDraft: string; setAssumptionsDraft: (value: string) => void; proposal: FarmerProposal | null }) {
  const candidates = conversation?.messages.filter((message) => message.speaker === "advisor" && message.validation_status === "references_verified" && !!message.proposed_actions?.length) || [];
  return <><span className="ik-kicker">Saved discussions · read-only replay</span><h2>Complete adviser transcripts</h2><p>Opening a saved thread reads its recorded messages and makes no inference request.</p>
    <label className="ik-thread-picker">Saved thread<select value={selected} onChange={(event) => setSelected(event.target.value)}><option value="">Select a thread</option>{threads.map((thread) => <option key={thread.id} value={thread.id}>{thread.title || words(thread.advisor_role || thread.advisor_id || "Adviser thread")} · {date(thread.updated_at || thread.created_at)}</option>)}</select></label>
    {!!candidates.length && <section className="ik-proposal"><h3>Reviewed adviser handoff</h3><p>Select a validated message, then enter the exact assumptions to review. Adviser actions are displayed as context and are never copied into farm state automatically.</p><label>Validated message<select value={proposalMessage} onChange={(event) => setProposalMessage(event.target.value)}><option value="">Select message</option>{candidates.map((message) => <option key={message.id} value={message.id}>{message.speaker_name || words(message.speaker)} · {message.content.slice(0, 65)}</option>)}</select></label>{proposalMessage && <><RecordFacts value={candidates.find((message) => message.id === proposalMessage)?.proposed_actions}/><label>Exact planning assumptions<textarea value={assumptionsDraft} onChange={(event) => setAssumptionsDraft(event.target.value)} rows={10}/></label></>}{proposal && <RecordFacts value={proposal}/>}</section>}
    {conversation && <Transcript conversation={conversation}/>}</>;
}

function Transcript({ conversation }: { conversation: Conversation }) {
  return <section className="ik-transcript"><header><h3>Recorded transcript</h3><span>{conversation.replay ? "Replay · zero inference" : words(conversation.last_request_status || conversation.status)}</span></header>
    {conversation.messages.length ? conversation.messages.map((message) => <article key={message.id} className={`ik-message is-${message.speaker}`}><div><b>{message.speaker_name || words(message.speaker)}</b><span>{words(message.validation_status || message.evidence_status || "recorded")}</span></div><p>{message.content}</p>{message.planner_conclusion && <strong>Planner conclusion</strong>}<AdvisorEvidence message={message} conversation={conversation}/></article>) : <p>No messages were recorded.</p>}
    {conversation.last_request_error && <p className="ik-boundary">Request stopped: {conversation.last_request_error}. The recorded transcript remains available.</p>}</section>;
}

function CouncilCard({ session, status }: { session: PlanningSession | null; status: string }) {
  const findings = session?.review?.findings || [];
  return <><span className="ik-kicker">Planning Council · advisory review</span><h2>Review the frozen alternatives</h2><p>The local strategies remain available when Council review is partial, withheld, or unavailable.</p>
    <dl className="ik-facts"><Fact label="Session revision" value={session?.revision ?? "Unavailable"}/><Fact label="Strategies" value={session?.result?.strategies?.length ?? 0}/><Fact label="Council status" value={words(status)}/></dl>
    <div className="ik-roster" aria-label="Seven Council roles">{ADVISORS.map((advisor) => <span key={advisor.id}><img src={`/art/advisors/${advisor.id}.svg`} alt=""/><small>{advisor.role}</small></span>)}</div>
    {!findings.length && <p>{session?.result?.strategies?.length ? "Ready for explicit review from the action row." : "Calculate planning alternatives before requesting review."}</p>}
    {!!findings.length && <section className="ik-findings"><h3>Recorded findings</h3>{findings.map((raw, index) => { const finding = raw as Record<string, unknown>; const facts = Array.isArray(finding.rendered_facts) ? finding.rendered_facts.filter((item): item is import("../lib/game").RenderedFact => !!item && typeof item === "object" && "reference" in item) : [];
      return <article key={String(finding.id || index)}><header><b>{words(finding.role || `Council finding ${index + 1}`)}</b><span>{words(finding.validation_status || finding.evidence_status || finding.status || "recorded")}</span></header><p>{String(finding.rendered_interpretation || finding.statement || finding.summary || "No interpretation supplied.")}</p><FrozenFactEvidence factRefs={Array.isArray(finding.fact_refs) ? finding.fact_refs.map(String) : []} renderedFacts={facts} validationStatus={String(finding.validation_status || "")} evidenceStatus={String(finding.evidence_status || finding.status || "")}/></article>; })}</section>}
    <p className="ik-boundary">Evidence-reference checks do not establish that qualitative prose is true. Council review never approves work or alters assumptions.</p></>;
}

function Fact({ label, value }: { label: string; value: unknown }) { return <div><dt>{label}</dt><dd>{String(value)}</dd></div>; }

export default IntegratedKnowledge;
