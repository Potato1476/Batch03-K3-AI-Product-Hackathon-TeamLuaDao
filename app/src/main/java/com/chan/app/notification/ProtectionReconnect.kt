package com.chan.app.notification

import android.content.ComponentName
import android.content.Context
import android.service.notification.NotificationListenerService

/** Asks Android to bind CHAN's listener again. Returns false when it refused. */
fun interface ListenerRebinder {
    fun requestRebind(): Boolean
}

/**
 * The real rebind. `requestRebind` is the only supported way to recover a
 * listener that Android has unbound without the user re-granting anything; it
 * is a request, and the `onListenerConnected` callback is the only proof it
 * worked.
 */
class AndroidListenerRebinder(context: Context) : ListenerRebinder {

    private val context = context.applicationContext

    override fun requestRebind(): Boolean = runCatching {
        NotificationListenerService.requestRebind(
            ComponentName(context, ZaloNotificationListenerService::class.java),
        )
        true
    }.getOrDefault(false)
}

/** What a reconnect request decided to do. Drives the copy the user sees. */
enum class ReconnectDecision {
    /** A rebind was requested and we are waiting for the real callback. */
    REQUESTED,

    /** Nothing to do: the listener is already connected. */
    ALREADY_CONNECTED,

    /** The in-app switch is off, so there is nothing to reconnect. */
    SCANNING_DISABLED,

    /** Android has not granted access; settings must be opened instead. */
    ACCESS_MISSING,

    /** The automatic attempt for this foreground event was already spent. */
    ALREADY_ATTEMPTED,

    /** An attempt is already outstanding; tapping again would change nothing. */
    IN_FLIGHT,

    /** Android refused the rebind request. */
    REFUSED,
}

/**
 * One bounded reconnect attempt per foreground event (§B3).
 *
 * Deliberately not a retry loop, an alarm, or a WorkManager job. If a rebind
 * does not produce `onListenerConnected` inside the window the caller applies,
 * the screen says so and offers "Kết nối lại" — a person deciding to try again
 * is a better signal than a background timer that drains the battery of a phone
 * whose owner never asked for it.
 */
class ProtectionReconnectController(
    private val monitor: ProtectionRuntimeMonitor,
    private val rebinder: ListenerRebinder,
) {

    private var automaticAttemptSpent = false

    /** Called on every resume. Re-arms the single automatic attempt. */
    fun onForeground() {
        automaticAttemptSpent = false
    }

    /**
     * The automatic attempt. Runs at most once per foreground event and only
     * when the listener is genuinely not connected.
     */
    fun requestAutomatic(zaloScanningEnabled: Boolean, notificationAccessGranted: Boolean): ReconnectDecision {
        if (automaticAttemptSpent) return ReconnectDecision.ALREADY_ATTEMPTED
        val decision = attempt(zaloScanningEnabled, notificationAccessGranted)
        // Only a real rebind spends the attempt. A resume where nothing could
        // be done — access missing, protection paused — must not stop the user
        // from being reconnected once they fix it.
        if (decision == ReconnectDecision.REQUESTED || decision == ReconnectDecision.REFUSED) {
            automaticAttemptSpent = true
        }
        return decision
    }

    /** A user-tapped "Kết nối lại". Always allowed to try once more. */
    fun requestManual(zaloScanningEnabled: Boolean, notificationAccessGranted: Boolean): ReconnectDecision =
        attempt(zaloScanningEnabled, notificationAccessGranted)

    private fun attempt(zaloScanningEnabled: Boolean, notificationAccessGranted: Boolean): ReconnectDecision {
        if (!zaloScanningEnabled) return ReconnectDecision.SCANNING_DISABLED
        if (!notificationAccessGranted) return ReconnectDecision.ACCESS_MISSING
        if (monitor.connection.value is ListenerConnection.Connected) return ReconnectDecision.ALREADY_CONNECTED
        // One outstanding attempt at a time. Tapping "Kết nối lại" repeatedly
        // only queues more requests for a system that is already ignoring one.
        if (monitor.attemptPending) return ReconnectDecision.IN_FLIGHT

        monitor.onConnecting(rebindRequested = true)
        if (!rebinder.requestRebind()) {
            monitor.onDisconnected(DisconnectReason.REBIND_NOT_ANSWERED)
            return ReconnectDecision.REFUSED
        }
        return ReconnectDecision.REQUESTED
    }

    companion object {
        /**
         * How long CHAN keeps saying "đang thử kết nối lại" before admitting
         * that Android has not answered.
         *
         * Deliberately short, and deliberately not tunable upward as a "fix":
         * a `requestRebind` the platform ignores is not ignored any less after
         * thirty seconds. The window only bounds the claim CHAN is making.
         */
        const val REBIND_WINDOW_MILLIS = 5_000L
    }
}
