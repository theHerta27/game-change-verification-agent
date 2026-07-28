import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  Activity, AlertTriangle, ArrowRight, Boxes, CheckCircle2, Code2, Database, FileText, GitBranch,
  Gamepad2, Languages, Play, RefreshCw, Server, Target, UserRound, Wrench, XCircle
} from 'lucide-react';
import './styles.css';
import { ChangeWorkflowPanel } from './ChangeWorkflowPanel';
import { CodeWorkflowPanel } from './CodeWorkflowPanel';
import { CodeChangeAgentPanel } from './CodeChangeAgentPanel';
import { CodeChangeBenchmarkPanel } from './CodeChangeBenchmarkPanel';
import { RealCodeEvaluationPanel } from './RealCodeEvaluationPanel';
import { BulletHellWorkflowPanel } from './BulletHellWorkflowPanel';
import { BulletHellBenchmarkPanel } from './BulletHellBenchmarkPanel';

const API_BASE = '';
type Language = 'zh' | 'en';
type Provider = 'mock' | 'openai_compatible';
type BackendHealth = { status: string; service: string; backend_version?: string; capabilities?: Record<string, boolean> };
type Artifact = { name: string; path: string; size: number };
type ClassicCase = {
  case_id: string; title: string; category: string; requirement_text: string;
  demo_priority: 'main' | 'backup'; expected_observations: string[];
  expected_runtime_targets: Record<string, any>;
};
type EvidenceCheck = {
  check_id: string; target: unknown; actual: unknown; status: 'passed' | 'failed' | 'unavailable';
  evidence: string; risk_reason: string; repair_suggestion: string;
};
type Evidence = {
  case: ClassicCase; generation_mode: string; evaluation_view: string;
  evidence_type: 'runtime_evaluation' | 'static_validation';
  telemetry_source: { label: string; path: string | null } | null;
  design_targets: Record<string, unknown>; checks: EvidenceCheck[];
  risks: Array<{ check_id: string; reason: string }>;
  recommendations: Array<{ check_id: string; suggestion: string }>;
  artifacts: Artifact[];
};
type DemoResult = {
  workflow_summary?: Record<string, unknown>; phase0?: Record<string, any>;
  test_scenarios?: any[]; evaluation?: Record<string, any>; real_run?: Record<string, any>;
  artifacts?: Record<string, Artifact[]>;
};
type BenchmarkResult = {
  benchmark?: { metrics: Record<string, number>; samples: Array<Record<string, any>> };
  artifacts?: Record<string, Artifact[]>;
};
type RuntimeEvaluationResult = {
  passed: boolean; runtime_target_pass_rate: number;
  checks: Array<{ check_id: string; passed: boolean; actual: unknown; expected: unknown }>;
};
type RuntimeRun = {
  run_id: string; case_id: string; case_title: string; provider: string;
  status: 'prepared' | 'launched' | 'evaluated' | 'failed'; mode: 'manual' | 'auto' | null;
  process_id: number | null; steps: Record<string, string>; error?: { type: string; message: string } | null;
  evaluation?: RuntimeEvaluationResult | null;
  telemetry?: Record<string, any> | null;
  improvement_suggestions: Array<{ check_id: string; reason: string; suggestion: string }>;
  available_artifacts: Artifact[];
};

const fallbackRequirement = '设计一个新手武器 Training Sword，基础攻击力 50，可升级 3 次，每级攻击力 +5。升级消耗 Gold 和 Refine Stone。该武器作为新手任务首通奖励，只能领取一次。';

