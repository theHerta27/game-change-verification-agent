import { useEffect, useState } from 'react';
import { Bot, CheckCircle2, FileCode2, RefreshCw, ShieldAlert, Sparkles, XCircle } from 'lucide-react';

type Language = 'zh' | 'en';
type Provider = 'mock' | 'openai_compatible';
type Capabilities = {
  max_target_files: number;
  allowed_target_files: string[];
  mock_recipes: Array<{ recipe_id: string; title: string; target_files: string[]; requirement_example: string; boundary: string }>;
};
type Proposal = {
  proposal_id: string; status: string; provider: string; model?: string | null;
  feasibility_gate: { decision: string; reason: string; errors: string[]; mock_recipe_id?: string | null };
  generation?: { summary: string; assumptions: string[]; target_files: string[]; diff: string; provider_evidence?: { latency_ms?: number; usage?: unknown; token_estimate?: number } } | null;
  code_workflow?: { workflow_id: string; status: string } | null;
  badcase?: { stage: string; error_type: string; error_message: string; raw_model_output?: string | null } | null;
};

const defaultTarget = 'game-unity/Assets/Scripts/RuntimeRunSettings.cs';
const copy = {
  zh: {
    title: '受控 Code Change Agent', subtitle: '描述代码需求并选择允许读取的 C# 文件。Agent 只生成候选 Diff，不能浏览其他文件、修改主仓库或绕过人工审批。',
    requirement: '代码变更需求', targetFiles: '允许读取的目标文件', generate: '生成候选 Diff', generating: '正在生成并执行安全门',
    provider: '生成模型', mock: '确定性 Mock recipe', real: '真实模型兼容接口', boundary: 'Mock 只支持运行参数空值保护，不代表通用代码生成能力。',
    gate: '生成可行性', generated: '候选 Diff 已生成，并已送入下方质量审查闭环。', clarification: '需要调整需求', rejected: '需求已被拒绝', failed: '候选生成失败',
    summary: '生成摘要', assumptions: '明确假设', diff: '候选 Unified Diff', badcase: '生成坏例', model: '模型', latency: '延迟',
    selected: '已选择', max: '最多', files: '个文件', noCapabilities: '无法读取目标文件能力清单。',
  },
  en: {
    title: 'Controlled Code Change Agent', subtitle: 'Describe a code change and select the C# files the Agent may read. It can only propose a diff and cannot browse other files, modify the repository, or bypass approval.',
    requirement: 'Code change requirement', targetFiles: 'Allowed target files', generate: 'Generate candidate diff', generating: 'Generating and running safety gates',
    provider: 'Generation provider', mock: 'Deterministic Mock recipe', real: 'OpenAI-compatible provider', boundary: 'Mock only supports the runtime argument null-guard recipe; it is not a general code model.',
    gate: 'Generation feasibility', generated: 'Candidate diff generated and sent to the quality workflow below.', clarification: 'Requirement needs adjustment', rejected: 'Requirement rejected', failed: 'Candidate generation failed',
    summary: 'Generation summary', assumptions: 'Explicit assumptions', diff: 'Candidate unified diff', badcase: 'Generation badcase', model: 'Model', latency: 'Latency',
    selected: 'Selected', max: 'up to', files: 'files', noCapabilities: 'Target-file capabilities are unavailable.',
  },
} as const;

