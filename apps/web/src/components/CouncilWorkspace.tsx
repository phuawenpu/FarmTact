import { CheckCircle2, CircleAlert, MessageSquareText, Send, ShieldCheck, Users, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { api, request } from "../lib/api";
import { editionStorageKey } from "../lib/edition";
import { ADVISORS, publicAdvisorLabel, type AdvisorId, type Conversation, type ConversationMessage, type ProposedAction, type RenderedFact } from "../lib/game";
import type { PlanningSession } from "../lib/planning";
import type { Strategy } from "../lib/types";
import "./CouncilWorkspace.css";

export type CouncilHandoff = {
  conversationId: string;
  messageId: string;
  actions: ProposedAction[];
};

type Props = {
  session: PlanningSession;
  strategy?: Strategy;
  busy: boolean;
  onReview: () => void;
  onSelectStrategy: (id: string) => void;
  onHandoff: (source: CouncilHandoff) => void;
  onError: (message: string) => void;
};

type Finding = {
  advisor: (typeof ADVISORS)[number];
  status: "validated" | "partial" | "withheld" | "unavailable";
  summary: string;
  recommendation?: string;
  rationale?: string;
  tradeoff?: string;
  renderedFacts: unknown[];
  reasons: string[];
  proposedStrategyId?: string;
};

const terminal = new Set(["COMPLETED", "FAILED", "CANCELLED", "WITHHELD", "BLOCKED"]);
const rolePrompts: Record<string, string[]> = {
  ravi: ["Which booked delivery is most exposed?", "Which plan protects confirmed demand best?"],
  hana: ["Which weather evidence is present, stale or missing?", "What weather uncertainty should I monitor?"],
  idris: ["What market evidence supports this choice?", "Which market claim should remain uncertain?"],
  mei: ["Which crop timing could invalidate this plan?", "What biological limit differs between these plans?"],
  lina: ["Where could harvest supply miss delivery timing?", "Which inventory or packing constraint matters most?"],
  ben: ["What drives the margin and cash tradeoff?", "Which cost assumption should I challenge?"],
  asha: ["Where do the specialists agree and disagree?", "Which option is supported by the verified facts?"],
};
const rolePurpose: Record<string, string> = {
  ravi: "Booked demand", hana: "Weather evidence", idris: "Market evidence",
  mei: "Crop timing", lina: "Supply timing", ben: "Cash and cost", asha: "Plan synthesis",
};

function resultId(session: PlanningSession) {
  return typeof session.result_id === "string" ? session.result_id : "";
}

function draftKey(sessionId: string, result: string, advisor: string) {
  return editionStorageKey(`council-draft:${sessionId}:${result || "before-calculation"}:${advisor}`);
}

function readDraft(key: string, fallback: string) {
  try { return localStorage.getItem(key) ?? fallback; } catch { return fallback; }
}

function saveDraft(key: string, value: string) {
  try { value ? localStorage.setItem(key, value) : localStorage.removeItem(key); } catch { /* optional persistence */ }
}

function words(value: unknown, fallback = "Not reported") {
  if (value === null || value === undefined || value === "") return fallback;
  if (typeof value === "object") return JSON.stringify(value);
  return String(value).replaceAll("_", " ");
}

function findings(session: PlanningSession): Finding[] {
  const reviewResult = typeof session.review?.result_id === "string" ? session.review.result_id : "";
  const rows = (!reviewResult || reviewResult === resultId(session)) && Array.isArray(session.review?.findings) ? session.review.findings : [];
  return ADVISORS.map((advisor) => {
    const row = rows.find((candidate) =>
      candidate.functional_role === advisor.role ||
      candidate.functional_role === advisor.roleId ||
      candidate.role === advisor.roleId || candidate.advisor_id === advisor.id) || {};
    const raw = String(row.truth_status || row.validation_status || row.status || "").toLowerCase();
    const status: Finding["status"] = raw === "validated" ? "validated" : raw === "partial" ? "partial" :
      ["rejected", "withheld", "blocked", "failed"].includes(raw) ? "withheld" : "unavailable";
    return {
      advisor, status,
      summary: String(row.summary || row.statement || row.rendered_interpretation || row.rationale || (session.review?.status && session.review.status !== "not_requested" ? "No finding was returned for this role. Inspect the review limits." : resultId(session) ? "Review not requested for this result." : "Waiting for calculated plans.")),
      recommendation: typeof row.recommendation === "string" ? row.recommendation : undefined,
      rationale: typeof row.rendered_interpretation === "string" ? row.rendered_interpretation : typeof row.rationale === "string" ? row.rationale : undefined,
      tradeoff: typeof row.tradeoff === "string" ? row.tradeoff : undefined,
      renderedFacts: Array.isArray(row.rendered_facts) ? row.rendered_facts : [],
      reasons: Array.isArray(row.rejection_reasons) ? row.rejection_reasons.map(String) : [],
      proposedStrategyId: typeof row.proposed_strategy_id === "string" ? row.proposed_strategy_id : undefined,
    };
  });
}

function snapshotResult(conversation: Conversation) {
  const ref = conversation.snapshot_ref;
  if (ref && typeof ref === "object") {
    const focus = (conversation.focus || {}) as Record<string, unknown>;
    const record = ref as Record<string, unknown>;
    return String(focus.result_id || record.result_id || String(ref.id || "").split(":")[1] || "");
  }
  return typeof ref === "string" ? ref.split(":")[1] || "" : "";
}

export function CouncilWorkspace({ session, strategy, busy, onReview, onSelectStrategy, onHandoff, onError }: Props) {
  const currentResult = resultId(session);
  const reviewedResult = typeof session.review?.result_id === "string" ? session.review.result_id : "";
  const reviewMatchesCurrent = Boolean(currentResult && reviewedResult === currentResult && session.review?.status !== "not_requested");
  const reviewRunning = Boolean(currentResult && String(session.job?.kind || "").toLowerCase().includes("review") && ["QUEUED", "RUNNING", "PENDING"].includes(String(session.job?.status || "").toUpperCase()));
  const normalized = useMemo(() => findings(session), [session]);
  const [recipient, setRecipient] = useState(ADVISORS[0].id);
  const [draft, setDraft] = useState("");
  const [threads, setThreads] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState("");
  const [sending, setSending] = useState<"role" | "council" | "">("");
  const [before, setBefore] = useState<string | undefined>();
  const [hasOlder, setHasOlder] = useState(false);
  const disposed = useRef(false);
  const context = `${session.id}:${currentResult || "before-calculation"}`;
  const contextRef = useRef(context);
  const recipientRef = useRef<AdvisorId>(recipient);
  const draftRef = useRef(draft);
  const pendingPoll = useRef<{ context: string; promise: Promise<void> } | null>(null);
  const inFlightMutation = useRef(false);
  contextRef.current = context;
  recipientRef.current = recipient;
  draftRef.current = draft;
  const key = draftKey(session.id, currentResult, recipient);
  const active = threads.find((thread) => thread.id === activeId);
  const historical = Boolean(active && snapshotResult(active) && snapshotResult(active) !== currentResult);

  useEffect(() => { setDraft(readDraft(key, rolePrompts[recipient]?.[0] || ADVISORS[0].prompt)); }, [key, recipient]);
  useEffect(() => { disposed.current = false; return () => { disposed.current = true; }; }, []);
  useEffect(() => {
    setActiveId(""); setBefore(undefined); setThreads([]); setHasOlder(false); setSending("");
    void loadThreads(false, context);
    // A result change deliberately starts a fresh frozen discussion context.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session.id, currentResult]);

  async function loadThreads(older: boolean, expectedContext = contextRef.current) {
    try {
      const query = new URLSearchParams({ planning_session_id: session.id, limit: "12" });
      if (older && before) query.set("before", before);
      const page = await request<{ conversations: Conversation[]; next_before?: string | null }>(`/conversations?${query}`);
      if (disposed.current || contextRef.current !== expectedContext) return;
      setThreads((existing) => older ? [...existing, ...page.conversations.filter((row) => !existing.some((item) => item.id === row.id))] : page.conversations);
      setBefore(page.next_before || page.conversations.at(-1)?.created_at || undefined);
      setHasOlder(Boolean(page.next_before));
    } catch (error) { if (contextRef.current === expectedContext) onError(error instanceof Error ? error.message : "Could not load Council discussions."); }
  }

  async function poll(id: string, expectedContext: string) {
    if (pendingPoll.current?.context === expectedContext) return pendingPoll.current.promise;
    const promise = (async () => {
      const deadline = Date.now() + 90000;
      while (!disposed.current && contextRef.current === expectedContext && Date.now() < deadline) {
        const next = await api.conversation(id);
        if (disposed.current || contextRef.current !== expectedContext) return;
        setThreads((items) => [next, ...items.filter((item) => item.id !== next.id)]);
        const state = String(next.last_request_status || next.status || "").toUpperCase();
        if (!state || terminal.has(state)) return;
        await new Promise((resolve) => window.setTimeout(resolve, 1200));
      }
    })().finally(() => { if (pendingPoll.current?.promise === promise) pendingPoll.current = null; });
    pendingPoll.current = { context: expectedContext, promise };
    return promise;
  }

  async function send(mode: "role" | "council") {
    const question = draft.trim();
    if (!question || !currentResult || historical || inFlightMutation.current) return;
    const expectedContext = context;
    const expectedRecipient = recipient;
    const expectedKey = key;
    inFlightMutation.current = true;
    setSending(mode);
    try {
      let conversation = active && snapshotResult(active) === currentResult && (mode === "council" || active.advisor_id === expectedRecipient) ? active : undefined;
      if (!conversation) {
        const created = await api.createConversation({ advisor: mode === "council" ? "asha" : expectedRecipient, snapshot_kind: "planning", snapshot_id: session.id, expected_result_id: currentResult, ...(reviewMatchesCurrent ? { council_review_result_id: currentResult } : {}) });
        if (disposed.current || contextRef.current !== expectedContext) return;
        conversation = await api.conversation(created.id);
        if (disposed.current || contextRef.current !== expectedContext) return;
        setThreads((items) => [conversation!, ...items.filter((item) => item.id !== conversation!.id)]);
        setActiveId(conversation.id);
      }
      if (mode === "council") await api.conveneCouncil(conversation.id, { question });
      else await api.sendConversationMessage(conversation.id, { content: question });
      if (readDraft(expectedKey, "") === question) saveDraft(expectedKey, "");
      if (contextRef.current === expectedContext && recipientRef.current === expectedRecipient && draftRef.current.trim() === question) setDraft("");
      await poll(conversation.id, expectedContext);
    } catch (error) { if (contextRef.current === expectedContext) onError(error instanceof Error ? error.message : "The Council request could not be completed."); }
    finally {
      inFlightMutation.current = false;
      if (contextRef.current === expectedContext) setSending("");
    }
  }

  const suggested = [...(rolePrompts[recipient] || []), strategy ? `What is the strongest reason to choose or reject ${strategy.name}?` : "Which plan should I inspect first?"] .slice(0, 3);
  const proposals = (session.result?.strategies || []) as Strategy[];
  const grouped = new Map<string, Finding[]>();
  normalized.forEach((item) => { if (item.proposedStrategyId && ["validated", "partial"].includes(item.status) && proposals.some((plan) => plan.id === item.proposedStrategyId)) grouped.set(item.proposedStrategyId, [...(grouped.get(item.proposedStrategyId) || []), item]); });

  async function openThread(thread: Conversation) {
    const expectedContext = context;
    setActiveId(thread.id);
    try {
      const transcript = await api.conversation(thread.id);
      if (disposed.current || contextRef.current !== expectedContext) return;
      setThreads((items) => items.map((item) => item.id === transcript.id ? transcript : item));
      if (["QUEUED", "RUNNING", "PENDING"].includes(String(transcript.last_request_status || "").toUpperCase())) void poll(thread.id, expectedContext).catch(error => { if (!disposed.current && contextRef.current === expectedContext) onError(error instanceof Error ? error.message : "Could not refresh this discussion."); });
    } catch (error) {
      if (contextRef.current === expectedContext) onError(error instanceof Error ? error.message : "Could not load the saved transcript.");
    }
  }

  return <section className="v22-council-workspace council-room" tabIndex={-1} aria-labelledby="council-workspace-title">
    <header className="cw-heading"><div><span className="cw-kicker">Shared decision area</span><h2 id="council-workspace-title">Planning Council</h2><p>Compare numerical plans, inspect each specialist’s actual status, then decide what to challenge. Advice cannot approve or change farm work.</p>{reviewRunning && <p className="cw-review-progress" role="status">Review in progress. Roles remain awaiting a recorded result until their saved finding is returned.</p>}</div>{currentResult && !reviewMatchesCurrent && <button className="cw-primary" disabled={busy} onClick={onReview}><Users size={18}/> Review these plans with Council</button>}</header>

    <div className="cw-roster" aria-label="Council role status">{normalized.map(({ advisor, status }) => <article key={advisor.id} data-status={status}><img src={`/art/advisors/${advisor.id}.svg`} alt=""/><div><strong>{advisor.name}</strong><span>{rolePurpose[advisor.id]}</span></div><small>{reviewRunning ? (status === "unavailable" ? "Awaiting result" : status) : !currentResult ? "Waiting for plans" : !reviewMatchesCurrent ? "Not requested" : status}</small></article>)}</div>

    {proposals.length > 0 && <section className="cw-decisions"><h3>Recorded recommendations and differences</h3><p>{grouped.size ? "Validated and partial roles are grouped only when their saved findings name the same valid plan. Withheld findings remain separate." : "No validated or partial finding recommends a plan yet; the numerical alternatives remain available without inferred consensus."}</p><div className="cw-plan-strip">{proposals.map((plan) => { const supporters = grouped.get(plan.id) || []; return <button key={plan.id} className={strategy?.id === plan.id ? "is-selected" : ""} onClick={() => onSelectStrategy(plan.id)}><strong>{plan.name}</strong><span>{supporters.length ? `${supporters.map((item) => `${item.advisor.name} (${item.status})`).join(", ")} recorded this option` : "No validated role recommendation"}</span></button>; })}</div></section>}

    {reviewMatchesCurrent && <div className="cw-findings">{normalized.map((finding) => <FindingCard key={finding.advisor.id} finding={finding}/>)}</div>}

    {currentResult && <section className="cw-discussion"><header><div><h3>Discuss this frozen result</h3><p>Questions use the current calculated result. Changing the result starts a new context; older threads stay read-only.</p></div></header>
      <label>Recipient<select disabled={Boolean(sending)} value={recipient} onChange={(event) => { saveDraft(key, draft); setRecipient(event.target.value as AdvisorId); }}>{ADVISORS.map((advisor) => <option key={advisor.id} value={advisor.id}>{advisor.name}</option>)}</select></label>
      <div className="cw-suggestions" aria-label="Suggested questions">{suggested.map((prompt) => <button key={prompt} type="button" disabled={Boolean(sending)} onClick={() => { const next = draft.trim() ? `${draft.trim()}\n${prompt}` : prompt; setDraft(next); saveDraft(key, next); }}>Add question: {prompt}</button>)}</div>
      <label>Your question<textarea disabled={Boolean(sending)} maxLength={1000} value={draft} onChange={(event) => { setDraft(event.target.value); saveDraft(key, event.target.value); }} placeholder="Ask, challenge or compare…"/></label>
      <div className="cw-compose-actions"><button type="button" className="cw-discard" disabled={!draft} onClick={() => { setDraft(""); saveDraft(key, ""); }}><X size={16}/> Discard draft</button><button type="button" disabled={busy || reviewRunning || !draft.trim() || !currentResult || Boolean(sending) || historical} onClick={() => void send("role")}><Send size={16}/> {sending === "role" ? "Sending…" : `Send to ${ADVISORS.find((item) => item.id === recipient)?.publicLabel}`}</button><button type="button" className="cw-primary" disabled={busy || reviewRunning || !draft.trim() || !currentResult || Boolean(sending) || historical} onClick={() => void send("council")}><Users size={16}/> {sending === "council" ? "Convening…" : "Ask Council"}</button></div>
      <p className="cw-boundary">Choosing a suggestion or editing a draft makes no provider request. Send and Ask Council are explicit requests. Device keyboard voice typing can enter text.</p>
    </section>}

    {currentResult && <section className="cw-threads"><header><h3>Saved discussions</h3><div>{active && <button type="button" onClick={() => setActiveId("")}>New discussion</button>}{hasOlder && <button type="button" onClick={() => void loadThreads(true, context)}>Load older</button>}</div></header>{!threads.length && <p>No saved discussion exists for this planning session.</p>}<div className="cw-thread-layout"><nav aria-label="Saved Council discussions">{threads.map((thread) => { const old = Boolean(snapshotResult(thread) && snapshotResult(thread) !== currentResult); return <button key={thread.id} className={thread.id === activeId ? "is-selected" : ""} onClick={() => void openThread(thread)}><strong>{thread.title || ADVISORS.find((item) => item.id === thread.advisor_id)?.name || "Council discussion"}</strong><span>{old ? "Historical · read-only" : "Current result"} · {thread.created_at ? new Date(thread.created_at).toLocaleDateString() : "saved"}</span></button>; })}</nav>{active && <div className="cw-transcript">{historical && <p className="cw-history"><ShieldCheck size={16}/> Historical transcript. Its original frozen context is preserved and it cannot receive new messages.</p>}{(active.messages || []).map((message) => <Message key={message.id} message={message} allowHandoff={!historical} onHandoff={() => onHandoff({ conversationId: active.id, messageId: message.id, actions: message.proposed_actions || [] })}/>)}</div>}</div></section>}
  </section>;
}

function FindingCard({ finding }: { finding: Finding }) {
  return <article className="cw-finding" data-status={finding.status}><header><img src={`/art/advisors/${finding.advisor.id}.svg`} alt=""/><div><h3>{finding.advisor.name}</h3><span>{rolePurpose[finding.advisor.id]}</span></div><small>{finding.status}</small></header><p>{finding.summary}</p>{(finding.recommendation || finding.rationale || finding.tradeoff) && <dl>{finding.recommendation && <div><dt>Recommendation</dt><dd>{words(finding.recommendation)}</dd></div>}{finding.rationale && <div><dt>Rationale</dt><dd>{words(finding.rationale)}</dd></div>}{finding.tradeoff && <div><dt>Tradeoff</dt><dd>{words(finding.tradeoff)}</dd></div>}</dl>}{finding.renderedFacts.length > 0 && <details><summary>Rendered facts ({finding.renderedFacts.length})</summary><ul>{finding.renderedFacts.map((fact, index) => <li key={index}><FindingFact value={fact}/></li>)}</ul></details>}{finding.reasons.length > 0 && <details><summary>Why this was withheld</summary><ul>{finding.reasons.map((reason) => <li key={reason}>{words(reason)}</li>)}</ul></details>}</article>;
}

function FindingFact({ value }: { value: unknown }) {
  if (!value || typeof value !== "object") return <>{words(value)}</>;
  const fact = value as Partial<RenderedFact>;
  return <span className="cw-rendered-fact"><b>{words(fact.value)} {fact.unit || ""}</b><span>{fact.reference ? factLabel(fact as RenderedFact) : words(fact.context, "Recorded planning fact")}</span><details><summary>Fact provenance</summary><dl>{fact.reference && <div><dt>Reference</dt><dd>{fact.reference}</dd></div>}{fact.entity?.id && <div><dt>Entity</dt><dd>{fact.entity.type || "record"} · {fact.entity.id}</dd></div>}{fact.period?.value && <div><dt>Period</dt><dd>{fact.period.kind || "period"} · {fact.period.value}</dd></div>}<div><dt>Verification</dt><dd>{fact.verification || "not reported"}</dd></div></dl></details></span>;
}

function factLabel(fact: RenderedFact) {
  const metric = (fact.reference.split(/[.:/]/).at(-1) || "planning fact").replace(/_(sgd|kg|hours?|percent)$/, "").replaceAll("_", " ");
  return [metric, fact.entity?.id?.replaceAll("_", " "), fact.context && fact.context !== "strategy" ? fact.context : ""].filter(Boolean).join(" · ");
}

function Message({ message, allowHandoff, onHandoff }: { message: ConversationMessage; allowHandoff: boolean; onHandoff: () => void }) {
  const valid = ["validated", "references_verified"].includes(String(message.validation_status || message.evidence_status).toLowerCase());
  return <article className="cw-message"><header><strong>{message.speaker === "user" ? "You" : publicAdvisorLabel(message.speaker_name || message.speaker_id || message.speaker)}</strong><span>{message.relationship ? words(message.relationship) : words(message.validation_status, "recorded")}</span></header><p>{message.content}</p>{valid && <small className="cw-validation"><CheckCircle2 size={14}/> References checked; interpretation {words(message.interpretation_status, "not assessed")}.</small>}{message.evidence_refs?.length ? <small>Evidence: {message.evidence_refs.join(" · ")}</small> : null}{message.rendered_facts?.length ? <div className="cw-facts"><strong>Typed facts from the frozen snapshot</strong>{message.rendered_facts.map((fact, index) => <article key={`${fact.reference}-${index}`}><b>{words(fact.value)} {fact.unit || ""}</b><span>{factLabel(fact)}</span><details><summary>Fact provenance</summary><dl><div><dt>Reference</dt><dd>{fact.reference}</dd></div>{fact.entity?.id && <div><dt>Entity</dt><dd>{fact.entity.type || "record"} · {fact.entity.id}</dd></div>}<div><dt>Verification</dt><dd>{fact.verification || "not reported"}</dd></div></dl></details></article>)}</div> : null}{message.proposed_actions?.length ? <><div className="cw-actions"><strong>Advisory actions</strong>{message.proposed_actions.map((action, index) => <span key={`${action.control}-${index}`}>{words(action.control)} · {action.target_id ? `target ${action.target_id} · ` : ""}{action.value} {action.unit} · {words(action.status)}</span>)}</div>{valid && allowHandoff && <button type="button" onClick={onHandoff}><MessageSquareText size={16}/> Review proposal from this discussion</button>}</> : null}{String(message.validation_status).toLowerCase() === "withheld" && <small className="cw-validation"><CircleAlert size={14}/> Recommendation withheld; inspect the recorded evidence limit.</small>}</article>;
}
