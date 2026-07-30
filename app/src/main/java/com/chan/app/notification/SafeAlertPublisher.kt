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
 * One warning event (§D4). [cancelIds] are the alerts to remove as this one is
 * posted.
 */
data class AlertEvent(
    val notificationId: Int,
    val requestCode: Int,
    val cancelIds: List<Int>,
)

/**
 * Hands out a fresh notification identity for each risky message (§D4).
 *
 * Sprint 02 always called `notify(4201, …)`. Android treats that as an update
 * to a notification the user has already seen, so the second scam message of
 * the evening quietly refreshed a line in the shade instead of raising a new
 * warning. Physical testing found exactly that.
 *
 * The ring is bounded to three ids and the previous alert is cancelled as the
 * new one is posted, so a person still sees at most one CHAN risk warning — the
 * Sprint 02 goal — while Android sees a genuinely new event.
 *
 * Rotation state is per process, and Android's is not: a warning posted before
 * the process was killed can still be sitting in the shade under one of these
 * ids. The first event of a new process therefore retires **every** id in the
 * ring before its own post, including the one it is about to use. Cancelling
 * then posting the same id is a new notification record, which is what makes it
 * a new event rather than an update to something the user already dismissed
 * mentally.
 */
class AlertEventRotator(private val ids: List<Int> = DEFAULT_IDS) {

    private var index = -1
    private var eventCount = 0

    @Synchronized
    fun next(): AlertEvent {
        val firstInThisProcess = index < 0
        val previous = if (index >= 0) ids[index] else null
        index = (index + 1) % ids.size
        eventCount++
        return AlertEvent(
            notificationId = ids[index],
            // A distinct request code per event: a PendingIntent reused from an
            // older warning could otherwise keep pointing at the older result.
            // The intent itself carries no payload, so the newest redacted
            // result is the only thing a tap can reach.
            requestCode = REQUEST_CODE_BASE + eventCount,
            cancelIds = if (firstInThisProcess) ids else listOfNotNull(previous),
        )
    }

    companion object {
        /** Bounded on purpose: a wall of warnings helps nobody. */
        val DEFAULT_IDS = listOf(4201, 4202, 4203)
        const val REQUEST_CODE_BASE = 4200
    }
}

/**
 * Posts a heads-up warning that says nothing about what triggered it (§B6,
 * §D4).
 *
 * Deliberately not a full-screen intent and never `setOnlyAlertOnce`: CHAN asks
 * for the user's attention and lets the OS decide whether to raise a banner.
 * Lock-screen visibility is private, so even the generic body stays behind the
 * lock.
 */
class AndroidSafeAlertPublisher(
    context: Context,
    private val rotator: AlertEventRotator = AlertEventRotator(),
) : SafeAlertPublisher {

    private val context = context.applicationContext
    private val manager = NotificationManagerCompat.from(this.context)

    init {
        createChannels()
    }

    override fun publish(risk: Risk): Boolean {
        val copy = SafeAlertCopy.forRisk(risk) ?: return false
        if (!manager.areNotificationsEnabled()) return false

        val event = rotator.next()
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
            .setContentIntent(openResultIntent(event.requestCode))
            .build()

        return try {
            // The older warning goes as the new one arrives: one visible alert,
            // but a new event Android is free to raise again. On the first
            // warning of a process this also clears anything left in the shade
            // by the process before it.
            event.cancelIds.forEach { id -> runCatching { manager.cancel(id) } }
            manager.notify(event.notificationId, notification)
            true
        } catch (error: SecurityException) {
            // POST_NOTIFICATIONS was revoked between the check and the post.
            false
        }
    }

    private fun openResultIntent(requestCode: Int): PendingIntent {
        val intent = Intent(context, MainActivity::class.java).apply {
            action = MainActivity.ACTION_OPEN_ALERT
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        return PendingIntent.getActivity(
            context,
            requestCode,
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
    }
}
