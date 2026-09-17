import {
  ArrowRight,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  ClipboardList,
  CloudRain,
  Database,
  ExternalLink,
  HelpCircle,
  Leaf,
  LoaderCircle,
  Menu,
  MessageCircleQuestion,
  RotateCcw,
  Sprout,
  Target,
  X,
} from "lucide-react";
import {
  useCallback,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
} from "react";
import { editionStorageKey as scopedStorageKey } from "../lib/edition";
import type { FarmerProposal, FarmerTask, PlanningJobStatus } from "../lib/planning";
import type { Strategy } from "../lib/types";
import "./tactical-console.css";

export type TacticalCardType =
  | "evidence"
  | "constraint"
  | "applied_constraint"
  | "crop"
  | "order"
  | "strategy"
  | "action"
  | "agent";

export type TacticalCardActionKind =
  | "review_impact"
  | "reserve_space"
  | "view_plan"
  | "inspect"
  | "preview"
  | "record_result"
  | "ask"
  | "ask_why"
  | "details"
  | "compare"
  | "approve"
  | "undo"
  | "evidence"
  | "role_details";

export interface TacticalEntityReference {
  kind:
    | "evidence"
    | "forecast"
    | "scenario"
    | "planning_constraint"
    | "grow_space"
    | "proposal"
    | "crop_batch"
    | "order"
    | "strategy"
    | "task"
    | "council_role";
  id: string;
  title?: string;
}

export interface TacticalPlanningBinding {
  snapshotId: string;
  snapshotHash?: string;
  sessionId?: string;
  revision?: number;
  resultId?: string;
  proposal?: Pick<
    FarmerProposal,
    "id" | "base_revision" | "proposal_revision" | "status"
  >;
  task?: Pick<FarmerTask, "id" | "event_revision" | "status">;
}

export interface TacticalCardProvenance {
  sourceTitle: string;
  sourceKind: "public" | "synthetic" | "farm_record" | "farmer_reported";
  observedAt?: string | null;
  retrievedAt?: string | null;
  freshness?: string;
  executionMode: string;
  /** Scenarios must opt in explicitly; the component never infers this from copy. */
  scenarioOnly?: boolean;
}

export interface TacticalCardFact {
  id: string;
  label: string;
  value: string;
  detail?: string;
  provenanceRef?: string;
}

export interface TacticalMetricDelta {
  id: string;
  label: string;
  value: string;
  delta?: string;
  direction?: "positive" | "negative" | "neutral";
}

export interface TacticalCardAction {
  id: string;
  kind: TacticalCardActionKind;
  label: string;
  emphasis?: "primary" | "secondary" | "danger";
  disabled?: boolean;
  disabledReason?: string;
}

export interface TacticalCard {
  /** Stable across recalculation and browser reloads. */
  id: string;
  type: TacticalCardType;
  eyebrow: string;
  title: string;
  summary: string;
  detail?: string;
  entity: TacticalEntityReference;
  state: "ready" | "selected" | "applied" | "pending" | "completed" | "stale";
  stateLabel: string;
  provenance: TacticalCardProvenance;
  boardTargets: string[];
  planning: TacticalPlanningBinding;
  facts?: TacticalCardFact[];
  metrics?: TacticalMetricDelta[];
  strategy?: Pick<Strategy, "id" | "name" | "status">;
  actions: TacticalCardAction[];
  suggestedQuestions?: string[];
}

export interface TacticalCalculationStatus {
  status: PlanningJobStatus | "IDLE";
  label: string;
  detail?: string;
  jobId?: string;
}

export interface TacticalMissionSummary {
  kicker?: string;
  title: string;
  detail?: string;
  executionLabel?: string;
}

export interface TacticalDemandSummary {
  demandLabel: string;
  demandValue: string;
  supplyLabel: string;
  supplyValue: string;
  gapLabel: string;
  gapValue: string;
  basis: string;
}

export interface TacticalMoreItem {
  id: string;
  label: string;
  href?: string;
  onSelect?: () => void;
}

export interface TacticalBoardContext {
  selectedCard: TacticalCard;
  highlightedBoardTargetIds: string[];
}

