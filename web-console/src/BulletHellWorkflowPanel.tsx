import React, { useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle, CheckCircle2, CircleDot, FileJson, Gauge, Gamepad2, Orbit,
  Play, RefreshCw, RotateCcw, ShieldCheck, SlidersHorizontal, Sparkles, ThumbsUp, Wrench
} from 'lucide-react';

type Language = 'zh' | 'en';
type Provider = 'mock' | 'openai_compatible';
type DiffRow = { change_type: string; path: string; before: unknown; after: unknown };
type MetricRow = { metric: string; baseline: unknown; candidate: unknown; target: string; passed: boolean; evidence: string };
type TimelineRow = { step: string; status: string; timestamp: string; detail: Record<string, unknown> };
type RepairRow = { iteration: number; action: string; applied: boolean; phase_id?: string; reason: string };
type Workflow = {
  workflow_id: string;
  provider: Provider;
  model?: string | null;
  status: string;
  current_iteration: number;
  budget: { max_unity_runs: number; max_model_calls: number; unity_runs_used: number; model_calls_used: number };
  authorization?: { actor: string; note: string; scope: string } | null;
  feasibility_gate?: { decision: string; reason: string; issues: Array<Record<string, unknown>> };
  structured_goal?: Record<string, unknown>;
  static_validation?: { passed: boolean; schema_errors: unknown[]; rule_errors: unknown[] };
  config_diff?: DiffRow[];
  repair_history?: RepairRow[];
  comparison_report?: { passed: boolean; metrics: MetricRow[]; evidence_scope: string };
  baseline_telemetry?: Record<string, unknown> | null;
  candidate_telemetry?: Record<string, unknown> | null;
  timeline: TimelineRow[];
  error?: { stage: string; type: string; message: string } | null;
  available_artifacts: Array<{ name: string; size: number }>;
};

const text = {
  zh: {
    eyebrow: 'GAME CHANGE VERIFICATION',
    title: '弹幕变更验证',
    subtitle: '用自然语言提出玩法调整。Agent 生成候选，确定性工具校验，Unity 在隔离环境自动对比修改前后结果。',
    boundary: '自动化边界',
    boundaryText: '一次授权后最多运行 3 个候选；只修改候选 JSON。正式基线必须由你最终接受。',
    requirement: '玩法变更需求',
    provider: '候选生成方式',
    mock: '确定性 Mock',
    real: '真实模型',
    timeout: '模型超时（秒）',
    create: '生成候选并静态校验',
    creating: '正在生成候选',
    loadLatest: '加载最近验证',
    authorize: '授权隔离自动验证',
    authorizedBy: '授权人',
    note: '授权说明',
    run: '开始自动对比与修复',
    running: 'Unity 正在运行，请保持后端窗口开启',
    manual: '打开 Unity 手动试玩',
    reset: '新建验证',
    accept: '接受候选',
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
    noEvidence: '完成自动验证后显示 baseline 与 candidate 的同条件对比。',
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
    presetRequirements: [
      '第二阶段改为双向螺旋弹，提高密度，但同时存在的子弹不能超过350发，最低帧率不能低于55 FPS。',
      '第三阶段使用花瓣弹提高压迫感，但玩家最多受击3次，最低帧率不能低于55 FPS。',
      '每0.02秒发射200颗高速弹，越密越好。'
    ],
    steps: ['需求与候选', '静态安全校验', '隔离测试授权', 'Baseline / Candidate', '自动修复', '人工结论'],
    planner: '策划控制台',
    debug: '展开原始 JSON'
  },
  en: {
    eyebrow: 'GAME CHANGE VERIFICATION',
    title: 'Bullet Hell Change Verification',
    subtitle: 'Describe a gameplay change. The Agent proposes a candidate, deterministic tools verify it, and Unity compares before and after in isolation.',
    boundary: 'Automation boundary',
    boundaryText: 'One authorization permits up to 3 candidate runs and candidate JSON changes only. You make the final baseline decision.',
    requirement: 'Gameplay change requirement',
    provider: 'Candidate provider',
    mock: 'Deterministic Mock',
    real: 'Real provider',
    timeout: 'Model timeout (seconds)',
    create: 'Create candidate and validate',
    creating: 'Creating candidate',
    loadLatest: 'Load latest verification',
    authorize: 'Authorize isolated auto validation',
    authorizedBy: 'Authorized by',
    note: 'Authorization note',
    run: 'Start comparison and repair',
    running: 'Unity is running. Keep the backend window open.',
    manual: 'Open Unity manual playtest',
    reset: 'New verification',
    accept: 'Accept candidate',
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
    presetRequirements: [
      'Change phase 2 to a denser bidirectional spiral while keeping at most 350 alive bullets and at least 55 FPS.',
      'Use a denser petal pattern in phase 3, with at most 3 player hits and at least 55 FPS.',
      'Fire 200 high-speed bullets every 0.02 seconds. Denser is always better.'
    ],
    steps: ['Requirement', 'Static safety', 'Authorization', 'Baseline / Candidate', 'Auto repair', 'Human decision'],
    planner: 'Designer console',
    debug: 'Show raw JSON'
  }
} as const;

