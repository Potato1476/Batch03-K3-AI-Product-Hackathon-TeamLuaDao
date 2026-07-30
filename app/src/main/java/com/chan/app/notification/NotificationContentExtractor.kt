package com.chan.app.notification

/** The only package CHAN watches in Sprint 02. */
const val ZALO_PACKAGE = "com.zing.zalo"

/**
 * A plain-data copy of everything CHAN is willing to read from one posted
 * notification.
 *
 * The framework object is converted to this on the callback thread and then
 * released, so no `StatusBarNotification`, `Notification`, or `Bundle` is held
 * across the analysis. It also makes the whole extraction step a JVM unit test.
 */
data class NotificationSnapshot(
    val packageName: String,
    val key: String,
    val title: String? = null,
    val text: String? = null,
    val bigText: String? = null,
    val summaryText: String? = null,
    val textLines: List<String> = emptyList(),
    val messagingTexts: List<String> = emptyList(),
    val isOngoing: Boolean = false,
    val isGroupSummary: Boolean = false,
)

/** What survived extraction. [content] is held only for the current analysis. */
data class ExtractedNotification(
    val packageName: String,
    val key: String,
    val content: String,
    val truncated: Boolean,
)

/**
 * Turns a posted notification into analysable text, or nothing (§B3).
 *
 * Notification access is the *only* passive input in Sprint 02. CHAN does not
 * read Zalo's files, database, accessibility tree, or traffic, and this class
 * is the whole of the intake surface.
 *
 * Nothing here prints, stores, or returns content to a log. The caller gets one
 * string and is expected to drop it.
 */
class NotificationContentExtractor(
    private val ownPackage: String,
    private val watchedPackage: String = ZALO_PACKAGE,
    /**
     * Deterministic truncation markers. The service supplies the shared Rule
     * Bundle's `truncation_marker` patterns so Web and Android agree on what
     * "shortened" means; the defaults keep the extractor usable on its own.
     */
    private val truncationMarkers: List<Regex> = DEFAULT_TRUNCATION_MARKERS,
) {

    fun extract(snapshot: NotificationSnapshot): ExtractedNotification? {
        if (snapshot.packageName != watchedPackage) return null
        if (snapshot.packageName == ownPackage) return null
        // A group summary repeats what its children already said.
        if (snapshot.isGroupSummary) return null
        // Ongoing notifications are calls, uploads, and foreground services.
        if (snapshot.isOngoing) return null

        val segments = collapse(
            buildList {
                snapshot.title?.let { add(it) }
                snapshot.bigText?.let { add(it) }
                addAll(snapshot.messagingTexts)
                addAll(snapshot.textLines)
                snapshot.text?.let { add(it) }
            },
        )
        if (segments.isEmpty()) return null

        val joined = segments.joinToString("\n")
        val capped = joined.take(MAX_CONTENT_LENGTH)

        val truncated = capped.length < joined.length ||
            truncationMarkers.any { it.containsMatchIn(capped) } ||
            summaryPromisesMore(snapshot.summaryText, snapshot.textLines.size)

        return ExtractedNotification(
            packageName = snapshot.packageName,
            key = snapshot.key,
            content = capped,
            truncated = truncated,
        )
    }

    /**
     * Android hands the same sentence over in several extras at once — `text` is
     * usually a prefix of `bigText`, and a messaging-style line often repeats
     * the title. Keeping all of them would inflate the request and teach the
     * model that repetition is a signal.
     */
    private fun collapse(candidates: List<String>): List<String> {
        val accepted = mutableListOf<String>()
        for (candidate in candidates.map { it.trim().replace(WHITESPACE, " ") }) {
            if (candidate.isEmpty()) continue
            if (accepted.any { it.contains(candidate, ignoreCase = true) }) continue
            // A richer segment supersedes the shorter one it already contains.
            accepted.removeAll { candidate.contains(it, ignoreCase = true) }
            accepted.add(candidate)
        }
        return accepted
    }

    /**
     * "5 tin nhắn mới" next to two visible lines means three messages exist that
     * CHAN cannot see. A count that matches what we have is not truncation.
     */
    private fun summaryPromisesMore(summaryText: String?, visibleLines: Int): Boolean {
        val summary = summaryText?.trim().orEmpty()
        if (summary.isEmpty()) return false
        val count = MESSAGE_COUNT.find(summary)?.groupValues?.getOrNull(1)?.toIntOrNull() ?: return false
        return count > maxOf(visibleLines, 1)
    }

    companion object {
        /** The API's `text` bound; longer content is cut and marked truncated. */
        const val MAX_CONTENT_LENGTH = 4_000

        private val WHITESPACE = Regex("\\s+")
        private val MESSAGE_COUNT = Regex("(\\d+)\\s*(?:tin\\s*nhắn|tin\\s*nhan|new\\s*messages?|messages?)", RegexOption.IGNORE_CASE)

        val DEFAULT_TRUNCATION_MARKERS: List<Regex> = listOf(
            Regex("…$"),
            Regex("\\.\\.\\.$"),
        )
    }
}
