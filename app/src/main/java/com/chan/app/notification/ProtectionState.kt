package com.chan.app.notification

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.core.app.NotificationManagerCompat

/**
 * The user's in-app switch for passive Zalo scanning (§B2).
 *
 * Separate from the system's Notification Access grant on purpose: someone who
 * wants CHAN to stop reading notifications for an afternoon should not have to
 * go digging through Android settings, and turning it off here stops processing
 * on the very next callback.
 *
 * Default is off. Passive reading of another app's notifications begins only
 * after a deliberate act.
 */
class ProtectionPreferences(context: Context) {

    private val preferences =
        context.applicationContext.getSharedPreferences("chan_protection", Context.MODE_PRIVATE)

    var zaloScanningEnabled: Boolean
        get() = preferences.getBoolean(KEY_ZALO_SCANNING, false)
        set(value) = preferences.edit().putBoolean(KEY_ZALO_SCANNING, value).apply()

    private companion object {
        const val KEY_ZALO_SCANNING = "zalo_scanning_enabled"
    }
}

/**
 * The one state the user is shown, computed from every layer underneath it
 * (§B2).
 *
 * The ordering is the point. A green indicator is reachable only from a real
 * `onListenerConnected` in this process; a granted permission on its own gets
 * [CONNECTING] at best, and a cleared app data directory gets [OFF] however
 * generous Android is still being with the Notification Access grant.
 */
enum class ProtectionHealth {
    /** The in-app switch is off. Nothing is read. */
    OFF,

    /** The switch is on but Android has not granted Notification Access. */
    ACCESS_REQUIRED,

    /** Everything is granted; no listener callback has arrived yet. */
    CONNECTING,

    /** A rebind the user asked for is outstanding. No second tap while here. */
    RECONNECTING,

    /**
     * Android is not connecting CHAN to notifications.
     *
     * Reached either because the listener was bound and is not any more, or
     * because a rebind went unanswered. The remedy is the Notification Access
     * toggle, not another wait — see [DisconnectReason.REBIND_NOT_ANSWERED].
     */
    DISCONNECTED,

    /** Connected and scanning, but CHAN may not post the warning it would make. */
    ACTIVE_WITHOUT_WARNINGS,

    /** Connected, scanning, and able to warn. */
    ACTIVE,
    ;

    /** True only for a live listener. Never a statement about a message. */
    val listenerLive: Boolean get() = this == ACTIVE || this == ACTIVE_WITHOUT_WARNINGS

    /** The user has to do something for protection to work again. */
    val needsAttention: Boolean get() = this == ACCESS_REQUIRED || this == DISCONNECTED

    /** An attempt is outstanding, so the reconnect control must not be tappable. */
    val attemptPending: Boolean get() = this == RECONNECTING
}

/** Computes [ProtectionHealth]. Pure, so the whole truth table is unit tested. */
object EffectiveProtection {

    fun evaluate(
        /** The in-app switch. Cleared app data returns it to false. */
        zaloScanningEnabled: Boolean,
        /** Android's Notification Access grant for CHAN. */
        notificationAccessGranted: Boolean,
        /** What the listener is actually doing in this process. */
        connection: ListenerConnection,
        /** Whether CHAN may post its own warnings. */
        warningsAllowed: Boolean,
    ): ProtectionHealth = when {
        !zaloScanningEnabled -> ProtectionHealth.OFF
        !notificationAccessGranted -> ProtectionHealth.ACCESS_REQUIRED
        // Only a real `onListenerConnected` in this process can be active.
        connection is ListenerConnection.Connected && warningsAllowed -> ProtectionHealth.ACTIVE
        connection is ListenerConnection.Connected -> ProtectionHealth.ACTIVE_WITHOUT_WARNINGS
        connection is ListenerConnection.Disconnected -> ProtectionHealth.DISCONNECTED
        // A retry the user asked for is its own stage: it says something is
        // being tried, and it is what suppresses a second tap.
        connection is ListenerConnection.Connecting && connection.rebindRequested ->
            ProtectionHealth.RECONNECTING
        // Unknown and an ordinary bind are the same promise: "wait".
        else -> ProtectionHealth.CONNECTING
    }
}

/** How the three system layers behind the protection screen currently stand. */
data class ProtectionStatus(
    /** Android's Notification Access grant for CHAN. */
    val notificationAccessGranted: Boolean,
    /** The in-app switch. */
    val zaloScanningEnabled: Boolean,
    /** Whether CHAN may post its own warnings (Android 13+ runtime permission). */
    val warningsAllowed: Boolean,
    /** True when the rule layer is running from a server bundle rather than the APK copy. */
    val serverRulesFresh: Boolean,
) {
    /** Passive scanning is actually happening only when both layers agree. */
    val scanning: Boolean get() = notificationAccessGranted && zaloScanningEnabled
}

/**
 * Reads the platform's own answer about notification access. The app never
 * assumes access was granted because it opened the settings screen — the user
 * may have looked at it and walked away.
 */
object NotificationAccess {

    fun isListenerEnabled(context: Context): Boolean =
        NotificationManagerCompat.getEnabledListenerPackages(context).contains(context.packageName)

    fun areWarningsAllowed(context: Context): Boolean =
        NotificationManagerCompat.from(context).areNotificationsEnabled()

    /** Android's Notification Access list. There is no runtime dialog for this. */
    fun listenerSettingsIntent(): Intent =
        Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)

    /**
     * CHAN's own notification settings, for when warnings were denied. The
     * dedicated screen only exists from API 26; older phones get app details,
     * which has the same switch one level down.
     */
    fun appNotificationSettingsIntent(context: Context): Intent {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return appDetailsIntent(context)
        return Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS)
            .putExtra(Settings.EXTRA_APP_PACKAGE, context.packageName)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    }

    /**
     * The watched app's own notification settings (§B2).
     *
     * An ordinary app cannot read whether Zalo's notifications are enabled, so
     * CHAN never claims to know. When no Zalo events arrive at all, this is
     * offered as something the user can check for themselves.
     */
    fun watchedAppNotificationSettingsIntent(): Intent {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
            return Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
                .setData(Uri.fromParts("package", ZALO_PACKAGE, null))
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        return Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS)
            .putExtra(Settings.EXTRA_APP_PACKAGE, ZALO_PACKAGE)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    }

    /** App details, used when a permission was permanently denied. */
    fun appDetailsIntent(context: Context): Intent =
        Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
            .setData(Uri.fromParts("package", context.packageName, null))
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
}
