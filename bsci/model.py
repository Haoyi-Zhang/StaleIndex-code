"""Input validation for the declared discrete-time volatile-index model."""
from dataclasses import dataclass
from typing import Any
from collections.abc import Mapping


def _capture(values, name):
    """Materialize one finite iterable without retaining mutable input aliases."""
    if isinstance(values, (str, bytes, bytearray, Mapping)):
        raise ValueError(f'{name} must be a finite iterable, not text or a mapping')
    try:
        return tuple(values)
    except TypeError as exc:
        raise ValueError(f'{name} must be a finite iterable') from exc


def _pairs(values, name):
    rows = tuple(_capture(row, name) for row in _capture(values, name))
    if any(len(row) != 2 or any(type(x) is not int for x in row) for row in rows):
        raise ValueError(f'{name} must contain exact integer pairs')
    return rows

@dataclass(frozen=True, order=True)
class Message:
    u: int
    v: int
    s: int
    a: int
    b: int

@dataclass(frozen=True)
class Instance:
    n: int
    horizon: int
    cutoff: int
    messages: tuple[Message, ...]
    queries: tuple[tuple[int, int], ...]
    mandatory: tuple[tuple[int, int], ...] = ()
    candidates: tuple[tuple[int, int], ...] = ()

    def __post_init__(self) -> None:
        # frozen=True alone does not freeze lists or preserve one-shot iterators.
        # Snapshot every collection once before checking or repeatedly using it.
        messages = _capture(self.messages, 'messages')
        if any(type(m) is not Message for m in messages):
            raise ValueError('messages must contain Message objects; use from_dict for JSON rows')
        object.__setattr__(self, 'messages', messages)
        for name in ('queries', 'mandatory', 'candidates'):
            object.__setattr__(self, name, _pairs(getattr(self, name), name))
        if type(self.n) is not int or self.n < 1:
            raise ValueError('n must be a positive integer')
        if type(self.horizon) is not int or self.horizon < 0:
            raise ValueError('horizon must be a nonnegative integer')
        if type(self.cutoff) is not int or not 0 <= self.cutoff <= self.horizon:
            raise ValueError('cutoff must lie in [0,horizon]')
        for m in self.messages:
            if any(type(x) is not int for x in (m.u,m.v,m.s,m.a,m.b)):
                raise ValueError('message fields must be integers')
            if not (0<=m.u<self.n and 0<m.v<self.n and 0<=m.s<m.a<=m.b<=self.horizon):
                raise ValueError('invalid message endpoint or interval')
        if not self.queries:
            raise ValueError('at least one query is required')
        for v,t in self.queries:
            if type(v) is not int or type(t) is not int or not (0<=v<self.n and 0<=t<=self.horizon):
                raise ValueError('invalid query')
        for seq in (self.mandatory,self.candidates):
            if len(set(seq))!=len(seq):
                raise ValueError('duplicate reset event')
            for v,t in seq:
                if type(v) is not int or type(t) is not int or not (0<v<self.n and 1<=t<=self.horizon):
                    raise ValueError('invalid reset event')
        if set(self.mandatory)&set(self.candidates):
            raise ValueError('mandatory and optional resets must be disjoint')

    @classmethod
    def from_dict(cls, obj: dict[str,Any]) -> 'Instance':
        required = {'n', 'horizon', 'cutoff', 'messages', 'queries'}
        allowed = required | {'mandatory', 'candidates'}
        if not isinstance(obj, dict) or not required <= set(obj) or not set(obj) <= allowed:
            raise ValueError('instance object has missing or unknown fields')
        rows = tuple(_capture(row, 'messages') for row in _capture(obj['messages'], 'messages'))
        if any(len(row) != 5 for row in rows):
            raise ValueError('each message must have five integer fields')
        return cls(obj['n'], obj['horizon'], obj['cutoff'],
                   tuple(Message(*row) for row in rows), obj['queries'],
                   obj.get('mandatory', ()), obj.get('candidates', ()))

    def to_dict(self) -> dict[str,Any]:
        return dict(n=self.n,horizon=self.horizon,cutoff=self.cutoff,
                    messages=[[m.u,m.v,m.s,m.a,m.b] for m in self.messages],
                    queries=[list(q) for q in self.queries],
                    mandatory=[list(r) for r in self.mandatory],
                    candidates=[list(r) for r in self.candidates])

    def resets(self, optional=()) -> tuple[tuple[int,int],...]:
        s = _pairs(optional, 'optional resets')
        if len(s)!=len(set(s)) or not set(s)<=set(self.candidates):
            raise ValueError('optional resets must be distinct eligible events')
        return tuple(sorted((*self.mandatory,*s)))
