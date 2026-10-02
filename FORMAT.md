# Instance, certificate, and replay formats

## Exact input

An instance is a JSON object with `n`, `horizon`, `cutoff`, `messages`, and a nonempty `queries` array. `mandatory` and `candidates` default to empty arrays. Integer fields reject booleans and floating-point times; unknown root fields are invalid. A message is `[sender, receiver, send, earliest, latest]`, with `0 <= send < earliest <= latest <= horizon`. Node 0 is the immortal origin; receivers must be nonorigin nodes. Queries are `[node,time]`. Resets are `[nonorigin_node,time]` with `1 <= time <= horizon`. Duplicate reset events and overlap between mandatory and candidates are invalid. Distinct messages may have identical five-tuples: they still represent distinct captured packets.

The Python constructor captures all finite input iterables exactly once and stores immutable tuples, including nested query/reset pairs. Lists cannot mutate the validated schedule afterward. Direct message elements are `Message` instances; the JSON decoder converts exact five-field rows. These guards do not detect an infinite iterable, which is outside the finite input contract.

All-time numeric horizon and explicit input length are distinct. Sparse eligibility can be represented in binary time with few points. Eligibility at every slot is an explicit input of size proportional to the horizon in the general checker. Input validation does not impose a workload cap: family enumeration is intended for bounded owned toy instances.

## Fixed-pattern positive certificate

`safe: true`, an `optional` array, a `steps` array, and diagnostic `stats`. Each step begins `[node,time,reason,...]`. The legal reasons are `query` with no further argument; `mem` followed by the next retained time at the same node; or `msg` followed by the zero-based message index. A point occurs at most once. Its justification must be satisfied by earlier steps. A message premise covers **all** retained receiver points in the original arrival interval. A memory premise requires the next point already marked and no actual reset in the intervening half-open memory segment `(time,next_time]`. At least one derived origin point must have time at or after the cutoff.

The statistics are diagnostics; the verifier does not trust them. Points are regenerated from the supplied instance, including all eligible reset boundaries, even if a particular optional reset is not selected. A certificate is not a signed statement of physical timing.

## Fixed-pattern negative certificate

`safe: false`, `optional`, and `arrivals` (one integer per message, in input order), with diagnostic `stats`. Replay checks all intervals and eligibility, captures payloads at sends, and applies reset, origin advance, arrivals, queries, sends in that order. The largest query answer must be strictly below the cutoff. A replay trace records event time, post-event node values, reset nodes, message indices arriving/sending, and query indices. Node values are scalar watermarks, not contents or probability estimates.

## Aggregate certificates

A positive aggregate contains `safe: true`, a `rule`, and `certificates` covering exactly all inclusion-maximal admissible reset subsets, without duplication. A cardinality rule is `{"kind":"cardinality","k":k}`; a rolling rule is `{"kind":"rolling","b":b,"W":W}`. `k,b` are nonnegative integers and `W` is positive. A negative aggregate contains one fixed-pattern negative `certificate` plus its `rule`. Generation also reports `minimal_optional_count`, but ordinary verification does not establish that annotation. The explicit `verify_minimum` option checks all smaller admissible subsets. This can be much more expensive than checking a witness.

## Binding the assertion

The caller supplies an independent instance, including cutoff and query batch. `verify(ins, packet, expected_optional=S)` additionally requires that the packet select exactly `S`; the mandatory profile remains part of the instance. `verify_universal(ins, packet, expected_rule=rule)` additionally requires exact equality with the independently supplied cardinality or rolling rule. The rule schema admits only the documented keys. All integer fields reject booleans and floating-point values, even if their numerical values compare equal to integers.

When the expected argument is omitted, the Python API checks the packet's self-described assertion only. This mode cannot establish a stronger externally requested bound. The CLI defaults fixed-pattern verification to the empty optional set unless `--optional` is supplied, and requires `--k` explicitly for cardinality-family generation and verification. Diagnostic statistics and a minimum-count annotation are never substitutes for these premises.

## Encoding and work

The producer uses a balanced range tree and least implication closure. The positive verifier instead counts marked points in a Fenwick tree. Negative replay sorts only actual event times. Arithmetic is exact integer arithmetic; stated complexity bounds count word operations and comparisons. Integers require logarithmically many bits in the numeric horizon. Python object overhead and observed CPU time are not part of the mathematical encoding bound.

## Periodic calculation interface

The phase helpers operate on exact integers: `P,D,b,W,r >= 1`, `B >= 0`, `0 <= qphase < P`, and nonempty phase sequences with every entry in `[0,P)`. Booleans and floating-point aliases are invalid. Finite iterables are materialized once so that a generator is not consumed by validation before calculation. `window` rejects an invalid phase instead of dropping all of that replica's sends. These helper restrictions do not change the general certificate family's permitted zero reset budget.

## Stable reset patterns in Python calls

For finite Python iterables, optional reset events are captured exactly once per producer/checker/oracle call, including nested event pairs. Aggregate family coverage and the checked subcertificate are bound to that captured pattern. Every arrival assignment in an exhaustive call uses the same captured resets. Capturing creates detached tuples without changing the caller's dictionary; it cannot restore an iterator already consumed in an earlier call. JSON arrays and all reset-budget semantics are unchanged. Malformed rows, boolean/float coordinates, duplicates and ineligible events are rejected, rather than converted into a different claim.
