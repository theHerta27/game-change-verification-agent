import { AlertTriangle, CheckCircle2, CloudCog, RefreshCw } from 'lucide-react';
import { useEffect, useState } from 'react';

type Language = 'zh' | 'en';
type ConfigStatus = { configured: boolean; variables: Record<string, boolean>; missing: string[] };
type Dataset = { dataset_id: string; title: string; scope: string; sample_count: number };
type Sample = {
  sample_id: string; title: string; proposal_status: string;
  stages: Record<string, boolean>; badcase?: { stage: string; error_message: string } | null;
};
type Result = {
  run_status: 'blocked' | 'completed'; dataset_id: string; provider: string; model?: string | null;
  evidence_boundary: string; metrics: Record<string, unknown>; samples: Sample[];
  configuration_error?: { error_message: string } | null; exported_files: string[];
};

const copy = {
  zh: {
    title: '真实模型代码生成评测', subtitle: '对 5 个固定 Unity C# 防御式需求调用 OpenAI Compatible Provider，分别检查输出契约、安全、质量、补丁可应用性和语义证据。',
    staticBoundary: '本面板不会自动审批、编译、启动 Unity 或合并代码。candidate_ready 仅表示静态证据齐全。',
    configured: 'Provider 配置已就绪', missing: 'Provider 尚未配置', variables: '所需环境变量', dataset: '评测数据集', samples: '个真实调用样本',
    run: '运行 5 个真实样本', blockedRun: '生成配置阻塞报告', running: '真实模型评测执行中', result: '真实评测结果', blocked: '评测未运行', completed: '评测已完成',
    details: '样本结果', artifacts: '报告产物', model: '模型', status: '状态', semantic: '语义', ready: '候选就绪', noScore: '没有发生模型调用，空指标不能解释为模型 0 分。',
    metrics: {
      sample_count: '样本数', provider_call_success_rate: '调用成功率', json_parse_success_rate: 'JSON 解析率', generation_contract_pass_rate: '输出契约通过率',
      patch_safety_pass_rate: '安全门通过率', quality_review_pass_rate: '质量审查通过率', patch_apply_success_rate: '补丁可应用率',
      semantic_intent_pass_rate: '语义意图命中率', semantic_requirement_pass_rate: '应用后语义通过率', candidate_ready_rate: '候选就绪率', badcase_count: '坏例数', repository_unchanged: '主仓库未修改',
    },
  },
  en: {
    title: 'Real-model Code Generation Evaluation', subtitle: 'Calls the OpenAI-compatible provider for five fixed defensive Unity C# changes and checks contract, safety, quality, patch applicability, and semantic evidence.',
    staticBoundary: 'This panel never auto-approves, compiles, launches Unity, or merges code. candidate_ready only means static evidence is complete.',
    configured: 'Provider configuration ready', missing: 'Provider not configured', variables: 'Required environment variables', dataset: 'Evaluation dataset', samples: 'real provider samples',
    run: 'Run 5 real samples', blockedRun: 'Generate blocked report', running: 'Running real-model evaluation', result: 'Real evaluation result', blocked: 'Evaluation not run', completed: 'Evaluation completed',
    details: 'Sample results', artifacts: 'Report artifacts', model: 'Model', status: 'Status', semantic: 'Semantic', ready: 'Candidate ready', noScore: 'No model call occurred; empty metrics are not a zero model score.',
    metrics: {
      sample_count: 'Samples', provider_call_success_rate: 'Provider success', json_parse_success_rate: 'JSON parse', generation_contract_pass_rate: 'Contract pass',
      patch_safety_pass_rate: 'Safety pass', quality_review_pass_rate: 'Quality pass', patch_apply_success_rate: 'Patch apply',
      semantic_intent_pass_rate: 'Semantic intent', semantic_requirement_pass_rate: 'Applied semantics', candidate_ready_rate: 'Candidate ready', badcase_count: 'Badcases', repository_unchanged: 'Repository unchanged',
    },
  },
} as const;

function metricValue(key: string, value: unknown, language: Language) {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'number' && key.endsWith('_rate')) return `${(value * 100).toFixed(0)}%`;
  if (typeof value === 'boolean') return value ? (language === 'zh' ? '是' : 'Yes') : (language === 'zh' ? '否' : 'No');
  return String(value);
}

