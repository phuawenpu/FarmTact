import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  HelpCircle,
  Keyboard,
  Leaf,
  LoaderCircle,
  Menu,
  Pause,
  Play,
  RotateCcw,
  Sparkles,
  Sprout,
  Volume2,
} from "lucide-react";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type KeyboardEvent as ReactKeyboardEvent,
  type PointerEvent as ReactPointerEvent,
} from "react";
import {
  beginnerPhaseLabels,
  beginnerPhaseOrder,
  beginnerStorageKey,
  clampProgress,
  defaultBeginnerUtilities,
  readBeginnerProgress,
  seasonFromBeginnerJourney,
  writeBeginnerProgress,
  type BeginnerAction,
  type BeginnerCard,
  type BeginnerJourney,
  type BeginnerSeasonState,
  type BeginnerStoredProgress,
  type BeginnerUtilityCard,
} from "../lib/beginner";
import "./BeginnerGame.css";

export interface BeginnerGameProps {
  /** Defaults to pathname: `/play` is the season, every other route is the introduction. */
  landing?: boolean;
  /** Raw V14 server response. `season` can be used instead when the parent already adapted it. */
  journey?: BeginnerJourney | null;
  season?: BeginnerSeasonState | null;
  loading?: boolean;
  busy?: boolean;
  error?: string | null;
  hasSavedSeason?: boolean;
  utilities?: BeginnerUtilityCard[];
  storageKey?: string;
  onStart?: () => void | Promise<void>;
  onContinue?: () => void | Promise<void>;
  onJourneyAction?: (
    request: { journeyId: string; revision: number; actionId: string; optionId?: string },
    card: BeginnerCard,
  ) => void | Promise<void>;
  onUtilityAction?: (utility: BeginnerUtilityCard, action: BeginnerAction) => void | Promise<void>;
  onAsk?: (question: string, card: BeginnerCard) => void | Promise<void>;
  onReplayIntroduction?: () => void;
}

const introCards = [
  {
    id: "intro-goal",
    number: "01",
    eyebrow: "Your goal",
    title: "Keep one promise",
    body: "Guide a tiny Singapore farm from a confirmed order to a recorded delivery.",
    caption: "Illustrative animation · not a live farm reading",
    art: "goal",
  },
  {
    id: "intro-choices",
    number: "02",
    eyebrow: "Your choices",
    title: "Choose with real limits",
    body: "Compare server-calculated plans, then make one clear choice at a time.",
    caption: "Guide preview · actual eligibility comes from the server",
    art: "choices",
  },
  {
    id: "intro-consequences",
    number: "03",
    eyebrow: "Consequences",
    title: "See the farm respond",
    body: "Weather, maintenance and delivery reveal the cost of each decision without changing real operations.",
    caption: "Illustrative animation · simulation only",
    art: "consequences",
  },
] as const;

type Swipe = {
  pointerId: number;
  x: number;
  y: number;
  dx: number;
  dy: number;
  axis: "pending" | "horizontal" | "vertical";
};

function defaultLanding() {
  return !window.location.pathname.replace(/\/+$/, "").endsWith("/play");
}

function navigateToPlay() {
  const path = window.location.pathname.replace(/\/+$/, "");
  window.location.assign(path.endsWith("/play") ? path : `${path || ""}/play`.replace("//", "/"));
}

