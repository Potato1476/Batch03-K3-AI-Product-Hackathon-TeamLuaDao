package com.chan.app

import com.chan.app.domain.Risk
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class RiskModelTest {

    @Test
    fun riskModelHasNoSafeState() {
        val names = Risk.entries.map { it.name }.toSet()
        assertEquals(setOf("HIGH", "MEDIUM", "UNKNOWN"), names)

        // Explicitly assert there is no SAFE-like value.
        assertTrue("Risk must never contain a SAFE state", names.none { it.contains("SAFE") })
    }

    @Test(expected = IllegalArgumentException::class)
    fun safeValueDoesNotExist() {
        Risk.valueOf("SAFE")
    }
}
