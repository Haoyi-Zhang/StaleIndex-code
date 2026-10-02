# Small exact inputs

These are original synthetic instances, not observations of a network.

- `case-001.json`: an arrival at time 1 is erased by the reset at 2; arrival at 2 survives. The all-latest negative control.
- `case-002.json`: two individually vulnerable queried replicas form a universally fresh batch. One packet chooses which replica is fresh. Five derivation entries suffice for the batch.
- `case-003.json`: two fixed-arrival source replicas need two optional erasures to make their batch stale. Cardinality budget 1 is safe; budget 2 has minimum failure count 2.

All larger exact cases are retained with their outcomes in `results/campaign/*.jsonl`. Scaling rows use an explicit deterministic construction recipe rather than duplicating thousands of packet fields; the construction is in `bsci/campaign.py`. No external data is needed.