export default function BeginnerGame({
  landing,
  journey,
  season: suppliedSeason,
  loading = false,
  busy = false,
  error,
  hasSavedSeason,
  utilities = defaultBeginnerUtilities,
  storageKey = beginnerStorageKey(),
  onStart,
  onContinue,
  onJourneyAction,
  onUtilityAction,
  onAsk,
  onReplayIntroduction,
}: BeginnerGameProps) {
  const serverSeason = useMemo(
    () => suppliedSeason || (journey ? seasonFromBeginnerJourney(journey) : null),
    [journey, suppliedSeason],
  );
  const [stored, setStored] = useState<BeginnerStoredProgress>(() => readBeginnerProgress(storageKey));
  const [introIndex, setIntroIndex] = useState(0);
  const [replayingIntro, setReplayingIntro] = useState(false);
  const [motionPaused, setMotionPaused] = useState(false);
  const [prefersReduced, setPrefersReduced] = useState(false);
  const [selectedCardId, setSelectedCardId] = useState<string | undefined>(
    serverSeason?.selectedCardId || stored.selectedCardId,
  );
  const [utilityOpen, setUtilityOpen] = useState(false);
  const [utilityCardId, setUtilityCardId] = useState(stored.utilityCardId || utilities[0]?.id);
  const [explanationOpen, setExplanationOpen] = useState(stored.explanationOpen === true);
  const [askOpen, setAskOpen] = useState(false);
  const [askDraft, setAskDraft] = useState(stored.askDraft || "");
  const [localBusy, setLocalBusy] = useState(false);
  const [announce, setAnnounce] = useState("");
  const [slideDirection, setSlideDirection] = useState<"next" | "previous">("next");
  const swipe = useRef<Swipe | null>(null);
  const cardStageRef = useRef<HTMLDivElement>(null);
  const isLanding = landing ?? defaultLanding();
  const showIntro = isLanding || replayingIntro;
  const isPaused = motionPaused || prefersReduced;

  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const sync = () => setPrefersReduced(media.matches);
    sync();
    media.addEventListener("change", sync);
    return () => media.removeEventListener("change", sync);
  }, []);

  useEffect(() => {
    if (!serverSeason) return;
    const preferred = serverSeason.selectedCardId || stored.selectedCardId;
    setSelectedCardId(serverSeason.cards.some((card) => card.id === preferred) ? preferred : serverSeason.cards[0]?.id);
    setExplanationOpen(false);
    setUtilityOpen(false);
  }, [serverSeason?.id, serverSeason?.revision]); // Server revision is the selection authority.

  useEffect(() => {
    const next: BeginnerStoredProgress = {
      ...stored,
      introSeen: stored.introSeen || (!showIntro && Boolean(serverSeason)),
      selectedCardId,
      utilityCardId,
      explanationOpen,
      askDraft,
      serverSeasonId: serverSeason?.id || stored.serverSeasonId,
      serverRevision: serverSeason?.revision ?? stored.serverRevision,
    };
    writeBeginnerProgress(next, storageKey);
    setStored((current) => JSON.stringify(current) === JSON.stringify(next) ? current : next);
  }, [askDraft, explanationOpen, selectedCardId, serverSeason?.id, serverSeason?.revision, showIntro, storageKey, utilityCardId]);

  const cards = serverSeason?.cards || [];
  const cardIndex = Math.max(0, cards.findIndex((card) => card.id === selectedCardId));
  const activeCard = cards[cardIndex] || cards[0];
  const utilityIndex = Math.max(0, utilities.findIndex((card) => card.id === utilityCardId));
  const activeUtility = utilities[utilityIndex] || utilities[0];

  const selectCard = useCallback((index: number, direction: "next" | "previous" = "next") => {
    if (!cards.length) return;
    const normalized = (index + cards.length) % cards.length;
    setSlideDirection(direction);
    setSelectedCardId(cards[normalized].id);
    setExplanationOpen(false);
    setAnnounce(`${cards[normalized].title}. Card ${normalized + 1} of ${cards.length}.`);
  }, [cards]);

  const selectUtility = useCallback((index: number, direction: "next" | "previous" = "next") => {
    if (!utilities.length) return;
    const normalized = (index + utilities.length) % utilities.length;
    setSlideDirection(direction);
    setUtilityCardId(utilities[normalized].id);
    setAskOpen(false);
    setAnnounce(`${utilities[normalized].title}. Utility ${normalized + 1} of ${utilities.length}.`);
  }, [utilities]);

  const move = useCallback((delta: number) => {
    if (showIntro) {
      setSlideDirection(delta > 0 ? "next" : "previous");
      setIntroIndex((value) => (value + delta + introCards.length) % introCards.length);
      return;
    }
    if (utilityOpen) selectUtility(utilityIndex + delta, delta > 0 ? "next" : "previous");
    else selectCard(cardIndex + delta, delta > 0 ? "next" : "previous");
  }, [cardIndex, selectCard, selectUtility, showIntro, utilityIndex, utilityOpen]);

  const pointerDown = (event: ReactPointerEvent<HTMLElement>) => {
    if (event.pointerType === "mouse" && event.button !== 0) return;
    swipe.current = { pointerId: event.pointerId, x: event.clientX, y: event.clientY, dx: 0, dy: 0, axis: "pending" };
  };
  const pointerMove = (event: ReactPointerEvent<HTMLElement>) => {
    const state = swipe.current;
    if (!state || state.pointerId !== event.pointerId) return;
    state.dx = event.clientX - state.x;
    state.dy = event.clientY - state.y;
    if (state.axis === "pending" && Math.max(Math.abs(state.dx), Math.abs(state.dy)) > 10)
      state.axis = Math.abs(state.dx) > Math.abs(state.dy) * 1.15 ? "horizontal" : "vertical";
    if (state.axis === "horizontal") event.preventDefault();
  };
  const pointerEnd = (event: ReactPointerEvent<HTMLElement>) => {
    const state = swipe.current;
    swipe.current = null;
    if (!state || state.pointerId !== event.pointerId || state.axis !== "horizontal" || Math.abs(state.dx) < 48) return;
    move(state.dx < 0 ? 1 : -1);
  };

  const runLandingAction = async () => {
    setLocalBusy(true);
    try {
      if (serverSeason || hasSavedSeason || stored.serverSeasonId) {
        if (onContinue) await onContinue();
        else navigateToPlay();
      } else if (onStart) await onStart();
      else navigateToPlay();
      setStored((current) => ({ ...current, introSeen: true }));
    } finally {
      setLocalBusy(false);
    }
  };

  const runPrimary = async () => {
    if (!activeCard?.primaryAction || activeCard.primaryAction.disabled || !serverSeason || busy || localBusy) return;
    setLocalBusy(true);
    try {
      await onJourneyAction?.({
        journeyId: serverSeason.id,
        revision: serverSeason.revision,
        actionId: activeCard.primaryAction.id,
        ...(activeCard.primaryAction.optionId ? { optionId: activeCard.primaryAction.optionId } : {}),
      }, activeCard);
    } finally {
      setLocalBusy(false);
    }
  };

  const runUtilityPrimary = async () => {
    const action = activeUtility?.primaryAction;
    if (!activeUtility || !action || action.disabled) return;
    if (action.id === "return-to-season") { setUtilityOpen(false); return; }
    if (action.id === "replay-introduction") {
      setReplayingIntro(true);
      setUtilityOpen(false);
      setIntroIndex(0);
      onReplayIntroduction?.();
      return;
    }
    if (action.kind === "ask") { setAskOpen(true); return; }
    await onUtilityAction?.(activeUtility, action);
  };

  const submitAsk = async () => {
    if (!activeCard || !onAsk || !askDraft.trim()) return;
    setLocalBusy(true);
    try {
      await onAsk(askDraft.trim(), activeCard);
      setAskDraft("");
      setAskOpen(false);
      setAnnounce("Question submitted with the current card as context.");
    } finally { setLocalBusy(false); }
  };

  const keyDown = (event: ReactKeyboardEvent<HTMLElement>) => {
    if (event.target instanceof HTMLTextAreaElement) return;
    if (event.key === "ArrowRight") { event.preventDefault(); move(1); }
    else if (event.key === "ArrowLeft") { event.preventDefault(); move(-1); }
    else if (event.key === "Enter") {
      event.preventDefault();
      if (showIntro) void runLandingAction();
      else if (utilityOpen) void runUtilityPrimary();
      else void runPrimary();
    } else if (event.key.toLowerCase() === "e" && !showIntro && !utilityOpen) setExplanationOpen((value) => !value);
    else if (event.key.toLowerCase() === "m" && !showIntro) setUtilityOpen(true);
    else if (event.key === "Escape" && (utilityOpen || replayingIntro)) { setUtilityOpen(false); setReplayingIntro(false); }
  };

  if (showIntro) return <IntroLanding
    index={introIndex}
    continuing={Boolean(serverSeason || hasSavedSeason || stored.serverSeasonId)}
    busy={busy || localBusy}
    paused={isPaused}
    reduced={prefersReduced}
    replaying={replayingIntro}
    direction={slideDirection}
    onMove={move}
    onStart={() => void runLandingAction()}
    onPause={() => setMotionPaused((value) => !value)}
    onBackToSeason={() => setReplayingIntro(false)}
    onPointerDown={pointerDown}
    onPointerMove={pointerMove}
    onPointerEnd={pointerEnd}
    onKeyDown={keyDown}
  />;

  return <main className={`bg-game ${isPaused ? "is-paused" : ""}`} data-motion={isPaused ? "paused" : "playing"}
    data-testid="beginner-shell" data-stage={serverSeason?.serverStage || serverSeason?.phase || "empty"}
    data-revision={serverSeason?.revision ?? 0}>
    <div className="bg-sr-live" aria-live="polite">{announce}</div>
    <section className="bg-objective" aria-labelledby="bg-objective-title">
      <div className="bg-objective__mark" aria-hidden="true"><Sprout /></div>
      <div>
        <span>{serverSeason?.progressLabel || "First season"}</span>
        <h1 id="bg-objective-title">{serverSeason?.objective || "Open your first season"}</h1>
        {serverSeason?.objectiveDetail && <p>{serverSeason.objectiveDetail}</p>}
      </div>
      {serverSeason && <div className="bg-progress" aria-label={`${beginnerPhaseLabels[serverSeason.phase]}, ${serverSeason.progressLabel || "season in progress"}`}>
        <i style={{ "--bg-progress": `${((beginnerPhaseOrder.indexOf(serverSeason.phase) + 1) / beginnerPhaseOrder.length) * 100}%` } as CSSProperties} />
        <b>{beginnerPhaseLabels[serverSeason.phase]}</b>
      </div>}
    </section>

    {error && <div className="bg-notice bg-notice--error" role="alert"><CircleAlert /><span>{error}</span></div>}
    {serverSeason?.notice && <div className="bg-notice" role="status"><CircleAlert /><span>{serverSeason.notice}</span></div>}

    <section className="bg-farm-region" aria-labelledby="bg-farm-title">
      <div className="bg-section-label"><span>Farm view</span><strong id="bg-farm-title">{serverSeason?.scene.eventLabel || "Season not started"}</strong></div>
      <FarmScene scene={serverSeason?.scene} paused={isPaused} />
    </section>

    <section
      className="bg-decision-region"
      aria-label={utilityOpen ? "Utility cards" : "Season decision cards"}
      tabIndex={0}
      ref={cardStageRef}
      onKeyDown={keyDown}
      onPointerDown={pointerDown}
      onPointerMove={pointerMove}
      onPointerUp={pointerEnd}
      onPointerCancel={pointerEnd}
    >
      {loading && !serverSeason ? <LoadingCard /> : !serverSeason || !activeCard ? <EmptyCard /> : utilityOpen && activeUtility
        ? <UtilityCardView card={activeUtility} index={utilityIndex} count={utilities.length} direction={slideDirection} />
        : <DecisionCard card={activeCard} index={cardIndex} count={cards.length} explanationOpen={explanationOpen} direction={slideDirection} />}
    </section>

    <section className="bg-action-area" aria-label="Card actions" data-testid="beginner-action-area">
      {serverSeason && !utilityOpen && cards.length > 1 && <CardNavigation
        index={cardIndex} count={cards.length} onPrevious={() => move(-1)} onNext={() => move(1)} />}
      {utilityOpen && utilities.length > 1 && <CardNavigation
        index={utilityIndex} count={utilities.length} onPrevious={() => move(-1)} onNext={() => move(1)} utility />}

      {askOpen && utilityOpen ? <div className="bg-ask-composer">
        <label htmlFor="bg-ask-draft">Question about {activeCard?.title || "this decision"}</label>
        <textarea id="bg-ask-draft" value={askDraft} onChange={(event) => setAskDraft(event.target.value)} rows={3}
          placeholder="What should I understand before deciding?" />
        <div><button type="button" onClick={() => setAskOpen(false)}>Cancel</button><button type="button" className="is-primary"
          disabled={!onAsk || !askDraft.trim() || busy || localBusy} onClick={() => void submitAsk()}>Submit question</button></div>
        {!onAsk && <small>Asking is unavailable until a validated conversation handler is connected.</small>}
      </div> : <div className="bg-actions">
        {utilityOpen ? <>
          <button type="button" onClick={() => { setUtilityOpen(false); setAskOpen(false); }}><ArrowLeft />Back</button>
          <button type="button" className="is-primary" disabled={!activeUtility?.primaryAction || activeUtility.primaryAction.disabled || busy || localBusy}
            title={activeUtility?.primaryAction?.disabledReason} onClick={() => void runUtilityPrimary()}>
            {localBusy ? <LoaderCircle className="bg-spin" /> : utilityIcon(activeUtility?.kind)}
            {activeUtility?.primaryAction?.label || "Open"}
          </button>
          <button type="button" onClick={() => setMotionPaused((value) => !value)}>{isPaused ? <Play /> : <Pause />}{isPaused ? "Motion on" : "Pause"}</button>
        </> : <>
          <button type="button" disabled={!activeCard} aria-pressed={explanationOpen} onClick={() => setExplanationOpen((value) => !value)}><HelpCircle />Explain</button>
          <button type="button" className="is-primary" data-testid="beginner-primary" disabled={!activeCard?.primaryAction || activeCard.primaryAction.disabled || busy || localBusy}
            title={activeCard?.primaryAction?.disabledReason} onClick={() => void runPrimary()}>
            {busy || localBusy ? <LoaderCircle className="bg-spin" /> : <ArrowRight />}
            {busy || localBusy ? activeCard?.primaryAction?.pendingLabel || serverSeason?.statusLabel || "Working…" : activeCard?.primaryAction?.label || "Waiting for next step"}
          </button>
          <button type="button" disabled={!utilities.length} onClick={() => { setUtilityOpen(true); setAskOpen(false); }}><Menu />More</button>
        </>}
      </div>}
      {!askOpen && <div className="bg-control-strip">
        <button type="button" onClick={() => setMotionPaused((value) => !value)} aria-pressed={isPaused}>{isPaused ? <Play /> : <Pause />}{isPaused ? "Play motion" : "Pause motion"}</button>
        <span><Keyboard /> <kbd>←</kbd><kbd>→</kbd> cards · <kbd>Enter</kbd> act · <kbd>E</kbd> explain · <kbd>M</kbd> more</span>
      </div>}
      {activeCard?.primaryAction?.disabledReason && !utilityOpen && <p className="bg-disabled-reason" role="status">{activeCard.primaryAction.disabledReason}</p>}
      {serverSeason?.statusLabel && <p className="bg-server-status" aria-live="polite">{serverSeason.status === "running" && <LoaderCircle className="bg-spin" />} {serverSeason.statusLabel}</p>}
    </section>
  </main>;
}