export function CodeChangeAgentPanel({ language, provider, timeoutSeconds, onGenerated }: {
  language: Language; provider: Provider; timeoutSeconds: number; onGenerated: (workflowId: string) => void;
}) {
  const t = copy[language];
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null);
  const [requirement, setRequirement] = useState('为 RuntimeRunSettings.FromArgs 增加 args 空值保护，不改变现有玩法。');
  const [targets, setTargets] = useState<string[]>([defaultTarget]);
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetch('/api/code-change-agent/capabilities').then(async (response) => {
      if (!response.ok) throw new Error(await response.text());
      setCapabilities(await response.json());
    }).catch((cause) => setError(cause instanceof Error ? cause.message : String(cause)));
  }, []);

  function toggleTarget(path: string) {
    const selected = targets.includes(path);
    if (selected) { setTargets(targets.filter((item) => item !== path)); return; }
    if (capabilities && targets.length >= capabilities.max_target_files) return;
    setTargets([...targets, path]);
  }

  async function generate() {
    setBusy(true); setError(''); setProposal(null);
    try {
      const response = await fetch('/api/code-change-agent/proposals', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ requirement_text: requirement, target_files: targets, provider, timeout_seconds: timeoutSeconds }),
      });
      if (!response.ok) { const payload = await response.json().catch(() => ({ detail: response.statusText })); throw new Error(payload.detail ?? response.statusText); }
      const result = await response.json() as Proposal;
      setProposal(result);
      if (result.code_workflow?.workflow_id) onGenerated(result.code_workflow.workflow_id);
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
    finally { setBusy(false); }
  }

  const statusText = proposal?.status === 'generated' ? t.generated : proposal?.status === 'needs_clarification' ? t.clarification : proposal?.status === 'rejected' ? t.rejected : t.failed;
  return <section className="rounded-md border border-line bg-panel p-5 shadow-sm">
    <div className="flex items-start gap-3"><span className="rounded-md bg-run/15 p-2 text-run"><Bot className="h-5 w-5"/></span><div><h2 className="text-lg font-semibold">{t.title}</h2><p className="mt-2 max-w-4xl text-sm leading-6 text-slate-400">{t.subtitle}</p></div></div>
    <div className="mt-4 border-l-2 border-amber-400 bg-amber-400/5 px-3 py-2 text-xs leading-5 text-amber-100">{t.boundary}</div>

    <div className="mt-5 grid gap-4">
      <label className="label">{t.requirement}<textarea className="input mt-1 min-h-28 resize-y" value={requirement} onChange={(event) => setRequirement(event.target.value)}/></label>
      <div><div className="mb-2 flex flex-wrap items-center justify-between gap-2"><span className="label mb-0">{t.targetFiles}</span><span className="text-xs text-slate-400">{t.selected} {targets.length} · {t.max} {capabilities?.max_target_files ?? 3} {t.files}</span></div>
        {!capabilities ? <p className="text-sm text-slate-500">{t.noCapabilities}</p> : <div className="grid max-h-56 gap-2 overflow-auto rounded-md border border-line bg-slate-950 p-3 md:grid-cols-2">{capabilities.allowed_target_files.map((path) => <label key={path} className="flex cursor-pointer items-start gap-2 rounded-sm px-2 py-2 text-xs text-slate-300 hover:bg-panel2"><input className="mt-0.5 accent-emerald-400" type="checkbox" checked={targets.includes(path)} onChange={() => toggleTarget(path)}/><span className="break-all font-mono">{path}</span></label>)}</div>}
      </div>
      <div className="grid gap-2 text-xs text-slate-400 md:grid-cols-2"><div className="border-l-2 border-run bg-panel2 px-3 py-2"><strong className="text-slate-200">{t.provider}：</strong>{provider === 'mock' ? t.mock : t.real}</div><div className="border-l-2 border-sky-400 bg-panel2 px-3 py-2">timeout_seconds: {timeoutSeconds}</div></div>
      <button className="button-primary w-fit" disabled={busy || !requirement.trim() || !targets.length} onClick={generate}>{busy ? <RefreshCw className="h-4 w-4 animate-spin"/> : <Sparkles className="h-4 w-4"/>}{busy ? t.generating : t.generate}</button>
    </div>

    {error && <p className="mt-4 rounded-md border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-100">{error}</p>}
    {proposal && <div className="mt-5 space-y-4">
      <div className={`flex items-start gap-2 border-l-2 px-3 py-3 text-sm ${proposal.status === 'generated' ? 'border-run bg-run/5 text-green-100' : 'border-red-400 bg-red-400/5 text-red-100'}`}>{proposal.status === 'generated' ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0"/> : <XCircle className="mt-0.5 h-4 w-4 shrink-0"/>}<div><strong>{statusText}</strong><p className="mt-1 text-slate-400">{proposal.feasibility_gate.reason}</p></div></div>
      <div className="rounded-md border border-line bg-slate-950/60 p-4"><div className="mb-3 flex items-center gap-2 text-sm font-semibold"><ShieldAlert className="h-4 w-4 text-run"/>{t.gate}</div><p className="text-sm text-slate-300">{proposal.feasibility_gate.decision}</p>{proposal.feasibility_gate.errors.map((item) => <p className="mt-2 text-sm text-red-200" key={item}>{item}</p>)}</div>
      {proposal.generation && <><div className="grid gap-4 lg:grid-cols-2"><div className="rounded-md border border-line bg-slate-950/60 p-4"><div className="text-sm font-semibold">{t.summary}</div><p className="mt-2 text-sm text-slate-300">{proposal.generation.summary}</p><div className="mt-3 text-xs text-slate-500">{t.model}: {proposal.model ?? '—'} · {t.latency}: {proposal.generation.provider_evidence?.latency_ms ?? 0}ms</div></div><div className="rounded-md border border-line bg-slate-950/60 p-4"><div className="text-sm font-semibold">{t.assumptions}</div><ul className="mt-2 space-y-2 text-sm text-slate-400">{proposal.generation.assumptions.map((item) => <li key={item}>· {item}</li>)}</ul></div></div><div className="rounded-md border border-line bg-slate-950/60 p-4"><div className="mb-3 flex items-center gap-2 text-sm font-semibold"><FileCode2 className="h-4 w-4"/>{t.diff}</div><pre className="max-h-96 overflow-auto rounded-md bg-slate-950 p-4 text-xs leading-5 text-slate-200">{proposal.generation.diff}</pre></div></>}
      {proposal.badcase && <div className="rounded-md border border-red-500/40 bg-red-500/10 p-4"><div className="text-sm font-semibold text-red-100">{t.badcase}</div><p className="mt-2 font-mono text-xs text-red-200">{proposal.badcase.stage} · {proposal.badcase.error_type}</p><p className="mt-2 text-sm text-slate-300">{proposal.badcase.error_message}</p></div>}
    </div>}
  </section>;
}
