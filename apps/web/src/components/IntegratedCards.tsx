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
import { ApiError, api } from "../lib/api";
import type { FarmCard, ToolDeck, ToolTarget } from "../lib/cards";
import BoundCard from "./BoundCard";
import { CURRENT_EDITION, editionStorageKey } from "../lib/edition";
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
  if (value === null || value === undefined || value === "") return "—";
  const parsed = Number(value);
  return Number.isFinite(parsed)
    ? new Intl.NumberFormat(undefined, { maximumFractionDigits: digits }).format(parsed)
    : "—";
}

function signed(value: unknown, unit: string) {
  if (value === null || value === undefined || value === "") return "Not reported";
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return "Not reported";
  return `${parsed > 0 ? "+" : parsed < 0 ? "−" : "±"}${num(Math.abs(parsed))} ${unit}`;
}

function difference(left: unknown, right: unknown, multiplier = 1) {
  if (left === null || left === undefined || right === null || right === undefined) return null;
  const a = Number(left), b = Number(right);
  return Number.isFinite(a) && Number.isFinite(b) ? (a - b) * multiplier : null;
}

function progressLabel(stage: string | null | undefined) {
  if (!stage) return "Calculating plans…";
  const known: Record<string, string> = {
    queued: "Waiting to calculate…",
    calculating_schedules_and_inventory: "Calculating schedules and inventory…",
    calculating_strategies: "Comparing plan choices…",
    recalculating: "Recalculating plans…",
  };
  return known[stage.toLowerCase()] || `${stage.replaceAll("_", " ").replace(/^./, (letter) => letter.toUpperCase())}…`;
}

function assumptionsFor(session: PlanningSession): FarmerAssumptions {
  const value = (session.assumptions || {}) as Partial<FarmerAssumptions>;
  return {
    tentative_orders: value.tentative_orders || [], future_demand: value.future_demand || [],
    seasonal: value.seasonal || [], order_changes: value.order_changes || [],
    reservations: value.reservations || [], ...(value.capacity ? { capacity: value.capacity } : {}),
  };
}

function isReservationOnly(proposal: FarmerProposal, session: PlanningSession, bedId: string) {
  const changes = Array.isArray(proposal.changes) ? proposal.changes as Array<{ kind?: string; assumptions?: FarmerAssumptions }> : [];
  if (changes.length !== 1 || changes[0].kind !== "planning_assumptions" || !changes[0].assumptions) return false;
  const inverse = Array.isArray(proposal.inverse_changes) ? proposal.inverse_changes as Array<{ kind?: string; assumptions?: FarmerAssumptions }> : [];
  const frozenBefore = inverse.length === 1 && inverse[0].kind === "planning_assumptions" ? inverse[0].assumptions : undefined;
  // A draft is still based on the current revision. Once applied, only the
  // proposal's frozen inverse records the actual before state; never infer it
  // from the already-mutated current session.
  const before = proposal.status === "draft" ? assumptionsFor(session) : frozenBefore;
  if (!before) return false;
  const after = changes[0].assumptions;
  const unchangedArrays = ["tentative_orders", "future_demand", "seasonal", "order_changes"] as const;
  if (unchangedArrays.some((key) => JSON.stringify(before[key] || []) !== JSON.stringify(after[key] || []))) return false;
  if (JSON.stringify(before.capacity ?? null) !== JSON.stringify(after.capacity ?? null)) return false;
  const withoutBed = (rows: FarmerAssumptions["reservations"] = []) => rows.filter((row) => row.bed_id !== bedId);
  if (JSON.stringify(withoutBed(before.reservations)) !== JSON.stringify(withoutBed(after.reservations))) return false;
  const reservation = after.reservations?.find((row) => row.bed_id === bedId);
  const previous = before.reservations?.find((row) => row.bed_id === bedId);
  return Boolean(reservation && JSON.stringify(reservation) !== JSON.stringify(previous ?? null));
}

function reservationChangeText(proposal: FarmerProposal) {
  type AssumptionChange = { kind?: string; assumptions?: FarmerAssumptions };
  const changes = Array.isArray(proposal.changes) ? proposal.changes as AssumptionChange[] : [];
  const inverse = Array.isArray(proposal.inverse_changes) ? proposal.inverse_changes as AssumptionChange[] : [];
  if (changes.length !== 1 || inverse.length !== 1 || changes[0].kind !== "planning_assumptions" || inverse[0].kind !== "planning_assumptions") return undefined;
  const before = inverse[0].assumptions, after = changes[0].assumptions;
  if (!before || !after) return undefined;
  const unchanged = ["tentative_orders", "future_demand", "seasonal", "order_changes"] as const;
  if (unchanged.some((key) => JSON.stringify(before[key] || []) !== JSON.stringify(after[key] || []))) return undefined;
  if (JSON.stringify(before.capacity ?? null) !== JSON.stringify(after.capacity ?? null)) return undefined;
  const beforeRows = new Map((before.reservations || []).map((row) => [row.bed_id, row]));
  const afterRows = new Map((after.reservations || []).map((row) => [row.bed_id, row]));
  const changedBeds = [...new Set([...beforeRows.keys(), ...afterRows.keys()])]
    .filter((id) => JSON.stringify(beforeRows.get(id) ?? null) !== JSON.stringify(afterRows.get(id) ?? null));
  if (changedBeds.length !== 1) return undefined;
  const bedId = changedBeds[0], previous = beforeRows.get(bedId), saved = afterRows.get(bedId);
  if (saved && !previous) return `Saved reservation for ${bedId} from ${saved.start_date} to ${saved.end_date}.`;
  if (!saved && previous) return `Restored ${bedId} by removing the saved reservation from ${previous.start_date} to ${previous.end_date}.`;
  if (saved && previous) return `Updated reservation for ${bedId} from ${previous.start_date}–${previous.end_date} to ${saved.start_date}–${saved.end_date}.`;
  return undefined;
}

function reservationStateText(proposal: FarmerProposal | undefined, bedId: string, fallback?: FarmerAssumptions["reservations"][number]) {
  type AssumptionChange = { kind?: string; assumptions?: FarmerAssumptions };
  const change = (Array.isArray(proposal?.changes) ? proposal.changes as AssumptionChange[] : []).find((row) => row.kind === "planning_assumptions");
  const inverse = (Array.isArray(proposal?.inverse_changes) ? proposal.inverse_changes as AssumptionChange[] : []).find((row) => row.kind === "planning_assumptions");
  if (!proposal) return fallback ? `${bedId} is currently saved from ${fallback.start_date} to ${fallback.end_date}; no bound proposal comparison is available.` : `${bedId} has no saved reservation and no bound proposal comparison is available.`;
  if (!change?.assumptions || !inverse?.assumptions) return `${bedId} before/after reservation facts are unavailable in this frozen proposal.`;
  const before = inverse.assumptions.reservations?.find((row) => row.bed_id === bedId);
  const after = change.assumptions.reservations?.find((row) => row.bed_id === bedId);
  const dates = (row: typeof after) => row ? `${row.start_date} to ${row.end_date}` : "no saved reservation";
  if (before && after && JSON.stringify(before) === JSON.stringify(after)) return `${bedId} remained reserved from ${dates(after)}; this proposal did not change that reservation.`;
  if (!before && after) return `${bedId} changed from no saved reservation to ${dates(after)}.`;
  if (before && !after) return `${bedId} changed from ${dates(before)} to no saved reservation.`;
  if (before && after) return `${bedId} changed from ${dates(before)} to ${dates(after)}.`;
  return `${bedId} has no reservation dates in the frozen proposal facts.`;
}

function newerSession(current: PlanningSession | null, next: PlanningSession) {
  if (!current) return next;
  if (current.id !== next.id) return next;
  if (next.revision !== current.revision) return next.revision > current.revision ? next : current;
  return next.updated_at >= current.updated_at ? next : current;
}

function afterPaint(callback: () => void) {
  window.requestAnimationFrame(() => window.requestAnimationFrame(callback));
}