const copy = {
  zh: {
    appTitle: '游戏配置验证工作台', appSubtitle: '将策划需求转成配置，并通过静态校验与 Unity 运行数据验证配置目标。',
    developerTitle: 'Agent 工程调试控制台', plannerMode: '策划 / QA 视图', developerMode: '开发者调试',
    languageButton: 'English', localApi: '本地 API 服务',
    runControls: '运行控制', classicCase: '经典案例', manualInput: '手动输入', main: '核心案例', backup: '专项案例',
    requirement: '配置需求', provider: '模型来源', timeout: '超时时间（秒）',
    mockProvider: 'Mock 模型（确定性演示）', realProvider: '真实模型兼容接口',
    runDemo: '生成并校验当前需求', runBenchmark: '运行离线回归评测（10 个固定样本）',
    benchmarkHint: '检查校验、修复和测试场景生成的稳定性；不会启动 Unity，也不代表真实 LLM 生成质量。',
    workflowSummary: '工作流摘要', timeline: 'Agent / Tool 时间线',
    timelineHint: '“发现配置问题”表示草案未通过校验且可进入修复，不代表工具执行异常。最终结果以“最终校验”为准。',
    runtimeEvaluation: '案例规则证据（补充）', telemetrySource: '运行数据来源', evaluationView: '当前评估视角',
    evidenceType: '证据类型', runtimeEvidence: 'Unity 运行证据', staticEvidence: '静态校验证据',
    mockBoundary: 'Mock 边界', mockBoundaryText: '当前 Mock 固定生成 Training Sword。案例切换只改变需求文本和评估视角，不代表五套模型输出或五个独立 Unity 关卡。',
    latestTrainingSword: '最近一次 Training Sword Unity 实测', noTelemetry: '尚无 Unity telemetry',
    check: '检查项', target: '策划目标', actual: '实际结果', status: '状态', evidence: '证据',
    passed: '通过', failed: '失败', unavailable: '不可用', risks: '风险原因', recommendations: '修复建议',
    artifactEntry: '证据文件', noEvidence: '暂无评估证据。请确认 FastAPI 已启动。',
    generateHint: '未找到运行产物。请运行 Unity 自动回归生成 telemetry 和评估报告。',
    tabs: { blackboard: '黑板追踪', draft: '配置草案', final: '最终配置', validation: '校验错误', review: '审查发现', repair: '修复动作', scenarios: '测试场景' },
    markdownReports: 'Markdown 报告', metrics: '评测指标', benchmark: '离线回归评测',
    badcases: '坏例', artifacts: '产物文件', emptySummary: '运行单样本演示后显示工作流摘要。',
    emptyMetrics: '暂无评测指标。', emptyTimeline: '运行单样本演示后显示 Agent 与工具事件。',
    emptyReport: '选择报告或证据文件后在此预览。', emptyBadcases: '当前没有记录到坏例。',
    emptyArtifacts: '暂无产物文件。', noReports: '运行工作流后可加载 Markdown 报告。',
    reportLoadFailed: '文件加载失败', unexpectedError: '发生未预期错误', backendUnavailable: '无法连接本地 API。请在一个 PowerShell 窗口运行 .\\scripts\\start_backend.ps1，并保持窗口开启；前端默认连接 http://127.0.0.1:8000。', yes: '是', no: '否', none: '暂无',
    realGenerationFailed: '真实模型配置未通过契约校验', realGenerationPassed: '真实模型配置通过静态校验', realFailureSummary: '模型返回了可解析 JSON，但字段结构不符合项目配置契约，因此本次结果不能进入 Unity 试玩。',
    jsonParseCheck: 'JSON 解析', schemaContractCheck: '配置结构契约', finalValidationCheck: '修复后最终校验', parseableJson: '可解析 JSON', validProjectSchema: '符合项目 Schema', finalConfigValid: '最终配置可用',
    providerName: '模型来源', modelName: '模型', schemaIssues: '结构问题', cannotEnterUnity: '错误配置进入运行时会导致引用、读表或玩法逻辑异常。', contractSuggestion: '根据具体字段错误收紧 Prompt Contract 或修复输出，再重新校验。',
    backendOutdated: '当前 FastAPI 后端仍是旧版本，不支持真实配置交接 Unity。请在后端 PowerShell 窗口按 Ctrl+C，然后重新运行 .\\scripts\\start_backend.ps1。',
    statusIssues: '发现配置问题', statusSucceeded: '成功', statusFailed: '执行失败', statusRecorded: '已记录',
    badcaseStage: '阶段'
    ,guidedRun: 'Unity 引导验证', guidedSubtitle: '把当前需求、配置快照、Unity 试玩和本次 telemetry 串成一个独立 run。',
    stepRequirement: '1. 配置需求', stepStatic: '2. 静态校验', stepUnity: '3. Unity 试玩', stepEvaluation: '4. 运行评测', stepSuggestion: '5. 改进建议',
    stepPending: '等待', stepReady: '就绪', stepProgress: '进行中', stepComplete: '完成',
    validateFirst: '请先点击“生成并校验当前需求”，最终校验通过后才能准备 Unity 测试。',
    prepareUnity: '准备本次 Unity 测试', launchManual: '打开 Unity 手动试玩', launchAuto: '运行 Unity 自动回归',
    unityRunning: 'Unity 已启动。完成试玩后 telemetry 会写入本次 run，此页面将自动轮询评测结果。',
    mockOnlyRun: '真实配置会在准备 Unity 测试时由后端再次执行 Schema、Reference 和 Rule 校验，通过后保存为本次 run 的独立快照。',
    staticOnlyRun: '该案例属于静态引用校验，不需要启动 Unity。请查看下方静态证据。',
    manualNeedsCase: '手动输入仍需选择一个经典案例作为 Unity 场景和验收目标。',
    runId: '本次运行', runMode: '运行模式', manualMode: '手动试玩', autoMode: '自动回归',
    runResult: '本次运行结果', businessFailed: 'Unity 正常完成，但存在未达到的策划目标。',
    runPassed: '本次运行达到全部策划目标。', runFailed: '运行任务失败', runArtifacts: '本次运行证据'
    ,validationConclusion: '本次验证结论', keyRisks: '关键风险', nextAction: '下一步建议',
    waitingConclusion: '等待验证', waitingSummary: '选择案例并生成配置后，启动 Unity 试玩获得本次实测结果。',
    staticReadySummary: '静态校验已通过，下一步准备并启动 Unity 试玩。', runningSummary: 'Unity 试玩进行中，完成关卡后将自动生成结论。',
    preparedSummary: '本次配置与 Unity Contract 已准备完成，等待启动试玩。', passedSummary: '本次配置达到当前全部策划目标。',
    failedSummary: '本次验证未通过', issueUnit: '个关键问题', noRisk: '当前没有发现关键风险。',
    resultTable: '策划目标与实测结果', impact: '影响', suggestion: '建议', currentMetrics: '本次试玩概览',
    clearTime: '通关时间', enemyCount: '击败敌人数', skillCount: '技能使用次数', goldEarned: '获得金币', goldSpent: '消耗金币',
    seconds: '秒', enemies: '个', times: '次', gold: '金币', developerHint: 'Agent 执行过程、JSON、离线回归和产物已收纳到开发者调试视图。',
    guidedPlannerSubtitle: '按顺序完成配置校验和 Unity 试玩，系统会自动读取本次结果。', noMeasuredResult: '尚无本次试玩数据。完成 Unity 试玩后显示目标与实测对比。'
  },
  en: {
    appTitle: 'Game Config Validation Workspace', appSubtitle: 'Turn design requirements into configs and validate targets with static checks and Unity runtime data.',
    developerTitle: 'Agent Engineering Debug Console', plannerMode: 'Designer / QA', developerMode: 'Developer Debug',
    languageButton: '中文', localApi: 'Local API service',
    runControls: 'Run controls', classicCase: 'Classic case', manualInput: 'Manual input', main: 'Main demo', backup: 'Backup',
    requirement: 'Requirement', provider: 'Provider', timeout: 'Timeout seconds',
    mockProvider: 'Mock provider (deterministic)', realProvider: 'OpenAI-compatible provider',
    runDemo: 'Generate and validate requirement', runBenchmark: 'Run offline regression (10 fixtures)',
    benchmarkHint: 'Checks validation, repair, and test-scenario stability. It does not launch Unity or measure real-LLM generation quality.',
    workflowSummary: 'Workflow summary', timeline: 'Agent / Tool timeline',
    timelineHint: 'Issues found means the draft can enter repair; it does not mean the tool crashed. Use Final Validation for the workflow outcome.',
    runtimeEvaluation: 'Case Rule Evidence (Supplement)', telemetrySource: 'Telemetry source', evaluationView: 'Evaluation view',
    evidenceType: 'Evidence type', runtimeEvidence: 'Unity runtime evidence', staticEvidence: 'Static validation evidence',
    mockBoundary: 'Mock boundary', mockBoundaryText: 'The Mock always generates Training Sword. Case selection changes requirement text and evaluation view, not five model outputs or five Unity levels.',
    latestTrainingSword: 'Latest Training Sword Unity runtime run', noTelemetry: 'No Unity telemetry',
    check: 'Check', target: 'Design target', actual: 'Actual', status: 'Status', evidence: 'Evidence',
    passed: 'Passed', failed: 'Failed', unavailable: 'Unavailable', risks: 'Risk reasons', recommendations: 'Repair suggestions',
    artifactEntry: 'Evidence files', noEvidence: 'No evaluation evidence. Check that FastAPI is running.',
    generateHint: 'Runtime artifacts are missing. Run the Unity auto smoke to generate telemetry and the report.',
    tabs: { blackboard: 'Blackboard trace', draft: 'Draft config', final: 'Final config', validation: 'Validation errors', review: 'Review findings', repair: 'Repair actions', scenarios: 'Test scenarios' },
    markdownReports: 'Markdown reports', metrics: 'Evaluation metrics', benchmark: 'Phase 3 benchmark',
    badcases: 'Badcases', artifacts: 'Artifacts', emptySummary: 'Run a sample to show the workflow summary.',
    emptyMetrics: 'No metrics yet.', emptyTimeline: 'Run a sample to show Agent and tool events.',
    emptyReport: 'Select a report or evidence file to preview it.', emptyBadcases: 'No badcases recorded.',
    emptyArtifacts: 'No artifacts yet.', noReports: 'Run a workflow to load Markdown reports.',
    reportLoadFailed: 'File loading failed', unexpectedError: 'Unexpected error', backendUnavailable: 'Cannot reach the local API. Run .\\scripts\\start_backend.ps1 in a PowerShell window and keep it open. The frontend connects to http://127.0.0.1:8000 by default.', yes: 'Yes', no: 'No', none: 'N/A',
    realGenerationFailed: 'Real model config failed contract validation', realGenerationPassed: 'Real model config passed static validation', realFailureSummary: 'The model returned parseable JSON, but its fields did not match the project config contract, so this result cannot enter the Unity playtest.',
    jsonParseCheck: 'JSON parsing', schemaContractCheck: 'Config schema contract', finalValidationCheck: 'Final validation after repair', parseableJson: 'Parseable JSON', validProjectSchema: 'Matches project schema', finalConfigValid: 'Final config is valid',
    providerName: 'Provider', modelName: 'Model', schemaIssues: 'Schema issues', cannotEnterUnity: 'Invalid configs can break references, table loading, or runtime behavior.', contractSuggestion: 'Tighten the prompt contract or repair the listed fields, then validate again.',
    backendOutdated: 'The FastAPI process is an older version and cannot hand real configs to Unity. Press Ctrl+C in the backend PowerShell window, then run .\\scripts\\start_backend.ps1 again.',
    statusIssues: 'Issues found', statusSucceeded: 'Succeeded', statusFailed: 'Execution failed', statusRecorded: 'Recorded',
    badcaseStage: 'Stage'
    ,guidedRun: 'Guided Unity Validation', guidedSubtitle: 'Bind the requirement, config snapshot, Unity playtest, and telemetry to one isolated run.',
    stepRequirement: '1. Requirement', stepStatic: '2. Static validation', stepUnity: '3. Unity playtest', stepEvaluation: '4. Runtime evaluation', stepSuggestion: '5. Suggestions',
    stepPending: 'Pending', stepReady: 'Ready', stepProgress: 'In progress', stepComplete: 'Completed',
    validateFirst: 'Generate and validate the requirement before preparing a Unity run.',
    prepareUnity: 'Prepare Unity run', launchManual: 'Open Unity manual playtest', launchAuto: 'Run Unity auto regression',
    unityRunning: 'Unity is running. This page polls the isolated run and evaluates its telemetry after completion.',
    mockOnlyRun: 'Before a real config enters Unity, the backend re-runs Schema, Reference, and Rule validation and stores an isolated snapshot for this run.',
    staticOnlyRun: 'This case uses static reference evidence and does not launch Unity.',
    manualNeedsCase: 'Select a classic case to supply Unity scenario targets for manual input.',
    runId: 'Run', runMode: 'Mode', manualMode: 'Manual playtest', autoMode: 'Auto regression',
    runResult: 'Run result', businessFailed: 'Unity completed, but one or more design targets failed.',
    runPassed: 'All runtime design targets passed.', runFailed: 'Runtime task failed', runArtifacts: 'Run evidence'
    ,validationConclusion: 'Validation conclusion', keyRisks: 'Key risks', nextAction: 'Next action',
    waitingConclusion: 'Waiting for validation', waitingSummary: 'Select a case, generate the config, and launch Unity to collect this run\'s evidence.',
    staticReadySummary: 'Static validation passed. Prepare and launch the Unity playtest next.', runningSummary: 'Unity playtest is running. Results appear after the scenario completes.',
    preparedSummary: 'This run\'s config and Unity contract are ready to launch.', passedSummary: 'All current design targets passed.',
    failedSummary: 'Validation failed', issueUnit: 'key issues', noRisk: 'No key risks found.',
    resultTable: 'Design targets and measured results', impact: 'Impact', suggestion: 'Suggestion', currentMetrics: 'Playtest overview',
    clearTime: 'Clear time', enemyCount: 'Enemies defeated', skillCount: 'Skill uses', goldEarned: 'Gold earned', goldSpent: 'Gold spent',
    seconds: 's', enemies: '', times: '', gold: 'gold', developerHint: 'Agent traces, JSON, offline regression, and artifacts are available in Developer Debug.',
    guidedPlannerSubtitle: 'Complete static validation and the Unity playtest in order; results are collected automatically.', noMeasuredResult: 'No measured playtest result yet. Complete the Unity run to compare targets and actuals.'
  }
} as const;

