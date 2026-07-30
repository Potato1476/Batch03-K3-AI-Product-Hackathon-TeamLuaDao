package com.chan.app

import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ThemePreferenceStoreTest {

    @Test
    fun darkModePreferenceSurvivesRecreation() = runTest {
        val backing = mutableMapOf<String, Boolean>()

        // First "process": user turns dark mode on.
        val first = FakeThemePreferenceStore(backing)
        assertFalse("Defaults to light", first.current)
        first.setDarkMode(true)
        assertTrue(first.current)

        // Recreate the store over the same persisted backing (process restart).
        val second = FakeThemePreferenceStore(backing)
        assertTrue("Dark-mode preference must survive recreation", second.current)

        // And turning it back off persists too.
        second.setDarkMode(false)
        val third = FakeThemePreferenceStore(backing)
        assertFalse(third.current)
    }
}
