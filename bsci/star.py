"""Exact direct-source replica erasure packing, plus common-period phase bounds."""
from itertools import combinations_with_replacement
from .model import Instance,Message


def _integer(name, value, minimum=1):
    """Keep the mathematical integer domain; bool and floats are not times."""
    if type(value) is not int or value < minimum:
        raise ValueError(f'{name} must be an integer >= {minimum}')
    return value


def _schedule(P, D, phases):
    """Validate and capture the phase iterable once, before any repeated use."""
    _integer('P', P)
    _integer('D', D)
    if isinstance(phases, (str, bytes, dict)):
        raise ValueError('phases must be a nonempty iterable of integer phases')
    try:
        phases = tuple(phases)
    except TypeError as exc:
        raise ValueError('phases must be an iterable') from exc
    if not phases or any(type(p) is not int or not 0 <= p < P for p in phases):
        raise ValueError('each phase must be an integer in [0,P)')
    return phases

def packing(ins:Instance,b:int,W:int):
    if type(b) is not int or type(W) is not int or b<1 or W<1:raise ValueError('b,W must be positive integers')
    if ins.mandatory:raise ValueError('packing model has no mandatory resets')
    if any(m.u!=0 for m in ins.messages):raise ValueError('not a direct-source star')
    q=ins.queries[0][1]
    if set(ins.queries)!={(v,q) for v in range(1,ins.n)}:raise ValueError('query must read every replica at one time')
    if len(ins.candidates)!=(ins.n-1)*q or any(t>q for v,t in ins.candidates):
        raise ValueError('packing requires every replica/time reset candidate through the query')
    latest={}
    for m in ins.messages:
        if m.s>=ins.cutoff and m.b<=q:
            latest[m.v]=max(latest.get(m.v,0),m.a+1)
    releases=[]
    for v in range(1,ins.n):
        if v in latest:releases.append((latest[v],v))
    releases.sort(reverse=True)
    slots=[q-W*(j//b) for j in range(len(releases))]
    violating=[j for j,((r,v),t) in enumerate(zip(releases,slots)) if r>t]
    if violating:return dict(safe=True,releases=releases,violation=violating[0]+1)
    resets=[(v,t) for (r,v),t in zip(releases,slots)]
    arrivals=[]
    for m in ins.messages:
        if m.s>=ins.cutoff and m.b<=q:arrivals.append(m.a)
        else:arrivals.append(m.b)
    return dict(safe=False,releases=releases,optional=resets,arrivals=arrivals)

def phase_bounds(P:int,D:int,b:int,W:int,phases):
    phases = _schedule(P, D, phases)
    _integer('b', b)
    _integer('W', W)
    rows=[]
    for q in range(P):
        ages=sorted(D+(q-D-p)%P for p in phases)
        qualifying=[age for j,age in enumerate(ages) if age<=1+W*(j//b)]
        rows.append(min(qualifying) if qualifying else None)
    return dict(bound=max(rows) if all(x is not None for x in rows) else None,
                phase_bounds=rows)

def optimize(P,D,b,W,r):
    _schedule(P, D, (0,))
    _integer('b', b)
    _integer('W', W)
    _integer('r', r)
    best=None;optimal=[];count=0;finite=0
    # Rotation preserves the all-query-phase bound; replica names are irrelevant.
    for tail in combinations_with_replacement(range(P),r-1):
        phases=(0,*tail);count+=1;bound=phase_bounds(P,D,b,W,phases)['bound']
        if bound is None:continue
        finite+=1
        if best is None or bound<best:best=bound;optimal=[phases]
        elif bound==best:optimal.append(phases)
    return dict(bound=best,phases=optimal[0] if optimal else None,
                ties=len(optimal),phase_multisets=count,finite_multisets=finite)

def window(P,D,phases,B,qphase):
    """Cutoff-relative star window. Late arrivals are retained through B+D."""
    phases = _schedule(P, D, phases)
    _integer('B', B, minimum=0)
    _integer('qphase', qphase, minimum=0)
    if qphase >= P:
        raise ValueError('qphase must be in [0,P)')
    startphase=(qphase-B)%P;messages=[]
    for s in range(B):
        for v,theta in enumerate(phases,1):
            if (startphase+s)%P==theta:messages.append(Message(0,v,s,s+1,s+D))
    r=len(phases)
    return Instance(r+1,B+D,0,tuple(messages),tuple((v,B) for v in range(1,r+1)),(),
                    tuple((v,t) for v in range(1,r+1) for t in range(1,B+1)))
