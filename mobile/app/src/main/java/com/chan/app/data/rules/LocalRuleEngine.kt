package com.chan.app.data.rules

/** What the on-device rule layer decided about a piece of content. */
enum class LocalVerdict {
    /** I1: an OTP was requested or quoted. Decide here; send nothing. */
    OTP_BLOCK,

    /** I3: below the gate. Answer `unknown` locally; send nothing. */
    BELOW_GATE,

    /** Above the gate. The backend may see this one request. */
    CALL_SERVER,
}

/**
 * The outcome of L0+L1. [localSignals] is the L1 vocabulary (bundle rule
 * names), not the eight-signal taxonomy the backend returns.
 */
data class LocalDecision(
    val verdict: LocalVerdict,
    val localSignals: List<String>,
    val truncated: Boolean,
    val score: Double,
)

/**
 * The deterministic rule layer, ported from `apps/web/src/engine.ts`.
 *
 * Every pattern, threshold, and name comes from the [RuleBundle]. Adding a
 * scam regex to this file would break Web/Android equivalence and is
 * forbidden by the architecture.
 *
 * The engine holds no content: [evaluate] takes a string, returns a verdict,
 * and keeps nothing.
 */
class LocalRuleEngine(val bundle: RuleBundle) {

    /** Compiled once per bundle. Patterns that fail to compile are skipped. */
    private val otpPatterns: List<Regex> = bundle.l1.otpBlock.patterns.mapNotNull(::compile)
    private val signalPatterns: Map<String, List<Regex>> =
        bundle.l1.localSignals.mapValues { (_, rule) -> rule.patterns.mapNotNull(::compile) }

    fun normalize(text: String): String = TextNormalizer.normalize(text, bundle.l0)

    fun evaluate(text: String): LocalDecision {
        val normalized = normalize(text)

        if (otpPatterns.any { it.containsMatchIn(normalized) }) {
            // The web port returns here too, before any local-signal matching:
            // nothing is sent, so there is no signal list to build.
            return LocalDecision(LocalVerdict.OTP_BLOCK, emptyList(), truncated = false, score = 1.0)
        }

        val matched = signalPatterns
            .filterValues { patterns -> patterns.any { it.containsMatchIn(normalized) } }
            .keys
            .toList()
        val truncated = matched.contains(TRUNCATION_SIGNAL)
        val score = matched.sumOf { name ->
            (bundle.l1.localSignals[name]?.boost ?: 0.0).coerceAtLeast(0.0)
        }
        val gate = bundle.l1.gate
        val alwaysCall = matched.any { gate.alwaysCallWhenLocalSignal.contains(it) }

        val belowGate = normalized.length < gate.minLengthToCallServer ||
            (!alwaysCall && score < gate.minScoreToCallServer)

        return LocalDecision(
            verdict = if (belowGate) LocalVerdict.BELOW_GATE else LocalVerdict.CALL_SERVER,
            localSignals = matched,
            truncated = truncated,
            score = score,
        )
    }

    /** True when [name] is a rule this bundle knows — used to filter what we send. */
    fun knowsLocalSignal(name: String): Boolean = bundle.l1.localSignals.containsKey(name)

    private companion object {
        const val TRUNCATION_SIGNAL = "truncation_marker"
    }
}

/** Placeholder the bundle uses for "handled by otp_block"; never compiled. */
private const val OTP_BLOCK_PLACEHOLDER = "__see_otp_block__"

/**
 * The bundle stores patterns in a portable form with a leading `(?i)`. The web
 * port strips it and sets the flag; Kotlin does the same so the two engines
 * interpret the same source identically.
 */
private fun compile(source: String): Regex? {
    if (source.isEmpty() || source == OTP_BLOCK_PLACEHOLDER) return null
    val caseInsensitive = source.startsWith("(?i)")
    val pattern = if (caseInsensitive) source.removePrefix("(?i)") else source
    val options = if (caseInsensitive) setOf(RegexOption.IGNORE_CASE) else emptySet()
    return try {
        Regex(pattern, options)
    } catch (error: IllegalArgumentException) {
        null
    }
}
