import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
  type PointerEvent,
  type ReactNode,
} from "react";
import { api } from "../lib/api";
import type { FarmCard, ToolDeck } from "../lib/cards";
import { editionStorageKey } from "../lib/edition";
import {
  farmerWorkflowApi,
  planningApi,
  rememberPlanningSession,
  rememberedPlanningSession,
  type FarmerAssumptions,
  type FarmerProposal,
  type FarmerWorkflowState,
  type PlanningSession,
} from "../lib/planning";
import type { Bootstrap, Strategy } from "../lib/types";
import "./IntegratedCards.css";

type ToolId = ToolDeck;
type Surface = "mission" | "tools" | ToolId;

const toolCards: Array<{ id: ToolId; title: string; summary: string }> = [
  { id: "plan", title: "Plan", summary: "Calculate, compare and approve revision-bound plans." },
  { id: "records", title: "Records & work", summary: "Review farm records, imports, tasks and corrections." },
  { id: "knowledge", title: "Knowledge & evidence", summary: "Inspect crops, sources and saved specialist reviews." },
  { id: "experiments", title: "Experiments", summary: "Open scenarios, datasets, forecasts and local studies." },
  { id: "history", title: "History & preferences", summary: "Replay saved events and manage display preferences." },
];

const emptyWorkflow: FarmerWorkflowState = {
  version: "farmer-workflow-v1", phase: "planning", revision: 0,
  inbox: [], proposals: [], tasks: [], events: [], real_operations_enabled: false,
};

function message(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

function num(value: unknown, digits = 1) {
  const parsed = Number(value);
  return Number.isFinite(parsed)
    ? new Intl.NumberFormat(undefined, { maximumFractionDigits: digits }).format(parsed)
    : "—";
}

function signed(value: unknown, unit: string) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return "Not reported";
  return `${parsed > 0 ? "+" : parsed < 0 ? "−" : "±"}${num(Math.abs(parsed))} ${unit}`;
}

function assumptionsFor(session: PlanningSession): FarmerAssumptions {
  const value = (session.assumptions || {}) as Partial<FarmerAssumptions>;
  return {
    tentative_orders: value.tentative_orders || [], future_demand: value.future_demand || [],
    seasonal: value.seasonal || [], order_changes: value.order_changes || [],
    reservations: value.reservations || [], ...(value.capacity ? { capacity: value.capacity } : {}),
  };
}

function hasReservation(proposal: FarmerProposal, bedId: string) {
  return (Array.isArray(proposal.changes) ? proposal.changes : []).some((change) =>
    (change as { assumptions?: FarmerAssumptions }).assumptions?.reservations?.some((row) => row.bed_id === bedId),
  );
}

