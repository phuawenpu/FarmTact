import { AlertTriangle, Check, LoaderCircle, ShieldCheck, Sprout } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "../lib/api";
import { ADVISORS, type Conversation } from "../lib/game";
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
import type { Crop, Strategy } from "../lib/types";
import {
  TacticalConsole,
  type TacticalBoardContext,
  type TacticalCard,
  type TacticalCardAction,
  type TacticalMetricDelta,
} from "./TacticalConsole";
import "./tactical-mission.css";

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

function errorMessage(value: unknown, fallback: string) {
  return value instanceof Error ? value.message : fallback;
}

function number(value: unknown, digits = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed)
    ? new Intl.NumberFormat(undefined, { maximumFractionDigits: digits }).format(parsed)
    : "—";
}

function signed(value: number | null | undefined, unit = "") {
  if (value == null || !Number.isFinite(value)) return undefined;
  const prefix = value > 0 ? "+" : value < 0 ? "−" : "±";
  return `${prefix}${number(Math.abs(value), 1)}${unit}`;
}

function includesBedReservation(proposal: FarmerProposal) {
  const changes = Array.isArray(proposal.changes) ? proposal.changes : [];
  return changes.some((change) => {
    const assumptions = (change as { assumptions?: { reservations?: Array<{ bed_id?: string }> } }).assumptions;
    return assumptions?.reservations?.some((item) => item.bed_id === "bed-07");
  });
}

function proposalMetrics(proposal?: FarmerProposal): TacticalMetricDelta[] {
  if (!proposal?.recalculated_metrics) return [];
  const labels: Record<string, [string, string]> = {
    coverage_kg: ["Production coverage", " kg"],
    surplus_kg: ["Closing surplus", " kg"],
    expiry_kg: ["Expiry exposure", " kg"],
    rejection_kg: ["Rejection exposure", " kg"],
    margin_sgd: ["Planner margin", " SGD"],
  };
  return Object.entries(labels).map(([id, [label, unit]]) => ({
    id,
    label,
    value: proposal.recalculated_metrics?.[id] == null
      ? "Not calculated"
      : `${number(proposal.recalculated_metrics[id], 1)}${unit}`,
    delta: signed(proposal.metric_deltas?.[id], unit),
    direction: "neutral",
  }));
}

function normalizedAssumptions(session: PlanningSession): FarmerAssumptions {
  const current = (session.assumptions || {}) as Partial<FarmerAssumptions>;
  return {
    tentative_orders: current.tentative_orders || [],
    future_demand: current.future_demand || [],
    seasonal: current.seasonal || [],
    order_changes: current.order_changes || [],
    reservations: current.reservations || [],
    ...(current.capacity ? { capacity: current.capacity } : {}),
  };
}

function focusKind(card: TacticalCard) {
  const map: Record<string, string> = {
    scenario: "scenario",
    grow_space: "grow_space",
    proposal: "grow_space",
    strategy: "strategy",
    order: "order",
    crop_batch: "batch",
    task: "task",
    council_role: "agent",
    evidence: "evidence",
    forecast: "evidence",
    planning_constraint: "grow_space",
  };
  return map[card.entity.kind] || card.entity.kind;
}