function IntroLanding({ index, continuing, busy, paused, reduced, replaying, direction, onMove, onStart, onPause, onBackToSeason,
  onPointerDown, onPointerMove, onPointerEnd, onKeyDown }: {
  index: number; continuing: boolean; busy: boolean; paused: boolean; reduced: boolean; replaying: boolean; direction: "next" | "previous";
  onMove: (delta: number) => void; onStart: () => void; onPause: () => void; onBackToSeason: () => void;
  onPointerDown: (event: ReactPointerEvent<HTMLElement>) => void; onPointerMove: (event: ReactPointerEvent<HTMLElement>) => void;
  onPointerEnd: (event: ReactPointerEvent<HTMLElement>) => void; onKeyDown: (event: ReactKeyboardEvent<HTMLElement>) => void;
}) {
  return <main className={`bg-landing ${paused ? "is-paused" : ""}`} data-motion={paused ? "paused" : "playing"}>
    <header className="bg-landing__hero">
      <span className="bg-wordmark"><i><Sprout /></i> FarmTact</span>
      <p className="bg-kicker">A first season you can finish</p>
      <h1>Plan the farm.<br /><em>Watch it respond.</em></h1>
      <p>Learn production planning through one small order, one clear choice and its recorded consequences.</p>
    </header>
    <section className="bg-intro-stage" aria-label="How the season works" tabIndex={0} onKeyDown={onKeyDown}
      onPointerDown={onPointerDown} onPointerMove={onPointerMove} onPointerUp={onPointerEnd} onPointerCancel={onPointerEnd}>
      <div className="bg-intro-cards">
        {introCards.map((card, cardIndex) => <article key={card.id}
          className={`bg-intro-card bg-intro-card--${card.art} ${cardIndex === index ? "is-active" : ""} is-${direction}`}
          aria-hidden={cardIndex !== index}>
          <div className="bg-intro-card__art" aria-hidden="true"><IntroArt kind={card.art} /></div>
          <div className="bg-intro-card__copy"><span>{card.number} · {card.eyebrow}</span><h2>{card.title}</h2><p>{card.body}</p><small><Sparkles />{card.caption}</small></div>
        </article>)}
      </div>
    </section>
    <section className="bg-landing-actions" aria-label="Introduction actions">
      <CardNavigation index={index} count={introCards.length} onPrevious={() => onMove(-1)} onNext={() => onMove(1)} />
      <button className="bg-landing-primary" data-testid="beginner-primary" type="button" disabled={busy} onClick={onStart}>
        {busy ? <LoaderCircle className="bg-spin" /> : continuing ? <Play /> : <Sprout />}
        {busy ? "Opening season…" : continuing ? "Continue my season" : "Start playing"}
      </button>
      <button type="button" onClick={onPause} aria-pressed={paused}>{paused ? <Play /> : <Pause />}{paused ? "Play illustrations" : "Pause illustrations"}</button>
      {replaying && <button type="button" onClick={onBackToSeason}><ArrowLeft />Return to season</button>}
      <p><Keyboard /> Use <kbd>←</kbd><kbd>→</kbd> to move · <kbd>Enter</kbd> to {continuing ? "continue" : "start"}</p>
      {reduced && <small>Reduced motion preference detected. Illustrations remain still.</small>}
    </section>
  </main>;
}

