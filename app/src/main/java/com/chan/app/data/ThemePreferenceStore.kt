package com.chan.app.data

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

/**
 * Persists the user's dark-mode choice. Abstracted behind an interface so the
 * persistence contract can be exercised without an Android device.
 */
interface ThemePreferenceStore {
    /** Emits the persisted dark-mode preference, defaulting to false. */
    val darkMode: Flow<Boolean>

    /** Persists the dark-mode preference. */
    suspend fun setDarkMode(enabled: Boolean)
}

private val Context.themeDataStore: DataStore<Preferences> by preferencesDataStore(name = "chan_theme")

/** DataStore-backed implementation used by the running app. */
class DataStoreThemePreferenceStore(private val context: Context) : ThemePreferenceStore {

    override val darkMode: Flow<Boolean> =
        context.themeDataStore.data.map { prefs -> prefs[DARK_MODE_KEY] ?: false }

    override suspend fun setDarkMode(enabled: Boolean) {
        context.themeDataStore.edit { prefs -> prefs[DARK_MODE_KEY] = enabled }
    }

    private companion object {
        val DARK_MODE_KEY = booleanPreferencesKey("dark_mode")
    }
}
