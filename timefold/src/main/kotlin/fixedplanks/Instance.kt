// Copyright (c) 2026 Taras Bulubas. All rights reserved.
// Use requires prior written permission; see LICENSE.

package fixedplanks

import java.io.File

/** Input data of a rope bridge with fixed planks, as written by the Python package. */
class Instance(val planks: IntArray, val minPallet: Int, val maxPallet: Int) {

    val last: Int get() = planks.size - 1

    /** Candidate pallets (a, b): planks a < b at a distance in [m, M]. */
    fun candidates(): List<Pair<Int, Int>> {
        val pallets = ArrayList<Pair<Int, Int>>()
        for (a in 0 until last) {
            for (b in a + 1..last) {
                val span = planks[b] - planks[a]
                if (span > maxPallet) break
                if (span >= minPallet) pallets.add(a to b)
            }
        }
        return pallets
    }

    companion object {
        /** Reads {"planks": [...], "min_pallet": m, "max_pallet": M}. */
        fun load(path: String): Instance {
            val text = File(path).readText()
            val planks = Regex("\"planks\"\\s*:\\s*\\[([^\\]]*)]").find(text)!!.groupValues[1]
                .split(",").map { it.trim().toInt() }.toIntArray()
            fun number(key: String) = Regex("\"$key\"\\s*:\\s*(\\d+)").find(text)!!.groupValues[1].toInt()
            return Instance(planks, number("min_pallet"), number("max_pallet"))
        }
    }
}

/** A plan as two lanes of pallets (start plank, end plank). */
class Plan(val left: List<Pair<Int, Int>>, val right: List<Pair<Int, Int>>) {
    private fun lane(pallets: List<Pair<Int, Int>>) =
        pallets.sortedBy { it.first }.joinToString(", ", "[", "]") { "[${it.first}, ${it.second}]" }

    fun json(): String = "\"left\": ${lane(left)}, \"right\": ${lane(right)}"
}
