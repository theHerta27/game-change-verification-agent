import React, { useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle, Bot, Camera, CheckCircle2, ChevronLeft, ChevronRight, CircleDot, Cpu, Eye,
  FileJson, Gauge, Gamepad2, HelpCircle, Orbit, Play, RefreshCw, RotateCcw,
  Settings, ShieldCheck, SlidersHorizontal, Sparkles, ThumbsUp, Wrench, X
} from 'lucide-react';

type Language = 'zh' | 'en';
type Provider = 'mock' | 'openai_compatible';
type EngineName = 'unity' | 'unreal';
type ExperienceMode = 'novice' | 'professional';
type PlayVariant = 'baseline' | 'candidate';
type DiffRow = { change_type: string; path: string; before: unknown; after: unknown };
type MetricRow = { metric: string; baseline: unknown; candidate: unknown; target: string; passed: boolean; evidence: string };
type TimelineRow = { step: string; status: string; timestamp: string; detail: Record<string, unknown> };
type RepairRow = { iteration: number; action: string; applied: boolean; phase_id?: string; reason: string };
type AgentRun = {
  agent_name: string;
  prompt_name: string;
  provider: string;
  model?: string | null;
  latency_ms: number;
  status: string;
  model_call: boolean;
  iteration?: number;
};
type QualityReview = {
  iteration: number;
  agent_output: { decision: string; repair_action?: string | null; reason: string; evidence_refs: string[] };
  policy_gate: {
    passed: boolean;
    effective_decision: string;
    effective_action?: string | null;
    expected_action?: string | null;
    reason: string;
  };
};
type EngineCapability = {
  engine: EngineName;
  display_name: string;
  status: 'unavailable' | 'build_required' | 'available' | 'verified' | 'failed';
  reason: string;
  patterns: string[];
  automated_run: boolean;
  manual_play: boolean;
};
type BulletCapabilities = {
  default_engine: EngineName;
  engines: Record<EngineName, EngineCapability>;
};
type VisualCapture = { time_seconds: number; phase_id: string; phase_name: string; pattern_type: string; file_name: string };
type VisualVariant = {
  variant: PlayVariant;
  duration_seconds: number;
  random_seed: number;
  run_mode: string;
  fixed_trajectory: boolean;
  config_sha256: string;
  captures: VisualCapture[];
};
type VisualComparison = {
  status: 'running' | 'completed' | 'failed';
  random_seed: number;
  fixed_trajectory: boolean;
  duration_seconds?: number;
  capture_times_seconds: number[];
  camera?: string;
  generated_at?: string;
  variants: Partial<Record<PlayVariant, VisualVariant>>;
  error?: { type: string; message: string } | null;
};
type Workflow = {
  workflow_id: string;
  provider: Provider;
  engine?: EngineName;
  model?: string | null;
  status: string;
  current_iteration: number;
  budget: { max_unity_runs: number; max_model_calls: number; unity_runs_used: number; model_calls_used: number };
  authorization?: { actor: string; note: string; scope: string } | null;
  feasibility_gate?: { decision: string; reason: string; issues: Array<Record<string, unknown>> };
  structured_goal?: Record<string, unknown>;
  static_validation?: {
    passed: boolean;
    schema_errors: unknown[];
    reference_errors?: unknown[];
    rule_errors: unknown[];
    safety_errors?: unknown[];
    layers?: Record<string, { passed: boolean; errors: unknown[] }>;
  };
  config_diff?: DiffRow[];
  repair_history?: RepairRow[];
  agent_runs?: AgentRun[];
  quality_reviews?: QualityReview[];
  badcases?: Array<Record<string, unknown>>;
  comparison_report?: { passed: boolean; metrics: MetricRow[]; evidence_scope: string };
  baseline_telemetry?: Record<string, unknown> | null;
  candidate_telemetry?: Record<string, unknown> | null;
  visual_comparison?: VisualComparison | null;
  timeline: TimelineRow[];
  error?: { stage: string; type: string; message: string } | null;
  available_artifacts: Array<{ name: string; size: number }>;
};