const caseTitles: Record<Language, Record<string, string>> = {
  zh: {
    case_01_baseline_trial: '标准新手试炼关卡', case_02_reward_overgrant: '首通奖励过量风险',
    case_03_combat_too_fast: '关卡节奏过快风险', case_04_missing_reference: 'Trial Medal 引用缺失',
    case_05_skill_guidance_balance: '技能引导与战斗平衡'
  },
  en: {
    case_01_baseline_trial: 'Baseline beginner trial', case_02_reward_overgrant: 'First-clear reward overgrant',
    case_03_combat_too_fast: 'Combat pacing too fast', case_04_missing_reference: 'Missing Trial Medal reference',
    case_05_skill_guidance_balance: 'Skill guidance and balance'
  }
};

type BusinessRow = {
  checkId: string; label: string; target: string; actual: string;
  passed: boolean | null; impact: string; suggestion: string;
};

const businessMessages: Record<Language, Record<string, { impact: string; suggestion: string }>> = {
  zh: {
    run_completed: { impact: '关卡未完成时，其他体验指标缺少有效参考。', suggestion: '检查玩家生存、敌人压力和关卡完成条件。' },
    completion_time_in_target: { impact: '过快会削弱教学和成长节奏，过慢会增加新手挫败。', suggestion: '调整敌人耐久、波次压力或玩家输出后重新试玩。' },
    completion_time: { impact: '关卡节奏与策划目标不一致。', suggestion: '调整敌人耐久、波次压力或玩家输出。' },
    normal_enemy_hits_to_kill_in_target: { impact: '影响基础攻击手感和普通敌人的威胁感。', suggestion: '调整武器攻击力或普通敌人生命值。' },
    enemies_defeated: { impact: '击败数量异常可能表示波次、生成或结算配置有误。', suggestion: '检查波次配置和敌人生成记录。' },
    skill_usage: { impact: '技能未被使用，无法证明技能在当前关卡中有实际作用。', suggestion: '检查技能可见性、冷却、范围和战斗引导。' },
    first_upgrade_affordable: { impact: '首通后无法升级会中断预期的新手成长反馈。', suggestion: '提高首通奖励或降低第一次升级成本。' },
    first_upgrade: { impact: '首通资源不足会中断第一次成长反馈。', suggestion: '调整首通 Gold、Refine Stone 或第一次升级成本。' },
    second_upgrade_affordable: { impact: '连续升级两次会压缩新手期成长节奏。', suggestion: '降低首通奖励或提高第二次升级成本。' },
    second_upgrade_after_first: { impact: '首通后连续升级两次会造成奖励过量。', suggestion: '同时检查 Gold 和 Refine Stone，收紧首通资源。' },
    trial_medal_reference: { impact: '缺失引用会导致升级材料无法被运行时正确解析。', suggestion: '补齐 Trial Medal 定义后重新执行引用校验。' },
    trial_medal_repair: { impact: '无边界修复可能引入错误资源定义。', suggestion: '只允许从确定性资源目录补齐已知材料。' }
  },
  en: {
    run_completed: { impact: 'Other experience metrics are unreliable when the scenario is incomplete.', suggestion: 'Check survival, encounter pressure, and completion conditions.' },
    completion_time_in_target: { impact: 'A fast run weakens pacing; a slow run increases beginner frustration.', suggestion: 'Tune durability, wave pressure, or player output and replay.' },
    completion_time: { impact: 'Encounter pacing does not match the design target.', suggestion: 'Tune durability, wave pressure, or player output.' },
    normal_enemy_hits_to_kill_in_target: { impact: 'Changes basic-attack feel and normal-enemy pressure.', suggestion: 'Tune weapon attack or normal-enemy health.' },
    enemies_defeated: { impact: 'An unexpected count may indicate wave, spawn, or completion issues.', suggestion: 'Check wave config and spawn telemetry.' },
    skill_usage: { impact: 'No skill use means the current run cannot validate skill usefulness.', suggestion: 'Review skill visibility, cooldown, range, and guidance.' },
    first_upgrade_affordable: { impact: 'An unaffordable first upgrade breaks the intended growth reward.', suggestion: 'Increase the reward or lower the first upgrade cost.' },
    first_upgrade: { impact: 'Insufficient first-clear resources interrupt initial progression.', suggestion: 'Tune Gold, Refine Stone, or first upgrade cost.' },
    second_upgrade_affordable: { impact: 'Two immediate upgrades compress early progression.', suggestion: 'Reduce rewards or increase the second upgrade cost.' },
    second_upgrade_after_first: { impact: 'Two upgrades after first clear indicate reward overgrant.', suggestion: 'Tighten both Gold and Refine Stone grants.' },
    trial_medal_reference: { impact: 'A missing reference prevents the runtime from resolving the material.', suggestion: 'Add Trial Medal and rerun reference validation.' },
    trial_medal_repair: { impact: 'Unbounded repair can introduce an invalid resource definition.', suggestion: 'Only repair resources present in the deterministic catalog.' }
  }
};
const checkLabels: Record<Language, Record<string, string>> = {
  zh: { completion_time: '通关时间', enemies_defeated: '敌人击败数', skill_usage: '技能使用', first_upgrade: '首通后完成第一次升级', second_upgrade_after_first: '第一次升级后仍可完成第二次升级', trial_medal_reference: 'Trial Medal 引用完整性', trial_medal_repair: '受约束引用修复', run_completed: '关卡是否完成', completion_time_in_target: '通关时间', normal_enemy_hits_to_kill_in_target: '普通敌人击杀次数', first_upgrade_affordable: '第一次升级可支付', second_upgrade_affordable: '第二次升级不可连续支付' },
  en: { completion_time: 'Clear time', enemies_defeated: 'Enemies defeated', skill_usage: 'Skill usage', first_upgrade: 'First upgrade after first clear', second_upgrade_after_first: 'Second upgrade after first upgrade', trial_medal_reference: 'Trial Medal reference', trial_medal_repair: 'Bounded reference repair', run_completed: 'Run completed', completion_time_in_target: 'Clear time', normal_enemy_hits_to_kill_in_target: 'Normal enemy hits to kill', first_upgrade_affordable: 'First upgrade affordable', second_upgrade_affordable: 'Second upgrade not consecutively affordable' }
};