export function TacticalMission({
  crops,
  onNavigate,
  onOpenTool,
}: {
  crops: Crop[];
  onNavigate: (destination: "mission" | "records" | "crops" | "more") => void;
  onOpenTool: (destination: "data" | "council" | "outcomes" | "board" | "setup") => void;
}) {
  const [session, setSession] = useState<PlanningSession | null>(null);
  const [workflow, setWorkflow] = useState<FarmerWorkflowState>(emptyWorkflow);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [selectedCardId, setSelectedCardId] = useState<string>();
  const [detailCard, setDetailCard] = useState<TacticalCard | null>(null);
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const strategyTrayRef = useRef<HTMLDivElement>(null);
  const mutationLockRef = useRef<string | null>(null);

  const refreshWorkflow = useCallback(async () => {
    const next = await farmerWorkflowApi.state();
    setWorkflow({ ...emptyWorkflow, ...next });
    return next;
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
      if (!current) {
        const page = await planningApi.list();
        current = page.sessions.find((item) => item.workflow === true);
      }
      if (!current?.workflow) current = await planningApi.create("V13 tactical mission", true);
      rememberPlanningSession(current.id);
      setSession(current);
      await refreshWorkflow();
    } catch (caught) {
      setError(errorMessage(caught, "The tactical mission could not be opened."));
    } finally {
      setLoading(false);
    }
  }, [refreshWorkflow]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    if (!session?.job || !["QUEUED", "RUNNING"].includes(session.job.status)) return;
    const timer = window.setInterval(() => {
      void planningApi.get(session.id).then(async (next) => {
        setSession(next);
        if (!["QUEUED", "RUNNING"].includes(next.job?.status || "")) {
          setBusy("");
          await refreshWorkflow();
        }
      }).catch(() => {});
    }, 1400);
    return () => window.clearInterval(timer);
  }, [session?.id, session?.job?.id, session?.job?.status, refreshWorkflow]);
  useEffect(() => {
    if (!conversation?.id || !["QUEUED", "RUNNING"].includes(conversation.last_request_status || "")) return;
    const timer = window.setInterval(() => {
      void api.conversation(conversation.id).then((next) => {
        setConversation(next);
        if (!["QUEUED", "RUNNING"].includes(next.last_request_status || "")) window.clearInterval(timer);
      }).catch(() => window.clearInterval(timer));
    }, 1500);
    return () => window.clearInterval(timer);
  }, [conversation?.id, conversation?.last_request_status]);

  const sessionProposals = workflow.proposals.filter((item) => item.session_id === session?.id);
  const originalReservation = [...sessionProposals].reverse().find(
    (item) => !item.inverse_of_proposal_id && includesBedReservation(item),
  );
  const inverse = originalReservation
    ? sessionProposals.find((item) => item.inverse_of_proposal_id === originalReservation.id)
    : undefined;
  const inverseComplete = Boolean(
    inverse?.recalculation_job?.id && session?.status === "COMPLETED" &&
    session.result && inverse.recalculation_job.id === (session as { result_id?: string }).result_id,
  );
  const constraintActive = Boolean(originalReservation && !inverseComplete);
  const strategies = session?.result?.strategies || [];
  const selectedStrategy = strategies.find(
    (item) => item.id === session?.selected_strategy_id && item.status === "FEASIBLE" && !item.violations?.length,
  ) || strategies.find((item) => item.status === "FEASIBLE" && !item.violations?.length);
  const tactical = session?.tactical_context;
  const growSpace = tactical?.grow_space;
  const planningSnapshot = tactical?.planning_snapshot;
  const askEligible = Boolean(tactical?.scenario.ask_eligible);
  const jobActive = Boolean(session?.job && ["QUEUED", "RUNNING"].includes(session.job.status));

  const cards = useMemo<TacticalCard[]>(() => {
    if (!session || !tactical || !planningSnapshot) return [];
    const binding = {
      snapshotId: planningSnapshot.result_id
        ? `${planningSnapshot.session_id}:${planningSnapshot.result_id}`
        : planningSnapshot.session_id,
      snapshotHash: planningSnapshot.input_hash,
      sessionId: session.id,
      revision: session.revision,
      resultId: planningSnapshot.result_id || undefined,
    };
    const commonAsk = {
      id: "ask", kind: "ask" as const, label: "Ask", emphasis: "secondary" as const,
      disabled: !askEligible, disabledReason: tactical.scenario.ask_disabled_reason || undefined,
    };
    const details = { id: "details", kind: "details" as const, label: "Details", emphasis: "secondary" as const };
    const result: TacticalCard[] = [{
      id: "scenario-heavy-rainfall", type: "evidence", eyebrow: "Seasonal planning signal",
      title: tactical.scenario.title,
      summary: "Review a frozen synthetic rainfall scenario against the current planning result.",
      detail: "This is a scenario input, not an observed forecast and not evidence of actual weather.",
      entity: { kind: "scenario", id: tactical.scenario.id, title: tactical.scenario.title },
      state: "ready", stateLabel: "Review",
      provenance: { sourceTitle: tactical.scenario.source, sourceKind: "synthetic",
        executionMode: tactical.scenario.execution_mode, scenarioOnly: true },
      boardTargets: [], planning: binding,
      facts: [{ id: "mode", label: "Evidence class", value: tactical.scenario.label },
        { id: "provider", label: "Provider activity", value: "None on open" }],
      actions: [{ id: "impact", kind: "review_impact", label: "Review impact", emphasis: "primary" }, commonAsk, details],
      suggestedQuestions: ["How could this scenario affect the current plan?", "Which assumptions remain synthetic?"],
    }];
    if (growSpace) {
      const pendingInverse = Boolean(inverse && !inverseComplete);
      const state = jobActive || pendingInverse ? "pending" : constraintActive ? "applied" : "ready";
      const undo = originalReservation?.undo;
      result.push({
        id: "constraint-bed-07", type: constraintActive ? "applied_constraint" : "constraint",
        eyebrow: constraintActive ? "Current revision-bound proposal" : "Capacity constraint",
        title: constraintActive ? "Grow space B3 reserved" : growSpace.title,
        summary: constraintActive
          ? "The reservation is bound to the stored proposal and recalculated planning result."
          : "Keep bed-07 free after its recorded crop clears, through the remaining planning horizon.",
        detail: `${growSpace.area_m2} m² · ${growSpace.system.replaceAll("_", " ")} · ${growSpace.reservation_window.start_date} to ${growSpace.reservation_window.end_date}`,
        entity: { kind: constraintActive ? "proposal" : "grow_space", id: growSpace.id, title: growSpace.title },
        state, stateLabel: state === "pending" ? "Recalculating" : constraintActive ? "Applied" : "Ready",
        provenance: { sourceTitle: growSpace.source, sourceKind: "farm_record", executionMode: "local_planner" },
        boardTargets: [growSpace.id],
        planning: { ...binding, proposal: originalReservation ? {
          id: originalReservation.id, base_revision: originalReservation.base_revision,
          proposal_revision: originalReservation.proposal_revision, status: originalReservation.status,
        } : undefined },
        facts: [{ id: "mapping", label: "Farm entity", value: `${growSpace.name} = ${growSpace.id}` },
          { id: "window", label: "Reservation window", value: `${growSpace.reservation_window.start_date} → ${growSpace.reservation_window.end_date}` }],
        metrics: constraintActive ? proposalMetrics(originalReservation) : [],
        actions: constraintActive ? [
          { id: "undo", kind: "undo", label: "Undo", emphasis: "danger", disabled: !undo?.available,
            disabledReason: undo?.reason || undefined },
          { id: "plan", kind: "view_plan", label: "View new plan", emphasis: "primary" },
          { id: "why", kind: "ask_why", label: "Ask why", emphasis: "secondary", disabled: !askEligible,
            disabledReason: tactical.scenario.ask_disabled_reason || undefined },
        ] : [
          { id: "reserve", kind: "reserve_space", label: "Reserve space", emphasis: "primary",
            disabled: !growSpace.reserve_eligible, disabledReason: growSpace.reserve_disabled_reason || undefined },
          { ...commonAsk, id: "ask-space" }, details,
        ],
        suggestedQuestions: ["Why did reserving B3 change this plan?", "Which constraint became binding?"],
      });
    }
    strategies.forEach((strategy) => {
      const eligibleProposal = sessionProposals.find((item) => item.status === "applied" &&
        item.recalculation_job?.id === (session as { result_id?: string }).result_id);
      const approvalDisabledReason = strategy.status !== "FEASIBLE"
        ? "The local planner marked this option infeasible under the current constraints."
        : strategy.id !== session.selected_strategy_id
          ? "Only the currently selected feasible option can be approved."
          : undefined;
      result.push({
        id: `strategy-${strategy.id}`, type: "strategy", eyebrow: "Calculated option", title: `${strategy.name} strategy`,
        summary: strategy.description, entity: { kind: "strategy", id: strategy.id, title: strategy.name },
        state: strategy.id === selectedStrategy?.id ? "selected" : "ready",
        stateLabel: strategy.status, provenance: { sourceTitle: "Stored local planner result", sourceKind: "synthetic", executionMode: "local_cpsat" },
        boardTargets: [...new Set(strategy.allocations.map((item) => item.bed_id))], planning: binding,
        facts: [{ id: "fill", label: "Fill rate", value: `${number(Number(strategy.metrics.fill_rate) * 100, 1)}%` },
          { id: "margin", label: "Margin", value: `SGD ${number(strategy.metrics.margin_sgd, 0)}` }],
        strategy, actions: [
          { id: "preview", kind: "preview", label: "Preview plan", emphasis: "primary" },
          eligibleProposal
            ? { id: "approve", kind: "approve", label: "Approve", emphasis: "secondary",
                disabled: Boolean(approvalDisabledReason), disabledReason: approvalDisabledReason }
            : { id: "compare", kind: "compare", label: "Compare", emphasis: "secondary" },
          details,
        ], suggestedQuestions: ["What is the strongest evidence for this strategy?"],
      });
    });
    const rawFarm = session.farm as typeof session.farm & { batches?: Array<Record<string, unknown>> };
    const batch = rawFarm.batches?.[0];
    if (batch) result.push({
      id: `crop-batch-${String(batch.id)}`, type: "crop", eyebrow: "Current crop batch",
      title: `Inspect ${String(batch.id)}`, summary: "Dates and expected quantity come from the frozen farm record.",
      entity: { kind: "crop_batch", id: String(batch.id) }, state: "ready", stateLabel: "Recorded",
      provenance: { sourceTitle: "Frozen farm snapshot", sourceKind: "farm_record", executionMode: "recorded" },
      boardTargets: [String(batch.bed_id)], planning: binding,
      facts: [{ id: "harvest", label: "Harvest date", value: String(batch.harvest_date || "—") },
        { id: "yield", label: "Expected", value: `${String(batch.expected_marketable_kg || "—")} kg` }],
      actions: [{ id: "inspect", kind: "inspect", label: "Inspect batch", emphasis: "primary" },
        { id: "compare", kind: "compare", label: "Compare" }, details],
    });
    const order = session.farm.orders[0];
    if (order) result.push({
      id: `order-${order.id}`, type: "order", eyebrow: "Confirmed commitment", title: `Order ${order.id}`,
      summary: "A tenant-owned booked order; tentative demand is not included here.",
      entity: { kind: "order", id: order.id }, state: "ready", stateLabel: "Confirmed",
      provenance: { sourceTitle: "Frozen farm order", sourceKind: "farm_record", executionMode: "recorded" },
      boardTargets: [], planning: binding,
      facts: [{ id: "quantity", label: "Quantity", value: `${number(order.quantity_kg, 1)} kg` },
        { id: "due", label: "Due", value: order.due_date }],
      actions: [{ id: "inspect", kind: "inspect", label: "Inspect commitment", emphasis: "primary" }, commonAsk, details],
      suggestedQuestions: ["How does the current plan cover this confirmed order?"],
    });
    const task = workflow.tasks.find((item) => sessionProposals.some((proposal) => proposal.id === item.proposal_id));
    const planner = ADVISORS.find((advisor) => advisor.id === "asha");
    if (planner) result.push({
      id: `agent-${planner.id}`, type: "agent", eyebrow: "Council role", title: `${planner.name} · ${planner.role}`,
      summary: planner.focus, detail: `${planner.location} · ${planner.prompt}`,
      entity: { kind: "council_role", id: planner.id, title: `${planner.name} · ${planner.role}` },
      state: "ready", stateLabel: "Advisory",
      provenance: { sourceTitle: "FarmTact council roster", sourceKind: "advisory_role", executionMode: "explicit_ask_only" },
      boardTargets: [], planning: binding,
      facts: [{ id: "boundary", label: "Decision influence", value: "Advisory only" },
        { id: "trigger", label: "Provider trigger", value: "Explicit submitted question" }],
      actions: [{ id: "ask-specialist", kind: "ask", label: "Ask specialist", emphasis: "primary",
        disabled: !askEligible, disabledReason: tactical.scenario.ask_disabled_reason || undefined },
        { id: "evidence", kind: "details", label: "Evidence" },
        { id: "role", kind: "details", label: "Role details" }],
      suggestedQuestions: ["Which option is feasible under the current constraints?", "What evidence limits this recommendation?"],
    });
    if (task) result.push({
      id: `action-${task.id}`, type: "action", eyebrow: "Sandbox farm task", title: `${task.action.replaceAll("_", " ")} · ${task.crop_id || "farm"}`,
      summary: "The task is revision-bound; results append events and never authorize a physical operation.",
      entity: { kind: "task", id: task.id }, state: task.status === "completed" ? "completed" : "ready", stateLabel: task.status,
      provenance: { sourceTitle: "Approved sandbox action", sourceKind: "farm_record", executionMode: "simulation_only" },
      boardTargets: task.location?.startsWith("bed-") ? [task.location] : [], planning: { ...binding,
        task: { id: task.id, event_revision: task.event_revision, status: task.status } },
      actions: [{ id: "record", kind: "record_result", label: "Record result", emphasis: "primary", disabled: true,
        disabledReason: "Open the Records workflow to review the full checklist." }, details],
    });
    return result;
  }, [session, tactical, planningSnapshot, askEligible, constraintActive, originalReservation, inverse,
      inverseComplete, jobActive, strategies, selectedStrategy, sessionProposals, workflow.tasks]);

  const reserve = async () => {
    if (!session || !growSpace || !selectedStrategy || mutationLockRef.current) return;
    mutationLockRef.current = "reserve";
    setBusy("Submitting B3 reservation"); setError("");
    try {
      const assumptions = normalizedAssumptions(session);
      assumptions.reservations = [
        ...assumptions.reservations.filter((item) => item.bed_id !== growSpace.id),
        { bed_id: growSpace.id, ...growSpace.reservation_window },
      ];
      const draft = await farmerWorkflowApi.createProposal(session, selectedStrategy.id, assumptions);
      await farmerWorkflowApi.applyProposal(draft);
      setSession(await planningApi.get(session.id));
      await refreshWorkflow();
    } catch (caught) { setBusy(""); setError(errorMessage(caught, "Could not reserve grow space B3.")); }
    finally { mutationLockRef.current = null; }
  };

  const undo = async () => {
    if (!session || !originalReservation || mutationLockRef.current) return;
    mutationLockRef.current = "undo";
    setBusy("Submitting inverse proposal"); setError("");
    try {
      await farmerWorkflowApi.inverseProposal(originalReservation);
      setSession(await planningApi.get(session.id));
      await refreshWorkflow();
    } catch (caught) { setBusy(""); setError(errorMessage(caught, "Could not submit the inverse proposal.")); }
    finally { mutationLockRef.current = null; }
  };

  const calculateBaseline = async () => {
    if (!session || mutationLockRef.current) return;
    mutationLockRef.current = "baseline";
    setBusy("Calculating baseline"); setError("");
    try { setSession(await planningApi.calculate(session.id, session.revision)); }
    catch (caught) { setBusy(""); setError(errorMessage(caught, "Could not calculate the baseline.")); }
    finally { mutationLockRef.current = null; }
  };

  const approve = async () => {
    const proposal = sessionProposals.find((item) => item.status === "applied" &&
      item.recalculation_job?.id === (session as { result_id?: string } | null)?.result_id);
    if (!session || !proposal) return;
    setBusy("Approving sandbox actions");
    try {
      await farmerWorkflowApi.approve(proposal);
      await refreshWorkflow(); setSession(await planningApi.get(session.id)); setBusy("");
    } catch (caught) { setBusy(""); setError(errorMessage(caught, "Could not approve this strategy.")); }
  };

  const action = async (card: TacticalCard, item: TacticalCardAction) => {
    if (item.kind === "reserve_space") return reserve();
    if (item.kind === "undo") return undo();
    if (item.kind === "approve") return approve();
    if (item.kind === "review_impact") setSelectedCardId("constraint-bed-07");
    else if (item.kind === "view_plan" || item.kind === "preview" || item.kind === "compare")
      strategyTrayRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    else if (item.kind === "details" || item.kind === "inspect" || item.kind === "record_result")
      setDetailCard(card);
  };

  const ask = async (card: TacticalCard, question: string) => {
    if (!session || session.status !== "COMPLETED" || !session.result) {
      setError("Complete the local planning calculation before asking a specialist.");
      return;
    }
    setError("");
    setDetailCard(null);
    try {
      const advisor = card.entity.kind === "scenario" ? "hana" : card.entity.kind === "order" ? "ravi" :
        card.entity.kind === "crop_batch" ? "mei" : "asha";
      const created = await api.createConversation({ advisor, snapshot_kind: "planning", snapshot_id: session.id,
        focus: { card_id: card.id, entity_kind: focusKind(card), entity_id: card.entity.id } });
      let current = await api.conversation(created.id);
      setConversation(current);
      await api.sendConversationMessage(current.id, { content: question });
      current = await api.conversation(current.id);
      setConversation(current);
    } catch (caught) { setError(errorMessage(caught, "Could not start the card-grounded discussion.")); }
  };

  if (loading) return <div className="tm-state"><LoaderCircle className="tm-spin" /><h1>Opening tactical mission</h1><p>Loading the frozen farm and planning record.</p></div>;
  if (!session) return <div className="tm-state"><AlertTriangle /><h1>Mission unavailable</h1><p>{error}</p><button onClick={() => void load()}>Try again</button></div>;

  const metrics = selectedStrategy?.metrics as Record<string, unknown> | undefined;
  const calculationStatus = session.job ? {
    status: session.job.status,
    label: session.job.status === "QUEUED" ? "Calculation queued" : session.job.status === "RUNNING" ? "Recalculating plan" : session.job.status === "COMPLETED" ? "Recalculation complete" : `Calculation ${session.job.status.toLowerCase()}`,
    detail: session.job.error || `Planner stage: ${session.job.stage}`,
    jobId: session.job.id,
  } : { status: "IDLE" as const, label: "Ready" };

  return <div className="tm-root">
    {error && <div className="tm-error" role="alert"><AlertTriangle /><span>{error}</span><button onClick={() => setError("")}>Dismiss</button></div>}
    <TacticalConsole
      cards={cards}
      selectedCardId={selectedCardId}
      onSelectedCardChange={(card) => { setSelectedCardId(card.id); setDetailCard(null); }}
      onAction={action}
      onAskSubmit={ask}
      calculationStatus={calculationStatus}
      mission={{ kicker: "Singapore demo farm · tactical field console", title: "Protect the next harvest",
        detail: `Planning session ${session.id.slice(0, 8)} · revision ${session.revision}`,
        executionLabel: "Simulation · real operations disabled" }}
      demandSummary={{ demandLabel: "Booked demand", demandValue: metrics?.booked_requested_kg == null ? "—" : `${number(metrics.booked_requested_kg, 1)} kg`,
        supplyLabel: "Planned supply", supplyValue: metrics?.booked_delivered_kg == null ? "—" : `${number(metrics.booked_delivered_kg, 1)} kg`,
        gapLabel: "Booked gap", gapValue: metrics?.booked_shortfall_kg == null ? "—" : `${number(metrics.booked_shortfall_kg, 1)} kg`,
        basis: selectedStrategy ? `${selectedStrategy.name} · stored planner metrics` :
          strategies.length ? "No feasible strategy · diagnostics only" : "Calculate a local baseline" }}
      councilStatus={conversation ? conversation.last_request_status || conversation.status || "Open" : "Not submitted"}
      board={(context) => <TacticalFarmBoard session={session} crops={crops} context={context}
        active={constraintActive} busy={Boolean(busy) || jobActive}
        onCalculate={calculateBaseline} />}
      conversation={detailCard ? <CardDetails card={detailCard} /> : conversation ? <ConversationSummary conversation={conversation} /> : undefined}
      strategyTray={<div ref={strategyTrayRef}><StrategyTray strategies={strategies} selectedId={selectedStrategy?.id} /></div>}
      moreItems={[
        { id: "data", label: "Data Explorer", onSelect: () => onOpenTool("data") },
        { id: "research", label: "Council research", onSelect: () => onOpenTool("council") },
        { id: "outcomes", label: "Planning outcomes", onSelect: () => onOpenTool("outcomes") },
        { id: "records", label: "Reviews & records", onSelect: () => onNavigate("records") },
        { id: "reviews", label: "Edition reviews", href: "/v13/review" },
        { id: "audio-settings", label: "Audio & settings", onSelect: () => onOpenTool("setup") },
        { id: "changes", label: "Edition controls", href: "/v13/changes" },
      ]}
      onNavigate={onNavigate}
    />
  </div>;
}

