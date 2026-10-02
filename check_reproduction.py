"""Compare exact deterministic scientific records, not timing fingerprints."""
import argparse,json
from pathlib import Path
from bsci.evidence import strict_equal
FAMILIES=('random','overlay','resets','reduction','fixed','direct','periodic','phases','scaling')
OBSERVATIONAL={'producer_cpu','producer_wall','verifier_cpu','verifier_wall','process_peak_rss_kib'}
def main():
    p=argparse.ArgumentParser();p.add_argument('--reference',default='results/campaign');p.add_argument('--candidate',default='results/reproduced');p.add_argument('--out',default='results/reproduction-check.json');a=p.parse_args()
    result=[]
    for family in FAMILIES:
        paths=[Path(folder)/(family+'.jsonl') for folder in (a.reference,a.candidate)]
        rows=[[json.loads(line) for line in path.open()] for path in paths]
        if len(rows[0])!=len(rows[1]):raise AssertionError(f'{family}: row count differs')
        for i,(x,y) in enumerate(zip(*rows)):
            if family=='scaling':
                x={k:v for k,v in x.items() if k not in OBSERVATIONAL};y={k:v for k,v in y.items() if k not in OBSERVATIONAL}
            if not strict_equal(x,y):raise AssertionError(f'{family}: deterministic record {i} differs')
        result.append(dict(family=family,rows=len(rows[0]),deterministic_equal=True))
    out=dict(families=result,all_deterministic_records_equal=True,excluded_scaling_observation_fields=sorted(OBSERVATIONAL),scope='Exact record comparison; not an unbounded proof or independent external review')
    target=Path(a.out);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
if __name__=='__main__':main()