export interface TacticalConsoleProps {
  cards: TacticalCard[];
  /** Defaults to editionStorageKey("v13-tactical-card-stack"). */
  editionStorageKey?: string;
  selectedCardId?: string;
  onSelectedCardChange?: (card: TacticalCard, index: number) => void;
  onAction: (card: TacticalCard, action: TacticalCardAction) => void | Promise<void>;
  onAskSubmit?: (card: TacticalCard, question: string) => void | Promise<void>;
  dockMode?: "normal" | "inline" | "sticky";
  calculationStatus?: TacticalCalculationStatus;
  mission: TacticalMissionSummary;
  demandSummary: TacticalDemandSummary;
  councilStatus?: string;
  board:
    | ReactNode
    | ((context: TacticalBoardContext) => ReactNode);
  conversation?: ReactNode;
  strategyTray?: ReactNode;
  moreItems?: TacticalMoreItem[];
  moreContent?: ReactNode;
  onNavigate?: (destination: "mission" | "records" | "crops" | "more") => void;
  className?: string;
}

const typeLabels: Record<TacticalCardType, string> = {
  evidence: "Evidence",
  constraint: "Constraint",
  applied_constraint: "Active constraint",
  crop: "Crop",
  order: "Order",
  strategy: "Strategy",
  action: "Farm action",
  agent: "Council role",
};

const statusIcons: Partial<Record<TacticalCardActionKind, ReactNode>> = {
  ask: <MessageCircleQuestion aria-hidden="true" />,
  ask_why: <MessageCircleQuestion aria-hidden="true" />,
  undo: <RotateCcw aria-hidden="true" />,
  reserve_space: <Target aria-hidden="true" />,
  view_plan: <ArrowRight aria-hidden="true" />,
  details: <ClipboardList aria-hidden="true" />,
};

type StoredSelection = { selectedCardId: string; position: number };
type SwipeState = {
  pointerId: number;
  x: number;
  y: number;
  dx: number;
  dy: number;
  axis: "pending" | "horizontal" | "vertical";
};

function readStoredSelection(key: string): StoredSelection | null {
  try {
    const parsed = JSON.parse(localStorage.getItem(key) || "null") as Partial<StoredSelection> | null;
    if (
      parsed &&
      typeof parsed.selectedCardId === "string" &&
      Number.isInteger(parsed.position)
    )
      return {
        selectedCardId: parsed.selectedCardId,
        position: Number(parsed.position),
      };
  } catch {
    /* Browser storage is an enhancement; the card stack remains usable. */
  }
  return null;
}

function developmentDockMode(
  requested: TacticalConsoleProps["dockMode"],
): NonNullable<TacticalConsoleProps["dockMode"]> {
  if (requested) return requested;
  if (import.meta.env.DEV) {
    const candidate = new URLSearchParams(window.location.search).get("v13Dock");
    if (candidate === "inline" || candidate === "sticky") return candidate;
  }
  return "normal";
}

function orderActions(actions: TacticalCardAction[]) {
  const visible = actions.slice(0, 3);
  const primary = visible.find((action) => action.emphasis === "primary");
  if (!primary || visible.length < 3 || visible[1] === primary) return visible;
  const secondary = visible.filter((action) => action !== primary);
  return [secondary[0], primary, ...secondary.slice(1)];
}

function formatDate(value?: string | null) {
  if (!value) return "Not supplied";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(date);
}

