"""Range-AND stale closure and compact derivation production.

This module does not call the replay or certificate-verification implementation.
"""
from bisect import bisect_left, bisect_right
from collections import deque
from .model import Instance, _pairs

def endpoint_sets(ins: Instance):
    points=[{0} for _ in range(ins.n)]
    for m in ins.messages:
        points[m.u].add(m.s); points[m.v].add(m.b)
    for v,t in ins.queries: points[v].add(t)
    for v,t in (*ins.mandatory,*ins.candidates): points[v].update((t-1,t))
    return [sorted(p) for p in points]

def certify(ins: Instance, optional=()) -> dict:
    optional=_pairs(optional, 'optional resets')
    resets=ins.resets(optional)
    reset_times=[[] for _ in range(ins.n)]
    for v,t in resets: reset_times[v].append(t)
    P=endpoint_sets(ins)
    states=[(v,t) for v,p in enumerate(P) for t in p]
    index={p:i for i,p in enumerate(states)}
    K=len(states)
    # Every Horn rule has antecedent ids, one consequent id, and a base reason.
    rules=[]; next_id=K; trees=[]
    def build(v,lo,hi):
        nonlocal next_id
        if hi-lo==1:
            return (lo,hi,index[v,P[v][lo]],None,None)
        mid=(lo+hi)//2; left=build(v,lo,mid); right=build(v,mid,hi)
        node=next_id;next_id+=1
        rules.append(((left[2],right[2]),node,None))
        return (lo,hi,node,left,right)
    for v in range(ins.n): trees.append(build(v,0,len(P[v])))
    def cover(tree,lo,hi,out):
        l,r,node,left,right=tree
        if lo<=l and r<=hi:out.append(node);return
        if left is not None and lo<left[1] and left[0]<hi:cover(left,lo,hi,out)
        if right is not None and lo<right[1] and right[0]<hi:cover(right,lo,hi,out)
    for v,p in enumerate(P):
        rt=reset_times[v]
        for a,b in zip(p,p[1:]):
            j=bisect_right(rt,a)
            if j==len(rt) or rt[j]>b:
                rules.append(((index[v,b],),index[v,a],['mem',b]))
    for j,m in enumerate(ins.messages):
        lo=bisect_left(P[m.v],m.a);hi=bisect_right(P[m.v],m.b)
        assert lo<hi
        heads=[]; cover(trees[m.v],lo,hi,heads)
        rules.append((tuple(heads),index[m.u,m.s],['msg',j]))
    uses=[[] for _ in range(next_id)]; remaining=[]
    for j,(heads,tail,reason) in enumerate(rules):
        remaining.append(len(heads))
        for h in heads: uses[h].append(j)
    marked=bytearray(next_id); queue=deque();steps=[]
    def mark(i,why):
        if not marked[i]:
            marked[i]=1; queue.append(i)
            if i<K:steps.append([*states[i],*why])
    for v,t in sorted(set(ins.queries)):mark(index[v,t],['query'])
    while queue:
        h=queue.popleft()
        for j in uses[h]:
            remaining[j]-=1
            if remaining[j]==0:
                _,tail,why=rules[j]
                mark(tail,why)
    fresh=[i for i,(v,t) in enumerate(states) if v==0 and t>=ins.cutoff and marked[i]]
    stats=dict(points=K,auxiliary=next_id-K,rules=len(rules),
               incidences=sum(len(r[0]) for r in rules),marked_points=len(steps))
    if fresh:
        # A prefix ending at a fresh source is enough to refute all-query staleness.
        end=next(j for j,s in enumerate(steps) if s[0]==0 and s[1]>=ins.cutoff)
        return dict(safe=True,optional=[list(x) for x in sorted(optional)],
                    steps=steps[:end+1],stats=stats)
    unmarked=[[t for t in p if not marked[index[v,t]]] for v,p in enumerate(P)]
    arrivals=[]
    for m in ins.messages:
        if marked[index[m.u,m.s]]: arrivals.append(m.b)
        else:
            pos=bisect_left(unmarked[m.v],m.a)
            if pos==len(unmarked[m.v]) or unmarked[m.v][pos]>m.b:
                raise AssertionError('closure failed its message premise')
            arrivals.append(unmarked[m.v][pos])
    return dict(safe=False,optional=[list(x) for x in sorted(optional)],
                arrivals=arrivals,stats=stats)