export function RealCodeEvaluationPanel({ language, timeoutSeconds }: { language: Language; timeoutSeconds: number }) {
  const t = copy[language];
  const [config, setConfig] = useState<ConfigStatus | null>(null);
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([
      fetch('/api/code-change-agent/real-evaluation/config').then((response) => response.json()),
      fetch('/api/code-change-agent/real-evaluation/dataset').then((response) => response.json()),
      fetch('/api/code-change-agent/real-evaluation/latest').then((response) => response.ok ? response.json() : null),
    ]).then(([configuration, data, latest]) => { setConfig(configuration); setDataset(data); if (latest) setResult(latest); })
      .catch((cause) => setError(cause instanceof Error ? cause.message : String(cause)));
  }, []);

  async function run() {
    setBusy(true); setError(''); setResult(null);
    try {
      const response = await fetch('/api/code-change-agent/real-evaluation', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ timeout_seconds: timeoutSeconds }),
      });
      if (!response.ok) throw new Error(await response.text());
      setResult(await response.json() as Result);
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
    finally { setBusy(false); }
  }

  const metricOrder = ['sample_count', 'provider_call_success_rate', 'json_parse_success_rate', 'generation_contract_pass_rate', 'patch_safety_pass_rate', 'quality_review_pass_rate', 'patch_apply_success_rate', 'semantic_intent_pass_rate', 'semantic_requirement_pass_rate', 'candidate_ready_rate', 'badcase_count', 'repository_unchanged'];
  return <section className="rounded-md border border-line bg-panel p-5 shadow-sm">
    <div className="flex flex-wrap items-start justify-between gap-4"><div className="flex max-w-4xl items-start gap-3"><span className="rounded-md bg-violet-400/15 p-2 text-violet-300"><CloudCog className="h-5 w-5"/></span><div><h2 className="text-lg font-semibold">{t.title}</h2><p className="mt-2 text-sm leading-6 text-slate-400">{t.subtitle}</p></div></div><button className="button-secondary" disabled={busy} onClick={run}>{busy ? <RefreshCw className="h-4 w-4 animate-spin"/> : <CloudCog className="h-4 w-4"/>}{busy ? t.running : config?.configured ? t.run : t.blockedRun}</button></div>
    <div className="mt-4 border-l-2 border-violet-400 bg-violet-400/5 px-3 py-2 text-xs leading-5 text-violet-100">{t.staticBoundary}</div>
    <div className="mt-4 grid gap-3 md:grid-cols-2"><div className={`rounded-md border p-3 ${config?.configured ? 'border-run/40 bg-run/5' : 'border-amber-400/40 bg-amber-400/5'}`}><div className="flex items-center gap-2 text-sm font-semibold">{config?.configured ? <CheckCircle2 className="h-4 w-4 text-run"/> : <AlertTriangle className="h-4 w-4 text-amber-300"/>}{config?.configured ? t.configured : t.missing}</div><div className="mt-2 break-all font-mono text-xs text-slate-400">{t.variables}：GAMECONFIG_LLM_BASE_URL / GAMECONFIG_LLM_API_KEY / GAMECONFIG_LLM_MODEL</div>{config?.missing?.length ? <div className="mt-2 break-all font-mono text-xs text-amber-200">missing: {config.missing.join(', ')}</div> : null}</div><div className="rounded-md border border-line bg-slate-950/60 p-3"><div className="text-sm font-semibold">{t.dataset}</div><div className="mt-2 font-mono text-xs text-slate-400">{dataset?.dataset_id ?? '—'}</div><div className="mt-1 text-xs text-slate-500">{dataset?.sample_count ?? 5} {t.samples}</div></div></div>
    {error && <p className="mt-4 rounded-md border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-100">{error}</p>}
    {result && <div className="mt-5 space-y-5"><div className={`border-l-2 px-3 py-3 text-sm ${result.run_status === 'completed' ? 'border-run bg-run/5 text-green-100' : 'border-amber-400 bg-amber-400/5 text-amber-100'}`}><strong>{result.run_status === 'completed' ? t.completed : t.blocked}</strong><p className="mt-1 text-slate-400">{result.configuration_error?.error_message ?? result.evidence_boundary}</p>{result.run_status === 'blocked' && <p className="mt-2 text-xs text-amber-200">{t.noScore}</p>}</div><div><div className="mb-3 text-sm font-semibold">{t.result}</div><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{metricOrder.map((key) => <div key={key} className="rounded-md border border-line bg-slate-950/60 p-3"><div className="text-xs leading-5 text-slate-500">{t.metrics[key as keyof typeof t.metrics]}</div><div className="mt-1 text-lg font-semibold">{metricValue(key, result.metrics[key], language)}</div></div>)}</div></div>{result.run_status === 'completed' && <div><div className="mb-3 text-sm font-semibold">{t.details}</div><div className="overflow-x-auto rounded-md border border-line"><table className="w-full min-w-[700px] text-left text-xs"><thead className="bg-slate-950 text-slate-400"><tr><th className="p-3">sample_id</th><th className="p-3">{t.status}</th><th className="p-3">{t.semantic}</th><th className="p-3">{t.ready}</th><th className="p-3">badcase</th></tr></thead><tbody>{result.samples.map((sample) => <tr className="border-t border-line text-slate-300" key={sample.sample_id}><td className="p-3 font-mono">{sample.sample_id}</td><td className="p-3">{sample.proposal_status}</td><td className="p-3">{String(sample.stages.semantic_requirement_pass ?? false)}</td><td className="p-3">{String(sample.stages.candidate_ready ?? false)}</td><td className="p-3 font-mono">{sample.badcase?.stage ?? '—'}</td></tr>)}</tbody></table></div></div>}<div><div className="mb-2 text-sm font-semibold">{t.artifacts}</div><ul className="space-y-1 text-xs text-slate-400">{result.exported_files.map((path) => <li className="break-all font-mono" key={path}>{path}</li>)}</ul></div></div>}
  </section>;
}
