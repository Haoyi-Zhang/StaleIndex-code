# Bounded-Staleness Cooperative

Offline certificates for a deliberately limited cooperative-index model: fixed sends, one authoritative snapshot origin, interval delivery, volatile reset/rejoin, durable captured packets, and maximum-watermark lookup batches. This is an internal research artifact, not a production index, a cryptographic attestation system, or a Coral implementation.

## Run from this directory

The repository is self-contained. It needs a Python interpreter supporting the standard-library code and annotations used here (Python 3.10 or newer); no installation, network access, solver, GPU, third-party package, account, or manuscript directory is required. The campaign uses the POSIX `resource` module and was reproduced on Linux; other operating systems were not tested. All scientific commands below use one worker.

Run the complete offline validation in a new directory:

```sh
python validate.py --out results/validation-run
```

This command runs the suite, both pilots, all nine campaign families, the separate epoch audit, examples, documented CLI paths, and expected-failure controls. It compares deterministic records, regenerates the retained tables, and compares newly reproduced derived data after excluding only declared resource/timing observations. JSON scientific comparisons preserve types, so `true`, `1` and `1.0` are not interchangeable. It refuses existing output directories and does not overwrite the reference results. Its summary, actual command exits, resources and logs are in the selected directory. Assertions must be enabled; optimized Python validation is refused. The standalone check does not compile or inspect the manuscript.

`scientific-checks.yml` schedules this check from the flat artifact repository root on Ubuntu 24.04, with a 20-minute whole-command wall limit, 4 GiB address-space cap, and raw-output upload on both success and failure. Preparing the workflow is not evidence of a completed CI run.

For tools with a short execution window, use bounded batches. Exit status 3 means an incomplete checkpoint, not a pass. Resume only while the source and reference inputs are unchanged; the checkpoint validates command order, expected exits and logs, but is not a content-attestation mechanism. The following four invocations completed the clean validation used here:

```sh
python validate.py --out results/validation-run --max-commands 4
python validate.py --out results/validation-run --resume --max-commands 4
python validate.py --out results/validation-run --resume --max-commands 7
python validate.py --out results/validation-run --resume --max-commands 8
```

These are alternatives to the unbounded invocation above, not commands to append after it. Use a new output directory for a new validation. A tool interruption within one command does not make that command complete; the unchanged-source resume reruns it unless a matching completed-command record exists. The final summary must contain `all_checks_passed: true`.

The individual commands are also available:

```sh
python -m unittest discover -s tests -v
python pilots/initial.py --out results/pilots-reproduced/initial.json
python pilots/compact.py --out results/pilots-reproduced/compact.json
python examples.py --out results/examples
python reproduce.py --out results/reproduced
python -m bsci.summarize --results results/reproduced --out results/reproduced-derived
python check_reproduction.py --reference results/campaign --candidate results/reproduced
python epoch_audit.py --out results/epoch-reproduced
python check_epoch_audit.py --reference results/epoch-audit --candidate results/epoch-reproduced
```

The full campaign is sequential. Each family has a 1,800-second child timeout, below the 45-minute run ceiling. On the recorded environment the retained campaign consumed 7.495 CPU seconds and about 114 MiB peak process RSS. Resource observations are not portable speed guarantees. `reproduce.py` stops on a failed command; it does not turn timeouts or mismatches into passing cases. Existing output files for a selected family are overwritten, so use a new output directory when preserving another measurement.

The two `pilots/` scripts preserve the original pre-campaign selections and algorithms with relative output paths. Their fixed scientific counts can be compared to `results/pilot-result.json` and `results/compact-pilot-result.json`; timings, RSS, and the historical projection field are not equality targets.

A family can be rerun in isolation:

```sh
python -m bsci.campaign random --out results/reproduced
```

The nine names are `random`, `overlay`, `resets`, `reduction`, `fixed`, `direct`, `periodic`, `phases`, and `scaling`. `experiment-specification.md` gives the fixed selection. `check_reproduction.py` compares every deterministic field, including the stored exact inputs and certificates; it excludes only the timing and process-RSS fields in the scaling rows. It does not equate successful reproduction with a general proof. Timing and operating-system observations will differ across runs. The clean-copy audit result is in `results/reproduction-check.json`. `results/clean-validation.json` records the current 86-test suite, complete command checks and exact pilot/example comparisons. `results/paper-data-check.json` separately records the project-level plot-data comparison. The separate epoch audit is checked in `results/epoch-reproduction-check.json`. Command-level resources and conservative charges for interrupted orchestration calls are kept separate from the original campaign timings in `results/resource-accounting.json`.

