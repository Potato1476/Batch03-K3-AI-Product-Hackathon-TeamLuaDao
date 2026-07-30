package com.chan.app.domain

/**
 * Risk is intentionally restricted. There is deliberately NO `SAFE` value: CHAN
 * must never tell a person a message, caller, account, phone number, or link is
 * safe. `UNKNOWN` means "Chưa phát hiện dấu hiệu" — the absence of a detected
 * signal, not reassurance. (Backend invariant I6.)
 */
enum class Risk {
    HIGH,
    MEDIUM,
    UNKNOWN,
    ;

    companion object {
        /** Maps the backend's lowercase wire value; anything unknown is [UNKNOWN]. */
        fun fromWire(value: String?): Risk = when (value) {
            "high" -> HIGH
            "medium" -> MEDIUM
            else -> UNKNOWN
        }
    }
}

/**
 * How the content to analyze arrived. [wireValue] is the backend `input_mode`
 * enum; only these three are used in Sprint 02.
 */
enum class InputMode(val wireValue: String) {
    /** Typed, pasted, or dictated-then-reviewed by the user. */
    MANUAL("manual"),

    /** Arrived through the Android share sheet. */
    SHARE("share"),

    /** Read passively from a watched app's notification. */
    NOTIFICATION("notification"),
}

/** What the community lookup is checking. [wireValue] is the API path segment. */
enum class LookupType(val wireValue: String) {
    ACCOUNT("account"),
    PHONE("phone"),
    URL("url"),
}

/**
 * One manipulation signal returned by the backend. [code] is the server's
 * taxonomy string; the UI — never the data layer — maps it to a localized
 * label. [evidence] is already redacted by the backend (`<ACCOUNT>`,
 * `<AMOUNT:trieu>`, …) and must never be "restored".
 */
data class AnalysisSignal(
    val code: String,
    val confidence: Double,
    val evidence: String,
)

/** A hotline the user can call themselves, rather than trusting an inbound number. */
data class VerifiedHotline(val name: String, val number: String)

/**
 * Result of analyzing a message. Contains no Android resource IDs: the data
 * layer stays free of UI concerns so the same model serves the screen, the
 * notification pipeline, and the tests.
 */
data class AnalysisResult(
    val risk: Risk,
    val score: Double,
    val signals: List<AnalysisSignal>,
    val explanation: String,
    val questions: List<String>,
    val verifiedHotline: VerifiedHotline?,
    val actions: List<String>,
    val engineVersion: String,
    val ruleBundleVersion: String,
    /** Source content was shortened before CHAN saw it (§B4). */
    val truncated: Boolean = false,
    /** True when L0/L1 decided this locally and no byte left the device. */
    val decidedOnDevice: Boolean = false,
) {
    val hitCodes: Set<String> get() = signals.map { it.code }.toSet()
}

/**
 * Result of a k-anonymity community lookup. The raw value never appears here —
 * matching happens on-device against the returned hash cluster.
 */
data class LookupResult(
    val type: LookupType,
    val matched: Boolean,
    val reportCount: Int,
    val lastReportedDaysAgo: Int?,
    val origin: String?,
    /** Server-provided copy for the no-match case. Never says "safe". */
    val noMatchMessage: String,
    val bundleVersion: String,
) {
    /** A reported indicator is a caution, never an official conclusion. */
    val risk: Risk get() = if (matched) Risk.MEDIUM else Risk.UNKNOWN
}

/**
 * Why a request could not be completed, in terms the UI can turn into normal
 * language. Never carries a status code, stack trace, or server identifier.
 */
enum class FailureReason {
    /** No usable network connection. */
    OFFLINE,

    /** The request exceeded the interactive timeout. */
    TIMEOUT,

    /** 429 — the user checked too many times in a row. */
    RATE_LIMITED,

    /** 5xx, or the analysis service is not ready. */
    BACKEND_UNAVAILABLE,

    /** The device's Rule Bundle disagrees with the server's, twice in a row. */
    BUNDLE_MISMATCH,

    /** The value the user typed is not a usable account/phone/link. */
    INVALID_INPUT,

    /** Anything else. Deliberately coarse — details would leak into the UI. */
    UNEXPECTED,
}

/** A success/failure pair with no exception, message, or HTTP detail attached. */
sealed interface ChanOutcome<out T> {
    data class Success<T>(val value: T) : ChanOutcome<T>
    data class Failure(val reason: FailureReason) : ChanOutcome<Nothing>
}