function App() {
  const [language, setLanguage] = useState<Language>('zh');
  const [viewMode, setViewMode] = useState<'planner' | 'developer'>('planner');
  const [plannerTool, setPlannerTool] = useState<'bullet' | 'legacy'>('bullet');
  const [cases, setCases] = useState<ClassicCase[]>([]);
  const [selectedCase, setSelectedCase] = useState('case_01_baseline_trial');
  const [requirement, setRequirement] = useState(fallbackRequirement);
  const [provider, setProvider] = useState<Provider>('mock');
  const [timeoutSeconds, setTimeoutSeconds] = useState(60);
  const [evidence, setEvidence] = useState<Evidence | null>(null);
  const [demo, setDemo] = useState<DemoResult | null>(null);
  const [benchmark, setBenchmark] = useState<BenchmarkResult | null>(null);
  const [runtimeRun, setRuntimeRun] = useState<RuntimeRun | null>(null);
  const [selectedReport, setSelectedReport] = useState('');
  const [reportText, setReportText] = useState('');
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [backendHealth, setBackendHealth] = useState<BackendHealth | null>(null);
  const [generatedCodeWorkflowId, setGeneratedCodeWorkflowId] = useState<string | null>(null);
  const t = copy[language];

  useEffect(() => {
    getJson<BackendHealth>('/api/health').then(setBackendHealth).catch((err) => setError(messageFromError(err, language)));
    getJson<{ cases: ClassicCase[] }>('/api/classic-cases').then(({ cases: loaded }) => {
      setCases(loaded);
      const baseline = loaded.find((item) => item.case_id === 'case_01_baseline_trial');
      if (baseline) setRequirement(baseline.requirement_text);
    }).catch((err) => setError(messageFromError(err, language)));
  }, []);

  useEffect(() => {
    if (selectedCase === 'manual') { setEvidence(null); return; }
    getJson<Evidence>(`/api/evaluation-evidence?case_id=${encodeURIComponent(selectedCase)}`)
      .then(setEvidence).catch((err) => setError(messageFromError(err, language)));
  }, [selectedCase]);

  useEffect(() => {
    if (!runtimeRun || runtimeRun.status !== 'launched') return;
    const timer = window.setInterval(() => {
      getJson<RuntimeRun>(`/api/runtime-runs/${runtimeRun.run_id}`)
        .then(setRuntimeRun)
        .catch((err) => setError(messageFromError(err, language)));
    }, 1500);
    return () => window.clearInterval(timer);
  }, [runtimeRun?.run_id, runtimeRun?.status]);

  const metrics = benchmark?.benchmark?.metrics ?? demo?.real_run?.metrics ?? demo?.evaluation ?? {};
  const realSample = demo?.real_run?.results?.[0];
  const trace = demo?.phase0?.trace ?? realSample?.trace ?? [];
  const displayDraft = demo?.phase0?.draft_configs ?? realSample?.draft_configs ?? {};
  const displayFinal = demo?.phase0?.repaired_configs ?? realSample?.repaired_configs ?? {};
  const displayValidation = demo?.phase0?.validation_errors ?? [
    ...(realSample?.draft_validation?.schema_errors ?? []),
    ...(realSample?.draft_validation?.reference_errors ?? []),
    ...(realSample?.draft_validation?.rule_errors ?? [])
  ];
  const displayReview = demo?.phase0?.review_findings ?? realSample?.review_findings ?? [];
  const displayRepair = demo?.phase0?.repair_actions ?? realSample?.repair_actions ?? [];
  const badcases = benchmark?.benchmark?.samples?.flatMap((sample) => sample.badcases ?? [])
    ?? demo?.real_run?.results?.flatMap((sample: any) => sample.badcases ?? []) ?? [];
  const allArtifacts = {
    ...demo?.artifacts, ...benchmark?.artifacts,
    ...(evidence?.artifacts.length ? { unity: evidence.artifacts } : {})
  };
  const activeCase = cases.find((item) => item.case_id === selectedCase) ?? null;

  function chooseCase(caseId: string) {
    setSelectedCase(caseId);
    setDemo(null);
    setRuntimeRun(null);
    if (caseId !== 'manual') {
      const chosen = cases.find((item) => item.case_id === caseId);
      if (chosen) setRequirement(chosen.requirement_text);
    }
  }
  async function runDemo() {
    setLoading('demo'); setError(''); setDemo(null); setRuntimeRun(null);
    try {
      setDemo(await postJson('/api/runs/demo', { requirement_text: requirement, provider, timeout_seconds: timeoutSeconds }));
    } catch (err) { setError(messageFromError(err, language)); }
    finally { setLoading(null); }
  }
  async function prepareRuntimeRun() {
    if (provider === 'openai_compatible' && backendHealth?.capabilities?.real_provider_runtime_handoff !== true) {
      setError(t.backendOutdated);
      return;
    }
    setLoading('runtime-prepare'); setError('');
    try {
      const realResult = demo?.real_run?.results?.[0];
      const payload = provider === 'openai_compatible'
        ? {
            case_id: selectedCase, requirement_text: requirement, provider,
            structured_requirement: realResult?.structured_requirement,
            final_configs: realResult?.repaired_configs,
            model: demo?.real_run?.model ?? null
          }
        : { case_id: selectedCase, requirement_text: requirement, provider };
      setRuntimeRun(await postJson('/api/runtime-runs', payload));
    } catch (err) { setError(messageFromError(err, language)); }
    finally { setLoading(null); }
  }
  async function launchRuntimeRun(mode: 'manual' | 'auto') {
    if (!runtimeRun) return;
    setLoading(`runtime-${mode}`); setError('');
    try { setRuntimeRun(await postJson(`/api/runtime-runs/${runtimeRun.run_id}/launch`, { mode })); }
    catch (err) { setError(messageFromError(err, language)); }
    finally { setLoading(null); }
  }
  async function loadRuntimeArtifact(name: string) {
    if (!runtimeRun) return;
    setSelectedReport(`${runtimeRun.run_id}/${name}`); setError('');
    try {
      const response = await fetch(`${API_BASE}/api/runtime-runs/${runtimeRun.run_id}/artifacts/${name}`);
      if (!response.ok) throw new Error(await response.text());
      setReportText(await response.text());
    } catch (err) { setError(`${t.reportLoadFailed}: ${messageFromError(err, language)}`); }
  }
  async function runBenchmark() {
    setLoading('benchmark'); setError('');
    try { setBenchmark(await postJson('/api/runs/benchmark', { output: 'outputs/phase3' })); }
    catch (err) { setError(messageFromError(err, language)); }
    finally { setLoading(null); }
  }
  async function loadReport(path: string) {
    setSelectedReport(path); setError('');
    try {
      const [phase, name] = path.split('/');
      const response = await fetch(`${API_BASE}/api/reports/${phase}/${name}`);
      if (!response.ok) throw new Error(await response.text());
      setReportText(await response.text());
    } catch (err) { setError(`${t.reportLoadFailed}: ${messageFromError(err, language)}`); }
  }

  const controls = <RunControls
    language={language} cases={cases} selectedCase={selectedCase} requirement={requirement}
    provider={provider} timeoutSeconds={timeoutSeconds} loading={loading} error={error}
    showDemo={viewMode === 'developer'} showBenchmark={viewMode === 'developer'} onChooseCase={chooseCase}
    onRequirement={(value) => { setRequirement(value); setDemo(null); setRuntimeRun(null); if (selectedCase !== 'manual') setSelectedCase('manual'); }}
    onProvider={(value) => { setProvider(value); setDemo(null); setRuntimeRun(null); setError(''); }} onTimeout={setTimeoutSeconds} onRunDemo={runDemo} onBenchmark={runBenchmark}
  />;

  return <main className="min-h-screen bg-ink text-slate-100">
    <header className="border-b border-line bg-panel/95 px-5 py-4">
      <div className="mx-auto flex max-w-[1800px] flex-wrap items-center justify-between gap-4">
        <div className="max-w-3xl">
          <p className="text-xs uppercase text-run">GameConfig Agent</p>
          <h1 className="mt-1 text-2xl font-semibold">{viewMode === 'planner' ? t.appTitle : t.developerTitle}</h1>
          <p className="mt-1 text-sm leading-6 text-slate-400">{viewMode === 'planner' ? t.appSubtitle : t.developerHint}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex rounded-md border border-line bg-slate-950 p-1">
            <button className={`${viewMode === 'planner' ? 'tab-active' : 'tab'} flex items-center gap-2`} onClick={() => setViewMode('planner')}><UserRound className="h-4 w-4"/>{t.plannerMode}</button>
            <button className={`${viewMode === 'developer' ? 'tab-active' : 'tab'} flex items-center gap-2`} onClick={() => setViewMode('developer')}><Code2 className="h-4 w-4"/>{t.developerMode}</button>
          </div>
          <button className="button-secondary px-3" onClick={() => setLanguage(language === 'zh' ? 'en' : 'zh')}><Languages className="h-4 w-4"/>{t.languageButton}</button>
          <div className="hidden items-center gap-2 rounded-md border border-line bg-panel2 px-3 py-2 text-sm text-slate-300 md:flex"><Server className="h-4 w-4 text-run"/>{t.localApi}{backendHealth?.backend_version ? ` · ${backendHealth.backend_version}` : ''}</div>
        </div>
      </div>
    </header>

    {viewMode === 'planner' ? <div className="mx-auto max-w-[1700px] p-4">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3 border-b border-line pb-3">
        <div className="flex rounded-md border border-line bg-panel p-1">
          <button className={plannerTool === 'bullet' ? 'tab-active' : 'tab'} onClick={() => setPlannerTool('bullet')}>弹幕变更验证</button>
          <button className={plannerTool === 'legacy' ? 'tab-active' : 'tab'} onClick={() => setPlannerTool('legacy')}>Training Sword 旧回归</button>
        </div>
        {plannerTool === 'bullet' && <div className="grid grid-cols-2 gap-2 text-xs text-slate-400">
          <span>Provider: {provider}</span><span>Timeout: {timeoutSeconds}s</span>
        </div>}
      </div>
      {plannerTool === 'bullet'
        ? <BulletHellWorkflowPanel
            language={language}
            provider={provider}
            timeoutSeconds={timeoutSeconds}
            onProvider={setProvider}
            onTimeout={setTimeoutSeconds}
          />
        : <div className="grid grid-cols-1 gap-4 xl:grid-cols-[360px_minmax(0,1fr)]"><aside>{controls}</aside><section><ChangeWorkflowPanel language={language} requirement={requirement} caseId={selectedCase} provider={provider} timeoutSeconds={timeoutSeconds}/></section></div>}
    </div> : <div className="mx-auto grid max-w-[1800px] grid-cols-1 gap-4 p-4 xl:grid-cols-[360px_minmax(0,1fr)_360px]">
      <aside className="space-y-4">{controls}<Panel title={t.workflowSummary} icon={<Activity className="h-4 w-4"/>}><KeyValue data={demo?.workflow_summary ?? { status: t.emptySummary }} language={language}/></Panel></aside>
      <section className="space-y-4">
        <BulletHellBenchmarkPanel language={language}/>
        <CodeChangeAgentPanel language={language} provider={provider} timeoutSeconds={timeoutSeconds} onGenerated={setGeneratedCodeWorkflowId}/>
        <CodeChangeBenchmarkPanel language={language}/>
        <RealCodeEvaluationPanel language={language} timeoutSeconds={timeoutSeconds}/>
        <CodeWorkflowPanel language={language} provider={provider} timeoutSeconds={timeoutSeconds} loadWorkflowId={generatedCodeWorkflowId}/>
        <GuidedRuntimePanel language={language} selectedCase={selectedCase} provider={provider} demo={demo}
          runtimeRun={runtimeRun} loading={loading} onPrepare={prepareRuntimeRun} onLaunch={launchRuntimeRun}
          onArtifact={loadRuntimeArtifact}/>
        <RuntimeEvidencePanel evidence={evidence} language={language} onLoad={loadReport}/>
        <Panel title={t.timeline} icon={<GitBranch className="h-4 w-4"/>}><p className="mb-3 text-xs leading-5 text-slate-400">{t.timelineHint}</p><Timeline events={trace} language={language}/></Panel>
        <Tabs tabs={[
          { label: t.tabs.blackboard, content: <JsonBlock value={trace}/> },
          { label: t.tabs.draft, content: <JsonBlock value={displayDraft}/> },
          { label: t.tabs.final, content: <JsonBlock value={displayFinal}/> },
          { label: t.tabs.validation, content: <JsonBlock value={displayValidation}/> },
          { label: t.tabs.review, content: <JsonBlock value={displayReview}/> },
          { label: t.tabs.repair, content: <JsonBlock value={displayRepair}/> },
          { label: t.tabs.scenarios, content: <JsonBlock value={demo?.test_scenarios ?? []}/> }
        ]}/>
        <Panel title={t.markdownReports} icon={<FileText className="h-4 w-4"/>}><ReportPicker artifacts={allArtifacts} onLoad={loadReport} selected={selectedReport} language={language}/><pre className="mt-3 max-h-80 overflow-auto rounded-md bg-slate-950 p-4 text-sm text-slate-200">{reportText || t.emptyReport}</pre></Panel>
      </section>
      <aside className="space-y-4">
        <Panel title={t.metrics} icon={<Boxes className="h-4 w-4"/>}><MetricGrid data={metrics} language={language}/></Panel>
        <Panel title={t.benchmark} icon={<Activity className="h-4 w-4"/>}><MetricGrid data={benchmark?.benchmark?.metrics ?? { sample_count: 0 }} language={language}/></Panel>
        <Panel title={t.badcases} icon={<AlertTriangle className="h-4 w-4"/>}><BadcaseList badcases={badcases} language={language}/></Panel>
        <Panel title={t.artifacts} icon={<Wrench className="h-4 w-4"/>}><ArtifactList artifacts={allArtifacts} language={language}/></Panel>
      </aside>
    </div>}
  </main>;
}

