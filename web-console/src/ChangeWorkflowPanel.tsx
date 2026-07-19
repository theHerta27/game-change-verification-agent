import { useEffect, useState } from 'react';
import {
  CheckCircle2, ClipboardCheck, Gamepad2, GitCompareArrows, Play,
  RefreshCw, RotateCcw, ShieldCheck, ThumbsUp, Wrench
} from 'lucide-react';

type Language = 'zh' | 'en';
type Provider = 'mock' | 'openai_compatible';
type Workflow = {
  workflow_id: string;
  status: string;
  change_count?: number;
  feasibility_gate?: { decision: string; reason: string; missing_information?: string[] } | null;
  config_diff: Array<{ change_type: string; path: string; before: unknown; after: unknown }>;
  static_validation?: { passed: boolean } | null;
  quality_review?: {
    approval_recommended: boolean;
    summary: string;
    findings: Array<{ severity: string; title: string; suggestion: string }>;
    test_suggestions: Array<{ test_id: string; reason: string }>;
  } | null;
  runtime_evidence_review?: {
    runtime_passed: boolean;
    failed_check_count: number;
    summary: string;
    recommendation: string;
  } | null;
  runtime_run?: {
    status: string;
    mode: string | null;
    evaluation?: {
      passed: boolean;
      checks: Array<{ check_id: string; passed: boolean; expected: unknown; actual: unknown }>;
    } | null;
  } | null;
  approval?: { approver: string; note: string } | null;
  final_decision?: { decision: string; actor: string; note: string } | null;
  timeline: Array<{ step: string; status: string }>;
  error?: { type: string; message: string } | null;
};

const text = {
  zh: {
    title: '配置变更闭环', subtitle: '先查看候选变化并人工批准，再让 Unity 验证；系统不会直接覆盖基线配置。',
    create: '创建变更提案', creating: '正在生成提案', status: '当前状态', noProposal: '尚未创建提案',
    gate: '需求可行性', diff: '配置变化', review: '质量审查', tests: '建议验证', approval: '人工审批',
    path: '配置项', before: '修改前', after: '修改后', noChange: '需求没有改变当前基线字段。',
    approver: '审批人', approvalNote: '审批说明（可选）', approve: '批准进入 Unity 验证',
    prepare: '准备隔离 Unity 测试', manual: '打开 Unity 手动试玩', auto: '运行固定种子自动试玩',
    running: 'Unity 正在运行。试玩结束后会自动读取 telemetry。', evidence: 'Unity 运行证据',
    check: '检查项', target: '目标', actual: '实测', result: '结果', passed: '通过', failed: '未通过',
    decision: '最终人工决策', decisionNote: '说明本次为什么接受、要求修订或回滚',
    accept: '接受候选配置', revise: '要求修订', rollback: '回滚到基线',
    actor: '决策人', refresh: '刷新状态', complete: '本次变更已完成决策。',
    mock: 'Mock 会从固定 Training Sword 基线应用明确约束；它不是自由生成模型。',
    real: '真实模型先生成候选，但仍必须经过同一套静态校验、人工审批和 Unity 证据验证。',
  },
  en: {
    title: 'Config Change Loop', subtitle: 'Review and approve the candidate before Unity validation. The committed baseline is never overwritten.',
    create: 'Create change proposal', creating: 'Creating proposal', status: 'Status', noProposal: 'No proposal yet',
    gate: 'Feasibility gate', diff: 'Config changes', review: 'Quality review', tests: 'Suggested validation', approval: 'Human approval',
    path: 'Config field', before: 'Before', after: 'After', noChange: 'The requirement does not change a baseline field.',
    approver: 'Approver', approvalNote: 'Approval note (optional)', approve: 'Approve for Unity validation',
    prepare: 'Prepare isolated Unity run', manual: 'Open manual Unity playtest', auto: 'Run fixed-seed auto playtest',
    running: 'Unity is running. Telemetry is collected after the playtest.', evidence: 'Unity evidence',
    check: 'Check', target: 'Target', actual: 'Measured', result: 'Result', passed: 'Passed', failed: 'Failed',
    decision: 'Final human decision', decisionNote: 'Explain why this candidate is accepted, revised, or rolled back',
    accept: 'Accept candidate', revise: 'Request revision', rollback: 'Roll back to baseline',
    actor: 'Decision maker', refresh: 'Refresh', complete: 'This change has a final decision.',
    mock: 'Mock applies explicit constraints to the fixed Training Sword baseline; it is not a free-form model.',
    real: 'The real model proposes a candidate, but the same validation, approval, and Unity evidence gates still apply.',
  },
} as const;

