"""Model-boundary regressions; these are separate from the frozen campaign."""
from dataclasses import FrozenInstanceError
import unittest
from bsci.model import Instance, Message
from bsci.certify import certify
from bsci.replay import replay, verify

class InstanceInterfaceTests(unittest.TestCase):
    def make(self, **changes):
        fields = dict(n=2, horizon=3, cutoff=0, messages=(Message(0, 1, 0, 1, 1),),
                      queries=((1, 3),), mandatory=(), candidates=((1, 2),))
        fields.update(changes)
        return Instance(**fields)

    def test_message_generator_preserves_schedule_and_certificate(self):
        expected = self.make()
        actual = self.make(messages=(m for m in expected.messages))
        self.assertEqual(actual, expected)
        self.assertEqual(certify(actual), certify(expected))
        self.assertTrue(certify(actual)['safe'])
        self.assertEqual(replay(actual, (), [1])['answer'], 0)

    def test_all_collection_generators_are_captured(self):
        expected = self.make(mandatory=((1, 3),))
        values = {name: (x for x in getattr(expected, name))
                  for name in ('messages', 'queries', 'mandatory', 'candidates')}
        actual = self.make(**values)
        self.assertEqual(actual, expected)
        self.assertEqual(certify(actual), certify(expected))
        self.assertFalse(certify(actual)['safe'])

    def test_nested_pair_generators_are_captured(self):
        actual = self.make(queries=(iter((1, 3)),), candidates=(iter((1, 2)),))
        self.assertEqual(actual, self.make())
        self.assertTrue(verify(actual, certify(actual)))

    def test_lists_are_detached_from_caller(self):
        messages = [Message(0, 1, 0, 1, 1)]
        queries, mandatory, candidates = [[1, 3]], [], [[1, 2]]
        actual = self.make(messages=messages, queries=queries,
                           mandatory=mandatory, candidates=candidates)
        expected = self.make()
        messages.clear(); queries[0][0] = 0; mandatory.append([1, 3]); candidates[0][1] = 3
        self.assertEqual(actual, expected)
        self.assertEqual(certify(actual), certify(expected))
        self.assertTrue(certify(actual)['safe'])

    def test_from_dict_is_detached_and_round_trips(self):
        obj = self.make().to_dict()
        actual = Instance.from_dict(obj)
        obj['messages'][0][0] = 1; obj['queries'][0][1] = 0
        self.assertEqual(actual, self.make())
        self.assertEqual(Instance.from_dict(actual.to_dict()), actual)

    def test_empty_query_iterator_is_rejected(self):
        with self.assertRaises(ValueError): self.make(queries=iter(()))

    def test_duplicate_and_overlapping_iterated_resets_are_rejected(self):
        for changes in ({'candidates': iter(((1, 2), (1, 2)))},
                        {'mandatory': iter(((1, 2),))}):
            with self.subTest(changes=tuple(changes)):
                with self.assertRaises(ValueError): self.make(**changes)

    def test_invalid_collection_and_message_shapes_raise_value_error(self):
        for name in ('messages', 'queries', 'mandatory', 'candidates'):
            for value in (None, 1, '12', b'12', {1: 2}):
                with self.subTest(name=name, value=value):
                    with self.assertRaises(ValueError): self.make(**{name: value})
        for message in (None, [0, 1, 0, 1, 1], {'u': 0}):
            with self.subTest(message=message):
                with self.assertRaises(ValueError): self.make(messages=[message])
        for pair in ((1,), (1, 2, 3), (True, 2), (1, 2.0), 1, None):
            with self.subTest(pair=pair):
                with self.assertRaises(ValueError): self.make(candidates=[pair])

    def test_from_dict_rejects_missing_unknown_or_malformed_fields(self):
        for obj in (None, [], {}, {**self.make().to_dict(), 'canddiates': []}):
            with self.subTest(obj=obj):
                with self.assertRaises(ValueError): Instance.from_dict(obj)
        for row in ([], [0, 1, 0, 1], [0, 1, 0, 1, 1, 1], 3, None):
            with self.subTest(row=row):
                with self.assertRaises(ValueError):
                    Instance.from_dict({**self.make().to_dict(), 'messages': [row]})

    def test_frozen_instance_and_messages_remain_immutable(self):
        ins = self.make()
        with self.assertRaises(FrozenInstanceError): ins.queries = ()
        with self.assertRaises(FrozenInstanceError): ins.messages[0].a = 2
        self.assertIsInstance(hash(ins), int)

    def test_optional_pair_iterators_and_malformed_values(self):
        ins = self.make()
        self.assertEqual(ins.resets(iter((iter((1, 2)),))), ((1, 2),))
        for value in (None, 1, {1: 2}, [(1,)], [(1, 2, 3)], [(1.0, 2)]):
            with self.subTest(value=value):
                with self.assertRaises(ValueError): ins.resets(value)

if __name__ == '__main__': unittest.main()
