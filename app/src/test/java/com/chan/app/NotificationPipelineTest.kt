package com.chan.app

import com.chan.app.domain.AnalysisResult
import com.chan.app.domain.ChanOutcome
import com.chan.app.domain.ChanRepository
import com.chan.app.domain.FailureReason
import com.chan.app.domain.InputMode
import com.chan.app.domain.LookupResult
import com.chan.app.domain.LookupType
import com.chan.app.domain.Risk
import com.chan.app.notification.AlertEventRotator
import com.chan.app.notification.NotificationContentExtractor
import com.chan.app.notification.NotificationOccurrenceCache
import com.chan.app.notification.NotificationPipeline
import com.chan.app.notification.NotificationSnapshot
import com.chan.app.notification.PipelineOutcome
import com.chan.app.notification.ProtectionTelemetry
import com.chan.app.notification.RestartableScope
import com.chan.app.notification.SafeAlertPublisher
import com.chan.app.notification.ZALO_PACKAGE
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Repeated Zalo detections (§D2–D5).
 *
 * Physical testing found that the first high-risk message warned and later ones
 * did not. Two mechanisms caused it: a ten-minute content-only suppression
 * window, and a fixed notification id that Android treated as an update to a
 * warning the user had already seen.
 *
 * The matrix below is the acceptance criterion for the fix. Every row states
 * how many repository calls and how many warnings one sequence must produce.
 */
class NotificationPipelineTest {

    private class RecordingPublisher(var succeeds: Boolean = true) : SafeAlertPublisher {
        val published = mutableListOf<Risk>()
        override fun publish(risk: Risk): Boolean {
            published += risk
            return succeeds
        }
    }

    /** A repository whose analysis throws, modelling an unexpected crash. */
    private class ExplodingRepository : ChanRepository {
        override suspend fun analyzeMessage(
            message: String,
            inputMode: InputMode,
            appPackage: String?,
            truncated: Boolean,
        ): ChanOutcome<AnalysisResult> = throw IllegalStateException("boom")

        override suspend fun lookup(type: LookupType, value: String): ChanOutcome<LookupResult> =
            throw IllegalStateException("boom")
    }

    /** Records what was handed to the pending-alert store, and in what order. */
    private class Harness(
        scanningEnabled: Boolean = true,
        val repository: FakeChanRepository = FakeChanRepository(),
    ) {
        var clock = 1_000L
        var scanning = scanningEnabled

        val occurrences = NotificationOccurrenceCache()
        val publisher = RecordingPublisher()
        val telemetry = ProtectionTelemetry(now = { clock })
        val stored = mutableListOf<AnalysisResult>()

        /** Publisher calls seen at the moment each result was stored. */
        val publishCountWhenStored = mutableListOf<Int>()

        private val extractor = NotificationContentExtractor(ownPackage = "com.chan.app")

        val pipeline = NotificationPipeline(
            scanningEnabled = { scanning },
            extract = { snapshot -> extractor.extract(snapshot) },
            // The production normalizer lowercases and strips accents; for the
            // pipeline the only property that matters is that it is stable.
            normalize = { content -> content.lowercase().trim() },
            occurrences = occurrences,
            repository = repository,
            pendingAlerts = { result ->
                stored += result
                publishCountWhenStored += publisher.published.size
            },
            alerts = publisher,
            telemetry = telemetry,
        )
    }

    private fun zalo(
        text: String,
        key: String = CONVERSATION_KEY,
        postTime: Long = 1_000L,
        messageTimestamps: List<Long> = emptyList(),
    ) = NotificationSnapshot(
        packageName = ZALO_PACKAGE,
        key = key,
        title = "Anh Minh",
        text = text,
        postTime = postTime,
        messageTimestamps = messageTimestamps,
    )

    // --- the acceptance matrix (§D5) ----------------------------------------

