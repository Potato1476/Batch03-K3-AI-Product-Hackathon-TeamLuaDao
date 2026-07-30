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
import com.chan.app.domain.Risk

/** Publishes CHAN's own warning. Returns false when the OS will not show it. */
fun interface SafeAlertPublisher {
    fun publish(risk: Risk): Boolean
}

/**
 * Posts a heads-up warning that says nothing about what triggered it (§B6).
 *
 * Deliberately not a full-screen intent: Sprint 02 uses a high-importance
 * channel and lets the OS decide whether to raise it. Lock-screen visibility is
 * private, so even the generic body stays behind the lock.
 */
class AndroidSafeAlertPublisher(context: Context) : SafeAlertPublisher {

    private val context = context.applicationContext
    private val manager = NotificationManagerCompat.from(this.context)

    init {
        createChannels()
    }

    override fun publish(risk: Risk): Boolean {
        val copy = SafeAlertCopy.forRisk(risk) ?: return false
        if (!manager.areNotificationsEnabled()) return false

        val channelId = if (risk == Risk.HIGH) CHANNEL_HIGH_RISK else CHANNEL_CAUTION
        val notification = NotificationCompat.Builder(context, channelId)
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentTitle(copy.title)
            .setContentText(copy.body)
            .setPriority(if (risk == Risk.HIGH) NotificationCompat.PRIORITY_HIGH else NotificationCompat.PRIORITY_DEFAULT)
            .setCategory(NotificationCompat.CATEGORY_MESSAGE)
            // The body is generic, but a locked phone still shows nothing extra.
            .setVisibility(NotificationCompat.VISIBILITY_PRIVATE)
            .setAutoCancel(true)
            .setContentIntent(openResultIntent())
            .build()

        return try {
            // A single id: a newer warning replaces the older one rather than
            // stacking up a wall of alerts on the lock screen.
            manager.notify(ALERT_NOTIFICATION_ID, notification)
            true
        } catch (error: SecurityException) {
            // POST_NOTIFICATIONS was revoked between the check and the post.
            false
        }
    }

    private fun openResultIntent(): PendingIntent {
        val intent = Intent(context, MainActivity::class.java).apply {
            action = MainActivity.ACTION_OPEN_ALERT
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        return PendingIntent.getActivity(
            context,
            0,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
    }

    private fun createChannels() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val system = context.getSystemService(NotificationManager::class.java) ?: return

        val highRisk = NotificationChannel(
            CHANNEL_HIGH_RISK,
            context.getString(R.string.channel_high_risk_name),
            NotificationManager.IMPORTANCE_HIGH,
        ).apply {
            description = context.getString(R.string.channel_high_risk_description)
            lockscreenVisibility = NotificationCompat.VISIBILITY_PRIVATE
        }
        val caution = NotificationChannel(
            CHANNEL_CAUTION,
            context.getString(R.string.channel_caution_name),
            NotificationManager.IMPORTANCE_DEFAULT,
        ).apply {
            description = context.getString(R.string.channel_caution_description)
            lockscreenVisibility = NotificationCompat.VISIBILITY_PRIVATE
        }
        system.createNotificationChannel(highRisk)
        system.createNotificationChannel(caution)
    }

    companion object {
        const val CHANNEL_HIGH_RISK = "chan_high_risk"
        const val CHANNEL_CAUTION = "chan_caution"
        const val ALERT_NOTIFICATION_ID = 4201
    }
}
