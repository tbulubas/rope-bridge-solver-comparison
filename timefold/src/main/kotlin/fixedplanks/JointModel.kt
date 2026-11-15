// Copyright (c) 2026 Taras Bulubas. All rights reserved.
// Use requires prior written permission; see LICENSE.

package fixedplanks

import ai.timefold.solver.core.api.domain.common.PlanningId
import ai.timefold.solver.core.api.domain.entity.PlanningEntity
import ai.timefold.solver.core.api.domain.entity.PlanningPin
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

// Model "joints": one planning entity per lane and plank, and the solver
// decides whether the lane has a joint there. A lane is then covered without
// holes and overlaps by construction: its pallets run from joint to joint.
//
//   hard    consecutive joints of a lane are m to M apart, penalised by the
//           missing or excess millimetres so that every step towards a
//           valid pallet length improves the score; joints of the two lanes
//           do not lie on the same interior plank, penalised like a pallet
//           that is STAGGER_WEIGHT millimetres too long
//   soft    number of joints (pallets = interior joints + 2)
//
// The medium level stays empty; the score type is shared with the pallet model.

@PlanningEntity
class JointSlot() {
    @PlanningId
    var id: Int = 0
    var lane: Int = 0
    var plank: Int = 0
    var position: Int = 0
    var isLast: Boolean = false
    var minPallet: Int = 0
    var maxPallet: Int = 0

    /** The anchored planks always carry a joint. */
    @PlanningPin
    var anchored: Boolean = false

    @PlanningVariable
    var joint: Boolean? = null

    constructor(id: Int, lane: Int, plank: Int, instance: Instance) : this() {
        this.id = id
        this.lane = lane
        this.plank = plank
        position = instance.planks[plank]
        isLast = plank == instance.last
        minPallet = instance.minPallet
        maxPallet = instance.maxPallet
        anchored = plank == 0 || isLast
        if (anchored) joint = true
    }
}

@PlanningSolution
class JointSolution() {
    @ProblemFactCollectionProperty
    @ValueRangeProvider
    var choices: List<Boolean> = listOf(false, true)

    @PlanningEntityCollectionProperty
    var slots: List<JointSlot> = emptyList()

    @PlanningScore
    var score: HardMediumSoftScore? = null

    constructor(instance: Instance) : this() {
        var id = 0
        slots = listOf(1, 2).flatMap { lane -> (0..instance.last).map { j -> JointSlot(id++, lane, j, instance) } }
    }

    fun plan(): Plan {
        fun lane(lane: Int) = slots.filter { it.lane == lane && it.joint == true }.map { it.plank }.sorted()
            .zipWithNext()
        return Plan(lane(1), lane(2))
    }
}

class JointConstraints : ConstraintProvider {

    override fun defineConstraints(factory: ConstraintFactory): Array<Constraint> = arrayOf(
        palletLength(factory),
        staggering(factory),
        jointCount(factory),
    )

    private fun joints(factory: ConstraintFactory) =
        factory.forEach(JointSlot::class.java).filter { s -> s.joint == true }

    /** Consecutive joints a < b of a lane: no joint of the lane lies between them. */
    private fun palletLength(factory: ConstraintFactory): Constraint =
        joints(factory)
            .join(
                joints(factory),
                Joiners.equal({ a: JointSlot -> a.lane }, { b: JointSlot -> b.lane }),
                Joiners.lessThan({ a: JointSlot -> a.position }, { b: JointSlot -> b.position }),
            )
            .filter { a, b -> b.position - a.position !in a.minPallet..a.maxPallet }
            .ifNotExists(
                joints(factory),
                Joiners.equal({ a: JointSlot, _: JointSlot -> a.lane }, { c: JointSlot -> c.lane }),
                Joiners.lessThan({ a: JointSlot, _: JointSlot -> a.position }, { c: JointSlot -> c.position }),
                Joiners.greaterThan({ _: JointSlot, b: JointSlot -> b.position }, { c: JointSlot -> c.position }),
            )
            .penalize(HardMediumSoftScore.ONE_HARD) { a, b ->
                val length = b.position - a.position
                (if (length > a.maxPallet) length - a.maxPallet else a.minPallet - length).toLong()
            }
            .asConstraint("Pallet length outside the limits")

    private fun staggering(factory: ConstraintFactory): Constraint =
        joints(factory)
            .filter { a -> a.lane == 1 && !a.anchored }
            .join(
                joints(factory),
                Joiners.equal({ a: JointSlot -> a.plank }, { b: JointSlot -> b.plank }),
                Joiners.filtering { _: JointSlot, b: JointSlot -> b.lane == 2 },
            )
            .penalize(HardMediumSoftScore.ONE_HARD) { _, _ -> STAGGER_WEIGHT }
            .asConstraint("Joints of both lanes on the same plank")

    private fun jointCount(factory: ConstraintFactory): Constraint =
        joints(factory)
            .filter { a -> !a.anchored }
            .penalize(HardMediumSoftScore.ONE_SOFT)
            .asConstraint("Joint")
}
