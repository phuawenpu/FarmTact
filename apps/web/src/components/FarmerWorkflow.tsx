import {
  AlertTriangle,
  ArrowRight,
  Check,
  CheckCircle2,
  ClipboardCheck,
  FileSpreadsheet,
  Leaf,
  LoaderCircle,
  PackageCheck,
  Play,
  Recycle,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Upload,
  Users,
  X,
} from "lucide-react";
import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { api } from "../lib/api";
import { ADVISORS, publicAdvisorLabel } from "../lib/game";
import { CouncilWorkspace } from "./CouncilWorkspace";
import { DecisionGuide, SavedConsequence } from "./DecisionGuide";
import { workspaceDrafts } from "../lib/workspaceDrafts";
import { editionPath, editionStorageKey } from "../lib/edition";
import {
  farmerWorkflowApi,
  planningApi,
  rememberPlanningSession,
  rememberedPlanningSession,
  type FarmerAssumptions,
  type FarmerProposal,
  type FarmerTask,
  type FarmerWorkflowState,
  type PlanningSession,
} from "../lib/planning";
import type { Conversation, ConversationMessage } from "../lib/game";
import type { Crop, Strategy } from "../lib/types";
import { CropArt } from "./Visuals";
import "./v22-decision.css";

type Phase =
  "observe" | "discuss" | "decide" | "approve" | "act" | "verify" | "replan";
type DiscussionSource = {
  conversationId: string;
  messageId: string;
  actions: NonNullable<ConversationMessage["proposed_actions"]>;
};
type ProposalDraft = {
  demand: number;
  yieldPct: number;
  delay: number;
  scenarioCrop: string;
  bed: string;
  reserveStart: string;
  reserveEnd: string;
  nursery: number;
  labour: number;
  cash: number;
  orderEnabled: boolean;
  orderReference: string;
  orderCrop: string;
  orderDueDate: string;
  orderQty: number;
  orderPrice: number;
  orderStatus: "confirmed" | "tentative";
};
type PendingProposalApply = {
  version: "v22-pending-proposal-apply-v1";
  sessionId: string;
  resultId: string;
  baseRevision: number;
  strategyId: string;
  draftKey: string;
  draft: ProposalDraft;
  assumptions: FarmerAssumptions;
  proposal: FarmerProposal;
  createdAt: string;
};

function pendingProposalKey(sessionId: string) {
  return editionStorageKey(`pending-proposal-apply:${sessionId}`);
}

function readPendingProposal(sessionId: string): PendingProposalApply | null {
  try {
    const value = JSON.parse(localStorage.getItem(pendingProposalKey(sessionId)) || "null") as PendingProposalApply | null;
    return value?.version === "v22-pending-proposal-apply-v1" && value.sessionId === sessionId ? value : null;
  } catch { return null; }
}

function savePendingProposal(sessionId: string, value: PendingProposalApply | null) {
  try {
    const key = pendingProposalKey(sessionId);
    if (value) localStorage.setItem(key, JSON.stringify(value));
    else localStorage.removeItem(key);
  } catch { /* local recovery is optional; server idempotency remains authoritative */ }
}
const phases: Array<[Phase, string, string]> = [
  ["observe", "Observe", "Review records"],
  ["discuss", "Discuss", "Council review"],
  ["decide", "Decide", "Compare proposals"],
  ["approve", "Approve", "Create actions"],
  ["act", "Act", "Record results"],
  ["verify", "Verify", "Check impact"],
  ["replan", "Replan", "Recover safely"],
];
const roleFallbacks = [
  "Demand Planner",
  "Crop Planner",
  "Weather & Risk Monitor",
  "Market & Price Analyst",
  "Capacity & Cost Analyst",
  "Farm Planner",
  "Plan Reviewer",
];
const functionalRoleIds: Record<string, string> = {
  "Demand Planner": "demand_analyst",
  "Crop Planner": "production_analyst",
  "Weather & Risk Monitor": "weather_analyst",
  "Market & Price Analyst": "market_analyst",
  "Capacity & Cost Analyst": "profit_analyst",
  "Farm Planner": "supply_chain_analyst",
  "Plan Reviewer": "planning_chair",
};
const blankWorkflow: FarmerWorkflowState = {
  version: "farmer-workflow-v1",
  phase: "planning",
  revision: 0,
  inbox: [],
  proposals: [],
  tasks: [],
  events: [],
  real_operations_enabled: false,
};