export function TacticalConsole({
  cards,
  editionStorageKey,
  selectedCardId,
  onSelectedCardChange,
  onAction,
  onAskSubmit,
  dockMode: requestedDockMode,
  calculationStatus = { status: "IDLE", label: "Ready" },
  mission,
  demandSummary,
  councilStatus = "Not requested",
  board,
  conversation,
  strategyTray,
  moreItems = [],
  moreContent,
  onNavigate,
  className = "",
}: TacticalConsoleProps) {
  const storageKey = useMemo(
    () => editionStorageKey || scopedStorageKey("v13-tactical-card-stack"),
    [editionStorageKey],
  );
  const initialStored = useMemo(() => readStoredSelection(storageKey), [storageKey]);
  const matchedInitialIndex = cards.findIndex(
    (card) =>
      card.id === selectedCardId || card.id === initialStored?.selectedCardId,
  );
  const initialIndex =
    matchedInitialIndex >= 0
      ? matchedInitialIndex
      : Math.min(Math.max(initialStored?.position || 0, 0), Math.max(cards.length - 1, 0));
  const [internalCardId, setInternalCardId] = useState(
    cards[initialIndex]?.id || "",
  );
  const effectiveId = selectedCardId || internalCardId;
  const selectedIndex = Math.max(
    0,
    cards.findIndex((card) => card.id === effectiveId),
  );
  const selectedCard = cards[selectedIndex];
  const dockMode = developmentDockMode(requestedDockMode);
  const [askOpen, setAskOpen] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [stackVisible, setStackVisible] = useState(true);
  const [askBusy, setAskBusy] = useState(false);
  const stackRef = useRef<HTMLDivElement>(null);
  const askPanelRef = useRef<HTMLDivElement>(null);
  const askInputRef = useRef<HTMLTextAreaElement>(null);
  const restoreFocusRef = useRef<HTMLElement | null>(null);
  const swipeRef = useRef<SwipeState | null>(null);
  const titleId = useId();
  const askTitleId = useId();
  const appliedCards = cards.filter(
    (card) => card.type === "applied_constraint" || card.state === "applied",
  );

  useEffect(() => {
    if (!cards.length) return;
    if (cards.some((card) => card.id === effectiveId)) return;
    setInternalCardId(cards[0].id);
  }, [cards, effectiveId]);

  useEffect(() => {
    if (!selectedCard) return;
    try {
      localStorage.setItem(
        storageKey,
        JSON.stringify({ selectedCardId: selectedCard.id, position: selectedIndex }),
      );
    } catch {
      /* Browser storage is optional. */
    }
  }, [selectedCard, selectedIndex, storageKey]);

  useEffect(() => {
    const element = stackRef.current;
    if (!element || !("IntersectionObserver" in window)) return;
    const observer = new IntersectionObserver(
      ([entry]) => setStackVisible(entry.isIntersecting),
      { threshold: 0.12 },
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const closeAsk = useCallback(() => {
    setAskOpen(false);
    window.setTimeout(() => restoreFocusRef.current?.focus(), 0);
  }, []);

  useEffect(() => {
    if (!askOpen) return;
    askInputRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        closeAsk();
        return;
      }
      if (event.key !== "Tab" || !askPanelRef.current) return;
      const focusable = [...askPanelRef.current.querySelectorAll<HTMLElement>(
        'button:not([disabled]), textarea:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])',
      )];
      if (!focusable.length) return;
      const first = focusable[0],
        last = focusable.at(-1)!;
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [askOpen, closeAsk]);

  const selectAt = useCallback(
    (nextIndex: number) => {
      if (!cards.length) return;
      const normalized = (nextIndex + cards.length) % cards.length;
      const next = cards[normalized];
      setInternalCardId(next.id);
      onSelectedCardChange?.(next, normalized);
    },
    [cards, onSelectedCardChange],
  );
  const previous = useCallback(() => selectAt(selectedIndex - 1), [selectAt, selectedIndex]);
  const next = useCallback(() => selectAt(selectedIndex + 1), [selectAt, selectedIndex]);

  const onStackKeyDown = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    if (event.altKey || event.ctrlKey || event.metaKey) return;
    if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
      event.preventDefault();
      previous();
    } else if (event.key === "ArrowRight" || event.key === "ArrowDown") {
      event.preventDefault();
      next();
    } else if (event.key === "Home") {
      event.preventDefault();
      selectAt(0);
    } else if (event.key === "End") {
      event.preventDefault();
      selectAt(cards.length - 1);
    }
  };

  const onPointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.pointerType === "mouse" && event.button !== 0) return;
    swipeRef.current = {
      pointerId: event.pointerId,
      x: event.clientX,
      y: event.clientY,
      dx: 0,
      dy: 0,
      axis: "pending",
    };
  };
  const onPointerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    const swipe = swipeRef.current;
    if (!swipe || swipe.pointerId !== event.pointerId) return;
    swipe.dx = event.clientX - swipe.x;
    swipe.dy = event.clientY - swipe.y;
    if (swipe.axis === "pending" && Math.max(Math.abs(swipe.dx), Math.abs(swipe.dy)) > 10)
      swipe.axis = Math.abs(swipe.dx) > Math.abs(swipe.dy) * 1.25 ? "horizontal" : "vertical";
    if (swipe.axis === "horizontal") event.preventDefault();
  };
  const onPointerEnd = (event: ReactPointerEvent<HTMLDivElement>) => {
    const swipe = swipeRef.current;
    swipeRef.current = null;
    if (!swipe || swipe.pointerId !== event.pointerId || swipe.axis !== "horizontal") return;
    if (Math.abs(swipe.dx) < 48) return;
    if (swipe.dx < 0) next();
    else previous();
  };

  const activate = async (
    action: TacticalCardAction,
    trigger: HTMLElement,
  ) => {
    if (!selectedCard || action.disabled) return;
    if (action.kind === "ask" || action.kind === "ask_why") {
      restoreFocusRef.current = trigger;
      setQuestion(selectedCard.suggestedQuestions?.[0] || "");
      setAskOpen(true);
    }
    await onAction(selectedCard, action);
  };
  const submitQuestion = async () => {
    if (!selectedCard || !onAskSubmit || !question.trim()) return;
    setAskBusy(true);
    try {
      await onAskSubmit(selectedCard, question.trim());
    } finally {
      setAskBusy(false);
    }
  };

  if (!selectedCard)
    return (
      <section className={`tc-empty ${className}`} aria-labelledby={titleId}>
        <CircleAlert aria-hidden="true" />
        <h1 id={titleId}>{mission.title}</h1>
        <p>No tactical cards are available for this planning snapshot.</p>
      </section>
    );

  const actions = orderActions(selectedCard.actions);
  const boardContext: TacticalBoardContext = {
    selectedCard,
    highlightedBoardTargetIds: selectedCard.boardTargets,
  };
  const boardNode = typeof board === "function" ? board(boardContext) : board;

  return (
    <div
      className={`tc-shell tc-shell--dock-${dockMode} ${className}`.trim()}
      data-selected-card={selectedCard.id}
      data-selected-entity={`${selectedCard.entity.kind}:${selectedCard.entity.id}`}
      data-planning-snapshot={selectedCard.planning.snapshotId}
      data-board-targets={selectedCard.boardTargets.join(" ")}
    >
      <header className="tc-mission-header">
        <div className="tc-mission-header__identity">
          <span className="tc-mission-header__mark"><Sprout aria-hidden="true" /></span>
          <div>
            <p>{mission.kicker || "Singapore demo farm · tactical console"}</p>
            <h1 id={titleId}>{mission.title}</h1>
            {mission.detail && <span>{mission.detail}</span>}
          </div>
        </div>
        <div className="tc-mission-header__boundary">
          <strong>{mission.executionLabel || "Simulation · real operations disabled"}</strong>
          <span>Snapshot {selectedCard.planning.snapshotId.slice(0, 12)}</span>
        </div>
        <dl className="tc-demand-bar" aria-label="Demand and supply summary">
          <div><dt>{demandSummary.demandLabel}</dt><dd>{demandSummary.demandValue}</dd></div>
          <div><dt>{demandSummary.supplyLabel}</dt><dd>{demandSummary.supplyValue}</dd></div>
          <div className="tc-demand-bar__gap"><dt>{demandSummary.gapLabel}</dt><dd>{demandSummary.gapValue}</dd></div>
          <div className="tc-demand-bar__basis"><dt>Basis</dt><dd>{demandSummary.basis}</dd></div>
        </dl>
      </header>

      <div className="tc-workspace">
        <section className="tc-card-panel" aria-label="Tactical cards">
          <header className="tc-panel-heading">
            <div><p>Field deck</p><h2>What needs a decision?</h2></div>
            <span aria-label={`Card ${selectedIndex + 1} of ${cards.length}`}>
              {String(selectedIndex + 1).padStart(2, "0")} / {String(cards.length).padStart(2, "0")}
            </span>
          </header>

          <div
            className="tc-card-stack"
            ref={stackRef}
            tabIndex={0}
            role="group"
            aria-roledescription="card carousel"
            aria-label={`${selectedCard.title}. Use arrow keys or Previous and Next to change cards.`}
            onKeyDown={onStackKeyDown}
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerEnd}
            onPointerCancel={() => { swipeRef.current = null; }}
          >
            <div className="tc-card-layer tc-card-layer--back" aria-hidden="true" />
            <div className="tc-card-layer tc-card-layer--middle" aria-hidden="true" />
            <article
              className={`tc-card-layer tc-card tc-card--${selectedCard.type}`}
              data-card-id={selectedCard.id}
              aria-labelledby={`${titleId}-card`}
            >
              <header className="tc-card__header">
                <span className="tc-card__type">{typeLabels[selectedCard.type]}</span>
                <span className={`tc-card__state tc-card__state--${selectedCard.state}`}>
                  {selectedCard.stateLabel}
                </span>
              </header>
              <div className="tc-card__body">
                <p className="tc-card__eyebrow">{selectedCard.eyebrow}</p>
                <h3 id={`${titleId}-card`}>{selectedCard.title}</h3>
                <p>{selectedCard.summary}</p>
                {selectedCard.detail && <p className="tc-card__detail">{selectedCard.detail}</p>}
                {!!selectedCard.facts?.length && (
                  <dl className="tc-card__facts">
                    {selectedCard.facts.map((fact) => (
                      <div key={fact.id}>
                        <dt>{fact.label}</dt><dd>{fact.value}</dd>
                        {fact.detail && <small>{fact.detail}</small>}
                      </div>
                    ))}
                  </dl>
                )}
                {!!selectedCard.boardTargets.length && (
                  <div className="tc-target-row">
                    <Target aria-hidden="true" />
                    <span>Board target</span>
                    {selectedCard.boardTargets.map((target) => <b key={target}>{target}</b>)}
                  </div>
                )}
              </div>
              <ProvenanceStrip card={selectedCard} />
              {dockMode === "inline" && (
                <ActionDock
                  actions={actions}
                  card={selectedCard}
                  calculationStatus={calculationStatus}
                  onActivate={activate}
                />
              )}
            </article>
          </div>

          <div className="tc-stack-controls" aria-label="Card navigation">
            <button type="button" onClick={previous} aria-label="Previous tactical card">
              <ChevronLeft aria-hidden="true" /> Previous
            </button>
            <div aria-hidden="true">
              {cards.map((card, index) => (
                <span className={index === selectedIndex ? "is-current" : ""} key={card.id} />
              ))}
            </div>
            <button type="button" onClick={next} aria-label="Next tactical card">
              Next <ChevronRight aria-hidden="true" />
            </button>
          </div>

          {dockMode !== "inline" && (
            <ActionDock
              actions={actions}
              card={selectedCard}
              calculationStatus={calculationStatus}
              onActivate={activate}
            />
          )}

          {!!appliedCards.length && (
            <section className="tc-active-constraints" aria-labelledby={`${titleId}-active`}>
              <header>
                <span><CheckCircle2 aria-hidden="true" /></span>
                <div><p>Revision-bound</p><h3 id={`${titleId}-active`}>Active Constraints</h3></div>
              </header>
              <div>
                {appliedCards.map((card) => (
                  <button
                    type="button"
                    className={card.id === selectedCard.id ? "is-current" : ""}
                    key={card.id}
                    onClick={() => selectAt(cards.findIndex((item) => item.id === card.id))}
                  >
                    <span>{card.title}</span>
                    <small>{card.planning.proposal ? `Revision ${card.planning.proposal.proposal_revision}` : card.stateLabel}</small>
                  </button>
                ))}
              </div>
            </section>
          )}
        </section>

        <section className="tc-board-column" aria-label="Farm board and calculated changes">
          {!stackVisible && (
            <button
              type="button"
              className="tc-selected-summary"
              onClick={() => stackRef.current?.scrollIntoView({ behavior: "smooth", block: "center" })}
            >
              <span>{typeLabels[selectedCard.type]}</span>
              <strong>{selectedCard.title}</strong>
              <small>{selectedCard.stateLabel} · return to card</small>
            </button>
          )}
          <header className="tc-context-heading">
            <div><p>Live layout</p><h2>Farm board</h2></div>
            {!!selectedCard.boardTargets.length && (
              <span className="tc-board-focus"><Target aria-hidden="true" /> {selectedCard.boardTargets.join(", ")}</span>
            )}
          </header>
          <div className="tc-board-stage">{boardNode}</div>
          {!!selectedCard.metrics?.length && (
            <section
              className={`tc-metric-changes ${calculationStatus.status === "COMPLETED" ? "is-complete" : ""}`}
              aria-labelledby={`${titleId}-changes`}
            >
              <header><p>Code-derived</p><h3 id={`${titleId}-changes`}>Calculated changes</h3></header>
              <div>
                {selectedCard.metrics.map((metric) => (
                  <article className={`tc-delta tc-delta--${metric.direction || "neutral"}`} key={metric.id}>
                    <small>{metric.label}</small><strong>{metric.value}</strong>
                    {metric.delta && <span>{metric.delta}</span>}
                  </article>
                ))}
              </div>
            </section>
          )}
        </section>

        <aside className="tc-conversation-column" aria-label="Council context">
          <header className="tc-context-heading">
            <div><p>Contextual Council</p><h2>Ask with the card attached</h2></div>
            <span className="tc-council-status">{councilStatus}</span>
          </header>
          {conversation || (
            <div className="tc-context-empty">
              <MessageCircleQuestion aria-hidden="true" />
              <strong>No question submitted</strong>
              <p>Select Ask on an eligible card. FarmTact will not contact a provider automatically.</p>
            </div>
          )}
        </aside>

        <section className="tc-strategy-tray" aria-label="Strategy tray">
          <header className="tc-context-heading">
            <div><p>Revised options</p><h2>Strategy tray</h2></div>
          </header>
          {strategyTray || <p className="tc-tray-empty">Complete a numerical calculation to compare strategies.</p>}
        </section>
      </div>

      <nav className="tc-mobile-nav" aria-label="Primary">
        <button type="button" className="is-current" onClick={() => onNavigate?.("mission")}>
          <Target aria-hidden="true" /><span>Mission</span>
        </button>
        <button type="button" onClick={() => onNavigate?.("records")}>
          <Database aria-hidden="true" /><span>Records</span>
        </button>
        <button type="button" onClick={() => onNavigate?.("crops")}>
          <Leaf aria-hidden="true" /><span>Crops</span>
        </button>
        <button
          type="button"
          aria-expanded={moreOpen}
          aria-controls={`${titleId}-more`}
          onClick={() => { setMoreOpen((value) => !value); onNavigate?.("more"); }}
        >
          <Menu aria-hidden="true" /><span>More</span>
        </button>
      </nav>

      {moreOpen && (
        <section className="tc-more-sheet" id={`${titleId}-more`} aria-label="More FarmTact tools">
          <header><div><p>Workspace</p><h2>More</h2></div><button type="button" onClick={() => setMoreOpen(false)} aria-label="Close More"><X /></button></header>
          {!!moreItems.length && (
            <nav aria-label="More tools">
              {moreItems.map((item) => item.href ? (
                <a href={item.href} key={item.id}>{item.label}<ExternalLink aria-hidden="true" /></a>
              ) : (
                <button type="button" key={item.id} onClick={() => { item.onSelect?.(); setMoreOpen(false); }}>{item.label}<ArrowRight aria-hidden="true" /></button>
              ))}
            </nav>
          )}
          {moreContent}
        </section>
      )}

      <div className="tc-live-status" role="status" aria-live="polite" aria-atomic="true">
        {calculationStatus.status !== "IDLE" && `${calculationStatus.label}. ${calculationStatus.detail || ""}`}
      </div>

      {askOpen && (
        <div className="tc-dialog-scrim" onPointerDown={(event) => { if (event.target === event.currentTarget) closeAsk(); }}>
          <div
            className="tc-ask-panel"
            ref={askPanelRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby={askTitleId}
          >
            <header>
              <div><p>Card-grounded question</p><h2 id={askTitleId}>Ask why</h2></div>
              <button type="button" onClick={closeAsk} aria-label="Close Ask why"><X /></button>
            </header>
            <div className="tc-ask-card">
              <span>{typeLabels[selectedCard.type]} · {selectedCard.entity.kind}</span>
              <strong>{selectedCard.title}</strong>
              <small>{selectedCard.entity.id} · snapshot {selectedCard.planning.snapshotId.slice(0, 12)}</small>
            </div>
            {!!selectedCard.suggestedQuestions?.length && (
              <div className="tc-question-prompts" aria-label="Suggested questions">
                {selectedCard.suggestedQuestions.map((suggestion) => (
                  <button type="button" key={suggestion} onClick={() => { setQuestion(suggestion); askInputRef.current?.focus(); }}>{suggestion}</button>
                ))}
              </div>
            )}
            <label>
              Question
              <textarea
                ref={askInputRef}
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="Ask about this card and its frozen planning snapshot"
              />
            </label>
            <p className="tc-provider-boundary">
              Sending creates a contextual conversation. Numerical values stay server-derived; no question is sent automatically.
            </p>
            {!onAskSubmit && <p className="tc-disabled-reason">Conversation is unavailable for this card.</p>}
            <button
              type="button"
              className="tc-ask-submit"
              disabled={!onAskSubmit || !question.trim() || askBusy}
              onClick={() => void submitQuestion()}
            >
              {askBusy ? <LoaderCircle className="tc-spin" aria-hidden="true" /> : <MessageCircleQuestion aria-hidden="true" />}
              {askBusy ? "Creating conversation…" : "Ask with this card"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function ProvenanceStrip({ card }: { card: TacticalCard }) {
  const sourceLabel = card.provenance.sourceKind.replaceAll("_", " ");
  return (
    <footer className="tc-provenance" aria-label="Card provenance">
      <div>
        {card.provenance.scenarioOnly && (
          <strong><CloudRain aria-hidden="true" /> SIMULATION · SCENARIO ONLY</strong>
        )}
        <span>{sourceLabel} · {card.provenance.executionMode}</span>
      </div>
      <dl>
        <div><dt>Source</dt><dd>{card.provenance.sourceTitle}</dd></div>
        <div><dt>Observed</dt><dd>{formatDate(card.provenance.observedAt)}</dd></div>
        <div><dt>Freshness</dt><dd>{card.provenance.freshness || "Not supplied"}</dd></div>
      </dl>
    </footer>
  );
}

function ActionDock({
  actions,
  card,
  calculationStatus,
  onActivate,
}: {
  actions: TacticalCardAction[];
  card: TacticalCard;
  calculationStatus: TacticalCalculationStatus;
  onActivate: (action: TacticalCardAction, trigger: HTMLElement) => void | Promise<void>;
}) {
  const running = ["QUEUED", "RUNNING"].includes(calculationStatus.status);
  if (running)
    return (
      <div className="tc-action-dock tc-action-dock--progress" role="status" aria-live="polite">
        <LoaderCircle className="tc-spin" aria-hidden="true" />
        <span><strong>{calculationStatus.label}</strong><small>{calculationStatus.detail || "Local planner is recalculating the revision-bound proposal."}</small></span>
        {calculationStatus.jobId && <code>{calculationStatus.jobId.slice(0, 12)}</code>}
      </div>
    );
  return (
    <div className="tc-action-dock" aria-label={`Actions for ${card.title}`}>
      {actions.map((action) => (
        <div
          className={`tc-action-slot ${action.emphasis === "primary" ? "tc-action-slot--primary" : ""}`}
          key={action.id}
        >
          <button
            type="button"
            className={`tc-action tc-action--${action.emphasis || "secondary"}`}
            disabled={action.disabled}
            aria-describedby={action.disabledReason ? `${card.id}-${action.id}-reason` : undefined}
            onClick={(event) => void onActivate(action, event.currentTarget)}
          >
            {statusIcons[action.kind] || (action.emphasis === "primary" ? <ArrowRight aria-hidden="true" /> : <HelpCircle aria-hidden="true" />)}
            <span>{action.label}</span>
          </button>
          {action.disabledReason && (
            <small className="tc-disabled-reason" id={`${card.id}-${action.id}-reason`}>{action.disabledReason}</small>
          )}
        </div>
      ))}
    </div>
  );
}

export default TacticalConsole;
