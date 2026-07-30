package com.chan.app.data.rules

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

/**
 * The shared Rule Bundle (`codebase/rules/bundle.json`), parsed.
 *
 * This file is the single source of truth for the on-device rule layer. Web
 * (TypeScript) and Android (Kotlin) compile the same document, which is why
 * their L1 behaviour cannot drift. Nothing in this package may hardcode a scam
 * regex, keyword, or threshold in Kotlin.
 *
 * Bundle data itself is safe to persist — it contains no user content.
 */
@Serializable
data class RuleBundle(
    @SerialName("bundle_version") val bundleVersion: String = "",
    @SerialName("schema_version") val schemaVersion: Int = 0,
    val l0: L0Config = L0Config(),
    val l1: L1Config = L1Config(),
    @SerialName("watchlist_packages") val watchlistPackages: List<String> = emptyList(),
    @SerialName("risk_labels") val riskLabels: Map<String, String> = emptyMap(),
    @SerialName("forbidden_labels") val forbiddenLabels: List<String> = emptyList(),
)

@Serializable
data class L0Config(
    @SerialName("unicode_form") val unicodeForm: String = "NFKC",
    val lowercase: Boolean = true,
    @SerialName("collapse_whitespace") val collapseWhitespace: Boolean = true,
    @SerialName("strip_invisible") val stripInvisible: List<String> = emptyList(),
    @SerialName("strip_diacritics_for_matching") val stripDiacriticsForMatching: Boolean = true,
    val teencode: Map<String, String> = emptyMap(),
)

@Serializable
data class L1Config(
    val gate: GateConfig = GateConfig(),
    @SerialName("otp_block") val otpBlock: OtpBlockConfig = OtpBlockConfig(),
    @SerialName("local_signals") val localSignals: Map<String, LocalSignalRule> = emptyMap(),
)

@Serializable
data class GateConfig(
    @SerialName("min_score_to_call_server") val minScoreToCallServer: Double = 1.0,
    @SerialName("min_length_to_call_server") val minLengthToCallServer: Int = Int.MAX_VALUE,
    @SerialName("always_call_when_local_signal") val alwaysCallWhenLocalSignal: List<String> = emptyList(),
)

@Serializable
data class OtpBlockConfig(
    val patterns: List<String> = emptyList(),
)

@Serializable
data class LocalSignalRule(
    val patterns: List<String> = emptyList(),
    @SerialName("boost_signal") val boostSignal: String? = null,
    val boost: Double = 0.0,
)

/** Thrown when a candidate bundle is not usable. Never carries user content. */
class RuleBundleInvalid(val code: String) : Exception(code)

object RuleBundleParser {

    /** The only schema revision this build knows how to execute. */
    const val SUPPORTED_SCHEMA_VERSION: Int = 1

    private val json = Json {
        ignoreUnknownKeys = true
        isLenient = false
    }

    /**
     * Parses and validates a candidate bundle. A bundle is replaced only after
     * this succeeds, so a malformed server response can never leave the app
     * without a working rule layer.
     */
    fun parse(raw: String): RuleBundle {
        val bundle = try {
            json.decodeFromString(RuleBundle.serializer(), raw)
        } catch (error: Exception) {
            throw RuleBundleInvalid("bundle_unparsable")
        }
        validate(bundle)
        return bundle
    }

    private fun validate(bundle: RuleBundle) {
        if (bundle.bundleVersion.isBlank()) throw RuleBundleInvalid("bundle_version_missing")
        if (bundle.schemaVersion != SUPPORTED_SCHEMA_VERSION) {
            throw RuleBundleInvalid("bundle_schema_unsupported")
        }
        if (bundle.l0.unicodeForm != "NFKC") throw RuleBundleInvalid("bundle_unicode_form_unsupported")
        if (bundle.l1.otpBlock.patterns.isEmpty()) throw RuleBundleInvalid("bundle_otp_block_empty")
        if (bundle.l1.localSignals.isEmpty()) throw RuleBundleInvalid("bundle_local_signals_empty")
        if (bundle.l1.gate.minLengthToCallServer < 0) throw RuleBundleInvalid("bundle_gate_invalid")
    }
}