function IntroArt({ kind }: { kind: "goal" | "choices" | "consequences" }) {
  return <svg viewBox="0 0 360 190" role="presentation">
    <path className="bg-art-sun" d="M284 19a28 28 0 1 1 0 56 28 28 0 0 1 0-56Z" />
    <path className="bg-art-ground" d="m24 117 142-73 170 82-151 58Z" />
    <path className="bg-art-bed" d="m62 120 88-44 49 24-91 44Z" />
    <path className="bg-art-bed bg-art-bed--two" d="m153 145 83-42 46 22-85 43Z" />
    <g className="bg-art-plants">
      {[0,1,2,3].map((item) => <g key={item} transform={`translate(${88 + item * 22} ${103 - item * 11})`}><path d="M0 20V4" /><path d="M0 11c-13-1-13-11-12-14C-2-3 1 5 0 11Z" /><path d="M0 8C12 8 14-1 13-4 3-4-1 2 0 8Z" /></g>)}
    </g>
    {kind === "goal" && <g className="bg-art-crate"><path d="m231 89 49-23 37 18-49 24Z" /><path d="m231 89 37 19v38l-37-19Z" /><path d="m268 108 49-24v39l-49 23Z" /><path className="bg-art-check" d="m276 120 8 6 17-19" /></g>}
    {kind === "choices" && <g className="bg-art-choice"><path d="M221 63h54v72h-54z" /><path d="M232 81h32M232 95h22M232 109h29" /><circle cx="248" cy="49" r="17" /><path d="m239 49 7 7 12-15" /></g>}
    {kind === "consequences" && <g className="bg-art-weather"><path d="M210 56c5-19 34-21 43-6 19-7 33 17 18 30h-61c-16-8-12-22 0-24Z" /><path d="m220 92-8 19m31-19-8 19m31-19-8 19" /><path className="bg-art-arrow" d="M294 104v36m-12-11 12 12 12-12" /></g>}
  </svg>;
}

