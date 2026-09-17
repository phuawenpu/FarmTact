import { editionStorageKey } from "./edition";

export type BeginnerPhase =
  | "order"
  | "calculate"
  | "choose"
  | "event"
  | "maintenance"
  | "recovery"
  | "delivery"
  | "debrief";

export type BeginnerCropStage =
  | "empty"
  | "seedling"
  | "growing"
  | "ready"
  | "maintenance"
  | "recovering"
  | "harvested";

export type BeginnerActionKind =
  | "start"
  | "calculate"
  | "choose"
  | "advance_event"
  | "maintain"
  | "recover"
  | "deliver"
  | "continue"
  | "replay"
  | "explore"
  | "open"
  | "ask";

export interface BeginnerFact {
  id: string;
  label: string;
  value: string;
  detail?: string;
  tone?: "default" | "good" | "warning" | "risk";
  source?: string;
}

export interface BeginnerAction {
  id: string;
  kind: BeginnerActionKind;
  label: string;
  disabled?: boolean;
  disabledReason?: string;
  pendingLabel?: string;
  optionId?: string;
}

export interface BeginnerCard {
  id: string;
  phase: BeginnerPhase;
  eyebrow: string;
  title: string;
  summary: string;
  explanation?: string;
  /** Authored orientation copy. Always rendered with a visible Guide tip label. */
  guideTip?: string;
  statusLabel?: string;
  facts?: BeginnerFact[];
  primaryAction?: BeginnerAction;
  boardTargetIds?: string[];
  resultId?: string;
  entity?: {
    kind: string;
    id: string;
    revision?: number;
  };
}

export interface BeginnerBed {
  id: string;
  name: string;
  cropLabel?: string;
  cropStage: BeginnerCropStage;
  progress?: number;
  accent?: string;
  statusLabel?: string;
}

export interface BeginnerScene {
  resultId?: string;
  dateLabel?: string;
  weatherLabel?: string;
  eventLabel?: string;
  eventTone?: "calm" | "rain" | "heat" | "maintenance" | "recovery" | "delivery" | "warning" | "success" | "neutral";
  beds: BeginnerBed[];
}

export interface BeginnerSeasonState {
  id: string;
  revision: number;
  /** Exact backend stage used by journeys and accessibility tests. */
  serverStage?: string;
  phase: BeginnerPhase;
  objective: string;
  objectiveDetail?: string;
  progressLabel?: string;
  cards: BeginnerCard[];
  selectedCardId?: string;
  scene: BeginnerScene;
  status?: "ready" | "queued" | "running" | "completed" | "blocked";
  statusLabel?: string;
  /** Server-provided notice, including revision conflicts or ineligible actions. */
  notice?: string;
}

export type BeginnerJourneyStage =
  | "START"
  | "CALCULATING"
  | "CHOOSE_PLAN"
  | "PLAN_SELECTED"
  | "MAINTENANCE_DUE"
  | "RECALCULATING"
  | "CHOOSE_RECOVERY"
  | "RECOVERY_SELECTED"
  | "DELIVERY_DUE"
  | "COMPLETE";

export interface BeginnerJourneyChoice {
  id: string;
  strategy_id?: string | null;
  title: string;
  tradeoff: string;
  metrics: Record<string, string | number | null>;
  eligible: boolean;
  disabled_reason?: string | null;
  result_id?: string | null;
  board_target_ids?: string[];
  result_hash?: string | null;
  allocations?: Array<{
    id: string;
    bed_id: string;
    crop_id: string;
    sow_date: string;
    transplant_date: string;
    harvest_date: string;
    expected_kg: number;
  }>;
}

export interface BeginnerJourneyCard {
  id: string;
  type: string;
  title: string;
  summary: string;
  state: string;
  provenance: { label: string; source: string };
  entity: { kind: string; id: string };
  actions: Array<BeginnerJourneyNextAction & { inference_triggered?: false }>;
}

export interface BeginnerJourneyNextAction {
  id: string;
  label: string;
  kind: string;
  eligible: boolean;
  disabled_reason?: string | null;
  requires_option?: boolean;
}