export function FarmerWorkflow({
  crops,
  onOpenSetup,
}: {
  crops: Crop[];
  onOpenSetup: () => void;
}) {
  const [session, setSession] = useState<PlanningSession | null>(null),
    [workflow, setWorkflow] = useState<FarmerWorkflowState>(blankWorkflow);
  const [loading, setLoading] = useState(true),
    [busy, setBusy] = useState(""),
    [error, setError] = useState(""),
    [navigationHint, setNavigationHint] = useState(""),
    [phase, setPhase] = useState<Phase>("observe");
  const [inboxOpen, setInboxOpen] = useState(false),
    [mediaOpen, setMediaOpen] = useState(false),
    [selected, setSelected] = useState("");
  const [formOpen, setFormOpen] = useState(false),
    [actionsOpen, setActionsOpen] = useState(false),
    [discussionSource, setDiscussionSource] = useState<DiscussionSource | null>(null),
    [rescueOpen, setRescueOpen] = useState(false);
  // Edition-scoped local drafts survive reload; they never become submitted records.
  const [proposalDrafts] = useState(() => workspaceDrafts<ProposalDraft>("proposals"));
  const refreshWorkflow = useCallback(async () => {
    const next = await farmerWorkflowApi.state();
    setWorkflow({ ...blankWorkflow, ...next });
    return next;
  }, []);
  const loadPending = useRef(false);
  const load = useCallback(async () => {
    if (loadPending.current) return;
    loadPending.current = true;
    setLoading(true);
    setError("");
    try {
      let value: PlanningSession | undefined;
      const remembered = rememberedPlanningSession();
      if (remembered)
        try {
          value = await planningApi.get(remembered);
        } catch {
          /* latest */
        }
      if (!value) {
        const page = await planningApi.list();
        value = page.sessions.find((item) => item.workflow === true);
      }
      if (!value?.workflow)
        value = await planningApi.create("V12 farmer workflow", true);
      rememberPlanningSession(value.id);
      const flow = await refreshWorkflow();
      setSession(value);
      setSelected(
        value.selected_strategy_id || value.result?.strategies?.[0]?.id || "",
      );
      setPhase(derivePhase(value, flow));
    } catch (caught) {
      setError(message(caught, "The farm workflow could not be opened."));
    } finally {
      loadPending.current = false;
      setLoading(false);
    }
  }, [refreshWorkflow]);
  useEffect(() => {
    void load();
  }, [load]);
  useEffect(() => {
    if (!session?.job || !["QUEUED", "RUNNING"].includes(session.job.status))
      return;
    let disposed = false;
    let pending = false;
    const timer = window.setInterval(async () => {
      if (pending) return;
      pending = true;
      try {
        const next = await planningApi.get(session.id);
        if (disposed) return;
        setSession(next);
        if (!["QUEUED", "RUNNING"].includes(next.job?.status || "")) {
          window.clearInterval(timer);
          setBusy("");
          const flow = await refreshWorkflow();
          if (!disposed) setPhase(derivePhase(next, flow));
        }
      } catch {
        // A later read reconciles the same job; never resubmit a mutation here.
      } finally {
        pending = false;
      }
    }, 1800);
    return () => { disposed = true; window.clearInterval(timer); };
  }, [session?.id, session?.job?.id, refreshWorkflow]);
  const mutate = async (
    label: string,
    action: (current: PlanningSession) => Promise<PlanningSession>,
  ) => {
    if (!session) return;
    setBusy(label);
    setError("");
    try {
      const next = await action(session);
      setSession(next);
      if (!["QUEUED", "RUNNING"].includes(next.job?.status || "")) setBusy("");
    } catch (caught) {
      setBusy("");
      setError(message(caught, `Could not ${label}.`));
    }
  };
  const strategies = session?.result?.strategies || [],
    chosen = strategies.find((item) => item.id === selected) || strategies[0],
    findings = normalizedFindings(session),
    reviewState = reviewStatus(session, findings),
    approvableProposal = session
      ? currentAppliedProposal(session, workflow, selected)
      : undefined,
    sessionProposalIds = new Set(
      workflow.proposals
        .filter((proposal) => proposal.session_id === session?.id)
        .map((proposal) => proposal.id),
    ),
    sessionTasks = workflow.tasks.filter((task) =>
      sessionProposalIds.has(task.proposal_id),
    );
  useEffect(() => {
    setSelected(current => strategies.some(item => item.id === current)
      ? current : session?.selected_strategy_id || strategies[0]?.id || "");
  }, [session?.result, session?.selected_strategy_id]);
  const jumpToPhase = (next: Phase) => {
    setPhase(next);
    const targets: Record<Phase, string> = {
      observe: '.flow-observe', discuss: '.council-room', decide: '.decision-stage',
      approve: '.decision-actions', act: '.action-stage', verify: '.task-result-panel', replan: '.recovery-stage',
    };
    let target = document.querySelector<HTMLElement>(targets[next]);
    const missing = !target;
    if (!target) target = document.querySelector<HTMLElement>(strategies.length ? '.decision-stage' : '.flow-callout');
    setNavigationHint(missing ? (!strategies.length ? 'Compare planting plans first. No farm change has been made.'
      : next === 'verify' ? 'Record a task result before verifying its impact.'
      : next === 'replan' ? 'No task currently requires recovery. Use Adjust assumptions to review a future change.'
      : 'Review and approve a proposal before recording sandbox work.') : '');
    target?.focus({preventScroll:true});
    target?.scrollIntoView({block:'start',behavior:'instant'});
  };
  if (loading)
    return (
      <Empty
        icon={<LoaderCircle className="spin" />}
        title="Opening the farm decision loop"
        detail="Loading records, farm state and saved review."
      />
    );
  if (!session)
    return (
      <Empty
        icon={<AlertTriangle />}
        title="Workflow unavailable"
        detail={error}
        action={
          <button className="button button--forest" onClick={() => void load()}>
            Try again
          </button>
        }
      />
    );
  const firstOrder = [...session.farm.orders].sort((a,b)=>a.due_date.localeCompare(b.due_date)||a.id.localeCompare(b.id))[0];
  const objective = firstOrder ? `Can we cover ${num(firstOrder.quantity_kg)} kg ${crops.find(crop=>crop.id===firstOrder.crop_id)?.name || firstOrder.crop_id.replaceAll('_',' ')} by ${civil(firstOrder.due_date)}?` : 'What should this farm plan next?';
  const draftContext = JSON.stringify([session.id, session.revision, chosen?.id || ""]);
  const proposalDraftKey = JSON.stringify([
    draftContext, discussionSource?.conversationId || "", discussionSource?.messageId || "",
  ]);
  return (
    <div className="farmer-flow">
      <DecisionGuide title={sessionTasks.some(task=>task.status==='recovery_required') ? "Review what changed; plan the next step" : objective}
        detail={!strategies.length ? "Start with this dated order. All recorded demand stays in the calculation. Compare options, then ask the Council about the tradeoffs." : "Ask a specialist, compare recommendations and review exact changes before saving simulated work."}
        label={!strategies.length ? 'Compare planting plans' : sessionTasks.some(task=>task.status==='recovery_required') ? 'Compare recovery plans' : sessionTasks.length ? 'Report a result' : approvableProposal ? 'Save simulation plan' : 'Discuss these plans'}
        disabled={Boolean(busy)}
        onAction={()=>{if(!strategies.length)void mutate('Calculating planting plans',value=>planningApi.calculate(value.id,value.revision));else if(sessionTasks.some(task=>task.status==='recovery_required'))setFormOpen(true);else if(sessionTasks.length)jumpToPhase('act');else if(approvableProposal)setActionsOpen(true);else jumpToPhase('discuss')}}
        secondary={strategies.length ? 'Review this plan' : 'Review records'}
        onSecondary={()=>strategies.length?jumpToPhase('decide'):setInboxOpen(true)} />
      <nav className="flow-rail" aria-label="Farm decision workflow">
        {phases.map(([id, label, hint], index) => (
          <button
            key={id}
            className={phase === id ? "is-current" : ""}
            aria-current={phase === id ? "location" : undefined}
            onClick={() => jumpToPhase(id)}
          >
            <b>{index + 1}</b>
            <span>
              {label}
              <small>{hint}</small>
            </span>
          </button>
        ))}
      </nav>
      <p className="flow-navigation-hint" role="status">{navigationHint || "Choose a section to jump to it. Saved milestones below show completed work."}</p>
      {error && (
        <div className="guided-error" role="alert">
          <AlertTriangle size={18} />
          <span>{error}</span>
          <button onClick={() => setError("")} aria-label="Dismiss error">
            <X size={16} />
          </button>
        </div>
      )}
      {session.job?.status === "FAILED" && (
        <div className="guided-error" role="alert">
          <AlertTriangle size={18} />
          <span>
            The calculation did not finish. Your saved inputs remain available.{" "}
            {strategies.length
              ? "Review the inputs with Adjust assumptions before trying again."
              : "Review your records, then try Compare planting plans again."}
          </span>
        </div>
      )}
      {busy && (
        <div className="guided-running" role="status">
          <LoaderCircle className="spin" />
          <span>
            <b>{busy}</b>
            <small>
              Numerical work runs locally. Specialist inference runs only after
              a question is submitted.
            </small>
          </span>
        </div>
      )}
      <CouncilWorkspace session={session} strategy={chosen} busy={Boolean(busy)}
        onReview={()=>void mutate('Reviewing plans with Council',value=>planningApi.review(value.id,value.revision))}
        onSelectStrategy={setSelected}
        onHandoff={source=>{setDiscussionSource(source);setFormOpen(true)}} onError={setError}/>
      <section className="flow-observe" tabIndex={-1}>
        <header>
          <div>
            <p className="kicker">Observe · current farm picture</p>
            <h2>What needs attention today?</h2>
          </div>
          <div className="flow-header-actions">
            <button
              className="button button--cream"
              onClick={() => setInboxOpen(true)}
            >
              <FileSpreadsheet size={17} /> Inbox{" "}
              {workflow.inbox.some((x) => x.status === "candidate") && (
                <span className="notification-dot">!</span>
              )}
            </button>
            <button className="text-button" onClick={() => setMediaOpen(true)}>
              <Play size={16} /> How it works
            </button>
          </div>
        </header>
        {!strategies.length && (
          <div className="flow-callout" tabIndex={-1}>
            <span>
              <Leaf size={22} />
            </span>
            <div>
              <strong>Compare plans against every recorded order</strong>
              <p>
                Calculation is numerical and uses the current records, crop
                cycles and constraints.
              </p>
            </div>
            <button
              className="button button--forest"
              disabled={Boolean(busy)}
              onClick={() =>
                void mutate("Calculating three schedules", (value) =>
                  planningApi.calculate(value.id, value.revision),
                )
              }
            >
              Compare planting plans <ArrowRight size={16} />
            </button>
          </div>
        )}
        <MetricStrip strategy={chosen} session={session} />
        <FarmBoard session={session} crops={crops} strategy={chosen} />
      </section>
      {Boolean(session.result_id) && <SavedConsequence identity={String(session.result_id)+':'+String(workflow.revision)} label={sessionTasks.length ? `${sessionTasks.length} saved simulation tasks` : `${strategies.length} plans ready`} details={`Result ${String(session.result_id).slice(0,8)} · revision ${session.revision}. ${sessionTasks.length ? 'Reports and corrections remain in history.' : 'Projected options. Selecting a candidate does not save or approve it.'}`}/>}
      <MissionProgress session={session} workflow={workflow} />
      {!!strategies.length && (
        <section className="decision-stage" tabIndex={-1}>
          <header>
            <div>
              <p className="kicker">Decide · reviewed proposals</p>
              <h2>Choose what the farm should test</h2>
              <p>
                Every value is projected. Calculate revised plans creates a
                revision-bound proposal; approval is a separate action.
              </p>
            </div>
          </header>
          <div className="proposal-grid">
            {strategies.map((strategy) => (
              <Proposal
                key={strategy.id}
                strategy={strategy}
                selected={strategy.id === selected}
                onSelect={() => setSelected(strategy.id)}
              />
            ))}
          </div>
          {chosen && <PlanBrief strategy={chosen} session={session} crops={crops} />}
          <p className="flow-next-action">{approvableProposal
            ? 'Ready to review approval for this calculated proposal. Approval creates sandbox tasks.'
            : 'Select an option and Adjust assumptions to review it before approval. Council review is optional.'}</p>
          <div className="decision-actions" tabIndex={-1}>
            <div>
              <strong>{chosen?.name} candidate</strong>
              <small>
                Session revision {session.revision} · Council {reviewState}
              </small>
            </div>
            <button
              className="button button--cream"
              onClick={() => setFormOpen(true)}
            >
              <RefreshCw size={16} /> Adjust assumptions
            </button>
            <button
              className="button button--forest"
              disabled={!approvableProposal}
              onClick={() => setActionsOpen(true)}
            >
              <ClipboardCheck size={17} /> Save simulation plan
            </button>
          </div>
        </section>
      )}
      {!!sessionTasks.length && (
        <TaskWorkspace
          tasks={sessionTasks}
          workflow={workflow}
          onRefresh={refreshWorkflow}
          onError={setError}
          onPhase={setPhase}
        />
      )}
      {sessionTasks.some((task) => task.status === "recovery_required") && (
        <section className="recovery-stage" tabIndex={-1}>
          <div>
            <p className="kicker">Replan · recovery path</p>
            <h2>Keep completed work, change only the future</h2>
            <p>
              Reported work and lot origins remain in the ledger. Open the
              proposal editor to change only remaining assumptions.
            </p>
          </div>
          <button
            className="button button--coral"
            onClick={() => setFormOpen(true)}
          >
            <RefreshCw size={17} /> Compare recovery plans
          </button>
        </section>
      )}
      <section className="waste-rescue-card">
        <div>
          <p className="kicker">Waste Rescue</p>
          <h2>Compare a dated surplus before it expires</h2>
          <p>
            Local scenario arithmetic only. A comparison never authorizes a
            sale, donation or disposal.
          </p>
        </div>
        <button
          className="button button--cream"
          onClick={() => setRescueOpen(true)}
        >
          <Recycle size={17} /> Open Waste Rescue
        </button>
      </section>
      {inboxOpen && (
        <Inbox
          session={session}
          workflow={workflow}
          onRefresh={refreshWorkflow}
          onOpenSetup={onOpenSetup}
          onClose={() => setInboxOpen(false)}
        />
      )}
      {mediaOpen && <Explainers onClose={() => setMediaOpen(false)} />}
      {formOpen && chosen && (
        <ProposalEditor
          key={proposalDraftKey}
          draftKey={proposalDraftKey}
          drafts={proposalDrafts}
          session={session}
          strategy={chosen}
          workflow={workflow}
          discussionSource={discussionSource}
          onDone={async () => {
            setFormOpen(false);
            setDiscussionSource(null);
            await refreshWorkflow();
            setSession(await planningApi.get(session.id));
            setPhase("decide");
          }}
          onError={setError}
          onClose={() => setFormOpen(false)}
        />
      )}
      {actionsOpen && (
        <ApprovalDialog
          session={session}
          selected={selected}
          workflow={workflow}
          onDone={async () => {
            setActionsOpen(false);
            await refreshWorkflow();
            setSession(await planningApi.get(session.id));
            setPhase("act");
          }}
          onError={setError}
          onClose={() => setActionsOpen(false)}
        />
      )}
      {rescueOpen && (
        <WasteRescue
          session={session}
          strategy={chosen}
          onError={setError}
          onClose={() => setRescueOpen(false)}
        />
      )}
    </div>
  );
}

