"""Finite pointwise checks of receiver-epoch postponement; not general proofs."""
import argparse
import itertools
import json
from pathlib import Path
import random
import resource
import time

from bsci.model import Instance, Message


def histories(ins, optional, arrivals):
    """Literal slot-by-slot simulation, independent of producer and replay code."""
    resets = set(ins.resets(optional))
    state = [-1] * ins.n
    packets = [None] * len(ins.messages)
    result = []
    for t in range(ins.horizon + 1):
        for v in range(1, ins.n):
            if (v, t) in resets:
                state[v] = -1
        state[0] = t
        for i, message in enumerate(ins.messages):
            if arrivals[i] == t:
                assert packets[i] is not None
                state[message.v] = max(state[message.v], packets[i])
        result.append(list(state))
        for i, message in enumerate(ins.messages):
            if message.s == t:
                packets[i] = state[message.u]
    return result


def dominated(later, earlier):
    return all(x <= y for a, b in zip(later, earlier) for x, y in zip(a, b))


def cases():
    rng = random.Random(910743)
    for case in range(96):
        n = rng.randint(2, 4); horizon = rng.randint(3, 7)
        messages = []
        for _ in range(rng.randint(1, 5)):
            u = rng.randrange(n); v = rng.randrange(1, n)
            s = rng.randrange(horizon); a = rng.randint(s + 1, horizon)
            upper = min(horizon, a + rng.randrange(2))
            messages.append(Message(u, v, s, a, upper))
        pool = [(v, t) for v in range(1, n) for t in range(1, horizon + 1)]
        rng.shuffle(pool)
        nf = rng.randint(0, min(2, len(pool)))
        nc = rng.randint(0, min(2, len(pool) - nf))
        yield case, Instance(n, horizon, rng.randrange(horizon + 1), tuple(messages),
            tuple((v, horizon) for v in range(1, n)),
            tuple(sorted(pool[:nf])), tuple(sorted(pool[nf:nf + nc])))


def run(out):
    out.mkdir(parents=True, exist_ok=True)
    start = time.process_time()
    totals = dict(cases=0, reset_patterns=0, arrival_assignments=0,
                  single_postponements=0, canonicalizations=0, stale_canonicalizations=0)
    with (out/'cases.jsonl').open('w') as stream:
        for case, ins in cases():
            counts = {key: 0 for key in totals if key != 'cases'}
            for k in range(len(ins.candidates) + 1):
                for optional in itertools.combinations(ins.candidates, k):
                    counts['reset_patterns'] += 1
                    resets = ins.resets(optional)
                    for arrivals in itertools.product(*(range(m.a, m.b + 1) for m in ins.messages)):
                        counts['arrival_assignments'] += 1
                        before = histories(ins, optional, arrivals)
                        canonical = []
                        for i, (message, arrival) in enumerate(zip(ins.messages, arrivals)):
                            for later in range(arrival + 1, message.b + 1):
                                if any(v == message.v and arrival < t <= later for v, t in resets):
                                    continue
                                changed = list(arrivals); changed[i] = later
                                after = histories(ins, optional, changed)
                                counts['single_postponements'] += 1
                                if not dominated(after, before):
                                    (out/'discrepancy.json').write_text(json.dumps(dict(
                                        instance=ins.to_dict(), optional=optional,
                                        arrivals=arrivals, changed=changed, before=before, after=after), indent=2))
                                    raise AssertionError('receiver-epoch domination failed')
                            end = min([message.b] + [t - 1 for v, t in resets
                                if v == message.v and arrival < t <= message.b])
                            canonical.append(end)
                        after = histories(ins, optional, canonical)
                        if not dominated(after, before):
                            (out/'discrepancy.json').write_text(json.dumps(dict(
                                instance=ins.to_dict(), optional=optional, arrivals=arrivals,
                                changed=canonical, before=before, after=after), indent=2))
                            raise AssertionError('joint canonicalization domination failed')
                        counts['canonicalizations'] += 1
                        if max(before[t][v] for v, t in ins.queries) < ins.cutoff:
                            assert max(after[t][v] for v, t in ins.queries) < ins.cutoff
                            counts['stale_canonicalizations'] += 1
            stream.write(json.dumps(dict(case=case, instance=ins.to_dict(), **counts), sort_keys=True) + '\n')
            stream.flush()
            totals['cases'] += 1
            for key, value in counts.items(): totals[key] += value
            if time.process_time() - start > 60: raise TimeoutError('audit CPU budget exceeded')
            if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss > 256 * 1024:
                raise MemoryError('audit process RSS budget exceeded')
    control = Instance(2, 2, 0, (Message(0, 1, 0, 1, 2),), ((1, 2),), ((1, 2),))
    early = histories(control, (), [1]); late = histories(control, (), [2])
    assert early[2][1] == -1 and late[2][1] == 0 and not dominated(late, early)
    summary = dict(**totals, all_pointwise_checks_passed=True,
        negative_control=dict(instance=control.to_dict(), early_arrivals=[1], late_arrivals=[2],
                              early_answer=early[2][1], late_answer=late[2][1], distinguishes_reset_boundary=True),
        scope='Finite validation of written arguments; separate from the original nine-family campaign.')
    (out/'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    observations = dict(cpu_seconds=time.process_time() - start,
        peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, workers=1, complete=True)
    (out/'resources.json').write_text(json.dumps(observations, indent=2) + '\n')
    print(json.dumps(dict(summary=summary, resources=observations), indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path('results/epoch-audit'))
    run(parser.parse_args().out)