function TacticalFarmBoard({ session, crops, context, active, busy, onCalculate }: {
  session: PlanningSession; crops: Crop[]; context: TacticalBoardContext; active: boolean; busy: boolean; onCalculate: () => Promise<void>;
}) {
  const raw = session.farm as typeof session.farm & { batches?: Array<Record<string, unknown>>; recipes?: Array<Record<string, unknown>> };
  const recipes = new Map((raw.recipes || []).map((item) => [String(item.id), String(item.crop_id)]));
  const batches = new Map((raw.batches || []).map((item) => [String(item.bed_id), item]));
  const cropNames = new Map(crops.map((crop) => [crop.id, crop.label]));
  const highlighted = new Set(context.highlightedBoardTargetIds);
  return <div className="tm-board">
    <div className="tm-board__legend"><span><i /> Frozen farm</span><span><i className="is-focus" /> Card target</span>{active && <b><Check /> B3 reservation active</b>}</div>
    <div className="tm-bed-grid">
      {session.farm.beds.map((bed) => {
        const batch = batches.get(bed.id), cropId = batch ? recipes.get(String(batch.recipe_id)) : undefined;
        const focus = highlighted.has(bed.id);
        return <article key={bed.id} data-board-target-id={bed.id} data-highlighted={focus ? "true" : "false"} className={bed.id === "bed-07" && active ? "is-reserved" : ""}>
          <span><Sprout /></span><div><strong>{bed.name}</strong><small>{cropId ? cropNames.get(cropId) || cropId.replaceAll("_", " ") : "Available grow space"}</small></div><em>{number(bed.area_m2)} m²</em>
        </article>;
      })}
    </div>
    {!session.result?.strategies?.length && <div className="tm-calculate"><div><strong>Calculate the baseline first</strong><p>Local CP-SAT only. No Council or provider call is made.</p></div><button disabled={busy} onClick={() => void onCalculate()}>{busy ? <LoaderCircle className="tm-spin" /> : <ShieldCheck />} Calculate baseline</button></div>}
  </div>;
}

