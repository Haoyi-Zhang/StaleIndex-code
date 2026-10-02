"""Predeclared finite falsification families. Standard library; one worker.

Write deterministic case rows and a separate resource observation. A mismatch raises
immediately. Families are individually repeatable; graph subsets are bounded chunks.
"""
import argparse, itertools, json, os, random, resource, time
from pathlib import Path
from .model import Instance, Message
from .certify import certify
from .replay import verify, replay
from .oracle import exhaustive, expanded_closure, scalar
from .families import all_sets, legal, universal, verify_universal
from .flow import minimum_resets
from .star import packing, phase_bounds, optimize


def random_instance(rng, n=None,H=None,m=None,single=False,Cmax=4,Fmax=3):
    n=n or rng.randint(2,6); H=H or rng.randint(3,8)
    m=rng.randint(0,7) if m is None else m
    messages=[]
    for _ in range(m):
        u=rng.randrange(n);v=rng.randrange(1,n);s=rng.randrange(H)
        a=rng.randint(s+1,H);b=a if single else min(H,a+rng.randrange(2))
        messages.append(Message(u,v,s,a,b))
    Q=tuple((rng.randrange(n),rng.randrange(H+1)) for _ in range(rng.randint(1,3)))
    pool=[(v,t) for v in range(1,n) for t in range(1,H+1)];rng.shuffle(pool)
    nf=min(len(pool),rng.randint(0,Fmax));F=tuple(sorted(pool[:nf]));pool=pool[nf:]
    nc=min(len(pool),rng.randint(0,Cmax));C=tuple(sorted(pool[:nc]))
    return Instance(n,H,rng.randrange(H+1),tuple(messages),Q,F,C)


def check(ins,S=(),full=True):
    cert=certify(ins,S)
    assert verify(ins,cert), ('certificate rejected',ins.to_dict(),S,cert)
    assert cert['safe']==expanded_closure(ins,S), ('expanded closure disagreement',ins.to_dict(),S)
    out=dict(instance=ins.to_dict(),optional=list(S),certificate=cert)
    if full:
        oracle=exhaustive(ins,S)
        assert cert['safe']==oracle['safe'],('arrival oracle disagreement',out,oracle)
        out['oracle']=oracle
    return out


def random_family():
    rng=random.Random(910731)
    for i in range(3200):
        ins=random_instance(rng);S=tuple(e for e in ins.candidates if rng.randrange(2))
        yield dict(case=i,**check(ins,S))


def overlay_family():
    contacts=(Message(0,1,0,1,2),Message(0,2,0,1,2),Message(1,2,1,2,3),Message(2,1,1,2,3))
    for mask in range(16):
        for rmask in range(4):
            F=tuple((v,2) for v in (1,2) if rmask>>(v-1)&1)
            for c in range(4):
                ins=Instance(3,3,c,tuple(m for j,m in enumerate(contacts) if mask>>j&1),((1,3),(2,3)),F)
                yield dict(contact_mask=mask,reset_mask=rmask,**check(ins))


def reset_family():
    rng=random.Random(910733)
    for i in range(96):
        ins=random_instance(rng,n=rng.randint(2,4),H=rng.randint(4,6),m=rng.randint(2,5),Cmax=6,Fmax=2)
        rule=dict(kind='cardinality',k=rng.randint(1,3)) if i%2==0 else dict(kind='rolling',b=rng.randint(1,2),W=rng.randint(2,3))
        patterns=[];min_count=None
        for S in all_sets(ins.candidates,rule):
            row=check(ins,S);patterns.append(dict(optional=list(S),safe=row['certificate']['safe'],oracle=row['oracle']))
            if not row['oracle']['safe'] and min_count is None:min_count=len(S)
        packet=universal(ins,rule)
        assert verify_universal(ins,packet,True)
        assert packet['safe']==(min_count is None)
        if min_count is not None:assert packet['minimal_optional_count']==min_count
        yield dict(case=i,instance=ins.to_dict(),rule=rule,patterns=patterns,minimum=min_count,packet=packet)


def gadget(n,edges):
    # Replica ids 1..n; switches n+1 onward; observer last.
    z=n+len(edges)+1;M=[];F=[]
    for j,(u,v) in enumerate(edges):
        x=n+j+1;M.extend((Message(0,x,0,1,2),Message(x,u+1,1,3,3),Message(x,v+1,2,3,3)));F.append((x,2))
    M.extend(Message(v,z,5,6,6) for v in range(1,n+1))
    return Instance(z+1,6,0,tuple(M),((z,6),),tuple(F),tuple((v,4) for v in range(1,n+1)))