const text = {
  zh: {
    eyebrow: 'GAME CHANGE VERIFICATION',
    title: '弹幕变更验证',
    subtitle: '用自然语言提出玩法调整。Agent 生成并审查候选，确定性工具校验，游戏引擎在隔离环境自动对比修改前后结果。',
    boundary: '自动化边界',
    boundaryText: '一次授权后最多运行 3 个候选；只修改候选 JSON。本页面不会覆盖正式基线。',
    requirement: '玩法变更需求',
    provider: '候选生成方式',
    engine: '验证引擎',
    engineHint: '候选 JSON 使用同一份 Bullet Hell 1.0 契约；不同引擎只负责执行和采集证据。',
    engineUnavailable: '当前环境不可运行',
    engineBuildRequired: '需要先构建本地 Player',
    engineAvailable: '可运行，尚未形成完整验证证据',
    engineVerified: '已完成真实运行验证',
    mock: '确定性 Mock',
    mockNovice: '固定演示模型（免费、结果可重复）',
    real: '真实模型',
    timeout: '模型超时（秒）',
    create: '生成候选并静态校验',
    creating: '正在生成候选',
    loadLatest: '查看上次完整演示（只读，不运行）',
    authorize: '授权本次隔离测试',
    authorizationSafety: '仅允许本次隔离测试，不修改正式配置。',
    authorizedBy: '授权人',
    note: '授权说明',
    run: '开始自动对比与修复',
    running: '游戏引擎正在运行，请保持后端窗口开启',
    manual: '打开 Unity 手动试玩',
    reset: '重新开始一次演示',
    accept: '记录为接受（当前不会写回正式基线）',
    revise: '要求修订',
    rollback: '回滚候选',
    decisionNote: '最终决策说明',
    status: '当前状态',
    goal: '结构化目标',
    changes: '候选配置变化',
    evidence: '修改前后运行证据',
    repairs: '自动修复记录',
    events: '可观察执行事件',
    artifacts: '原始证据文件',
    noEvidence: '完成自动验证后显示修改前与修改后的同条件对比。',
    noRepairs: '当前候选尚未触发自动修复。',
    pass: '通过',
    fail: '未通过',
    before: '修改前',
    after: '修改后',
    target: '目标',
    check: '指标',
    scope: '证据边界',
    mockHint: 'Mock 会按固定规则修改真实弹幕基线，用于稳定回归；它不是自由理解任意需求的模型。',
    realHint: '真实模型只提出完整候选 JSON，仍须通过同一 Schema、安全规则和 Unity 证据。',
    blocked: '需求已被安全门拦截',
    failed: '工作流执行失败',
    awaiting: '候选已就绪，等待你授权隔离测试预算。',
    ready: '证据已完成，请根据指标决定接受、修订或回滚。',
    exhausted: '自动运行预算已用完，当前候选仍未满足全部目标。',
    presets: ['双向螺旋主案例', '高密度修复观察', '危险需求拦截'],
    presetDescriptions: [
      '系统会把第二阶段改成双向螺旋，先做安全校验，再用同一轨迹分别运行修改前和修改后；若受击或性能不达标，会在预算内自动调低弹速并复测。',
      '系统会提高第三阶段花瓣弹的压迫感，重点观察玩家受击和低分位 FPS，并展示一次候选如何被证据驱动地修复。',
      '这是一条故意越界的高密度需求。安全门应在启动 Unity 前直接拦截，并解释为什么不能运行以及可接受的边界。'
    ],
    presetRequirements: [
      '第二阶段改为双向螺旋弹，提高密度，但同时存在的子弹不能超过350发，最低帧率不能低于55 FPS。',
      '第三阶段使用花瓣弹提高压迫感，但玩家最多受击3次，最低帧率不能低于55 FPS。',
      '每0.02秒发射200颗高速弹，越密越好。'
    ],
    steps: ['需求与候选', '静态安全校验', '隔离测试授权', 'Baseline / Candidate', '自动修复', '人工结论'],
    planner: '策划控制台',
    debug: '展开原始 JSON',
    safeDemo: '安全演示：所有修改都发生在临时副本中，不会覆盖正式基线',
    noviceMode: '新手模式',
    professionalMode: '专业模式',
    replayGuide: '重新查看引导',
    settings: '显示设置',
    caseOutcome: '这个案例会发生什么',
    beforeProfessional: 'Baseline（修改前）',
    afterProfessional: 'Candidate（修改后）',
    beforeAfterTitle: '真人手动体验',
    beforeAfterText: '手动操作路线每次不同，只用于分别感受两个版本的视觉和操作，不作为严格的前后效果证明。',
    playBefore: '手动体验修改前',
    playAfter: '手动体验修改后',
    temporaryPlayerNote: '只启动后端登记的临时游戏 Player，并读取本工作流快照；不会修改正式基线。',
    selectedPlay: '当前已启动',
    baselineSnapshot: '修改前',
    candidateSnapshot: '修改后',
    launchSucceeded: '临时 Player 已启动，可以开始主观体验。',
    launchFailed: '临时 Player 启动失败',
    visualTitle: '自动固定轨迹画面对比',
    visualPurpose: '自动画面用于证明改了什么；运行数据用于证明约束是否达标；手动试玩只用于主观体验。',
    visualFairness: '两侧使用相同 seed、固定轨迹、36 秒时长和相机，在 10、20、30 秒自动截图。',
    generateVisual: '生成自动画面对比',
    generatingVisual: '正在依次生成修改前和修改后截图',
    visualReady: '自动截图证据已生成',
    visualFailed: '自动截图生成失败',
    visualEmpty: '当前工作流还没有自动画面证据。生成后会显示三个相同时间点的并排截图。',
    atSecond: '第 {second} 秒',
    phase: '阶段',
    pattern: '弹幕类型',
    keyChanges: '本次关键变化',
    visualChanges: ['第二阶段：单向螺旋 → 双向螺旋', '每波子弹：12 → 16', '子弹速度：3.6 → 2.6（两轮自动修复后）'],
    evidenceLayers: ['自动截图：肉眼确认修改效果', '自动数据：验证数量、受击与性能约束', '手动体验：补充主观操作感受'],
    readOnlyLoaded: '已载入只读演示记录。查看不会重新运行模型或 Unity。',
    newDemoHint: '从只读正式基线创建一个全新的临时 Workflow，不复用上次的候选结果。',
    guideTitle: '五分钟安全演示引导',
    guideSkip: '跳过引导',
    guidePrevious: '上一步',
    guideNext: '下一步',
    guideDone: '完成引导',
    guideSteps: [
      '先查看上次完整演示。这个动作只读取已有证据，不会运行任何程序。',
      '阅读案例说明，确认这次要观察的是弹幕样式、受击、性能还是安全拦截。',
      '需要亲自走流程时，重新开始一次演示；系统会从只读基线建立新的临时 Workflow。',
      '候选通过静态校验后，再授权本次隔离测试。授权不会修改正式配置。',
      '证据完成后，先试玩修改前，再试玩修改后，最后只记录你的结论。'
    ],
    termBaseline: 'Baseline 是修改前的只读基线配置，用作对照。',
    termCandidate: 'Candidate 是 Agent 提出的修改后候选，只存在于临时工作流中。',
    termWorkflow: 'Workflow 是一次从需求、校验、授权到证据和结论的完整验证记录。',
    termArtifact: 'Artifact 是工作流保存的 JSON、日志和报告等原始证据文件。',
    termTelemetry: 'Telemetry 是引擎运行时自动记录的子弹、受击、存活时间和 FPS 等数据。',
    agentEvidence: 'Agent 分工与决策证据',
    requirementAgent: '需求解析 Agent',
    qualityReviewAgent: '质量审查 Agent',
    requirementAgentHelp: '只把自然语言需求转换为结构化目标和候选配置，无权运行引擎或写回基线。',
    qualityReviewAgentHelp: '只读取需求、配置差异和运行证据，输出接受、有限修复或人工复核；不能直接改数值。',
    deterministicGate: '确定性策略门',
    noAgentEvidence: '创建新工作流后显示两个 Agent 的调用与审查记录。',
    modelCall: '模型调用',
    deterministicRun: '确定性执行'
  },
  en: {
    eyebrow: 'GAME CHANGE VERIFICATION',
    title: 'Bullet Hell Change Verification',
    subtitle: 'Describe a gameplay change. Bounded agents propose and review a candidate, deterministic tools verify it, and a game engine compares before and after in isolation.',
    boundary: 'Automation boundary',
    boundaryText: 'One authorization permits up to 3 candidate runs and candidate JSON changes only. You make the final baseline decision.',
    requirement: 'Gameplay change requirement',
    provider: 'Candidate provider',
    engine: 'Verification engine',
    engineHint: 'Both engines consume the same Bullet Hell 1.0 candidate; the engine backend only executes and records evidence.',
    engineUnavailable: 'Unavailable in this environment',
    engineBuildRequired: 'Build the local Player first',
    engineAvailable: 'Runnable, not yet fully verified',
    engineVerified: 'Verified with real runtime evidence',
    mock: 'Deterministic Mock',
    mockNovice: 'Fixed demo model (free and repeatable)',
    real: 'Real provider',
    timeout: 'Model timeout (seconds)',
    create: 'Create candidate and validate',
    creating: 'Creating candidate',
    loadLatest: 'View last complete demo (read-only)',
    authorize: 'Authorize this isolated test',
    authorizationSafety: 'This authorization applies only to this isolated test and never changes the formal configuration.',
    authorizedBy: 'Authorized by',
    note: 'Authorization note',
    run: 'Start comparison and repair',
    running: 'The game engine is running. Keep the backend window open.',
    manual: 'Open Unity manual playtest',
    reset: 'Start a new demo',
    accept: 'Record as accepted (does not write to baseline)',
    revise: 'Request revision',
    rollback: 'Roll back candidate',
    decisionNote: 'Final decision note',
    status: 'Current status',
    goal: 'Structured goal',
    changes: 'Candidate config changes',
    evidence: 'Before / after runtime evidence',
    repairs: 'Automatic repair history',
    events: 'Observable execution events',
    artifacts: 'Raw evidence files',
    noEvidence: 'Baseline and candidate comparison appears after automatic validation.',
    noRepairs: 'The current candidate has not triggered a repair.',
    pass: 'Passed',
    fail: 'Failed',
    before: 'Before',
    after: 'After',
    target: 'Target',
    check: 'Metric',
    scope: 'Evidence boundary',
    mockHint: 'Mock deterministically changes the real bullet-hell baseline for repeatable regression. It is not a general language model.',
    realHint: 'The real provider only proposes candidate JSON. The same schema, safety, and Unity evidence still apply.',
    blocked: 'The safety gate blocked this requirement',
    failed: 'Workflow execution failed',
    awaiting: 'Candidate ready. Authorize the isolated test budget.',
    ready: 'Evidence is ready. Accept, revise, or roll back.',
    exhausted: 'The automatic run budget is exhausted and targets are still unmet.',
    presets: ['Bidirectional spiral', 'Dense pattern repair', 'Unsafe request block'],
    presetDescriptions: [
      'The system changes phase 2 to a bidirectional spiral, validates it, then runs before and after with the same trajectory. It can reduce speed and retest when evidence misses a target.',
      'The system raises pressure in phase 3 and focuses on player hits and low-percentile FPS, showing an evidence-driven bounded repair.',
      'This intentionally unsafe density request should be blocked before Unity starts, with a clear explanation of the supported boundary.'
    ],
    presetRequirements: [
      'Change phase 2 to a denser bidirectional spiral while keeping at most 350 alive bullets and at least 55 FPS.',
      'Use a denser petal pattern in phase 3, with at most 3 player hits and at least 55 FPS.',
      'Fire 200 high-speed bullets every 0.02 seconds. Denser is always better.'
    ],
    steps: ['Requirement', 'Static safety', 'Authorization', 'Baseline / Candidate', 'Auto repair', 'Human decision'],
    planner: 'Designer console',
    debug: 'Show raw JSON',
    safeDemo: 'Safe demo: every change stays in a temporary copy and never overwrites the formal baseline',
    noviceMode: 'Novice mode',
    professionalMode: 'Professional mode',
    replayGuide: 'Replay guide',
    settings: 'Display settings',
    caseOutcome: 'What will happen in this case',
    beforeProfessional: 'Baseline',
    afterProfessional: 'Candidate',
    beforeAfterTitle: 'Manual human experience',
    beforeAfterText: 'Manual movement differs between runs. Use these only to feel each version, not as strict before/after proof.',
    playBefore: 'Manually experience Before',
    playAfter: 'Manually experience After',
    temporaryPlayerNote: 'This starts only a registered temporary game Player with a workflow snapshot and never changes the formal baseline.',
    selectedPlay: 'Currently launched',
    baselineSnapshot: 'Before',
    candidateSnapshot: 'After',
    launchSucceeded: 'The temporary Player started for subjective playtesting.',
    launchFailed: 'The temporary Player failed to start',
    visualTitle: 'Automatic fixed-trajectory visual comparison',
    visualPurpose: 'Automatic visuals show what changed; runtime data proves constraints; manual playtesting adds subjective experience.',
    visualFairness: 'Both sides use the same seed, fixed trajectory, 36-second duration, and camera, captured at 10, 20, and 30 seconds.',
    generateVisual: 'Generate automatic visual comparison',
    generatingVisual: 'Generating Before and After screenshots in sequence',
    visualReady: 'Automatic screenshot evidence is ready',
    visualFailed: 'Automatic screenshot generation failed',
    visualEmpty: 'This workflow has no automatic visual evidence yet. Generate it to compare three identical time points.',
    atSecond: '{second} seconds',
    phase: 'Phase',
    pattern: 'Pattern',
    keyChanges: 'Key changes',
    visualChanges: ['Phase 2: one-way spiral → bidirectional spiral', 'Bullets per wave: 12 → 16', 'Bullet speed: 3.6 → 2.6 after two bounded repairs'],
    evidenceLayers: ['Automatic screenshots: visually confirm the change', 'Automatic data: verify density, hits, and performance', 'Manual playtest: add subjective feel'],
    readOnlyLoaded: 'Read-only demo loaded. Viewing it does not rerun the model or Unity.',
    newDemoHint: 'Create a fresh temporary Workflow from the read-only formal baseline without reusing the last candidate.',
    guideTitle: 'Five-minute safe demo guide',
    guideSkip: 'Skip guide',
    guidePrevious: 'Previous',
    guideNext: 'Next',
    guideDone: 'Finish guide',
    guideSteps: [
      'Start by viewing the last complete demo. This reads saved evidence only and runs nothing.',
      'Read the case description and confirm whether this demo focuses on pattern style, hits, performance, or safety blocking.',
      'To perform the flow yourself, start a new demo. A fresh temporary Workflow is created from the read-only baseline.',
      'After static validation, authorize only this isolated test. The formal configuration is never changed.',
      'When evidence is ready, play Before first, then After, and only record your final decision.'
    ],
    termBaseline: 'Baseline is the read-only configuration before the change and is used for comparison.',
    termCandidate: 'Candidate is the proposed configuration after the change and exists only in a temporary workflow.',
    termWorkflow: 'Workflow is one complete record from requirement and validation through evidence and decision.',
    termArtifact: 'Artifact is a saved JSON, log, or report that provides raw workflow evidence.',
    termTelemetry: 'Telemetry is runtime data recorded by an engine, such as bullets, hits, survival time, and FPS.',
    agentEvidence: 'Agent roles and decision evidence',
    requirementAgent: 'Requirement Agent',
    qualityReviewAgent: 'Quality Review Agent',
    requirementAgentHelp: 'Converts natural language into a structured goal and candidate config. It cannot run an engine or write to the baseline.',
    qualityReviewAgentHelp: 'Reads the requirement, diff, and runtime evidence to recommend accept, bounded repair, or human review. It cannot edit values.',
    deterministicGate: 'Deterministic policy gate',
    noAgentEvidence: 'Create a new workflow to see both agent runs and review records.',
    modelCall: 'Model call',
    deterministicRun: 'Deterministic execution'
  }
} as const;