export interface BeginnerJourney {
  id: string;
  version: string;
  revision: number;
  status: string;
  stage: BeginnerJourneyStage;
  objective: string | { title?: string; detail?: string };
  scenario: {
    title: string;
    summary: string;
    bed_id: string;
    bed_name: string;
    maintenance: { start_date: string; end_date: string };
    provenance_label: string;
    data_mode: string;
  };
  result_id?: string | null;
  scene?: {
    result_id?: string | null;
    world_id?: string | null;
    clock_date?: string | null;
    projection_source: string;
    board_target_ids: string[];
    beds: Array<{
      id: string;
      name: string;
      crop_label?: string | null;
      crop_stage: BeginnerCropStage;
      progress?: number | null;
      accent?: string | null;
      status_label?: string | null;
      allocation_id?: string | null;
    }>;
    event?: {
      tone: "warning" | "success" | "neutral";
      label: string;
      date?: string | null;
      weather?: string | null;
    } | null;
  } | null;
  planning_session?: {
    id: string;
    status: string;
    revision: number;
    job?: { id?: string; status?: string; stage?: string; error?: string | null } | null;
  } | null;
  cards: BeginnerJourneyCard[];
  choices: BeginnerJourneyChoice[];
  selected_choice_id?: string | null;
  next_action?: BeginnerJourneyNextAction | null;
  timeline: Array<Record<string, unknown>>;
  metrics: {
    clock_date?: string | null;
    horizon_end?: string | null;
    planned_harvest_kg?: number | null;
    committed_demand_kg?: number | null;
    fulfilled_demand_kg?: number | null;
    waste_kg?: number | null;
    shortfall_kg?: number | null;
    land_utilization_pct?: number | null;
    cash_balance?: number | null;
    [key: string]: string | number | null | undefined;
  };
  debrief?: {
    outcome: string;
    title: string;
    summary: string;
    objective_met: boolean;
    highlights: string[];
    replay_available: boolean;
  } | null;
  audit: Array<Record<string, unknown>>;
  execution_mode: string;
  data_mode: string;
  real_operations_enabled: false;
  inference_calls?: number;
}

export type BeginnerUtilityKind =
  | "journal"
  | "records"
  | "crops"
  | "settings"
  | "replay"
  | "next_step"
  | "adviser";

export interface BeginnerUtilityCard {
  id: string;
  kind: BeginnerUtilityKind;
  title: string;
  summary: string;
  eyebrow?: string;
  guideTip?: string;
  primaryAction?: BeginnerAction;
}

export interface BeginnerStoredProgress {
  introSeen: boolean;
  selectedCardId?: string;
  utilityCardId?: string;
  explanationOpen?: boolean;
  askDraft?: string;
  serverSeasonId?: string;
  serverRevision?: number;
}

export const beginnerPhaseOrder: BeginnerPhase[] = [
  "order",
  "calculate",
  "choose",
  "event",
  "maintenance",
  "recovery",
  "delivery",
  "debrief",
];

export const beginnerPhaseLabels: Record<BeginnerPhase, string> = {
  order: "Meet the order",
  calculate: "Calculate plans",
  choose: "Choose a plan",
  event: "Next event",
  maintenance: "Farm maintenance",
  recovery: "Recovery",
  delivery: "Delivery",
  debrief: "Season debrief",
};

export const defaultBeginnerUtilities: BeginnerUtilityCard[] = [
  {
    id: "utility-next-step",
    kind: "next_step",
    eyebrow: "Continue",
    title: "Your next step",
    summary: "Return to the current season decision and take the next eligible action.",
    primaryAction: { id: "return-to-season", kind: "continue", label: "Back to season" },
  },
  {
    id: "utility-journal",
    kind: "journal",
    eyebrow: "Season memory",
    title: "Journal",
    summary: "Review the decisions and consequences already recorded for this season.",
    primaryAction: { id: "open-journal", kind: "open", label: "Open journal" },
  },
  {
    id: "utility-records",
    kind: "records",
    eyebrow: "Farm facts",
    title: "Records",
    summary: "Inspect the source records that the current plan is using.",
    primaryAction: { id: "open-records", kind: "open", label: "View records" },
  },
  {
    id: "utility-crops",
    kind: "crops",
    eyebrow: "Crop guide",
    title: "Crops",
    summary: "Learn the growth cycle and evidence limits for crops in this farm.",
    primaryAction: { id: "open-crops", kind: "open", label: "Browse crops" },
  },
  {
    id: "utility-adviser",
    kind: "adviser",
    eyebrow: "Optional",
    title: "Ask an adviser",
    summary: "Submit a question about the current server-validated card. Nothing is sent automatically.",
    primaryAction: { id: "ask-adviser", kind: "ask", label: "Prepare a question" },
  },
  {
    id: "utility-settings",
    kind: "settings",
    eyebrow: "Preferences",
    title: "Settings",
    summary: "Adjust motion and other presentation preferences without changing the farm plan.",
    primaryAction: { id: "open-settings", kind: "open", label: "Open settings" },
  },
  {
    id: "utility-replay",
    kind: "replay",
    eyebrow: "Learn again",
    title: "Replay introduction",
    summary: "Return to the three-part introduction. Your stored server season is not deleted.",
    primaryAction: { id: "replay-introduction", kind: "replay", label: "Replay introduction" },
  },
];

