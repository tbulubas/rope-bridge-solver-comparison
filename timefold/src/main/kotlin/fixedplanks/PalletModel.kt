// Copyright (c) 2026 Taras Bulubas. All rights reserved.
// Use requires prior written permission; see LICENSE.

package fixedplanks

import ai.timefold.solver.core.api.domain.common.PlanningId
import ai.timefold.solver.core.api.domain.entity.PlanningEntity
import ai.timefold.solver.core.api.domain.solution.PlanningEntityCollectionProperty
import ai.timefold.solver.core.api.domain.solution.PlanningScore
import ai.timefold.solver.core.api.domain.solution.PlanningSolution
import ai.timefold.solver.core.api.domain.solution.ProblemFactCollectionProperty
import ai.timefold.solver.core.api.domain.valuerange.ValueRangeProvider
import ai.timefold.solver.core.api.domain.variable.PlanningVariable
import ai.timefold.solver.core.api.score.HardMediumSoftScore
import ai.timefold.solver.core.api.score.stream.Constraint
import ai.timefold.solver.core.api.score.stream.ConstraintFactory
import ai.timefold.solver.core.api.score.stream.ConstraintProvider
import ai.timefold.solver.core.api.score.stream.Joiners

// Model "pallets": every candidate pallet is a planning entity and the solver
// decides whether it is laid in lane 1, in lane 2 or not at all.
//
//   hard    pallets of one lane do not overlap
//   medium  every gap of every lane is covered; joints of the two lanes do not
//           lie on the same interior plank
//   soft    number of pallets

const val STAGGER_WEIGHT = 1000L

@PlanningEntity
class PalletChoice() {
    @PlanningId
    var id: Int = 0
    var start: Int = 0
    var end: Int = 0
    var startsInside: Boolean = false
    var endsInside: Boolean = false

    @PlanningVariable(allowsUnassigned = true)
    var lane: Int? = null

    constructor(id: Int, start: Int, end: Int, last: Int) : this() {
        this.id = id
        this.start = start
        this.end = end
        startsInside = start > 0
        endsInside = end < last
    }
}

/** Gap `index` (between planks index − 1 and index) of one lane. */
class LaneGap(val lane: Int, val index: Int, val length: Long)

@PlanningSolution
class PalletSolution() {
    @ProblemFactCollectionProperty
    @ValueRangeProvider
    var lanes: List<Int> = listOf(1, 2)

    @ProblemFactCollectionProperty
    var gaps: List<LaneGap> = emptyList()

    @PlanningEntityCollectionProperty
    var pallets: List<PalletChoice> = emptyList()

    @PlanningScore
    var score: HardMediumSoftScore? = null

    constructor(instance: Instance) : this() {
        gaps = lanes.flatMap { lane ->
            (1..instance.last).map { k -> LaneGap(lane, k, (instance.planks[k] - instance.planks[k - 1]).toLong()) }
        }
        pallets = instance.candidates().mapIndexed { id, (a, b) -> PalletChoice(id, a, b, instance.last) }
    }

    fun plan(): Plan = Plan(
        pallets.filter { it.lane == 1 }.map { it.start to it.end },
        pallets.filter { it.lane == 2 }.map { it.start to it.end },
    )
}

class PalletConstraints : ConstraintProvider {

    override fun defineConstraints(factory: ConstraintFactory): Array<Constraint> = arrayOf(
        overlap(factory),
        uncoveredGap(factory),
        jointsOnEnds(factory),
        jointsOnStarts(factory),
        jointsOnEndAndStart(factory),
        palletCount(factory),
    )

    private fun overlap(factory: ConstraintFactory): Constraint =
        factory.forEachUniquePair(
            PalletChoice::class.java,
            Joiners.equal { p: PalletChoice -> p.lane },
            Joiners.overlapping({ p: PalletChoice -> p.start }, { p: PalletChoice -> p.end }),
        )
            .penalize(HardMediumSoftScore.ONE_HARD)
            .asConstraint("Pallets of one lane overlap")

    private fun uncoveredGap(factory: ConstraintFactory): Constraint =
        factory.forEach(LaneGap::class.java)
            .ifNotExists(
                PalletChoice::class.java,
                Joiners.equal({ g: LaneGap -> g.lane }, { p: PalletChoice -> p.lane }),
                Joiners.greaterThan({ g: LaneGap -> g.index }, { p: PalletChoice -> p.start }),
                Joiners.lessThanOrEqual({ g: LaneGap -> g.index }, { p: PalletChoice -> p.end }),
            )
            .penalize(HardMediumSoftScore.ONE_MEDIUM) { g -> g.length }
            .asConstraint("Gap is not covered")

    private fun jointsOnEnds(factory: ConstraintFactory): Constraint =
        factory.forEach(PalletChoice::class.java)
            .filter { p -> p.lane == 1 && p.endsInside }
            .join(
                PalletChoice::class.java,
                Joiners.equal({ p: PalletChoice -> p.end }, { q: PalletChoice -> q.end }),
                Joiners.filtering { _: PalletChoice, q: PalletChoice -> q.lane == 2 },
            )
            .penalize(HardMediumSoftScore.ONE_MEDIUM) { _, _ -> STAGGER_WEIGHT }
            .asConstraint("Both lanes end a pallet on the same plank")

    private fun jointsOnStarts(factory: ConstraintFactory): Constraint =
        factory.forEach(PalletChoice::class.java)
            .filter { p -> p.lane == 1 && p.startsInside }
            .join(
                PalletChoice::class.java,
                Joiners.equal({ p: PalletChoice -> p.start }, { q: PalletChoice -> q.start }),
                Joiners.filtering { _: PalletChoice, q: PalletChoice -> q.lane == 2 },
            )
            .penalize(HardMediumSoftScore.ONE_MEDIUM) { _, _ -> STAGGER_WEIGHT }
            .asConstraint("Both lanes start a pallet on the same plank")

    private fun jointsOnEndAndStart(factory: ConstraintFactory): Constraint =
        factory.forEach(PalletChoice::class.java)
            .filter { p -> p.endsInside }
            .join(
                PalletChoice::class.java,
                Joiners.equal({ p: PalletChoice -> p.end }, { q: PalletChoice -> q.start }),
                Joiners.filtering { p: PalletChoice, q: PalletChoice -> p.lane != q.lane },
            )
            .penalize(HardMediumSoftScore.ONE_MEDIUM) { _, _ -> STAGGER_WEIGHT }
            .asConstraint("One lane ends and the other starts a pallet on the same plank")

    private fun palletCount(factory: ConstraintFactory): Constraint =
        factory.forEach(PalletChoice::class.java)
            .penalize(HardMediumSoftScore.ONE_SOFT)
            .asConstraint("Pallet is laid")
}