const runningStatuses = new Set(['running_baseline', 'running_candidate', 'analyzing', 'repairing']);
const EXPERIENCE_MODE_KEY = 'agentic-game-rd.bullet-hell.experience-mode';
const GUIDE_DISMISSED_KEY = 'agentic-game-rd.bullet-hell.guide-dismissed';

export function BulletHellWorkflowPanel({ language, provider, timeoutSeconds, onProvider, onTimeout }: {
  language: Language;
  provider: Provider;
  timeoutSeconds: number;
  onProvider: (provider: Provider) => void;
  onTimeout: (seconds: number) => void;
}) {
  const t = text[language];
  const [requirement, setRequirement] = useState<string>(t.presetRequirements[0]);
  const [workflow, setWorkflow] = useState<Workflow | null>(null);
  const [actor, setActor] = useState(language === 'zh' ? '策划演示者' : 'Demo designer');
  const [authorizationNote, setAuthorizationNote] = useState(language === 'zh' ? '允许在隔离环境最多运行三轮' : 'Allow up to three isolated runs');
  const [decisionNote, setDecisionNote] = useState('');
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [selectedPreset, setSelectedPreset] = useState(0);
  const [experienceMode, setExperienceMode] = useState<ExperienceMode>(() => readExperienceMode());
  const [guideActive, setGuideActive] = useState(() => readExperienceMode() === 'novice' && !readGuideDismissed());
  const [guideStep, setGuideStep] = useState(0);
  const [playVariant, setPlayVariant] = useState<PlayVariant | null>(null);
  const [playMessage, setPlayMessage] = useState('');
  const [latestLoaded, setLatestLoaded] = useState(false);
  const [engine, setEngine] = useState<EngineName>('unity');
  const [capabilities, setCapabilities] = useState<BulletCapabilities | null>(null);

  useEffect(() => {
    request<BulletCapabilities>('/api/bullet-hell/capabilities')
      .then((value) => {
        setCapabilities(value);
        setEngine((current) => current || value.default_engine);
      })
      .catch((reason) => setError(String(reason)));
  }, []);

  useEffect(() => {
    if (!workflow || (!runningStatuses.has(workflow.status) && workflow.visual_comparison?.status !== 'running')) return;
    const timer = window.setInterval(() => {
      request<Workflow>(`/api/bullet-hell/workflows/${workflow.workflow_id}`).then(setWorkflow).catch((reason) => setError(String(reason)));
    }, 1200);
    return () => window.clearInterval(timer);
  }, [workflow?.workflow_id, workflow?.status, workflow?.visual_comparison?.status]);

  useEffect(() => {
    window.localStorage.setItem(EXPERIENCE_MODE_KEY, experienceMode);
  }, [experienceMode]);

  useEffect(() => {
    if (workflow?.engine) setEngine(workflow.engine);
  }, [workflow?.engine]);

  const currentStep = useMemo(() => stepForStatus(workflow?.status), [workflow?.status]);
  const novice = experienceMode === 'novice';
  const beforeLabel = novice ? t.before : t.beforeProfessional;
  const afterLabel = novice ? t.after : t.afterProfessional;
  const displaySteps = useMemo(
    () => t.steps.map((label, index) => novice && index === 3 ? `${t.before} / ${t.after}` : label),
    [novice, t]
  );
  const manualPlayAllowed = !!workflow && [
    'authorized', 'evidence_ready', 'budget_exhausted', 'accepted', 'revision_requested', 'rolled_back'
  ].includes(workflow.status);
  const visualComparisonAllowed = !!workflow && [
    'evidence_ready', 'budget_exhausted', 'accepted', 'revision_requested', 'rolled_back'
  ].includes(workflow.status);
  const activeEngine = capabilities?.engines[workflow?.engine ?? engine];
  const engineReady = !!activeEngine && ['available', 'verified'].includes(activeEngine.status);

  async function act(name: string, action: () => Promise<Workflow>) {
    setBusy(name);
    setError('');
    try {
      setWorkflow(await action());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setBusy('');
    }
  }

  function choosePreset(index: number) {
    setSelectedPreset(index);
    setRequirement(t.presetRequirements[index]);
    setWorkflow(null);
    setError('');
    setLatestLoaded(false);
    setPlayVariant(null);
    setPlayMessage('');
  }

  function createWorkflow(name = 'create') {
    setLatestLoaded(false);
    setPlayVariant(null);
    setPlayMessage('');
    setDecisionNote('');
    return act(name, () => request('/api/bullet-hell/workflows', {
      method: 'POST',
      body: JSON.stringify({ requirement_text: requirement, provider, timeout_seconds: timeoutSeconds, engine })
    }));
  }

  function changeExperienceMode(mode: ExperienceMode) {
    setExperienceMode(mode);
    window.localStorage.setItem(EXPERIENCE_MODE_KEY, mode);
    if (mode === 'professional') {
      setGuideActive(false);
      window.localStorage.setItem(GUIDE_DISMISSED_KEY, 'true');
    }
  }

  function dismissGuide() {
    setGuideActive(false);
    window.localStorage.setItem(GUIDE_DISMISSED_KEY, 'true');
  }

  function replayGuide() {
    setExperienceMode('novice');
    setGuideStep(0);
    setGuideActive(true);
  }

  async function launchManualPlay(variant: PlayVariant) {
    if (!workflow) return;
    setPlayVariant(variant);
    setPlayMessage('');
    setBusy(`play-${variant}`);
    setError('');
    try {
      await request(`/api/bullet-hell/workflows/${workflow.workflow_id}/play/${variant}`, { method: 'POST' });
      setPlayMessage(t.launchSucceeded);
    } catch (reason) {
      setPlayMessage(`${t.launchFailed}：${reason instanceof Error ? reason.message : String(reason)}`);
    } finally {
      setBusy('');
    }
  }

  async function generateVisualComparison() {
    if (!workflow) return;
    setBusy('visual-comparison');
    setError('');
    try {
      setWorkflow(await request(`/api/bullet-hell/workflows/${workflow.workflow_id}/visual-comparison`, { method: 'POST' }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setBusy('');
    }
  }

  return <section className="bullet-workbench">
    <div className="bullet-command">
      <div className="safe-demo-banner" role="status">
        <ShieldCheck className="h-5 w-5 shrink-0"/>
        <strong>{t.safeDemo}</strong>
      </div>

      <div className="experience-toolbar" aria-label={t.settings}>
        <div className="mode-switch" role="group" aria-label={t.settings}>
          <button
            type="button"
            className={novice ? 'mode-switch-active' : ''}
            aria-pressed={novice}
            onClick={() => changeExperienceMode('novice')}
          >{t.noviceMode}</button>
          <button
            type="button"
            className={!novice ? 'mode-switch-active' : ''}
            aria-pressed={!novice}
            onClick={() => changeExperienceMode('professional')}
          >{t.professionalMode}</button>
        </div>
        <button type="button" className="button-quiet" onClick={replayGuide}>
          <Settings className="h-4 w-4"/>{t.replayGuide}
        </button>
      </div>

      {guideActive && <GuideCard
        step={guideStep}
        steps={t.guideSteps}
        title={t.guideTitle}
        previous={t.guidePrevious}
        next={t.guideNext}
        done={t.guideDone}
        skip={t.guideSkip}
        onPrevious={() => setGuideStep((value) => Math.max(0, value - 1))}
        onNext={() => guideStep === t.guideSteps.length - 1 ? dismissGuide() : setGuideStep((value) => value + 1)}
        onSkip={dismissGuide}
      />}

      <div>
        <p className="text-xs font-semibold text-cyan-300">{t.eyebrow}</p>
        <h2 className="mt-2 text-2xl font-semibold text-white">{t.title}</h2>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-300">{t.subtitle}</p>
      </div>

      <div className="mt-5 border-l-2 border-cyan-400 pl-4">
        <p className="text-xs font-semibold text-cyan-200">{t.boundary}</p>
        <p className="mt-1 text-sm leading-6 text-slate-300">{t.boundaryText}</p>
      </div>

      <div className="mt-6">
        <div className="flex flex-wrap gap-2">
          {t.presets.map((label, index) =>
            <button key={label} className={selectedPreset === index ? 'chip-active' : 'chip'} onClick={() => choosePreset(index)}>
              {label}
            </button>
          )}
        </div>
        {selectedPreset >= 0 && <div className={`case-outcome mt-4 ${guideActive && guideStep === 1 ? 'guide-focus' : ''}`}>
          <div className="flex items-center gap-2 text-sm font-semibold text-cyan-100">
            <Eye className="h-4 w-4"/>{t.caseOutcome}
          </div>
          <p className="mt-2 text-sm leading-6 text-slate-300">{t.presetDescriptions[selectedPreset]}</p>
        </div>}
        <label className="label mt-4" htmlFor="bullet-requirement">{t.requirement}</label>
        <textarea
          id="bullet-requirement"
          className="input min-h-32 resize-y leading-6"
          value={requirement}
          onChange={(event) => { setRequirement(event.target.value); setSelectedPreset(-1); setWorkflow(null); }}
        />
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <label className="label" htmlFor="bullet-provider">
          {t.provider}
          <select
            id="bullet-provider"
            className="input mt-1"
            value={provider}
            disabled={!!workflow}
            onChange={(event) => onProvider(event.target.value as Provider)}
          >
            <option value="mock">{novice ? t.mockNovice : t.mock}</option>
            <option value="openai_compatible">{t.real}</option>
          </select>
        </label>
        <label className="label" htmlFor="bullet-engine">
          {t.engine}
          <select
            id="bullet-engine"
            className="input mt-1"
            value={engine}
            disabled={!!workflow}
            onChange={(event) => setEngine(event.target.value as EngineName)}
          >
            <option value="unity">Unity 6</option>
            <option value="unreal">Unreal Engine 5</option>
          </select>
        </label>
        <label className="label" htmlFor="bullet-timeout">
          {t.timeout}
          <input
            id="bullet-timeout"
            className="input mt-1"
            type="number"
            min={5}
            max={300}
            value={timeoutSeconds}
            disabled={!!workflow}
            onChange={(event) => onTimeout(Math.min(300, Math.max(5, Number(event.target.value) || 5)))}
          />
        </label>
      </div>
      <p className="mt-3 text-xs leading-5 text-slate-400">{provider === 'mock' ? t.mockHint : t.realHint}</p>
      <div className={`engine-capability mt-3 ${engineReady ? 'engine-capability-ready' : 'engine-capability-blocked'}`}>
        <Cpu className="h-4 w-4 shrink-0"/>
        <div>
          <p className="text-xs font-semibold">
            {activeEngine?.display_name ?? (engine === 'unity' ? 'Unity 6' : 'Unreal Engine 5')}
            {' · '}
            {engineStatusLabel(activeEngine?.status, t)}
          </p>
          <p className="mt-1 text-xs leading-5 opacity-80">{activeEngine?.reason ?? t.engineHint}</p>
        </div>
      </div>

      <div className="mt-5 flex flex-wrap gap-2">
        {!workflow && <button className={`button-primary ${guideActive && guideStep === 2 ? 'guide-focus' : ''}`} disabled={!!busy || !requirement.trim()} onClick={() => createWorkflow()}>
          {busy === 'create' ? <RefreshCw className="h-4 w-4 animate-spin"/> : <Sparkles className="h-4 w-4"/>}
          {busy === 'create' ? t.creating : t.create}
        </button>}
        {!workflow && <button className={`button-secondary ${guideActive && guideStep === 0 ? 'guide-focus' : ''}`} disabled={!!busy} onClick={() => {
          setLatestLoaded(true);
          setPlayVariant(null);
          void act('latest', () => request('/api/bullet-hell/workflows/latest'));
        }}>
          {busy === 'latest' ? <RefreshCw className="h-4 w-4 animate-spin"/> : <FileJson className="h-4 w-4"/>}
          {t.loadLatest}
        </button>}
        {workflow && <button className={`button-secondary ${guideActive && guideStep === 2 ? 'guide-focus' : ''}`} disabled={!!busy} onClick={() => void createWorkflow('restart')}>
          <RotateCcw className="h-4 w-4"/>{t.reset}
        </button>}
      </div>
      {latestLoaded && workflow && <p className="mt-3 text-xs leading-5 text-cyan-100">{t.readOnlyLoaded}</p>}
      {workflow && <p className="mt-2 text-xs leading-5 text-slate-400">{t.newDemoHint}</p>}

      {workflow?.status === 'awaiting_authorization' && <div className="mt-5 border-t border-line pt-5">
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="label">{t.authorizedBy}<input className="input mt-1" value={actor} onChange={(event) => setActor(event.target.value)}/></label>
          <label className="label">{t.note}<input className="input mt-1" value={authorizationNote} onChange={(event) => setAuthorizationNote(event.target.value)}/></label>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-3">
        <button className={`button-primary ${guideActive && guideStep === 3 ? 'guide-focus' : ''}`} disabled={!!busy || !actor.trim()} onClick={() => act('authorize', () => request(`/api/bullet-hell/workflows/${workflow.workflow_id}/authorize`, {
          method: 'POST', body: JSON.stringify({ actor, note: authorizationNote })
        }))}><ShieldCheck className="h-4 w-4"/>{t.authorize}</button>
        <span className="max-w-sm text-xs leading-5 text-cyan-100">{t.authorizationSafety}</span>
        </div>
      </div>}

      {workflow?.status === 'authorized' && <div className="mt-5 flex flex-wrap gap-2 border-t border-line pt-5">
        <button className="button-primary" disabled={!!busy || !engineReady} onClick={() => act('run', () => request(`/api/bullet-hell/workflows/${workflow.workflow_id}/run`, { method: 'POST' }))}>
          <Play className="h-4 w-4"/>{t.run}
        </button>
        {!engineReady && <span className="self-center text-xs leading-5 text-amber-200">{activeEngine?.reason}</span>}
      </div>}

      {workflow && ['evidence_ready', 'budget_exhausted', 'blocked'].includes(workflow.status) && <div className="mt-5 border-t border-line pt-5">
        <label className="label">{t.decisionNote}<input className="input mt-1" value={decisionNote} onChange={(event) => setDecisionNote(event.target.value)}/></label>
        <div className="mt-3 flex flex-wrap gap-2">
          {workflow.status === 'evidence_ready' && <DecisionButton label={t.accept} icon={<ThumbsUp className="h-4 w-4"/>} disabled={!!busy || !decisionNote.trim()} onClick={() => decide('accept')}/>}
          <DecisionButton label={t.revise} icon={<Wrench className="h-4 w-4"/>} secondary disabled={!!busy || !decisionNote.trim()} onClick={() => decide('revise')}/>
          <DecisionButton label={t.rollback} icon={<RotateCcw className="h-4 w-4"/>} secondary disabled={!!busy || !decisionNote.trim()} onClick={() => decide('rollback')}/>
        </div>
      </div>}

      {manualPlayAllowed && engineReady && workflow && <BeforeAfterPlay
        beforeLabel={beforeLabel}
        afterLabel={afterLabel}
        title={t.beforeAfterTitle}
        description={t.beforeAfterText}
        beforeButton={t.playBefore}
        afterButton={t.playAfter}
        note={t.temporaryPlayerNote}
        selectedLabel={t.selectedPlay}
        selectedVariant={playVariant}
        baselineLabel={t.baselineSnapshot}
        candidateLabel={t.candidateSnapshot}
        playMessage={playMessage}
        playerName={activeEngine?.display_name ?? (engine === 'unity' ? 'Unity 6' : 'Unreal Engine 5')}
        busy={busy}
        guideFocus={guideActive && guideStep === 4}
        onPlay={launchManualPlay}
      />}

      {error && <p role="alert" className="mt-4 rounded-md border border-red-500/40 bg-red-950/40 p-3 text-sm text-red-100">{error}</p>}
    </div>

    <div className="bullet-evidence">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold text-slate-500">{t.planner}</p>
          <h3 className="mt-1 flex items-center gap-1 text-lg font-semibold text-white">{t.status}<TermHelp label="Workflow" explanation={t.termWorkflow}/></h3>
        </div>
        <StatusBadge status={workflow?.status ?? 'drafted'} language={language} novice={novice}/>
      </div>

      <div className="evidence-rail mt-5" aria-label={t.status}>
        {displaySteps.map((label, index) => <div key={label} className={`evidence-stop ${index <= currentStep ? 'evidence-stop-active' : ''}`}>
          <span>{index + 1}</span><p>{label}</p>
        </div>)}
      </div>

      {workflow && <p className="mt-4 text-sm leading-6 text-slate-300">{statusMessage(workflow.status, t)}</p>}
      {workflow?.error && <p className="mt-3 border-l-2 border-red-400 pl-3 text-sm text-red-200">{workflow.error.type}: {workflow.error.message}</p>}

      {visualComparisonAllowed && engineReady && workflow && <AutomaticVisualComparison
        workflow={workflow}
        language={language}
        beforeLabel={beforeLabel}
        afterLabel={afterLabel}
        title={t.visualTitle}
        purpose={t.visualPurpose}
        fairness={t.visualFairness}
        generateLabel={t.generateVisual}
        generatingLabel={t.generatingVisual}
        readyLabel={t.visualReady}
        failedLabel={t.visualFailed}
        emptyLabel={t.visualEmpty}
        atSecond={t.atSecond}
        phaseLabel={t.phase}
        patternLabel={t.pattern}
        changesTitle={t.keyChanges}
        layers={t.evidenceLayers}
        busy={busy === 'visual-comparison'}
        onGenerate={generateVisualComparison}
      />}

      {workflow?.structured_goal && <EvidenceBand title={t.goal} icon={<SlidersHorizontal className="h-4 w-4"/>}>
        <GoalSummary value={workflow.structured_goal} language={language}/>
      </EvidenceBand>}

      {workflow && <EvidenceBand title={t.agentEvidence} icon={<Bot className="h-4 w-4"/>}>
        <AgentEvidence
          runs={workflow.agent_runs ?? []}
          reviews={workflow.quality_reviews ?? []}
          language={language}
          novice={novice}
          labels={{
            requirement: t.requirementAgent,
            quality: t.qualityReviewAgent,
            requirementHelp: t.requirementAgentHelp,
            qualityHelp: t.qualityReviewAgentHelp,
            policyGate: t.deterministicGate,
            empty: t.noAgentEvidence,
            modelCall: t.modelCall,
            deterministic: t.deterministicRun
          }}
        />
      </EvidenceBand>}

      {workflow?.config_diff && workflow.config_diff.length > 0 && <EvidenceBand title={t.changes} icon={<Orbit className="h-4 w-4"/>}>
        <div className="overflow-x-auto"><table className="w-full min-w-[620px] text-left text-sm">
          <thead className="text-xs text-slate-500"><tr><th className="px-2 py-2">Path</th><th className="px-2 py-2">{beforeLabel}<TermHelp label="Baseline" explanation={t.termBaseline}/></th><th className="px-2 py-2">{afterLabel}<TermHelp label="Candidate" explanation={t.termCandidate}/></th></tr></thead>
          <tbody>{workflow.config_diff.slice(0, 16).map((row) => <tr key={row.path} className="border-t border-line">
            <td className="px-2 py-2 font-mono text-xs text-cyan-200">{row.path}</td>
            <td className="px-2 py-2 text-slate-400">{display(row.before)}</td>
            <td className="px-2 py-2 text-slate-100">{display(row.after)}</td>
          </tr>)}</tbody>
        </table></div>
      </EvidenceBand>}

      <EvidenceBand title={<>{t.evidence}<TermHelp label="Telemetry" explanation={t.termTelemetry}/></>} icon={<Gauge className="h-4 w-4"/>}>
        {!workflow?.comparison_report ? <p className="text-sm text-slate-400">{t.noEvidence}</p> :
          <>
            <div className="overflow-x-auto"><table className="w-full min-w-[620px] text-left text-sm">
              <thead className="text-xs text-slate-500"><tr><th className="px-2 py-2">{t.check}</th><th className="px-2 py-2">{beforeLabel}<TermHelp label="Baseline" explanation={t.termBaseline}/></th><th className="px-2 py-2">{afterLabel}<TermHelp label="Candidate" explanation={t.termCandidate}/></th><th className="px-2 py-2">{t.target}</th><th className="px-2 py-2">{t.status}</th></tr></thead>
              <tbody>{workflow.comparison_report.metrics.map((row) => <tr key={row.metric} className="border-t border-line">
                <td className="px-2 py-2 font-medium text-slate-100">{metricLabel(row.metric, language)}</td>
                <td className="px-2 py-2 text-slate-400">{metricValue(row.metric, row.baseline)}</td>
                <td className="px-2 py-2">{metricValue(row.metric, row.candidate)}</td>
                <td className="px-2 py-2 text-slate-400">{row.target}</td>
                <td className={`px-2 py-2 font-medium ${row.passed ? 'text-run' : 'text-red-300'}`}>{row.passed ? t.pass : t.fail}</td>
              </tr>)}</tbody>
            </table></div>
            <p className="mt-3 border-l-2 border-amber-400 pl-3 text-xs leading-5 text-amber-100"><strong>{t.scope}：</strong>{workflow.comparison_report.evidence_scope}</p>
          </>
        }
      </EvidenceBand>

      <div className="grid gap-4 lg:grid-cols-2">
        <EvidenceBand title={t.repairs} icon={<Wrench className="h-4 w-4"/>}>
          {!workflow?.repair_history?.length ? <p className="text-sm text-slate-400">{t.noRepairs}</p> :
            <div className="space-y-3">{workflow.repair_history.map((row) => <div key={`${row.iteration}-${row.action}`} className="border-l-2 border-violet-400 pl-3">
              <p className="text-sm font-medium text-slate-100">{language === 'zh' ? `第 ${row.iteration} 轮` : `Round ${row.iteration}`} · {repairLabel(row.action, language)}</p>
              <p className="mt-1 text-xs leading-5 text-slate-400">{repairReason(row.reason, language)}</p>
            </div>)}</div>}
        </EvidenceBand>
        <EvidenceBand title={t.events} icon={<CircleDot className="h-4 w-4"/>}>
          <div className="max-h-60 space-y-3 overflow-auto">{workflow?.timeline?.map((row, index) => <div key={`${row.timestamp}-${index}`} className="flex gap-3 text-sm">
            <span className={`mt-1 h-2 w-2 shrink-0 rounded-full ${row.status === 'failed' || row.status === 'blocked' ? 'bg-red-400' : 'bg-cyan-400'}`}/>
            <div><p className="text-slate-200">{eventLabel(row.step, language)}</p><p className="text-xs text-slate-500">{eventStatusLabel(row.status, language)}</p></div>
          </div>) ?? <p className="text-sm text-slate-400">—</p>}</div>
        </EvidenceBand>
      </div>

      {!!workflow?.available_artifacts?.length && <EvidenceBand title={<>{t.artifacts}<TermHelp label="Artifact" explanation={t.termArtifact}/></>} icon={<FileJson className="h-4 w-4"/>}>
        <div className="flex flex-wrap gap-2">{workflow.available_artifacts.filter((row) => !row.name.endsWith('.log')).map((row) =>
          <a key={row.name} className="chip" href={`/api/bullet-hell/workflows/${workflow.workflow_id}/artifacts/${row.name}`} target="_blank" rel="noreferrer">{row.name}</a>
        )}</div>
        <details className="mt-4"><summary className="cursor-pointer text-sm text-slate-400">{t.debug}</summary><pre className="mt-3 max-h-72 overflow-auto rounded-md bg-slate-950 p-3 text-xs text-slate-300">{JSON.stringify(workflow, null, 2)}</pre></details>
      </EvidenceBand>}
    </div>
  </section>;

  function decide(decision: 'accept' | 'revise' | 'rollback') {
    if (!workflow) return;
    return act(decision, () => request(`/api/bullet-hell/workflows/${workflow.workflow_id}/decision`, {
      method: 'POST', body: JSON.stringify({ decision, actor, note: decisionNote })
    }));
  }
}

function AgentEvidence({ runs, reviews, language, novice, labels }: {
  runs: AgentRun[];
  reviews: QualityReview[];
  language: Language;
  novice: boolean;
  labels: {
    requirement: string;
    quality: string;
    requirementHelp: string;
    qualityHelp: string;
    policyGate: string;
    empty: string;
    modelCall: string;
    deterministic: string;
  };
}) {
  if (!runs.length) return <p className="text-sm text-slate-400">{labels.empty}</p>;
  return <div className="agent-evidence-list">
    {runs.map((run, index) => {
      const requirement = run.agent_name === 'requirement_agent';
      const title = requirement ? labels.requirement : labels.quality;
      const description = requirement ? labels.requirementHelp : labels.qualityHelp;
      return <div className="agent-evidence-row" key={`${run.agent_name}-${run.iteration ?? 0}-${index}`}>
        <div className="agent-evidence-heading">
          <span className={`agent-status-dot ${run.status === 'succeeded' ? 'agent-status-ok' : 'agent-status-failed'}`}/>
          <div>
            <p className="text-sm font-semibold text-slate-100">
              {title}{run.iteration ? ` · ${language === 'zh' ? `第 ${run.iteration} 轮` : `Round ${run.iteration}`}` : ''}
            </p>
            <p className="mt-1 text-xs leading-5 text-slate-400">{description}</p>
          </div>
        </div>
        <div className="agent-evidence-meta">
          <span>{run.model_call ? labels.modelCall : labels.deterministic}</span>
          <span>{run.provider}{run.model ? ` / ${run.model}` : ''}</span>
          {!novice && <span className="font-mono">{run.prompt_name}</span>}
          <span>{run.latency_ms} ms</span>
        </div>
      </div>;
    })}
    {reviews.map((review) => <div className="policy-gate-row" key={`review-${review.iteration}`}>
      <ShieldCheck className="h-4 w-4 shrink-0 text-cyan-300"/>
      <div>
        <p className="text-sm font-semibold text-slate-100">
          {labels.policyGate} · {review.policy_gate.effective_decision}
        </p>
        <p className="mt-1 text-xs leading-5 text-slate-400">{review.policy_gate.reason}</p>
        {!novice && <p className="mt-1 font-mono text-xs text-cyan-200">
          agent={review.agent_output.decision}
          {' · '}action={review.agent_output.repair_action ?? 'none'}
          {' · '}expected={review.policy_gate.expected_action ?? 'none'}
        </p>}
      </div>
    </div>)}
  </div>;
}

function GuideCard({ step, steps, title, previous, next, done, skip, onPrevious, onNext, onSkip }: {
  step: number;
  steps: readonly string[];
  title: string;
  previous: string;
  next: string;
  done: string;
  skip: string;
  onPrevious: () => void;
  onNext: () => void;
  onSkip: () => void;
}) {
  return <aside className="guide-card" aria-live="polite">
    <div className="flex items-start justify-between gap-3">
      <div>
        <p className="text-xs font-semibold text-cyan-200">{title}</p>
        <p className="mt-1 text-xs text-slate-400">{step + 1} / {steps.length}</p>
      </div>
      <button type="button" className="icon-button" title={skip} aria-label={skip} onClick={onSkip}><X className="h-4 w-4"/></button>
    </div>
    <p className="mt-3 text-sm leading-6 text-slate-100">{steps[step]}</p>
    <div className="mt-4 flex flex-wrap items-center justify-between gap-2">
      <button type="button" className="button-quiet" onClick={onSkip}>{skip}</button>
      <div className="flex gap-2">
        <button type="button" className="button-secondary" disabled={step === 0} onClick={onPrevious}><ChevronLeft className="h-4 w-4"/>{previous}</button>
        <button type="button" className="button-primary" onClick={onNext}>{step === steps.length - 1 ? done : next}<ChevronRight className="h-4 w-4"/></button>
      </div>
    </div>
  </aside>;
}

function AutomaticVisualComparison({ workflow, language, beforeLabel, afterLabel, title, purpose, fairness,
  generateLabel, generatingLabel, readyLabel, failedLabel, emptyLabel, atSecond, phaseLabel, patternLabel,
  changesTitle, layers, busy, onGenerate }: {
  workflow: Workflow;
  language: Language;
  beforeLabel: string;
  afterLabel: string;
  title: string;
  purpose: string;
  fairness: string;
  generateLabel: string;
  generatingLabel: string;
  readyLabel: string;
  failedLabel: string;
  emptyLabel: string;
  atSecond: string;
  phaseLabel: string;
  patternLabel: string;
  changesTitle: string;
  layers: readonly string[];
  busy: boolean;
  onGenerate: () => void;
}) {
  const visual = workflow.visual_comparison;
  const complete = visual?.status === 'completed';
  const running = visual?.status === 'running';
  const changes = summarizeVisualChanges(workflow, language);
  const imageUrl = (variant: PlayVariant, name: string) =>
    `/api/bullet-hell/workflows/${workflow.workflow_id}/visuals/${variant}/${name}?v=${visual?.generated_at ?? 'current'}`;
  return <section className="automatic-visual-panel mt-5">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div className="max-w-2xl">
        <h4 className="flex items-center gap-2 text-base font-semibold text-white"><Camera className="h-5 w-5 text-cyan-300"/>{title}</h4>
        <p className="mt-2 text-sm leading-6 text-slate-200">{purpose}</p>
        <p className="mt-1 text-xs leading-5 text-cyan-100">{fairness}</p>
      </div>
      <button type="button" className="button-primary" disabled={busy || running} onClick={onGenerate}>
        {running ? <RefreshCw className="h-4 w-4 animate-spin"/> : <Camera className="h-4 w-4"/>}
        {running ? generatingLabel : generateLabel}
      </button>
    </div>

    <div className="evidence-layer-strip mt-4">
      {layers.map((item, index) => <div key={item}><span>{index + 1}</span><p>{item}</p></div>)}
    </div>

    <div className="mt-4 border-l-2 border-cyan-400 bg-cyan-400/5 px-3 py-3">
      <p className="text-xs font-semibold text-cyan-100">{changesTitle}</p>
      <ul className="mt-2 grid gap-2 text-sm text-slate-200 md:grid-cols-3">
        {changes.map((item) => <li key={item}>{item}</li>)}
      </ul>
    </div>

    {!visual && <p className="mt-4 rounded-md border border-line bg-slate-950/50 p-3 text-sm text-slate-400">{emptyLabel}</p>}
    {running && <p className="mt-4 flex items-center gap-2 text-sm text-cyan-100"><RefreshCw className="h-4 w-4 animate-spin"/>{generatingLabel}</p>}
    {visual?.status === 'failed' && <p className="mt-4 border-l-2 border-red-400 pl-3 text-sm text-red-200">{failedLabel}：{visual.error?.message}</p>}
    {complete && <div className="mt-5">
      <p className="mb-4 flex items-center gap-2 text-sm font-semibold text-green-200"><CheckCircle2 className="h-4 w-4"/>{readyLabel}</p>
      <div className="space-y-6">
        {visual.capture_times_seconds.map((second) => {
          const baseline = visual.variants.baseline?.captures.find((item) => item.time_seconds === second);
          const candidate = visual.variants.candidate?.captures.find((item) => item.time_seconds === second);
          if (!baseline || !candidate) return null;
          return <section key={second} className="visual-timepoint">
            <h5>{atSecond.replace('{second}', String(second))}</h5>
            <div className="mt-3 grid gap-3 md:grid-cols-2">
              <ScreenshotEvidence label={beforeLabel} capture={baseline} url={imageUrl('baseline', baseline.file_name)} phaseLabel={phaseLabel} patternLabel={patternLabel}/>
              <ScreenshotEvidence label={afterLabel} capture={candidate} url={imageUrl('candidate', candidate.file_name)} phaseLabel={phaseLabel} patternLabel={patternLabel}/>
            </div>
          </section>;
        })}
      </div>
    </div>}
  </section>;
}

function ScreenshotEvidence({ label, capture, url, phaseLabel, patternLabel }: {
  label: string;
  capture: VisualCapture;
  url: string;
  phaseLabel: string;
  patternLabel: string;
}) {
  return <figure className="media-evidence">
    <div className="media-evidence-title">{label}</div>
    <img src={url} alt={`${label} ${capture.time_seconds}s ${capture.phase_name}`}/>
    <figcaption>{phaseLabel}：{capture.phase_name} · {patternLabel}：{capture.pattern_type}</figcaption>
  </figure>;
}

function BeforeAfterPlay({ beforeLabel, afterLabel, title, description, beforeButton, afterButton, note,
  selectedLabel, selectedVariant, baselineLabel, candidateLabel, playMessage, playerName, busy, guideFocus, onPlay }: {
  beforeLabel: string;
  afterLabel: string;
  title: string;
  description: string;
  beforeButton: string;
  afterButton: string;
  note: string;
  selectedLabel: string;
  selectedVariant: PlayVariant | null;
  baselineLabel: string;
  candidateLabel: string;
  playMessage: string;
  playerName: string;
  busy: string;
  guideFocus: boolean;
  onPlay: (variant: PlayVariant) => void;
}) {
  return <section className={`before-after-panel mt-5 ${guideFocus ? 'guide-focus' : ''}`}>
    <div className="flex items-start gap-3">
      <Gamepad2 className="mt-0.5 h-5 w-5 shrink-0 text-cyan-300"/>
      <div>
        <h3 className="text-base font-semibold text-white">{title}</h3>
        <p className="mt-1 text-sm leading-6 text-slate-300">{description}</p>
      </div>
    </div>
    <div className="mt-4 grid gap-3 sm:grid-cols-2">
      <button type="button" className="play-variant-button" disabled={!!busy} onClick={() => onPlay('baseline')}>
        <span className="play-variant-index">1</span><span><strong>{beforeButton}</strong><small>{beforeLabel}</small></span>
      </button>
      <button type="button" className="play-variant-button" disabled={!!busy} onClick={() => onPlay('candidate')}>
        <span className="play-variant-index">2</span><span><strong>{afterButton}</strong><small>{afterLabel}</small></span>
      </button>
    </div>
    <p className="mt-3 flex items-start gap-2 text-xs leading-5 text-cyan-100"><ShieldCheck className="mt-0.5 h-4 w-4 shrink-0"/>{note}</p>
    {selectedVariant && <div className="launch-command-panel mt-4" role="status">
      <p className="text-sm font-semibold text-white">{selectedLabel}：{selectedVariant === 'baseline' ? baselineLabel : candidateLabel}</p>
      {busy === `play-${selectedVariant}` && <p className="mt-2 flex items-center gap-2 text-xs text-cyan-100"><RefreshCw className="h-4 w-4 animate-spin"/>{playerName} Player</p>}
      {playMessage && <p className={`mt-2 text-xs ${playMessage.includes('失败') || playMessage.includes('failed') ? 'text-red-200' : 'text-green-200'}`}>{playMessage}</p>}
    </div>}
  </section>;
}

function TermHelp({ label, explanation }: { label: string; explanation: string }) {
  return <button type="button" className="term-help" title={`${label}：${explanation}`} aria-label={`${label}：${explanation}`}>
    <HelpCircle className="h-3.5 w-3.5"/>
  </button>;
}

function EvidenceBand({ title, icon, children }: { title: React.ReactNode; icon: React.ReactNode; children: React.ReactNode }) {
  return <section className="mt-5 border-t border-line pt-5">
    <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-200">{icon}{title}</h4>
    {children}
  </section>;
}

function DecisionButton({ label, icon, disabled, secondary, onClick }: { label: string; icon: React.ReactNode; disabled: boolean; secondary?: boolean; onClick: () => void }) {
  return <button className={secondary ? 'button-secondary' : 'button-primary'} disabled={disabled} onClick={onClick}>{icon}{label}</button>;
}

function StatusBadge({ status, language, novice }: { status: string; language: Language; novice: boolean }) {
  const passed = ['evidence_ready', 'accepted'].includes(status);
  const failed = ['blocked', 'failed', 'budget_exhausted'].includes(status);
  const label = statusLabel(status, language, novice);
  return <span className={`inline-flex min-h-9 items-center gap-2 rounded-md border px-3 py-1.5 text-sm ${passed ? 'border-run/50 bg-run/10 text-run' : failed ? 'border-red-400/50 bg-red-950/40 text-red-200' : 'border-cyan-400/40 bg-cyan-950/30 text-cyan-200'}`}>
    {passed ? <CheckCircle2 className="h-4 w-4"/> : failed ? <AlertTriangle className="h-4 w-4"/> : runningStatuses.has(status) ? <RefreshCw className="h-4 w-4 animate-spin"/> : <CircleDot className="h-4 w-4"/>}
    {label}
  </span>;
}

function GoalSummary({ value, language }: { value: Record<string, unknown>; language: Language }) {
  return <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
    {Object.entries(value).filter(([key]) => key !== 'source_text').map(([key, item]) => <div key={key}>
      <p className="text-xs text-slate-500">{goalLabel(key, language)}</p><p className="mt-1 break-words text-sm text-slate-100">{display(item)}</p>
    </div>)}
  </div>;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) }, ...init });
  if (!response.ok) {
    const body = await response.text();
    try {
      const parsed = JSON.parse(body);
      throw new Error(parsed.detail ?? body);
    } catch (error) {
      if (error instanceof Error && error.message !== body) throw error;
      throw new Error(body || `HTTP ${response.status}`);
    }
  }
  return response.json();
}