function ProposalEditor({
  draftKey,
  drafts,
  session,
  strategy,
  workflow,
  discussionSource,
  onDone,
  onError,
  onClose,
}: {
  draftKey: string;
  drafts: Map<string, ProposalDraft>;
  session: PlanningSession;
  strategy: Strategy;
  workflow: FarmerWorkflowState;
  discussionSource: DiscussionSource | null;
  onDone: () => Promise<void>;
  onError: (v: string) => void;
  onClose: () => void;
}) {
  const start = session.farm.planning_date || session.farm.cutoff.slice(0, 10),
    end = addDays(start, Math.min(55, session.farm.horizon_days - 1)),
    recipes = (Array.isArray(session.farm.recipes) ? session.farm.recipes : []) as Array<{ crop_id: string }>,
    cropIds = Array.from(new Set([
      ...strategy.allocations.map((item) => item.crop_id),
      ...session.farm.orders.map((item) => item.crop_id),
      ...recipes.map((item) => item.crop_id),
    ].filter(Boolean))),
    defaultCrop = cropIds[0] || "caixin";
  const storedPending = readPendingProposal(session.id);
  const savedDraft = storedPending?.draft ?? drafts.get(draftKey);
  const [demand, setDemand] = useState(savedDraft?.demand ?? 100),
    [yieldPct, setYieldPct] = useState(savedDraft?.yieldPct ?? 100),
    [delay, setDelay] = useState(savedDraft?.delay ?? 0),
    [scenarioCrop, setScenarioCrop] = useState(savedDraft?.scenarioCrop ?? defaultCrop),
    [bed, setBed] = useState(savedDraft?.bed ?? ""),
    [reserveStart, setReserveStart] = useState(savedDraft?.reserveStart ?? start),
    [reserveEnd, setReserveEnd] = useState(savedDraft?.reserveEnd ?? (addDays(start, 3) > end ? end : addDays(start, 3))),
    [nursery, setNursery] = useState(savedDraft?.nursery ?? session.farm.resources.nursery_sites),
    [labour, setLabour] = useState(
      savedDraft?.labour ?? session.farm.resources.labour_hours_per_week,
    ),
    [cash, setCash] = useState(savedDraft?.cash ?? session.farm.resources.cash_sgd),
    [orderEnabled, setOrderEnabled] = useState(savedDraft?.orderEnabled ?? false),
    [orderReference, setOrderReference] = useState(savedDraft?.orderReference ?? ""),
    [orderCrop, setOrderCrop] = useState(savedDraft?.orderCrop ?? defaultCrop),
    [orderDueDate, setOrderDueDate] = useState(savedDraft?.orderDueDate ?? (addDays(start, 21) > end ? end : addDays(start, 21))),
    [orderQty, setOrderQty] = useState(savedDraft?.orderQty ?? 0),
    [orderPrice, setOrderPrice] = useState(savedDraft?.orderPrice ?? 8),
    [orderStatus, setOrderStatus] = useState<"confirmed" | "tentative">(savedDraft?.orderStatus ?? "confirmed"),
    [busy, setBusy] = useState(false),
    [pending, setPending] = useState<PendingProposalApply | null>(storedPending),
    [recoveryNotice, setRecoveryNotice] = useState("");
  const currentDraft: ProposalDraft = {
    demand, yieldPct, delay, scenarioCrop, bed, reserveStart, reserveEnd,
    nursery, labour, cash, orderEnabled, orderReference, orderCrop,
    orderDueDate, orderQty, orderPrice, orderStatus,
  };
  useEffect(() => {
    if (pending) return;
    drafts.set(draftKey, {
      demand, yieldPct, delay, scenarioCrop, bed, reserveStart, reserveEnd,
      nursery, labour, cash, orderEnabled, orderReference, orderCrop,
      orderDueDate, orderQty, orderPrice, orderStatus,
    });
  }, [drafts, draftKey, pending, demand, yieldPct, delay, scenarioCrop, bed, reserveStart, reserveEnd,
    nursery, labour, cash, orderEnabled, orderReference, orderCrop, orderDueDate,
    orderQty, orderPrice, orderStatus]);
  const submit = async () => {
    if (pending) return;
    setBusy(true);
    try {
      const assumptions: FarmerAssumptions = {
        tentative_orders:
          orderEnabled && orderStatus === "tentative" && orderQty > 0
            ? [
                {
                  order_id: orderReference.trim(),
                  crop_id: orderCrop,
                  due_date: orderDueDate,
                  quantity_kg: orderQty,
                  price_sgd_per_kg: orderPrice,
                  status: "tentative",
                },
              ]
            : [],
        future_demand: [
          { crop_id: scenarioCrop, start_date: start, end_date: end, percent: demand },
        ],
        seasonal: [
          {
            crop_id: scenarioCrop,
            system: "sheltered_hydroponic",
            start_date: start,
            end_date: end,
            yield_percent: yieldPct,
            delay_days: delay,
            reason: "Farmer-entered planning challenge",
            provenance: "synthetic_assumption",
          },
        ],
        order_changes:
          orderEnabled && orderStatus === "confirmed" && orderQty > 0
            ? [
                {
                  operation: "add",
                  order_id: orderReference.trim(),
                  crop_id: orderCrop,
                  due_date: orderDueDate,
                  quantity_kg: orderQty,
                  price_sgd_per_kg: orderPrice,
                },
              ]
            : [],
        reservations: bed
          ? [{ bed_id: bed, start_date: reserveStart, end_date: reserveEnd }]
          : [],
        capacity: {
          nursery_sites: nursery,
          labour_hours_per_week: labour,
          cash_sgd: cash,
        },
      };
      const sources = workflow.inbox
        .filter((x) => x.status === "confirmed" && x.planning_eligible)
        .map((x) => x.candidate_id);
      const proposal = await farmerWorkflowApi.createProposal(
        session,
        strategy.id,
        assumptions,
        sources,
        discussionSource
          ? {
              conversation_id: discussionSource.conversationId,
              message_id: discussionSource.messageId,
            }
          : undefined,
      );
      const recovery: PendingProposalApply = {
        version: "v22-pending-proposal-apply-v1",
        sessionId: session.id,
        resultId: String(session.result_id || ""),
        baseRevision: session.revision,
        strategyId: strategy.id,
        draftKey,
        draft: currentDraft,
        assumptions,
        proposal,
        createdAt: new Date().toISOString(),
      };
      savePendingProposal(session.id, recovery);
      setPending(recovery);
      await farmerWorkflowApi.applyProposal(proposal);
      savePendingProposal(session.id, null);
      setPending(null);
      drafts.delete(draftKey);
      await onDone();
    } catch (caught) {
      onError(message(caught, "Could not apply the proposal."));
    } finally {
      setBusy(false);
    }
  };
  const reconcilePending = async () => {
    if (!pending || busy) return;
    setBusy(true);
    setRecoveryNotice("");
    try {
      const latest = await farmerWorkflowApi.state();
      const recorded = latest.proposals.find((item) => item.id === pending.proposal.id);
      if (!recorded) {
        setRecoveryNotice("The saved proposal was not found in this farm workspace. No replacement was created; keep this draft and ask an owner to inspect the saved operation.");
        return;
      }
      if (["applied", "approved"].includes(recorded.status)) {
        savePendingProposal(session.id, null);
        setPending(null);
        drafts.delete(pending.draftKey);
        await onDone();
        return;
      }
      if (recorded.status !== "draft") {
        setRecoveryNotice(`Proposal ${recorded.id.slice(0, 8)} is ${recorded.status}. No replacement was created; resolve or discard that server record before editing again.`);
        return;
      }
      await farmerWorkflowApi.applyProposal(recorded);
      savePendingProposal(session.id, null);
      setPending(null);
      drafts.delete(pending.draftKey);
      await onDone();
    } catch (caught) {
      setRecoveryNotice(message(caught, "The saved proposal could not be reconciled. No replacement proposal was created."));
    } finally {
      setBusy(false);
    }
  };
  return (
    <Dialog title="Challenge constraints and recalculate" onClose={onClose}>
      <p className="media-boundary">
        Explicit edits create a draft proposal. Confirmed imports remain
        evidence; they do not silently rewrite demand or yield.
        Unsubmitted edits are saved on this device for this edition, session and
        revision. They never contain credentials and can be discarded below.
      </p>
      {pending && <section className="proposal-recovery" role="status">
        <strong>Revised-plan submission needs reconciliation</strong>
        <p>Proposal {pending.proposal.id.slice(0, 8)} was created for result {pending.resultId.slice(0, 8) || "unknown"}, revision {pending.baseRevision}. Its apply response was not confirmed. The original fields are locked and retained; resuming will inspect this exact proposal and will never create another one.</p>
        {recoveryNotice && <p className="warning-box">{recoveryNotice}</p>}
        <button className="button button--forest" disabled={busy} onClick={() => void reconcilePending()}>{busy ? <LoaderCircle className="spin" /> : <RefreshCw />} Resume / reconcile saved proposal</button>
      </section>}
      {discussionSource && (
        <section className="discussion-handoff">
          <strong>Reviewed advisory context</strong>
          <p>
            Review and enter the exact crop, batch, dates and quantities below.
            Specialist actions are context only; nothing is copied, widened or
            applied automatically.
          </p>
          {discussionSource.actions.length ? (
            <ul>
              {discussionSource.actions.map((action, index) => (
                <li key={`${action.control}-${index}`}>
                  <b>{action.control.replaceAll("_", " ")}</b> · target{" "}
                  {action.target_id || "not specified"} · {action.value}{" "}
                  {action.unit} · {action.status}
                </li>
              ))}
            </ul>
          ) : (
            <p>No structured actions were proposed.</p>
          )}
          <small>
            Conversation {discussionSource.conversationId.slice(0, 8)} ·
            message {discussionSource.messageId.slice(0, 8)}
          </small>
        </section>
      )}
      <fieldset className="proposal-editor-lock" disabled={Boolean(pending)}>
      <div className="assumption-grid">
        <label>
          Crop affected by demand, yield and delay
          <select value={scenarioCrop} onChange={(event) => setScenarioCrop(event.target.value)}>
            {cropIds.map((cropId) => <option key={cropId} value={cropId}>{cropId}</option>)}
          </select>
          <small>Only this crop changes for {civil(start)}–{civil(end)}.</small>
        </label>
        <Range
          label={`Expected demand · current estimate is 100% · ${civil(start)}–${civil(end)}`}
          value={demand}
          setValue={setDemand}
          min={50}
          max={150}
          suffix="%"
        />
        <Range
          label={`Seasonal yield · current estimate is 100% · ${civil(start)}–${civil(end)}`}
          value={yieldPct}
          setValue={setYieldPct}
          min={50}
          max={100}
          suffix="%"
        />
        <Range
          label={`Harvest delay for ${scenarioCrop} · ${civil(start)}–${civil(end)}`}
          value={delay}
          setValue={setDelay}
          min={0}
          max={14}
          suffix=" days"
        />
        <label>
          Reserve a bed
          <select aria-label="Reserve a bed" value={bed} onChange={(e) => setBed(e.target.value)}>
            <option value="">No reservation</option>
            {session.farm.beds.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
        {bed && (
          <>
            <label>
              Reservation starts
              <input
                type="date"
                min={start} max={end}
                value={reserveStart}
                onChange={(e) => setReserveStart(e.target.value)}
              />
            </label>
            <label>
              Reservation ends
              <input
                type="date"
                min={reserveStart || start} max={end}
                value={reserveEnd}
                onChange={(e) => setReserveEnd(e.target.value)}
              />
            </label>
          </>
        )}
        <NumberField
          label="Nursery sites"
          value={nursery}
          setValue={setNursery}
        />
        <NumberField
          label="Labour hours/week"
          value={labour}
          setValue={setLabour}
        />
        <NumberField
          label="Cash capacity (SGD)"
          value={cash}
          setValue={setCash}
        />
        <label className="proposal-order-toggle">
          <input type="checkbox" checked={orderEnabled} onChange={(event) => setOrderEnabled(event.target.checked)} />
          Add an order to this scenario
        </label>
        {orderEnabled && <fieldset className="proposal-order-fields">
          <legend>Order addition</legend>
          <label>Customer / order reference<input required value={orderReference} onChange={(event) => setOrderReference(event.target.value)} /></label>
          <label>Crop<select value={orderCrop} onChange={(event) => setOrderCrop(event.target.value)}>{cropIds.map((cropId) => <option key={cropId} value={cropId}>{cropId}</option>)}</select></label>
          <label>Due date<input type="date" min={start} max={end} value={orderDueDate} onChange={(event) => setOrderDueDate(event.target.value)} /></label>
          <NumberField label="Quantity (kg)" value={orderQty} setValue={setOrderQty} />
          <NumberField label="Price (SGD/kg)" value={orderPrice} setValue={setOrderPrice} />
          <label>Status<select value={orderStatus} onChange={(event) => setOrderStatus(event.target.value as "confirmed" | "tentative")}><option value="confirmed">Confirmed commitment</option><option value="tentative">Tentative scenario evidence</option></select></label>
        </fieldset>}
      </div>
      <section className="proposal-review" aria-label="Exact changes to calculate">
        <h3>Review exact changes</h3>
        <ul>
          <li><b>{scenarioCrop}</b> demand {demand}% of the current estimate and yield {yieldPct}% of the current estimate from {civil(start)} to {civil(end)}.</li>
          <li><b>{scenarioCrop}</b> harvest dates move {delay ? `${delay} days later` : "0 days (unchanged)"} within that period.</li>
          <li>Capacity: {num(nursery)} nursery sites, {num(labour)} labour hours/week and SGD {num(cash)} cash.</li>
          <li>{bed ? `${session.farm.beds.find((item) => item.id === bed)?.name || bed} reserved ${civil(reserveStart)}–${civil(reserveEnd)}.` : "No bed reservation added."}</li>
          <li>{orderEnabled ? `${orderStatus === "confirmed" ? "Confirmed" : "Tentative"} order ${orderReference || "(reference required)"}: ${num(orderQty)} kg ${orderCrop}, due ${civil(orderDueDate)}, SGD ${num(orderPrice)}/kg.` : "No order added."}</li>
        </ul>
        <p>Past recorded work stays unchanged. The server will validate these assumptions and calculate a new revision; this does not approve tasks.</p>
      </section>
      </fieldset>
      <div className="proposal-editor-actions">
      <button
        className="button button--forest"
        disabled={busy || Boolean(pending) || Boolean(bed && (!reserveStart || reserveStart < start || reserveEnd < reserveStart || reserveEnd > end)) || (orderEnabled && (!orderReference.trim() || orderQty <= 0 || orderPrice < 0 || !orderDueDate || orderDueDate < start || orderDueDate > end))}
        onClick={() => void submit()}
      >
        {busy ? <LoaderCircle className="spin" /> : <RefreshCw />} Calculate revised plans
      </button>
      <button className="text-button" disabled={busy || Boolean(pending)} onClick={() => { drafts.delete(draftKey); onClose(); }}>Discard saved draft</button>
      </div>
    </Dialog>
  );
}

function ApprovalDialog({
  session,
  selected,
  workflow,
  onDone,
  onError,
  onClose,
}: {
  session: PlanningSession;
  selected: string;
  workflow: FarmerWorkflowState;
  onDone: () => Promise<void>;
  onError: (v: string) => void;
  onClose: () => void;
}) {
  const proposal = currentAppliedProposal(session, workflow, selected),
    councilState = reviewStatus(session, normalizedFindings(session)),
    [busy, setBusy] = useState(false);
  const approve = async () => {
    if (!proposal) return;
    setBusy(true);
    try {
      await farmerWorkflowApi.approve(proposal);
      await onDone();
    } catch (caught) {
      onError(message(caught, "Could not approve this recalculated proposal."));
    } finally {
      setBusy(false);
    }
  };
  return (
    <Dialog title="Save simulation plan" onClose={onClose}>
      <p>
        Approval is bound to proposal revision{" "}
        {proposal?.proposal_revision ?? "—"} and creates simulation tasks only.
        Real operations remain disabled.
      </p>
      <p className="warning-box">
        Council evidence: <strong>{councilState}</strong>. The Council is
        advisory and {councilState === "awaiting" ? "was not requested" : "does not replace your decision"}.
        Approval relies on the completed numerical checks shown below and your
        explicit confirmation.
      </p>
      {proposal ? (
        <>
          <MetricValues values={proposal.calculated_metrics} />
          <button
            className="button button--forest"
            disabled={busy}
            onClick={() => void approve()}
          >
            <ClipboardCheck /> Confirm simulation plan
          </button>
        </>
      ) : (
        <p className="warning-box">
          Apply and finish a recalculation before approval. The current
          numerical result is not implicitly approved.
        </p>
      )}
    </Dialog>
  );
}

function currentAppliedProposal(
  session: PlanningSession,
  workflow: FarmerWorkflowState,
  selected: string,
) {
  if (
    !session.result_id ||
    !["COMPLETED", "SUCCEEDED"].includes(
      String(session.job?.status || session.status).toUpperCase(),
    )
  )
    return undefined;
  return [...workflow.proposals].reverse().find(
    (proposal) =>
      proposal.session_id === session.id &&
      (proposal.selected_strategy_id === selected || proposal.approval?.strategy_id === selected) &&
      proposal.approval?.available === true &&
      proposal.status === "applied" &&
      proposal.recalculation_job?.id === session.result_id,
  );
}

function TaskWorkspace({
  tasks,
  workflow,
  onRefresh,
  onError,
  onPhase,
}: {
  tasks: FarmerTask[];
  workflow: FarmerWorkflowState;
  onRefresh: () => Promise<FarmerWorkflowState>;
  onError: (v: string) => void;
  onPhase: (v: Phase) => void;
}) {
  const [selected, setSelected] = useState(
      tasks.find((x) =>
        ["pending", "in_progress", "recovery_required"].includes(x.status),
      )?.id || tasks[0].id,
    ),
    task = tasks.find((x) => x.id === selected) || tasks[0];
  const [status, setStatus] = useState<"completed" | "failed">("completed"),
    [quantity, setQuantity] = useState(
      task.actual_quantity == null
        ? Number(task.planned_quantity || 0)
        : Number(task.actual_quantity),
    ),
    [rejectedQuantity, setRejectedQuantity] = useState(0),
    [note, setNote] = useState(""),
    [checks, setChecks] = useState<string[]>([]),
    [photo, setPhoto] = useState(""),
    [correction, setCorrection] = useState(""),
    [reason, setReason] = useState(""),
    [busy, setBusy] = useState(false);
  const confirmedPhotos = workflow.inbox.filter(
    (x) => x.status === "confirmed" && x.source_kind === "photo_observation",
  );
  useEffect(() => {
    setQuantity(
      task.actual_quantity == null
        ? Number(task.planned_quantity || 0)
        : Number(task.actual_quantity),
    );
    setChecks([]);
  }, [task.id, task.actual_quantity, task.planned_quantity]);
  const save = async () => {
    setBusy(true);
    try {
      await farmerWorkflowApi.taskResult(
        task,
        status,
        task.unit ? quantity : null,
        task.action === "delivery" ? rejectedQuantity : null,
        note,
        checks,
        photo || null,
      );
      await onRefresh();
      onPhase(status === "failed" ? "replan" : "verify");
    } catch (caught) {
      onError(message(caught, "Could not save the reported result."));
    } finally {
      setBusy(false);
    }
  };
  const correct = async () => {
    setBusy(true);
    try {
      await farmerWorkflowApi.correctTask(
        task,
        "actual_quantity",
        Number(correction),
        reason,
      );
      await onRefresh();
    } catch (caught) {
      onError(message(caught, "Could not save the auditable correction."));
    } finally {
      setBusy(false);
    }
  };
  return (
    <section className="action-stage" tabIndex={-1}>
      <header>
        <div>
          <p className="kicker">Act → Verify</p>
          <h2>Simulation action ledger</h2>
          <p>
            Planned quantities are projected. Actual quantities and notes are
            farmer-reported and unverified.
          </p>
        </div>
        <span className="mode-label">SIMULATED ACTIONS</span>
      </header>
      <div className="action-layout">
        <div className="task-list">
          {tasks.map((item, index) => (
            <button
              type="button"
              key={item.id}
              data-task-id={item.id}
              onClick={() => setSelected(item.id)}
            >
              <article>
                <span>{index + 1}</span>
                <div>
                  <b>
                    {item.action} · {item.crop_id} · {item.location}
                  </b>
                  <small>
                    Due {civil(item.due_date)} ·{" "}
                    {item.planned_quantity == null
                      ? "no quantity"
                      : `${num(item.planned_quantity)} ${item.unit}`}
                  </small>
                </div>
                <em>{item.status}</em>
              </article>
            </button>
          ))}
        </div>
        <div className="task-result-panel" tabIndex={-1}>
          <form
            className="result-form"
            onSubmit={(e) => {
              e.preventDefault();
              void save();
            }}
          >
            <label>
              Result
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value as typeof status)}
              >
                <option value="completed">Completed</option>
                <option value="failed">Blocked or failed</option>
              </select>
            </label>
            {task.unit && (
              <NumberField
                label={`Actual quantity (${task.unit})`}
                value={quantity}
                setValue={setQuantity}
              />
            )}
            {task.action === "delivery" && (
              <NumberField
                label="Rejected quantity (kg)"
                value={rejectedQuantity}
                setValue={setRejectedQuantity}
              />
            )}
            <fieldset>
              <legend>Checklist completed</legend>
              {task.checklist.map((item) => (
                <label key={item}>
                  <input
                    type="checkbox"
                    checked={checks.includes(item)}
                    onChange={(e) =>
                      setChecks((old) =>
                        e.target.checked
                          ? [...old, item]
                          : old.filter((x) => x !== item),
                      )
                    }
                  />
                  {item}
                </label>
              ))}
            </fieldset>
            {confirmedPhotos.length > 0 && (
              <label>
                Reviewed task photo
                <select
                  value={photo}
                  onChange={(e) => setPhoto(e.target.value)}
                >
                  <option value="">No photo</option>
                  {confirmedPhotos.map((item) => (
                    <option key={item.candidate_id} value={item.candidate_id}>
                      {item.source_name}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <label>
              Farmer note
              <textarea
                required
                value={note}
                onChange={(e) => setNote(e.target.value)}
              />
            </label>
            <button className="button button--coral" disabled={busy}>
              <PackageCheck /> Save reported result
            </button>
          </form>
          {task.event_revision > 0 && (
            <form
              className="result-form correction-form"
              onSubmit={(e) => {
                e.preventDefault();
                void correct();
              }}
            >
              <strong>Correct a reported quantity</strong>
              <NumberField
                label="Corrected quantity"
                value={Number(correction || 0)}
                setValue={(v) => setCorrection(String(v))}
              />
              <label>
                Reason
                <input
                  required
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                />
              </label>
              <button className="button button--cream" disabled={busy}>
                Save auditable correction
              </button>
            </form>
          )}
        </div>
      </div>
    </section>
  );
}

function WasteRescue({
  session,
  strategy,
  onError,
  onClose,
}: {
  session: PlanningSession;
  strategy?: Strategy;
  onError: (v: string) => void;
  onClose: () => void;
}) {
  const [sale, setSale] = useState(8),
    [rescue, setRescue] = useState(3),
    [cost, setCost] = useState(0.5),
    [selectedLot, setSelectedLot] = useState(""),
    [result, setResult] = useState<Awaited<
      ReturnType<typeof farmerWorkflowApi.wasteRescue>
    > | null>(null);
  const run = async () => {
    try {
      const resultId = String(session.result_id || "");
      if (!resultId || !strategy)
        throw new Error(
          "A frozen calculated result and strategy are required.",
        );
      setResult(
        await farmerWorkflowApi.wasteRescue({
          session_id: session.id,
          result_id: resultId,
          strategy_id: strategy.id,
          ...(selectedLot ? { lot_id: selectedLot } : {}),
          sale_price_sgd_per_kg: sale,
          rescue_price_sgd_per_kg: rescue,
          rescue_cost_sgd_per_kg: cost,
        }),
      );
    } catch (caught) {
      onError(message(caught, "Could not compare Waste Rescue scenarios."));
    }
  };
  return (
    <Dialog title="Waste Rescue comparison" onClose={onClose}>
      <p className="media-boundary">
        The server derives quantity and expiry from this frozen projected
        terminal stock. Price and cost fields are hypothetical scenario
        assumptions.
      </p>
      <div className="assumption-grid">
        <NumberField
          label="Planned sale price/kg"
          value={sale}
          setValue={setSale}
        />
        <NumberField
          label="Rescue price/kg"
          value={rescue}
          setValue={setRescue}
        />
        <NumberField label="Rescue cost/kg" value={cost} setValue={setCost} />
      </div>
      <button className="button button--forest" onClick={() => void run()}>
        <Recycle /> Compare frozen surplus locally
      </button>
      {result && (
        <>
          <p>
            {result.quantity_kg} kg projected terminal stock · expires{" "}
            {civil(result.expires_on)} · {result.days_remaining} days from
            projected horizon close
          </p>
          <p className="media-boundary">
            As of {civil(result.as_of)} ({result.as_of_basis}).{" "}
            {result.selection_basis ===
            "all_terminal_lots_aggregated_using_earliest_actual_expiry"
              ? "Mixed projected lots use the conservative earliest actual expiry."
              : "One exact projected terminal lot is selected."}{" "}
            This does not imply stock exists today.
          </p>
          {!!result.surplus_lots.length && (
            <div className="surplus-lot-list">
              <strong>Projected terminal lots</strong>
              {result.surplus_lots.map((lot) => (
                <button
                  type="button"
                  className={selectedLot === lot.lot_id ? "is-selected" : ""}
                  key={lot.lot_id}
                  onClick={() => setSelectedLot(lot.lot_id)}
                >
                  <span>
                    {lot.crop_id} · {lot.quantity_kg} kg
                  </span>
                  <small>
                    Expires {civil(lot.expires_on)} · {lot.origin}
                  </small>
                </button>
              ))}
              {selectedLot && (
                <button
                  className="text-button"
                  onClick={() => setSelectedLot("")}
                >
                  Compare all lots
                </button>
              )}
            </div>
          )}
          <div className="proposal-grid">
            {result.scenarios.map((item) => (
              <article className="proposal-card" key={item.id}>
                <h3>{item.id.replaceAll("_", " ")}</h3>
                <p>{item.rescued_kg} kg rescued</p>
                <strong>SGD {num(item.projected_margin_sgd)}</strong>
                <small> · Δ SGD {num(item.margin_delta_sgd)}</small>
              </article>
            ))}
          </div>
          <p className="council-boundary">
            Basis: {result.basis}. Frozen result {result.binding.result_id}.
            This comparison authorizes no operation.
          </p>
        </>
      )}
    </Dialog>
  );
}

function Inbox({
  session,
  workflow,
  onRefresh,
  onOpenSetup,
  onClose,
}: {
  session: PlanningSession;
  workflow: FarmerWorkflowState;
  onRefresh: () => Promise<FarmerWorkflowState>;
  onOpenSetup: () => void;
  onClose: () => void;
}) {
  const [file, setFile] = useState<File | null>(null),
    [busy, setBusy] = useState(false),
    [manualOpen, setManualOpen] = useState(false),
    [manualName, setManualName] = useState("Farmer manual record"),
    [manualDate, setManualDate] = useState(session.farm.planning_date),
    [manualKind, setManualKind] = useState("expense"),
    [manualReference, setManualReference] = useState(`manual-${Date.now()}`),
    [manualTarget, setManualTarget] = useState(""),
    [manualDescription, setManualDescription] = useState(""),
    [manualAmount, setManualAmount] = useState("");
  const upload = async () => {
    if (!file) return;
    setBusy(true);
    try {
      const kind = file.type.startsWith("image/")
        ? "photo_observation"
        : /\.(csv|xlsx|xls)$/i.test(file.name)
          ? "accounting_export"
          : "document_extraction";
      const saved = await farmerWorkflowApi.upload(file, kind);
      void saved;
      await onRefresh();
    } finally {
      setBusy(false);
    }
  };
  const review = async (id: string, decision: "confirm" | "reject") => {
    setBusy(true);
    try {
      await farmerWorkflowApi.reviewImport(id, decision);
      await onRefresh();
    } finally {
      setBusy(false);
    }
  };
  const createManual = async () => {
    if (
      !manualName.trim() ||
      !manualReference.trim() ||
      !manualAmount ||
      (manualKind === "correction" && !manualTarget.trim())
    )
      return;
    setBusy(true);
    try {
      await farmerWorkflowApi.manualImport(manualName.trim(), [
        {
          date: manualDate,
          kind: manualKind,
          reference: manualReference.trim(),
          corrects_reference:
            manualKind === "correction" ? manualTarget.trim() : undefined,
          description: manualDescription.trim(),
          amount: manualAmount,
          currency: "SGD",
          provenance: "farmer_manual_unverified",
        },
      ]);
      await onRefresh();
      setManualAmount("");
      setManualTarget("");
      setManualDescription("");
      setManualReference(`manual-${Date.now()}`);
      setManualOpen(false);
    } finally {
      setBusy(false);
    }
  };
  return (
    <Dialog title="Farm Inbox" onClose={onClose}>
      <div className="inbox-default">
        <FileSpreadsheet />
        <div>
          <strong>Singapore leafy greens demo records</strong>
          <p>
            {session.farm.orders.length} orders · {session.farm.beds.length}{" "}
            beds · synthetic default
          </p>
          <small>
            Reviewed demonstration fixture; no real-farm provenance claim.
          </small>
        </div>
        <span>ACTIVE</span>
      </div>
      {workflow.inbox.map((item) => (
        <article className="upload-review" key={item.candidate_id}>
          <strong>
            {item.source_name} · {item.status}
          </strong>
          <p>
            {item.source_kind} · {item.authority || "review candidate"} ·{" "}
            {item.rows?.length || 0} extracted rows
          </p>
          <details className="candidate-review" open={item.status === "candidate"}>
            <summary>Review extracted evidence</summary>
            <dl>
              <div><dt>Provenance</dt><dd>{reviewValue(item.provenance || item.source_sha256 || item.sha256 || "Not supplied")}</dd></div>
              <div><dt>Authority</dt><dd>{String(item.authority || "review candidate")}</dd></div>
              <div><dt>Current planning authority</dt><dd>{item.status === "candidate" ? "Not active; confirmation required" : item.planning_eligible === true ? "Eligible reviewed evidence" : "Observation only"}</dd></div>
            </dl>
            {!!item.warnings?.length && (
              <div className="candidate-warnings"><strong>Warnings</strong><ul>{item.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></div>
            )}
            {!!item.rows?.length ? (
              <div className="candidate-rows" role="region" aria-label={`${item.source_name} extracted fields`}>
                {item.rows.map((row, rowIndex) => (
                  <article key={rowIndex}>
                    <strong>Record {rowIndex + 1}</strong>
                    <dl>{Object.entries(row).map(([field, value]) => <div key={field}><dt>{field.replaceAll("_", " ")}</dt><dd>{reviewValue(value)}</dd></div>)}</dl>
                  </article>
                ))}
              </div>
            ) : <p>No structured rows were extracted. Review the observation metadata and warnings before deciding.</p>}
          </details>
          {item.status === "candidate" && (
            <div className="guided-buttons">
              <button
                className="button button--cream"
                disabled={busy}
                onClick={() => void review(item.candidate_id, "reject")}
              >
                Reject
              </button>
              <button
                className="button button--forest"
                disabled={busy}
                onClick={() => void review(item.candidate_id, "confirm")}
              >
                Confirm reviewed fields
              </button>
            </div>
          )}
        </article>
      ))}
      <div className="sandbox-upload">
        <h3>Optional sandbox upload</h3>
        <p>
          CSV, XLSX, document or photo files remain candidates until explicit
          review. Documents and photos are observations and never yield
          authority.
        </p>
        <label>
          <Upload />
          <span>{file?.name || "Choose a sandbox file"}</span>
          <input
            type="file"
            accept=".csv,.xlsx,.xls,.doc,.docx,.pdf,image/*"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
        </label>
        <button
          className="button button--cream"
          disabled={!file || busy}
          onClick={() => void upload()}
        >
          Upload candidate
        </button>
        <button className="text-button" onClick={() => setManualOpen((value) => !value)}>
          {manualOpen ? "Close manual entry" : "Open manual entry"} <ArrowRight />
        </button>
        {manualOpen && (
          <form className="manual-candidate" onSubmit={(event) => { event.preventDefault(); void createManual(); }}>
            <strong>Create an unverified manual candidate</strong>
            <p>Review and confirm it in this Inbox before it can support planning.</p>
            <label>Source name<input required value={manualName} onChange={(event) => setManualName(event.target.value)} /></label>
            <label>Record date<input required type="date" value={manualDate} onChange={(event) => setManualDate(event.target.value)} /></label>
            <label>Record kind<select value={manualKind} onChange={(event) => setManualKind(event.target.value)}><option value="expense">Expense</option><option value="sale">Sale</option><option value="correction">Correction</option></select></label>
            <label>Record reference<input required value={manualReference} onChange={(event) => setManualReference(event.target.value)} /></label>
            {manualKind === "correction" && <label>Target transaction reference<input required value={manualTarget} onChange={(event) => setManualTarget(event.target.value)} /></label>}
            <label>Description (optional)<input value={manualDescription} onChange={(event) => setManualDescription(event.target.value)} /></label>
            <label>{manualKind === "correction" ? "Signed correction amount (SGD)" : "Amount (SGD)"}<input required type="number" min={manualKind === "correction" ? undefined : "0"} step="0.01" value={manualAmount} onChange={(event) => setManualAmount(event.target.value)} /></label>
            {manualKind === "correction" && <p className="tentative-disclosure">Enter a signed delta. Positive raises the target sale or expense; negative lowers it. The target must be one distinct reviewed sale or expense reference.</p>}
            <button className="button button--cream" disabled={busy}>Create review candidate</button>
          </form>
        )}
      </div>
    </Dialog>
  );
}

function MissionProgress({
  session,
  workflow,
}: {
  session: PlanningSession;
  workflow: FarmerWorkflowState;
}) {
  const resultId = String(session.result_id || ""),
    findings = normalizedFindings(session),
    reviewHistory = Array.isArray(session.review_history)
      ? (session.review_history as Array<Record<string, unknown>>)
      : [],
    completedReview = [...reviewHistory]
      .reverse()
      .find((item) =>
        ["completed", "partial", "succeeded"].includes(
          String(item.status || "").toLowerCase(),
        ),
      ),
    reviewReady =
      findings.length > 0 &&
      findings.some((item) => item.truth === "validated" || item.truth === "partial") &&
      !["blocked", "failed", "withheld"].includes(
        String(session.review?.status || "").toLowerCase(),
      ),
    sessionProposals = workflow.proposals.filter(
      (item) => item.session_id === session.id,
    ),
    proposal = [...sessionProposals]
      .reverse()
      .find((item) => ["applied", "approved"].includes(item.status)),
    recalculationComplete = Boolean(
      proposal &&
        proposal.recalculation_job?.id === resultId &&
        ["completed", "succeeded"].includes(
          String(session.job?.status || session.status).toLowerCase(),
        ),
    ),
    approved = sessionProposals.find((item) => item.status === "approved"),
    proposalIds = new Set(sessionProposals.map((item) => item.id)),
    sessionTasks = workflow.tasks.filter((item) => proposalIds.has(item.proposal_id)),
    reported = sessionTasks.filter((item) => item.event_revision > 0),
    recovery = workflow.tasks.filter(
      (item) => proposalIds.has(item.proposal_id) && item.status === "recovery_required",
    ),
    chosen = session.result?.strategies?.find(
      (item) => item.id === session.selected_strategy_id,
    ),
    priorMargin = Number(chosen?.metrics?.margin_sgd),
    calculatedMargin = Number(proposal?.calculated_metrics?.margin_sgd),
    marginDelta = calculatedMargin - priorMargin,
    outcomeEarned = recalculationComplete && Number.isFinite(marginDelta) && marginDelta !== 0;
  const milestones = [
    {
      label: "Options calculated",
      done: Boolean(resultId),
      evidence: resultId || "Awaiting numerical result",
      basis: "projected",
    },
    {
      label: "Council reviewed",
      done: reviewReady,
      evidence: reviewReady
        ? `review ${String(completedReview?.job_id || completedReview?.id || session.review?.id || session.revision)}`
        : "Explicit review not requested",
      basis: "advisory",
    },
    {
      label: "Proposal applied",
      done: recalculationComplete,
      evidence: recalculationComplete
        ? `${proposal?.id} · recalculation ${proposal?.recalculation_job?.id || "completed"}`
        : "No applied proposal with completed recalculation",
      basis: "projected",
    },
    {
      label: "Actions approved",
      done: Boolean(approved),
      evidence: approved?.id || "No approved revision",
      basis: "simulated",
    },
    {
      label: "Results reported",
      done: reported.length > 0,
      evidence: reported.length
        ? `${reported.length} task event${reported.length === 1 ? "" : "s"}`
        : "No farmer report",
      basis: "user-reported",
    },
    {
      label: "Attention required",
      done: recovery.length > 0,
      evidence: recovery.length
        ? recovery.map((item) => item.id).join(", ")
        : "No evidenced recovery trigger",
      basis: "user-reported",
    },
    {
      label: "Calculated outcome",
      done: outcomeEarned,
      evidence: outcomeEarned
        ? `Projected contribution margin ${marginDelta > 0 ? "+" : ""}SGD ${num(marginDelta)}`
        : "Awaiting a calculated change in coverage, waste or margin",
      basis: "projected",
    },
  ];
  return (
    <section
      className="mission-progress"
      aria-label="Singapore Demo Farm mission"
    >
      <header>
        <div>
          <p className="kicker">Connected Singapore Demo Farm mission</p>
          <h2>Evidence-earned outcomes</h2>
          <p>
            Badges unlock from persisted result, review, proposal and task IDs.
            Opening a panel earns nothing.
          </p>
        </div>
        <strong>
          {milestones.filter((item) => item.done).length}/{milestones.length}{" "}
          evidenced
        </strong>
      </header>
      <div>
        {milestones.map((item, index) => (
          <article className={item.done ? "is-earned" : ""} key={item.label}>
            <span>{item.done ? <Check size={16} /> : index + 1}</span>
            <b>{item.label}</b>
            <small>{item.evidence}</small>
            <em>{item.basis}</em>
          </article>
        ))}
      </div>
    </section>
  );
}

function PlanBrief({strategy, session, crops}: {strategy:Strategy;session:PlanningSession;crops:Crop[]}) {
  const beds = new Set(strategy.allocations.map(item => item.bed_id));
  const [cropFilter, setCropFilter] = useState(""),
    [bedFilter, setBedFilter] = useState(""),
    [dateFrom, setDateFrom] = useState(""),
    [dateTo, setDateTo] = useState("");
  const schedule = strategy.allocations.filter((item) =>
    (!cropFilter || item.crop_id === cropFilter) &&
    (!bedFilter || item.bed_id === bedFilter) &&
    (!dateFrom || item.harvest_date >= dateFrom) &&
    (!dateTo || item.sow_date <= dateTo));
  const current = metricValues(strategy);
  const alternatives = (session.result?.strategies || []).filter((item) => item.id !== strategy.id);
  const signed = (value: number | null, unit: string) => value === null ? "Unknown" : `${value > 0 ? "+" : value < 0 ? "−" : "±"}${num(Math.abs(value))}${unit}`;
  return <section className="v12-plan-brief" aria-label="Selected plan details" data-preview-strategy={strategy.id}>
    <h3>{strategy.name} · projected plan</h3>
    <p>{strategy.allocations.length} dated allocations across {beds.size} beds. Selecting a candidate changes this preview only; it does not save assumptions or approve work.</p>
    <p><b>{current.requested === null ? "Unknown requested kg" : `${num(current.delivered)} of ${num(current.requested)} kg fulfilled`}</b> for {civil(session.farm.planning_date || session.farm.cutoff)}–{civil(addDays(session.farm.planning_date || session.farm.cutoff, session.farm.horizon_days - 1))}; {current.shortfall === null ? "shortfall unknown" : `${num(current.shortfall)} kg shortfall`}.</p>
    <p>{strategy.violations.length ? `${strategy.violations.length} declared constraint${strategy.violations.length === 1 ? " is" : "s are"} flagged.` : "Feasible within the modeled resource, timing and inventory limits."} This does not mean every order is fulfilled or that unmodeled farm conditions are safe. Contribution margin is projected revenue minus modeled variable costs, not net profit.</p>
    {!!alternatives.length && <div className="strategy-differences" aria-label={`Differences from ${strategy.name}`}>
      <strong>Difference if you choose another plan</strong>
      {alternatives.map((alternative) => {
        const other = metricValues(alternative);
        return <p key={alternative.id}><b>{alternative.name}</b>: {signed(other.delivered === null || current.delivered === null ? null : other.delivered - current.delivered, " kg fulfilled")} · {signed(other.shortfall === null || current.shortfall === null ? null : other.shortfall - current.shortfall, " kg shortfall")} · {signed(other.expiry === null || current.expiry === null ? null : other.expiry - current.expiry, " kg expiry")} · {signed(other.margin === null || current.margin === null ? null : other.margin - current.margin, " SGD contribution margin")}</p>;
      })}
    </div>}
    <details><summary>View full dated schedule and evidence</summary>
      <p>Session revision {session.revision} · result {String(session.result_id || 'not supplied')}</p>
      <div className="schedule-filters" aria-label="Schedule filters">
        <label>Crop<select value={cropFilter} onChange={(event) => setCropFilter(event.target.value)}><option value="">All crops</option>{Array.from(new Set(strategy.allocations.map((item) => item.crop_id))).map((id) => <option key={id} value={id}>{crops.find((crop) => crop.id === id)?.label || id}</option>)}</select></label>
        <label>Bed<select value={bedFilter} onChange={(event) => setBedFilter(event.target.value)}><option value="">All beds</option>{Array.from(beds).map((id) => <option key={id} value={id}>{session.farm.beds.find((bed) => bed.id === id)?.name || id}</option>)}</select></label>
        <label>Active on/after<input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} /></label>
        <label>Active on/before<input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} /></label>
      </div>
      <p>{schedule.length} of {strategy.allocations.length} complete schedule rows shown.</p>
      <ol>{schedule.map((item,index) => <li key={item.id || index}>
        <strong>{session.farm.beds.find(bed=>bed.id===item.bed_id)?.name || item.bed_id} · {crops.find(crop=>crop.id===item.crop_id)?.label || item.crop_id}</strong>
        <span>Sow {item.sow_date} → transplant {item.transplant_date} → harvest {item.harvest_date}</span>
        <span>{num(item.expected_kg)} kg projected · {num(item.area_m2)} m²</span>
      </li>)}</ol>
      {!schedule.length && <p>No schedule rows match these filters.</p>}
    </details>
  </section>;
}

function FarmBoard({
  session,
  crops,
  strategy,
}: {
  session: PlanningSession;
  crops: Crop[];
  strategy?: Strategy;
}) {
  const batches = (Array.isArray(session.farm.batches) ? session.farm.batches : []) as Array<{bed_id:string;recipe_id?:string;crop_id?:string;stage?:string}>;
  const recipes = (Array.isArray(session.farm.recipes) ? session.farm.recipes : []) as Array<{id:string;crop_id:string}>;
  const alloc = new Map<string, Strategy['allocations']>();
  for (const item of [...(strategy?.allocations || [])].sort((a,b) => a.sow_date.localeCompare(b.sow_date))) {
    alloc.set(item.bed_id, [...(alloc.get(item.bed_id) || []), item]);
  }
  // A selected strategy is always a preview. Only a new server revision may
  // briefly mark the beds whose recorded plan changed, so the scene never
  // implies that simply browsing has changed the farm.
  const allocationSignature = [...alloc.entries()]
    .map(([bedId, cycles]) => `${bedId}:${cycles.map((item) => `${item.crop_id}/${item.sow_date}/${item.harvest_date}`).join(',')}`)
    .sort()
    .join('|');
  const previous = useRef<{revision:number; allocations:Map<string,string>} | undefined>(undefined);
  const [affectedBeds, setAffectedBeds] = useState<Set<string>>(() => new Set());
  useEffect(() => {
    const next = new Map(allocationSignature.split('|').filter(Boolean).map((entry) => {
      const [bedId, value = ''] = entry.split(':', 2);
      return [bedId, value];
    }));
    const before = previous.current;
    if (before && before.revision !== session.revision) {
      const ids = new Set([...before.allocations.keys(), ...next.keys()]);
      const changed = new Set([...ids].filter((id) => before.allocations.get(id) !== next.get(id)));
      setAffectedBeds(changed);
      const timer = window.setTimeout(() => setAffectedBeds(new Set()), 550);
      previous.current = {revision: session.revision, allocations: next};
      return () => window.clearTimeout(timer);
    }
    previous.current = {revision: session.revision, allocations: next};
  }, [allocationSignature, session.revision]);
  return (
    <div className="living-board" data-preview-strategy={strategy?.id || ""}>
      <div className="living-board__beds">
        {session.farm.beds.map((bed) => {
          const cycles = alloc.get(bed.id) || [], item = cycles[0];
          const batch = batches.find(record => record.bed_id === bed.id);
          const cropId = item?.crop_id || batch?.crop_id || recipes.find(recipe => recipe.id === batch?.recipe_id)?.crop_id || bed.crop_id;
          const stage = item ? 'planned' : batch?.stage || bed.stage || (cropId ? 'recorded batch' : 'empty');
          const crop = crops.find(x => x.id === cropId);
          return (
            <article key={bed.id} className={affectedBeds.has(bed.id) ? "is-affected" : ""} data-affected={affectedBeds.has(bed.id) || undefined}>
              <CropArt
                cropId={cropId}
                color={crop?.color}
                stage={item ? "seedling" : ["harvested", "sanitation", "empty"].includes(stage) ? "empty" : stage === "ready" ? "ready" : stage === "nursery" ? "seedling" : "growing"}
                compact
              />
              <span>
                <b>{bed.name}</b>
                <small>
                  {crop?.label || cropId || 'No recorded crop'} · {item ? 'preview' : stage}
                </small>
                {item && <small>{item.sow_date} → {item.harvest_date}{cycles.length > 1 ? ` · ${cycles.length} cycles` : ''}</small>}
              </span>
            </article>
          );
        })}
      </div>
      <aside>
        <p className="kicker">{strategy ? `${strategy.name} · planning preview` : "Recorded farm snapshot"}</p>
        <strong>
          {session.farm.beds.length} beds ·{" "}
          {num(
            session.farm.beds.reduce(
              (total, bed) => total + Number(bed.area_m2 || 0),
              0,
            ),
          )}{" "}
          m²
        </strong>
        <span>
          Cash <b>SGD {num(session.farm.resources.cash_sgd)}</b>
        </span>
        <span>
          Labour{" "}
          <b>{num(session.farm.resources.labour_hours_per_week)} h/week</b>
        </span>
        <span>
          Horizon <b>{session.farm.horizon_days} days</b>
        </span>
        <small>{strategy ? "Projected allocations, not live growth. Selecting an option does not save or approve work; see its full schedule below." : "Saved synthetic records. No crop is inferred where records are missing."}</small>
      </aside>
    </div>
  );
}
function MetricStrip({
  strategy,
  session,
}: {
  strategy?: Strategy;
  session: PlanningSession;
}) {
  const m = metricValues(strategy),
    reported = session.reported_forecast as
      { metrics?: Record<string, unknown> } | undefined,
    reportedRequested = Number(reported?.metrics?.booked_requested_kg || 0),
    reportedDelivered = Number(reported?.metrics?.booked_delivered_kg || 0),
    rows = [
      ["Booked coverage", m.coverage, "%"],
      ["Surplus", m.surplus, "kg"],
      ["Expiry", m.expiry, "kg"],
      ["Rejection", m.rejection, "kg"],
      ["Margin", m.margin, "SGD"],
      ["Waste Rescue", m.rescue, "kg"],
    ];
  return (
    <div className="metric-strip">
      {rows.map(([label, value, unit]) => (
        <article key={String(label)}>
          <small>{label}</small>
          <strong>
            {!strategy ? "Not calculated" : value === null ? "Unknown" : `${num(value)} ${unit}`}
          </strong>
          <span>Projected</span>
        </article>
      ))}
      <article className="metric-strip__coverage">
        <small>Confirmed orders · {civil(session.farm.planning_date || session.farm.cutoff)}–{civil(addDays(session.farm.planning_date || session.farm.cutoff, session.farm.horizon_days - 1))}</small>
        <strong>{!strategy ? "Not calculated" : m.requested === null ? "Unknown" : `${num(m.delivered)} / ${num(m.requested)} kg`}</strong>
        <span>{m.shortfall === null ? "Shortfall unknown" : `${num(m.shortfall)} kg shortfall`}</span>
      </article>
      <article className="metric-strip__reported">
        <small>Reported forecast</small>
        <strong>
          {reportedRequested
            ? `${num((100 * Math.min(reportedDelivered, reportedRequested)) / reportedRequested)}% coverage · ${num(reported?.metrics?.rejected_kg || 0)} kg rejected`
            : "No results yet"}
        </strong>
        <span>Farmer-reported · unverified</span>
      </article>
    </div>
  );
}
function Proposal({
  strategy,
  selected,
  onSelect,
}: {
  strategy: Strategy;
  selected: boolean;
  onSelect: () => void;
}) {
  const m = metricValues(strategy);
  return (
    <button
      className={`proposal-card ${selected ? "is-selected" : ""}`}
      onClick={onSelect}
    >
      <span>{selected ? "Candidate" : "Alternative"}</span>
      <h3>{strategy.name}</h3>
      <p>{strategy.name === "Lean" ? "Uses a tighter resource plan while the modeled limits hold." : strategy.name === "Resilient" ? "Keeps more modeled capacity for demand and supply variation." : "Balances modeled order service, capacity and contribution margin."}</p>
      <div>
        <b>{m.coverage === null ? "Unknown" : `${num(m.coverage)}%`}</b>
        <small>booked coverage</small>
        <b>{num(m.expiry)} kg</b>
        <small>expiry</small>
        <b>SGD {num(m.margin)}</b>
        <small>margin</small>
      </div>
      <em>
        {strategy.violations.length
          ? `${strategy.violations.length} constraints flagged`
          : `Feasible within modeled limits${m.shortfall && m.shortfall > 0 ? ` · ${num(m.shortfall)} kg still unfulfilled` : ""}`}
      </em>
    </button>
  );
}
function Explainers({ onClose }: { onClose: () => void }) {
  type TranscriptScene = { title: string; text: string };
  const [transcripts, setTranscripts] = useState<
    Record<string, TranscriptScene[]>
  >({});
  useEffect(() => {
    let current = true;
    void fetch(editionPath("/explainers/transcripts.json"))
      .then((response) => {
        if (!response.ok) throw new Error("Transcript unavailable");
        return response.json() as Promise<Record<string, TranscriptScene[]>>;
      })
      .then((value) => {
        if (current) setTranscripts(value);
      })
      .catch(() => {
        if (current) setTranscripts({});
      });
    return () => {
      current = false;
    };
  }, []);
  const items = [
    [
      "observe-decide",
      "From records to options",
      "observe-decide.mp4",
      "Review the Inbox and compare projected coverage, expiry, rejection and margin.",
    ],
    [
      "council-evidence",
      "How the Council earns trust",
      "council-evidence.mp4",
      "Seven roles show evidence, tools and validation status before advice reaches approval.",
    ],
    [
      "act-replan",
      "From action to recovery",
      "act-replan.mp4",
      "Record what happened, verify the difference and preserve completed work while replanning.",
    ],
  ];
  return (
    <Dialog title="Three short guides" onClose={onClose}>
      <p className="media-boundary">
        Captioned local explainers. Playback uses no inference. Reduced-motion
        users choose when playback begins.
      </p>
      {items.map(([slug, title, file, text]) => (
        <article className="explainer-item" key={file}>
          <video
            controls
            preload="metadata"
            playsInline
            poster={editionPath(`/explainers/${file.replace(".mp4", ".png")}`)}
          >
            <source src={editionPath(`/explainers/${file}`)} type="video/mp4" />
            <track
              kind="captions"
              src={editionPath(`/explainers/${file.replace(".mp4", ".vtt")}`)}
              srcLang="en"
              label="English"
              default
            />
          </video>
          <div>
            <h3>{title}</h3>
            <p>{text}</p>
            <details>
              <summary>Transcript</summary>
              <div className="explainer-transcript">
                {transcripts[slug]?.map((scene, index) => (
                  <section
                    className="explainer-transcript-scene"
                    key={scene.title}
                  >
                    <strong>
                      {index + 1}. {scene.title}
                    </strong>
                    <p>{scene.text}</p>
                  </section>
                )) ?? <p>Loading the caption-matched transcript…</p>}
              </div>
            </details>
            <a
              className="text-button"
              href={editionPath(`/explainers/${file}`)}
              download
            >
              Download MP4
            </a>
          </div>
        </article>
      ))}
    </Dialog>
  );
}
function Dialog({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  const dialogRef = useRef<HTMLElement>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const closeRef = useRef(onClose);

  useLayoutEffect(() => {
    closeRef.current = onClose;
  }, [onClose]);

  useLayoutEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    const opener = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null;
    const windowPosition = { left: window.scrollX, top: window.scrollY };
    const ancestors: { element: HTMLElement; left: number; top: number }[] = [];
    for (let element = opener?.parentElement; element; element = element.parentElement) {
      ancestors.push({ element, left: element.scrollLeft, top: element.scrollTop });
    }
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const focusHeading = () => headingRef.current?.focus({ preventScroll: true });
    const focusable = () => Array.from(dialog.querySelectorAll<HTMLElement>(
      'a[href], button, input, select, textarea, [contenteditable="true"], [tabindex]',
    )).filter((element) => element.tabIndex >= 0
      && !element.matches(":disabled")
      && !element.closest('[hidden], [inert], [aria-hidden="true"]')
      && element.getClientRects().length > 0
      && getComputedStyle(element).visibility !== "hidden");
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.defaultPrevented) return;
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        closeRef.current();
        return;
      }
      if (event.key !== "Tab") return;
      const items = focusable();
      const current = document.activeElement;
      const index = items.indexOf(current as HTMLElement);
      if (items.length === 0) {
        event.preventDefault();
        focusHeading();
      } else if (index < 0 || (event.shiftKey ? index === 0 : index === items.length - 1)) {
        event.preventDefault();
        items[event.shiftKey ? items.length - 1 : 0].focus();
      }
    };
    const onFocusIn = (event: FocusEvent) => {
      if (event.target instanceof Node && !dialog.contains(event.target)) focusHeading();
    };
    document.addEventListener("keydown", onKeyDown);
    document.addEventListener("focusin", onFocusIn);
    focusHeading();

    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("focusin", onFocusIn);
      document.body.style.overflow = previousOverflow;
      // Synchronous restoration also makes StrictMode's setup/cleanup replay safe.
      if (opener?.isConnected) opener.focus({ preventScroll: true });
      for (const { element, left, top } of ancestors) {
        if (element.isConnected) element.scrollTo({ left, top, behavior: "instant" });
      }
      window.scrollTo({ ...windowPosition, behavior: "instant" });
    };
  }, []);

  return (
    <div
      className="sheet-layer"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <section
        ref={dialogRef}
        className="bottom-sheet explainer-sheet"
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <header>
          <h2 ref={headingRef} tabIndex={-1}>{title}</h2>
          <button
            className="icon-button"
            onClick={onClose}
            aria-label={`Close ${title}`}
          >
            <X />
          </button>
        </header>
        <div className="bottom-sheet__body">{children}</div>
      </section>
    </div>
  );
}
function Range({
  label,
  value,
  setValue,
  min,
  max,
  suffix,
}: {
  label: string;
  value: number;
  setValue: (v: number) => void;
  min: number;
  max: number;
  suffix: string;
}) {
  return (
    <label>
      {label}
      <input
        aria-label={label}
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(e) => setValue(Number(e.target.value))}
      />
      <small>
        {value}
        {suffix}
      </small>
    </label>
  );
}
function NumberField({
  label,
  value,
  setValue,
}: {
  label: string;
  value: number;
  setValue: (v: number) => void;
}) {
  return (
    <label>
      {label}
      <input
        aria-label={label}
        type="number"
        min="0"
        step="0.1"
        value={value}
        onChange={(e) => setValue(Number(e.target.value))}
      />
    </label>
  );
}
function MetricValues({ values }: { values: Record<string, number | null> }) {
  return (
    <div className="metric-strip">
      {Object.entries(values).map(([key, value]) => (
        <article key={key}>
          <small>{key.replaceAll("_", " ")}</small>
          <strong>{value === null ? "Unknown" : num(value)}</strong>
          <span>Projected</span>
        </article>
      ))}
    </div>
  );
}
function reviewValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "Not supplied";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
function Empty({
  icon,
  title,
  detail,
  action,
}: {
  icon: ReactNode;
  title: string;
  detail: string;
  action?: ReactNode;
}) {
  return (
    <section className="flow-empty">
      {icon}
      <h1>{title}</h1>
      <p>{detail}</p>
      {action}
    </section>
  );
}
function normalizedFindings(session: PlanningSession | null) {
  const raw = (session?.review?.findings || []) as Array<
    Record<string, unknown>
  >;
  return roleFallbacks.map((functionalRole) => {
    const advisor =
        ADVISORS.find(
          (item) => item.roleId === functionalRoleIds[functionalRole],
        ) || ADVISORS[0],
      row = raw.find((item) => item.functional_role === functionalRole) || {},
      truth = String(
        row.truth_status ||
          row.validation_status ||
          row.status ||
          (session?.review?.status === "not_requested"
            ? "unavailable"
            : "withheld"),
      ).toLowerCase();
    return {
      name: advisor.name,
      advisor,
      role: functionalRole,
      truth:
        truth === "validated"
          ? "validated"
          : truth === "partial"
            ? "partial"
            : truth === "rejected" || truth === "withheld"
              ? "withheld"
              : "unavailable",
      summary: String(
        row.summary || row.statement || "Awaiting explicit review.",
      ),
      question: String(row.question || "What could invalidate this proposal?"),
      evidence: Array.isArray(row.evidence)
        ? row.evidence.map((x) =>
            typeof x === "string"
              ? x
              : String((x as Record<string, unknown>).id || "evidence"),
          )
        : [],
      tool: String(row.tool_status || "unavailable"),
      reasons: Array.isArray(row.rejection_reasons)
        ? row.rejection_reasons.map(String)
        : [],
    };
  });
}
function reviewStatus(
  session: PlanningSession | null,
  findings: ReturnType<typeof normalizedFindings>,
) {
  if (!session?.review || session.review.status === "not_requested")
    return "awaiting";
  if (!findings.length || findings.every((x) => x.truth === "unavailable"))
    return "withheld";
  if (
    ["blocked", "withheld", "failed"].includes(
      String(session.review.status).toLowerCase(),
    )
  )
    return "withheld";
  return String(session.review.truth_status || "").toLowerCase() ===
    "partial" ||
    findings.some((x) => x.truth === "partial" || x.truth === "withheld")
    ? "partial"
    : "ready";
}
function metricValues(strategy?: Strategy) {
  const m = strategy?.metrics as
      | (Strategy["metrics"] & {
          booked_requested_kg?: number;
          booked_delivered_kg?: number;
          rejected_kg?: number;
          waste_rescue_kg?: number;
        })
      | undefined,
    requested = Number(m?.booked_requested_kg || 0),
    delivered = Number(m?.booked_delivered_kg || 0);
  return {
    coverage: requested
      ? (100 * Math.min(delivered, requested)) / requested
      : null,
    surplus: m?.closing_stock_kg == null ? null : Number(m.closing_stock_kg),
    expiry: Number(m?.waste_kg || 0),
    rejection: m?.rejected_kg == null ? null : Number(m.rejected_kg),
    margin: Number(m?.margin_sgd || 0),
    rescue: Number(m?.waste_rescue_kg || 0),
    requested: m?.booked_requested_kg == null ? null : requested,
    delivered: m?.booked_delivered_kg == null ? null : delivered,
    shortfall:
      m?.booked_requested_kg == null || m?.booked_delivered_kg == null
        ? null
        : Math.max(0, requested - delivered),
  };
}
function derivePhase(
  session: PlanningSession,
  workflow: FarmerWorkflowState,
): Phase {
  if (workflow.phase === "replanning") return "replan";
  if (workflow.phase === "verification") return "verify";
  if (workflow.phase === "acting") return "act";
  if (workflow.phase === "decision") return "decide";
  if (session.review && session.review.status !== "not_requested")
    return "decide";
  if (session.result?.strategies?.length) return "discuss";
  return "observe";
}
function addDays(value: string, days: number) {
  const date = new Date(`${value.slice(0, 10)}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}
function civil(value: string) {
  const [y, m, d] = value.slice(0, 10).split("-");
  return `${d}/${m}/${y}`;
}
function num(value: unknown) {
  return Number(value || 0).toLocaleString("en-SG", {
    maximumFractionDigits: 1,
  });
}
function message(value: unknown, fallback: string) {
  return value instanceof Error ? value.message : fallback;
}
