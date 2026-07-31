package com.chan.app.notification

import java.security.MessageDigest

/**
 * Remembers which *occurrences* have already been analysed (§D2).
 *
 * Sprint 02 hashed package + key + content and suppressed that digest for ten
 * minutes. On a real phone that turned out to be wrong in the direction that
 * matters: a second scam message with the same wording in the same Zalo
 * conversation was indistinguishable from Android repeating one callback, so
 * the user was warned once and never again.
 *
 * The fix is to hash *when the message happened* alongside what it said. Zalo
 * re-posting the same notification for a read receipt keeps the same occurrence
 * token and is dropped; a genuinely new message carries a newer timestamp and
 * is analysed, even when the text is identical.
 *
 * What is kept is a SHA-256 digest and the time it was claimed — never content.
 * The cache is in memory and bounded; process death resets it, which is
 * accepted: the cost is one duplicate analysis, not a missed warning.
 */
class NotificationOccurrenceCache(
    /**
     * Collapses the burst of callbacks Android fires for one occurrence. It
     * deliberately does not suppress a *new* occurrence carrying the same text.
     */
    private val maxEntries: Int = DEFAULT_MAX_ENTRIES,
    private val now: () -> Long = System::currentTimeMillis,
) {

    private val seen = LinkedHashMap<String, Long>()

    /** True the first time an occurrence is offered, false for every repeat. */
    @Synchronized
    fun claim(occurrenceDigest: String): Boolean {
        if (seen.containsKey(occurrenceDigest)) return false

        seen[occurrenceDigest] = now()
        while (seen.size > maxEntries) {
            val oldest = seen.keys.firstOrNull() ?: break
            seen.remove(oldest)
        }
        return true
    }

    @Synchronized
    fun clear() = seen.clear()

    @Synchronized
    fun size(): Int = seen.size

    companion object {
        private const val DEFAULT_MAX_ENTRIES = 64

        /**
         * `package + notification key + occurrence token + normalized content`,
         * hashed. The digest is one-way, so the cache cannot be read back into
         * message text, and the timestamp inside it is what makes a repeat of
         * the same sentence a new event rather than a duplicate.
         */
        fun digestOf(
            packageName: String,
            key: String,
            occurrenceToken: Long,
            normalizedContent: String,
        ): String {
            val bytes = MessageDigest.getInstance("SHA-256")
                .digest("$packageName|$key|$occurrenceToken|$normalizedContent".toByteArray(Charsets.UTF_8))
            return bytes.joinToString("") { "%02x".format(it) }
        }
    }
}