function StrategyTray({ strategies, selectedId }: { strategies: Strategy[]; selectedId?: string }) {
  if (!strategies.length) return <p className="tm-empty">No calculated strategy yet.</p>;
  const noFeasible = strategies.every((strategy) => strategy.status !== "FEASIBLE");
  return <div className="tm-strategy-wrap">
    {noFeasible && <p className="tm-strategy-alert" role="status"><AlertTriangle /> No feasible option under the current constraints. Inspect the violation or undo the latest constraint before approval.</p>}
    <p className="tm-strategy-hint">{strategies.length} calculated options <span>Swipe sideways to compare</span></p>
    <div className="tm-strategies">{strategies.map((strategy) => {
      const violation = (strategy.violations?.[0] || {}) as { constraint_code?: string };
      return <article key={strategy.id} className={strategy.id === selectedId && strategy.status === "FEASIBLE" ? "is-selected" : ""}>
        <span>{strategy.status === "FEASIBLE" ? "Feasible" : "Not feasible"}</span><h3>{strategy.name}</h3><p>{strategy.description}</p>
        {violation.constraint_code && <p className="tm-strategy-violation">Constraint: {violation.constraint_code.toLowerCase().replaceAll("_", " ")}</p>}
        <dl><div><dt>Fill rate</dt><dd>{number(Number(strategy.metrics.fill_rate) * 100, 1)}%</dd></div><div><dt>Margin</dt><dd>SGD {number(strategy.metrics.margin_sgd)}</dd></div><div><dt>Waste</dt><dd>{number(strategy.metrics.waste_kg, 1)} kg</dd></div></dl>
      </article>;
    })}</div>
  </div>;
}

