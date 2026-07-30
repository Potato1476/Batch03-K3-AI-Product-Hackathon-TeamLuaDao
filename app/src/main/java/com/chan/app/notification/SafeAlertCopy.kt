package com.chan.app.notification

import com.chan.app.domain.Risk

/** Title and body of a CHAN warning notification. */
data class AlertCopy(val title: String, val body: String)

/**
 * The complete text of every warning CHAN posts (§B6).
 *
 * These four strings are the entire vocabulary on purpose. A warning appears on
 * the lock screen of a phone that may be in someone else's hand, so it must not
 * name the sender, quote the message, or hint at what was found. The user opens
 * CHAN to see the reason.
 *
 * The copy lives in Kotlin rather than `strings.xml` so a JVM test can assert
 * that no source content can reach it; CHAN ships in Vietnamese only.
 */
object SafeAlertCopy {

    private val HIGH = AlertCopy(
        title = "CHAN phát hiện nguy cơ cao",
        body = "Đừng chuyển tiền hoặc đọc mã OTP. Mở CHAN để xem lý do.",
    )

    private val MEDIUM = AlertCopy(
        title = "Tin nhắn cần cẩn trọng",
        body = "Mở CHAN để kiểm tra trước khi làm theo.",
    )

    /** Null for `UNKNOWN`: nothing was found, so nothing is worth interrupting for. */
    fun forRisk(risk: Risk): AlertCopy? = when (risk) {
        Risk.HIGH -> HIGH
        Risk.MEDIUM -> MEDIUM
        Risk.UNKNOWN -> null
    }
}