function RunControls({ language, cases, selectedCase, requirement, provider, timeoutSeconds, loading, error, showDemo, showBenchmark, onChooseCase, onRequirement, onProvider, onTimeout, onRunDemo, onBenchmark }: {
  language: Language; cases: ClassicCase[]; selectedCase: string; requirement: string; provider: Provider;
  timeoutSeconds: number; loading: string | null; error: string; showDemo: boolean; showBenchmark: boolean;
  onChooseCase: (caseId: string) => void; onRequirement: (value: string) => void;
  onProvider: (provider: Provider) => void; onTimeout: (value: number) => void;
  onRunDemo: () => void; onBenchmark: () => void;
}) {
  const t = copy[language];
  return <Panel title={t.runControls} icon={<Target className="h-4 w-4"/>}>
    <label className="label" htmlFor="classic-case">{t.classicCase}</label>
    <select id="classic-case" className="input" value={selectedCase} onChange={(event) => onChooseCase(event.target.value)}>
      {cases.map((item) => <option key={item.case_id} value={item.case_id}>{caseTitles[language][item.case_id] ?? item.case_id} · {item.demo_priority === 'main' ? t.main : t.backup}</option>)}
      <option value="manual">{t.manualInput}</option>
    </select>
    <label className="label mt-4" htmlFor="requirement">{t.requirement}</label>
    <textarea id="requirement" className="input min-h-40 resize-y" value={requirement} onChange={(event) => onRequirement(event.target.value)}/>
    <div className="mt-4 grid grid-cols-2 gap-3">
      <div><label className="label" htmlFor="provider">{t.provider}</label><select id="provider" className="input" value={provider} onChange={(event) => onProvider(event.target.value as Provider)}><option value="mock">{t.mockProvider}</option><option value="openai_compatible">{t.realProvider}</option></select></div>
      <div><label className="label" htmlFor="timeout">{t.timeout}</label><input id="timeout" className="input" type="number" min={5} max={300} value={timeoutSeconds} onChange={(event) => onTimeout(Number(event.target.value))}/></div>
    </div>
    <div className="mt-4 grid gap-2">
      {showDemo && <button className="button-primary" disabled={loading !== null} onClick={onRunDemo}>{loading === 'demo' ? <RefreshCw className="h-4 w-4 animate-spin"/> : <Play className="h-4 w-4"/>}{t.runDemo}</button>}
      {showBenchmark && <><button className="button-secondary" disabled={loading !== null} onClick={onBenchmark}>{loading === 'benchmark' ? <RefreshCw className="h-4 w-4 animate-spin"/> : <GitBranch className="h-4 w-4"/>}{t.runBenchmark}</button><p className="text-xs leading-5 text-slate-400">{t.benchmarkHint}</p></>}
    </div>
    {error && <div className="mt-4 rounded-md border border-bad/50 bg-bad/10 p-3 text-sm text-red-100">{error}</div>}
  </Panel>;
}

function BusinessConclusion({ language, demo, runtimeRun, evidence, selectedCase, activeCase }: { language: Language; demo: DemoResult | null; runtimeRun: RuntimeRun | null; evidence: Evidence | null; selectedCase: string; activeCase: ClassicCase | null }) {
  const t = copy[language];
  const rows = buildBusinessRows(language, selectedCase, activeCase, runtimeRun, evidence);
  const failed = rows.filter((row) => row.passed === false);
  const real = realRunView(demo, language);
  const resultAvailable = selectedCase === 'case_04_missing_reference' || runtimeRun?.status === 'evaluated';
  const visibleFailed = resultAvailable ? failed : [];
  let tone: 'waiting' | 'passed' | 'failed' = 'waiting';
  let title: string = t.waitingConclusion;
  let summary: string = t.waitingSummary;
  if (real && !real.finalPassed && !runtimeRun) {
    tone = 'failed'; title = t.realGenerationFailed; summary = t.realFailureSummary;
  } else if (selectedCase === 'case_04_missing_reference' && rows.length) {
    tone = failed.length ? 'failed' : 'passed'; title = failed.length ? `${t.failedSummary}：${failed.length} ${t.issueUnit}` : t.runPassed; summary = failed[0]?.impact ?? t.noRisk;
  } else if (runtimeRun?.status === 'failed') {
    tone = 'failed'; title = t.runFailed; summary = runtimeRun.error?.message ?? t.runFailed;
  } else if (runtimeRun?.status === 'evaluated') {
    tone = failed.length ? 'failed' : 'passed'; title = failed.length ? `${t.failedSummary}：${failed.length} ${t.issueUnit}` : t.runPassed; summary = failed.length ? failed.map((row) => row.label).join(language === 'zh' ? '、' : ', ') : t.passedSummary;
  } else if (runtimeRun?.status === 'launched') {
    title = t.stepProgress; summary = t.runningSummary;
  } else if (runtimeRun?.status === 'prepared') {
    title = t.stepReady; summary = t.preparedSummary;
  } else if (real?.finalPassed) {
    tone = 'passed'; title = t.realGenerationPassed; summary = t.staticReadySummary;
  } else if (demo?.workflow_summary?.final_validation_passed === true) {
    title = t.stepReady; summary = t.staticReadySummary;
  }
  const showingRuntimeResult = runtimeRun?.status === 'evaluated';
  const riskCount = showingRuntimeResult ? visibleFailed.length : real ? real.badcases.length : visibleFailed.length;
  const next = real && !real.finalPassed && !runtimeRun ? real.firstError ?? t.contractSuggestion : visibleFailed[0]?.suggestion ?? (tone === 'passed' ? t.noRisk : summary);
  const styles = tone === 'failed' ? 'border-red-400/60 bg-red-400/10' : tone === 'passed' ? 'border-run/60 bg-run/10' : 'border-sky-400/50 bg-sky-400/5';
  return <section className={`border-l-4 p-5 ${styles}`}>
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div><div className="text-xs font-semibold text-slate-400">{t.validationConclusion}</div><h2 className="mt-2 text-xl font-semibold text-slate-50">{title}</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-300">{summary}</p></div>
      <div className="min-w-32 border-l border-line pl-4"><div className="text-xs text-slate-400">{t.keyRisks}</div><div className="mt-1 font-mono text-3xl font-semibold text-slate-50">{riskCount}</div></div>
    </div>
    <div className="mt-4 flex items-start gap-2 border-t border-line/70 pt-3 text-sm text-slate-200"><ArrowRight className="mt-0.5 h-4 w-4 shrink-0 text-run"/><div><strong>{t.nextAction}：</strong>{next}</div></div>
  </section>;
}

