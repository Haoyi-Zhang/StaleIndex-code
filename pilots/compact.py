"""Original compression and packing pilot; fixed seed and selection."""
import argparse,itertools,random,resource,time,json
from pathlib import Path
from reference import sim,close as expanded
parser=argparse.ArgumentParser();parser.add_argument('--out',default='results/pilots-reproduced/compact.json');args=parser.parse_args()
output=Path(args.out);output.parent.mkdir(parents=True,exist_ok=True)
def compact(n,H,msg,R,Q,c,eligible=()):
    points=[{0} for _ in range(n)]
    for u,v,s,A in msg: points[u].add(s);points[v].add(max(A))
    for v,t in Q: points[v].add(t)
    for v,t in set(R)|set(eligible):
        points[v].add(t)
        if t>0:points[v].add(t-1)
    points=[sorted(p) for p in points]
    index={}; states=[]
    for v in range(n):
      for t in points[v]:index[v,t]=len(states);states.append((v,t))
    rules=[]; R=set(R)
    for v,P in enumerate(points):
      for a,b in zip(P,P[1:]):
        if not any((v,t) in R for t in range(a+1,b+1)):
          rules.append(((index[v,b],),index[v,a]))
    for u,v,s,A in msg:
      rules.append((tuple(index[v,a] for a in points[v] if min(A)<=a<=max(A)),index[u,s]))
    M={index[v,t] for v,t in Q}
    while True:
      old=len(M)
      for tail,head in rules:
        if all(t in M for t in tail): M.add(head)
      if len(M)==old:break
    safe=any(v==0 and t>=c for i,(v,t) in enumerate(states) if i in M)
    witness=[]
    for u,v,s,A in msg:
      a=[a for a in points[v] if min(A)<=a<=max(A) and index[v,a] not in M]
      witness.append(min(a) if index[u,s] not in M and a else max(A))
    return safe,witness,len(states)

def packing(n,msg,q,c,b,W):
    release=[]
    for v in range(1,n):
      a=[min(A)+1 for u,w,s,A in msg if w==v and s>=c and max(A)<=q]
      if a:release.append(max(a))
    release.sort(reverse=True)
    safe=any(r>q-W*(j//b) for j,r in enumerate(release))
    return safe

def legal(R,b,W):
    ts=sorted(t for v,t in R)
    return all(ts[i+b]-ts[i]>=W for i in range(len(ts)-b))

start=time.process_time();wall=time.perf_counter();rng=random.Random(86231)
counts={'compression_cases':0,'oracle_executions':0,'star_cases':0,'star_reset_sets':0,'star_executions':0,'mismatches':0}
for case in range(240):
 n=4;H=6;msg=[]
 for j in range(6):
  u=rng.randrange(n);v=rng.randrange(1,n);s=rng.randrange(H)
  a=rng.randrange(s+1,H+1);z=rng.randrange(a,H+1)
  msg.append((u,v,s,tuple(range(a,z+1))))
 R=[(v,t) for v in range(1,n) for t in range(1,H+1) if rng.random()<.12]
 Q=[(n-1,H)];c=rng.randrange(H+1)
 a,w,K=compact(n,H,msg,R,Q,c);e,_=expanded(n,H,msg,R,Q,c)
 assert a==e
 allvals=[sim(n,H,msg,R,Q,d) for d in itertools.product(*(m[3] for m in msg))]
 assert a==(min(allvals)>=c)
 if not a:assert sim(n,H,msg,R,Q,w)<c
 counts['compression_cases']+=1;counts['oracle_executions']+=len(allvals)
for case in range(36):
 n=3+(case%3==0);q=4;b=1+(case%4==0);W=2+case%3;c=case%4
 msg=[]
 for j in range(4):
  v=rng.randrange(1,n);s=rng.randrange(q)
  msg.append((0,v,s,tuple(range(s+1,min(q+2,s+2)+1))))
 H=max(q,max(max(m[3]) for m in msg));Q=[(v,q) for v in range(1,n)]
 C=[(v,t) for v in range(1,n) for t in range(1,q+1)]
 safe=True
 for bits in range(1<<len(C)):
  R=[x for i,x in enumerate(C) if bits>>i&1]
  if not legal(R,b,W):continue
  counts['star_reset_sets']+=1
  for d in itertools.product(*(m[3] for m in msg)):
   val=sim(n,H,msg,R,Q,d);counts['star_executions']+=1
   if val<c:safe=False
 assert safe==packing(n,msg,q,c,b,W),(case,msg,b,W,c,safe)
 counts['star_cases']+=1
out={**counts,'cpu_seconds':time.process_time()-start,'wall_seconds':time.perf_counter()-wall,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'workers':1,'seed':86231}
output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
