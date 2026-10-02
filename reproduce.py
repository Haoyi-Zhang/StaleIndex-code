#!/usr/bin/env python3
"""Run the complete fixed campaign sequentially, without third-party dependencies."""
import argparse,json,subprocess,sys
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',default='results/reproduced');p.add_argument('--families',nargs='+',default=['random','overlay','resets','reduction','fixed','direct','periodic','phases','scaling']);args=p.parse_args()
    root=Path(__file__).resolve().parent;out=Path(args.out)
    if not out.is_absolute():out=root/out
    out.mkdir(parents=True,exist_ok=True)
    subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=root,check=True,timeout=120)
    for family in args.families:
        subprocess.run([sys.executable,'-m','bsci.campaign',family,'--out',str(out)],cwd=root,check=True,timeout=1800)
    resources=[json.loads((out/(f+'-resources.json')).read_text()) for f in args.families]
    summary=dict(families=resources,total_cpu_seconds=sum(x['cpu_seconds'] for x in resources),
                 max_child_peak_rss_kib=max(x['peak_rss_kib'] for x in resources),workers=1)
    (out/'campaign-resources.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