function PlannerResults({ language, activeCase, selectedCase, demo, runtimeRun, evidence }: { language: Language; activeCase: ClassicCase | null; selectedCase: string; demo: DemoResult | null; runtimeRun: RuntimeRun | null; evidence: Evidence | null }) {
  const t = copy[language];
  const real = realRunView(demo, language);
  const showRealGate = real && runtimeRun?.status !== 'evaluated';
  const rows = showRealGate ? buildRealRows(language, real) : buildBusinessRows(language, selectedCase, activeCase, runtimeRun, evidence);
  const telemetry = runtimeRun?.telemetry;
  return <Panel title={t.resultTable} icon={<CheckCircle2 className="h-4 w-4"/>}>
    {showRealGate && <div className="mb-4 grid gap-2 md:grid-cols-3">
      <MetricTile label={t.providerName} value={real.provider}/>
      <MetricTile label={t.modelName} value={real.model ?? t.none}/>
      <MetricTile label={t.schemaIssues} value={String(real.schemaErrors.length)}/>
    </div>}
    {!showRealGate && telemetry && <div className="mb-4 grid grid-cols-2 gap-2 md:grid-cols-5">
      <MetricTile label={t.clearTime} value={telemetry.completion_time_seconds == null ? t.none : `${Number(telemetry.completion_time_seconds).toFixed(2)} ${t.seconds}`}/>
      <MetricTile label={t.enemyCount} value={telemetry.enemies_defeated == null ? t.none : `${telemetry.enemies_defeated} ${t.enemies}`}/>
      <MetricTile label={t.skillCount} value={telemetry.skill_uses == null ? t.none : `${telemetry.skill_uses} ${t.times}`}/>
      <MetricTile label={t.goldEarned} value={telemetry.gold_earned == null ? t.none : `${telemetry.gold_earned}`}/>
      <MetricTile label={t.goldSpent} value={telemetry.gold_spent == null ? t.none : `${telemetry.gold_spent}`}/>
    </div>}
    {!rows.length ? <p className="text-sm text-slate-400">{t.noMeasuredResult}</p> : <div className="overflow-x-auto"><table className="w-full min-w-[900px] border-collapse text-left text-sm">
      <thead className="bg-slate-950 text-xs text-slate-400"><tr>{[t.check,t.target,t.actual,t.status,t.impact,t.suggestion].map((label) => <th key={label} className="border-b border-line px-3 py-2 font-medium">{label}</th>)}</tr></thead>
      <tbody>{rows.map((row) => <tr key={row.checkId} className="border-b border-line/70 align-top"><td className="px-3 py-3 font-medium text-slate-100">{row.label}</td><td className="px-3 py-3 text-slate-300">{row.target}</td><td className="px-3 py-3 text-slate-100">{row.actual}</td><td className="px-3 py-3">{row.passed == null ? <span className="text-slate-400">{t.unavailable}</span> : <Status status={row.passed ? 'passed' : 'failed'} language={language}/>}</td><td className="px-3 py-3 leading-5 text-slate-400">{row.impact}</td><td className="px-3 py-3 leading-5 text-slate-300">{row.suggestion}</td></tr>)}</tbody>
    </table></div>}
  </Panel>;
}

type RealRunView = {
  provider: string; model: string | null; jsonParsePassed: boolean; schemaPassed: boolean;
  finalPassed: boolean; schemaErrors: any[]; finalErrors: any[]; badcases: any[]; firstError: string | null;
};

function realRunView(demo: DemoResult | null, language: Language): RealRunView | null {
  if (demo?.workflow_summary?.provider !== 'openai_compatible') return null;
  const sample = demo.real_run?.results?.[0];
  if (!sample) return null;
  const badcases = sample.badcases ?? [];
  const schemaErrors = sample.draft_validation?.schema_errors ?? [];
  const finalErrors = sample.final_validation?.schema_errors ?? [];
  const model = demo.real_run?.model ?? badcases.find((item: any) => item.model)?.model ?? null;
  const first = schemaErrors[0] ?? finalErrors[0];
  return {
    provider: sample.provider ?? 'openai_compatible', model,
    jsonParsePassed: (sample.trace ?? []).length > 0 && (sample.trace ?? []).every((event: any) => event.json_parse_success === true),
    schemaPassed: sample.draft_validation?.schema_passed === true,
    finalPassed: sample.final_validation?.passed === true,
    schemaErrors, finalErrors, badcases,
    firstError: first ? `${first.path}: ${localizeSchemaMessage(first.message, language)}` : null
  };
}

function localizeSchemaMessage(message: string, language: Language): string {
  if (language !== 'zh') return message;
  if (message === 'Required field is missing.') return '缺少必填字段。';
  if (message === 'Config group is missing.') return '缺少配置组。';
  const typeMatch = message.match(/^Expected (\w+), got (\w+)\.$/);
  if (typeMatch) {
    const names: Record<string, string> = { list: '数组', dict: '对象', object: '对象', str: '字符串', int: '整数', bool: '布尔值' };
    return `应为${names[typeMatch[1]] ?? typeMatch[1]}，实际为${names[typeMatch[2]] ?? typeMatch[2]}。`;
  }
  return message;
}

function buildRealRows(language: Language, real: RealRunView): BusinessRow[] {
  const t = copy[language];
  return [
    { checkId: 'real_json_parse', label: t.jsonParseCheck, target: t.parseableJson, actual: real.jsonParsePassed ? t.passed : t.failed, passed: real.jsonParsePassed, impact: real.jsonParsePassed ? '' : t.cannotEnterUnity, suggestion: real.jsonParsePassed ? t.noRisk : t.contractSuggestion },
    { checkId: 'real_schema_contract', label: t.schemaContractCheck, target: t.validProjectSchema, actual: real.schemaPassed ? t.passed : `${real.schemaErrors.length} ${t.schemaIssues}`, passed: real.schemaPassed, impact: real.schemaPassed ? '' : t.cannotEnterUnity, suggestion: real.schemaPassed ? t.noRisk : t.contractSuggestion },
    { checkId: 'real_final_validation', label: t.finalValidationCheck, target: t.finalConfigValid, actual: real.finalPassed ? t.passed : `${real.finalErrors.length} ${t.schemaIssues}`, passed: real.finalPassed, impact: real.finalPassed ? '' : t.cannotEnterUnity, suggestion: real.finalPassed ? t.noRisk : t.contractSuggestion }
  ];
}

function MetricTile({ label, value }: { label: string; value: string }) { return <div className="border-l-2 border-run bg-panel2 px-3 py-2"><div className="text-xs text-slate-400">{label}</div><div className="mt-1 font-mono text-base text-slate-50">{value}</div></div>; }

function buildBusinessRows(language: Language, selectedCase: string, activeCase: ClassicCase | null, runtimeRun: RuntimeRun | null, evidence: Evidence | null): BusinessRow[] {
  const rows: BusinessRow[] = [];
  const messages = businessMessages[language];
  if (runtimeRun?.evaluation) {
    for (const check of runtimeRun.evaluation.checks) {
      const focusedChecks: Record<string, string[]> = {
        case_02_reward_overgrant: ['run_completed'],
        case_03_combat_too_fast: ['run_completed', 'completion_time_in_target'],
        case_05_skill_guidance_balance: ['run_completed', 'completion_time_in_target']
      };
      if (focusedChecks[selectedCase] && !focusedChecks[selectedCase].includes(check.check_id)) continue;
      if (["case_01_baseline_trial", "case_02_reward_overgrant"].includes(selectedCase) && ["first_upgrade_affordable", "second_upgrade_affordable"].includes(check.check_id)) continue;
      const message = messages[check.check_id] ?? { impact: '', suggestion: '' };
      rows.push({ checkId: check.check_id, label: checkLabels[language][check.check_id] ?? check.check_id, target: plannerValue(check.expected, check.check_id, language), actual: plannerValue(check.actual, check.check_id, language), passed: check.passed, ...message });
    }
    const telemetry = runtimeRun.telemetry ?? {};
    const targets = activeCase?.expected_runtime_targets ?? {};
    if (targets.enemies_defeated != null && telemetry.enemies_defeated != null) rows.push(makeTelemetryRow('enemies_defeated', targets.enemies_defeated, telemetry.enemies_defeated, telemetry.enemies_defeated === targets.enemies_defeated, language));
    if (targets.skill_uses_min != null && telemetry.skill_uses != null) rows.push(makeTelemetryRow('skill_usage', `>= ${targets.skill_uses_min}`, telemetry.skill_uses, telemetry.skill_uses >= targets.skill_uses_min, language));
  }
  if (evidence && (selectedCase === 'case_04_missing_reference' || (runtimeRun?.status === 'evaluated' && ["case_01_baseline_trial", "case_02_reward_overgrant"].includes(selectedCase)))) {
    for (const check of evidence.checks) {
      if (rows.some((row) => row.checkId === check.check_id)) continue;
      if (!["first_upgrade", "second_upgrade_after_first", "trial_medal_reference", "trial_medal_repair"].includes(check.check_id)) continue;
      const message = messages[check.check_id] ?? { impact: '', suggestion: '' };
      rows.push({ checkId: check.check_id, label: checkLabels[language][check.check_id] ?? check.check_id, target: plannerValue(check.target, check.check_id, language), actual: plannerValue(check.actual, check.check_id, language), passed: check.status === 'passed' ? true : check.status === 'failed' ? false : null, ...message });
    }
  }
  return rows;
}

function makeTelemetryRow(checkId: string, target: unknown, actual: unknown, passed: boolean, language: Language): BusinessRow { const message = businessMessages[language][checkId]; return { checkId, label: checkLabels[language][checkId] ?? checkId, target: plannerValue(target, checkId, language), actual: plannerValue(actual, checkId, language), passed, ...message }; }

