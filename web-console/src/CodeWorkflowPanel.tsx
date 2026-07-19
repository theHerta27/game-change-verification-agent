import { useEffect, useState } from 'react';
import {
  CheckCircle2, Code2, FileCode2, FlaskConical, RefreshCw,
  RotateCcw, ShieldCheck, ThumbsUp, Wrench, XCircle
} from 'lucide-react';

type Language = 'zh' | 'en';
type Provider = 'mock' | 'openai_compatible';
type Finding = { severity: string; category: string; title: string; evidence: string; suggestion: string; file_path: string; line_number: number };
type CodeWorkflow = {
  workflow_id: string; title: string; status: string; provider: string; model?: string | null; source?: 'human' | 'code_change_agent';
  patch_safety_gate?: { passed: boolean; file_count: number; changed_line_count: number; errors: Array<{ rule_id: string; message: string; path?: string; line?: number }> } | null;
  quality_review?: { findings: Finding[]; test_suggestions: Array<{ test_name: string; description: string }>; validation_errors: string[] } | null;
  isolated_apply?: { changed_paths: string[]; baseline_unchanged: boolean } | null;
  validation_result?: { passed: boolean; compilation_passed: boolean; editor_smoke_passed: boolean; player_runs_passed: boolean; repeatability_passed: boolean; repeatability_rate?: number; runtime_target_pass_rate?: number; error?: { type: string; message: string } | null } | null;
  approval?: { approver: string; note: string } | null;
  final_decision?: { decision: string; actor: string; note: string; patch_applied_to_repository: boolean } | null;
  available_artifacts: Array<{ name: string; size: number }>;
  timeline: Array<{ step: string; status: string }>;
  error?: { type: string; message: string } | null;
};

const safePatch = `diff --git a/game-unity/Assets/Scripts/RuntimeRunSettings.cs b/game-unity/Assets/Scripts/RuntimeRunSettings.cs
--- a/game-unity/Assets/Scripts/RuntimeRunSettings.cs
+++ b/game-unity/Assets/Scripts/RuntimeRunSettings.cs
@@ -13,6 +13,8 @@ namespace GameConfig.Runtime
         public static RuntimeRunSettings FromArgs(string[] args)
         {
+            if (args == null)
+                throw new ArgumentNullException(nameof(args));
             RuntimeRunSettings settings = new()
             {
                 AutoRun = Array.IndexOf(args, "--auto-run") >= 0,
`;