export function beginnerStorageKey(key = "beginner-game-progress") {
  return editionStorageKey(key);
}

export function readBeginnerProgress(key = beginnerStorageKey()): BeginnerStoredProgress {
  try {
    const value = JSON.parse(localStorage.getItem(key) || "null") as Partial<BeginnerStoredProgress> | null;
    return value && typeof value === "object"
      ? {
          introSeen: value.introSeen === true,
          ...(typeof value.selectedCardId === "string" ? { selectedCardId: value.selectedCardId } : {}),
          ...(typeof value.utilityCardId === "string" ? { utilityCardId: value.utilityCardId } : {}),
          ...(typeof value.explanationOpen === "boolean" ? { explanationOpen: value.explanationOpen } : {}),
          ...(typeof value.askDraft === "string" ? { askDraft: value.askDraft } : {}),
          ...(typeof value.serverSeasonId === "string" ? { serverSeasonId: value.serverSeasonId } : {}),
          ...(typeof value.serverRevision === "number" ? { serverRevision: value.serverRevision } : {}),
        }
      : { introSeen: false };
  } catch {
    return { introSeen: false };
  }
}

export function writeBeginnerProgress(progress: BeginnerStoredProgress, key = beginnerStorageKey()) {
  try {
    localStorage.setItem(key, JSON.stringify(progress));
  } catch {
    /* The game remains usable when browser storage is unavailable. */
  }
}

export function clampProgress(value: number | undefined) {
  return Math.max(0, Math.min(1, Number.isFinite(value) ? Number(value) : 0));
}

function journeyPhase(stage: string): BeginnerPhase {
  if (stage === "START") return "order";
  if (stage === "CALCULATING") return "calculate";
  if (stage === "CHOOSE_PLAN" || stage === "PLAN_SELECTED") return "choose";
  if (stage === "MAINTENANCE_DUE") return "maintenance";
  if (stage === "RECALCULATING" || stage === "CHOOSE_RECOVERY" || stage === "RECOVERY_SELECTED") return "recovery";
  if (stage === "DELIVERY_DUE") return "delivery";
  if (stage === "COMPLETE") return "debrief";
  return "event";
}

function metricLabel(key: string) {
  const known: Record<string, string> = {
    planned_harvest_kg: "Planned harvest",
    committed_demand_kg: "Committed demand",
    fulfilled_demand_kg: "Fulfilled demand",
    waste_kg: "Expected waste",
    shortfall_kg: "Expected shortfall",
    land_utilization_pct: "Land used",
    cash_balance: "Cash balance",
  };
  return known[key] || key.replaceAll("_", " ");
}

