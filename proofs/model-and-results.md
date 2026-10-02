# Model and mathematical arguments

These are mathematical proofs, not proof-assistant mechanizations. Executable finite checks test implementations and boundary cases; they do not establish the unbounded theorems. All times are integers, encoded in binary. A certificate is a replayable derivation or execution, not a cryptographic attestation.

## Definitions

There are n fixed nodes, including an immortal authoritative origin 0. At the beginning, every other node has watermark -1. At slot t events occur in this order: volatile resets; the origin sets its watermark to t; packet arrivals, merged by maximum; queries; predetermined sends. An as-of watermark certifies a complete authoritative snapshot including deletions and no-change confirmation. It is not the time of the last application update. Packets retain their captured send-time payload through subsequent sender and receiver resets. Resets are instantaneous erasure and rejoin, not periods of unavailability. All sends are fixed independently of execution, and all messages are delivered exactly once.

A message m=(u,v,s,[a,b]) is sent at s and arrives at one independently chosen integer in [a,b], with 0 <= s < a <= b <= H. A query is a node-time pair. A batch returns the maximum of its queried watermarks, with -1 a failed answer rather than permissible abstention. Given a cutoff c >= 0, a reset pattern R is safe when every legal arrival assignment produces a batch answer >= c. For queries at q this is an age bound B=q-c. Known mandatory resets F and selectable candidate resets C are disjoint; only additional resets S subset C count against the optional budget. Neither set contains origin resets or time-zero resets.

## 1. Postponement within a receiver epoch

