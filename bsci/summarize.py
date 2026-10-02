"""Derive manuscript tables and PGFPlots inputs from preserved raw JSONL rows."""
import argparse,csv,json,statistics
from pathlib import Path

def load(path):
    with path.open() as f:return [json.loads(line) for line in f]

def main():
    p=argparse.ArgumentParser();p.add_argument('--results',default='results/campaign');p.add_argument('--out',default='results/derived');a=p.parse_args()
    src=Path(a.results);out=Path(a.out);out.mkdir(parents=True,exist_ok=True);summary={};total=0
    for name in ('random','overlay','resets','reduction','fixed','direct','periodic'):
        rows=load(src/(name+'.jsonl'));patterns=[]
        if name in ('random','overlay'):patterns=rows
        else:
            for r in rows:patterns.extend(r['patterns'])
        oracles=[r['oracle'] for r in patterns if 'oracle' in r]
        count=sum(r['executions'] for r in oracles);total+=count
        summary[name]=dict(instances=len(rows),patterns=len(patterns),oracle_patterns=len(oracles),
                           arrival_executions=count,oracle_safe=sum(r['safe'] for r in oracles))
        if name in ('random','overlay'):summary[name]['safe']=sum(r['certificate']['safe'] for r in rows)
        elif name in ('resets','fixed'):summary[name]['universally_safe']=sum(r['minimum'] is None for r in rows)
        elif name=='direct':summary[name]['universally_safe']=sum(r['packing']['safe'] for r in rows)
        elif name=='periodic':summary[name]['universally_safe']=sum(r['safe'] for r in rows)
    phases=load(src/'phases.jsonl');both=sum(r['optimal']['bound'] is not None and r['synchronous']['bound'] is not None for r in phases)
    summary['phases']=dict(settings=len(phases),both_finite=both,
        strict_finite_improvement=sum(r['optimal']['bound'] is not None and r['synchronous']['bound'] is not None and r['optimal']['bound']<r['synchronous']['bound'] for r in phases),
        synchronous_infinite_optimized_finite=sum(r['optimal']['bound'] is not None and r['synchronous']['bound'] is None for r in phases),
        both_infinite=sum(r['optimal']['bound'] is None for r in phases),
        candidate_multisets=sum(r['optimal']['phase_multisets'] for r in phases))
    rows=load(src/'scaling.jsonl');scaling=[]
    for key in dict.fromkeys((r['axis'],r['m'],r['scale']) for r in rows):
        group=[r for r in rows if (r['axis'],r['m'],r['scale'])==key];r=group[0]
        assert len(group)==5
        stats=[x['stats'] for x in group];assert all(x==stats[0] for x in stats)
        row=dict(axis=key[0],m=key[1],scale=key[2],horizon=r['horizon'],**r['stats'])
        for metric in ('producer_cpu','verifier_cpu'):
            values=[x[metric] for x in group];row[metric+'_median_ms']=1000*statistics.median(values);row[metric+'_min_ms']=1000*min(values);row[metric+'_max_ms']=1000*max(values)
        scaling.append(row)
    def write(name,rows):
        with (out/name).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    write('scaling.csv',scaling)
    for axis in ('events','time'):
        selected=[dict(row) for row in scaling if row['axis']==axis]
        for row in selected:
            for metric in ('producer_cpu','verifier_cpu'):
                row[metric+'_error_minus']=row[metric+'_median_ms']-row[metric+'_min_ms']
                row[metric+'_error_plus']=row[metric+'_max_ms']-row[metric+'_median_ms']
        write('scaling-'+axis+'.csv',selected)
    phase_rows=[]
    for r in phases:
        phase_rows.append(dict(r=r['r'],P=r['P'],D=r['D'],b=r['b'],W=r['W'],synchronous='inf' if r['synchronous']['bound'] is None else r['synchronous']['bound'],
                              optimized='inf' if r['optimal']['bound'] is None else r['optimal']['bound'],phases=str(r['optimal']['phases']),ties=r['optimal']['ties']))
    write('phase-design.csv',phase_rows)
    # A fixed illustrative slice, not selected to maximize a reported improvement.
    write('phase-slice.csv',[r for r in phase_rows if r['r']==3 and r['P']==4 and r['D']==2 and r['b']==1])
    resources=[json.loads(p.read_text()) for p in sorted(src.glob('*-resources.json')) if p.name!='campaign-resources.json']
    summary['resources']=dict(total_cpu_seconds=sum(r['cpu_seconds'] for r in resources),peak_rss_kib=max(r['peak_rss_kib'] for r in resources),workers=1)
    summary['full_oracle_arrival_executions']=total
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