const statusLabels: Record<Language, Record<string, string>> = {
  zh: {
    proposing: '生成中', proposed: '等待审批', approved: '已批准', runtime_prepared: 'Unity 已准备',
    runtime_launched: 'Unity 运行中', evidence_ready: '证据已完成', accepted: '已接受',
    revision_requested: '需要修订', rolled_back: '已回滚', rejected: '需求不支持',
    needs_clarification: '需要补充需求', failed: '流程失败',
  },
  en: {
    proposing: 'Proposing', proposed: 'Awaiting approval', approved: 'Approved', runtime_prepared: 'Unity ready',
    runtime_launched: 'Unity running', evidence_ready: 'Evidence ready', accepted: 'Accepted',
    revision_requested: 'Revision requested', rolled_back: 'Rolled back', rejected: 'Unsupported',
    needs_clarification: 'Needs clarification', failed: 'Failed',
  },
};

export function ChangeWorkflowPanel({
  language, requirement, caseId, provider, timeoutSeconds,
}: {
  language: Language;
  requirement: string;
  caseId: string;
  provider: Provider;
  timeoutSeconds: number;
}) {
  const t = text[language];
  const [workflow, setWorkflow] = useState<Workflow | null>(null);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [approver, setApprover] = useState(language === 'zh' ? '策划演示者' : 'Demo designer');
  const [approvalNote, setApprovalNote] = useState('');
  const [decisionNote, setDecisionNote] = useState('');

  useEffect(() => {
    setWorkflow(null);
    setError('');
  }, [requirement, caseId, provider]);

  useEffect(() => {
    if (workflow?.status !== 'runtime_launched') return;
    const timer = window.setInterval(() => refresh(workflow.workflow_id), 1500);
    return () => window.clearInterval(timer);
  }, [workflow?.workflow_id, workflow?.status]);

  async function request(path: string, body?: unknown) {
    const response = await fetch(path, {
      method: body === undefined ? 'GET' : 'POST',
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(payload.detail ?? response.statusText);
    }
    return response.json() as Promise<Workflow>;
  }

  async function act(key: string, operation: () => Promise<Workflow>) {
    setBusy(key);
    setError('');
    try { setWorkflow(await operation()); }
    catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); }
    finally { setBusy(''); }
  }

  function refresh(id: string) {
    return request(`/api/change-workflows/${id}`).then(setWorkflow).catch((reason) => setError(String(reason)));
  }

  const terminal = workflow && ['accepted', 'revision_requested', 'rolled_back'].includes(workflow.status);
  return <section className="rounded-md border border-line bg-panel p-5 shadow-sm">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <div className="flex items-center gap-2"><GitCompareArrows className="h-5 w-5 text-run"/><h2 className="text-lg font-semibold">{t.title}</h2></div>
        <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-400">{t.subtitle}</p>
        <p className="mt-1 text-xs leading-5 text-slate-500">{provider === 'mock' ? t.mock : t.real}</p>
      </div>
      {workflow && <div className="rounded-md border border-line bg-slate-950 px-3 py-2 text-sm">
        <span className="text-slate-400">{t.status}: </span><strong className="text-run">{statusLabels[language][workflow.status] ?? workflow.status}</strong>
      </div>}
    </div>

    {!workflow && <button className="button-primary mt-4" disabled={!!busy || !requirement.trim()} onClick={() => act('create', () => request('/api/change-workflows', {
      requirement_text: requirement,
      case_id: caseId === 'manual' ? 'case_01_baseline_trial' : caseId,
      provider,
      timeout_seconds: timeoutSeconds,
    }))}>{busy === 'create' ? <RefreshCw className="h-4 w-4 animate-spin"/> : <GitCompareArrows className="h-4 w-4"/>}{busy === 'create' ? t.creating : t.create}</button>}

    {error && <p className="mt-4 rounded-md border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-100">{error}</p>}

    {workflow && <div className="mt-5 space-y-5">
      <WorkflowSteps language={language} workflow={workflow}/>
      {workflow.feasibility_gate && <InfoBlock icon={<ShieldCheck className="h-4 w-4"/>} title={t.gate}>
        <p className="text-sm text-slate-300">{workflow.feasibility_gate.reason}</p>
      </InfoBlock>}

      {workflow.quality_review && <>
        <InfoBlock icon={<GitCompareArrows className="h-4 w-4"/>} title={`${t.diff} (${workflow.change_count ?? 0})`}>
          {workflow.config_diff.length ? <div className="overflow-x-auto"><table className="w-full table-fixed text-left text-sm">
            <thead className="text-xs text-slate-400"><tr><th className="w-2/5 px-2 py-2">{t.path}</th><th className="px-2 py-2">{t.before}</th><th className="px-2 py-2">{t.after}</th></tr></thead>
            <tbody>{workflow.config_diff.map((change, index) => <tr key={`${change.path}-${index}`} className="border-t border-line">
              <td className="break-words px-2 py-2 font-mono text-xs text-slate-300">{fieldLabel(language, change.path)}</td>
              <td className="break-words px-2 py-2 text-slate-400">{display(change.before)}</td>
              <td className="break-words px-2 py-2 font-medium text-run">{display(change.after)}</td>
            </tr>)}</tbody>
          </table></div> : <p className="text-sm text-slate-400">{t.noChange}</p>}
        </InfoBlock>

        <div className="grid gap-4 lg:grid-cols-2">
          <InfoBlock icon={<ClipboardCheck className="h-4 w-4"/>} title={t.review}>
            <p className="text-sm text-slate-300">{workflow.quality_review.summary}</p>
            {workflow.quality_review.findings.map((item, index) => <div key={index} className="mt-3 border-l-2 border-amber-400 pl-3 text-sm">
              <strong>{item.title}</strong><p className="mt-1 text-slate-400">{item.suggestion}</p>
            </div>)}
          </InfoBlock>
          <InfoBlock icon={<Wrench className="h-4 w-4"/>} title={t.tests}>
            {workflow.quality_review.test_suggestions.map((item) => <div key={item.test_id} className="mb-3 text-sm"><strong>{testLabel(language, item.test_id)}</strong><p className="mt-1 text-slate-400">{item.reason}</p></div>)}
          </InfoBlock>
        </div>
      </>}

      {workflow.status === 'proposed' && <InfoBlock icon={<CheckCircle2 className="h-4 w-4"/>} title={t.approval}>
        <div className="grid gap-3 md:grid-cols-2">
          <label className="label">{t.approver}<input className="input mt-1" value={approver} onChange={(event) => setApprover(event.target.value)}/></label>
          <label className="label">{t.approvalNote}<input className="input mt-1" value={approvalNote} onChange={(event) => setApprovalNote(event.target.value)}/></label>
        </div>
        <button className="button-primary mt-3" disabled={!approver.trim() || !!busy} onClick={() => act('approve', () => request(`/api/change-workflows/${workflow.workflow_id}/approve`, { approver, note: approvalNote }))}><ThumbsUp className="h-4 w-4"/>{t.approve}</button>
      </InfoBlock>}

      {workflow.status === 'approved' && <button className="button-primary" disabled={!!busy} onClick={() => act('prepare', () => request(`/api/change-workflows/${workflow.workflow_id}/runtime`, {}))}><Gamepad2 className="h-4 w-4"/>{t.prepare}</button>}
      {workflow.status === 'runtime_prepared' && <div className="flex flex-wrap gap-2">
        <button className="button-primary" disabled={!!busy} onClick={() => act('manual', () => request(`/api/change-workflows/${workflow.workflow_id}/launch`, { mode: 'manual' }))}><Gamepad2 className="h-4 w-4"/>{t.manual}</button>
        <button className="button-secondary" disabled={!!busy} onClick={() => act('auto', () => request(`/api/change-workflows/${workflow.workflow_id}/launch`, { mode: 'auto' }))}><Play className="h-4 w-4"/>{t.auto}</button>
      </div>}
      {workflow.status === 'runtime_launched' && <p className="flex items-center gap-2 text-sm text-slate-300"><RefreshCw className="h-4 w-4 animate-spin text-run"/>{t.running}</p>}

      {workflow.runtime_run?.evaluation && <InfoBlock icon={<Gamepad2 className="h-4 w-4"/>} title={t.evidence}>
        <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead className="text-xs text-slate-400"><tr><th className="px-2 py-2">{t.check}</th><th className="px-2 py-2">{t.target}</th><th className="px-2 py-2">{t.actual}</th><th className="px-2 py-2">{t.result}</th></tr></thead>
          <tbody>{workflow.runtime_run.evaluation.checks.map((check) => <tr key={check.check_id} className="border-t border-line"><td className="px-2 py-2">{checkLabel(language, check.check_id)}</td><td className="break-all px-2 py-2 text-slate-400">{display(check.expected)}</td><td className="break-all px-2 py-2">{display(check.actual)}</td><td className={`px-2 py-2 font-medium ${check.passed ? 'text-run' : 'text-red-300'}`}>{check.passed ? t.passed : t.failed}</td></tr>)}</tbody>
        </table></div>
        {workflow.runtime_evidence_review && <p className="mt-3 text-sm text-slate-300">{workflow.runtime_evidence_review.summary}</p>}
      </InfoBlock>}

      {workflow.status === 'evidence_ready' && <InfoBlock icon={<ClipboardCheck className="h-4 w-4"/>} title={t.decision}>
        <div className="grid gap-3 md:grid-cols-2">
          <label className="label">{t.actor}<input className="input mt-1" value={approver} onChange={(event) => setApprover(event.target.value)}/></label>
          <label className="label">{t.decisionNote}<input className="input mt-1" value={decisionNote} onChange={(event) => setDecisionNote(event.target.value)}/></label>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          <DecisionButton label={t.accept} disabled={!decisionNote.trim() || !!busy} icon={<ThumbsUp className="h-4 w-4"/>} onClick={() => act('accept', () => request(`/api/change-workflows/${workflow.workflow_id}/decision`, { decision: 'accept', actor: approver, note: decisionNote }))}/>
          <DecisionButton label={t.revise} disabled={!decisionNote.trim() || !!busy} icon={<Wrench className="h-4 w-4"/>} secondary onClick={() => act('revise', () => request(`/api/change-workflows/${workflow.workflow_id}/decision`, { decision: 'revise', actor: approver, note: decisionNote }))}/>
          <DecisionButton label={t.rollback} disabled={!decisionNote.trim() || !!busy} icon={<RotateCcw className="h-4 w-4"/>} secondary onClick={() => act('rollback', () => request(`/api/change-workflows/${workflow.workflow_id}/decision`, { decision: 'rollback', actor: approver, note: decisionNote }))}/>
        </div>
      </InfoBlock>}

      {terminal && <p className="rounded-md border border-run/30 bg-run/10 p-3 text-sm text-run">{t.complete} {workflow.final_decision?.note}</p>}
      <button className="button-secondary" disabled={!!busy} onClick={() => refresh(workflow.workflow_id)}><RefreshCw className="h-4 w-4"/>{t.refresh}</button>
    </div>}
  </section>;
}