export default function IntegratedCards({
  editionId = CURRENT_EDITION,
  renderTool,
}: {
  editionId?: string;
  renderTool?: (tool: ToolDeck, close: () => void, initialTarget?: ToolTarget) => ReactNode;
}) {
  const [bootstrap, setBootstrap] = useState<Bootstrap | null>(null);
  const [session, setSession] = useState<PlanningSession | null>(null);
  const [workflow, setWorkflow] = useState<FarmerWorkflowState>(emptyWorkflow);
  const [surface, setSurface] = useState<Surface>("mission");
  const [index, setIndex] = useState(0);
  const [loadingBusy, setLoadingBusy] = useState("");
  const [mutationBusy, setMutationBusy] = useState("");
  const [guidanceBusy, setGuidanceBusy] = useState("");
  const [error, setError] = useState("");
  const [reviewProposal, setReviewProposal] = useState<FarmerProposal | null>(null);
  const [reviewInverse, setReviewInverse] = useState<FarmerProposal | null>(null);
  const [detail, setDetail] = useState<"explain" | "review" | "inverse" | null>(null);
  const [transitionLabel, setTransitionLabel] = useState("");
  const [reducedMotion, setReducedMotion] = useState(false);
  const [toolTarget, setToolTarget] = useState<ToolTarget | undefined>();
  const [demoStep, setDemoStep] = useState<number | null>(null);
  const pointerStart = useRef<number | null>(null);
  const mutation = useRef(false);
  const guidanceInFlight = useRef(false);
  const loadInFlight = useRef(false);
  const loadQueued = useRef(false);
  const loadGeneration = useRef(0);
  const cardRef = useRef<HTMLElement>(null);
  const missionIndex = useRef(0);
  const missionScroll = useRef(0);
  const origin = useRef<{ label: string; scroll: number } | null>(null);
  const missionOrigin = useRef<{ label: string; scroll: number } | null>(null);
  const pendingRestore = useRef<{ label: string; scroll: number } | null>(null);
  const directTool = useRef(false);
  const navigationReady = useRef(false);
  const resumedSession = useRef("");
  const transitionReady = useRef(false);
  const pollGeneration = useRef(0);
  const dataGeneration = useRef(0);
  const selectedSession = useRef("");
  const busy = mutationBusy || guidanceBusy || loadingBusy;

  const refreshWorkflow = useCallback(async () => {
    const generation = ++dataGeneration.current;
    const value = await farmerWorkflowApi.state();
    if (generation === dataGeneration.current) setWorkflow({ ...emptyWorkflow, ...value });
    return value;
  }, []);

  const reconcileSession = useCallback(async (id: string, received?: PlanningSession, stillCurrent: () => boolean = () => true) => {
    if (selectedSession.current && selectedSession.current !== id) return null;
    const generation = ++dataGeneration.current;
    const next = received || await planningApi.get(id);
    const state = await farmerWorkflowApi.state();
    if (generation !== dataGeneration.current || selectedSession.current !== id || !stillCurrent()) return null;
    // React batches these updates. A terminal result therefore cannot render
    // against proposal/explanation facts from an older workflow receipt.
    setWorkflow({ ...emptyWorkflow, ...state });
    setSession((current) => newerSession(current, next));
    return next;
  }, []);

  const load = useCallback(async () => {
    if (loadInFlight.current) {
      loadQueued.current = true;
      ++loadGeneration.current; ++dataGeneration.current; ++pollGeneration.current;
      const intended = rememberedPlanningSession();
      if (intended) selectedSession.current = intended;
      return;
    }
    loadInFlight.current = true;
    setLoadingBusy("Opening sandbox farm");
    try {
      do {
        loadQueued.current = false;
        ++pollGeneration.current;
        const dataOwner = ++dataGeneration.current, generation = ++loadGeneration.current;
        const intended = rememberedPlanningSession();
        if (intended) selectedSession.current = intended;
        try {
          // Bootstrap establishes the tenant before any tenant-bound planning request.
          const farm = await api.bootstrap();
          const listed = await planningApi.list();
          let current: PlanningSession | undefined;
          if (intended) {
            try {
              const candidate = await planningApi.get(intended);
              if (candidate.workflow === true) current = candidate;
            } catch (caught) {
              if (!(caught instanceof ApiError) || caught.status !== 404) throw caught;
              /* stale local pointer; choose an ordinary workflow below */
            }
          }
          if (rememberedPlanningSession() !== intended) {
            loadQueued.current = true; ++loadGeneration.current; ++dataGeneration.current; continue;
          }
          current ||= listed.sessions.find((item) => item.workflow === true);
          if (!current) current = await planningApi.create("Integrated farm plan", true);
          if (generation !== loadGeneration.current || dataOwner !== dataGeneration.current || rememberedPlanningSession() !== intended) {
            if (rememberedPlanningSession() !== intended) loadQueued.current = true;
            continue;
          }
          selectedSession.current = current.id;
          const state = await farmerWorkflowApi.state();
          if (generation !== loadGeneration.current || dataOwner !== dataGeneration.current || selectedSession.current !== current.id || rememberedPlanningSession() !== intended) {
            if (rememberedPlanningSession() !== intended) {
              loadQueued.current = true; ++loadGeneration.current; ++dataGeneration.current;
              const latest = rememberedPlanningSession();
              if (latest) selectedSession.current = latest;
            }
            continue;
          }
          rememberPlanningSession(current.id);
          setWorkflow({ ...emptyWorkflow, ...state });
          setBootstrap(farm); setSession((existing) => newerSession(existing, current));
          const proposals = state.proposals.filter((item) => item.session_id === current.id);
          const growSpaceId = current.tactical_context?.grow_space?.id;
          const reservationDraft = growSpaceId
            ? [...proposals].reverse().find((item) => item.status === "draft" && isReservationOnly(item, current, growSpaceId))
            : undefined;
          setReviewProposal(reservationDraft || null); setDetail(null); setError("");
        } catch (caught) {
          if (generation === loadGeneration.current && dataOwner === dataGeneration.current)
            setError(message(caught, "The sandbox farm could not be opened."));
        }
      } while (loadQueued.current);
    } finally { setLoadingBusy(""); loadInFlight.current = false; }
  }, []);

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
    navigationReady.current = false;
    resumedSession.current = session.id;
    try {
      const saved = JSON.parse(localStorage.getItem(editionStorageKey(`integrated-cards-navigation:${session.id}`)) || "null") as { surface?: Surface; index?: number; missionIndex?: number; missionScroll?: number; directTool?: boolean; toolTarget?: ToolTarget; origin?: { label: string; scroll: number }; missionOrigin?: { label: string; scroll: number } } | null;
      if (saved && ["mission", "tools", ...toolCards.map((item) => item.id)].includes(saved.surface as Surface)) {
        setSurface(saved.surface as Surface); setIndex(Math.max(0, Number(saved.index) || 0)); missionIndex.current = Math.max(0, Number(saved.missionIndex) || 0);
        missionScroll.current = Math.max(0, Number(saved.missionScroll) || 0); directTool.current = Boolean(saved.directTool);
        setToolTarget(saved.toolTarget);
        origin.current = saved.origin || null; missionOrigin.current = saved.missionOrigin || null;
        window.requestAnimationFrame(() => { navigationReady.current = true; });
        return;
      }
    } catch { /* invalid navigation state falls back to guidance */ }
    const step = session.guidance?.step;
    if (step === "compare" || step === "tradeoff") setIndex(1);
    else if (["review", "recalculate", "approve"].includes(step || ""))
      setIndex(Math.max(0, missionCards.findIndex((card) => card.id === "reservation")));
    else if (step === "results") setIndex(Math.max(0, missionCards.findIndex((card) => card.id === "approved")));
    window.requestAnimationFrame(() => { navigationReady.current = true; });
  // missionCards intentionally excluded: resume once, without stealing later selection.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session?.id]);
  useEffect(() => {
    if (!session) return;
    try {
      const saved = JSON.parse(localStorage.getItem(editionStorageKey(`first-use-demo:${session.id}`)) || "null") as { step?: number; done?: boolean; skipped?: boolean } | null;
      if (!saved) setDemoStep(0);
      else if (!saved.done && !saved.skipped) setDemoStep(Math.max(0, Number(saved.step) || 0));
      else setDemoStep(null);
    } catch { setDemoStep(0); }
  }, [session?.id]);
  useEffect(() => {
    if (!session || !navigationReady.current || detail) return;
    try { localStorage.setItem(editionStorageKey(`integrated-cards-navigation:${session.id}`), JSON.stringify({ surface, index, missionIndex: missionIndex.current, missionScroll: missionScroll.current, directTool: directTool.current, toolTarget, origin: origin.current, missionOrigin: missionOrigin.current })); } catch { /* optional */ }
  }, [session?.id, surface, index, detail, toolTarget]);
  useEffect(() => {
    if (loadingBusy || !pendingRestore.current) return;
    const restore = pendingRestore.current; pendingRestore.current = null;
    afterPaint(() => {
      window.scrollTo({ top: restore.scroll, behavior: "auto" });
      [...document.querySelectorAll<HTMLButtonElement>(".ic-context-links button,.ic-tool-index button,.ic-actions button")].find((button) => button.textContent?.trim() === restore.label)?.focus();
    });
  }, [loadingBusy, surface, index]);
  useEffect(() => {
    if (loadingBusy) return;
    if (!session?.job || !["QUEUED", "RUNNING"].includes(session.job.status)) return;
    let cancelled = false, timer = 0;
    const generation = ++pollGeneration.current;
    const poll = async () => {
      try {
        const next = await planningApi.get(session.id);
        if (cancelled || generation !== pollGeneration.current || selectedSession.current !== session.id) return;
        if (!["QUEUED", "RUNNING"].includes(next.job?.status || "")) {
          // Fetch the workflow after the terminal session receipt. Publish both
          // together so the result never renders against an older proposal list.
          const reconciled = await reconcileSession(session.id, next,
            () => !cancelled && generation === pollGeneration.current && selectedSession.current === session.id);
          if (!reconciled && !cancelled && generation === pollGeneration.current && selectedSession.current === session.id)
            timer = window.setTimeout(() => { void poll(); }, 1600);
          return;
        }
        setSession((current) => newerSession(current, next));
        timer = window.setTimeout(() => { void poll(); }, 1600);
      } catch (caught) {
        if (cancelled || generation !== pollGeneration.current) return;
        setError(message(caught, "The calculation status could not be refreshed."));
        timer = window.setTimeout(() => { void poll(); }, 1600);
      }
    };
    timer = window.setTimeout(() => { void poll(); }, 1600);
    return () => { cancelled = true; ++pollGeneration.current; window.clearTimeout(timer); };
  }, [session?.id, session?.job?.id, session?.job?.status, loadingBusy, reconcileSession]);

  const tactical = session?.tactical_context;
  const snapshotBinding = tactical?.planning_snapshot;
  const boundResultId = snapshotBinding?.result_id || (session as { result_id?: string } | null)?.result_id;
  const grow = tactical?.grow_space;
  const proposals = workflow.proposals.filter((item) => item.session_id === session?.id);
  const original = grow && session ? [...proposals].reverse().find((item) => !item.inverse_of_proposal_id && ["applied", "approved"].includes(item.status) && isReservationOnly(item, session, grow.id)) : undefined;
  const inverse = original ? proposals.find((item) => item.inverse_of_proposal_id === original.id) : undefined;
  const inverseComplete = Boolean(inverse?.recalculation_job?.id && inverse.recalculation_job.id === (session as { result_id?: string } | null)?.result_id);
  const activeProposal = original && !inverseComplete ? original : undefined;
  const boundProposal = [...proposals].reverse().find((item) => ["applied", "approved"].includes(item.status) && item.recalculation_job?.id === boundResultId);
  const reservationExplanationProposal = grow && session ? [...proposals].reverse().find((item) => ["applied", "approved"].includes(item.status) && item.recalculation_job?.id === boundResultId && isReservationOnly(item, session, grow.id)) : undefined;
  const proposalTransition = boundProposal?.scene_transition;
  const simulationTransition = session?.simulation?.scene_transition;
  const sceneTransition = simulationTransition || proposalTransition;
  const strategies = session?.result?.strategies || [];
  const feasible = strategies.filter((item) => item.status === "FEASIBLE" && !item.violations?.length);
  const chosen = feasible.find((item) => item.id === session?.selected_strategy_id) || feasible[0];
  const applied = proposals.find((item) => item.status === "applied" && item.recalculation_job?.id === (session as { result_id?: string } | null)?.result_id);
  const approval = applied?.approval as undefined | { available?: boolean; reason?: string; strategy_id?: string };
  const taskCount = workflow.tasks.filter((item) => proposals.some((proposal) => proposal.id === item.proposal_id)).length;
  const boundTasks = boundProposal ? workflow.tasks.filter((item) => item.proposal_id === boundProposal.id) : [];
  const sessionTasks = workflow.tasks.filter((item) => proposals.some((proposal) => proposal.id === item.proposal_id));
  const approvedTasks = boundTasks.length ? boundTasks : sessionTasks;

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
    if (!reducedMotion) setTransitionLabel(`${sceneTransition.outcome_basis === "recorded_simulation" ? "Recorded simulation" : "Saved projection"} changed · ${sceneTransition.effective_date || "current planning date"}`);
    const timer = window.setTimeout(() => setTransitionLabel(""), 1500);
    return () => window.clearTimeout(timer);
  }, [sceneTransition?.event_id, sceneTransition?.effective_date, reducedMotion]);

  const missionCards = useMemo(() => {
    if (!session) return [];
    const base = [{
      id: "situation", eyebrow: "Sample farm · current situation", title: session.farm.name,
      summary: `This selected order is the example. Planning still includes all ${session.farm.orders.length} order lines across the ${session.farm.horizon_days}-day horizon.`,
      facts: [
        ["Sample farm date", session.farm.planning_date || session.farm.cutoff],
        ["All demand lines", String(session.farm.orders.length)],
        ["Planning horizon", `${session.farm.horizon_days} days`],
        ["Grow spaces", String(session.farm.beds.length)],
      ],
    }];
    if (!strategies.length) return base;
    const options = strategies.map((strategy) => ({
      id: `strategy-${strategy.id}`, eyebrow: "Calculated choice", title: `${strategy.name} plan`,
      summary: strategy.description || "A stored local-planner result for the same baseline and horizon.",
      strategy,
      facts: [
        ["All-demand coverage", `${num(strategy.metrics.fill_rate == null ? null : Number(strategy.metrics.fill_rate) * 100)}%`],
        ["All-demand shortfall", `${num(strategy.metrics.shortfall_kg)} kg`],
        ["Horizon", `${session.farm.horizon_days} days`],
        ["Selected order", "Coverage not separately reported"],
      ],
    }));
    const reservation = grow ? [{
      id: "reservation", eyebrow: activeProposal ? "Applied constraint" : "Optional sample constraint",
      title: activeProposal ? `${grow.name} is reserved` : `Try setting ${grow.name} aside`,
      summary: activeProposal
        ? "The saved recalculation includes this reservation. Server deltas show its consequence."
        : `Practice a what-if: leave ${grow.name} out of future allocations from ${grow.reservation_window.start_date} to ${grow.reservation_window.end_date}, then compare production and cost before deciding.`,
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
    const approved = approvedTasks.length ? [{
      id: "approved", eyebrow: "Approval record · tasks are not results", title: `${approvedTasks.length} sandbox task${approvedTasks.length === 1 ? "" : "s"} created, not completed`,
      summary: "Approval created a simulation-only work list. Completion and recorded simulation results are separate; no physical farm operation was authorized.",
      facts: [["Session revision", String(session.revision)], ["Operations", "Disabled"], ["History", `${workflow.events.length} events`]],
    }] : [];
    const recorded = session.simulation ? [{
      id: "simulation-result", eyebrow: "Recorded simulation", title: `Farm date ${session.simulation.clock_date || session.simulation.start_date}`,
      summary: "These quantities come from recorded simulation events, separate from the planning projection.",
      facts: [["Harvested", `${num(session.simulation.totals.harvest_kg)} kg`], ["Delivered", `${num(session.simulation.totals.delivered_kg)} kg`], ["Cash", `SGD ${num(session.simulation.cash_sgd)}`]],
    }] : [];
    return [...base, ...options, ...reservation, ...approved, ...recorded];
  }, [session, strategies, grow, activeProposal, approvedTasks.length, workflow.events.length]);

  const activeIndex = Math.min(index, Math.max(0, (surface === "tools" ? toolCards.length : missionCards.length) - 1));
  const move = (amount: number) => {
    const length = surface === "tools" ? toolCards.length : missionCards.length;
    if (surface !== "mission" && surface !== "tools") return;
    setIndex((value) => Math.max(0, Math.min(length - 1, value + amount)));
  };
  const run = async (label: string, operation: () => Promise<void>) => {
    if (mutation.current) return;
    mutation.current = true; setMutationBusy(label); setError("");
    try { await operation(); }
    catch (caught) {
      if (caught instanceof ApiError && caught.status === 409 && session) {
        try { await reconcileSession(session.id); } catch { /* retain original stale error */ }
        setError(`${caught.message}. Current saved state was refreshed; review it before trying again.`);
      } else setError(message(caught, `${label} failed. Your current review remains open.`));
    }
    finally { mutation.current = false; setMutationBusy(""); }
  };

  const guide = async (step: NonNullable<PlanningSession["guidance"]>["step"], skipped = false) => {
    if (!session || guidanceInFlight.current) return;
    const actionSessionId = session.id;
    guidanceInFlight.current = true; setGuidanceBusy("Saving guide progress");
    try {
      await planningApi.guidance(session, step, skipped);
      if (selectedSession.current !== actionSessionId) return;
      // Reconcile after a possibly replayed receipt so an older snapshot cannot replace the bound result/job.
      await reconcileSession(actionSessionId);
    }
    catch (caught) { setError(message(caught, "Guide progress was not saved; the planning record is unchanged.")); }
    finally { guidanceInFlight.current = false; setGuidanceBusy(""); }
  };

  const calculate = () => session && run("Calculating three plans", async () => {
    const actionSessionId = session.id;
    const next = await planningApi.calculate(actionSessionId, session.revision);
    if (selectedSession.current !== actionSessionId) return;
    setSession((current) => newerSession(current, next));
    await guide("compare");
  });
  const propose = () => session && grow && chosen && run("Preparing reservation review", async () => {
    const actionSessionId = session.id;
    const next = assumptionsFor(session);
    next.reservations = [...next.reservations.filter((row) => row.bed_id !== grow.id),
      { bed_id: grow.id, ...grow.reservation_window }];
    const proposal = await farmerWorkflowApi.createProposal(session, chosen.id, next);
    if (selectedSession.current !== actionSessionId) return;
    setReviewProposal(proposal); setDetail("review"); await refreshWorkflow(); await guide("review");
  });
  const apply = () => reviewProposal && session && run("Applying and recalculating", async () => {
    const actionSessionId = session.id;
    await farmerWorkflowApi.applyProposal(reviewProposal);
    if (selectedSession.current !== actionSessionId) return;
    setReviewProposal(null); setDetail(null); await reconcileSession(actionSessionId); await guide("recalculate");
  });
  const approve = () => applied && session && run("Approving simulation actions", async () => {
    const actionSessionId = session.id;
    await farmerWorkflowApi.approve(applied);
    if (selectedSession.current !== actionSessionId) return;
    await reconcileSession(actionSessionId); await guide("results");
  });
  const prepareInverse = () => { if (original) { setReviewInverse(original); setDetail("inverse"); } };
  const acceptInverse = () => reviewInverse && session && run("Recalculating inverse", async () => {
    const actionSessionId = session.id;
    await farmerWorkflowApi.inverseProposal(reviewInverse);
    if (selectedSession.current !== actionSessionId) return;
    setReviewInverse(null); setDetail(null); await reconcileSession(actionSessionId);
  });

  const primary = () => {
    if (detail || !["mission", "tools"].includes(surface)) return;
    if (surface === "tools") { setToolTarget(undefined); setSurface(toolCards[activeIndex].id); setIndex(0); return; }
    if (busy) return;
    if (["QUEUED", "RUNNING"].includes(session?.job?.status || "")) return;
    const card = missionCards[activeIndex];
    if (card?.id === "reservation" && !taskCount && (activeProposal ? approval?.available === false : grow?.reserve_eligible === false)) return;
    if (card?.id === "approved" || (card?.id === "reservation" && taskCount)) {
      origin.current = { label: primaryLabel, scroll: window.scrollY };
      missionIndex.current = activeIndex; missionScroll.current = window.scrollY; directTool.current = true;
      setToolTarget({ records: { view: "tasks" } }); setSurface("records"); setIndex(0); return;
    }
    if (card?.id === "simulation-result") {
      origin.current = { label: primaryLabel, scroll: window.scrollY };
      missionIndex.current = activeIndex; missionScroll.current = window.scrollY; directTool.current = true;
      setToolTarget({ history: "simulations" }); setSurface("history"); setIndex(0); return;
    }
    if (!strategies.length) void calculate();
    else if (card?.id === "situation") setIndex(Math.max(1, missionCards.findIndex((item) => item.id.startsWith("strategy-"))));
    else if (card?.id.startsWith("strategy-")) { setIndex(missionCards.findIndex((item) => item.id === "reservation")); void guide("tradeoff"); }
    else if (card?.id === "reservation" && !activeProposal && reviewProposal) setDetail("review");
    else if (card?.id === "reservation" && !activeProposal) void propose();
    else if (card?.id === "reservation" && activeProposal) void approve();
    else setSurface("tools");
  };

  const keyboard = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.defaultPrevented || detail || !["mission", "tools"].includes(surface)) return;
    if ((event.target as HTMLElement).closest("button,a,input,select,textarea")) return;
    if (demoStep != null) {
      if (event.key === "ArrowLeft") { event.preventDefault(); changeDemo(demoStep - 1); }
      if (event.key === "ArrowRight") { event.preventDefault(); changeDemo(demoStep + 1); }
      if (event.key === "Enter") { event.preventDefault(); demoStep >= demoSteps.length - 1 ? finishDemo(false) : changeDemo(demoStep + 1); }
      return;
    }
    if (event.key === "ArrowLeft") { event.preventDefault(); move(-1); }
    if (event.key === "ArrowRight") { event.preventDefault(); move(1); }
    if (event.key === "Enter") { event.preventDefault(); primary(); }
  };
  const closeDetail = () => {
    setDetail(null); setReviewProposal(null); setReviewInverse(null);
    afterPaint(() => {
      if (origin.current) {
        window.scrollTo({ top: origin.current.scroll, behavior: "auto" });
        [...document.querySelectorAll<HTMLButtonElement>(".ic-actions button")].find((button) => button.textContent?.trim() === origin.current?.label)?.focus();
      } else cardRef.current?.focus();
    });
  };
  const rememberOrigin = (button: HTMLButtonElement) => { origin.current = { label: button.textContent?.trim() || "", scroll: window.scrollY }; };
  const openContextTool = (tool: ToolId, target: ToolTarget | undefined, button: HTMLButtonElement) => {
    rememberOrigin(button); missionIndex.current = activeIndex; missionScroll.current = window.scrollY;
    directTool.current = true; setToolTarget(target); setSurface(tool); setIndex(0);
  };
  const openIndexedTool = (tool: ToolId, target: ToolTarget | undefined, button: HTMLButtonElement) => {
    rememberOrigin(button); directTool.current = false; setToolTarget(target); setSurface(tool); setIndex(0);
  };
  const closeTool = () => {
    if (directTool.current) {
      directTool.current = false; setToolTarget(undefined); setSurface("mission"); setIndex(missionIndex.current);
      pendingRestore.current = { label: origin.current?.label || "", scroll: origin.current?.scroll ?? missionScroll.current };
      void load(); return;
    }
    const toolIndex = toolCards.findIndex((item) => item.id === surface);
    setToolTarget(undefined); setSurface("tools"); setIndex(Math.max(0, toolIndex));
    pendingRestore.current = { label: origin.current?.label || "", scroll: origin.current?.scroll ?? missionScroll.current };
    void load();
  };
  const openTools = () => { missionIndex.current = activeIndex; missionScroll.current = window.scrollY; missionOrigin.current = { label: "More", scroll: window.scrollY }; setSurface("tools"); setIndex(0); };
  const returnToMission = () => {
    setSurface("mission"); setIndex(missionIndex.current);
    afterPaint(() => {
      window.scrollTo({ top: missionOrigin.current?.scroll ?? missionScroll.current, behavior: "auto" });
      [...document.querySelectorAll<HTMLButtonElement>(".ic-actions button")].find((button) => button.textContent?.trim() === missionOrigin.current?.label)?.focus();
    });
  };
  const pointerUp = (event: PointerEvent<HTMLDivElement>) => {
    if (pointerStart.current == null) return;
    const distance = event.clientX - pointerStart.current; pointerStart.current = null;
    if (Math.abs(distance) > 48) demoStep != null ? changeDemo(demoStep + (distance < 0 ? 1 : -1)) : move(distance < 0 ? 1 : -1);
  };

  if (!session || !bootstrap) return <section className="ic-state" aria-live="polite"><span className="ic-spinner" />
    <h1>{error ? "Sandbox farm unavailable" : "Opening sandbox farm"}</h1><p>{error || busy || "Loading ordinary farm and planning records."}</p>
    {error && <button onClick={() => void load()}>Try again</button>}</section>;

  const current = surface === "tools" ? toolCards[activeIndex] : missionCards[activeIndex];
  const toolOpen = surface !== "mission" && surface !== "tools";
  const hasSimulationBeds = Boolean(session.simulation?.beds?.length);
  const sceneBeds = (hasSimulationBeds ? session.simulation!.beds : session.farm.beds).slice(0, 8);
  const raw = session.farm as typeof session.farm & { batches?: Array<Record<string, unknown>> };
  const batches = new Map((raw.batches || []).map((row) => [String(row.bed_id), row]));
  const recipes = new Map(((raw as typeof raw & { recipes?: Array<Record<string, unknown>> }).recipes || [])
    .map((row) => [String(row.id), String(row.crop_id)]));
  const objectiveOrder = session.farm.orders[0];
  const selectedStrategy = current?.id.startsWith("strategy-") ? strategies.find((row) => `strategy-${row.id}` === current.id) : undefined;
  const jobRunning = ["QUEUED", "RUNNING"].includes(session.job?.status || "");
  const primaryLabel = !strategies.length ? "Calculate three plans" : current?.id === "situation" ? "View calculated plans" : current?.id?.startsWith("strategy-") ? "Try optional B3 constraint" : current?.id === "reservation" ? taskCount ? "Review sandbox work" : activeProposal ? "Approve actions" : "Review reservation" : current?.id === "approved" ? "Open work records" : current?.id === "simulation-result" ? "Open simulation history" : "Open farm tools";
  const reservationDecision = current?.id === "reservation" && !taskCount;
  const reservationEligible = !reservationDecision || (activeProposal ? approval?.available !== false : grow?.reserve_eligible !== false);
  const reservationReason = reservationDecision && activeProposal && approval?.available === false ? approval.reason || "Approval is unavailable."
    : reservationDecision && !activeProposal && grow?.reserve_eligible === false ? grow.reserve_disabled_reason || "Reservation is unavailable." : undefined;
  const demoStepCount = 2 + (chosen && feasible.some((item) => item.id !== chosen.id) ? 1 : 0) + (grow ? 1 : 0)
    + (proposalTransition?.event_id ? 1 : 0) + (approvedTasks.length ? 1 : 0) + (simulationTransition?.event_id ? 1 : 0);
  const cardActions = demoStep != null ? [
    { id: "demo-previous", label: "Previous step", eligible: demoStep > 0, authority: "local_navigation" as const, eligibilitySource: "local" as const },
    { id: "demo-next", label: demoStep >= demoStepCount - 1 ? "Finish demonstration" : "Next step", eligible: true, authority: "local_navigation" as const, eligibilitySource: "local" as const },
    { id: "demo-skip", label: "Skip demonstration", eligible: true, authority: "local_navigation" as const, eligibilitySource: "local" as const },
  ] : detail ? [
    { id: "back", label: "Back", eligible: true, authority: "local_navigation" as const, eligibilitySource: "local" as const },
    { id: detail === "review" ? "apply" : detail === "inverse" ? "confirm-inverse" : "close-detail", label: detail === "review" ? "Apply & recalculate" : detail === "inverse" ? "Confirm inverse" : "Back to card", eligible: !busy && (detail !== "review" || Boolean(reviewProposal)) && (detail !== "inverse" || Boolean(reviewInverse)), authority: detail === "review" || detail === "inverse" ? "server_mutation" as const : "local_navigation" as const, eligibilitySource: "local" as const },
    { id: detail === "explain" && activeProposal?.undo?.available && current?.id === "reservation" ? "review-inverse" : detail === "explain" ? "toggle-guide" : "details", label: detail === "explain" && activeProposal?.undo?.available && current?.id === "reservation" ? "Review inverse" : detail === "explain" ? session.guidance?.skipped ? "Resume guide" : "Skip guide" : "Details", eligible: detail === "explain" && !(activeProposal?.undo?.available && current?.id === "reservation") ? !busy && !jobRunning : true, authority: detail === "explain" && !(activeProposal?.undo?.available && current?.id === "reservation") ? "server_mutation" as const : "local_navigation" as const, eligibilitySource: "local" as const },
  ] : surface === "tools" ? [
    { id: "back", label: "Back", eligible: true, authority: "local_navigation" as const, eligibilitySource: "local" as const },
    { id: "open-tool", label: "Open tool", eligible: true, authority: "local_navigation" as const, eligibilitySource: "local" as const },
    { id: "toggle-guide", label: session.guidance?.skipped ? "Resume guide" : "Skip guide", eligible: !busy && !jobRunning, authority: "server_mutation" as const, eligibilitySource: "local" as const },
  ] : [
    { id: "explain", label: "Explain", eligible: true, authority: "local_navigation" as const, eligibilitySource: "local" as const },
    { id: "primary", label: primaryLabel, eligible: !busy && !jobRunning && reservationEligible, authority: ["Calculate three plans", "Review reservation", "Approve actions"].includes(primaryLabel) ? "server_mutation" as const : "local_navigation" as const, eligibilitySource: reservationDecision ? "server" as const : "local" as const, ...(reservationReason ? { disabledReason: reservationReason } : jobRunning ? { disabledReason: session.job?.stage || "Calculation is in progress." } : busy ? { disabledReason: "Waiting for server confirmation." } : {}) },
    { id: "more", label: "More", eligible: true, authority: "local_navigation" as const, eligibilitySource: "local" as const },
  ];
  const boundCard: FarmCard | null = demoStep != null ? {
    id: `first-use-demo-${demoStep + 1}`, entityId: session.id, entityKind: "demonstration", title: "First-use demonstration", provenance: [],
    binding: { sessionId: session.id, inputHash: snapshotBinding?.input_hash || session.input_hash, revision: snapshotBinding?.revision ?? session.revision, resultId: boundResultId || null },
    boardTargets: [], actions: cardActions, outcomeBasis: null,
  } : current ? surface === "tools" ? {
    id: `tool-${current.id}`, entityId: current.id, entityKind: "tool", title: current.title, provenance: [],
    binding: { sessionId: null, inputHash: null, revision: null, resultId: null },
    boardTargets: [], actions: cardActions, outcomeBasis: null,
  } : surface === "mission" ? {
    id: current.id,
    entityId: current.id === "situation" ? objectiveOrder?.id || session.farm.id
      : current.id === "reservation" ? grow?.id || current.id
        : current.id.startsWith("strategy-") ? current.id.slice("strategy-".length)
          : current.id === "approved" ? session.id
            : current.id === "simulation-result" ? session.simulation?.id || session.id : current.id,
    entityKind: current.id === "situation" ? "order" : current.id.startsWith("strategy-") ? "strategy"
      : current.id === "approved" ? "planning_session" : current.id === "simulation-result" ? "simulation_world" : current.id,
    title: current.title, provenance: current.id === "reservation" && grow?.source ? [grow.source] : current.id === "situation" && session.tactical_context?.scenario.source ? [session.tactical_context.scenario.source] : [],
    binding: { sessionId: session.id, inputHash: snapshotBinding?.input_hash || session.input_hash, revision: snapshotBinding?.revision ?? session.revision,
      resultId: boundResultId || null },
    boardTargets: current.id === "reservation" && grow ? [grow.id] : selectedStrategy ? selectedStrategy.allocations.map((allocation) => allocation.bed_id) : [],
    actions: cardActions,
    outcomeBasis: current.id === "simulation-result" ? "recorded_simulation" : boundResultId ? "projection" : null,
  } : null : null;

  const transitionEntities = new Set(sceneTransition?.entity_ids || []);
  const currentStrategy = selectedStrategy;
  const alternativeStrategy = currentStrategy ? strategies.find((row) => row.id !== currentStrategy.id && row.status === "FEASIBLE" && !row.violations?.length) : undefined;
  const strategyStatus = currentStrategy ? currentStrategy.status === "FEASIBLE" && !currentStrategy.violations?.length
    ? "Feasible in this frozen result."
    : `${currentStrategy.status.replaceAll("_", " ")}; ${(currentStrategy.violations || []).join("; ") || "no violation detail reported"}.` : "";
  const strategyWhy = currentStrategy && alternativeStrategy
    ? `${strategyStatus} ${currentStrategy.name} compared with feasible ${alternativeStrategy.name}: delivery ${signed(difference(currentStrategy.metrics.fill_rate, alternativeStrategy.metrics.fill_rate, 100), "percentage points")}; shortfall ${signed(difference(currentStrategy.metrics.shortfall_kg, alternativeStrategy.metrics.shortfall_kg), "kg")}; cost ${signed(difference(currentStrategy.metrics.cost_sgd, alternativeStrategy.metrics.cost_sgd), "SGD")}.`
    : undefined;
  const reservationExplanation = reservationExplanationProposal?.explanation;
  const reservationTradeoff = typeof reservationExplanation?.tradeoff === "object"
    ? Object.entries(reservationExplanation.tradeoff).map(([key, value]) => `${key.replaceAll("_", " ")}: ${value == null ? "not available" : typeof value === "number" ? signed(value, key.includes("sgd") ? "SGD" : "kg") : typeof value === "string" ? value : "not reported"}`).join("; ")
    : reservationExplanation?.tradeoff;
  const reservationAllocationEvidence = reservationExplanation?.allocation_changes?.slice(0, 3).map((change) => {
    const before = change.before, after = change.after, row = after || before;
    return `${String(row?.bed_id || change.id || "allocation")}: ${before ? `${String(before.crop_id || "crop")} ${String(before.transplant_date || "—")}→${String(before.harvest_date || "—")} ${num(before.expected_kg)} kg` : "none"} → ${after ? `${String(after.crop_id || "crop")} ${String(after.transplant_date || "—")}→${String(after.harvest_date || "—")} ${num(after.expected_kg)} kg` : "none"}`;
  }).join("; ");
  const previewStrategy = surface === "mission" && current?.id.startsWith("strategy-")
    ? strategies.find((item) => `strategy-${item.id}` === current.id) : undefined;
  const previewAllocations = new Map((previewStrategy?.allocations || []).map((row) => [row.bed_id, row]));
  const savedReservation = assumptionsFor(session).reservations.find((row) => row.bed_id === grow?.id);
  const stageExplanation = (() => {
    const projectionLabel = boundResultId ? `Projection · frozen result ${boundResultId}` : `Frozen planning input · no calculated result bound`;
    if (current?.id === "situation") return {
      changed: `No plan change is shown here. This is the frozen ${session.farm.planning_date || session.farm.cutoff} baseline with all ${session.farm.orders.length} order records and ${session.farm.beds.length} grow spaces.`,
      why: objectiveOrder ? `The objective retains ${num(objectiveOrder.quantity_kg)} kg of ${objectiveOrder.crop_id.replaceAll("_", " ")} due ${objectiveOrder.due_date}.` : "No objective order was reported in the frozen farm record.",
      tradeoff: "No choice is selected on this card; the calculated cards compare service, shortfall and cost against this same baseline.",
      evidence: `${projectionLabel}; planning input ${snapshotBinding?.input_hash || session.input_hash || "hash not reported"}. This explanation uses frozen farm facts, not provider interpretation or an unbound user report.`,
      next: strategies.length ? "Compare each calculated choice without saving it." : "Calculate the three local-planner choices.",
    };
    if (currentStrategy) {
      const dated = currentStrategy.allocations.slice(0, 3).map((row) => `${row.bed_id}: ${row.crop_id.replaceAll("_", " ")} ${row.transplant_date} to ${row.harvest_date}, ${num(row.expected_kg)} kg`).join("; ");
      return {
        changed: `${currentStrategy.name} is a preview—not saved. It retains the same frozen demand and shows ${currentStrategy.allocations.length} dated allocations.`,
        why: strategyWhy || `${strategyStatus} No compatible feasible alternative from this frozen result was reported for a signed comparison.`,
        tradeoff: `Delivery ${num(currentStrategy.metrics.fill_rate == null ? null : Number(currentStrategy.metrics.fill_rate) * 100)}%; shortfall ${num(currentStrategy.metrics.shortfall_kg)} kg; cost SGD ${num(currentStrategy.metrics.cost_sgd)}.`,
        evidence: `${projectionLabel}; ${dated || "no dated allocations reported"}. This explanation uses planner output, not provider interpretation or an unbound user report.`,
        next: "Compare the other choices, then review the dated grow-space reservation.",
      };
    }
    if (current?.id === "reservation" && grow) return {
      changed: reservationStateText(boundProposal, grow.id, savedReservation),
      why: reservationExplanation?.why || `The current bound proposal does not report a target-specific reason for changing ${grow.id}; review the saved dates separately from whole-plan effects.`,
      tradeoff: reservationTradeoff || `No target-specific signed delta is reported for ${grow.id}; whole-proposal differences are not attributed to this reservation.`,
      evidence: `${projectionLabel}; ${reservationAllocationEvidence || "no target-specific allocation differences reported"}; target ${grow.id}. This explanation uses frozen reservation facts, not provider interpretation or an unbound user report.`,
      next: reservationExplanation?.next_action || (taskCount ? "Open Records to review previously saved sandbox work, or review the current reservation dates." : activeProposal ? "Review current approval or inverse eligibility." : "Review the exact reservation before applying it."),
    };
    if (current?.id === "approved") {
      const tasks = approvedTasks;
      const taskProposalIds = [...new Set(tasks.map((item) => item.proposal_id))];
      return {
        changed: `${tasks.length} ${boundTasks.length ? "current-result" : "previously saved"} sandbox task${tasks.length === 1 ? " was" : "s were"} created; physical farm operations remain disabled.`,
        why: "The tasks exist because an eligible calculated proposal received explicit sandbox approval.",
        tradeoff: "Approval records simulation work only; it does not report completed farm work or authorize a physical operation.",
        evidence: `Recorded workflow facts · task-owning proposal IDs ${taskProposalIds.join(", ") || "not reported"}; task IDs ${tasks.slice(0, 5).map((item) => item.id).join(", ") || "not reported"}; session revision ${session.revision}. This explanation does not substitute provider interpretation or an unbound user report.`,
        next: "Open Records to inspect, report or correct the saved sandbox tasks.",
      };
    }
    if (current?.id === "simulation-result" && session.simulation) {
      const differences = simulationTransition?.fact_differences
        ? Object.entries(simulationTransition.fact_differences).map(([key, value]) => `${key.replaceAll("_", " ")} ${signed(value, key.includes("sgd") ? "SGD" : "kg")}`).join("; ")
        : "fact differences not reported";
      return {
        changed: `Recorded simulation date ${session.simulation.clock_date || session.simulation.start_date}; ${differences}.`,
        why: "These facts come from saved simulation events after approved sandbox work, separate from the planning projection.",
        tradeoff: `Recorded totals: harvested ${num(session.simulation.totals.harvest_kg)} kg, delivered ${num(session.simulation.totals.delivered_kg)} kg, cash SGD ${num(session.simulation.cash_sgd)}. They are not physical-farm outcomes.`,
        evidence: `Recorded simulation · event ${simulationTransition?.event_id || "not reported"}; affected entities ${(simulationTransition?.entity_ids || []).join(", ") || "not reported"}. This explanation uses the recorded event, not provider interpretation or an unbound user report.`,
        next: "Open History to inspect the saved event and earlier planning result.",
      };
    }
    return { changed: current.summary, why: "No stage-specific reason was reported.", tradeoff: "No stage-specific tradeoff was reported.", evidence: "Evidence was not reported.", next: "Return to the card." };
  })();
  const targetBed = grow ? session.farm.beds.find((bed) => bed.id === grow.id) : undefined;
  const comparisonAlternative = chosen ? feasible.find((item) => item.id !== chosen.id) : undefined;
  const demoSteps = [
    {
      label: "1 · Read the situation", title: "One sample order, all demand retained",
      body: objectiveOrder ? `The example is ${num(objectiveOrder.quantity_kg)} kg of ${objectiveOrder.crop_id.replaceAll("_", " ")} due ${objectiveOrder.due_date}. The planner includes all ${session.farm.orders.length} order lines across ${session.farm.horizon_days} days.` : `No selected order is reported. The planner still includes all ${session.farm.orders.length} order lines.`,
      fact: `Sample farm date ${session.farm.planning_date || session.farm.cutoff} · ${session.farm.beds.length} grow spaces`, basis: "Recorded sample-farm input",
    },
    ...(chosen && comparisonAlternative ? [{
      label: "2 · Compare without saving", title: `${chosen.name} and ${comparisonAlternative.name} use the same farm and dates`,
      body: `Preview—not saved. All-demand coverage differs by ${signed(difference(chosen.metrics.fill_rate, comparisonAlternative.metrics.fill_rate, 100), "percentage points")}; shortfall differs by ${signed(difference(chosen.metrics.shortfall_kg, comparisonAlternative.metrics.shortfall_kg), "kg")}. This does not change the selected strategy.`,
      fact: `Frozen result ${boundResultId || "not reported"}`, basis: "Planner projection",
    }] : []),
    ...(grow ? [{
      label: "3 · Understand the constraint", title: `Optional sample constraint for ${grow.name}`,
      body: `The proposed window is ${grow.reservation_window.start_date} to ${grow.reservation_window.end_date}. The recorded bed crop is ${targetBed?.crop_id?.replaceAll("_", " ") || "not reported"}; recorded harvest date ${targetBed?.harvest_date || "not reported"}; sanitation date is not separately reported. No maintenance reason is invented.`,
      fact: `${grow.id} · ${num(grow.area_m2)} m²`, basis: "Recorded bed facts and server-supplied reservation window",
    }] : []),
    ...(proposalTransition?.event_id ? [{
      label: "4 · Saved after explicit apply", title: "The confirmed recalculation changed the saved projection",
      body: `Event ${proposalTransition.event_id} affected ${(proposalTransition.entity_ids || []).join(", ") || "no listed beds"} on ${proposalTransition.effective_date || "an unreported date"}. Aggregate differences describe the whole recalculated plan, not B3 alone.`,
      fact: Object.entries(proposalTransition.fact_differences || {}).slice(0, 3).map(([key, value]) => `${key.replaceAll("_", " ")} ${signed(value, key.includes("sgd") ? "SGD" : "kg")}`).join(" · ") || "No fact differences reported", basis: "Saved projection event",
    }] : []),
    ...(approvedTasks.length ? [{
      label: "5 · Approval creates tasks", title: `${approvedTasks.length} sandbox tasks are saved`,
      body: "Created tasks are not completed work and do not authorize physical farm activity. Farmer reports and simulated results remain separate records.",
      fact: `Task-owning proposal ${approvedTasks[0]?.proposal_id || "not reported"}`, basis: "Recorded workflow facts",
    }] : []),
    ...(simulationTransition?.event_id ? [{
      label: "6 · Recorded simulation result", title: `Finite saved event on ${simulationTransition.effective_date || session.simulation?.clock_date || "an unreported date"}`,
      body: `Only this saved simulation event supports the displayed consequence. Affected entities: ${(simulationTransition.entity_ids || []).join(", ") || "not reported"}.`,
      fact: Object.entries(simulationTransition.fact_differences || {}).slice(0, 3).map(([key, value]) => `${key.replaceAll("_", " ")} ${signed(value, key.includes("sgd") ? "SGD" : "kg")}`).join(" · ") || "No recorded differences reported", basis: "Recorded simulation",
    }] : []),
    { label: "Next · Choose a useful tool", title: "Continue with the evidence you need", body: "Open crop evidence, compare another scenario, inspect research and data, or replay saved history. Opening a reference does not change the farm or invoke an adviser.", fact: "Five tool categories are available from More", basis: "Read-only navigation" },
  ];
  const activeDemo = demoStep == null ? null : demoSteps[Math.min(demoStep, demoSteps.length - 1)];
  const demoRead = activeDemo?.label.startsWith("1 ·") || false;
  const demoCompare = activeDemo?.label.startsWith("2 ·") || false;
  const demoConstraint = activeDemo?.label.startsWith("3 ·") || false;
  const demoSavedProjection = activeDemo?.label.startsWith("4 ·") || false;
  const demoRecordedEvent = activeDemo?.label.startsWith("6 ·") || false;
  const renderedPreviewAllocations = demoCompare && chosen ? new Map(chosen.allocations.map((row) => [row.bed_id, row])) : previewAllocations;
  const saveDemo = (value: { step?: number; done?: boolean; skipped?: boolean }) => {
    try { localStorage.setItem(editionStorageKey(`first-use-demo:${session.id}`), JSON.stringify(value)); } catch { /* optional */ }
  };
  const changeDemo = (next: number) => { const step = Math.max(0, Math.min(demoSteps.length - 1, next)); setDemoStep(step); saveDemo({ step }); };
  const finishDemo = (skipped = false) => { setDemoStep(null); saveDemo(skipped ? { skipped: true } : { done: true }); afterPaint(() => cardRef.current?.focus()); };
  const guideTips: Record<NonNullable<PlanningSession["guidance"]>["step"], string> = {
    inspect: "Inspect the confirmed order, available space and planning date before calculating.",
    compare: "Swipe through all three previews. Selection alone does not save a plan.",
    tradeoff: "Compare delivery and shortfall with the space and cost each option uses.",
    review: "Review the exact grow-space identity and dates; only Apply changes the plan.",
    recalculate: "Wait for the server result, then read its signed changes against the saved baseline.",
    approve: "Approval creates sandbox-only tasks and never authorizes physical farm work.",
    results: "Recorded simulation outcomes and projections stay separately labelled in history.",
  };
  return <section className={`ic-shell ${reducedMotion ? "is-reduced-motion" : ""}`} data-edition={editionId} onKeyDown={keyboard} tabIndex={-1}>
    <header className={`ic-heading ${demoRead ? "is-demo-focus" : ""}`}><div><span>Objective · selected sample order</span><strong>{objectiveOrder ? `${num(objectiveOrder.quantity_kg)} kg ${objectiveOrder.crop_id.replaceAll("_", " ")} by ${objectiveOrder.due_date}` : session.farm.name}</strong><small>All {session.farm.orders.length} order lines remain in the {session.farm.horizon_days}-day plan.</small></div>
      <p>Sandbox farm · real operations disabled</p></header>
    <div className="ic-layout">
      <section className={`ic-scene ${transitionLabel ? "is-transitioning" : ""} ${demoConstraint ? "is-demo-constraint" : ""} ${(demoSavedProjection || demoRecordedEvent) ? "is-demo-event" : ""}`} aria-label="Passive farm scene">
        <div className="ic-scene-head"><span>{hasSimulationBeds ? "Saved simulation scene" : "Sample farm records"} · Area 1 of {Math.ceil((hasSimulationBeds ? session.simulation!.beds.length : session.farm.beds.length) / 8)} · showing {sceneBeds.length} of {hasSimulationBeds ? session.simulation!.beds.length : session.farm.beds.length}</span><strong>{session.simulation?.clock_date || session.farm.planning_date || session.farm.cutoff}</strong></div>
        <div className="ic-beds">{sceneBeds.map((bed) => {
          const batch = batches.get(bed.id), crop = String(hasSimulationBeds ? bed.crop_id || "" : batch?.crop_id || recipes.get(String(batch?.recipe_id)) || bed.crop_id || "");
          const stage = String(hasSimulationBeds ? bed.stage : batch?.stage || bed.stage || (crop ? "recorded batch" : "empty"));
          const assetStage = stage === "ready" ? "ready" : stage === "nursery" ? "seedling" : stage === "growing" ? "growing" : "";
          const src = crop && assetStage ? `/art/crops/${crop}-${assetStage}.svg` : "";
          const focused = grow?.id === bed.id && (current?.id === "reservation" || demoConstraint);
          const demoEntities = demoRecordedEvent ? simulationTransition?.entity_ids : demoSavedProjection ? proposalTransition?.entity_ids : [];
          const changing = Boolean((transitionLabel && transitionEntities.has(bed.id)) || ((demoSavedProjection || demoRecordedEvent) && demoEntities?.includes(bed.id)));
          const preview = renderedPreviewAllocations.get(bed.id);
          return <article key={bed.id} className={`${focused ? "is-focus" : ""} ${changing ? "is-changing" : ""}`}><b>{bed.name}</b>
            {src ? <img src={src} alt="" onError={(event) => { event.currentTarget.hidden = true; }} /> : <span className="ic-empty">{stage === "harvested" ? "Harvested residue" : stage === "sanitation" ? "Sanitation" : stage === "empty" ? "Empty" : stage.replaceAll("_", " ")}</span>}
            <small>{crop ? crop.replaceAll("_", " ") : "Available"}</small><em>{stage}</em>
            {preview && <span className="ic-allocation-preview">{demoCompare ? "Demonstration preview—not saved" : "Preview—not saved"}<br/>{preview.crop_id.replaceAll("_", " ")}<br/>{preview.transplant_date} → {preview.harvest_date}</span>}
            {savedReservation && activeProposal && bed.id === grow?.id && <span className="ic-reservation-barrier">Saved reservation<br/>{savedReservation.start_date} → {savedReservation.end_date}</span>}
          </article>;
        })}</div>
        <p className="ic-scene-note">Showing {sceneBeds.length} of {hasSimulationBeds ? session.simulation!.beds.length : session.farm.beds.length} grow spaces. Scene reflects saved records; listed affected IDs may include spaces outside this area. Selecting cards only changes the highlighted preview.</p>
        {transitionLabel && <p className="ic-transition" role="status">{transitionLabel}</p>}
        {sceneTransition?.event_id && <p className="ic-saved-change">{sceneTransition.outcome_basis === "recorded_simulation" ? "Recorded simulation" : "Saved projection"} · {sceneTransition.effective_date} · {(sceneTransition.entity_ids || []).join(", ") || "planning result"}{sceneTransition.fact_differences && ` · ${Object.entries(sceneTransition.fact_differences).slice(0, 3).map(([key, value]) => `${key.replaceAll("_", " ")} ${typeof value === "number" ? signed(value, key.includes("sgd") ? "SGD" : "kg") : String(value)}`).join(" · ")}`}</p>}
      </section>

      <div className="ic-card-column">
        {error && <div className="ic-error" role="alert"><span>{error}</span><button onClick={() => setError("")}>Dismiss</button></div>}
        {toolOpen ? <section className="ic-tool"><p className="ic-tool-parent">Farm tools › {toolCards.find((item) => item.id === surface)?.title}</p>
          <div className="ic-tool-body">{renderTool ? renderTool(surface, closeTool, toolTarget) : <><span className="ic-eyebrow">Tool adapter</span>
            <h2>{toolCards.find((item) => item.id === surface)?.title}</h2><p>This tool is unavailable in this build.</p></>}</div></section> : <>
          <div className="ic-deck" onPointerDown={(event) => { pointerStart.current = event.clientX; }} onPointerUp={pointerUp}>
            {boundCard && <BoundCard card={boundCard} ref={cardRef} tabIndex={-1} className="ic-card" aria-live="polite" aria-label={`${surface === "tools" ? "Farm tools" : "Planning"} card ${activeIndex + 1} of ${surface === "tools" ? toolCards.length : missionCards.length}`}>
              {activeDemo ? <section className="ic-demo" key={activeDemo.label}><span className="ic-eyebrow">First-use demonstration · {demoStep! + 1} of {demoSteps.length}</span><h1>{activeDemo.title}</h1><strong>{activeDemo.label}</strong><p>{activeDemo.body}</p>{demoConstraint && grow && <ol className="ic-demo-timeline" aria-label="B3 dated lifecycle"><li><b>Recorded crop</b><span>{targetBed?.crop_id?.replaceAll("_", " ") || "Not reported"}</span></li><li><b>Recorded harvest</b><span>{targetBed?.harvest_date || "Not reported"}</span></li><li><b>Sanitation</b><span>Not separately reported</span></li><li><b>Proposed reservation</b><span>{grow.reservation_window.start_date} → {grow.reservation_window.end_date}</span></li></ol>}<dl><div><dt>Authoritative fact</dt><dd>{activeDemo.fact}</dd></div><div><dt>Basis</dt><dd>{activeDemo.basis}</dd></div><div><dt>Motion</dt><dd>{reducedMotion ? "Reduced · final facts shown immediately" : "Finite highlights on authoritative entities"}</dd></div></dl></section>
                : detail === "explain" ? <><span className="ic-eyebrow">{current.title} › Why</span><h1>What this means</h1><p>{current.summary}</p>
                <dl className="ic-explanation"><div><dt>What changed</dt><dd>{stageExplanation.changed}</dd></div>
                  <div><dt>Why</dt><dd>{stageExplanation.why}</dd></div>
                  <div><dt>Tradeoff</dt><dd>{stageExplanation.tradeoff}</dd></div>
                  <div><dt>Evidence / limits</dt><dd>{stageExplanation.evidence}</dd></div>
                  <div><dt>Next action</dt><dd>{stageExplanation.next}</dd></div>
                  <div><dt>Record identity</dt><dd>{boundCard ? `${boundCard.entityKind} · ${boundCard.entityId}` : current.id}</dd></div></dl></>
                : detail === "review" || detail === "inverse" ? <><span className="ic-eyebrow">Review before applying</span><h1>{detail === "inverse" ? "Restore the grow space" : `Reserve ${grow?.name || "grow space"}`}</h1>
                  <p>{detail === "inverse" ? "The inverse preserves the original event and recalculates future work at the current eligible revision." : `${grow?.id} will be unavailable ${grow?.reservation_window.start_date} to ${grow?.reservation_window.end_date}. Existing work remains recorded.`}</p>
                  <dl><div><dt>Proposal</dt><dd>{String((reviewInverse || reviewProposal)?.id)}</dd></div><div><dt>Revision</dt><dd>{(reviewInverse || reviewProposal)?.proposal_revision}</dd></div><div><dt>Scope</dt><dd>Future simulation work only</dd></div></dl></>
                : <><span className="ic-eyebrow">{"eyebrow" in current ? current.eyebrow : "Farm tools"}</span>
                  <h1>{surface === "tools" ? "Choose a tool" : current.title}</h1><p>{surface === "tools" ? "Open one category or use Next and Previous to inspect its summary." : current.summary}</p>
                  {current.id.startsWith("strategy-") && <span className="ic-preview">Preview—not saved</span>}
                  {surface === "mission" && !session.guidance?.skipped && session.guidance?.step !== "results" && <p className="ic-guide-tip"><b>Guide · {(session.guidance?.step || "inspect").replaceAll("_", " ")}</b> {guideTips[session.guidance?.step || "inspect"]}</p>}
                  {"facts" in current && current.facts && <dl>{current.facts.slice(0, 4).map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>}
                  {surface === "mission" && <div className="ic-context-links" aria-label="Relevant tools">
                    {current.id === "situation" && objectiveOrder && <><button onClick={(event) => openContextTool("records", { records: { view: "orders", entityId: objectiveOrder.id } }, event.currentTarget)}>Inspect selected order</button><button onClick={(event) => openContextTool("knowledge", { knowledge: { kind: "crop", id: objectiveOrder.crop_id } }, event.currentTarget)}>Crop evidence</button></>}
                    {current.id.startsWith("strategy-") && <><button onClick={(event) => openContextTool("plan", { plan: "strategies" }, event.currentTarget)}>Dated schedule</button><button onClick={(event) => openContextTool("knowledge", { knowledge: { kind: "council" } }, event.currentTarget)}>Planning Council</button><button onClick={(event) => openContextTool("experiments", { experiments: "research", research: "overview" }, event.currentTarget)}>Research overview</button></>}
                    {current.id === "simulation-result" && <button onClick={(event) => openContextTool("history", { history: "simulations" }, event.currentTarget)}>View simulation results</button>}
                  </div>}
                  {surface === "tools" && <div className="ic-tool-index" aria-label="Farm tool categories">{toolCards.map((tool) => <button key={tool.id} onClick={(event) => openIndexedTool(tool.id, undefined, event.currentTarget)}><b>{tool.title}</b><span>{tool.summary}</span></button>)}<button onClick={() => { setDemoStep(0); saveDemo({ step: 0 }); }}><b>Replay demonstration</b><span>Review the factual decision sequence without saving or inference.</span></button></div>}
                  {reservationReason && surface === "mission" && <p role="status">{reservationReason}</p>}
                  {surface === "tools" && <span className="ic-path">Farm tools › {current.title}</span>}</>}
            </BoundCard>}
          </div>
          <nav className="ic-actions" aria-label="Card actions">
            {!activeDemo && <div className="ic-deck-nav"><button onClick={() => move(-1)} disabled={activeIndex === 0}>← Previous</button>
              <span>{surface === "tools" ? "Farm tools" : "Farm plan"} · {activeIndex + 1} of {surface === "tools" ? toolCards.length : missionCards.length}</span>
              <button onClick={() => move(1)} disabled={activeIndex === (surface === "tools" ? toolCards.length : missionCards.length) - 1}>Next →</button></div>}
            <div className="ic-keys">
              {activeDemo ? <><button disabled={demoStep === 0} onClick={() => changeDemo((demoStep || 0) - 1)}>Previous step</button><button className="is-primary" onClick={() => demoStep! >= demoSteps.length - 1 ? finishDemo(false) : changeDemo(demoStep! + 1)}>{demoStep! >= demoSteps.length - 1 ? "Finish demonstration" : "Next step"}</button><button onClick={() => finishDemo(true)}>Skip demonstration</button></>
                : detail ? <><button onClick={closeDetail}>Back</button><button className="is-primary" disabled={Boolean(busy || (detail === "review" && !reviewProposal) || (detail === "inverse" && !reviewInverse))} onClick={() => void (detail === "review" ? apply() : detail === "inverse" ? acceptInverse() : closeDetail())}>{busy || (detail === "review" ? "Apply & recalculate" : detail === "inverse" ? "Confirm inverse" : "Back to card")}</button>{detail === "explain" && activeProposal?.undo?.available && current?.id === "reservation" ? <button onClick={prepareInverse}>Review inverse</button> : detail === "explain" ? <button disabled={Boolean(busy || jobRunning)} onClick={() => void guide(session.guidance?.step || "inspect", !session.guidance?.skipped)}>{session.guidance?.skipped ? "Resume guide" : "Skip guide"}</button> : <button onClick={() => setDetail("explain")}>Details</button>}</>
                : surface === "tools" ? <><button onClick={returnToMission}>Back</button><button className="is-primary" onClick={(event) => { rememberOrigin(event.currentTarget); primary(); }}>Open tool</button><button disabled={Boolean(busy || jobRunning)} onClick={() => void guide(session.guidance?.step || "inspect", !session.guidance?.skipped)}>{session.guidance?.skipped ? "Resume guide" : "Skip guide"}</button></>
                : <><button onClick={(event) => { rememberOrigin(event.currentTarget); setDetail("explain"); }}>Explain</button>
                  <button className="is-primary" title={reservationReason} disabled={Boolean(!reservationEligible || busy || (surface === "mission" && ["QUEUED", "RUNNING"].includes(session.job?.status || "")) || (current?.id === "reservation" && activeProposal && !taskCount && approval?.available === false))} onClick={(event) => { rememberOrigin(event.currentTarget); primary(); }}>{busy || (surface === "mission" && ["QUEUED", "RUNNING"].includes(session.job?.status || "") ? progressLabel(session.job?.stage) : primaryLabel)}</button>
                  <button onClick={(event) => { rememberOrigin(event.currentTarget); openTools(); }}>More</button></>}
            </div>
          </nav>
        </>}
      </div>
    </div>
  </section>;
}
