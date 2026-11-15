// Copyright (c) 2026 Taras Bulubas. All rights reserved.
// Use requires prior written permission; see LICENSE.

package fixedplanks

import ai.timefold.solver.core.api.score.HardMediumSoftScore
import ai.timefold.solver.core.api.solver.SolverFactory
import ai.timefold.solver.core.config.solver.EnvironmentMode
import ai.timefold.solver.core.config.solver.SolverConfig
import ai.timefold.solver.core.config.solver.termination.TerminationConfig
import java.io.File
import kotlin.system.exitProcess

// Solves one instance with one of the two Timefold models and writes the
// result as one JSON object:
//
//   --instance FILE   instance written by the Python package
//   --model NAME      pallets | joints
//   --seconds N       time limit (default 10)
//   --target N        stop as soon as a valid plan with N pallets is found
//   --seed N          random seed (default 0)
//   --out FILE        write the JSON there instead of standard output

private class Run<S : Any>(
    val solutionClass: Class<S>,
    val entityClass: Class<*>,
    val constraints: Class<out ai.timefold.solver.core.api.score.stream.ConstraintProvider>,
    val problem: S,
    val score: (S) -> HardMediumSoftScore,
    val plan: (S) -> Plan,
    /** Soft score of a valid plan with the given number of pallets. */
    val softOf: (Int) -> Int,
    val palletsOf: (Long) -> Long,
)

fun main(args: Array<String>) {
    val options = args.toList().chunked(2).associate { it[0] to it.getOrElse(1) { "" } }
    val instancePath = options["--instance"] ?: usage()
    val seconds = (options["--seconds"] ?: "10").toDouble()
    val seed = (options["--seed"] ?: "0").toLong()
    val target = options["--target"]?.toInt()
    val instance = Instance.load(instancePath)

    val run: Run<*> = when (val model = options["--model"] ?: "pallets") {
        "pallets" -> Run(
            PalletSolution::class.java, PalletChoice::class.java, PalletConstraints::class.java,
            PalletSolution(instance), { it.score!! }, { it.plan() }, { -it }, { -it },
        )
        "joints" -> Run(
            JointSolution::class.java, JointSlot::class.java, JointConstraints::class.java,
            JointSolution(instance), { it.score!! }, { it.plan() }, { -(it - 2) }, { -it + 2 },
        )
        else -> {
            System.err.println("unknown model $model")
            exitProcess(2)
        }
    }
    val json = solve(run, seconds, seed, target)
    val out = options["--out"]
    if (out != null) File(out).writeText(json + "\n") else println(json)
    exitProcess(0)
}

private fun <S : Any> solve(run: Run<S>, seconds: Double, seed: Long, target: Int?): String {
    val termination = TerminationConfig().withMillisecondsSpentLimit((seconds * 1000).toLong())
    if (target != null) termination.withBestScoreLimit("0hard/0medium/${run.softOf(target)}soft")
    val config = SolverConfig()
        .withSolutionClass(run.solutionClass)
        .withEntityClasses(run.entityClass)
        .withConstraintProviderClass(run.constraints)
        .withEnvironmentMode(EnvironmentMode.NO_ASSERT)
        .withRandomSeed(seed)
        .withTerminationConfig(termination)
    val solver = SolverFactory.create<S>(config).buildSolver()

    var firstValidMillis = -1L
    var bestMillis = -1L
    solver.addEventListener { event ->
        val score = event.newBestScore as HardMediumSoftScore
        bestMillis = event.timeMillisSpent
        if (firstValidMillis < 0 && score.hardScore() == 0L && score.mediumScore() == 0L) {
            firstValidMillis = event.timeMillisSpent
        }
    }
    val started = System.nanoTime()
    val best = solver.solve(run.problem)
    val solveMillis = (System.nanoTime() - started) / 1_000_000
    val score = run.score(best)
    val valid = score.hardScore() == 0L && score.mediumScore() == 0L
    val pallets = if (valid) run.palletsOf(score.softScore()) else -1
    return "{\"status\": \"${if (valid) "feasible" else "unknown"}\", \"score\": \"$score\", " +
        "\"pallets\": $pallets, \"solve_ms\": $solveMillis, \"first_valid_ms\": $firstValidMillis, " +
        "\"best_ms\": $bestMillis, ${run.plan(best).json()}}"
}

private fun usage(): Nothing {
    System.err.println(
        "usage: --instance FILE [--model pallets|joints] [--seconds N] [--target N] [--seed N] [--out FILE]"
    )
    exitProcess(2)
}
