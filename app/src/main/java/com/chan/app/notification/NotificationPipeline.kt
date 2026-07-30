package com.chan.app.notification

import com.chan.app.domain.AnalysisResult
import com.chan.app.domain.ChanOutcome
import com.chan.app.domain.ChanRepository
import com.chan.app.domain.InputMode
import com.chan.app.domain.Risk
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.isActive
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * What one Zalo callback ended up doing (§D3).
 *
 * A category, never a content excerpt. These names are the entire vocabulary
 * the protection screen and any debug row may use.
 */
enum class PipelineOutcome {
    /** Not Zalo, a group summary, an ongoing call, or nothing readable. */
    IGNORED,

    /** The in-app switch is off. Nothing was read. */
    SCANNING_DISABLED,

    /** The same occurrence was already handled. */
    DUPLICATE,

    /** The local rules answered: an OTP request, decided without the network. */
    LOCAL_OTP,

    /** Below the local gate. Nothing was sent. */
    LOCAL_LOW,

    /** The backend answered and the result did not warrant a warning. */
    BACKEND_SUCCESS,

    /** The one bounded attempt failed. Nothing is queued or replayed. */
    BACKEND_FAILURE,

    /** A warning was published. */
    ALERT_POSTED,
}

/**
 * A coroutine scope that survives the listener being torn down and rebuilt
 * (§D3).
 *
 * `onDestroy` cancels the scope, and on the supported API levels a reconnect
 * can hand the same service instance back. Reusing a cancelled scope is
 * indistinguishable from the app being broken: every callback is accepted and
 * silently dropped. This never returns one.
 */
class RestartableScope(
    private val factory: () -> CoroutineScope = {
        CoroutineScope(SupervisorJob() + Dispatchers.Default)
    },
) {
    private val lock = Any()
    private var current: CoroutineScope? = null

    fun active(): CoroutineScope = synchronized(lock) {
        current?.takeIf { it.isActive } ?: factory().also { current = it }
    }

    fun cancel() = synchronized(lock) {
        current?.cancel()
        current = null
    }
}

/** Content-free runtime facts for the protection screen (§D3). */
data class ProtectionActivity(
    /** When Zalo last woke CHAN up. */
    val lastCallbackAt: Long? = null,
    /** What that callback ended up doing. */
    val lastOutcome: PipelineOutcome? = null,
    /** When CHAN last published a warning. */
    val lastAlertAt: Long? = null,
)

/**
 * Records what the pipeline did, with nowhere to put a message even by mistake:
 * the only inputs are an enum and a clock.
 */
class ProtectionTelemetry(private val now: () -> Long = System::currentTimeMillis) {

    private val _activity = MutableStateFlow(ProtectionActivity())
    val activity: StateFlow<ProtectionActivity> = _activity.asStateFlow()

    fun recordCallback() {
        _activity.value = _activity.value.copy(lastCallbackAt = now())
    }

    fun recordOutcome(outcome: PipelineOutcome) {
        val timestamp = now()
        _activity.value = _activity.value.copy(
            lastOutcome = outcome,
            lastAlertAt = if (outcome == PipelineOutcome.ALERT_POSTED) timestamp else _activity.value.lastAlertAt,
        )
    }
}

/**
 * The Zalo intake pipeline, with no Android in it (§D3).
 *
 * Sprint 02 kept this inside the listener service, which made the "works once"
 * failure invisible to tests. Here it is a plain object over seams, so the
 * whole acceptance matrix — duplicate callback, same text later, failure then
 * success, reconnect — is a JVM test.
 *
 * Every call is independent. There is no `processing` flag, no queue, and no
 * retained content: one failure, one duplicate, or one unknown result changes
 * nothing about the next callback.
 */
class NotificationPipeline(
    private val scanningEnabled: () -> Boolean,
    private val extract: suspend (NotificationSnapshot) -> ExtractedNotification?,
    private val normalize: suspend (String) -> String?,
    private val occurrences: NotificationOccurrenceCache,
    private val repository: ChanRepository,
    private val pendingAlerts: (AnalysisResult) -> Unit,
    private val alerts: SafeAlertPublisher,
    private val telemetry: ProtectionTelemetry,
) {

    suspend fun process(snapshot: NotificationSnapshot): PipelineOutcome {
        telemetry.recordCallback()
        val outcome = try {
            run(snapshot)
        } catch (error: CancellationException) {
            throw error
        } catch (error: Exception) {
            // A thrown pipeline is still one callback's problem. The scope that
            // called us stays usable for the next message.
            PipelineOutcome.BACKEND_FAILURE
        }
        telemetry.recordOutcome(outcome)
        return outcome
    }

    private suspend fun run(snapshot: NotificationSnapshot): PipelineOutcome {
        if (!scanningEnabled()) return PipelineOutcome.SCANNING_DISABLED

        val extracted = extract(snapshot) ?: return PipelineOutcome.IGNORED
        val normalized = normalize(extracted.content) ?: return PipelineOutcome.IGNORED

        val digest = NotificationOccurrenceCache.digestOf(
            packageName = extracted.packageName,
            key = extracted.key,
            occurrenceToken = extracted.occurrenceToken,
            normalizedContent = normalized,
        )
        if (!occurrences.claim(digest)) return PipelineOutcome.DUPLICATE

        // One bounded attempt. Whatever happens, the content is released here.
        val outcome = repository.analyzeMessage(
            message = extracted.content,
            inputMode = InputMode.NOTIFICATION,
            appPackage = ZALO_PACKAGE,
            truncated = extracted.truncated,
        )
        if (outcome !is ChanOutcome.Success) return PipelineOutcome.BACKEND_FAILURE

        val result = outcome.value
        if (result.risk == Risk.UNKNOWN) return PipelineOutcome.LOCAL_LOW

        // The store is replaced before the notification exists, so the warning
        // the user taps can only ever open the newest result (§D4).
        pendingAlerts(result)
        val published = alerts.publish(result.risk)

        return when {
            published -> PipelineOutcome.ALERT_POSTED
            result.decidedOnDevice -> PipelineOutcome.LOCAL_OTP
            else -> PipelineOutcome.BACKEND_SUCCESS
        }
    }
}