To regenerate the paper's data from the retained observations rather than rerunning timings:

```sh
python -m bsci.summarize --results results/campaign --out results/derived
```

`scaling-events.csv` contains median/minimum/maximum CPU times and asymmetric error lengths for the PGFPlots figure. `phase-slice.csv` contains exact integer bounds, not estimates. Nothing in the summarizer reads the manuscript.

## Produce and verify one certificate

```sh
python -m bsci certify inputs/case-001.json --out results/examples/case-001-certificate.json
python -m bsci verify inputs/case-001.json --packet results/examples/case-001-certificate.json
python -m bsci replay inputs/case-001.json --packet results/examples/case-001-certificate.json
python -m bsci certify inputs/case-002.json --out results/examples/case-002-certificate.json
python -m bsci verify inputs/case-002.json --packet results/examples/case-002-certificate.json
python -m bsci universal inputs/case-003.json --k 1 --out results/examples/case-003-budget-one.json
python -m bsci verify-universal inputs/case-003.json --k 1 --packet results/examples/case-003-budget-one.json
```

`verify` and `verify-universal` return status 0 for valid packets and status 1 for invalid packets; input/IO errors return status 2. `replay` is for a negative packet containing arrivals, not a positive derivation. `--optional path.json` supplies a JSON array of selected eligible reset pairs to `certify` and binds `verify` to that independently requested pattern. Without it, the selected/expected optional pattern is empty. Mandatory resets always apply. `universal` and `verify-universal` require `--k`; verification rejects a packet whose rule differs from that requested budget, even when the packet is valid for its own rule. A budget-one proof is not a budget-two guarantee.

The universal CLI accepts cardinality budgets. Rolling budgets are available without another dependency through the Python interface:

```python
import json
from bsci.model import Instance
from bsci.families import universal, verify_universal
ins = Instance.from_dict(json.load(open("inputs/case-003.json")))
rule = {"kind": "rolling", "b": 1, "W": 2}
packet = universal(ins, rule)
assert verify_universal(ins, packet, expected_rule=rule)
```

Default negative verification establishes a failing admissible execution only. It does not certify a `minimal_optional_count` field. Use `verify_universal(ins, packet, verify_minimum=True, expected_rule=rule)` to additionally enumerate every smaller admissible set. This optional minimality path uses the producer to generate fresh positive proofs; it is not an independent search implementation. It can be exponential. `examples.py` exercises this distinction.

For the Python API, always bind the requested assertion: `verify(ins, packet, expected_optional=selected)` for a fixed pattern, or `verify_universal(ins, packet, expected_rule=rule)` for a reset family. The independently supplied instance includes the cutoff and queries. Omitting these optional binding arguments deliberately checks only the packet's self-described pattern/rule; it must not be interpreted as satisfying a different request. Budget schemas have exactly their documented keys. All integer fields, including optional reset coordinates, reject booleans and floating-point encodings.

## Supplemental epoch audit

`epoch-audit-specification.md` fixes a separate 96-case selection before execution. `epoch_audit.py` compares every node at every slot under single-packet same-epoch postponement and joint canonicalization, using a literal scalar history implementation. The retained audit checks 200 reset patterns, 432 arrival assignments, 250 individual postponements and 432 canonicalizations (239 with a stale batch); a cross-reset negative control distinguishes the invalid unrestricted rule. `check_epoch_audit.py` compares all scientific records and summaries, excluding the separate resource observations. These finite checks supplement, but do not change, the frozen nine-family campaign or its 60,026 execution denominator. The unit suite has 86 tests: 29 original checks, 13 claim-binding/type/CLI regressions, nine exact phase-domain and iterable regressions, six validation-wrapper controls, eleven immutable-instance-input regressions, seven type-preserving evidence-comparison controls, and eleven one-shot reset-capture regressions.

The preceding 86-test count and the retained Linux validation reports are historical. The current source adds one provenance-table regression for the published identity of *Robust Temporal Cut*, giving 87 tests. This addition does not change campaign inputs, scientific denominators, or timing plots.

## Scientific map

`proofs/model-and-results.md` contains complete written arguments. The manuscript also contains the central proofs; no proof assistant is claimed. `bsci/model.py` validates instances. `certify.py` is the range-AND producer. `replay.py` independently rebuilds points, checks positive derivations by Fenwick counts, and replays negative packets with scalar watermarks; it imports no producer code. `oracle.py` provides literal per-slot scalar execution, exhaustive arrival enumeration, and expanded closure. `flow.py` is the singleton-arrival minimum-cut baseline; it shares the producer's endpoint builder. `star.py` implements the direct-replica packing and phase formulas. `families.py` explicitly enumerates quantified reset families. `campaign.py` contains the deterministic generators and assertions.