function FarmScene({ scene, paused }: { scene?: BeginnerSeasonState["scene"]; paused: boolean }) {
  const beds = scene?.beds.slice(0, 4) || [];
  const label = beds.length
    ? `${beds.map((bed) => `${bed.name}, ${bed.cropLabel || "crop"}, ${bed.cropStage}`).join("; ")}. ${scene?.eventLabel || ""}`
    : "Illustrated farm view waiting for a server-owned season record.";
  return <figure className={`bg-farm-scene bg-farm-scene--${scene?.eventTone || "calm"} ${paused ? "is-paused" : ""}`} aria-label={label}
    data-testid="beginner-scene" data-result-id={scene?.resultId || undefined}>
    <svg viewBox="0 0 760 300" aria-hidden="true" focusable="false">
      <defs>
        <linearGradient id="bg-sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#bce2df" /><stop offset="1" stopColor="#f4e8c9" /></linearGradient>
        <linearGradient id="bg-soil" x1="0" y1="0" x2="1" y2="1"><stop stopColor="#765436" /><stop offset="1" stopColor="#4c3627" /></linearGradient>
      </defs>
      <rect width="760" height="300" rx="24" fill="url(#bg-sky)" />
      <circle className="bg-scene-sun" cx="630" cy="59" r="34" />
      <path className="bg-scene-horizon" d="M0 190 180 103l143 72 160-95 277 125v95H0Z" />
      <g className="bg-scene-greenhouse"><path d="m82 153 94-54 94 54v82l-94 45-94-45Z" /><path d="m82 153 94 46 94-46M176 99v100m-63-27v79m126-79v78" /></g>
      <path className="bg-scene-path" d="m286 300 165-95 83 41-93 54Z" />
      {beds.map((bed, index) => <SceneBed key={bed.id} bed={bed} index={index} />)}
      {(scene?.eventTone === "rain" || scene?.eventTone === "maintenance") && <g className="bg-scene-rain">{[320,352,384,416,448,480,512,544,576].map((x) => <path key={x} d={`M${x} 32l-12 25`} />)}</g>}
      {scene?.eventTone === "delivery" && <g className="bg-scene-truck"><path d="M565 213h96v44h-96z" /><path d="m661 229 29 1 21 27h-50Z" /><circle cx="590" cy="260" r="13" /><circle cx="683" cy="260" r="13" /><path d="M579 226h49m-25-12v25" /></g>}
      {scene?.eventTone === "recovery" && <g className="bg-scene-recovery"><path d="M596 103a34 34 0 1 1-13 28" /><path d="m568 109 16 23 20-18" /></g>}
    </svg>
    <figcaption><span>{scene?.dateLabel || "Season clock waits for the server"}</span><strong>{scene?.weatherLabel || scene?.eventLabel || "Tiny farm"}</strong><small>Illustrated view · server-owned state · noninteractive</small></figcaption>
  </figure>;
}