const copy = {
  zh: {
    title: '人工 C# Diff 质量闭环', subtitle: '开发者提交候选补丁，系统负责安全审查和隔离验证；Agent 不生成补丁，也不会修改主仓库。',
    agentTitle: 'Agent 候选 Diff 质量闭环', agentSubtitle: '上方 Agent 已生成候选补丁；本区域使用确定性安全门、质量审查、人工审批和隔离 Unity 验证，仍不会修改主仓库。',
    patchTitle: '变更标题', reason: '变更原因', patch: 'Unified Diff', create: '提交补丁并审查', reviewing: '正在审查',
    status: '当前状态', safety: '补丁安全门', quality: '质量审查', tests: '建议验证', approveTitle: '人工审批',
    approver: '审批人', note: '审批说明', approve: '批准进入隔离验证', prepare: '创建隔离 Unity 工作区', validate: '运行 Unity 验证',
    running: 'Unity 正在后台编译并执行两次固定种子自动试玩。', evidence: '验证证据', compilation: 'C# 编译与 Windows Build',
    editorSmoke: '编辑器确定性 smoke', playerRuns: 'Player 双跑', repeatability: '固定种子可重复性', targetRate: '运行目标通过率',
    decision: '最终人工决策', decisionNote: '记录为什么接受、要求修订或回滚', accept: '接受，待人工合并', revise: '要求修订', rollback: '回滚候选',
    actor: '决策人', baseline: '主仓库保持不变', artifacts: '证据文件', load: '查看', refresh: '刷新', newPatch: '开始新的补丁',
    boundary: '“接受”只形成可审计结论，不会自动把补丁合并到主仓库。', noFindings: '未发现静态风险。', noTests: '没有额外测试建议。',
    passed: '通过', failed: '失败', pending: '等待', highRisk: '高风险补丁已被拦截，不能进入审批和 Unity。',
  },
  en: {
    title: 'Human C# Diff Quality Loop', subtitle: 'A developer submits a candidate patch. The system reviews and validates it in isolation; the Agent neither writes the patch nor modifies the repository.',
    agentTitle: 'Agent Candidate Diff Quality Loop', agentSubtitle: 'The Agent proposed the patch above. Deterministic safety gates, review, approval, and isolated Unity validation still apply, and the repository remains unchanged.',
    patchTitle: 'Change title', reason: 'Change reason', patch: 'Unified Diff', create: 'Submit and review patch', reviewing: 'Reviewing',
    status: 'Status', safety: 'Patch safety gate', quality: 'Quality review', tests: 'Suggested validation', approveTitle: 'Human approval',
    approver: 'Approver', note: 'Approval note', approve: 'Approve isolated validation', prepare: 'Create isolated Unity workspace', validate: 'Run Unity validation',
    running: 'Unity is compiling and running two fixed-seed playtests in the background.', evidence: 'Validation evidence', compilation: 'C# compile and Windows Build',
    editorSmoke: 'Deterministic editor smoke', playerRuns: 'Two Player runs', repeatability: 'Fixed-seed repeatability', targetRate: 'Runtime target pass rate',
    decision: 'Final human decision', decisionNote: 'Explain why the patch is accepted, revised, or rolled back', accept: 'Accept for manual merge', revise: 'Request revision', rollback: 'Roll back candidate',
    actor: 'Decision maker', baseline: 'Repository remains unchanged', artifacts: 'Evidence artifacts', load: 'View', refresh: 'Refresh', newPatch: 'Start another patch',
    boundary: 'Accepting records an auditable decision; it never merges the patch into the repository.', noFindings: 'No static risks found.', noTests: 'No additional test suggestions.',
    passed: 'Passed', failed: 'Failed', pending: 'Pending', highRisk: 'The high-risk patch is blocked before approval and Unity validation.',
  },
} as const;

const statuses: Record<Language, Record<string, string>> = {
  zh: { reviewing: '审查中', proposed: '等待审批', approved: '已批准', workspace_prepared: '隔离工作区已准备', validation_running: 'Unity 验证中', evidence_ready: '证据已完成', accepted: '已接受，待人工合并', revision_requested: '需要修订', rolled_back: '已回滚', rejected: '已拦截', failed: '验证失败' },
  en: { reviewing: 'Reviewing', proposed: 'Awaiting approval', approved: 'Approved', workspace_prepared: 'Workspace ready', validation_running: 'Unity validation running', evidence_ready: 'Evidence ready', accepted: 'Accepted for manual merge', revision_requested: 'Revision requested', rolled_back: 'Rolled back', rejected: 'Blocked', failed: 'Validation failed' },
};

