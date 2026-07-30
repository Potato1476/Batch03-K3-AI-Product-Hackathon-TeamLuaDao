package com.chan.app.notification

import android.app.Notification
import android.os.Bundle
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import androidx.core.app.NotificationCompat
import com.chan.app.data.ChanGraph
import kotlinx.coroutines.launch

/**
 * Passive Zalo intake (§B5, §D3).
 *
 * The system binds this only after the user grants Notification Access by hand.
 * Every callback is filtered before anything is read, and the pipeline is:
 *
 * ```
 * consent + package checks → safe extraction → occurrence dedupe → L0/L1
 *     → OTP        : local high, no network
 *     → below gate : stop silently
 *     → above gate : one POST /v1/analyze
 * → publish a fresh generic warning for high/medium only
 * ```
 *
 * The decision logic lives in [NotificationPipeline] so it can be tested
 * without a device. This class is the Android adapter: it copies the framework
 * object into a plain snapshot, keeps a usable coroutine scope across
 * disconnect/reconnect, and reports listener liveness to
 * [ProtectionRuntimeMonitor] — the callbacks below are the *only* thing in CHAN
 * allowed to say the listener is connected.
 */
class ZaloNotificationListenerService : NotificationListenerService() {

    private val scope = RestartableScope()

    private val occurrences = NotificationOccurrenceCache()

    @Volatile
    private var extractor: NotificationContentExtractor? = null

    @Volatile
    private var pipeline: NotificationPipeline? = null

    override fun onCreate() {
        super.onCreate()
        // Creation is not a connection: the monitor only learns that a bind is
        // in progress. `onListenerConnected` is the callback that counts.
        ChanGraph.of(this).runtime.onConnecting()
    }

    override fun onListenerConnected() {
        super.onListenerConnected()
        val components = ChanGraph.of(this)
        components.runtime.onConnected()
        // A reconnected listener may be handed a cancelled scope. Rebuilding it
        // here is what keeps the second evening's messages flowing after
        // Android has unbound us once (§D3).
        scope.active()
        components.reconcileProtectionStatus()
        components.refreshRulesInBackground()
    }

    override fun onListenerDisconnected() {
        val components = ChanGraph.of(this)
        components.runtime.onDisconnected(DisconnectReason.LISTENER_DISCONNECTED)
        // The indicator must never outlive the thing it indicates.
        components.protectionStatus.cancel()
        super.onListenerDisconnected()
    }

    override fun onNotificationPosted(sbn: StatusBarNotification?) {
        val posted = sbn ?: return
        // Cheapest checks first, on the callback thread, before reading anything.
        if (posted.packageName != ZALO_PACKAGE) return
        if (!ChanGraph.of(this).protection.zaloScanningEnabled) return

        val snapshot = snapshotOf(posted)
        // The framework object is not captured by the coroutine below.
        scope.active().launch { pipelineFor().process(snapshot) }
    }

    override fun onDestroy() {
        val components = ChanGraph.of(this)
        components.runtime.onDisconnected(DisconnectReason.SERVICE_DESTROYED)
        components.protectionStatus.cancel()
        scope.cancel()
        occurrences.clear()
        super.onDestroy()
    }

    private fun pipelineFor(): NotificationPipeline {
        pipeline?.let { return it }
        val components = ChanGraph.of(this)
        return NotificationPipeline(
            scanningEnabled = { components.protection.zaloScanningEnabled },
            extract = { snapshot -> extractorFor().extract(snapshot) },
            normalize = { content ->
                runCatching { components.bundles.engine().normalize(content) }.getOrNull()
            },
            occurrences = occurrences,
            repository = components.repository,
            pendingAlerts = { result -> components.pendingAlerts.put(result) },
            alerts = components.alerts,
            telemetry = components.telemetry,
        ).also { pipeline = it }
    }

    /**
     * Truncation markers come from the shared Rule Bundle so Web and Android
     * agree on what "shortened" means. Built lazily and off the callback thread.
     */
    private suspend fun extractorFor(): NotificationContentExtractor {
        extractor?.let { return it }
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
     * read here is printed; the values go straight into extraction, and the
     * only identity-adjacent fields taken are timestamps (§D2).
     */
    private fun snapshotOf(posted: StatusBarNotification): NotificationSnapshot {
        val notification = posted.notification
        val extras: Bundle = notification.extras

        val messages = runCatching {
            NotificationCompat.MessagingStyle
                .extractMessagingStyleFromNotification(notification)
                ?.messages
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
            // The sender is deliberately not read — only what was said, and when.
            messagingTexts = messages.mapNotNull { message -> message.text?.toString() },
            isOngoing = posted.isOngoing,
            isGroupSummary = (notification.flags and Notification.FLAG_GROUP_SUMMARY) != 0,
            postTime = posted.postTime,
            messageTimestamps = messages.map { message -> message.timestamp },
            // The badge count, when Zalo sets one. A number, not a message.
            messageCount = notification.number.takeIf { it > 0 },
        )
    }

    private companion object {
        const val TRUNCATION_RULE = "truncation_marker"
    }
}