function SceneBed({ bed, index }: { bed: BeginnerSeasonState["scene"]["beds"][number]; index: number }) {
  const columns = [0, 1, 2, 3];
  const x = 330 + (index % 2) * 154;
  const y = 150 + Math.floor(index / 2) * 72;
  const progress = clampProgress(bed.progress);
  const plantScale = bed.cropStage === "seedling" ? .55 : bed.cropStage === "ready" ? 1.15 : bed.cropStage === "harvested" || bed.cropStage === "empty" ? .12 : .9;
  return <g className={`bg-scene-bed bg-scene-bed--${bed.cropStage}`} transform={`translate(${x} ${y})`} style={{ "--bed-accent": bed.accent || "#86b943", "--plant-scale": plantScale, "--growth-progress": progress } as CSSProperties}>
    <path d="M0 34 83 0l65 32-86 38Z" fill="url(#bg-soil)" /><path className="bg-scene-bed__edge" d="m0 34 62 36v15L0 49Zm62 36 86-38v15L62 85Z" />
    {columns.map((column) => <g className="bg-scene-plant" key={column} transform={`translate(${28 + column * 25} ${37 - column * 10}) scale(${plantScale})`}><path d="M0 15V-5" /><path d="M0 7c-16 0-18-13-16-17C-4-10 1-1 0 7Z" /><path d="M0 3c16 1 19-12 17-16C5-13-1-5 0 3Z" /></g>)}
    <text x="2" y="102">{bed.name}</text>
  </g>;
}