export default function IntegratedCards({
  editionId = "v15",
  renderTool,
}: {
  editionId?: string;
  renderTool?: (tool: string, close: () => void) => ReactNode;
}) {
  const [bootstrap, setBootstrap] = useState<Bootstrap | null>(null);
  const [session, setSession] = useState<PlanningSession | null>(null);
  const [workflow, setWorkflow] = useState<FarmerWorkflowState>(emptyWorkflow);
  const [surface, setSurface] = useState<Surface>("mission");
  const [index, setIndex] = useState(0);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [reviewProposal, setReviewProposal] = useState<FarmerProposal | null>(null);
  const [reviewInverse, setReviewInverse] = useState<FarmerProposal | null>(null);
  const [detail, setDetail] = useState<"explain" | "review" | "inverse" | null>(null);
  const [transitionLabel, setTransitionLabel] = useState("");
  const [reducedMotion, setReducedMotion] = useState(false);
  const pointerStart = useRef<number | null>(null);
  const mutation = useRef(false);
  const loadInFlight = useRef(false);
  const cardRef = useRef<HTMLElement>(null);
  const resumedSession = useRef("");
  const transitionReady = useRef(false);

  const refreshWorkflow = useCallback(async () => {
    const value = await farmerWorkflowApi.state();
    setWorkflow({ ...emptyWorkflow, ...value });
    return value;
  }, []);

  const load = useCallback(async () => {
    if (loadInFlight.current) return;
    loadInFlight.current = true;
    setBusy("Opening sandbox farm");
    try {
      // Bootstrap establishes the tenant before any tenant-bound planning request.
      const farm = await api.bootstrap();
      const listed = await planningApi.list();
      let current: PlanningSession | undefined;
      const remembered = rememberedPlanningSession();
      if (remembered) {
        try {
          const candidate = await planningApi.get(remembered);
          if (candidate.workflow === true) current = candidate;
        } catch { /* stale local pointer; choose an ordinary workflow below */ }
      }
      current ||= listed.sessions.find((item) => item.workflow === true);
      if (!current) current = await planningApi.create("Integrated farm plan", true);
      rememberPlanningSession(current.id);
      setBootstrap(farm); setSession(current);
      const state = await refreshWorkflow();
      const proposals = state.proposals.filter((item) => item.session_id === current.id);
      const draft = [...proposals].reverse().find((item) => item.status === "draft");
      setReviewProposal(draft || null); setDetail(draft ? "review" : null);
    } catch (caught) {
      setError(message(caught, "The sandbox farm could not be opened."));
    } finally { setBusy(""); loadInFlight.current = false; }
  }, [refreshWorkflow]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    const update = () => {
      let stored = false;
      try { stored = localStorage.getItem(editionStorageKey("reduced-motion")) === "true"; } catch { /* optional */ }
      setReducedMotion(stored || document.documentElement.dataset.reducedMotion === "true" || matchMedia("(prefers-reduced-motion: reduce)").matches);
    };
    update(); window.addEventListener("storage", update);
    const observer = new MutationObserver(update); observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-reduced-motion"] });
    return () => { window.removeEventListener("storage", update); observer.disconnect(); };
  }, []);
  useEffect(() => {
    if (!session || resumedSession.current === session.id) return;
    resumedSession.current = session.id;
    const step = session.guidance?.step;
    if (step === "compare" || step === "tradeoff") setIndex(1);
    else if (["review", "recalculate", "approve"].includes(step || ""))
      setIndex(Math.max(0, missionCards.findIndex((card) => card.id === "reservation")));
    else if (step === "results") setIndex(Math.max(0, missionCards.findIndex((card) => card.id === "approved")));
  // missionCards intentionally excluded: resume once, without stealing later selection.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session?.id]);
  useEffect(() => {
    if (!session?.job || !["QUEUED", "RUNNING"].includes(session.job.status)) return;
    const timer = window.setInterval(() => {
      void planningApi.get(session.id).then(async (next) => {
        setSession(next);
        if (!["QUEUED", "RUNNING"].includes(next.job?.status || "")) {
          setBusy(""); await refreshWorkflow();
        }
      }).catch((caught) => setError(message(caught, "The calculation status could not be refreshed.")));
    }, 1600);
    return () => window.clearInterval(timer);
  }, [session?.id, session?.job?.id, session?.job?.status, refreshWorkflow]);

  const tactical = session?.tactical_context;
  const grow = tactical?.grow_space;
  const proposals = workflow.proposals.filter((item) => item.session_id === session?.id);
  const original = grow ? [...proposals].reverse().find((item) => !item.inverse_of_proposal_id && ["applied", "approved"].includes(item.status) && hasReservation(item, grow.id)) : undefined;
  const inverse = original ? proposals.find((item) => item.inverse_of_proposal_id === original.id) : undefined;
  const inverseComplete = Boolean(inverse?.recalculation_job?.id && inverse.recalculation_job.id === (session as { result_id?: string } | null)?.result_id);
  const activeProposal = original && !inverseComplete ? original : undefined;
  const proposalExplanation = activeProposal?.explanation as undefined | {
    what_changed?: string; why?: string; tradeoff?: string | Record<string, unknown>; next_action?: string;
    affected_bed_ids?: string[];
    evidence?: { before_result_id?: string; after_result_id?: string };
    inference_triggered?: boolean;
  };
  const sceneTransition = activeProposal?.scene_transition as undefined | {
    event_id?: string; entity_ids?: string[]; effective_date?: string; outcome_basis?: string;
  };
  const strategies = session?.result?.strategies || [];
  const feasible = strategies.filter((item) => item.status === "FEASIBLE" && !item.violations?.length);
  const chosen = feasible.find((item) => item.id === session?.selected_strategy_id) || feasible[0];
  const applied = proposals.find((item) => item.status === "applied" && item.recalculation_job?.id === (session as { result_id?: string } | null)?.result_id);
  const taskCount = workflow.tasks.filter((item) => proposals.some((proposal) => proposal.id === item.proposal_id)).length;

  useEffect(() => {
    const eventId = sceneTransition?.event_id;
    const key = editionStorageKey("seen-scene-transition");
    if (!transitionReady.current) {
      transitionReady.current = true;
      if (eventId) { try { localStorage.setItem(key, eventId); } catch { /* optional */ } }
      return;
    }
    if (!eventId) return;
    let seen = "";
    try { seen = localStorage.getItem(key) || ""; } catch { /* storage is optional */ }
    if (seen === eventId) return;
    try { localStorage.setItem(key, eventId); } catch { /* optional */ }
    if (!reducedMotion) setTransitionLabel(`Saved projection changed · ${sceneTransition.effective_date || "current planning date"}`);
    const timer = window.setTimeout(() => setTransitionLabel(""), 1500);
    return () => window.clearTimeout(timer);
  }, [sceneTransition?.event_id, sceneTransition?.effective_date, reducedMotion]);

  const missionCards = useMemo(() => {
    if (!session) return [];
    const base = [{
      id: "situation", eyebrow: "Farm situation", title: session.farm.name,
      summary: "Review the frozen farm, then calculate three choices from its real planning records.",
      facts: [
        ["Planning date", session.farm.planning_date || session.farm.cutoff],
        ["Confirmed orders", String(session.farm.orders.length)],
        ["Grow spaces", String(session.farm.beds.length)],
      ],
    }];
    if (!strategies.length) return base;
    const options = strategies.map((strategy) => ({
      id: `strategy-${strategy.id}`, eyebrow: "Calculated choice", title: `${strategy.name} plan`,
      summary: strategy.description || "A stored local-planner result for the same baseline and horizon.",
      strategy,
      facts: [
        ["Delivery covered", `${num(Number(strategy.metrics.fill_rate) * 100)}%`],
        ["Shortfall", `${num(strategy.metrics.shortfall_kg)} kg`],
        ["Cost", `SGD ${num(strategy.metrics.cost_sgd)}`],
      ],
    }));
    const reservation = grow ? [{
      id: "reservation", eyebrow: activeProposal ? "Applied constraint" : "Planning challenge",
      title: activeProposal ? `${grow.name} is reserved` : `Keep ${grow.name} available`,
      summary: activeProposal
        ? "The saved recalculation includes this reservation. Server deltas show its consequence."
        : "Reserve this exact grow space after its current crop clears and compare the recalculated plan.",
      facts: activeProposal ? [
        ["Production coverage", signed(activeProposal.metric_deltas?.coverage_kg, "kg")],
        ["Expiry exposure", signed(activeProposal.metric_deltas?.expiry_kg, "kg")],
        ["Planner margin", signed(activeProposal.metric_deltas?.margin_sgd, "SGD")],
      ] : [
        ["Record identity", `${grow.name} · ${grow.id}`],
        ["Area", `${num(grow.area_m2)} m²`],
        ["Window", `${grow.reservation_window.start_date} → ${grow.reservation_window.end_date}`],
      ],
    }] : [];
    const approved = taskCount ? [{
      id: "approved", eyebrow: "Recorded consequence", title: `${taskCount} sandbox task${taskCount === 1 ? "" : "s"} created`,
      summary: "Approval created simulation-only work. It did not authorize any physical farm operation.",
      facts: [["Session revision", String(session.revision)], ["Operations", "Disabled"], ["History", `${workflow.events.length} events`]],
    }] : [];
    return [...base, ...options, ...reservation, ...approved];
  }, [session, strategies, grow, activeProposal, taskCount, workflow.events.length]);

  const activeIndex = Math.min(index, Math.max(0, (surface === "tools" ? toolCards.length : missionCards.length) - 1));
  const move = (amount: number) => {
    const length = surface === "tools" ? toolCards.length : missionCards.length;
    if (surface !== "mission" && surface !== "tools") return;
    setIndex((value) => Math.max(0, Math.min(length - 1, value + amount)));
  };
  const run = async (label: string, operation: () => Promise<void>) => {
    if (mutation.current) return;
    mutation.current = true; setBusy(label); setError("");
    try { await operation(); }
    catch (caught) { setError(message(caught, `${label} failed. Your current review remains open.`)); }
    finally { mutation.current = false; setBusy(""); }
  };

  const guide = async (step: NonNullable<PlanningSession["guidance"]>["step"], skipped = false) => {
    if (!session) return;
    try { setSession(await planningApi.guidance(session, step, skipped)); }
    catch (caught) { setError(message(caught, "Guide progress was not saved; the planning record is unchanged.")); }
  };

  const calculate = () => session && run("Calculating three plans", async () => {
    setSession(await planningApi.calculate(session.id, session.revision));
    await guide("compare");
  });
  const propose = () => session && grow && chosen && run("Preparing reservation review", async () => {
    const next = assumptionsFor(session);
    next.reservations = [...next.reservations.filter((row) => row.bed_id !== grow.id),
      { bed_id: grow.id, ...grow.reservation_window }];
    const proposal = await farmerWorkflowApi.createProposal(session, chosen.id, next);
    setReviewProposal(proposal); setDetail("review"); await refreshWorkflow(); await guide("review");
  });
  const apply = () => reviewProposal && session && run("Applying and recalculating", async () => {
    await farmerWorkflowApi.applyProposal(reviewProposal);
    setReviewProposal(null); setDetail(null); setSession(await planningApi.get(session.id)); await refreshWorkflow(); await guide("recalculate");
  });
  const approve = () => applied && session && run("Approving simulation actions", async () => {
    await farmerWorkflowApi.approve(applied);
    await refreshWorkflow(); setSession(await planningApi.get(session.id)); await guide("results");
  });
  const prepareInverse = () => { if (original) { setReviewInverse(original); setDetail("inverse"); } };
  const acceptInverse = () => reviewInverse && session && run("Recalculating inverse", async () => {
    await farmerWorkflowApi.inverseProposal(reviewInverse);
    setReviewInverse(null); setDetail(null); setSession(await planningApi.get(session.id)); await refreshWorkflow();
  });

  const primary = () => {
    if (surface === "tools") { setSurface(toolCards[activeIndex].id); setIndex(0); return; }
    const card = missionCards[activeIndex];
    if (!strategies.length) void calculate();
    else if (card?.id.startsWith("strategy-")) { setIndex(missionCards.findIndex((item) => item.id === "reservation")); void guide("tradeoff"); }
    else if (card?.id === "reservation" && !activeProposal) void propose();
    else if (card?.id === "reservation" && activeProposal) void approve();
    else setSurface("tools");
  };

  const keyboard = (event: KeyboardEvent<HTMLDivElement>) => {
    if ((event.target as HTMLElement).closest("button,a,input,select,textarea")) return;
    if (event.key === "ArrowLeft") { event.preventDefault(); move(-1); }
    if (event.key === "ArrowRight") { event.preventDefault(); move(1); }
    if (event.key === "Enter") { event.preventDefault(); primary(); }
  };
  const closeDetail = () => {
    setDetail(null); setReviewProposal(null); setReviewInverse(null);
    window.requestAnimationFrame(() => cardRef.current?.focus());
  };
  const closeTool = () => {
    setSurface("tools"); setIndex(0); void load();
  };
  const pointerUp = (event: PointerEvent<HTMLDivElement>) => {
    if (pointerStart.current == null) return;
    const distance = event.clientX - pointerStart.current; pointerStart.current = null;
    if (Math.abs(distance) > 48) move(distance < 0 ? 1 : -1);
  };

  if (!session || !bootstrap) return <section className="ic-state" aria-live="polite"><span className="ic-spinner" />
    <h1>{error ? "Sandbox farm unavailable" : "Opening sandbox farm"}</h1><p>{error || busy || "Loading ordinary farm and planning records."}</p>
    {error && <button onClick={() => void load()}>Try again</button>}</section>;

  const current = surface === "tools" ? toolCards[activeIndex] : missionCards[activeIndex];
  const toolOpen = surface !== "mission" && surface !== "tools";
  const sceneBeds = (session.simulation?.beds?.length ? session.simulation.beds : session.farm.beds).slice(0, 8);
  const raw = session.farm as typeof session.farm & { batches?: Array<Record<string, unknown>> };
  const batches = new Map((raw.batches || []).map((row) => [String(row.bed_id), row]));
  const recipes = new Map(((raw as typeof raw & { recipes?: Array<Record<string, unknown>> }).recipes || [])
    .map((row) => [String(row.id), String(row.crop_id)]));
  const objectiveOrder = session.farm.orders[0];
  const boundCard: FarmCard | null = surface === "mission" && current ? {
    id: current.id, entityId: current.id === "reservation" ? grow?.id || current.id : current.id,
    entityKind: current.id.startsWith("strategy-") ? "strategy" : current.id,
    title: current.title, provenance: ["ordinary farm bootstrap", "stored planning session"],
    binding: { sessionId: session.id, inputHash: session.input_hash, revision: session.revision,
      resultId: (session as { result_id?: string }).result_id || null },
    boardTargets: current.id === "reservation" && grow ? [grow.id] : [],
    actions: [{ id: "primary", label: "Primary action", eligible: !busy }],
    outcomeBasis: "projection",
  } : null;

  const tradeoffText = proposalExplanation?.tradeoff && typeof proposalExplanation.tradeoff === "object"
    ? Object.entries(proposalExplanation.tradeoff).map(([key, value]) => `${key.replaceAll("_", " ")}: ${typeof value === "number" ? signed(value, key.includes("sgd") ? "SGD" : "kg") : String(value)}`).join("; ")
    : proposalExplanation?.tradeoff;
  const transitionEntities = new Set(sceneTransition?.entity_ids || []);
  return <section className={`ic-shell ${reducedMotion ? "is-reduced-motion" : ""}`} data-edition={editionId} onKeyDown={keyboard} tabIndex={-1}>
    <header className="ic-heading"><div><span>Objective · deliver the confirmed order</span><strong>{objectiveOrder ? `${num(objectiveOrder.quantity_kg)} kg ${objectiveOrder.crop_id.replaceAll("_", " ")} by ${objectiveOrder.due_date}` : session.farm.name}</strong></div>
      <p>Sandbox farm · real operations disabled</p></header>
    <div className="ic-layout">
      <section className={`ic-scene ${transitionLabel ? "is-transitioning" : ""}`} aria-label="Passive farm scene">
        <div className="ic-scene-head"><span>Farm scene</span><strong>{session.farm.planning_date || session.farm.cutoff}</strong></div>
        <div className="ic-beds">{sceneBeds.map((bed) => {
          const batch = batches.get(bed.id), crop = String(batch?.crop_id || recipes.get(String(batch?.recipe_id)) || bed.crop_id || "");
          const stage = String(batch?.stage || bed.stage || (crop ? "growing" : "empty"));
          const assetStage = stage === "ready" ? "ready" : stage === "nursery" ? "seedling" : stage === "growing" ? "growing" : "";
          const src = crop && assetStage ? `/art/crops/${crop}-${assetStage}.svg` : "";
          const focused = grow?.id === bed.id && current?.id === "reservation";
          const changing = Boolean(transitionLabel && transitionEntities.has(bed.id));
          return <article key={bed.id} className={`${focused ? "is-focus" : ""} ${changing ? "is-changing" : ""}`}><b>{bed.name}</b>
            {src ? <img src={src} alt="" onError={(event) => { event.currentTarget.hidden = true; }} /> : <span className="ic-empty">Empty</span>}
            <small>{crop ? crop.replaceAll("_", " ") : "Available"}</small><em>{stage}</em></article>;
        })}</div>
        <p className="ic-scene-note">Scene reflects saved records. Selecting cards only changes the highlighted preview.</p>
        {transitionLabel && <p className="ic-transition" role="status">{transitionLabel}</p>}
        {sceneTransition?.event_id && <p className="ic-saved-change">Saved projection · {sceneTransition.effective_date} · {(sceneTransition.entity_ids || []).join(", ") || "planning result"}</p>}
      </section>

      <div className="ic-card-column">
        {error && <div className="ic-error" role="alert"><span>{error}</span><button onClick={() => setError("")}>Dismiss</button></div>}
        {toolOpen ? <section className="ic-tool"><button className="ic-back" onClick={closeTool}>← Farm tools</button>
          <div className="ic-tool-body">{renderTool ? renderTool(surface, closeTool) : <><span className="ic-eyebrow">Tool adapter</span>
            <h2>{toolCards.find((item) => item.id === surface)?.title}</h2><p>This tool is unavailable in this build.</p></>}</div></section> : <>
          <div className="ic-deck" onPointerDown={(event) => { pointerStart.current = event.clientX; }} onPointerUp={pointerUp}>
            <article ref={cardRef} tabIndex={-1} className="ic-card" data-card-id={boundCard?.id} data-session-revision={boundCard?.binding.revision} aria-live="polite" aria-label={`${surface === "tools" ? "Farm tools" : "Planning"} card ${activeIndex + 1} of ${surface === "tools" ? toolCards.length : missionCards.length}`}>
              {detail === "explain" ? <><span className="ic-eyebrow">{current.title} › Why</span><h1>What this means</h1><p>{current.summary}</p>
                <dl><div><dt>Why / tradeoff</dt><dd>{current.id === "reservation" && proposalExplanation ? `${proposalExplanation.why || "Reason not available for this saved result"} ${tradeoffText || ""}` : current.id === "reservation" ? "Less available grow space can change future production, cost and shortfall." : current.id.startsWith("strategy-") ? "Each option uses the same baseline while balancing delivery, cost and space differently." : "This card reflects the saved farm and planning state."}</dd></div>
                  <div><dt>Evidence / limits</dt><dd>{proposalExplanation?.evidence ? `${proposalExplanation.evidence.before_result_id || "baseline"} → ${proposalExplanation.evidence.after_result_id || "current result"}` : boundCard?.provenance.join(" · ") || "Stored farm records"}; no provider call.</dd></div>
                  <div><dt>Record identity</dt><dd>{boundCard ? `${boundCard.entityKind} · ${boundCard.entityId}` : current.id}</dd></div></dl></>
                : detail === "review" || detail === "inverse" ? <><span className="ic-eyebrow">Review before applying</span><h1>{detail === "inverse" ? "Restore the grow space" : `Reserve ${grow?.name || "grow space"}`}</h1>
                  <p>{detail === "inverse" ? "The inverse preserves the original event and recalculates future work at the current eligible revision." : `${grow?.id} will be unavailable ${grow?.reservation_window.start_date} to ${grow?.reservation_window.end_date}. Existing work remains recorded.`}</p>
                  <dl><div><dt>Proposal</dt><dd>{String((reviewInverse || reviewProposal)?.id)}</dd></div><div><dt>Revision</dt><dd>{(reviewInverse || reviewProposal)?.proposal_revision}</dd></div><div><dt>Scope</dt><dd>Future simulation work only</dd></div></dl></>
                : <><span className="ic-eyebrow">{"eyebrow" in current ? current.eyebrow : "Farm tools"}</span>
                  <h1>{current.title}</h1><p>{current.summary}</p>
                  {current.id.startsWith("strategy-") && <span className="ic-preview">Preview—not saved</span>}
                  {"facts" in current && current.facts && <dl>{current.facts.slice(0, 3).map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>}
                  {surface === "tools" && <span className="ic-path">Farm tools › {current.title}</span>}</>}
            </article>
          </div>
          <nav className="ic-actions" aria-label="Card actions">
            <div className="ic-deck-nav"><button onClick={() => move(-1)} disabled={activeIndex === 0}>← Previous</button>
              <span>{surface === "tools" ? "Farm tools" : "Farm plan"} · {activeIndex + 1} of {surface === "tools" ? toolCards.length : missionCards.length}</span>
              <button onClick={() => move(1)} disabled={activeIndex === (surface === "tools" ? toolCards.length : missionCards.length) - 1}>Next →</button></div>
            <div className="ic-keys">
              {detail ? <><button onClick={closeDetail}>Back</button><button className="is-primary" disabled={Boolean(busy || (detail === "review" && !reviewProposal) || (detail === "inverse" && !reviewInverse))} onClick={() => void (detail === "review" ? apply() : detail === "inverse" ? acceptInverse() : closeDetail())}>{busy || (detail === "review" ? "Apply & recalculate" : detail === "inverse" ? "Confirm inverse" : "Back to card")}</button>{detail === "explain" && activeProposal?.undo?.available && current?.id === "reservation" ? <button onClick={prepareInverse}>Review inverse</button> : detail === "explain" ? <button onClick={() => void guide(session.guidance?.step || "inspect", !session.guidance?.skipped)}>{session.guidance?.skipped ? "Resume guide" : "Skip guide"}</button> : <button onClick={() => setDetail("explain")}>Details</button>}</>
                : <><button onClick={() => setDetail("explain")}>Explain</button>
                  <button className="is-primary" disabled={Boolean(busy)} onClick={primary}>{busy || (surface === "tools" ? "Open tool" : !strategies.length ? "Calculate" : current?.id === "reservation" ? activeProposal ? "Approve actions" : "Review reservation" : "Continue")}</button>
                  <button onClick={() => setSurface("tools")}>More</button></>}
            </div>
          </nav>
        </>}
      </div>
    </div>
  </section>;
}
