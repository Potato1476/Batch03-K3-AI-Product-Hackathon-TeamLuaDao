package com.chan.app

import com.chan.app.domain.AnalysisResult
import com.chan.app.domain.AnalysisSignal
import com.chan.app.domain.Risk
import com.chan.app.notification.InMemoryAlertStorage
import com.chan.app.notification.PendingAlertStore
import com.chan.app.notification.SafeAlertCopy
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * What CHAN is willing to show on a lock screen, and what it is willing to
 * write to disk (§B6).
 *
 * The scenario these tests defend against is mundane: the phone is on a table,
 * someone else glances at it. A warning that quoted the message would hand that
 * person exactly what the user came to CHAN to protect.
 */
class SafeAlertTest {

    /** A scam message and the identifiers inside it, none of which may leak. */
    private val rawNotificationText =
        "Anh Minh: bác chuyển 20 triệu vào tài khoản 19001234567890 trước 17h, gọi 0912345678 gấp"

    private val notificationResult = AnalysisResult(
        risk = Risk.HIGH,
        score = 1.0,
        signals = listOf(
            // The backend already redacted this, and it still must not be persisted.
            AnalysisSignal("tk_ca_nhan", 1.0, "bác chuyển <AMOUNT:trieu> vào tài khoản <ACCOUNT>"),
            AnalysisSignal("ap_luc_thoi_gian", 0.9, "trước 17h"),
        ),
        explanation = "Tin nhắn yêu cầu chuyển tiền vào tài khoản cá nhân.",
        questions = listOf("Tại sao tiền lại chuyển vào tài khoản cá nhân?"),
        verifiedHotline = null,
        actions = listOf("report"),
        engineVersion = "ml-0.3.0",
        ruleBundleVersion = "rb-2026-07-30",
        truncated = true,
    )

    @Test
    fun warningTextContainsNoSenderMessageOrIdentifier() {
        val forbidden = listOf(
            "Anh Minh", "19001234567890", "0912345678", "20 triệu", "17h",
            "<ACCOUNT>", "<AMOUNT:trieu>", "tài khoản cá nhân",
        )

        listOf(Risk.HIGH, Risk.MEDIUM).forEach { risk ->
            val copy = SafeAlertCopy.forRisk(risk)!!
            val combined = "${copy.title} ${copy.body}"
            forbidden.forEach { fragment ->
                assertFalse(
                    "Alert for $risk must not contain \"$fragment\"",
                    combined.contains(fragment, ignoreCase = true),
                )
            }
        }
    }

    @Test
    fun warningTextIsTheAgreedGenericCopy() {
        val high = SafeAlertCopy.forRisk(Risk.HIGH)!!
        assertEquals("CHAN phát hiện nguy cơ cao", high.title)
        assertEquals("Đừng chuyển tiền hoặc đọc mã OTP. Mở CHAN để xem lý do.", high.body)

        val medium = SafeAlertCopy.forRisk(Risk.MEDIUM)!!
        assertEquals("Tin nhắn cần cẩn trọng", medium.title)
        assertEquals("Mở CHAN để kiểm tra trước khi làm theo.", medium.body)
    }

    @Test
    fun nothingIsPublishedForAnUnknownRisk() {
        assertNull(SafeAlertCopy.forRisk(Risk.UNKNOWN))
    }

    @Test
    fun rawNotificationTextIsAbsentFromPersistedState() {
        val storage = InMemoryAlertStorage()
        PendingAlertStore(storage).put(notificationResult)

        val persisted = storage.snapshot()
        assertTrue("Something must be stored for the tap-through", persisted.isNotEmpty())

        val serialized = persisted.entries.joinToString("\n") { "${it.key}=${it.value}" }
        val forbidden = listOf(
            rawNotificationText, "Anh Minh", "19001234567890", "0912345678",
            "<ACCOUNT>", "<AMOUNT:trieu>", "17h",
        )
        forbidden.forEach { fragment ->
            assertFalse("Persisted state must not contain \"$fragment\"", serialized.contains(fragment))
        }

        // Evidence excerpts are dropped even though the backend redacted them.
        assertFalse(serialized.contains("evidence"))
        // And no key is named after the source content.
        persisted.keys.forEach { key ->
            assertFalse(key, Regex("(raw|text|message|content|body|sender)").containsMatchIn(key))
        }
    }

    @Test
    fun theRedactedSkeletonSurvivesProcessDeathAndIsDeletedAfterDisplay() {
        val storage = InMemoryAlertStorage()
        PendingAlertStore(storage).put(notificationResult)

        // A fresh store models the listener process having been killed.
        val afterRestart = PendingAlertStore(storage)
        val restored = afterRestart.take()

        assertNotNull(restored)
        assertEquals(Risk.HIGH, restored!!.risk)
        assertEquals(listOf("tk_ca_nhan", "ap_luc_thoi_gian"), restored.signals.map { it.code })
        assertTrue("Evidence is not restored", restored.signals.all { it.evidence.isEmpty() })
        assertTrue(restored.truncated)

        // Taken once, then gone.
        assertNull(afterRestart.take())
        assertTrue(storage.snapshot().isEmpty())
    }

    @Test
    fun anExpiredWarningIsNotShown() {
        val storage = InMemoryAlertStorage()
        var clock = 1_000L
        PendingAlertStore(storage, ttlMillis = 60_000, now = { clock }).put(notificationResult)

        clock += 120_000
        val expired = PendingAlertStore(storage, ttlMillis = 60_000, now = { clock })
        assertNull("A stale warning must not open a stale screen", expired.take())
    }
}
