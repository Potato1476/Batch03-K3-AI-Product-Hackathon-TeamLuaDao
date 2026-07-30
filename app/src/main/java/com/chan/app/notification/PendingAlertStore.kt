package com.chan.app.notification

import android.content.Context
import com.chan.app.domain.AnalysisResult
import com.chan.app.domain.AnalysisSignal
import com.chan.app.domain.Risk

/** Minimal key/value storage behind [PendingAlertStore], so it is unit testable. */
interface AlertStorage {
    fun snapshot(): Map<String, String>
    fun write(values: Map<String, String>)
    fun clear()
}

/** Test and in-process implementation. */
class InMemoryAlertStorage : AlertStorage {
    private val values = mutableMapOf<String, String>()

    @Synchronized
    override fun snapshot(): Map<String, String> = values.toMap()

    @Synchronized
    override fun write(values: Map<String, String>) {
        this.values.clear()
        this.values.putAll(values)
    }

    @Synchronized
    override fun clear() = values.clear()
}

/** SharedPreferences-backed storage used by the running app. */
class SharedPreferencesAlertStorage(context: Context) : AlertStorage {

    private val preferences =
        context.applicationContext.getSharedPreferences("chan_pending_alert", Context.MODE_PRIVATE)

    override fun snapshot(): Map<String, String> =
        preferences.all.mapNotNull { (key, value) -> (value as? String)?.let { key to it } }.toMap()

    override fun write(values: Map<String, String>) {
        val editor = preferences.edit().clear()
        values.forEach { (key, value) -> editor.putString(key, value) }
        editor.apply()
    }

    override fun clear() = preferences.edit().clear().apply()
}

/**
 * Carries a warning from the notification listener to the screen the user
 * reaches by tapping it (§B6).
 *
 * Two layers on purpose. The full result stays in memory, where it dies with
 * the process. Only a redacted skeleton — risk, score, signal *codes*, the
 * backend's generic explanation — is written to disk, and only for a few
 * minutes, so that a tap after the listener process was killed still opens
 * something truthful.
 *
 * What is never persisted: the message, the sender, and every `evidence`
 * excerpt, even though the backend already redacted those.
 */
class PendingAlertStore(
    private val storage: AlertStorage,
    private val ttlMillis: Long = DEFAULT_TTL_MILLIS,
    private val now: () -> Long = System::currentTimeMillis,
) {

    @Volatile
    private var inMemory: AnalysisResult? = null

    fun put(result: AnalysisResult) {
        inMemory = result
        storage.write(
            mapOf(
                KEY_RISK to result.risk.name,
                KEY_SCORE to result.score.toString(),
                KEY_SIGNAL_CODES to result.signals.joinToString(",") { it.code },
                KEY_EXPLANATION to result.explanation,
                KEY_TRUNCATED to result.truncated.toString(),
                KEY_CREATED_AT to now().toString(),
            ),
        )
    }

    /** Returns the pending warning once and deletes it. */
    fun take(): AnalysisResult? {
        val result = inMemory ?: fromStorage()
        clear()
        return result
    }

    fun clear() {
        inMemory = null
        storage.clear()
    }

    /** Rebuilds the redacted skeleton after the listener process was killed. */
    private fun fromStorage(): AnalysisResult? {
        val values = storage.snapshot()
        if (values.isEmpty()) return null
        val createdAt = values[KEY_CREATED_AT]?.toLongOrNull() ?: return null
        if (now() - createdAt > ttlMillis) return null

        val risk = runCatching { Risk.valueOf(values[KEY_RISK].orEmpty()) }.getOrNull() ?: return null
        val codes = values[KEY_SIGNAL_CODES].orEmpty()
            .split(",")
            .map { it.trim() }
            .filter { it.isNotEmpty() }
        return AnalysisResult(
            risk = risk,
            score = values[KEY_SCORE]?.toDoubleOrNull() ?: 0.0,
            // Evidence was never written, so it comes back empty by construction.
            signals = codes.map { AnalysisSignal(code = it, confidence = 1.0, evidence = "") },
            explanation = values[KEY_EXPLANATION].orEmpty(),
            questions = emptyList(),
            verifiedHotline = null,
            actions = emptyList(),
            engineVersion = "",
            ruleBundleVersion = "",
            truncated = values[KEY_TRUNCATED]?.toBooleanStrictOrNull() ?: false,
        )
    }

    companion object {
        private const val DEFAULT_TTL_MILLIS = 10L * 60 * 1000

        // Deliberately named after the verdict, never after the source content.
        const val KEY_RISK = "alert_risk"
        const val KEY_SCORE = "alert_score"
        const val KEY_SIGNAL_CODES = "alert_signal_codes"
        const val KEY_EXPLANATION = "alert_explanation"
        const val KEY_TRUNCATED = "alert_truncated"
        const val KEY_CREATED_AT = "alert_created_at"
    }
}