function stepForStatus(status?: string) {
  if (!status || status === 'drafted') return 0;
  if (['blocked', 'needs_clarification'].includes(status)) return 1;
  if (status === 'awaiting_authorization') return 2;
  if (status === 'authorized') return 2;
  if (['running_baseline', 'running_candidate', 'analyzing'].includes(status)) return 3;
  if (status === 'repairing' || status === 'budget_exhausted') return 4;
  return 5;
}

function statusMessage(status: string, t: typeof text.zh | typeof text.en) {
  if (status === 'awaiting_authorization') return t.awaiting;
  if (runningStatuses.has(status)) return t.running;
  if (status === 'evidence_ready') return t.ready;
  if (status === 'budget_exhausted') return t.exhausted;
  if (status === 'blocked' || status === 'needs_clarification') return t.blocked;
  if (status === 'failed') return t.failed;
  return '';
}

function engineStatusLabel(status: EngineCapability['status'] | undefined, t: typeof text.zh | typeof text.en) {
  if (status === 'verified') return t.engineVerified;
  if (status === 'available') return t.engineAvailable;
  if (status === 'build_required') return t.engineBuildRequired;
  return t.engineUnavailable;
}

function statusLabel(status: string, language: Language, novice = false) {
  const labels: Record<Language, Record<string, string>> = {
    zh: { drafted: '等待输入', awaiting_authorization: '等待授权', authorized: '已授权', running_baseline: novice ? '运行修改前' : '运行 Baseline', running_candidate: novice ? '运行修改后' : '运行 Candidate', analyzing: '分析证据', repairing: '自动修复', evidence_ready: '证据就绪', budget_exhausted: '预算耗尽', blocked: '已拦截', needs_clarification: '需要补充', failed: '执行失败', accepted: '已接受', revision_requested: '要求修订', rolled_back: '已回滚' },
    en: { drafted: 'Draft', awaiting_authorization: 'Awaiting authorization', authorized: 'Authorized', running_baseline: 'Running baseline', running_candidate: 'Running candidate', analyzing: 'Analyzing', repairing: 'Repairing', evidence_ready: 'Evidence ready', budget_exhausted: 'Budget exhausted', blocked: 'Blocked', needs_clarification: 'Needs clarification', failed: 'Failed', accepted: 'Accepted', revision_requested: 'Revision requested', rolled_back: 'Rolled back' }
  };
  return labels[language][status] ?? status;
}