Fix a reset pattern and the arrival times of every packet. Move one packet's arrival from d to d' >= d, with no receiver reset in (d,d']. The modified execution has no larger watermark at any node and time. Before d the executions agree. The moved packet has the same payload because its send precedes d. Between d and d', omitting that arrival cannot increase any watermark: all resets are the same, all other arrivals carry payloads that are no larger by induction, and merge is maximum. At d' the original receiver still has a watermark at least as large as the moved packet's payload: it received that payload at d and had no intervening reset. Consequently adding the postponed arrival does not invalidate the comparison. The same induction continues afterward. This argument also covers cyclic physical overlays because every packet has strictly positive transmission time.

Sequentially apply this argument to each packet. Every execution has an execution with no larger query result in which every packet arrives at its upper endpoint b or at tau-1 immediately before some receiver reset tau. More precisely, replace its arrival d by min(b, next_receiver_reset_after_d - 1). This stays within [a,b] and the same reset-free epoch. Previously postponed packets can have smaller payloads after subsequent moves, but their arrival times remain canonical and the pointwise inequality remains valid. Thus an unsafe execution always has a canonical unsafe execution.

A global "all latest arrivals" test is false. With one origin packet sent at 0, arrival in [1,2], a receiver reset at 2 and query at 2, arrival 1 is erased and arrival 2 survives. The event order is essential.

## 2. A common endpoint representation

At node v retain time 0, every send time at v, every query time at v, the upper endpoint of every incoming message, and tau-1 and tau for every mandatory or eligible reset (v,tau). Let P_v be this sorted set and K=sum_v |P_v|. K=O(n+m+|Q|+|F|+|C|). For a message to v use the finite arrival set P_v intersect [a,b]. It is nonempty since b belongs to P_v. These finite sets contain all canonical choices for every S subset C. Restricting choices can only make universal safety easier, whereas the postponement lemma supplies a restricted counterexample to any unrestricted failure. Therefore the restriction is exact, simultaneously for all eligible reset patterns.

Join consecutive points (v,p),(v,t) by a memory edge precisely when there is no actual reset in (p,t]. This exactly preserves watermark propagation at retained event times under the restricted choices. Unretained slots contain no relevant send, query, selected reset, or restricted arrival. At the origin only retained source times need to be considered, since all source sends are retained and injection between source sends cannot reach another node.

The bound counts explicit eligible events. It does not turn a symbolic permission to reset at every one of H slots into an O(log H) input. With explicit input, time arithmetic and comparisons use O(log H) bits; the stated operation bounds are word-operation bounds, not constant-bit bounds.

## 3. Least stale closure

Start a marked set M with all queried point states. Apply these implications until no new point can be marked:

* If a later retained point is marked and its preceding memory edge is intact, mark that predecessor.
* For a message, if every retained allowed arrival point is marked, mark its send point.

Then safety is equivalent to M containing some origin state (0,t) with t >= c.

Necessity of the implications: By the common endpoint reduction in §2, any failed execution has a failed execution whose arrivals are retained points. Work with this restricted execution. All queried states are stale. An intact memory edge implies that a stale later state has a stale predecessor. If all possible heads of a packet are stale, its actual arrival head is stale, and hence its send payload was stale. Accordingly the least closure is contained in the actual stale states and cannot meet a fresh origin state.

Sufficiency of failure: Suppose the closure misses every fresh origin state. For every message whose send point is unmarked, at least one permitted head is unmarked; choose such a head. For messages with a marked send point choose any permitted head. This specifies one simultaneous arrival assignment, not different assignments for different queries or paths. Forward induction shows that no marked point becomes fresh. Fresh origin injections are unmarked. If an intact memory edge entered a marked point from an unmarked predecessor, the predecessor rule would have marked it. If a packet from an unmarked send point entered a marked point, it would contradict the selected unmarked head. Packets from marked sends carry stale payloads. A reset injects -1. All queries remain stale, establishing a legal failed execution.

The expanded implementation takes O(nH + sum_m (b_m-a_m+1)) space and work using counters. This generic Horn worklist is not claimed as a new algorithmic primitive.

## 4. Range-AND certificates

Construct a balanced binary range tree over each P_v. A leaf means its point is marked; an internal tree node means both children are marked. Every message interval is the disjoint union of O(log K) tree ranges; their conjunction implies the send leaf. Memory implications and query seeds are added unchanged. There are O(K + m log K) rule incidences. A counter-based worklist visits each incidence once. Sorting and locating endpoints give O((K+m) log K) word operations and O(K+m log K) space, independent of the numerical interval widths.

A positive certificate needs at most K base-point entries. Each entry is justified by a query, an already marked memory successor with no intervening actual reset, or a message whose retained head range is entirely already marked. Tree nodes need not be included. End at a fresh origin point. A separate verifier can regenerate point sets and use a Fenwick marked-count tree to validate range premises. It need not implement the certifier's Horn graph. A negative certificate gives all arrival times and selected resets; an independently implemented forward scalar replay checks it. These two code paths are independent implementations inside one artifact, not independent human review. The instance, cutoff and requested reset statement must be supplied independently of the certificate. A fixed-pattern check binds the selected optional set; an aggregate check binds the exact cardinality or rolling rule. Checking only a packet's self-described rule proves that rule, not a caller's possibly stronger request.

## 5. Fixed arrivals, optional reset minimization

When each arrival interval is a singleton, use the compressed forward event graph. Remove mandatory-reset memory edges. An eligible reset corresponds to its memory edge from tau-1 to tau, with capacity 1. All other memory edges and message edges have capacity |C|+1. Connect a supersource to each origin point t >= c and every query point to a supersink with that same large capacity. A minimum cut below |C|+1 consists only of eligible memory edges and gives a smallest-cardinality optional reset set that makes every query stale. Conversely any such erasure pattern disconnects the source and sink, so its edges contain a cut. If the cut has capacity at least |C|+1, no eligible erasure pattern suffices. This is an application of the standard max-flow/min-cut theorem. It does not solve rolling-window constraints or shared-cost node failures.

## 6. Interval arrivals: a constant-horizon hardness boundary

UNSAFE asks whether some S subset C with |S| <= k and some legal arrival assignment make the batch stale. It is in NP: a reset list and one binary-encoded arrival per message have polynomial length, and an event-sorted simulator checks the execution in polynomial time.

Reduce Vertex Cover on a simple graph G=(U,E). Create origin o; one switch x_e for each edge e={u,v}, oriented by a fixed ordering; one replica r_v per vertex; and observer z. For each edge add o->x_e sent at 0 with arrivals [1,2], a mandatory reset of x_e at 2, x_e->r_u sent at 1 and delivered at 3, and x_e->r_v sent at 2 and delivered at 3. For each vertex permit the sole optional reset (r_v,4) and add r_v->z sent at 5 and delivered at 6. Query z at 6 with c=0.

Early arrival at x_e forwards a fresh watermark only to r_u; reset at 2 erases it before the send to r_v. Late arrival occurs after that reset and forwards a fresh watermark only to r_v. Thus each edge independently chooses one endpoint to freshen. A failed query requires every freshened replica to be reset, and the selected reset vertices therefore cover every graph edge. Conversely, a vertex cover chooses a covered endpoint of every edge; the matching early/late arrivals and resets erase every fresh payload before the replica sends. The reduction preserves the minimum optional reset count exactly.

There are n'=|U|+|E|+2 nodes, 3|E|+|U| messages, |E| mandatory resets and |U| optional candidates. H=6, maximum transmission delay 2, a three-hop acyclic physical overlay, and only the origin-switch messages have two choices. Hence UNSAFE is NP-complete and safety is coNP-complete even in this class. The theorem explicitly includes the supplied mandatory reset profile; it makes no hardness claim for an empty mandatory profile. The combinatorial reduction source and use of cut constructions are standard, not themselves novelty claims.

Adding resets cannot increase any watermark for fixed arrival times under the stated durable-packet, fixed-send semantics. Thus for a downward-closed eligible family, testing its inclusion-maximal reset sets suffices for universal safety. A positive global certificate can enumerate those sets with a positive derivation for each. The verifier must check coverage of the family, not just correctness of the listed derivations. This may be exponential, consistent with the hardness theorem. Searching legal sets in increasing cardinality gives a minimum-number-of-resets negative certificate; it is not a shortest-time or shortest-event trace.

## 7. Periodic finite-window reduction

Assume sends, mandatory resets, query phases, and optional reset eligibility repeat with period P. Delay intervals are translated with sends and their upper delay is at most D. Optional resets satisfy a translation-invariant rolling constraint: at most b resets in every W consecutive slots. Consider query q with cutoff c=q-B >=0.

No packet sent before c can contain a watermark >=c, since every watermark is at most its generation/send time. Also no nonorigin node is fresh immediately before slot c. For this one threshold, discard older history and initialize every nonorigin fresh bit to false at c. All older in-flight packets carry false and cannot change a maximum/OR threshold state. Only sends at or after c and their descendants can matter. This yields an exact window from c to q. Arrival intervals must retain possible arrivals after q; forcing such packets to arrive by q would change the theorem. It suffices to represent through q+D. With the reset event order, a reset at c changes no fresh bit and may be omitted.

There are only P distinct translated windows of length B. The restriction of a globally legal optional reset schedule to a window is legal. Conversely a legal finite reset pattern extends by no optional resets outside the window: removing resets cannot violate an upper rolling bound. Mandatory resets follow their fixed periodic profile and are not charged to that optional bound. Consequently all sufficiently late periodic queries satisfy age B if and only if every one of these P windows is safe under all legal optional patterns. The implication holds for all q>=B for a schedule starting at time 0 with empty nonorigin state and sends defined at nonnegative times. A phase not occurring yet is tested at a later q with the same relative window.

## 8. Exact direct-replica packing condition

Consider only messages from the origin directly to replicas, a simultaneous query of all replicas at q, no mandatory resets, and optional resets allowed at every replica and every slot 1..q. At most b>=1 resets may occur in every W>=1 consecutive slots. For cutoff c, call an incoming message deadline-forced and fresh when s>=c and b_m<=q. A replica with no such message can be stale without a reset: any other fresh message can be delayed past q.

For each remaining replica v define R_v=1+max a_m over its deadline-forced fresh messages. A last reset at tau can erase all its fresh deadline-forced arrivals exactly when R_v<=tau<=q. Necessity: each such arrival must precede the last reset, hence a_m<tau. Sufficiency: choose those arrivals at their lower endpoints and other fresh arrivals after q. One last reset per active replica suffices; deleting any earlier resets can only help the budget. Older payloads remain below c.

Sort the k releases R_1>=...>=R_k. A stale execution exists exactly when

    R_j <= q - W floor((j-1)/b), for every 1<=j<=k.                 (S)

To prove this, sort all required reset times latest first. The rolling constraint is t_i-t_{i+b}>=W. Since t_1,...,t_b<=q, induction gives t_j<=q-W floor((j-1)/b). Assigning larger release times to later slots is without loss: exchanging an inverted pair preserves feasibility. Thus (S) is necessary. It is sufficient by assigning resets at q (b of them), q-W (the next b), and so on. These slots meet every rolling bound. All release times are at least 2, so an assignment satisfying (S) is within the allowed nonnegative horizon. The empty collection has a stale execution. Therefore safety is equivalent to at least one violated packing inequality.

For one source refresh to each replica per period P, phase theta_v, and delay interval [1,D], let

    a_v(q)=D+((q-D-theta_v) mod P).

At a sufficiently late query these are the ages of the latest deadline-forced source sends. Sort a_(1)<=...<=a_(r). Replica j is active precisely when a_(j)<=B and its release is q-a_(j)+2. Substitution into (S) gives safety exactly when some j satisfies

    a_(j) <= B  and  a_(j) <= 1 + W floor((j-1)/b).               (P)

The least qualifying age is the exact minimum B for that phase. If no j qualifies, no finite B works at all sufficiently late queries of that phase: even all replicas' received information can be erased within the rolling budget. The period-wide bound is the maximum of the phase bounds, with infinity if any phase has none. This infinity conclusion follows from the formula, not a finite search cap. Exhaustive phase optimization below is only within this fixed one-refresh-per-replica, common-period class, not optimal protocol synthesis.

## 9. A necessary replica count for finite direct-refresh age

For positive integers P,D,b,W and r replicas under the common-period assumptions of §8, every latest-forced age is at least D. The largest rank threshold in condition (P) is 1+W floor((r-1)/b). Thus a necessary condition for any finite period-wide age bound is r >= 1+b ceil((D-1)/W). If the inequality fails, no rank qualifies at any phase, even with all replicas active; the packing witness then works for every sufficiently late finite cutoff window. This is not a sufficient condition for an arbitrary phase vector. For example, P=3,D=2,b=1,W=1 and phases (0,0) pass the count inequality but have a query phase with no qualifying rank. Every finite age bound is at least D. This is an algebraic consequence of the proved phase formula, not a new empirical hypothesis.