export function CodeWorkflowPanel({ language, provider, timeoutSeconds, loadWorkflowId }: { language: Language; provider: Provider; timeoutSeconds: number; loadWorkflowId?: string | null }) {
  const t = copy[language];
  const [title, setTitle] = useState(language === 'zh' ? '运行参数空值保护' : 'Runtime argument null guard');
  const [reason, setReason] = useState(language === 'zh' ? '为运行参数解析增加明确失败路径，不改变玩法。' : 'Add an explicit failure path without changing gameplay.');
  const [diff, setDiff] = useState(safePatch);
  const [workflow, setWorkflow] = useState<CodeWorkflow | null>(null);
  const [approver, setApprover] = useState(language === 'zh' ? '开发者演示者' : 'Demo developer');
  const [note, setNote] = useState('');
  const [decisionNote, setDecisionNote] = useState('');
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [artifact, setArtifact] = useState('');
  const agentCandidate = workflow?.source === 'code_change_agent';

  useEffect(() => {
    if (!loadWorkflowId) return;
    setBusy('load'); setError('');
    request(`/api/code-workflows/${loadWorkflowId}`).then(setWorkflow).catch((cause) => setError(String(cause))).finally(() => setBusy(''));
  }, [loadWorkflowId]);

  useEffect(() => {
    if (workflow?.status !== 'validation_running') return;
    const timer = window.setInterval(() => refresh(workflow.workflow_id), 1500);
    return () => window.clearInterval(timer);
  }, [workflow?.workflow_id, workflow?.status]);

  async function request(path: string, body?: unknown) {
    const response = await fetch(path, { method: body === undefined ? 'GET' : 'POST', headers: body === undefined ? undefined : { 'Content-Type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body) });
    if (!response.ok) { const payload = await response.json().catch(() => ({ detail: response.statusText })); throw new Error(payload.detail ?? response.statusText); }
    return response.json() as Promise<CodeWorkflow>;
  }
  async function act(key: string, operation: () => Promise<CodeWorkflow>) {
    setBusy(key); setError('');
    try { setWorkflow(await operation()); } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); } finally { setBusy(''); }
  }
  function refresh(id: string) { return request(`/api/code-workflows/${id}`).then(setWorkflow).catch((cause) => setError(String(cause))); }
  async function loadArtifact(name: string) {
    if (!workflow) return;
    setError('');
    try { const response = await fetch(`/api/code-workflows/${workflow.workflow_id}/artifacts/${name}`); if (!response.ok) throw new Error(await response.text()); setArtifact(await response.text()); }
    catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
  }

  return <section className="rounded-md border border-line bg-panel p-5 shadow-sm">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div><div className="flex items-center gap-2"><FileCode2 className="h-5 w-5 text-run"/><h2 className="text-lg font-semibold">{agentCandidate ? t.agentTitle : t.title}</h2></div><p className="mt-2 max-w-4xl text-sm leading-6 text-slate-400">{agentCandidate ? t.agentSubtitle : t.subtitle}</p></div>
      {workflow && <div className="rounded-md border border-line bg-slate-950 px-3 py-2 text-sm"><span className="text-slate-400">{t.status}: </span><strong className="text-run">{statuses[language][workflow.status] ?? workflow.status}</strong></div>}
    </div>

    {!workflow && <div className="mt-5 grid gap-4">
      <div className="grid gap-3 md:grid-cols-2"><label className="label">{t.patchTitle}<input className="input mt-1" value={title} onChange={(event) => setTitle(event.target.value)}/></label><label className="label">{t.reason}<input className="input mt-1" value={reason} onChange={(event) => setReason(event.target.value)}/></label></div>
      <label className="label">{t.patch}<textarea className="input mt-1 min-h-64 resize-y font-mono text-xs leading-5" spellCheck={false} value={diff} onChange={(event) => setDiff(event.target.value)}/></label>
      <button className="button-primary w-fit" disabled={!!busy || !title.trim() || !reason.trim() || !diff.trim()} onClick={() => act('create', () => request('/api/code-workflows', { title, change_reason: reason, diff_text: diff, provider, timeout_seconds: timeoutSeconds }))}>{busy === 'create' ? <RefreshCw className="h-4 w-4 animate-spin"/> : <ShieldCheck className="h-4 w-4"/>}{busy === 'create' ? t.reviewing : t.create}</button>
    </div>}

    {error && <p className="mt-4 rounded-md border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-100">{error}</p>}
    {workflow && <div className="mt-5 space-y-4">
      <StepGrid language={language} status={workflow.status}/>
      {workflow.patch_safety_gate && <Block title={t.safety} icon={workflow.patch_safety_gate.passed ? <CheckCircle2 className="h-4 w-4 text-run"/> : <XCircle className="h-4 w-4 text-red-300"/>}>
        <div className="grid gap-2 sm:grid-cols-3"><Metric label={language === 'zh' ? '结论' : 'Result'} value={workflow.patch_safety_gate.passed ? t.passed : t.failed}/><Metric label={language === 'zh' ? '文件数' : 'Files'} value={String(workflow.patch_safety_gate.file_count)}/><Metric label={language === 'zh' ? '变更行' : 'Changed lines'} value={String(workflow.patch_safety_gate.changed_line_count)}/></div>
        {workflow.patch_safety_gate.errors.map((item) => <div key={`${item.rule_id}-${item.line}`} className="mt-3 border-l-2 border-red-400 pl-3 text-sm"><strong>{item.rule_id}</strong><p className="mt-1 text-slate-400">{item.path}{item.line ? `:${item.line}` : ''} {item.message}</p></div>)}
        {!workflow.patch_safety_gate.passed && <p className="mt-3 text-sm text-red-200">{t.highRisk}</p>}
      </Block>}

      {workflow.quality_review && <div className="grid gap-4 lg:grid-cols-2"><Block title={t.quality} icon={<Code2 className="h-4 w-4"/>}>{workflow.quality_review.findings.length ? workflow.quality_review.findings.map((finding, index) => <div key={index} className="mb-3 border-l-2 border-amber-400 pl-3 text-sm"><div className="flex gap-2"><strong>{finding.title}</strong><span className="font-mono text-xs text-amber-200">{finding.severity}</span></div><p className="mt-1 text-slate-400">{finding.file_path}:{finding.line_number} · {finding.evidence}</p><p className="mt-1 text-slate-300">{finding.suggestion}</p></div>) : <p className="text-sm text-slate-400">{t.noFindings}</p>}</Block><Block title={t.tests} icon={<FlaskConical className="h-4 w-4"/>}>{workflow.quality_review.test_suggestions.length ? workflow.quality_review.test_suggestions.map((test) => <div key={test.test_name} className="mb-3 text-sm"><strong>{test.test_name}</strong><p className="mt-1 text-slate-400">{test.description}</p></div>) : <p className="text-sm text-slate-400">{t.noTests}</p>}</Block></div>}

      {workflow.status === 'proposed' && <Block title={t.approveTitle} icon={<ThumbsUp className="h-4 w-4"/>}><div className="grid gap-3 md:grid-cols-2"><label className="label">{t.approver}<input className="input mt-1" value={approver} onChange={(event) => setApprover(event.target.value)}/></label><label className="label">{t.note}<input className="input mt-1" value={note} onChange={(event) => setNote(event.target.value)}/></label></div><button className="button-primary mt-3" disabled={!!busy || !approver.trim()} onClick={() => act('approve', () => request(`/api/code-workflows/${workflow.workflow_id}/approve`, { approver, note }))}><ThumbsUp className="h-4 w-4"/>{t.approve}</button></Block>}
      {workflow.status === 'approved' && <button className="button-primary" disabled={!!busy} onClick={() => act('prepare', () => request(`/api/code-workflows/${workflow.workflow_id}/workspace`, {}))}><Wrench className="h-4 w-4"/>{t.prepare}</button>}
      {workflow.status === 'workspace_prepared' && <div><p className="mb-3 text-sm text-run"><CheckCircle2 className="mr-2 inline h-4 w-4"/>{t.baseline}</p><button className="button-primary" disabled={!!busy} onClick={() => act('validate', () => request(`/api/code-workflows/${workflow.workflow_id}/validate`, {}))}><FlaskConical className="h-4 w-4"/>{t.validate}</button></div>}
      {workflow.status === 'validation_running' && <p className="flex items-center gap-2 text-sm text-slate-300"><RefreshCw className="h-4 w-4 animate-spin text-run"/>{t.running}</p>}

      {workflow.validation_result && <Block title={t.evidence} icon={<FlaskConical className="h-4 w-4"/>}><div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5"><PassMetric label={t.compilation} passed={workflow.validation_result.compilation_passed} t={t}/><PassMetric label={t.editorSmoke} passed={workflow.validation_result.editor_smoke_passed} t={t}/><PassMetric label={t.playerRuns} passed={workflow.validation_result.player_runs_passed} t={t}/><PassMetric label={t.repeatability} passed={workflow.validation_result.repeatability_passed} t={t}/><Metric label={t.targetRate} value={workflow.validation_result.runtime_target_pass_rate == null ? '—' : `${(workflow.validation_result.runtime_target_pass_rate * 100).toFixed(1)}%`}/></div>{workflow.validation_result.error && <p className="mt-3 text-sm text-red-200">{workflow.validation_result.error.type}: {workflow.validation_result.error.message}</p>}</Block>}

      {workflow.status === 'evidence_ready' && <Block title={t.decision} icon={<CheckCircle2 className="h-4 w-4"/>}><p className="mb-3 border-l-2 border-amber-400 pl-3 text-sm text-amber-100">{t.boundary}</p><div className="grid gap-3 md:grid-cols-2"><label className="label">{t.actor}<input className="input mt-1" value={approver} onChange={(event) => setApprover(event.target.value)}/></label><label className="label">{t.decisionNote}<input className="input mt-1" value={decisionNote} onChange={(event) => setDecisionNote(event.target.value)}/></label></div><div className="mt-3 flex flex-wrap gap-2"><Decision label={t.accept} disabled={!decisionNote.trim() || !!busy} onClick={() => act('accept', () => request(`/api/code-workflows/${workflow.workflow_id}/decision`, { decision: 'accept', actor: approver, note: decisionNote }))}/><Decision label={t.revise} secondary disabled={!decisionNote.trim() || !!busy} onClick={() => act('revise', () => request(`/api/code-workflows/${workflow.workflow_id}/decision`, { decision: 'revise', actor: approver, note: decisionNote }))}/><Decision label={t.rollback} secondary disabled={!decisionNote.trim() || !!busy} onClick={() => act('rollback', () => request(`/api/code-workflows/${workflow.workflow_id}/decision`, { decision: 'rollback', actor: approver, note: decisionNote }))}/></div></Block>}

      {workflow.available_artifacts.length > 0 && <Block title={t.artifacts} icon={<FileCode2 className="h-4 w-4"/>}><div className="flex flex-wrap gap-2">{workflow.available_artifacts.map((item) => <button className="chip" key={item.name} onClick={() => loadArtifact(item.name)}>{t.load} {item.name}</button>)}</div>{artifact && <pre className="mt-3 max-h-80 overflow-auto rounded-md bg-slate-950 p-4 text-xs leading-5 text-slate-200">{artifact}</pre>}</Block>}
      <div className="flex flex-wrap gap-2"><button className="button-secondary" disabled={!!busy} onClick={() => refresh(workflow.workflow_id)}><RefreshCw className="h-4 w-4"/>{t.refresh}</button>{['accepted','revision_requested','rolled_back','rejected','failed'].includes(workflow.status) && <button className="button-secondary" onClick={() => { setWorkflow(null); setArtifact(''); setError(''); }}><RotateCcw className="h-4 w-4"/>{t.newPatch}</button>}</div>
    </div>}
  </section>;
}

function StepGrid({ language, status }: { language: Language; status: string }) { const labels = language === 'zh' ? ['提交补丁','安全与质量审查','人工审批','隔离应用','Unity 验证','人工结论'] : ['Submit','Safety & review','Approval','Isolated apply','Unity validation','Decision']; const order = ['reviewing','proposed','approved','workspace_prepared','validation_running','evidence_ready','accepted']; const current = Math.max(0, order.indexOf(status)); const terminal = ['accepted','revision_requested','rolled_back'].includes(status); return <div className="grid grid-cols-2 gap-2 lg:grid-cols-6">{labels.map((label,index) => <div key={label} className={`min-h-14 rounded-md border px-3 py-2 text-xs ${index <= current || terminal ? 'border-run/50 bg-run/10 text-slate-100' : 'border-line bg-slate-950 text-slate-500'}`}><span className="mr-1 font-mono">{index + 1}</span>{label}</div>)}</div>; }
function Block({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) { return <div className="rounded-md border border-line bg-slate-950/60 p-4"><div className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-200">{icon}{title}</div>{children}</div>; }
function Metric({ label, value }: { label: string; value: string }) { return <div className="border-l-2 border-run bg-panel2 px-3 py-2"><div className="text-xs text-slate-400">{label}</div><div className="mt-1 text-sm font-medium text-slate-50">{value}</div></div>; }
function PassMetric({ label, passed, t }: { label: string; passed: boolean; t: typeof copy.zh | typeof copy.en }) { return <Metric label={label} value={passed ? t.passed : t.failed}/>; }
function Decision({ label, disabled, secondary, onClick }: { label: string; disabled: boolean; secondary?: boolean; onClick: () => void }) { return <button className={secondary ? 'button-secondary' : 'button-primary'} disabled={disabled} onClick={onClick}>{secondary ? <Wrench className="h-4 w-4"/> : <ThumbsUp className="h-4 w-4"/>}{label}</button>; }
