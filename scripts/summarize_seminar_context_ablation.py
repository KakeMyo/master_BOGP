"""Summarize paired state-feature ablation, including reproducibility audits."""
from pathlib import Path
import csv
import json
import os
os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/bogp_mpl_cache")
import numpy as np
from scipy.stats import t, ttest_rel, wilcoxon
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/seminar_context_ablation/20261001"
OLD = ROOT / "outputs/main_bo_current_friedman/sr_alpha_friedman/main_bo_current_friedman_seed100_eval60_20260603/runs/bogp_current"


def main():
    runs = {m: [json.loads((OUT / m / f"seed_{s}.json").read_text()) for s in range(100)]
            for m in ("contextual", "noncontextual")}
    for s, (a, b) in enumerate(zip(runs['contextual'], runs['noncontextual'])):
        old = [json.loads(line) for line in (OLD / f"seed_{s}/generation_metrics.jsonl").read_text().splitlines()]
        assert a['generations'] == old, f"original mismatch seed {s}"
        assert a['records'][:6] == b['records'][:6], f"warmup mismatch seed {s}"
        assert a['evaluations'] == b['evaluations'] == 1872
        assert len(a['generations']) == len(b['generations']) == 79
    metrics = {}
    rows = []
    for method, items in runs.items():
        for item in items:
            gs = item['generations']; rs = item['records']; post = rs[6:]
            row = {'method': method, 'seed': item['seed'],
                   'final_hv': gs[-1]['archive_hypervolume'],
                   'warmup_hv': gs[18]['archive_hypervolume'],
                   'gain': gs[-1]['archive_hypervolume']-gs[18]['archive_hypervolume'],
                   'auc': float(np.trapz([g['archive_hypervolume'] for g in gs[18:]], dx=1)/60),
                   'diversity': gs[-1]['population_diversity'],
                   'tree_size': gs[-1]['mean_tree_size'],
                   'steps': len(rs),
                   'pc': float(np.mean([r['control']['crossover_rate'] for r in post])),
                   'pm': float(np.mean([r['control']['mutation_rate'] for r in post]))}
            rows.append(row)
        subset = [r for r in rows if r['method'] == method]
        metrics[method] = {key: {'mean': float(np.mean([r[key] for r in subset])),
                                'std': float(np.std([r[key] for r in subset])),
                                'median': float(np.median([r[key] for r in subset]))}
                           for key in subset[0] if key not in ('method', 'seed')}
        metrics[method]['k_counts_post'] = {str(k): sum(r['control']['update_period']==k for item in items for r in item['records'][6:]) for k in (1,3,5)}
        metrics[method]['reward_post'] = {key: float(np.mean([r['reward'][key] for item in items for r in item['records'][6:]])) for key in items[0]['records'][0]['reward']}
    with (OUT/'summary_by_seed.csv').open('w') as f:
        writer=csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    paired = {}
    for key in ('final_hv','gain','auc','diversity','steps','tree_size'):
        a = np.array([r[key] for r in rows if r['method']=='contextual'])
        b = np.array([r[key] for r in rows if r['method']=='noncontextual'])
        d = a-b
        margin = t.ppf(.975,99)*np.std(d,ddof=1)/10
        paired[key] = {'mean': float(d.mean()), 'ci95': [float(d.mean()-margin),float(d.mean()+margin)],
                       'win': int(sum(d>1e-12)), 'tie': int(sum(abs(d)<=1e-12)), 'loss': int(sum(d < -1e-12)),
                       'paired_t_p':float(ttest_rel(a,b).pvalue), 'wilcoxon_p':float(wilcoxon(d).pvalue)}
    (OUT/'analysis.json').write_text(json.dumps({'metrics':metrics,'paired':paired,'audit':'100 seeds reproduce original histories exactly; all warmups match; 1872 evaluations/run'},indent=2))
    fig, axes = plt.subplots(1,3,figsize=(15,4.3))
    for method,color in (('contextual','#d95f5f'),('noncontextual','#377eb8')):
        values=np.array([[g['archive_hypervolume'] for g in x['generations']] for x in runs[method]])
        axes[0].plot(range(79),values.mean(0),label=method,color=color)
        axes[0].fill_between(range(79),values.mean(0)-values.std(0),values.mean(0)+values.std(0),color=color,alpha=.12)
    axes[0].axvline(18,color='gray',linestyle='--'); axes[0].set(xlabel='Generation',ylabel='Archive HV',title='Mean +/- SD'); axes[0].legend()
    a=[r['final_hv'] for r in rows if r['method']=='contextual']; b=[r['final_hv'] for r in rows if r['method']=='noncontextual']
    axes[1].scatter(b,a,s=18,alpha=.7); limits=[min(a+b)-.005,max(a+b)+.005]; axes[1].plot(limits,limits,color='gray',linestyle='--'); axes[1].set(xlabel='Noncontextual final HV',ylabel='Contextual final HV',title='Paired seeds')
    axes[2].hist(np.array(a)-np.array(b),bins=20,color='#777777'); axes[2].axvline(0,color='black'); axes[2].set(xlabel='Contextual - noncontextual final HV',ylabel='Seed count',title='Paired differences')
    fig.tight_layout(); fig.savefig(OUT/'comparison.png',dpi=180)
    print(json.dumps({'metrics':metrics,'paired':paired},indent=2))


if __name__ == '__main__':
    main()