function metricLabel(metric: string, language: Language) {
  const labels: Record<Language, Record<string, string>> = {
    zh: { peak_alive_bullets: '峰值存活子弹', player_hits: '玩家受击次数', player_survival_seconds: '玩家生存时间', low_percentile_fps: '低分位 FPS' },
    en: { peak_alive_bullets: 'Peak alive bullets', player_hits: 'Player hits', player_survival_seconds: 'Survival time', low_percentile_fps: 'Low-percentile FPS' }
  };
  return labels[language][metric] ?? metric;
}

function repairLabel(action: string, language: Language) {
  const labels: Record<string, string> = language === 'zh' ? {
    REDUCE_BULLETS_PER_WAVE: '减少每波子弹',
    INCREASE_WAVE_INTERVAL: '增加发射间隔',
    REDUCE_BULLET_SPEED: '降低子弹速度',
    REDUCE_BULLET_LIFETIME: '缩短子弹寿命',
    REDUCE_PATTERN_LAYERS: '减少 Pattern 层数'
  } : {};
  return labels[action] ?? action;
}

function metricValue(metric: string, value: unknown) {
  if (typeof value !== 'number') return display(value);
  if (['low_percentile_fps', 'player_survival_seconds'].includes(metric)) return value.toFixed(2);
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
}

