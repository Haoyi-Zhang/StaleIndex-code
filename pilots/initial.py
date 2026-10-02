"""Original one-worker expanded-closure pilot; fixed seed and selection."""
import argparse,itertools,random,resource,time,json
from pathlib import Path
from reference import close,sim,gadget
parser=argparse.ArgumentParser();parser.add_argument('--out',default='results/pilots-reproduced/initial.json');args=parser.parse_args()
output=Path(args.out);output.parent.mkdir(parents=True,exist_ok=True)
start=time.process_time(); wall=time.perf_counter();r=random.Random(5741)
counts={'random_instances':0,'delay_executions':0,'gadget_subsets':0,'mismatches':0}
for case in range(160):
    n=4;H=5;msg=[]
    for j in range(5):
      u=r.randrange(n);v=r.randrange(1,n);s=r.randrange(H)
      A=tuple(range(s+1,min(s+3,H)+1));msg.append((u,v,s,A))
    resets=[(v,t) for v in range(1,n) for t in range(1,H+1) if r.random()<.12]
    targets=[(n-1,H)];cutoff=r.randrange(0,H)
    a,w=close(n,H,msg,resets,targets,cutoff)
    vals=[sim(n,H,msg,resets,targets,d) for d in itertools.product(*(m[3] for m in msg))]
    b=min(vals)>=cutoff
    assert a==b,(case,msg,resets,a,b)
    if not a:assert sim(n,H,msg,resets,targets,w)<cutoff
    counts['random_instances']+=1;counts['delay_executions']+=len(vals)
for n in range(1,5):
  poss=list(itertools.combinations(range(n),2))
  for mask in range(1<<len(poss)):
    edges=[e for i,e in enumerate(poss) if mask>>i&1]
    N,H,msg,F,Q=gadget(n,edges)
    for bits in range(1<<n):
      X={v for v in range(n) if bits>>v&1}
      cover=all(u in X or v in X for u,v in edges)
      S=[(v+1,4) for v in X]
      safe,w=close(N,H,msg,F+S,Q,0)
      assert (not safe)==cover,(n,edges,X,safe)
      if not safe:assert sim(N,H,msg,F+S,Q,w)<0
      counts['gadget_subsets']+=1
# Latest arrival is NOT a sound worst-case rule after a reset.
msg=[(0,1,0,(1,2))]; F=[(1,2)]; Q=[(1,2)]
a,w=close(2,2,msg,F,Q,0)
assert not a and sim(2,2,msg,F,Q,[1])==-1 and sim(2,2,msg,F,Q,[2])==0
out={**counts,'cpu_seconds':time.process_time()-start,'wall_seconds':time.perf_counter()-wall,
'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'workers':1,
'seed':5741,'negative_control':{'early_value':-1,'late_value':0,'arrival_early':1,'arrival_late':2,'reset_time':2},
'projection':'Full oracle campaign 3200 small schedules; all 1099 simple graphs on 1..5 vertices and all 33866 vertex subsets; one worker, conservative <300 CPU seconds estimate from pilot.'}
output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
