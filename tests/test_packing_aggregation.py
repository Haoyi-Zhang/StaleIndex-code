"""Small independent packing references; no campaign, filesystem writes or clock."""
import itertools
import unittest
from bsci.model import Instance, Message
from bsci.star import packing
from bsci.replay import replay, verify


def instance(messages=(), n=3, q=3, cutoff=0, horizon=5):
    return Instance(n, horizon, cutoff, tuple(Message(*m) for m in messages),
                    tuple((v, q) for v in range(1, n)), (),
                    tuple((v, t) for v in range(1, n) for t in range(1, q + 1)))


def fixtures():
    return [instance(), instance(n=2, q=0),
            instance([(0,1,0,1,1)]), instance([(0,1,0,3,3)]),
            instance([(0,1,0,1,4)]), instance([(0,1,0,1,2)], cutoff=1),
            instance([(0,1,0,1,1),(0,2,0,1,1)]),
            instance([(0,1,0,1,1),(0,1,1,2,2),(0,2,0,1,2)]),
            instance([(0,1,0,1,2),(0,1,0,1,2),(0,2,0,1,2)]),
            instance([(0,1,0,1,4),(0,2,2,3,4)]),
            instance([(0,1,0,1,1),(0,2,0,1,1),(0,3,0,1,1)], n=4, q=4),
            instance([(0,1,0,1,2),(0,1,2,3,4),(0,2,1,2,3)], cutoff=1)]


def rolling(events, b, width):
    # Check every literal window, not the production sorted-rank formula.
    return all(sum(start <= t < start + width for _, t in events) <= b
               for start in range(1 - width, max((t for _, t in events), default=0) + 1))


def reference_packet(ins, b, width):
    """Find earliest erasing slots and greedily enumerate legal latest slots."""
    q = ins.queries[0][1]
    active = []
    for v in range(1, ins.n):
        obligations = [(m.a, m.s) for m in ins.messages if m.v == v and m.s >= ins.cutoff and m.b <= q]
        if obligations:
            earliest = next(t for t in range(1, ins.horizon + 2) if all(a < t for a, _ in obligations))
            active.append((earliest, v))
    active = sorted(active, reverse=True)
    resets = []
    for rank, (earliest, v) in enumerate(active, 1):
        possible = [t for t in range(q, 0, -1) if rolling([*resets, (v,t)], b, width)]
        if not possible or possible[0] < earliest:
            return dict(safe=True, releases=active, violation=rank)
        resets.append((v, possible[0]))
    arrivals = [m.a if m.s >= ins.cutoff and m.b <= q else m.b for m in ins.messages]
    return dict(safe=False, releases=active, optional=resets, arrivals=arrivals)


def literal_answer(ins, resets, arrivals):
    """Direct-source discrete execution, without production replay/helpers."""
    values = [-1] * ins.n
    answers = []
    for time in range(ins.horizon + 1):
        for v, t in resets:
            if t == time:
                values[v] = -1
        for m, arrival in zip(ins.messages, arrivals):
            if arrival == time:
                values[m.v] = max(values[m.v], m.s)
        answers.extend(values[v] for v, q in ins.queries if q == time)
    return max(answers)


def exhaustive_safety(ins, b, width):
    if ins.n > 3 or ins.horizon > 5 or len(ins.candidates) > 6 or len(ins.messages) > 3:
        raise AssertionError("finite oracle fixture bound exceeded")
    assignments = list(itertools.product(*(range(m.a, m.b + 1) for m in ins.messages)))
    if len(assignments) > 8:
        raise AssertionError("finite arrival bound exceeded")
    for mask in range(1 << len(ins.candidates)):
        resets = [event for j, event in enumerate(ins.candidates) if mask >> j & 1]
        if rolling(resets, b, width):
            for arrivals in assignments:
                if literal_answer(ins, resets, arrivals) < ins.cutoff:
                    return False
    return True


class PackingAggregationTests(unittest.TestCase):
    def test_complete_packets_against_slot_search_reference(self):
        for ins, b, width in itertools.product(fixtures(), (1, 2, 3), (1, 2, 4)):
            self.assertEqual(packing(ins, b, width), reference_packet(ins, b, width))

    def test_all_literal_patterns_and_arrivals_in_small_fixtures(self):
        for ins, b, width in itertools.product(fixtures()[:10], (1, 2), (1, 3)):
            self.assertEqual(packing(ins, b, width)["safe"], exhaustive_safety(ins, b, width))

    def test_duplicate_packets_and_equal_release_identity_ties(self):
        ins = fixtures()[8]
        out = packing(ins, 2, 2)
        self.assertEqual(out["releases"], [(2, 2), (2, 1)])
        self.assertEqual(out["arrivals"], [1, 1, 1])
        self.assertEqual(out["optional"], [(2, 3), (1, 3)])

    def test_reset_slot_arrival_survives_and_after_query_is_retained(self):
        forced = fixtures()[3]
        self.assertEqual(packing(forced, 1, 1), dict(safe=True, releases=[(4,1)], violation=1))
        late = fixtures()[4]
        out = packing(late, 1, 1)
        self.assertEqual(out["releases"], [])
        self.assertEqual(out["arrivals"], [4])
        self.assertLess(literal_answer(late, out["optional"], out["arrivals"]), late.cutoff)

    def test_subclass_and_exact_budget_rejections_remain(self):
        base = fixtures()[2]
        for index, value in itertools.product((0, 1), (True, 1.0, 0, -1)):
            args = [1, 2]; args[index] = value
            with self.assertRaisesRegex(ValueError, "b,W must be positive integers"):
                packing(base, *args)
        bad = [
            (Instance(3,5,0,base.messages,base.queries,((1,5),),base.candidates), "no mandatory resets"),
            (instance([(1,2,0,1,1)]), "not a direct-source star"),
            (Instance(3,5,0,base.messages,((1,3),),(),base.candidates), "query must read every replica"),
            (Instance(3,5,0,base.messages,base.queries,(),base.candidates[:-1]), "every replica/time"),
            (Instance(3,5,0,base.messages,base.queries,(),(*base.candidates[:-1],(1,4))), "every replica/time")]
        for ins, reason in bad:
            with self.assertRaisesRegex(ValueError, reason):
                packing(ins, 1, 2)

    def test_negative_witnesses_verify_without_mutating_input(self):
        for ins in fixtures():
            saved = ins.to_dict()
            out = packing(ins, 2, 2)
            if not out["safe"]:
                self.assertTrue(rolling(out["optional"], 2, 2))
                self.assertLess(literal_answer(ins, out["optional"], out["arrivals"]), ins.cutoff)
                packet = dict(safe=False, optional=out["optional"], arrivals=out["arrivals"])
                self.assertTrue(verify(ins, packet, expected_optional=out["optional"]))
                self.assertEqual(replay(ins, out["optional"], out["arrivals"])["answer"],
                                 literal_answer(ins, out["optional"], out["arrivals"]))
                if ins.messages:
                    self.assertFalse(verify(ins, dict(packet, arrivals=[0] * len(ins.messages))))
            self.assertEqual(ins.to_dict(), saved)


if __name__ == "__main__":
    unittest.main()
