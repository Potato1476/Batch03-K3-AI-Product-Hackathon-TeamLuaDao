package com.chan.app.notification

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.chan.app.MainActivity
import com.chan.app.R

/**
 * The ongoing "CHAN đang bảo vệ Zalo" indicator (§B4).
 *
 * There is no parameter anywhere in this interface: the notification is a fixed
 * sentence, so no caller can put a sender, a message, or an analysis result
 * into it even by accident.
 */
interface ProtectionStatusNotifier {
    /** Posts the indicator. Returns false when the OS will not show it. */
    fun show(): Boolean

    /** Removes it. Safe to call when nothing is showing. */
    fun cancel()
}

/**
 * Publishes the indicator only when the listener is genuinely live (§B4).
 *
 * A low-importance, ongoing notification is the only honest signal Android
 * gives a user that a passive service is bound. It is an indicator, not an
 * alert, and not a promise: Android may still kill the process, at which point
 * `onDestroy` takes the indicator away with it.
 */
class AndroidProtectionStatusNotifier(context: Context) : ProtectionStatusNotifier {

    private val context = context.applicationContext
    private val manager = NotificationManagerCompat.from(this.context)

    init {
        createChannel()
    }

    override fun show(): Boolean {
        if (!manager.areNotificationsEnabled()) return false

        val notification = NotificationCompat.Builder(context, CHANNEL_PROTECTION_STATUS)
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentTitle(context.getString(R.string.status_notification_title))
            .setContentText(context.getString(R.string.status_notification_body))
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setCategory(NotificationCompat.CATEGORY_STATUS)
            .setVisibility(NotificationCompat.VISIBILITY_PRIVATE)
            .setOngoing(true)
            .setShowWhen(false)
            .setSilent(true)
            .setContentIntent(openProtectionScreenIntent())
            .build()

        return try {
            manager.notify(STATUS_NOTIFICATION_ID, notification)
            true
        } catch (error: SecurityException) {
            // POST_NOTIFICATIONS was revoked between the check and the post.
            false
        }
    }

    override fun cancel() {
        runCatching { manager.cancel(STATUS_NOTIFICATION_ID) }
    }

    private fun openProtectionScreenIntent(): PendingIntent {
        val intent = Intent(context, MainActivity::class.java).apply {
            action = MainActivity.ACTION_OPEN_PROTECTION
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        return PendingIntent.getActivity(
            context,
            STATUS_REQUEST_CODE,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
    }

    /** Low importance, no sound, private on the lock screen. */
    private fun createChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val system = context.getSystemService(NotificationManager::class.java) ?: return
        val channel = NotificationChannel(
            CHANNEL_PROTECTION_STATUS,
            context.getString(R.string.channel_protection_status_name),
            NotificationManager.IMPORTANCE_LOW,
        ).apply {
            description = context.getString(R.string.channel_protection_status_description)
            lockscreenVisibility = NotificationCompat.VISIBILITY_PRIVATE
            setSound(null, null)
            enableVibration(false)
            enableLights(false)
        }
        system.createNotificationChannel(channel)
    }

    companion object {
        const val CHANNEL_PROTECTION_STATUS = "chan_protection_status"
        const val STATUS_NOTIFICATION_ID = 4101
        private const val STATUS_REQUEST_CODE = 41
    }
}

/**
 * Decides whether the indicator may be visible (§B4).
 *
 * Pure, and separated from the posting so the "publish only from a real
 * connected state" rule can be proven without a device. Every path that is not
 * [ProtectionHealth.ACTIVE] cancels: a stale indicator left over from a killed
 * process is exactly the lie this sprint exists to remove.
 */
object ProtectionStatusReconciler {

    fun shouldShow(health: ProtectionHealth): Boolean = health == ProtectionHealth.ACTIVE

    /** Applies the decision. Returns true when the indicator is now visible. */
    fun reconcile(health: ProtectionHealth, notifier: ProtectionStatusNotifier): Boolean {
        if (!shouldShow(health)) {
            notifier.cancel()
            return false
        }
        return notifier.show()
    }
}