function plannerValue(value: unknown, checkId: string, language: Language): string {
  const zh = language === 'zh';
  if (checkId.includes('completion_time') && Array.isArray(value)) return `${value[0]}–${value[1]} ${zh ? '秒' : 's'}`;
  if (checkId.includes('completion_time') && typeof value === 'number') return `${value.toFixed(2)} ${zh ? '秒' : 's'}`;
  if (checkId === 'run_completed') return value === 'completed' || value === true ? (zh ? '完成' : 'Completed') : String(value);
  if (checkId.includes('upgrade') && typeof value === 'boolean') return value ? (zh ? '可支付' : 'Affordable') : (zh ? '不可支付' : 'Not affordable');
  if (checkId === 'trial_medal_reference' && String(value).includes('missing')) return zh ? '缺少 Trial Medal 配置定义' : 'Trial Medal definition is missing';
  if (checkId === 'trial_medal_repair' && typeof value === 'boolean') return value ? (zh ? '已记录受约束修复' : 'Bounded repair recorded') : (zh ? '未记录修复' : 'Repair not recorded');
  if (typeof value === 'object' && value !== null) return Object.entries(value as Record<string, unknown>).map(([key, item]) => `${key}: ${item}`).join('，');
  const text = String(value);
  if (text === 'affordable') return zh ? '可支付' : 'Affordable';
  if (text === 'not affordable') return zh ? '不可支付' : 'Not affordable';
  if (text === 'reference resolves') return zh ? '引用完整' : 'Reference resolves';
  if (text === 'bounded repair recorded') return zh ? '记录受约束修复' : 'Bounded repair recorded';
  return text;
}

function GuidedRuntimePanel({ language, selectedCase, provider, demo, runtimeRun, loading, onPrepare, onLaunch, onArtifact, businessMode = false }: {
  language: Language; selectedCase: string; provider: Provider; demo: DemoResult | null;
  runtimeRun: RuntimeRun | null; loading: string | null; onPrepare: () => void;
  onLaunch: (mode: 'manual' | 'auto') => void; onArtifact: (name: string) => void; businessMode?: boolean;
}) {
  const t = copy[language];
  const staticOnly = selectedCase === 'case_04_missing_reference';
  const manualInput = selectedCase === 'manual';
  const real = realRunView(demo, language);
  const staticPassed = provider === 'openai_compatible' ? real?.finalPassed === true : demo?.workflow_summary?.final_validation_passed === true;
  const steps = runtimeRun?.steps ?? {
    requirement: manualInput ? 'pending' : 'completed',
    static_validation: staticPassed ? 'completed' : 'pending',
    unity_play: staticPassed && !staticOnly ? 'ready' : 'pending',
    runtime_evaluation: 'pending', improvement_suggestions: 'pending'
  };
  const stepItems = [
    [t.stepRequirement, steps.requirement], [t.stepStatic, steps.static_validation],
    [t.stepUnity, steps.unity_play], [t.stepEvaluation, steps.runtime_evaluation],
    [t.stepSuggestion, steps.improvement_suggestions]
  ];
  const evaluation = runtimeRun?.evaluation;

  return <Panel title={t.guidedRun} icon={<Gamepad2 className="h-4 w-4"/>}>
    <p className="text-sm leading-6 text-slate-300">{businessMode ? t.guidedPlannerSubtitle : t.guidedSubtitle}</p>
    <div className="mt-4 grid gap-2 md:grid-cols-5">
      {stepItems.map(([label, status]) => <RunStep key={label} label={label} status={status} language={language}/>) }
    </div>

    <div className="mt-4 border-l-2 border-run bg-run/5 px-3 py-3 text-sm">
      {staticOnly ? <p className="text-slate-300">{t.staticOnlyRun}</p>
        : manualInput ? <p className="text-amber-100">{t.manualNeedsCase}</p>
        : !staticPassed ? <p className="text-slate-300">{t.validateFirst}</p>
        : !runtimeRun ? <button className="button-primary" disabled={loading !== null} onClick={onPrepare}>
            {loading === 'runtime-prepare' ? <RefreshCw className="h-4 w-4 animate-spin"/> : <Gamepad2 className="h-4 w-4"/>}{t.prepareUnity}
          </button>
        : runtimeRun.status === 'prepared' ? <div className="flex flex-wrap gap-2">
            <button className="button-primary" disabled={loading !== null} onClick={() => onLaunch('manual')}><Play className="h-4 w-4"/>{t.launchManual}</button>
            <button className="button-secondary" disabled={loading !== null} onClick={() => onLaunch('auto')}><RefreshCw className="h-4 w-4"/>{t.launchAuto}</button>
          </div>
        : runtimeRun.status === 'launched' ? <div className="flex items-center gap-2 text-slate-200"><RefreshCw className="h-4 w-4 animate-spin text-run"/>{t.unityRunning}</div>
        : runtimeRun.status === 'failed' ? <p className="text-red-100">{t.runFailed}: {runtimeRun.error?.message}</p>
        : <p className={evaluation?.passed ? 'text-green-100' : 'text-amber-100'}>{evaluation?.passed ? t.runPassed : t.businessFailed}</p>}
    </div>

    {provider === 'openai_compatible' && staticPassed && !runtimeRun && <p className="mt-3 text-xs leading-5 text-slate-400">{t.mockOnlyRun}</p>}

    {runtimeRun && !businessMode && <div className="mt-4 grid gap-2 text-sm md:grid-cols-3">
      <EvidenceMeta label={t.runId} value={runtimeRun.run_id}/>
      <EvidenceMeta label={t.evaluationView} value={caseTitles[language][runtimeRun.case_id] ?? runtimeRun.case_id}/>
      <EvidenceMeta label={t.runMode} value={runtimeRun.mode === 'manual' ? t.manualMode : runtimeRun.mode === 'auto' ? t.autoMode : t.stepReady}/>
    </div>}

    {evaluation && !businessMode && <>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[680px] border-collapse text-left text-sm">
          <thead className="bg-slate-950 text-xs text-slate-400"><tr>{[t.check,t.target,t.actual,t.status].map(label => <th key={label} className="border-b border-line px-3 py-2 font-medium">{label}</th>)}</tr></thead>
          <tbody>{evaluation.checks.map(check => <tr key={check.check_id} className="border-b border-line/70">
            <td className="px-3 py-3 font-medium">{checkLabels[language][check.check_id] ?? check.check_id}</td>
            <td className="px-3 py-3 font-mono text-slate-300">{display(check.expected, language)}</td>
            <td className="px-3 py-3 font-mono text-slate-100">{display(check.actual, language)}</td>
            <td className="px-3 py-3"><Status status={check.passed ? 'passed' : 'failed'} language={language}/></td>
          </tr>)}</tbody>
        </table>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <EvidenceList title={t.risks} items={runtimeRun?.improvement_suggestions.map(item => item.reason) ?? []} tone="risk"/>
        <EvidenceList title={t.recommendations} items={runtimeRun?.improvement_suggestions.map(item => item.suggestion) ?? []} tone="advice"/>
      </div>
    </>}

    {runtimeRun && !businessMode && runtimeRun.available_artifacts.length > 0 && <div className="mt-4 flex flex-wrap items-center gap-2">
      <span className="text-xs text-slate-400">{t.runArtifacts}</span>
      {runtimeRun.available_artifacts.filter(file => ['telemetry.json','runtime_evaluation.json','runtime_evaluation_report.md','improvement_suggestions.json','run_manifest.json'].includes(file.name)).map(file =>
        <button className="chip" key={file.name} onClick={() => onArtifact(file.name)}>{file.name}</button>)}
    </div>}
  </Panel>;
}

function RunStep({ label, status, language }: { label: string; status: string; language: Language }) {
  const t = copy[language];
  const labelByStatus: Record<string, string> = { pending: t.stepPending, ready: t.stepReady, in_progress: t.stepProgress, completed: t.stepComplete };
  const color = status === 'completed' ? 'border-run/60 bg-run/10 text-green-100' : status === 'in_progress' ? 'border-amber-400/60 bg-amber-400/10 text-amber-100' : status === 'ready' ? 'border-sky-400/60 bg-sky-400/10 text-sky-100' : 'border-line bg-panel2 text-slate-400';
  return <div className={`min-h-20 rounded-md border p-3 ${color}`}><div className="text-xs font-medium">{label}</div><div className="mt-2 text-xs">{labelByStatus[status] ?? status}</div></div>;
}

function RuntimeEvidencePanel({ evidence, language, onLoad }: { evidence: Evidence | null; language: Language; onLoad: (path: string) => void }) {
  const t = copy[language];
  return <Panel title={t.runtimeEvaluation} icon={<Database className="h-4 w-4"/>}>
    {!evidence ? <p className="text-sm text-slate-400">{t.noEvidence}</p> : <>
      <div className="grid gap-2 text-sm md:grid-cols-3">
        <EvidenceMeta label={t.telemetrySource} value={evidence.telemetry_source ? t.latestTrainingSword : t.noTelemetry}/>
        <EvidenceMeta label={t.evaluationView} value={caseTitles[language][evidence.case.case_id] ?? evidence.evaluation_view}/>
        <EvidenceMeta label={t.evidenceType} value={evidence.evidence_type === 'static_validation' ? t.staticEvidence : t.runtimeEvidence}/>
      </div>
      <div className="mt-3 border-l-2 border-amber-400 bg-amber-400/5 px-3 py-2 text-xs leading-5 text-amber-100"><strong>{t.mockBoundary}：</strong>{t.mockBoundaryText}</div>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[720px] border-collapse text-left text-sm">
          <thead className="bg-slate-950 text-xs text-slate-400"><tr>{[t.check,t.target,t.actual,t.status,t.evidence].map((label) => <th key={label} className="border-b border-line px-3 py-2 font-medium">{label}</th>)}</tr></thead>
          <tbody>{evidence.checks.map((check) => <tr key={check.check_id} className="border-b border-line/70">
            <td className="px-3 py-3 font-medium">{checkLabels[language][check.check_id] ?? check.check_id}</td>
            <td className="px-3 py-3 font-mono text-slate-300">{display(check.target, language)}</td>
            <td className="px-3 py-3 font-mono text-slate-100">{display(check.actual, language)}</td>
            <td className="px-3 py-3"><Status status={check.status} language={language}/></td>
            <td className="px-3 py-3 text-xs text-slate-400">{check.evidence}</td>
          </tr>)}</tbody>
        </table>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <EvidenceList title={t.risks} items={evidence.risks.map((item) => item.reason)} tone="risk"/>
        <EvidenceList title={t.recommendations} items={evidence.recommendations.map((item) => item.suggestion)} tone="advice"/>
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-2"><span className="text-xs text-slate-400">{t.artifactEntry}</span>
        {evidence.artifacts.length ? evidence.artifacts.map((file) => <button className="chip" key={file.path} onClick={() => onLoad(file.path)}>{file.name}</button>) : <span className="text-xs text-amber-200">{t.generateHint}</span>}
      </div>
    </>}
  </Panel>;
}