function ConversationSummary({ conversation }: { conversation: Conversation }) {
  const focus = conversation.focus as { title?: string; source?: string; entity_kind?: string; entity_id?: string } | undefined;
  return <div className="tm-conversation">
    {focus && <div className="tm-focus"><span>Validated focus</span><strong>{focus.title}</strong><small>{focus.source} · {focus.entity_kind}:{focus.entity_id}</small></div>}
    <p className="tm-provider-boundary">Creating this discussion did not contact a provider. Only the submitted question enters the existing bounded DeepSeek workflow.</p>
    <div aria-live="polite">{conversation.messages?.map((message) => <article key={message.id} className={`is-${message.speaker}`}><b>{message.speaker_name || message.speaker}</b><p>{message.content}</p>{message.validation_status && <small>{message.validation_status.replaceAll("_", " ")}</small>}</article>)}</div>
    {["QUEUED", "RUNNING"].includes(conversation.last_request_status || "") && <p className="tm-conversation__running"><LoaderCircle className="tm-spin" /> Specialist response {conversation.last_request_status?.toLowerCase()}</p>}
    {conversation.last_request_error && <div className="tm-conversation__blocked" role="status"><AlertTriangle /><div><strong>Specialist response unavailable</strong><p>{conversation.last_request_error}</p><small>The stored local plan and code-derived metrics remain available. No fallback dialogue was invented.</small></div></div>}
  </div>;
}

function CardDetails({ card }: { card: TacticalCard }) {
  return <div className="tm-focus"><span>Card details</span><strong>{card.title}</strong><p>{card.detail || card.summary}</p><small>{card.entity.kind}:{card.entity.id} · snapshot {card.planning.snapshotId}</small></div>;
}