const runningStatuses = new Set(['running_baseline', 'running_candidate', 'analyzing', 'repairing']);

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

  useEffect(() => {
    if (!workflow || !runningStatuses.has(workflow.status)) return;
    const timer = window.setInterval(() => {
      request<Workflow>(`/api/bullet-hell/workflows/${workflow.workflow_id}`).then(setWorkflow).catch((reason) => setError(String(reason)));
    }, 1200);
    return () => window.clearInterval(timer);
  }, [workflow?.workflow_id, workflow?.status]);

  const currentStep = useMemo(() => stepForStatus(workflow?.status), [workflow?.status]);

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
  }

  return <section className="bullet-workbench">
    <div className="bullet-command">
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
        <label className="label mt-4" htmlFor="bullet-requirement">{t.requirement}</label>
        <textarea
          id="bullet-requirement"
          className="input min-h-32 resize-y leading-6"
          value={requirement}
          onChange={(event) => { setRequirement(event.target.value); setSelectedPreset(-1); setWorkflow(null); }}
        />
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <label className="label" htmlFor="bullet-provider">
          {t.provider}
          <select
            id="bullet-provider"
            className="input mt-1"
            value={provider}
            disabled={!!workflow}
            onChange={(event) => onProvider(event.target.value as Provider)}
          >
            <option value="mock">{t.mock}</option>
            <option value="openai_compatible">{t.real}</option>
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

      <div className="mt-5 flex flex-wrap gap-2">
        {!workflow && <button className="button-primary" disabled={!!busy || !requirement.trim()} onClick={() => act('create', () => request('/api/bullet-hell/workflows', {
          method: 'POST',
          body: JSON.stringify({ requirement_text: requirement, provider, timeout_seconds: timeoutSeconds })
        }))}>
          {busy === 'create' ? <RefreshCw className="h-4 w-4 animate-spin"/> : <Sparkles className="h-4 w-4"/>}
          {busy === 'create' ? t.creating : t.create}
        </button>}
        {!workflow && <button className="button-secondary" disabled={!!busy} onClick={() => act('latest', () => request('/api/bullet-hell/workflows/latest'))}>
          {busy === 'latest' ? <RefreshCw className="h-4 w-4 animate-spin"/> : <FileJson className="h-4 w-4"/>}
          {t.loadLatest}
        </button>}
        {workflow && <button className="button-secondary" onClick={() => { setWorkflow(null); setError(''); setDecisionNote(''); }}>
          <RotateCcw className="h-4 w-4"/>{t.reset}
        </button>}
      </div>

      {workflow?.status === 'awaiting_authorization' && <div className="mt-5 border-t border-line pt-5">
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="label">{t.authorizedBy}<input className="input mt-1" value={actor} onChange={(event) => setActor(event.target.value)}/></label>
          <label className="label">{t.note}<input className="input mt-1" value={authorizationNote} onChange={(event) => setAuthorizationNote(event.target.value)}/></label>
        </div>
        <button className="button-primary mt-3" disabled={!!busy || !actor.trim()} onClick={() => act('authorize', () => request(`/api/bullet-hell/workflows/${workflow.workflow_id}/authorize`, {
          method: 'POST', body: JSON.stringify({ actor, note: authorizationNote })
        }))}><ShieldCheck className="h-4 w-4"/>{t.authorize}</button>
      </div>}

      {workflow?.status === 'authorized' && <div className="mt-5 flex flex-wrap gap-2 border-t border-line pt-5">
        <button className="button-primary" disabled={!!busy} onClick={() => act('run', () => request(`/api/bullet-hell/workflows/${workflow.workflow_id}/run`, { method: 'POST' }))}>
          <Play className="h-4 w-4"/>{t.run}
        </button>
        <button className="button-secondary" disabled={!!busy} onClick={() => request(`/api/bullet-hell/workflows/${workflow.workflow_id}/play`, { method: 'POST' }).catch((reason) => setError(String(reason)))}>
          <Gamepad2 className="h-4 w-4"/>{t.manual}
        </button>
      </div>}

      {workflow && ['evidence_ready', 'budget_exhausted'].includes(workflow.status) && <div className="mt-5 border-t border-line pt-5">
        <label className="label">{t.decisionNote}<input className="input mt-1" value={decisionNote} onChange={(event) => setDecisionNote(event.target.value)}/></label>
        <div className="mt-3 flex flex-wrap gap-2">
          {workflow.status === 'evidence_ready' && <DecisionButton label={t.accept} icon={<ThumbsUp className="h-4 w-4"/>} disabled={!!busy || !decisionNote.trim()} onClick={() => decide('accept')}/>}
          <DecisionButton label={t.revise} icon={<Wrench className="h-4 w-4"/>} secondary disabled={!!busy || !decisionNote.trim()} onClick={() => decide('revise')}/>
          <DecisionButton label={t.rollback} icon={<RotateCcw className="h-4 w-4"/>} secondary disabled={!!busy || !decisionNote.trim()} onClick={() => decide('rollback')}/>
        </div>
      </div>}

      {error && <p role="alert" className="mt-4 rounded-md border border-red-500/40 bg-red-950/40 p-3 text-sm text-red-100">{error}</p>}
    </div>

    <div className="bullet-evidence">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold text-slate-500">{t.planner}</p>
          <h3 className="mt-1 text-lg font-semibold text-white">{t.status}</h3>
        </div>
        <StatusBadge status={workflow?.status ?? 'drafted'} language={language}/>
      </div>

      <div className="evidence-rail mt-5" aria-label={t.status}>
        {t.steps.map((label, index) => <div key={label} className={`evidence-stop ${index <= currentStep ? 'evidence-stop-active' : ''}`}>
          <span>{index + 1}</span><p>{label}</p>
        </div>)}
      </div>

      {workflow && <p className="mt-4 text-sm leading-6 text-slate-300">{statusMessage(workflow.status, t)}</p>}
      {workflow?.error && <p className="mt-3 border-l-2 border-red-400 pl-3 text-sm text-red-200">{workflow.error.type}: {workflow.error.message}</p>}

      {workflow?.structured_goal && <EvidenceBand title={t.goal} icon={<SlidersHorizontal className="h-4 w-4"/>}>
        <GoalSummary value={workflow.structured_goal} language={language}/>
      </EvidenceBand>}

      {workflow?.config_diff && workflow.config_diff.length > 0 && <EvidenceBand title={t.changes} icon={<Orbit className="h-4 w-4"/>}>
        <div className="overflow-x-auto"><table className="w-full min-w-[620px] text-left text-sm">
          <thead className="text-xs text-slate-500"><tr><th className="px-2 py-2">Path</th><th className="px-2 py-2">{t.before}</th><th className="px-2 py-2">{t.after}</th></tr></thead>
          <tbody>{workflow.config_diff.slice(0, 16).map((row) => <tr key={row.path} className="border-t border-line">
            <td className="px-2 py-2 font-mono text-xs text-cyan-200">{row.path}</td>
            <td className="px-2 py-2 text-slate-400">{display(row.before)}</td>
            <td className="px-2 py-2 text-slate-100">{display(row.after)}</td>
          </tr>)}</tbody>
        </table></div>
      </EvidenceBand>}

      <EvidenceBand title={t.evidence} icon={<Gauge className="h-4 w-4"/>}>
        {!workflow?.comparison_report ? <p className="text-sm text-slate-400">{t.noEvidence}</p> :
          <>
            <div className="overflow-x-auto"><table className="w-full min-w-[620px] text-left text-sm">
              <thead className="text-xs text-slate-500"><tr><th className="px-2 py-2">{t.check}</th><th className="px-2 py-2">{t.before}</th><th className="px-2 py-2">{t.after}</th><th className="px-2 py-2">{t.target}</th><th className="px-2 py-2">{t.status}</th></tr></thead>
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

      {!!workflow?.available_artifacts?.length && <EvidenceBand title={t.artifacts} icon={<FileJson className="h-4 w-4"/>}>
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

function EvidenceBand({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return <section className="mt-5 border-t border-line pt-5">
    <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-200">{icon}{title}</h4>
    {children}
  </section>;
}

function DecisionButton({ label, icon, disabled, secondary, onClick }: { label: string; icon: React.ReactNode; disabled: boolean; secondary?: boolean; onClick: () => void }) {
  return <button className={secondary ? 'button-secondary' : 'button-primary'} disabled={disabled} onClick={onClick}>{icon}{label}</button>;
}

function StatusBadge({ status, language }: { status: string; language: Language }) {
  const passed = ['evidence_ready', 'accepted'].includes(status);
  const failed = ['blocked', 'failed', 'budget_exhausted'].includes(status);
  const label = statusLabel(status, language);
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

function statusLabel(status: string, language: Language) {
  const labels: Record<Language, Record<string, string>> = {
    zh: { drafted: '等待输入', awaiting_authorization: '等待授权', authorized: '已授权', running_baseline: '运行基线', running_candidate: '运行候选', analyzing: '分析证据', repairing: '自动修复', evidence_ready: '证据就绪', budget_exhausted: '预算耗尽', blocked: '已拦截', needs_clarification: '需要补充', failed: '执行失败', accepted: '已接受', revision_requested: '要求修订', rolled_back: '已回滚' },
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
    'Bounded repair policy': '受约束自动修复',
    'Evidence review': '运行证据审查',
    'Final human decision': '人工最终决策',
    'Manual Unity playtest': 'Unity 手动试玩',
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
