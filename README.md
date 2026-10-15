# Bounded-Staleness Cooperative

Offline certificates for a cooperative-index model with fixed sends, one authoritative snapshot origin, interval delivery, volatile reset/rejoin, durable captured packets, and maximum-watermark lookup batches. This is not a production index, cryptographic attestation system, or Coral implementation.

## Requirements and quick checks

Run commands from this directory with Python 3.10+ and assertions enabled (no `-O` or `PYTHONOPTIMIZE`). No installation, third-party package, solver, network access, external dataset, account, GPU, or manuscript directory is needed. Full validation and campaigns require Linux/POSIX's `resource` module; the finite certificate API is separate from that measurement runner. Commands use one worker.

```sh
python -B -m unittest discover -s tests -v
python -B -m bsci --help
```

The current discovered suite has 93 tests. Historical reports with 86 or 87 tests describe the suite at those executions, not a current 93-test rerun.

## Complete isolated validation

Choose an output directory that does not already exist:

```sh
python -B validate.py --out results/validation-run
```

This runs the suite, both pilots, all nine campaign families, the separate epoch audit, examples, documented CLI paths, and expected-failure controls. It compares deterministic records and derived data while excluding only declared timing/resource observations. JSON comparisons distinguish `true`, `1`, and `1.0`. Reference results are not overwritten. The selected directory contains logs, command exits/resources, and `summary.json`; completion requires `all_checks_passed: true`. No manuscript build is performed.

For bounded execution windows, start with `--max-commands 4`, then repeat with `--resume --max-commands 4` until complete. Exit 3 means an incomplete checkpoint, not success. Resume only with unchanged source/reference inputs. The checkpoint validates command order, expected exits, and logs; it is not content attestation. A command interrupted before its completion record is written is rerun.

The scientific GitHub workflow runs this validation on Ubuntu 24.04 with a 20-minute command limit, 4 GiB address-space cap, and raw-output upload on success or failure. Each campaign child has a 1,800-second timeout. A failed command or mismatch stops reproduction.

## Produce and verify certificates

These examples write to a separate local-output directory, not the retained `results/examples/`:

```sh
python -B -m bsci certify inputs/case-001.json --out results/local-examples/case-001.json
python -B -m bsci verify inputs/case-001.json --packet results/local-examples/case-001.json
python -B -m bsci replay inputs/case-001.json --packet results/local-examples/case-001.json
python -B -m bsci certify inputs/case-002.json --out results/local-examples/case-002.json
python -B -m bsci verify inputs/case-002.json --packet results/local-examples/case-002.json
python -B -m bsci universal inputs/case-003.json --k 1 --out results/local-examples/budget-one.json
python -B -m bsci verify-universal inputs/case-003.json --k 1 --packet results/local-examples/budget-one.json
```

`verify` and `verify-universal` exit 0 for valid packets, 1 for invalid packets, and 2 for input/IO errors. `replay` requires a negative packet containing arrivals. `--optional path.json` supplies selected eligible reset pairs to `certify` and independently binds `verify` to that pattern; the default optional pattern is empty. Mandatory resets always apply. Universal CLI commands require `--k`; a budget-one proof does not establish a budget-two guarantee.

In Python, bind the requested assertion with `verify(ins, packet, expected_optional=selected)` or `verify_universal(ins, packet, expected_rule=rule)`. Omitting these arguments checks only the packet's self-described pattern/rule. Rolling families are available through this API:

```python
import json
from bsci.model import Instance
from bsci.families import universal, verify_universal
with open("inputs/case-003.json") as stream:
    ins = Instance.from_dict(json.load(stream))
rule = {"kind": "rolling", "b": 1, "W": 2}
packet = universal(ins, rule)
assert verify_universal(ins, packet, expected_rule=rule)
```

Ordinary negative verification checks a failing admissible execution, not `minimal_optional_count`. Set `verify_minimum=True` to enumerate every smaller admissible reset set; this can be exponential and uses the producer for fresh positive proofs, not an independent search implementation.

See `FORMAT.md` for exact schemas, strict integer domains, periodic-helper restrictions, immutable finite input capture, and one-shot reset iterable handling. An iterable consumed by an earlier call must be replaced or retained as a tuple. Infinite iterables are outside the contract.

