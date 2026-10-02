"""Standard integral augmenting-path min-cut baseline for singleton arrivals."""
from collections import deque
from bisect import bisect_right
from .model import Instance
from .certify import endpoint_sets

def minimum_resets(ins:Instance):
    if any(m.a!=m.b for m in ins.messages):raise ValueError('min-cut requires fixed arrivals')
    P=endpoint_sets(ins);states=[(v,t) for v,p in enumerate(P) for t in p]
    ids={p:i for i,p in enumerate(states)};source=len(states);sink=source+1
    graph=[[] for _ in range(sink+1)]
    def add(u,v,cap):
        a=[v,cap,len(graph[v])];b=[u,0,len(graph[u])]
        graph[u].append(a);graph[v].append(b)
    M=len(ins.candidates)+1;C=set(ins.candidates);F=set(ins.mandatory);reset_edges=[]
    for v,p in enumerate(P):
        for a,b in zip(p,p[1:]):
            if (v,b) in F:continue
            cap=1 if (v,b) in C else M
            add(ids[v,a],ids[v,b],cap)
            if cap==1 and (v,b) in C:reset_edges.append((ids[v,a],ids[v,b],(v,b)))
    for m in ins.messages:add(ids[m.u,m.s],ids[m.v,m.a],M)
    for t in P[0]:
        if t>=ins.cutoff:add(source,ids[0,t],M)
    for v,t in ins.queries:add(ids[v,t],sink,M)
    value=0
    while value<M:
        parent=[None]*len(graph);parent[source]=(-1,-1);todo=deque([source])
        while todo and parent[sink] is None:
            u=todo.popleft()
            for j,(v,cap,rev) in enumerate(graph[u]):
                if cap and parent[v] is None:parent[v]=(u,j);todo.append(v)
        if parent[sink] is None:break
        amount=M-value;v=sink
        while v!=source:
            u,j=parent[v];amount=min(amount,graph[u][j][1]);v=u
        v=sink
        while v!=source:
            u,j=parent[v];edge=graph[u][j];edge[1]-=amount;graph[v][edge[2]][1]+=amount;v=u
        value+=amount
    if value>=M:return dict(count=None,optional=[])
    reachable={source};todo=[source]
    for u in todo:
        for v,cap,rev in graph[u]:
            if cap and v not in reachable:reachable.add(v);todo.append(v)
    resets=[r for a,b,r in reset_edges if a in reachable and b not in reachable]
    if len(resets)!=value:raise AssertionError('cut contains an unremovable edge')
    return dict(count=value,optional=[list(r) for r in sorted(resets)])