    @Test
    fun theSameOsCallbackDeliveredTwiceIsProcessedOnce() = runTest {
        val harness = Harness()
        val callback = zalo(SCAM_TEXT, messageTimestamps = listOf(5_000L))

        assertEquals(PipelineOutcome.ALERT_POSTED, harness.pipeline.process(callback))
        assertEquals(PipelineOutcome.DUPLICATE, harness.pipeline.process(callback))

        assertEquals(1, harness.repository.analyzeCalls.size)
        assertEquals(1, harness.publisher.published.size)
    }

    @Test
    fun theSameTextWithTheSameOccurrenceTimestampIsProcessedOnce() = runTest {
        val harness = Harness()

        // A presentation-only update: Zalo re-posts the notification with the
        // same message timestamp because a read receipt or ranking changed.
        harness.pipeline.process(zalo(SCAM_TEXT, postTime = 1_000L, messageTimestamps = listOf(5_000L)))
        harness.pipeline.process(zalo(SCAM_TEXT, postTime = 9_999L, messageTimestamps = listOf(5_000L)))

        assertEquals(1, harness.repository.analyzeCalls.size)
        assertEquals(1, harness.publisher.published.size)
    }

    @Test
    fun theSameTextWithALaterMessageTimestampIsAnalyzedAgain() = runTest {
        val harness = Harness()

        // The scammer sends the identical sentence again, as a new message.
        harness.pipeline.process(zalo(SCAM_TEXT, messageTimestamps = listOf(5_000L)))
        val second = harness.pipeline.process(zalo(SCAM_TEXT, messageTimestamps = listOf(6_000L)))

        assertEquals(PipelineOutcome.ALERT_POSTED, second)
        assertEquals(2, harness.repository.analyzeCalls.size)
        assertEquals(2, harness.publisher.published.size)
    }

    @Test
    fun aNotificationWithoutMessagingTimestampsFallsBackToPostTime() = runTest {
        val harness = Harness()

        harness.pipeline.process(zalo(SCAM_TEXT, postTime = 1_000L))
        harness.pipeline.process(zalo(SCAM_TEXT, postTime = 1_000L))
        harness.pipeline.process(zalo(SCAM_TEXT, postTime = 2_000L))

        assertEquals("Same post time is one occurrence", 2, harness.repository.analyzeCalls.size)
    }

    @Test
    fun differentTextInTheSameConversationIsNotSuppressed() = runTest {
        val harness = Harness()

        harness.pipeline.process(zalo(SCAM_TEXT, messageTimestamps = listOf(5_000L)))
        // Deliberately the same occurrence timestamp: content still differs.
        harness.pipeline.process(zalo(OTHER_TEXT, messageTimestamps = listOf(5_000L)))

        assertEquals(2, harness.repository.analyzeCalls.size)
    }

    @Test
    fun anUnknownResultDoesNotPreventTheNextNotification() = runTest {
        val harness = Harness()
        harness.repository.analysis = ChanOutcome.Success(unknownResult())

        val first = harness.pipeline.process(zalo(OTHER_TEXT, messageTimestamps = listOf(5_000L)))
        assertEquals(PipelineOutcome.LOCAL_LOW, first)
        assertTrue(harness.publisher.published.isEmpty())

        harness.repository.analysis = ChanOutcome.Success(FakeChanRepository.HIGH_RISK)
        val second = harness.pipeline.process(zalo(SCAM_TEXT, messageTimestamps = listOf(6_000L)))

        assertEquals(PipelineOutcome.ALERT_POSTED, second)
        assertEquals(2, harness.repository.analyzeCalls.size)
        assertEquals(1, harness.publisher.published.size)
    }