def reduction_family(part=None):
    for n in range(1,6):
        edges0=list(itertools.combinations(range(n),2))
        for mask in range(1<<len(edges0)):
            if part is not None and (n!=5 or mask//128!=part):continue
            edges=[e for j,e in enumerate(edges0) if mask>>j&1];ins=gadget(n,edges);patterns=[]
            for smask in range(1<<n):
                S=tuple((v+1,4) for v in range(n) if smask>>v&1)
                cover=all(smask>>u&1 or smask>>v&1 for u,v in edges)
                cert=certify(ins,S);assert verify(ins,cert);assert cert['safe']==(not cover)
                row=dict(subset=smask,cover=bool(cover),certificate=cert)
                if n<=4:
                    oracle=exhaustive(ins,S);assert oracle['safe']==cert['safe'];row['oracle']=oracle
                patterns.append(row)
            yield dict(vertices=n,graph_mask=mask,edges=edges,instance=ins.to_dict(),patterns=patterns,
                       minimum=min(p['subset'].bit_count() for p in patterns if p['cover']))


def fixed_family():
    rng=random.Random(910737)
    for i in range(256):
        ins=random_instance(rng,single=True,Cmax=6);patterns=[];best=None
        for S in all_sets(ins.candidates,dict(kind='cardinality',k=len(ins.candidates))):
            row=check(ins,S);patterns.append(dict(optional=list(S),oracle=row['oracle']))
            if not row['oracle']['safe'] and best is None:best=len(S)
        cut=minimum_resets(ins);assert cut['count']==best,(ins.to_dict(),cut,best)
        if best is not None:assert not exhaustive(ins,cut['optional'])['safe']
        yield dict(case=i,instance=ins.to_dict(),patterns=patterns,cut=cut,minimum=best)


def direct_family():
    rng=random.Random(910739);i=0
    for r,q,b,W in itertools.product((2,3),(3,4),(1,2),(2,3,4)):
        for rep in range(3):
            M=[]
            for _ in range(4):
                v=rng.randint(1,r);s=rng.randrange(q);a=rng.randint(s+1,q+1);upper=min(q+1,a+rng.randrange(2))
                M.append(Message(0,v,s,a,upper))
            ins=Instance(r+1,q+1,rng.randrange(q+1),tuple(M),tuple((v,q) for v in range(1,r+1)),(),tuple((v,t) for v in range(1,r+1) for t in range(1,q+1)))
            rule=dict(kind='rolling',b=b,W=W);out=packing(ins,b,W);patterns=[];safe=True
            for S in all_sets(ins.candidates,rule):
                o=exhaustive(ins,S);safe &= o['safe'];patterns.append(dict(optional=list(S),oracle=o))
            assert safe==out['safe'],(ins.to_dict(),b,W,out)
            if not safe:
                assert legal(out['optional'],rule)
                assert replay(ins,out['optional'],out['arrivals'])['answer']<ins.cutoff
            yield dict(case=i,b=b,W=W,instance=ins.to_dict(),patterns=patterns,packing=out);i+=1


def periodic_family():
    rng=random.Random(910741)
    for i in range(48):
        P=2+i%2;B=2+(i//2)%2;D=1+(i//4)%2;q=3*P;c=q-B;H=q+D
        # Three fixed contact phases per period; all positive delays <= D.
        profile=[(0,1,rng.randrange(P)),(1,2,rng.randrange(P)),(0,2,rng.randrange(P))]
        M=[]
        for base in range(0,q,P):
            for u,v,phase in profile:
                s=base+phase
                if s<q:M.append(Message(u,v,s,s+1,s+D))
        fphase=rng.randrange(P);ephase=rng.randrange(P)
        F=tuple((1,t) for t in range(1,q+1) if t%P==fphase)
        C=tuple((2,t) for t in range(1,q+1) if t%P==ephase)
        ins=Instance(3,H,c,tuple(M),((1,q),(2,q)),F,C)
        win=Instance(3,B+D,0,tuple(Message(m.u,m.v,m.s-c,m.a-c,m.b-c) for m in M if m.s>=c),((1,B),(2,B)),
                     tuple((v,t-c) for v,t in F if c<t<=q),tuple((v,t-c) for v,t in C if c<t<=q))
        rule=dict(kind='rolling',b=1,W=2+i%2);patterns=[]
        for S in all_sets(C,rule):
            T=tuple((v,t-c) for v,t in S if c<t<=q)
            a=certify(ins,S);z=certify(win,T);assert verify(ins,a) and verify(win,z)
            assert a['safe']==z['safe']==expanded_closure(ins,S)==expanded_closure(win,T)
            row=dict(optional=list(S),full_certificate=a,window_certificate=z)
            if i<12:
                o=exhaustive(ins,S);ow=exhaustive(win,T);assert o['safe']==ow['safe']==a['safe'];row.update(oracle=o,window_oracle=ow)
            patterns.append(row)
        full=universal(ins,rule);small=universal(win,rule)
        assert full['safe']==small['safe'] and verify_universal(ins,full) and verify_universal(win,small)
        yield dict(case=i,P=P,B=B,D=D,profile=profile,rule=rule,instance=ins.to_dict(),window=win.to_dict(),patterns=patterns,safe=full['safe'])


def phases_family():
    for r,P,D,b,W in itertools.product(range(2,6),range(2,9),range(1,4),(1,2),range(2,9)):
        opt=optimize(P,D,b,W,r);sync=phase_bounds(P,D,b,W,[0]*r)
        if opt['bound'] is not None and sync['bound'] is not None:assert opt['bound']<=sync['bound']
        if sync['bound'] is not None:assert opt['bound'] is not None
        yield dict(r=r,P=P,D=D,b=b,W=W,optimal=opt,synchronous=sync)


def scaling_instance(m,scale=1,fixed_horizon=None):
    n=64;base=20*m+10000 if fixed_horizon is None else fixed_horizon;M=[]
    for j in range(m):
        u=0 if j%3==0 else 1+j%63;v=1+(j*17+7)%63;s=10*j
        a=s+1;upper=base-100-v
        M.append(Message(u,v,s*scale,a*scale,upper*scale))
    C=tuple((v,(base-2000+v)*scale) for v in range(1,64))
    return Instance(n,base*scale,0,tuple(M),tuple((v,base*scale) for v in range(1,64)),(),C)


def scaling_family():
    settings=[('events',m,1) for m in (256,512,1024,2048,4096,8192)]
    settings += [('time',512,10**j) for j in range(0,9,2)]
    for axis,m,scale in settings:
        ins=scaling_instance(m,scale,10**12 if axis=='events' else None);S=ins.candidates[::3]
        for rep in range(5):
            p0=time.process_time();w0=time.perf_counter();cert=certify(ins,S);p1=time.process_time();w1=time.perf_counter()
            assert verify(ins,cert);p2=time.process_time();w2=time.perf_counter()
            yield dict(axis=axis,m=m,scale=scale,horizon=ins.horizon,rep=rep,stats=cert['stats'],safe=cert['safe'],
                       producer_cpu=p1-p0,producer_wall=w1-w0,verifier_cpu=p2-p1,verifier_wall=w2-w1,
                       process_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                       input_recipe=dict(generator='scaling_instance',messages=m,time_scale=scale,fixed_horizon=10**12 if axis=='events' else None,optional_stride=3))


FAMILIES={'random':random_family,'overlay':overlay_family,'resets':reset_family,'reduction':reduction_family,
          'fixed':fixed_family,'direct':direct_family,'periodic':periodic_family,'phases':phases_family,'scaling':scaling_family}

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('family',choices=FAMILIES);ap.add_argument('--out',default='results/campaign');ap.add_argument('--part',type=int)
    args=ap.parse_args();out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    label=args.family+(f'-{args.part}' if args.part is not None else '')
    path=out/(label+'.jsonl');count=0;p0=time.process_time();w0=time.perf_counter()
    generator=reduction_family(args.part) if args.family=='reduction' else FAMILIES[args.family]()
    # Truncate only this explicitly requested family output, not other evidence.
    with path.open('w') as f:
        for row in generator:
            f.write(json.dumps(row,separators=(',',':'),sort_keys=True)+'\n');f.flush();count+=1
    obs=dict(family=label,rows=count,cpu_seconds=time.process_time()-p0,wall_seconds=time.perf_counter()-w0,
             peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,workers=1,complete=True)
    (out/(label+'-resources.json')).write_text(json.dumps(obs,indent=2)+'\n');print(json.dumps(obs),flush=True)

if __name__=='__main__':main()