function goalLabel(key: string, language: Language) {
  const labels: Record<string, string> = language === 'zh' ? {
    target_phase_id: '目标阶段',
    requested_pattern: '目标弹幕类型',
    increase_pressure: '提高压迫感',
    preserve_visual_style: '保留视觉风格',
    constraints: '运行约束',
  } : {
    target_phase_id: 'Target phase',
    requested_pattern: 'Requested pattern',
    increase_pressure: 'Increase pressure',
    preserve_visual_style: 'Preserve visual style',
    constraints: 'Runtime constraints',
  };
  return labels[key] ?? key;
}

function eventLabel(step: string, language: Language) {
  const labels: Record<string, string> = language === 'zh' ? {
    'Requirement structured': '需求结构化',
    'Bullet Hell Feasibility Gate': '弹幕能力与安全门',
    'Isolated test budget authorized': '隔离测试预算已授权',
    'Baseline Unity run': 'Unity 基线运行',
    'Candidate Unity run': 'Unity 候选运行',
    'Baseline engine run': '修改前引擎运行',
    'Candidate engine run': '修改后引擎运行',
    'Bounded repair policy': '受约束自动修复',
    'Evidence review': '运行证据审查',
    'Quality Review Agent': '质量审查 Agent',
    'Final human decision': '人工最终决策',
    'Manual Unity playtest': 'Unity 手动试玩',
    'Manual engine playtest': '引擎手动试玩',
    'Workflow execution': '工作流执行',
    'Repair budget': '自动修复预算',
  } : {};
  return labels[step] ?? step;
}

