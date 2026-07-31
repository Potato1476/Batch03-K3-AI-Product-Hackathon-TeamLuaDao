package com.chan.app

import com.chan.app.data.ThemePreferenceStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * In-memory [ThemePreferenceStore] whose backing map can be shared across
 * instances to model persistence surviving process recreation.
 */
class FakeThemePreferenceStore(
    private val backing: MutableMap<String, Boolean> = mutableMapOf(),
) : ThemePreferenceStore {

    private val flow = MutableStateFlow(backing[KEY] ?: false)

    override val darkMode: Flow<Boolean> = flow.asStateFlow()

    override suspend fun setDarkMode(enabled: Boolean) {
        backing[KEY] = enabled
        flow.value = enabled
    }

    val current: Boolean get() = flow.value

    private companion object {
        const val KEY = "dark_mode"
    }
}
