package com.chan.app

import com.chan.app.notification.NotificationContentExtractor
import com.chan.app.notification.NotificationOccurrenceCache
import com.chan.app.notification.NotificationSnapshot
import com.chan.app.notification.ZALO_PACKAGE
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Notification intake (§B3, §B4).
 *
 * This is the only passive input CHAN has, so what it refuses to read matters
 * as much as what it reads. Everything here runs on the JVM because the
 * extractor takes a plain snapshot rather than a framework object.
 */
class NotificationIntakeTest {

    private val extractor = NotificationContentExtractor(ownPackage = "com.chan.app")

    private fun zalo(
        key: String = "0|com.zing.zalo|1|null|10123",
        title: String? = null,
        text: String? = null,
        bigText: String? = null,
        summaryText: String? = null,
        textLines: List<String> = emptyList(),
        messagingTexts: List<String> = emptyList(),
        isOngoing: Boolean = false,
        isGroupSummary: Boolean = false,
    ) = NotificationSnapshot(
        packageName = ZALO_PACKAGE,
        key = key,
        title = title,
        text = text,
        bigText = bigText,
        summaryText = summaryText,
        textLines = textLines,
        messagingTexts = messagingTexts,
        isOngoing = isOngoing,
        isGroupSummary = isGroupSummary,
    )

    @Test
    fun bigTextAndTextLinesCombineWithoutDuplication() {
        val extracted = extractor.extract(
            zalo(
                title = "Anh Minh",
                text = "Bác chuyển giúp cháu 5 triệu",
                bigText = "Bác chuyển giúp cháu 5 triệu vào tài khoản này trước 5 giờ chiều nhé",
                textLines = listOf("Bác chuyển giúp cháu 5 triệu", "Cháu đang cần gấp"),
            ),
        )

        assertNotNull(extracted)
        val content = extracted!!.content
        // `text` is a prefix of `bigText`; only the richer one survives.
        assertEquals(1, occurrencesOf(content, "Bác chuyển giúp cháu 5 triệu"))
        assertTrue(content.contains("trước 5 giờ chiều"))
        assertTrue("A genuinely new line is kept", content.contains("Cháu đang cần gấp"))
        assertTrue(content.contains("Anh Minh"))
    }

    @Test
    fun aTitleAlreadyContainedInTheBodyIsNotRepeated() {
        val extracted = extractor.extract(
            zalo(title = "Cháu cần tiền", bigText = "Cháu cần tiền gấp, bác giúp cháu nhé"),
        )
        assertEquals("Cháu cần tiền gấp, bác giúp cháu nhé", extracted?.content)
    }

    @Test
    fun messagingStyleMessagesAreRead() {
        val extracted = extractor.extract(
            zalo(title = "Nhóm gia đình", messagingTexts = listOf("Bác ơi", "Chuyển giúp cháu nhé")),
        )
        assertTrue(extracted!!.content.contains("Bác ơi"))
        assertTrue(extracted.content.contains("Chuyển giúp cháu nhé"))
    }

    @Test
    fun nonZaloNotificationsAreIgnored() {
        val others = listOf(
            "com.facebook.orca",
            "com.google.android.apps.messaging",
            "org.telegram.messenger",
            "com.chan.app",
        )
        others.forEach { packageName ->
            val snapshot = NotificationSnapshot(
                packageName = packageName,
                key = "0|$packageName|1|null|1",
                text = "Bác chuyển tiền ngay lập tức nhé",
            )
            assertNull("$packageName must not be read", extractor.extract(snapshot))
        }
    }

    @Test
    fun groupSummariesOngoingEmptyAndBlankNotificationsAreIgnored() {
        assertNull("group summary", extractor.extract(zalo(text = "3 tin nhắn mới", isGroupSummary = true)))
        assertNull("ongoing", extractor.extract(zalo(text = "Đang gọi…", isOngoing = true)))
        assertNull("no content at all", extractor.extract(zalo()))
        assertNull("blank content", extractor.extract(zalo(title = "   ", text = "")))
    }