    @Test
    fun aFailedBackendCallDoesNotPreventTheNextNotification() = runTest {
        val harness = Harness()
        harness.repository.analysis = FakeChanRepository.failure(FailureReason.OFFLINE)

        assertEquals(
            PipelineOutcome.BACKEND_FAILURE,
            harness.pipeline.process(zalo(SCAM_TEXT, messageTimestamps = listOf(5_000L))),
        )

        harness.repository.analysis = ChanOutcome.Success(FakeChanRepository.HIGH_RISK)
        assertEquals(
            PipelineOutcome.ALERT_POSTED,
            harness.pipeline.process(zalo(SCAM_TEXT, messageTimestamps = listOf(6_000L))),
        )

        assertEquals(2, harness.repository.analyzeCalls.size)
        assertEquals(1, harness.publisher.published.size)
    }

    @Test
    fun aThrownFailureIsContainedAndTheNextCallbackStillWorks() = runTest {
        val harness = Harness()
        val first = NotificationPipeline(
            scanningEnabled = { true },
            extract = { snapshot -> NotificationContentExtractor("com.chan.app").extract(snapshot) },
            normalize = { it },
            occurrences = harness.occurrences,
            repository = ExplodingRepository(),
            pendingAlerts = {},
            alerts = harness.publisher,
            telemetry = harness.telemetry,
        )

        assertEquals(
            PipelineOutcome.BACKEND_FAILURE,
            first.process(zalo(SCAM_TEXT, messageTimestamps = listOf(5_000L))),
        )
        // A different pipeline instance around the same cache keeps working.
        assertEquals(
            PipelineOutcome.ALERT_POSTED,
            harness.pipeline.process(zalo(SCAM_TEXT, messageTimestamps = listOf(6_000L))),
        )
    }

    @Test
    fun aReconnectedListenerGetsAUsableProcessingScope() = runTest {
        val scope = RestartableScope()

        val first = scope.active()
        assertTrue(first.isActive)
        assertTrue("A live scope is reused", first === scope.active())

        // `onDestroy` cancels it. A returned cancelled scope would accept every
        // future callback and silently drop it.
        scope.cancel()
        assertFalse(first.isActive)

        val afterReconnect = scope.active()
        assertNotEquals(first, afterReconnect)
        assertTrue(afterReconnect.isActive)

        var ran = false
        afterReconnect.launch { ran = true }.join()
        assertTrue("The new scope must actually run work", ran)
    }

    @Test
    fun processingResumesAfterAListenerReconnect() = runTest {
        val harness = Harness()

        harness.pipeline.process(zalo(SCAM_TEXT, messageTimestamps = listOf(5_000L)))

        // A disconnect clears the in-memory occurrence cache, exactly as
        // `onDestroy` does. A reconnected listener must analyse again.
        harness.occurrences.clear()

        val afterReconnect = harness.pipeline.process(zalo(SCAM_TEXT, messageTimestamps = listOf(5_000L)))

        assertEquals(PipelineOutcome.ALERT_POSTED, afterReconnect)
        assertEquals(2, harness.repository.analyzeCalls.size)
        assertEquals(2, harness.publisher.published.size)
    }

    @Test
    fun twoDistinctHighRiskMessagesProduceTwoWarnings() = runTest {
        val harness = Harness()

        harness.pipeline.process(zalo(SCAM_TEXT, messageTimestamps = listOf(5_000L)))
        harness.pipeline.process(zalo(OTHER_TEXT, messageTimestamps = listOf(6_000L)))

        assertEquals(2, harness.repository.analyzeCalls.size)
        assertEquals(listOf(Risk.HIGH, Risk.HIGH), harness.publisher.published)
    }

    // --- the surrounding guarantees -----------------------------------------

    @Test
    fun scanningDisabledReadsNothingAtAll() = runTest {
        val harness = Harness(scanningEnabled = false)

        assertEquals(
            PipelineOutcome.SCANNING_DISABLED,
            harness.pipeline.process(zalo(SCAM_TEXT, messageTimestamps = listOf(5_000L))),
        )
        assertTrue(harness.repository.analyzeCalls.isEmpty())
        assertTrue(harness.publisher.published.isEmpty())
    }

