"""One-worker discriminating pilot; self-contained synthetic schedules."""
import itertools, random, resource, time, json
from collections import deque
from pathlib import Path

def close(n,H,msg,resets,targets,cutoff):
    N=n*(H+1); resets=set(resets); incoming=[[] for _ in range(N)]
    tails=[]; heads=[]
    for v in range(n):
      for t in range(1,H+1):
        if (v,t) not in resets:
          tails.append((v*(H+1)+t,)); heads.append(v*(H+1)+t-1)
    for u,v,s,arr in msg:
      tails.append(tuple(v*(H+1)+t for t in arr)); heads.append(u*(H+1)+s)
    count=list(map(len,tails))
    for i,tail in enumerate(tails):
      for x in tail: incoming[x].append(i)
    marked=set(v*(H+1)+t for v,t in targets); q=deque(marked)
    while q:
      x=q.popleft()
      for i in incoming[x]:
        count[i]-=1
        if count[i]==0 and heads[i] not in marked:
          marked.add(heads[i]);q.append(heads[i])
    safe=any(t in marked for t in range(max(0,cutoff),H+1))
    delays=[]
    for u,v,s,arr in msg:
      opts=[t for t in arr if v*(H+1)+t not in marked]
      delays.append(min(opts) if u*(H+1)+s not in marked and opts else min(arr))
    return safe,delays

def sim(n,H,msg,resets,targets,arr):
    value=[-1]*n; arrival=[[] for _ in range(H+1)]; res=set(resets)
    result={}; sends=[[] for _ in range(H+1)]
    for i,m in enumerate(msg): sends[m[2]].append(i)
    for t in range(H+1):
      for v in range(n):
        if (v,t) in res:value[v]=-1
      value[0]=t
      for v,p in arrival[t]:value[v]=max(value[v],p)
      for v,q in targets:
        if q==t:result[(v,q)]=value[v]
      for i in sends[t]:
        u,v,s,A=msg[i];arrival[arr[i]].append((v,value[u]))
    return max(result.values())

def gadget(n,edges):
    H=6; z=1+n+len(edges); msg=[]; fixed=[]
    for i,(u,v) in enumerate(edges):
      x=1+n+i
      msg += [(0,x,0,(1,2)),(x,1+u,1,(3,)),(x,1+v,2,(3,))]
      fixed.append((x,2))
    for v in range(n):msg.append((1+v,z,5,(6,)))
    return z+1,H,msg,fixed,[(z,6)]