function Panel({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return <section className="rounded-md border border-line bg-panel p-4 shadow-xl shadow-black/20"><div className="mb-3 flex items-center gap-2 text-sm font-semibold"><span className="text-run">{icon}</span>{title}</div>{children}</section>;
}
function EvidenceMeta({ label, value }: { label: string; value: string }) { return <div className="border-b border-line/70 pb-2"><div className="text-xs text-slate-500">{label}</div><div className="mt-1 text-slate-200">{value}</div></div>; }
function EvidenceList({ title, items, tone }: { title: string; items: string[]; tone: 'risk' | 'advice' }) { return <div className={`border-l-2 px-3 py-2 ${tone === 'risk' ? 'border-red-400 bg-red-400/5' : 'border-run bg-run/5'}`}><div className="text-xs font-semibold text-slate-300">{title}</div>{items.length ? <ul className="mt-1 space-y-1 text-xs text-slate-400">{items.map((item, i) => <li key={i}>{item}</li>)}</ul> : <div className="mt-1 text-xs text-slate-500">—</div>}</div>; }
function Status({ status, language }: { status: EvidenceCheck['status']; language: Language }) { const t=copy[language]; const ok=status==='passed'; return <span className={`inline-flex items-center gap-1 rounded-sm px-2 py-1 text-xs ${ok ? 'bg-run/15 text-green-100' : status==='failed' ? 'bg-bad/20 text-red-100' : 'bg-slate-700 text-slate-300'}`}>{ok ? <CheckCircle2 className="h-3.5 w-3.5"/> : <XCircle className="h-3.5 w-3.5"/>}{t[status]}</span>; }
function KeyValue({ data, language }: { data: Record<string, unknown>; language: Language }) { return <dl className="space-y-2 text-sm">{Object.entries(data).map(([k,v]) => <div key={k} className="flex justify-between gap-3 border-b border-line/60 pb-2"><dt className="text-slate-400">{k}</dt><dd className="text-right font-mono">{display(v, language)}</dd></div>)}</dl>; }
function MetricGrid({ data, language }: { data: Record<string, any>; language: Language }) { const entries=Object.entries(data??{}).filter(([,v])=>typeof v!=='object'); if(!entries.length)return <p className="text-sm text-slate-400">{copy[language].emptyMetrics}</p>; return <div className="grid grid-cols-2 gap-2">{entries.map(([k,v])=><div key={k} className="rounded-md border border-line bg-panel2 p-3"><div className="text-xs text-slate-400">{k}</div><div className="mt-1 font-mono text-lg">{formatMetric(v)}</div></div>)}</div>; }
function Timeline({ events, language }: { events: any[]; language: Language }) { const t=copy[language]; if(!events.length)return <p className="text-sm text-slate-400">{t.emptyTimeline}</p>; return <ol className="space-y-3">{events.map((event,i)=><li key={i} className="grid grid-cols-[40px_minmax(0,1fr)] gap-3"><span className="flex h-8 w-8 items-center justify-center rounded-md bg-run/15 font-mono text-run">{event.step??i+1}</span><div className="rounded-md border border-line bg-panel2 p-3"><div className="flex flex-wrap items-center gap-2"><strong>{event.actor??event.action}</strong><span className={`rounded-sm px-2 py-0.5 text-xs ${event.status==='failed'?'bg-amber-400/15 text-amber-100':'bg-run/15 text-green-100'}`}>{event.status==='failed'?t.statusIssues:t.statusSucceeded}</span></div><div className="mt-2 text-xs text-slate-400">{event.action}</div></div></li>)}</ol>; }
function Tabs({ tabs }: { tabs: Array<{label:string;content:React.ReactNode}> }) { const[active,setActive]=useState(0); return <section className="rounded-md border border-line bg-panel"><div className="flex flex-wrap gap-1 border-b border-line p-2">{tabs.map((tab,i)=><button key={tab.label} className={i===active?'tab-active':'tab'} onClick={()=>setActive(i)}>{tab.label}</button>)}</div><div className="p-4">{tabs[active].content}</div></section>; }
function JsonBlock({ value }: { value: unknown }) { const text=useMemo(()=>JSON.stringify(value,null,2),[value]); return <pre className="max-h-[460px] overflow-auto rounded-md bg-slate-950 p-4 font-mono text-sm leading-6 text-slate-200">{text}</pre>; }
function BadcaseList({ badcases, language }: { badcases:any[];language:Language }) {
  const t=copy[language];
  if(!badcases.length)return <p className="text-sm text-slate-400">{t.emptyBadcases}</p>;
  return <div className="space-y-2">{badcases.map((b,i)=><div key={`${b.sample_id ?? 'sample'}-${b.stage ?? i}`} className="rounded-md border border-bad/40 bg-bad/10 p-3 text-sm">
    <div className="flex flex-wrap gap-x-4 gap-y-1"><strong>{t.badcaseStage}: {b.stage??'badcase'}</strong><span className="text-slate-400">sample_id: {b.sample_id ?? t.none}</span><span className="text-slate-400">provider: {b.provider ?? t.none}</span><span className="text-slate-400">model: {b.model ?? t.none}</span></div>
    <div className="mt-2 text-slate-200">{b.error_message ?? b.reason}</div>
    {Array.isArray(b.errors) && b.errors.length > 0 && <div className="mt-2 space-y-1 border-l border-bad/40 pl-3 text-xs text-slate-400">{b.errors.slice(0, 5).map((error:any,index:number)=><div key={`${error.path}-${index}`}><span className="font-mono text-slate-300">{error.path}</span>: {localizeSchemaMessage(error.message, language)}</div>)}{b.errors.length > 5 && <div>+ {b.errors.length - 5} {language === 'zh' ? '项更多问题' : 'more'}</div>}</div>}
  </div>)}</div>;
}
function ArtifactList({ artifacts, language }: { artifacts?:Record<string,Artifact[]>;language:Language }) { const entries=Object.entries(artifacts??{}).flatMap(([phase,files])=>files.map(file=>({phase,...file}))); if(!entries.length)return <p className="text-sm text-slate-400">{copy[language].emptyArtifacts}</p>; return <div className="space-y-2 text-sm">{entries.map(file=><div key={`${file.phase}-${file.name}`} className="flex justify-between gap-3 rounded-md border border-line bg-panel2 p-2"><span className="truncate">{file.phase}/{file.name}</span><span className="font-mono text-slate-400">{file.size}b</span></div>)}</div>; }
function ReportPicker({ artifacts,onLoad,selected,language }: { artifacts?:Record<string,Artifact[]>;onLoad:(path:string)=>void;selected:string;language:Language }) { const reports=Object.entries(artifacts??{}).flatMap(([phase,files])=>files.filter(f=>f.name.endsWith('.md')).map(f=>`${phase}/${f.name}`)); if(!reports.length)return <p className="text-sm text-slate-400">{copy[language].noReports}</p>; return <div className="flex flex-wrap gap-2">{reports.map(path=><button key={path} className={selected===path?'chip-active':'chip'} onClick={()=>onLoad(path)}>{path}</button>)}</div>; }

async function getJson<T>(url:string):Promise<T>{const response=await fetch(`${API_BASE}${url}`);if(!response.ok)throw new Error(await response.text());return response.json();}
async function postJson<T>(url:string,body:unknown):Promise<T>{const response=await fetch(`${API_BASE}${url}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});if(!response.ok)throw new Error(await response.text());return response.json();}
function messageFromError(err:unknown,language:Language){
  if (err instanceof Error && /Failed to fetch|NetworkError|Load failed|fetch failed/i.test(err.message)) {
    return copy[language].backendUnavailable;
  }
  return err instanceof Error ? err.message : copy[language].unexpectedError;
}
function formatMetric(value:unknown){if(typeof value==='number'&&value>0&&value<1)return `${(value*100).toFixed(1)}%`;return String(value);}
function display(value:unknown,language:Language){const t=copy[language];if(value===true)return t.yes;if(value===false)return t.no;if(value===null||value===undefined)return t.none;if(typeof value==='object')return JSON.stringify(value);return String(value);}

createRoot(document.getElementById('root')!).render(<App/>);
