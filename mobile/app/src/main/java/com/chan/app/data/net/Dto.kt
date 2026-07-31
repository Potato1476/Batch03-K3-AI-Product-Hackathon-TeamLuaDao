package com.chan.app.data.net

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/**
 * Wire types for the public `/v1` Gateway contract.
 *
 * The request models mirror the server's Pydantic schemas exactly. The server
 * uses `extra="forbid"`, so an accidental extra field is a 422 — the shapes
 * here are asserted field-for-field by `AnalyzeRequestSchemaTest`.
 */

@Serializable
data class DeviceTokenRequestDto(
    val platform: String,
    @SerialName("push_token") val pushToken: String? = null,
)

@Serializable
data class DeviceTokenResponseDto(
    @SerialName("device_id") val deviceId: String = "",
    val token: String = "",
    @SerialName("expires_at") val expiresAt: String = "",
)

@Serializable
data class AnalyzeRequestDto(
    val text: String,
    val source: String,
    @SerialName("input_mode") val inputMode: String,
    @SerialName("app_package") val appPackage: String?,
    @SerialName("local_signals") val localSignals: List<String>,
    val truncated: Boolean,
    val locale: String,
)

@Serializable
data class SignalDto(
    val code: String = "",
    val confidence: Double = 0.0,
    val evidence: String = "",
)

@Serializable
data class HotlineDto(
    val name: String = "",
    val number: String = "",
)

@Serializable
data class AnalyzeResponseDto(
    @SerialName("analysis_id") val analysisId: String = "",
    val risk: String = "unknown",
    val score: Double = 0.0,
    val signals: List<SignalDto> = emptyList(),
    val explanation: String = "",
    val questions: List<String> = emptyList(),
    @SerialName("verified_hotline") val verifiedHotline: HotlineDto? = null,
    val actions: List<String> = emptyList(),
    @SerialName("engine_version") val engineVersion: String = "",
    @SerialName("rule_bundle_version") val ruleBundleVersion: String = "",
)

@Serializable
data class BlocklistHitDto(
    val hash: String = "",
    @SerialName("report_cnt") val reportCount: Int = 0,
    @SerialName("first_seen") val firstSeen: String = "",
    @SerialName("last_seen") val lastSeen: String = "",
    val origin: String = "",
)

@Serializable
data class LookupResponseDto(
    val prefix: String = "",
    val kind: String = "",
    val hashes: List<BlocklistHitDto> = emptyList(),
    @SerialName("cluster_size") val clusterSize: Int = 0,
    @SerialName("bundle_version") val bundleVersion: String = "",
    @SerialName("no_match_message") val noMatchMessage: String = "",
)
