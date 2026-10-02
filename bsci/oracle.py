"""Literal full-slot simulation and exhaustive arrival oracle for small cases.

It deliberately does not import the event-sorted simulator or certificate code.
Do not use a huge binary-encoded horizon here: this is a bounded test oracle.
"""
from itertools import product
from .model import Instance, _pairs

def scalar(ins:Instance, optional, arrivals):
    if ins.horizon>10000:raise ValueError('full-slot oracle horizon exceeds test limit')
    R=set(ins.resets(optional));g=[-1]*ins.n;pack=[None]*len(ins.messages);out=[]
    for t in range(ins.horizon+1):
        for v in range(1,ins.n):
            if (v,t) in R:g[v]=-1
        g[0]=t
        for j,m in enumerate(ins.messages):
            if arrivals[j]==t:g[m.v]=max(g[m.v],pack[j])
        for v,q in ins.queries:
            if q==t:out.append(g[v])
        for j,m in enumerate(ins.messages):
            if m.s==t:pack[j]=g[m.u]
    return max(out)

def exhaustive(ins:Instance,optional=(),limit=2000000):
    # Every enumerated arrival assignment must use the same captured pattern.
    optional = _pairs(optional, 'optional resets')
    ins.resets(optional)
    count=1
    for m in ins.messages:count*=m.b-m.a+1
    if count>limit:raise ValueError(f'oracle would enumerate {count} executions')
    worst=ins.horizon+1;witness=None
    for a in product(*(range(m.a,m.b+1) for m in ins.messages)):
        value=scalar(ins,optional,a)
        if value<worst:worst=value;witness=a
    return dict(safe=worst>=ins.cutoff,answer=worst,arrivals=witness,executions=count)

def expanded_closure(ins:Instance,optional=()):
    """Naive full-state fixpoint, not a range-tree or endpoint algorithm."""
    if ins.horizon>10000:raise ValueError('expanded oracle horizon exceeds test limit')
    R=set(ins.resets(optional));M=set(ins.queries)
    while True:
        old=len(M)
        for v in range(ins.n):
            for t in range(1,ins.horizon+1):
                if (v,t) in M and (v,t) not in R:M.add((v,t-1))
        for m in ins.messages:
            if all((m.v,t) in M for t in range(m.a,m.b+1)):M.add((m.u,m.s))
        if len(M)==old:break
    return any(v==0 and t>=ins.cutoff for v,t in M)
