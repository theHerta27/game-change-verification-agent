import { AlertTriangle, FlaskConical, RefreshCw, ShieldCheck } from 'lucide-react';
import { useState } from 'react';

type Language = 'zh' | 'en';
type SampleResult = {
  sample_id: string;
  category: string;
  expectation_match: boolean;
  expected: { status: string; stage: string };
  actual: { status: string; stage: string; badcase: boolean; error_message?: string | null };
};
type BenchmarkResult = {
  dataset_id: string;
  provider_mode: string;
  model: string;
  disclaimer: string;
  metrics: Record<string, unknown>;
  samples: SampleResult[];
  exported_files: string[];
};

const copy = {
  zh: {
    title: '代码变更护栏评测',
    subtitle: '用 12 个固定样本检查需求门禁、JSON 契约、目标范围、安全门和坏例记录。不会调用真实模型、审批补丁或启动 Unity。',
    boundary: '脚本化 Provider 只验证工程护栏是否按预期工作，100% 不代表真实模型能正确编写任意 C#。',
    run: '运行护栏 Benchmark', running: '正在执行固定样本', result: '评测结论', samples: '样本明细', artifacts: '报告产物',
    expected: '预期', actual: '实际', stage: '失败阶段', match: '匹配', yes: '是', no: '否',
    metrics: {
      sample_count: '样本数', expectation_match_rate: '预期匹配率', feasibility_decision_accuracy: '门禁决策准确率',
      badcase_capture_rate: '坏例捕获率', unauthorized_change_block_rate: '越权阻断率', valid_candidate_acceptance_rate: '有效候选接受率',
      false_accept_count: '错误放行', false_reject_count: '错误拒绝', badcase_count: '坏例数', repository_unchanged: '主仓库未修改',
    },
  },
  en: {
    title: 'Code Change Guardrail Benchmark',
    subtitle: 'Runs 12 fixed samples against feasibility, JSON contract, target scope, patch safety, and badcase routing. It does not call a real model, approve a patch, or launch Unity.',
    boundary: 'The scripted provider measures deterministic guardrails. A 100% score does not mean a real model can implement arbitrary C# changes.',
    run: 'Run guardrail benchmark', running: 'Running fixed samples', result: 'Evaluation result', samples: 'Sample details', artifacts: 'Report artifacts',
    expected: 'Expected', actual: 'Actual', stage: 'Stage', match: 'Match', yes: 'Yes', no: 'No',
    metrics: {
      sample_count: 'Samples', expectation_match_rate: 'Expectation match', feasibility_decision_accuracy: 'Feasibility accuracy',
      badcase_capture_rate: 'Badcase capture', unauthorized_change_block_rate: 'Unauthorized block', valid_candidate_acceptance_rate: 'Valid acceptance',
      false_accept_count: 'False accepts', false_reject_count: 'False rejects', badcase_count: 'Badcases', repository_unchanged: 'Repository unchanged',
    },
  },
} as const;

function displayMetric(key: string, value: unknown, language: Language) {
  if (typeof value === 'number' && (key.endsWith('_rate') || key.endsWith('_accuracy'))) return `${(value * 100).toFixed(0)}%`;
  if (typeof value === 'boolean') return value ? (language === 'zh' ? '是' : 'Yes') : (language === 'zh' ? '否' : 'No');
  return String(value ?? '—');
}

export function CodeChangeBenchmarkPanel({ language }: { language: Language }) {
  const t = copy[language];
  const [result, setResult] = useState<BenchmarkResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function runBenchmark() {
    setBusy(true); setError('');
    try {
      const response = await fetch('/api/code-change-agent/benchmark', { method: 'POST' });
      if (!response.ok) throw new Error(await response.text());
      setResult(await response.json() as BenchmarkResult);
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
    finally { setBusy(false); }
  }

  const metricOrder = [
    'sample_count', 'expectation_match_rate', 'feasibility_decision_accuracy', 'badcase_capture_rate',
    'unauthorized_change_block_rate', 'valid_candidate_acceptance_rate', 'false_accept_count',
    'false_reject_count', 'badcase_count', 'repository_unchanged',
  ];
  return <section className="rounded-md border border-line bg-panel p-5 shadow-sm">
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div className="flex max-w-4xl items-start gap-3"><span className="rounded-md bg-sky-400/15 p-2 text-sky-300"><FlaskConical className="h-5 w-5"/></span><div><h2 className="text-lg font-semibold">{t.title}</h2><p className="mt-2 text-sm leading-6 text-slate-400">{t.subtitle}</p></div></div>
      <button className="button-secondary" disabled={busy} onClick={runBenchmark}>{busy ? <RefreshCw className="h-4 w-4 animate-spin"/> : <ShieldCheck className="h-4 w-4"/>}{busy ? t.running : t.run}</button>
    </div>
    <div className="mt-4 border-l-2 border-amber-400 bg-amber-400/5 px-3 py-2 text-xs leading-5 text-amber-100">{t.boundary}</div>
    {error && <p className="mt-4 rounded-md border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-100">{error}</p>}
    {result && <div className="mt-5 space-y-5">
      <div><div className="mb-3 text-sm font-semibold">{t.result}</div><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">{metricOrder.map((key) => <div key={key} className="min-w-0 rounded-md border border-line bg-slate-950/60 p-3"><div className="text-xs leading-5 text-slate-500">{t.metrics[key as keyof typeof t.metrics]}</div><div className="mt-1 text-lg font-semibold text-slate-100">{displayMetric(key, result.metrics[key], language)}</div></div>)}</div></div>
      <div><div className="mb-3 text-sm font-semibold">{t.samples}</div><div className="overflow-x-auto rounded-md border border-line"><table className="w-full min-w-[760px] text-left text-xs"><thead className="bg-slate-950 text-slate-400"><tr><th className="p-3">sample_id</th><th className="p-3">category</th><th className="p-3">{t.expected}</th><th className="p-3">{t.actual}</th><th className="p-3">{t.stage}</th><th className="p-3">{t.match}</th></tr></thead><tbody>{result.samples.map((sample) => <tr className="border-t border-line text-slate-300" key={sample.sample_id}><td className="p-3 font-mono">{sample.sample_id}</td><td className="p-3">{sample.category}</td><td className="p-3">{sample.expected.status}</td><td className="p-3">{sample.actual.status}</td><td className="p-3 font-mono">{sample.actual.stage}</td><td className="p-3">{sample.expectation_match ? <span className="text-run">{t.yes}</span> : <span className="flex items-center gap-1 text-red-300"><AlertTriangle className="h-3 w-3"/>{t.no}</span>}</td></tr>)}</tbody></table></div></div>
      <div><div className="mb-2 text-sm font-semibold">{t.artifacts}</div><ul className="space-y-1 text-xs text-slate-400">{result.exported_files.map((path) => <li className="break-all font-mono" key={path}>{path}</li>)}</ul></div>
    </div>}
  </section>;
}