function metricValue(key: string, value: string | number | null | undefined) {
  if (value == null) return "Not calculated";
  if (typeof value === "string") return value;
  if (key === "land_utilization_pct") return `${value.toLocaleString(undefined, { maximumFractionDigits: 1 })}%`;
  if (key === "cash_balance") return `SGD ${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
  if (key.endsWith("_kg")) return `${value.toLocaleString(undefined, { maximumFractionDigits: 1 })} kg`;
  return value.toLocaleString();
}

function actionKind(value: string, phase: BeginnerPhase): BeginnerActionKind {
  const known: BeginnerActionKind[] = ["calculate", "choose", "maintain", "recover", "deliver", "continue", "replay", "explore", "open", "ask"];
  if (known.includes(value as BeginnerActionKind)) return value as BeginnerActionKind;
  if (value === "advance") return "advance_event";
  if (value === "record") return phase === "delivery" ? "deliver" : phase === "recovery" ? "recover" : "maintain";
  return "continue";
}

export function seasonFromBeginnerJourney(journey: BeginnerJourney): BeginnerSeasonState {
  const phase = journeyPhase(journey.stage);
  const objective = typeof journey.objective === "string"
    ? journey.objective
    : journey.objective.title || "Complete your first farm season";
  const objectiveDetail = typeof journey.objective === "string" ? undefined : journey.objective.detail;
  const nextAction = journey.next_action;
  const serverDecisionCards = nextAction
    ? journey.cards.filter((card) => card.actions.some((action) => action.id === nextAction.id))
    : journey.cards.filter((card) => ["active", "selected", "completed", "current"].includes(card.state.toLowerCase()));
  const contextualCards = serverDecisionCards.length
    ? serverDecisionCards
    : journey.cards.length ? [journey.cards[journey.cards.length - 1]] : [];
  const choicesAreCurrent = Boolean(nextAction?.requires_option && journey.choices.length);
  const cards: BeginnerCard[] = (choicesAreCurrent ? [] : contextualCards).map((card) => {
    const cardAction = nextAction && !nextAction.requires_option ? nextAction : undefined;
    return {
      id: card.id,
      phase,
      eyebrow: card.type.replaceAll("_", " "),
      title: card.title,
      summary: card.summary,
      statusLabel: card.state.replaceAll("_", " "),
      explanation: `This comes from ${card.provenance.source}. It is recorded as ${card.provenance.label.toLowerCase()}.`,
      entity: { kind: card.entity.kind, id: card.entity.id, revision: journey.revision },
      primaryAction: cardAction ? {
        id: cardAction.id,
        kind: actionKind(cardAction.kind, phase),
        label: cardAction.label,
        disabled: !cardAction.eligible,
        disabledReason: cardAction.disabled_reason || undefined,
      } : undefined,
    };
  });
  if (choicesAreCurrent) {
    journey.choices.forEach((choice) => {
      const action = nextAction;
      cards.push({
        id: `choice-${choice.id}`,
        phase,
        eyebrow: phase === "recovery" ? "Recovery choice" : "Calculated plan",
        title: choice.title,
        summary: choice.tradeoff,
        statusLabel: choice.eligible ? "Eligible" : "Unavailable",
        facts: Object.entries(choice.metrics).map(([key, value]) => ({
          id: `${choice.id}-${key}`,
          label: metricLabel(key),
          value: metricValue(key, value),
          source: "Stored local planner result",
        })),
        boardTargetIds: choice.board_target_ids || [],
        resultId: choice.result_id || journey.result_id || undefined,
        entity: { kind: phase === "recovery" ? "recovery_choice" : "strategy", id: choice.strategy_id || choice.id, revision: journey.revision },
        primaryAction: action ? {
          id: action.id,
          kind: actionKind(action.kind, phase),
          label: action.label,
          disabled: !action.eligible || !choice.eligible,
          disabledReason: choice.disabled_reason || action.disabled_reason || undefined,
          optionId: choice.id,
        } : undefined,
      });
    });
  }
  if (!cards.length) {
    const action = journey.next_action;
    cards.push({
      id: `journey-${journey.id}-${journey.stage.toLowerCase()}`,
      phase,
      eyebrow: beginnerPhaseLabels[phase],
      title: journey.scenario.title,
      summary: journey.scenario.summary,
      statusLabel: journey.status.replaceAll("_", " "),
      facts: Object.entries(journey.metrics).filter(([, value]) => value != null).slice(0, 4).map(([key, value]) => ({
        id: key,
        label: metricLabel(key),
        value: metricValue(key, value),
        source: journey.scenario.provenance_label,
      })),
      entity: { kind: "beginner_journey", id: journey.id, revision: journey.revision },
      primaryAction: action ? {
        id: action.id,
        kind: actionKind(action.kind, phase),
        label: action.label,
        disabled: !action.eligible,
        disabledReason: action.disabled_reason || undefined,
      } : undefined,
    });
  }
  const preferredChoiceId = journey.selected_choice_id || journey.choices.find((choice) => choice.eligible)?.id;
  const selectedChoiceCard = preferredChoiceId ? `choice-${preferredChoiceId}` : undefined;
  return {
    id: journey.id,
    revision: journey.revision,
    phase,
    objective,
    objectiveDetail,
    progressLabel: `Step ${Math.min(beginnerPhaseOrder.indexOf(phase) + 1, beginnerPhaseOrder.length)} of ${beginnerPhaseOrder.length}`,
    cards,
    selectedCardId: cards.some((card) => card.id === selectedChoiceCard) ? selectedChoiceCard : cards[0]?.id,
    serverStage: journey.stage,
    scene: journey.scene ? {
      resultId: journey.scene.result_id || undefined,
      dateLabel: journey.scene.clock_date || journey.scene.event?.date || undefined,
      weatherLabel: journey.scene.event?.weather || undefined,
      eventLabel: journey.scene.event?.label || undefined,
      eventTone: journey.scene.event?.tone,
      beds: journey.scene.beds.map((bed) => ({
        id: bed.id,
        name: bed.name,
        cropLabel: bed.crop_label || undefined,
        cropStage: bed.crop_stage,
        progress: bed.progress == null ? undefined : bed.progress,
        accent: bed.accent || undefined,
        statusLabel: bed.status_label || undefined,
      })),
    } : { beds: [] },
    status: journey.stage === "CALCULATING" || journey.stage === "RECALCULATING" ? "running" : journey.status.toLowerCase().includes("block") ? "blocked" : journey.stage === "COMPLETE" ? "completed" : "ready",
    statusLabel: journey.planning_session?.job?.status
      ? `Plan calculation: ${journey.planning_session.job.status.replaceAll("_", " ").toLowerCase()}`
      : journey.status.replaceAll("_", " ").toLowerCase(),
  };
}
