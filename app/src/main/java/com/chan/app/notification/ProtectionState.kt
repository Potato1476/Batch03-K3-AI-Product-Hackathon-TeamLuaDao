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

    /** App details, used when a permission was permanently denied. */
    fun appDetailsIntent(context: Context): Intent =
        Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
            .setData(Uri.fromParts("package", context.packageName, null))
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
}
