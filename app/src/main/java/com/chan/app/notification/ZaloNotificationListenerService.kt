package com.chan.app.notification

import android.app.Notification
import android.os.Bundle
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import androidx.core.app.NotificationCompat
import com.chan.app.data.ChanGraph
import com.chan.app.domain.ChanOutcome
import com.chan.app.domain.InputMode
import com.chan.app.domain.Risk
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch

/**
 * Passive Zalo intake (§B5).
 *
 * The system binds this only after the user grants Notification Access by hand.
 * Every callback is filtered before anything is read, and the pipeline is:
 *
 * ```
 * consent + package checks → safe extraction → dedupe → L0/L1 on device
 *     → OTP        : local high, no network
 *     → below gate : stop silently
 *     → above gate : one POST /v1/analyze
 * → publish a generic warning for high/medium only
 * ```
 *
 * Callbacks arrive on the main thread, so matching and any request are moved to
 * a scope this service owns and cancels in [onDestroy]. A failed request is
 * dropped: there is no retry loop and no queue, because queueing would mean
 * keeping someone's message on disk.
 */
class ZaloNotificationListenerService : NotificationListenerService() {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    private val dedupe = NotificationDedupeCache()

    @Volatile
    private var extractor: NotificationContentExtractor? = null

    override fun onListenerConnected() {
        super.onListenerConnected()
        // A newly connected listener is a good moment to check for newer rules.
        ChanGraph.of(this).refreshRulesInBackground()
    }

    override fun onNotificationPosted(sbn: StatusBarNotification?) {
        val posted = sbn ?: return
        // Cheapest checks first, on the callback thread, before reading anything.
        if (posted.packageName != ZALO_PACKAGE) return
        if (!ChanGraph.of(this).protection.zaloScanningEnabled) return

        val snapshot = snapshotOf(posted)
        // The framework object is not captured by the coroutine below.
        scope.launch { process(snapshot) }
    }

    override fun onDestroy() {
        scope.cancel()
        dedupe.clear()
        super.onDestroy()
    }

    private suspend fun process(snapshot: NotificationSnapshot) {
        val components = ChanGraph.of(this)
        if (!components.protection.zaloScanningEnabled) return

        val extracted = extractorFor().extract(snapshot) ?: return

        val engine = runCatching { components.bundles.engine() }.getOrNull() ?: return
        val digest = NotificationDedupeCache.digestOf(
            packageName = extracted.packageName,
            key = extracted.key,
            normalizedContent = engine.normalize(extracted.content),
        )
        if (!dedupe.claim(digest)) return

        // One bounded attempt. Whatever happens, the content is released here.
        val outcome = components.repository.analyzeMessage(
            message = extracted.content,
            inputMode = InputMode.NOTIFICATION,
            appPackage = ZALO_PACKAGE,
            truncated = extracted.truncated,
        )
        if (outcome !is ChanOutcome.Success) return

        val result = outcome.value
        if (result.risk == Risk.UNKNOWN) return

        components.pendingAlerts.put(result)
        components.alerts.publish(result.risk)
    }

    private suspend fun extractorFor(): NotificationContentExtractor {
        extractor?.let { return it }
        // Truncation markers come from the shared Rule Bundle so Web and Android
        // agree on what "shortened" means.
        val markers = runCatching {
            ChanGraph.of(this).bundles.bundle()
                .l1.localSignals[TRUNCATION_RULE]
                ?.patterns
                ?.mapNotNull { pattern -> runCatching { Regex(pattern) }.getOrNull() }
                .orEmpty()
        }.getOrNull().orEmpty()

        return NotificationContentExtractor(
            ownPackage = packageName,
            truncationMarkers = markers.ifEmpty { NotificationContentExtractor.DEFAULT_TRUNCATION_MARKERS },
        ).also { extractor = it }
    }

    /**
     * Copies the extras CHAN is allowed to look at into a plain object. Nothing
     * read here is printed; the values go straight into extraction.
     */
    private fun snapshotOf(posted: StatusBarNotification): NotificationSnapshot {
        val notification = posted.notification
        val extras: Bundle = notification.extras

        val messagingTexts = runCatching {
            NotificationCompat.MessagingStyle
                .extractMessagingStyleFromNotification(notification)
                ?.messages
                // The sender is deliberately not read — only what was said.
                ?.mapNotNull { message -> message.text?.toString() }
                .orEmpty()
        }.getOrDefault(emptyList())

        return NotificationSnapshot(
            packageName = posted.packageName,
            key = posted.key.orEmpty(),
            title = extras.getCharSequence(Notification.EXTRA_TITLE)?.toString(),
            text = extras.getCharSequence(Notification.EXTRA_TEXT)?.toString(),
            bigText = extras.getCharSequence(Notification.EXTRA_BIG_TEXT)?.toString(),
            summaryText = extras.getCharSequence(Notification.EXTRA_SUMMARY_TEXT)?.toString(),
            textLines = extras.getCharSequenceArray(Notification.EXTRA_TEXT_LINES)
                ?.map { it.toString() }
                .orEmpty(),
            messagingTexts = messagingTexts,
            isOngoing = posted.isOngoing,
            isGroupSummary = (notification.flags and Notification.FLAG_GROUP_SUMMARY) != 0,
        )
    }

    private companion object {
        const val TRUNCATION_RULE = "truncation_marker"
    }
}
