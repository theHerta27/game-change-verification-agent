import React, { useState } from 'react';
import { Activity, RefreshCw } from 'lucide-react';

type Language = 'zh' | 'en';
type Result = { disclaimer: string; metrics: Record<string, number> };

export function BulletHellBenchmarkPanel({ language }: { language: Language }) {
  const [result, setResult] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const zh = language === 'zh';

  async function run() {
    setBusy(true); setError('');
    try {
      const response = await fetch('/api/bullet-hell/benchmark', { method: 'POST' });
      if (!response.ok) throw new Error(await response.text());
      setResult(await response.json());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setBusy(false);
    }
  }

  return <section className="rounded-md border border-line bg-panel p-4">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h3 className="flex items-center gap-2 text-base font-semibold"><Activity className="h-4 w-4 text-violet-300"/>{zh ? '弹幕工作流离线回归' : 'Bullet Hell offline regression'}</h3>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">{zh ? '20 个固定样本检查需求路由、Schema、安全门和有限修复。脚本化故障不代表真实 Unity 或真实模型质量。' : 'Twenty fixtures cover routing, schema, guardrails, and bounded repair. Scripted faults are not live Unity or real-model evidence.'}</p>
      </div>
      <button className="button-secondary" disabled={busy} onClick={run}>{busy ? <RefreshCw className="h-4 w-4 animate-spin"/> : <Activity className="h-4 w-4"/>}{zh ? '运行 20 个样本' : 'Run 20 fixtures'}</button>
    </div>
    {error && <p className="mt-3 text-sm text-red-200">{error}</p>}
    {result && <div className="mt-4">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{Object.entries(result.metrics).map(([key, value]) => <div key={key} className="border-t border-line pt-3">
        <p className="break-all text-xs text-slate-500">{key}</p>
        <p className="mt-1 text-xl font-semibold text-slate-100">{key.endsWith('_rate') ? `${(value * 100).toFixed(1)}%` : value}</p>
      </div>)}</div>
      <p className="mt-4 border-l-2 border-violet-400 pl-3 text-xs leading-5 text-slate-400">{result.disclaimer}</p>
    </div>}
  </section>;
}
