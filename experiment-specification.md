# Fixed validation specification

The campaign is a collection of exact finite falsification tests of the accompanying mathematical model. It is not a workload or deployment benchmark. It has no learned parameters, training set, participant study, or favorable-outcome selection rule.

Selections: random (3,200, seed 910731); four-contact overlay (256); reset families (96, seed 910733); graph reduction (all 1,099 labelled simple graphs on 1..5 vertices and all 33,866 vertex subsets); singleton-arrival minimum cut (256, seed 910737); direct-source packing (72, seed 910739); periodic threshold windows (48, seed 910741); phase design (1,176 settings, all zero-anchored nondecreasing phase multisets); event-count and binary-time sensitivity (one worker, five repetitions at each of six message counts); invalid-certificate and event-order controls.

Each deterministic row includes its source case and oracle verdict. Timings and process peak RSS are observations specific to a run. No numerical performance improvement is required. A discrepancy terminates a family and must be retained for repair, not excluded as an inconvenient instance. Whole families can be reproduced separately. No outside dataset or executable baseline is consumed.

Phase optimization compares equal-rate one-refresh-per-replica schedules only. Infinite bounds are derived from the exact packing formula, not from exhausting a search cap. Minimal negative certificates minimize optional reset count, not trace length or query time.