function eventStatusLabel(status: string, language: Language) {
  if (language === 'en') return status;
  const labels: Record<string, string> = {
    completed: '完成',
    accepted: '通过',
    passed: '通过',
    running: '运行中',
    launched: '已启动',
    failed: '失败',
    blocked: '已拦截',
    exhausted: '已耗尽',
    REDUCE_BULLETS_PER_WAVE: '减少每波子弹',
    INCREASE_WAVE_INTERVAL: '增加发射间隔',
    REDUCE_BULLET_SPEED: '降低子弹速度',
    REDUCE_BULLET_LIFETIME: '缩短子弹寿命',
    REDUCE_PATTERN_LAYERS: '减少弹幕层数',
  };
  return labels[status] ?? status;
}

function repairReason(reason: string, language: Language) {
  return language === 'zh'
    ? reason
    : 'Apply a bounded numeric adjustment from the previous Unity evidence while preserving the pattern type.';
}

function display(value: unknown) {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

function readExperienceMode(): ExperienceMode {
  try {
    return window.localStorage.getItem(EXPERIENCE_MODE_KEY) === 'professional' ? 'professional' : 'novice';
  } catch {
    return 'novice';
  }
}

function readGuideDismissed(): boolean {
  try {
    return window.localStorage.getItem(GUIDE_DISMISSED_KEY) === 'true';
  } catch {
    return false;
  }
}

function summarizeVisualChanges(workflow: Workflow, language: Language): string[] {
  const zh = language === 'zh';
  const rows = workflow.config_diff ?? [];
  const result: string[] = [];
  for (const row of rows) {
    if (row.path.endsWith('.bidirectional')) {
      result.push(zh ? '第二阶段：单向螺旋 → 双向螺旋' : 'Phase 2: one-way spiral → bidirectional spiral');
    } else if (row.path.endsWith('.bullets_per_wave')) {
      result.push(zh
        ? `每波子弹：${display(row.before)} → ${display(row.after)}`
        : `Bullets per wave: ${display(row.before)} → ${display(row.after)}`);
    } else if (row.path.endsWith('.bullet_speed')) {
      const repairCount = (workflow.repair_history ?? []).filter((item) => item.action === 'REDUCE_BULLET_SPEED').length;
      const repair = repairCount > 0
        ? (zh ? `（${repairCount} 轮自动修复后）` : ` after ${repairCount} bounded repair${repairCount > 1 ? 's' : ''}`)
        : '';
      result.push(zh
        ? `子弹速度：${display(row.before)} → ${display(row.after)}${repair}`
        : `Bullet speed: ${display(row.before)} → ${display(row.after)}${repair}`);
    }
  }
  return result.length > 0
    ? result
    : [zh ? '当前候选没有可展示的弹幕字段变化。' : 'No visual pattern field changed in this candidate.'];
}
