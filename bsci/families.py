"""Explicit optional-reset families and coverage-checked aggregate certificates."""
from itertools import combinations
from .certify import certify
from .replay import verify, capture_certificate

def normalize_rule(rule):
    """Validate the exact JSON rule schema; booleans are not integer budgets."""
    if not isinstance(rule,dict):raise ValueError('reset rule must be an object')
    if rule.get('kind')=='cardinality':
        if set(rule)!={'kind','k'} or type(rule['k']) is not int or rule['k']<0:
            raise ValueError('invalid cardinality rule')
        return dict(kind='cardinality',k=rule['k'])
    if rule.get('kind')=='rolling':
        if (set(rule)!={'kind','b','W'} or type(rule['b']) is not int or
                type(rule['W']) is not int or rule['b']<0 or rule['W']<1):
            raise ValueError('invalid rolling rule')
        return dict(kind='rolling',b=rule['b'],W=rule['W'])
    raise ValueError('unknown reset family')

def rolling_legal(events,b,W):
    if type(b) is not int or type(W) is not int or b<0 or W<1:raise ValueError('invalid rolling budget')
    times=sorted(t for v,t in events)
    if b==0:return not times
    return all(times[i+b]-times[i]>=W for i in range(len(times)-b))

def legal(events,rule):
    rule=normalize_rule(rule)
    if rule['kind']=='cardinality':
        k=rule['k']
        if type(k) is not int or k<0:raise ValueError('invalid cardinality budget')
        return len(events)<=k
    if rule['kind']=='rolling':return rolling_legal(events,rule['b'],rule['W'])
    raise ValueError('unknown reset family')

def all_sets(candidates,rule):
    C=tuple(sorted(candidates))
    for k in range(len(C)+1):
        for S in combinations(C,k):
            if legal(S,rule):yield S

def maximal_sets(candidates,rule):
    rule=normalize_rule(rule)
    C=tuple(sorted(candidates))
    if rule['kind']=='cardinality':
        k=rule['k']
        if type(k) is not int or k<0:raise ValueError('invalid cardinality budget')
        yield from combinations(C,min(k,len(C)));return
    for S in all_sets(C,rule):
        selected=set(S)
        if all(not legal((*S,e),rule) for e in C if e not in selected):yield S

def universal(ins,rule):
    """Positive packet covers every maximal set; negative is minimum cardinality."""
    rule=normalize_rule(rule)
    certificates=[]
    for S in maximal_sets(ins.candidates,rule):
        cert=certify(ins,S)
        if not cert['safe']:
            for T in all_sets(ins.candidates,rule):
                smaller=certify(ins,T)
                if not smaller['safe']:
                    return dict(safe=False,rule=rule,certificate=smaller,
                                minimal_optional_count=len(T))
            raise AssertionError('failed to recover known witness')
        certificates.append(cert)
    return dict(safe=True,rule=rule,certificates=certificates)

def verify_universal(ins,packet,verify_minimum=False,*,expected_rule=None):
    """Check the packet's assertion, or bind it to an independently supplied rule.

    Without expected_rule this checks only the packet's self-described budget.
    Minimum-count checking requires enumeration; a witness alone cannot prove it.
    """
    try:
        if type(packet['safe']) is not bool:return False
        rule=normalize_rule(packet['rule'])
        if expected_rule is not None and rule!=normalize_rule(expected_rule):return False
        if not packet['safe']:
            cert=capture_certificate(packet['certificate']);S=cert['optional']
            if cert['safe'] or not legal(S,rule) or not verify(ins,cert,expected_optional=S):return False
            if verify_minimum:
                claimed=packet['minimal_optional_count']
                if type(claimed) is not int or claimed!=len(S):return False
                # This optional check uses freshly generated positive certificates.
                # The default negative verifier checks failure only, not minimality.
                for T in all_sets(ins.candidates,rule):
                    if len(T)>=claimed:break
                    proof=certify(ins,T)
                    if not proof['safe'] or not verify(ins,proof):return False
            return True
        expected=set(maximal_sets(ins.candidates,rule));seen=set()
        for raw_certificate in packet['certificates']:
            cert=capture_certificate(raw_certificate)
            S=tuple(sorted(cert['optional']))
            if S in seen or S not in expected or not cert['safe'] or not verify(ins,cert,expected_optional=S):return False
            seen.add(S)
        return seen==expected
    except (KeyError,TypeError,ValueError):return False