The raw results cover 60,026 exhaustive full-history arrival executions, not 60,026 independent workloads. The graph family covers all 1,099 labelled graphs through five vertices and 33,866 vertex subsets, but full arrival enumeration is only through four vertices. The phase family evaluates 53,508 zero-anchored nondecreasing multisets in 1,176 settings; these are not distinct rotational orbits. See `results/derived/summary.json` and `claim_evidence_ledger.csv` for exact scope.

## Model boundaries

Resets erase a replica immediately before that slot's arrivals; sends happen after arrivals and queries. Payloads are captured at send time and survive subsequent endpoint resets. Every scheduled packet arrives exactly once at one independent integer time in its interval. The origin never resets or receives packets. Initial nonorigin state is -1. A snapshot watermark establishes complete information as of that time, including deletions and no-change intervals; it is not simply a last-record-update timestamp. The query returns the largest observed watermark, and -1 is failure rather than abstention.

A rolling budget counts optional erasures globally across replicas, not an unavailable-node fraction. Mandatory resets are uncharged and explicit. The NP-hardness result uses a mandatory reset profile. The polynomial cut result assumes singleton arrivals and unit per-event reset cost. The direct-replica formula assumes complete per-slot reset eligibility, no mandatory resets, and a simultaneous query of all replicas. Sparse eligibility, packet loss, downtime, adaptive sending, incomplete advertisements, authentication, arbitrary membership, and Internet performance are not covered.

## Provenance and limitations

All experimental inputs are original synthetic instances; no external data acquisition is needed for reproduction. Scholarly resources and exact read representations are recorded in `external_resources.csv`, `literature-boundary.md`, and the 31-entry `bibliography-audit.csv`; `bibliography-audit.md` states the reading and publication-status boundaries. Scholarly papers are not redistributed. `LICENSE` and `licenses/NOTICE.md` describe permissions and attribution. No invented repository URL is supplied.

The written proofs, finite checks, measurements, second verifier and clean-copy rerun are different kinds of evidence. None constitutes independent external review.

## Exact periodic-helper inputs

`bsci.star.phase_bounds(P, D, b, W, phases)` and `optimize(P, D, b, W, r)` require strictly positive integer period, maximum delay, rolling capacity, window width, and replica count. `window(P, D, phases, B, qphase)` requires integer `B >= 0` and `0 <= qphase < P`. Every phase is an integer in `[0,P)` and the collection is nonempty. Booleans, floats, strings and out-of-domain values are rejected with `ValueError`. A finite one-shot iterable of phases is captured once; list, tuple and iterator inputs then describe the same schedule. The general reset-family checker permits zero reset capacity, but these direct-star phase formulas intentionally use the proved `b >= 1` domain.

The phase-interface regressions address an input-contract defect, not a new theorem or experimental family. The retained campaign supplies ordinary integer lists/tuples; its complete deterministic phase records must remain unchanged after this repair. An out-of-domain phase must not be silently interpreted as a replica with no sends.

## Stable instance inputs

`Instance` captures finite message, query and reset iterables once, including nested query/reset pairs, and stores immutable tuples. A caller's later list mutation cannot change a validated instance. Direct messages must be `Message` objects; use `Instance.from_dict` for JSON five-field rows. JSON root fields are exactly the documented required fields plus optional `mandatory` and `candidates`; unknown fields are rejected rather than silently ignored. Malformed rows and boolean/float aliases in integer domains raise `ValueError`. Infinite iterables are outside this finite input contract. These are input guards, not a resource quota for potentially exponential reset-family enumeration.

`bsci/evidence.py` contains type-preserving result comparison and the explicit derived-data exclusion list. Original timing plots continue to use retained observations. A new timing measurement is neither required to equal the old one nor silently substituted into the paper.


Certificate producers, fixed-pattern and aggregate verifiers, and the exhaustive oracle capture each finite optional-reset iterable before reusing it. Nested one-shot pairs are normalized to immutable tuples. Coverage checks and proof replay therefore use the same reset pattern, and every arrival assignment in an exhaustive call uses that pattern. A caller reusing an already consumed generator in a separate API call must instead provide a new iterable or retain a tuple. The JSON certificate format remains unchanged. `tests/test_reset_capture.py` includes a two-node false-acceptance control and a one-edge gadget whose second enumerated arrival assignment is stale; these are finite interface regressions, not new campaign samples.
