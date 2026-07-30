package com.chan.app.notification

import java.security.MessageDigest

/**
 * Remembers which notifications have already been analysed (§B4).
 *
 * Zalo re-posts a conversation notification on every edit, read receipt, and
 * new message in the same thread. Without this, one conversation would be sent
 * to `/v1/analyze` repeatedly.
 *
 * What is kept is a SHA-256 digest and a timestamp — never content. The cache
 * is in memory and bounded; process death resets it, which Sprint 02 accepts.
 */
class NotificationDedupeCache(
    private val ttlMillis: Long = DEFAULT_TTL_MILLIS,
    private val maxEntries: Int = DEFAULT_MAX_ENTRIES,
    private val now: () -> Long = System::currentTimeMillis,
) {

    private val seen = LinkedHashMap<String, Long>()

    /** True the first time a digest is offered, false while it is still fresh. */
    @Synchronized
    fun claim(digest: String): Boolean {
        val timestamp = now()
        seen.entries.removeAll { timestamp - it.value > ttlMillis }

        val previous = seen[digest]
        if (previous != null && timestamp - previous <= ttlMillis) return false

        seen[digest] = timestamp
        while (seen.size > maxEntries) {
            val oldest = seen.keys.firstOrNull() ?: break
            seen.remove(oldest)
        }
        return true
    }

    @Synchronized
    fun clear() = seen.clear()

    companion object {
        private const val DEFAULT_TTL_MILLIS = 10L * 60 * 1000
        private const val DEFAULT_MAX_ENTRIES = 64

        /**
         * `package + notification key + normalized content`, hashed. The digest
         * is one-way, so the cache cannot be read back into message text.
         */
        fun digestOf(packageName: String, key: String, normalizedContent: String): String {
            val bytes = MessageDigest.getInstance("SHA-256")
                .digest("$packageName|$key|$normalizedContent".toByteArray(Charsets.UTF_8))
            return bytes.joinToString("") { "%02x".format(it) }
        }
    }
}
