"""Independent event-sorted scalar replay and base-derivation validation.

No imports from certify.py. Points are rebuilt independently; range premises use
Fenwick counts rather than the certifier's Horn range tree. This is implementation
independence, not external authorship, blind review, or a proof assistant.
"""
from bisect import bisect_left,bisect_right
from collections import defaultdict
from .model import Instance, _pairs

def replay(ins:Instance, optional, arrivals, include_trace=False):
    if len(arrivals)!=len(ins.messages):raise ValueError('wrong arrival count')
    reset=defaultdict(list);recv=defaultdict(list);send=defaultdict(list);queries=defaultdict(list)
    for v,t in ins.resets(optional):reset[t].append(v)
    for j,(m,d) in enumerate(zip(ins.messages,arrivals)):
        if type(d) is not int or not m.a<=d<=m.b:raise ValueError('arrival outside interval')
        send[m.s].append(j);recv[d].append(j)
    for j,(v,t) in enumerate(ins.queries):queries[t].append((j,v))
    event_times=sorted(set(reset)|set(recv)|set(send)|set(queries))
    values=[-1]*ins.n;payloads=[None]*len(ins.messages);answers=[-1]*len(ins.queries);trace=[]
    for t in event_times:
        for v in reset[t]:values[v]=-1
        values[0]=t
        for j in recv[t]:
            m=ins.messages[j]
            if payloads[j] is None:raise AssertionError('receive before send')
            values[m.v]=max(values[m.v],payloads[j])
        for j,v in queries[t]:answers[j]=values[v]
        for j in send[t]:payloads[j]=values[ins.messages[j].u]
        if include_trace:trace.append(dict(time=t,values=list(values),reset=reset[t],
                                         arrivals=recv[t],sends=send[t],queries=queries[t]))
    return dict(answer=max(answers),answers=answers,payloads=payloads,trace=trace)

class Fenwick:
    def __init__(self,n):self.data=[0]*(n+1)
    def add(self,i):
        i+=1
        while i<len(self.data):self.data[i]+=1;i+=i&-i
    def prefix(self,i):
        out=0
        while i:out+=self.data[i];i-=i&-i
        return out
    def count(self,l,r):return self.prefix(r)-self.prefix(l)

def capture_certificate(certificate: dict) -> dict:
    """Snapshot a finite optional pattern before coverage checks or replay reuse it.

    The JSON format uses arrays. The Python API also accepts finite iterables,
    which may be consumed only once. Copying the mapping avoids modifying the
    caller's certificate while the captured tuple binds all subsequent checks.
    """
    if not isinstance(certificate, dict):
        raise ValueError('certificate must be an object')
    return dict(certificate, optional=_pairs(certificate['optional'], 'certificate optional'))


def verify(ins:Instance,certificate:dict,*,expected_optional=None)->bool:
    """Check a packet, optionally binding its reset pattern to the caller's claim.

    Without expected_optional, the assertion checked is the pattern in the packet.
    The caller always supplies the independent instance (including the cutoff).
    """
    try:
        certificate=capture_certificate(certificate)
        optional=certificate['optional']; R=ins.resets(optional)
        if expected_optional is not None and R!=ins.resets(expected_optional):return False
        if type(certificate['safe']) is not bool:return False
        if not certificate['safe']:
            return replay(ins,optional,certificate['arrivals'])['answer']<ins.cutoff
        # Regenerate endpoints in a separate implementation, in one input pass.
        raw=[{0} for _ in range(ins.n)]
        for m in ins.messages:
            raw[m.u].add(m.s)
            raw[m.v].add(m.b)
        for v,t in ins.queries:raw[v].add(t)
        for v,t in (*ins.mandatory,*ins.candidates):raw[v].update((t-1,t))
        p=[sorted(times) for times in raw]
        counts=[Fenwick(len(x)) for x in p];marked=set();Q=set(ins.queries)
        rt=[[] for _ in range(ins.n)]
        for v,t in R:rt[v].append(t)
        for entry in certificate['steps']:
            if len(entry)<3:return False
            v,t,kind,*args=entry
            if type(v) is not int or type(t) is not int or not 0<=v<ins.n:return False
            pos=bisect_left(p[v],t)
            if pos==len(p[v]) or p[v][pos]!=t or (v,t) in marked:return False
            if kind=='query':
                if args or (v,t) not in Q:return False
            elif kind=='mem':
                if len(args)!=1 or type(args[0]) is not int or pos+1>=len(p[v]) or args[0]!=p[v][pos+1]:return False
                successor=args[0];j=bisect_right(rt[v],t)
                if (v,successor) not in marked or (j<len(rt[v]) and rt[v][j]<=successor):return False
            elif kind=='msg':
                if len(args)!=1 or type(args[0]) is not int or not 0<=args[0]<len(ins.messages):return False
                m=ins.messages[args[0]]
                if (m.u,m.s)!=(v,t):return False
                lo=bisect_left(p[m.v],m.a);hi=bisect_right(p[m.v],m.b)
                if lo>=hi or counts[m.v].count(lo,hi)!=hi-lo:return False
            else:return False
            marked.add((v,t));counts[v].add(pos)
        return any(v==0 and t>=ins.cutoff for v,t in marked)
    except (KeyError,TypeError,ValueError,IndexError):return False