function WorkflowSteps({ language, workflow }: { language: Language; workflow: Workflow }) {
  const labels = language === 'zh'
    ? ['需求与提案', '人工审批', 'Unity 试玩', '证据审查', '最终决策']
    : ['Proposal', 'Approval', 'Unity playtest', 'Evidence review', 'Final decision'];
  const order = ['proposed', 'approved', 'runtime_prepared', 'runtime_launched', 'evidence_ready', 'accepted'];
  const current = Math.max(0, order.indexOf(workflow.status));
  const done = workflow.status === 'accepted' || workflow.status === 'revision_requested' || workflow.status === 'rolled_back';
  return <div className="grid grid-cols-2 gap-2 md:grid-cols-5">{labels.map((label, index) => {
    const active = index <= current || done;
    return <div key={label} className={`min-h-16 rounded-md border px-3 py-2 text-sm ${active ? 'border-run/50 bg-run/10 text-slate-100' : 'border-line bg-slate-950 text-slate-500'}`}><span className="mr-2 font-mono text-xs">{index + 1}</span>{label}</div>;
  })}</div>;
}

function InfoBlock({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return <div className="rounded-md border border-line bg-slate-950/60 p-4"><div className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-200">{icon}{title}</div>{children}</div>;
}

function DecisionButton({ label, icon, disabled, secondary, onClick }: { label: string; icon: React.ReactNode; disabled: boolean; secondary?: boolean; onClick: () => void }) {
  return <button className={secondary ? 'button-secondary' : 'button-primary'} disabled={disabled} onClick={onClick}>{icon}{label}</button>;
}

function display(value: unknown) {
  if (value === null || value === undefined) return '—';
  return typeof value === 'object' ? JSON.stringify(value) : String(value);
}

function fieldLabel(language: Language, path: string) {
  if (language === 'en') return path;
  const labels: Record<string, string> = {
    'weapon_config[0].base_attack': '新手武器基础攻击力',
    'runtime_target_config[0].completion_time_seconds_min': '目标最短通关时间',
    'runtime_target_config[0].completion_time_seconds_max': '目标最长通关时间',
    'runtime_target_config[0].enemies_defeated': '目标击败敌人数',
    'runtime_target_config[0].skill_uses_min': '技能最低使用次数',
  };
  return labels[path] ?? path;
}

function testLabel(language: Language, id: string) {
  const zh: Record<string, string> = { static_contract_validation: '静态配置契约校验', unity_fixed_seed_playtest: 'Unity 固定种子试玩', first_clear_economy_check: '首通经济检查' };
  return language === 'zh' ? zh[id] ?? id : id;
}

function checkLabel(language: Language, id: string) {
  const zh: Record<string, string> = { run_completed: '关卡完成', completion_time_in_target: '通关时间', normal_enemy_hits_to_kill_in_target: '普通敌人受击次数', first_upgrade_affordable: '第一次升级可支付', second_upgrade_affordable: '第二次升级不可连续支付', enemies_defeated: '敌人击败数', enemies_defeated_in_target: '敌人击败数', skill_usage: '技能使用', skill_uses_in_target: '技能使用次数' };
  return language === 'zh' ? zh[id] ?? id : id;
}