    @Test
    fun theNewestResultIsStoredBeforeItsNotificationIsPosted() = runTest {
        val harness = Harness()

        harness.pipeline.process(zalo(SCAM_TEXT, messageTimestamps = listOf(5_000L)))
        harness.pipeline.process(zalo(OTHER_TEXT, messageTimestamps = listOf(6_000L)))

        // Each store happened before the matching publish, so a tap can never
        // open a result older than the warning that was shown (§D4).
        assertEquals(listOf(0, 1), harness.publishCountWhenStored)
        assertEquals(2, harness.stored.size)
    }

    @Test
    fun telemetryRecordsTimesAndCategoriesOnly() = runTest {
        val harness = Harness()

        harness.pipeline.process(zalo(SCAM_TEXT, messageTimestamps = listOf(5_000L)))

        val activity = harness.telemetry.activity.value
        assertEquals(1_000L, activity.lastCallbackAt)
        assertEquals(PipelineOutcome.ALERT_POSTED, activity.lastOutcome)
        assertEquals(1_000L, activity.lastAlertAt)

        // Nothing in the record can carry content: the whole type is timestamps
        // and one enum.
        val fields = activity.toString()
        assertFalse(fields.contains(SCAM_TEXT))
        assertFalse(fields.contains("Anh Minh"))
    }

    @Test
    fun aLowResultLeavesTheLastAlertTimeAlone() = runTest {
        val harness = Harness()
        harness.pipeline.process(zalo(SCAM_TEXT, messageTimestamps = listOf(5_000L)))
        val alertedAt = harness.telemetry.activity.value.lastAlertAt

        harness.repository.analysis = ChanOutcome.Success(unknownResult())
        harness.clock = 2_000L
        harness.pipeline.process(zalo(OTHER_TEXT, messageTimestamps = listOf(6_000L)))

        assertEquals(PipelineOutcome.LOCAL_LOW, harness.telemetry.activity.value.lastOutcome)
        assertEquals(alertedAt, harness.telemetry.activity.value.lastAlertAt)
    }

    // --- occurrence tokens and the digest -----------------------------------

    @Test
    fun theOccurrenceTokenPrefersTheNewestMessagingTimestamp() {
        val extractor = NotificationContentExtractor(ownPackage = "com.chan.app")

        val withMessages = extractor.extract(
            NotificationSnapshot(
                packageName = ZALO_PACKAGE,
                key = CONVERSATION_KEY,
                text = SCAM_TEXT,
                postTime = 1_000L,
                messageTimestamps = listOf(4_000L, 9_000L, 2_000L),
            ),
        )
        assertEquals(9_000L, withMessages!!.occurrenceToken)

        val withoutMessages = extractor.extract(
            NotificationSnapshot(
                packageName = ZALO_PACKAGE,
                key = CONVERSATION_KEY,
                text = SCAM_TEXT,
                postTime = 1_234L,
            ),
        )
        assertEquals("Falls back to postTime", 1_234L, withoutMessages!!.occurrenceToken)
    }

    @Test
    fun theOccurrenceDigestKeepsNoContent() {
        val digest = NotificationOccurrenceCache.digestOf(
            packageName = ZALO_PACKAGE,
            key = CONVERSATION_KEY,
            occurrenceToken = 5_000L,
            normalizedContent = "bac chuyen 20 trieu vao tai khoan 19001234567890",
        )

        assertTrue(digest.matches(Regex("[0-9a-f]{64}")))
        assertFalse(digest.contains("19001234567890"))
        assertFalse(digest.contains("chuyen"))
    }

    @Test
    fun theOccurrenceCacheStaysBounded() {
        val cache = NotificationOccurrenceCache(maxEntries = 8)
        repeat(50) { index ->
            assertTrue(
                cache.claim(
                    NotificationOccurrenceCache.digestOf(ZALO_PACKAGE, CONVERSATION_KEY, index.toLong(), "noi dung"),
                ),
            )
        }
        assertTrue("The cache must not grow without limit", cache.size() <= 8)
    }