function DecisionCard({ card, index, count, explanationOpen, direction }: { card: BeginnerCard; index: number; count: number; explanationOpen: boolean; direction: "next" | "previous" }) {
  return <article className={`bg-card is-${direction}`} data-card-id={card.id} data-testid="beginner-card" tabIndex={0}>
    <header><div><span>{card.eyebrow}</span><small>{index + 1} / {count}</small></div>{card.statusLabel && <b>{card.statusLabel}</b>}</header>
    <div className="bg-card__body"><h2>{card.title}</h2><p>{card.summary}</p>
      {card.facts?.length ? <dl>{card.facts.slice(0, 4).map((fact) => <div key={fact.id} data-tone={fact.tone || "default"}><dt>{fact.label}</dt><dd>{fact.value}</dd>{fact.detail && <small>{fact.detail}</small>}</div>)}</dl> : null}
      {card.guideTip && <aside><Sparkles /><div><b>Guide tip</b><p>{card.guideTip}</p></div></aside>}
      {explanationOpen && <div className="bg-card__explanation" role="status"><b>Why this is here</b><p>{card.explanation || "This card is part of the guided season. Its facts and action eligibility come from the stored server state."}</p></div>}
    </div>
    <footer><span>{card.entity ? `${card.entity.kind.replaceAll("_", " ")} · ${card.entity.id}` : "Guided season"}</span><strong>Swipe or use controls below</strong></footer>
  </article>;
}