## Reproduction entrypoints and results

Use fresh output paths: the individual campaign, example, pilot, and summarizer entrypoints can overwrite selected output files.

```sh
python -B reproduce.py --out results/reproduced
python -B -m bsci.summarize --results results/reproduced --out results/reproduced-derived
python -B check_reproduction.py --reference results/campaign --candidate results/reproduced --out results/reproduced-check.json
python -B epoch_audit.py --out results/epoch-reproduced
python -B check_epoch_audit.py --reference results/epoch-audit --candidate results/epoch-reproduced --out results/epoch-reproduced-check.json
python -B -m bsci.campaign random --out results/single-family
```

The nine families are `random`, `overlay`, `resets`, `reduction`, `fixed`, `direct`, `periodic`, `phases`, and `scaling`; their selection is in `experiment-specification.md`. `pilots/initial.py` and `pilots/compact.py` retain the pre-campaign algorithms, with scientific references in `results/pilot-result.json` and `results/compact-pilot-result.json`. `examples.py` exercises the CLI/API distinctions above. Each accepts `--out`.

To derive tables/plot inputs from retained observations without new timing measurements:

```sh
python -B -m bsci.summarize --results results/campaign --out results/local-derived
```

`results/derived/` is the retained comparison target. `scaling-events.csv` contains median/min/max CPU times and asymmetric error lengths; `phase-slice.csv` contains exact integer bounds. The summarizer does not read the manuscript.

The raw campaign covers 60,026 full-history arrival executions, not independent workloads. Graph reduction includes 1,099 labelled graphs through five vertices and 33,866 vertex subsets; full arrival enumeration stops at four vertices. Phase design includes 53,508 zero-anchored nondecreasing multisets in 1,176 settings, not distinct rotational orbits. The separate epoch audit covers 96 cases, 200 reset patterns, 432 arrival assignments, 250 postponements, and 432 canonicalizations; it does not change the campaign denominator. See `epoch-audit-specification.md`, `results/derived/summary.json`, and `claim_evidence_ledger.csv`.

Retained validation/resource records remain in `results/`; `results/measurements/current-linux/` contains an Ubuntu 24.04 run with 87 tests and 23 commands, all 6,258 campaign rows, six derived scientific files, and the epoch audit. These are recorded observations, not portable speed guarantees or a claim that later tests were executed in that run.

## Implementation and assumptions

`bsci/model.py` validates inputs; `certify.py` implements range-AND closure. `replay.py` independently reconstructs points, checks positive derivations with Fenwick counts, and replays negative packets with scalar watermarks without importing the producer. `oracle.py` supplies literal per-slot execution and exhaustive arrival enumeration. `flow.py` is the singleton-arrival min-cut baseline and shares the producer's endpoint builder. `star.py` supplies direct-replica packing/phase formulas; `families.py` enumerates reset families. Written arguments are in `proofs/model-and-results.md`; finite agreement is not a mechanized proof.

Resets happen immediately before arrivals; sends follow arrivals and queries. Captured payloads survive endpoint resets. Each packet arrives once at an independent integer time in its interval. The origin never resets or receives packets, and nonorigin state starts at -1. A watermark means a complete authoritative as-of snapshot, including deletions and unchanged intervals, not merely a last-update timestamp. Queries return the maximum watermark; -1 is failure, not abstention.

Rolling budgets count optional erasures globally, not unavailable-node fractions. Mandatory resets are explicit and uncharged. Hardness uses a mandatory reset profile; the polynomial cut result assumes singleton arrivals and unit per-event costs. Direct packing assumes complete per-slot reset eligibility, no mandatory resets, and simultaneous replica queries. Sparse eligibility, packet loss, downtime, adaptive sends, incomplete advertisements, authentication, arbitrary membership, and Internet performance are outside those formulas.

## Sources and license

Inputs are original synthetic instances; no outside dataset is required. Source identities/read scopes are retained in `external_resources.csv`, `bibliography-audit.csv`, `bibliography-audit.md`, and `literature-boundary.md`. Scholarly PDFs are not redistributed. `LICENSE` and `licenses/NOTICE.md` retain permissions, attribution, and tool-use disclosure.
