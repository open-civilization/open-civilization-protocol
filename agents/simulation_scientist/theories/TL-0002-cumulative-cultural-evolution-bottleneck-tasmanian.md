# TL-0002: Cumulative cultural evolution bottleneck / Tasmanian effect

**Citation:** Henrich, J. (2004). Demography and cultural evolution: why adaptive cultural systems can be maladaptive. American Antiquity, 69(2), 197-214.

**Domain:** anthropology / cultural evolution

**Prediction:** When population size falls below a critical threshold (typically ~250–300 individuals), the pool of knowledgeable individuals becomes too small to maintain complex, multi-step skills, leading to a net loss of adaptive cultural traits over time, even if the population later recovers.

**Discovered:** 2026-07-04T10:47:53.311734+00:00

## Write-up

**Cumulative Cultural Evolution Bottleneck (Tasmanian effect)** — Joseph Henrich (2004)

This theory, rooted in anthropology and cultural evolution, posits that the maintenance of complex, multi-step skills (e.g., tool-making, fire control, agriculture) depends critically on the size of the population of practitioners. Henrich demonstrated that when small populations experience even temporary bottlenecks (below ~40 individuals) or remain persistently small (below ~250–300), the fidelity of social learning degrades, and adaptive skills can be lost forever—even if the population later recovers. The classic empirical example is Tasmania, where isolation and small population size led to the loss of bone tools, fishing gear, and other complex technologies.

**Why this applies:** In this simulation, the agents acquire and transmit skills (knowledge_holders, language_holders, writing_holders, etc.) through social learning. The simulation already tracks skill holders per tick. If the population ever dips below a critical threshold (approx. 40 individuals, as per Henrich's analysis), the transmission chain can break: the few remaining experts die before passing on their full repertoire, and subsequent generations cannot reinvent the skills because they require cumulative knowledge. Even without a crash, if the population stays too small for too long, skill diversity erodes.

**What a confirming vs. disconfirming observation looks like:** A confirming observation would be a run where the population bottlenecked below 40 and, in the tail, one or more skills (e.g., writing, fire maintenance) dropped to zero holders, despite the population later recovering to >200. A disconfirming observation would show that after a bottleneck, all previously held skills are still present (no loss) or that they are lost but later reacquired through independent innovation—which would conflict with the theory's claim that loss is irreversible without external input. The current data shows a run with 274 peak population but no bottleneck mentioned; however, the average population may mask transient dips. The final state may reveal that certain skills are absent even though the population is large, pointing to a past bottleneck erased from the summary view.

## Implementation

```python
def _henrich_demographic_cultural_loss_compare(history, state):
    # Extract skill/knowledge holders per tick
    holders_keys = ['knowledge_holders', 'language_holders', 'writing_holders',
                    'shelter_holders', 'clothing_holders', 'fire_holders']
    # Check maximum holders for each skill across all ticks
    max_holders = {k: 0 for k in holders_keys}
    for row in history:
        for k in holders_keys:
            v = row.get(k, 0)
            if v is not None and v > max_holders[k]:
                max_holders[k] = v
    # Identify skills ever held by fewer than 5 individuals (critical loss risk)
    at_risk_skills = [k for k, v in max_holders.items() if v < 5]
    # Check that at the final tick, for any skill that ever had >=5 holders,
    # it still has >=5 holders
    final = history[-1]
    lost_skills = []
    for k in holders_keys:
        if max_holders.get(k, 0) >= 5:
            final_v = final.get(k, 0)
            if final_v is None or final_v < 5:
                lost_skills.append(k)
    # Also check that number of distinct skills held > 0 is not declining in the tail
    # (we define tail as last 20% of ticks)
    n = len(history)
    tail_start = int(n * 0.8)
    tail_ticks = history[tail_start:]
    first_tail = tail_ticks[0] if tail_ticks else {}
    last_tail = tail_ticks[-1] if tail_ticks else {}
    count_first = sum(1 for k in holders_keys if first_tail.get(k, 0) and first_tail[k] > 0)
    count_last = sum(1 for k in holders_keys if last_tail.get(k, 0) and last_tail[k] > 0)
    # Also check if population ever fell below 40 (critical threshold from Henrich)
    min_pop = min(row.get('pop', 999999) for row in history)
    population_bottleneck = min_pop < 40
    if population_bottleneck and count_last < count_first:
        return TheoryFinding(
            theory="Demographic cultural loss (Tasmanian effect)",
            citation="Henrich, J. (2004). Demography and cultural evolution. American Antiquity, 69(2), 197-214.",
            prediction="Complex skills should be maintained once acquired if population remains above ~40, but may be lost irreversibly after a population bottleneck below that threshold.",
            observed={
                "lost_skills": lost_skills,
                "first_tail_skill_count": count_first,
                "last_tail_skill_count": count_last,
                "minimum_population": min_pop,
                "population_bottleneck_detected": population_bottleneck
            },
            gap=f"Population fell to {min_pop} (below Henrich's ~40 threshold) and {count_last - count_first} skills were lost in the tail, indicating irreversible cultural loss despite later recovery.",
            severity="high",
            suggested_investigation="min_viable_pop_for_skill_transmission, skill_complexity_metrics"
        )
    # Even without a bottleneck, check monotonicity in tail
    if count_last < count_first - 1:  # loss of 2 or more skills
        return TheoryFinding(
            theory="Demographic cultural loss (Tasmanian effect)",
            citation="Henrich, J. (2004). Demography and cultural evolution. American Antiquity, 69(2), 197-214.",
            prediction="Complex skills should be stable or increase over time once acquired, unless population experiences a severe bottleneck.",
            observed={
                "first_tail_skill_count": count_first,
                "last_tail_skill_count": count_last,
                "minimum_population": min_pop,
                "lost_skills": lost_skills
            },
            gap=f"In the last 20% of ticks, the number of maintained skills dropped from {count_first} to {count_last} without a known population crash. This suggests cumulative cultural loss.",
            severity="medium",
            suggested_investigation="skill_loss_event_timing, social_network_connectivity"
        )
    return None
```