function UtilityCardView({ card, index, count, direction }: { card: BeginnerUtilityCard; index: number; count: number; direction: "next" | "previous" }) {
  return <article className={`bg-card bg-card--utility is-${direction}`} data-card-id={card.id} data-testid="beginner-card" tabIndex={0}>
    <header><div><span>{card.eyebrow || "More"}</span><small>{index + 1} / {count}</small></div>{utilityIcon(card.kind)}</header>
    <div className="bg-card__body"><h2>{card.title}</h2><p>{card.summary}</p>{card.guideTip && <aside><Sparkles /><div><b>Guide tip</b><p>{card.guideTip}</p></div></aside>}</div>
    <footer><span>Utility card</span><strong>Back returns to the same season card</strong></footer>
  </article>;
}

function utilityIcon(kind?: BeginnerUtilityCard["kind"]) {
  if (kind === "journal" || kind === "records") return <BookOpen />;
  if (kind === "crops") return <Leaf />;
  if (kind === "replay") return <RotateCcw />;
  if (kind === "adviser") return <Volume2 />;
  return <Sparkles />;
}

function CardNavigation({ index, count, onPrevious, onNext, utility = false }: { index: number; count: number; onPrevious: () => void; onNext: () => void; utility?: boolean }) {
  return <nav className="bg-card-nav" aria-label={utility ? "Browse utility cards" : "Browse cards"}>
    <button type="button" onClick={onPrevious} aria-label="Previous card"><ChevronLeft />Previous</button>
    <div aria-hidden="true">{Array.from({ length: count }, (_, item) => <i key={item} className={item === index ? "is-current" : ""} />)}</div>
    <button type="button" onClick={onNext} aria-label="Next card">Next<ChevronRight /></button>
  </nav>;
}

function LoadingCard() {
  return <article className="bg-card bg-card--empty" data-testid="beginner-card" tabIndex={0} aria-live="polite"><div className="bg-card__body"><LoaderCircle className="bg-spin" /><h2>Opening your season</h2><p>Loading the stored farm state and next eligible action.</p></div></article>;
}

function EmptyCard() {
  return <article className="bg-card bg-card--empty" data-testid="beginner-card" tabIndex={0}><div className="bg-card__body"><Sprout /><h2>Your season is ready to begin</h2><p>Start from the introduction. No farm action or inference runs automatically.</p></div></article>;
}
