package com.chan.app.data

import java.text.SimpleDateFormat
import java.util.Locale
import java.util.TimeZone

/**
 * Parses the ISO-8601 timestamps the Gateway returns.
 *
 * `java.time` needs core-library desugaring at this module's `minSdk`, and the
 * only thing CHAN does with these values is turn one into "n ngày trước", so a
 * small tolerant parser is cheaper than the toolchain change.
 */
object IsoTimestamps {

    private const val MILLIS_PER_DAY = 24L * 60 * 60 * 1000

    /** Returns epoch millis, or null when the value is not a timestamp we know. */
    fun parseEpochMillis(value: String?): Long? {
        if (value.isNullOrBlank()) return null
        val normalized = value.trim()
            .replace("Z", "+0000")
            .replace(Regex("([+-]\\d{2}):(\\d{2})$"), "$1$2")
        // Fractional seconds vary in width; SimpleDateFormat only accepts three.
        val trimmedFraction = normalized.replace(Regex("\\.(\\d{1,6})")) { match ->
            "." + match.groupValues[1].padEnd(3, '0').take(3)
        }
        for (pattern in PATTERNS) {
            val parsed = runCatching {
                SimpleDateFormat(pattern, Locale.US)
                    .apply { timeZone = TimeZone.getTimeZone("UTC") }
                    .parse(trimmedFraction)
            }.getOrNull()
            if (parsed != null) return parsed.time
        }
        return null
    }

    /** Whole days between [timestamp] and [nowMillis], never negative. */
    fun daysAgo(timestamp: String?, nowMillis: Long): Int? {
        val millis = parseEpochMillis(timestamp) ?: return null
        return ((nowMillis - millis) / MILLIS_PER_DAY).coerceAtLeast(0L).toInt()
    }

    private val PATTERNS = listOf(
        "yyyy-MM-dd'T'HH:mm:ss.SSSZ",
        "yyyy-MM-dd'T'HH:mm:ssZ",
        "yyyy-MM-dd'T'HH:mm:ss.SSS",
        "yyyy-MM-dd'T'HH:mm:ss",
    )
}