    // --- fresh alert events (§D4) -------------------------------------------

    @Test
    fun everyWarningGetsANewNotificationEventAndRetiresTheOldOne() {
        val rotator = AlertEventRotator()

        val first = rotator.next()
        val second = rotator.next()
        val third = rotator.next()

        assertEquals("The previous warning is retired", listOf(first.notificationId), second.cancelIds)
        assertEquals(listOf(second.notificationId), third.cancelIds)

        // A new event, not an update to one Android has already shown.
        assertNotEquals(first.notificationId, second.notificationId)
        assertNotEquals(second.notificationId, third.notificationId)
    }

    @Test
    fun theFirstWarningOfAProcessRetiresEveryBoundedIdBeforePosting() {
        // Rotation state dies with the process; Android's shade does not. A
        // warning posted before a restart can still be sitting under the very
        // id the new process is about to reuse, and `notify` on a live id is an
        // update — the Sprint 02 failure, across a restart.
        val rotator = AlertEventRotator()

        val first = rotator.next()

        assertEquals(
            "Every id CHAN could have left behind is cancelled first",
            AlertEventRotator.DEFAULT_IDS.toSet(),
            first.cancelIds.toSet(),
        )
        assertTrue(
            "Including the one about to be posted, so it becomes a new record",
            first.cancelIds.contains(first.notificationId),
        )
    }

    @Test
    fun aWarningSurvivingAProcessRestartIsReplacedByAFreshEvent() {
        // First process: one warning is posted and the process is killed with
        // that notification still visible.
        val beforeRestart = AlertEventRotator()
        val survivor = beforeRestart.next()
        val visible = mutableSetOf(survivor.notificationId)

        // Second process: rotation starts over at the same id.
        val afterRestart = AlertEventRotator()
        val fresh = afterRestart.next()

        // The publisher cancels before it posts.
        visible.removeAll(fresh.cancelIds.toSet())
        assertTrue("The stale warning must be gone first", visible.isEmpty())
        visible += fresh.notificationId

        assertEquals(1, visible.size)
        assertTrue(
            "The reused id is only reused after being cancelled",
            fresh.cancelIds.contains(fresh.notificationId),
        )

        // And the next warning in this process behaves normally again.
        val second = afterRestart.next()
        assertEquals(listOf(fresh.notificationId), second.cancelIds)
        assertNotEquals(fresh.notificationId, second.notificationId)
    }

    @Test
    fun alertIdsAreBoundedAndRecycled() {
        val rotator = AlertEventRotator()
        val ids = (1..12).map { rotator.next().notificationId }

        assertEquals("The ring is bounded", AlertEventRotator.DEFAULT_IDS.toSet(), ids.toSet())
        // Consecutive warnings are always distinct events.
        ids.zipWithNext().forEach { (previous, next) -> assertNotEquals(previous, next) }
    }

    @Test
    fun pendingIntentIdentityCannotBeRecycledFromAnOlderWarning() {
        val rotator = AlertEventRotator()
        val requestCodes = (1..12).map { rotator.next().requestCode }

        assertEquals(
            "Each warning owns a distinct PendingIntent identity",
            requestCodes.size,
            requestCodes.toSet().size,
        )
    }

    private fun unknownResult() = FakeChanRepository.HIGH_RISK.copy(
        risk = Risk.UNKNOWN,
        score = 0.0,
        signals = emptyList(),
        explanation = "Chưa phát hiện dấu hiệu.",
    )

    private companion object {
        const val CONVERSATION_KEY = "0|com.zing.zalo|1|null|10123"
        const val SCAM_TEXT = "Bác chuyển giúp cháu 5 triệu trước 5 giờ chiều nhé"
        const val OTHER_TEXT = "Bác đọc giúp cháu mã xác nhận vừa gửi tới máy bác"
    }
}