    @Test
    fun oneOccurrenceIsClaimedOnlyOnce() {
        val cache = NotificationOccurrenceCache(now = { 0L })
        val occurrence = NotificationOccurrenceCache.digestOf(
            packageName = ZALO_PACKAGE,
            key = "key-1",
            occurrenceToken = 5_000L,
            normalizedContent = "bac chuyen tien ngay",
        )

        assertTrue("first sighting", cache.claim(occurrence))
        assertFalse("a re-post of the same occurrence is dropped", cache.claim(occurrence))
    }

    @Test
    fun theSameWordsAtANewMomentAreANewOccurrence() {
        val cache = NotificationOccurrenceCache(now = { 0L })
        fun occurrence(token: Long) = NotificationOccurrenceCache.digestOf(
            packageName = ZALO_PACKAGE,
            key = "key-1",
            occurrenceToken = token,
            normalizedContent = "bac chuyen tien ngay",
        )

        assertTrue(cache.claim(occurrence(5_000L)))
        // Sprint 02 suppressed this for ten minutes and the user was never
        // warned about the second message (§D1).
        assertTrue("A new message with the same words must be analysed", cache.claim(occurrence(6_000L)))

        // A different message in the same conversation is still analysed.
        assertTrue(
            cache.claim(
                NotificationOccurrenceCache.digestOf(ZALO_PACKAGE, "key-1", 5_000L, "noi dung khac"),
            ),
        )
    }

    @Test
    fun theOccurrenceCacheKeepsDigestsRatherThanContent() {
        val content = "bac chuyen 20 trieu vao tai khoan 19001234567890"
        val digest = NotificationOccurrenceCache.digestOf(ZALO_PACKAGE, "key-1", 5_000L, content)

        assertTrue(digest.matches(Regex("[0-9a-f]{64}")))
        assertFalse(digest.contains("19001234567890"))
        assertFalse(digest.contains("chuyen"))
    }

    @Test
    fun theOccurrenceCacheStaysBounded() {
        val cache = NotificationOccurrenceCache(maxEntries = 8, now = { 0L })
        repeat(50) { index ->
            assertTrue(
                cache.claim(
                    NotificationOccurrenceCache.digestOf(
                        ZALO_PACKAGE,
                        "key-$index",
                        index.toLong(),
                        "noi dung $index",
                    ),
                ),
            )
        }
        // The oldest entries were evicted, so an early digest is claimable again.
        assertTrue(
            cache.claim(NotificationOccurrenceCache.digestOf(ZALO_PACKAGE, "key-0", 0L, "noi dung 0")),
        )
    }

    // --- truncation --------------------------------------------------------

    @Test
    fun anEllipsisMarksTheContentAsTruncated() {
        assertTrue(extractor.extract(zalo(bigText = "Bác chuyển giúp cháu ngay…"))!!.truncated)
        assertTrue(extractor.extract(zalo(bigText = "Bác chuyển giúp cháu ngay..."))!!.truncated)
    }

    @Test
    fun aSummaryPromisingMoreMessagesMarksTruncation() {
        val extracted = extractor.extract(
            zalo(
                summaryText = "5 tin nhắn mới",
                textLines = listOf("Bác ơi", "Cháu cần tiền"),
            ),
        )
        assertTrue("Three messages exist that CHAN cannot see", extracted!!.truncated)
    }

    @Test
    fun aShortMessageIsNotTruncated() {
        val extracted = extractor.extract(zalo(text = "Bác ăn cơm chưa"))
        assertFalse("Short is not the same as shortened", extracted!!.truncated)
    }

    @Test
    fun aSummaryThatMatchesTheVisibleLinesIsNotTruncation() {
        val extracted = extractor.extract(
            zalo(summaryText = "2 tin nhắn mới", textLines = listOf("Bác ơi", "Cháu cần tiền")),
        )
        assertFalse(extracted!!.truncated)
    }

    @Test
    fun contentIsCappedAtTheApiLimitAndDeclaredTruncated() {
        val long = "a".repeat(NotificationContentExtractor.MAX_CONTENT_LENGTH + 500)
        val extracted = extractor.extract(zalo(bigText = long))

        assertEquals(NotificationContentExtractor.MAX_CONTENT_LENGTH, extracted!!.content.length)
        assertTrue(extracted.truncated)
    }

    private fun occurrencesOf(haystack: String, needle: String): Int {
        if (needle.isEmpty() || haystack.length < needle.length) return 0
        return haystack.windowed(needle.length, 1) { it == needle }.count { it }
    }
}
