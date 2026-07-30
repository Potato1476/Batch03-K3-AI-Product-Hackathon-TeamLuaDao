package com.chan.app.data

import com.chan.app.data.lookup.IndicatorHasher
import com.chan.app.data.lookup.IndicatorInvalid
import com.chan.app.data.net.AnalyzeRequestDto
import com.chan.app.data.net.AnalyzeResponseDto
import com.chan.app.data.net.ChanApi
import com.chan.app.data.net.ChanApiFailure
import com.chan.app.data.rules.LocalDecision
import com.chan.app.data.rules.LocalVerdict
import com.chan.app.data.rules.RuleBundleStore
import com.chan.app.domain.AnalysisResult
import com.chan.app.domain.AnalysisSignal
import com.chan.app.domain.ChanOutcome
import com.chan.app.domain.ChanRepository
import com.chan.app.domain.FailureReason
import com.chan.app.domain.InputMode
import com.chan.app.domain.LookupResult
import com.chan.app.domain.LookupType
import com.chan.app.domain.Risk
import com.chan.app.domain.VerifiedHotline
import kotlinx.coroutines.CancellationException

/**
 * The production repository (§A4–A7).
 *
 * The order of operations is the privacy design, not an implementation detail:
 *
 * 1. L0/L1 runs on the device against the shared Rule Bundle;
 * 2. an OTP is answered here and nothing is sent (I1);
 * 3. content below the gate is answered here and nothing is sent (I3);
 * 4. only what is left crosses the network, once, and is then released.
 *
 * Nothing in this class logs, caches, or persists message text or lookup
 * values. The one exception to "never retry automatically" is a Rule Bundle
 * version mismatch, which §A7 requires be refreshed and retried exactly once.
 */
class LiveChanRepository(
    private val api: ChanApi,
    private val bundles: RuleBundleStore,
    private val now: () -> Long = System::currentTimeMillis,
) : ChanRepository {

    override suspend fun analyzeMessage(
        message: String,
        inputMode: InputMode,
        appPackage: String?,
        truncated: Boolean,
    ): ChanOutcome<AnalysisResult> {
        val capped = message.take(MAX_TEXT_LENGTH)
        val shortened = truncated || message.length > MAX_TEXT_LENGTH
        if (capped.isBlank()) return ChanOutcome.Failure(FailureReason.INVALID_INPUT)

        return try {
            analyzeOnce(capped, inputMode, appPackage, shortened, allowBundleRefresh = true)
        } catch (error: ChanApiFailure) {
            ChanOutcome.Failure(error.reason)
        } catch (error: CancellationException) {
            throw error
        } catch (error: Exception) {
            ChanOutcome.Failure(FailureReason.UNEXPECTED)
        }
    }

    private suspend fun analyzeOnce(
        text: String,
        inputMode: InputMode,
        appPackage: String?,
        truncated: Boolean,
        allowBundleRefresh: Boolean,
    ): ChanOutcome<AnalysisResult> {
        val engine = bundles.engine()
        val decision = engine.evaluate(text)
        val bundleVersion = engine.bundle.bundleVersion

        when (decision.verdict) {
            LocalVerdict.OTP_BLOCK -> return ChanOutcome.Success(localOtpHigh(bundleVersion, truncated))
            LocalVerdict.BELOW_GATE -> return ChanOutcome.Success(localUnknown(bundleVersion, truncated))
            LocalVerdict.CALL_SERVER -> Unit
        }

        val request = requestFor(text, inputMode, appPackage, decision, truncated)
        return try {
            ChanOutcome.Success(toDomain(api.analyze(request), truncated))
        } catch (error: ChanApiFailure) {
            if (error.reason == FailureReason.BUNDLE_MISMATCH && allowBundleRefresh) {
                // §A7: the client is running older rules than the server. Refresh
                // once, then re-run L0/L1 — the newer bundle may even decide this
                // locally. A second mismatch stops and offers a retry path.
                bundles.refresh()
                analyzeOnce(text, inputMode, appPackage, truncated, allowBundleRefresh = false)
            } else {
                throw error
            }
        }
    }

    private fun requestFor(
        text: String,
        inputMode: InputMode,
        appPackage: String?,
        decision: LocalDecision,
        truncated: Boolean,
    ) = AnalyzeRequestDto(
        text = text,
        source = SOURCE_ANDROID,
        inputMode = inputMode.wireValue,
        // Only a notification names its source app; anything else stays null.
        appPackage = appPackage.takeIf { inputMode == InputMode.NOTIFICATION },
        localSignals = decision.localSignals.take(MAX_LOCAL_SIGNALS),
        truncated = truncated || decision.truncated,
        locale = LOCALE,
    )

    override suspend fun lookup(type: LookupType, value: String): ChanOutcome<LookupResult> {
        val fullHash = try {
            IndicatorHasher.hash(type, value)
        } catch (error: IndicatorInvalid) {
            return ChanOutcome.Failure(FailureReason.INVALID_INPUT)
        }

        return try {
            val response = api.lookup(type.wireValue, IndicatorHasher.prefixOf(fullHash))
            // The cluster comes back whole; the comparison that reveals the answer
            // happens here, on the device, and the server never learns the result.
            val match = response.hashes.firstOrNull { it.hash.equals(fullHash, ignoreCase = true) }
            ChanOutcome.Success(
                LookupResult(
                    type = type,
                    matched = match != null,
                    reportCount = match?.reportCount ?: 0,
                    lastReportedDaysAgo = IsoTimestamps.daysAgo(match?.lastSeen, now()),
                    origin = match?.origin,
                    noMatchMessage = response.noMatchMessage.ifBlank { DEFAULT_NO_MATCH },
                    bundleVersion = response.bundleVersion,
                ),
            )
        } catch (error: ChanApiFailure) {
            ChanOutcome.Failure(error.reason)
        } catch (error: CancellationException) {
            throw error
        } catch (error: Exception) {
            ChanOutcome.Failure(FailureReason.UNEXPECTED)
        }
    }

    private fun toDomain(dto: AnalyzeResponseDto, truncated: Boolean) = AnalysisResult(
        risk = Risk.fromWire(dto.risk),
        score = dto.score,
        signals = dto.signals.map { AnalysisSignal(it.code, it.confidence, it.evidence) },
        explanation = dto.explanation,
        questions = dto.questions,
        verifiedHotline = dto.verifiedHotline?.let { VerifiedHotline(it.name, it.number) },
        actions = dto.actions,
        engineVersion = dto.engineVersion,
        ruleBundleVersion = dto.ruleBundleVersion,
        truncated = truncated,
        decidedOnDevice = false,
    )

    /**
     * I1: an OTP request is decided here with an empty evidence string. Quoting
     * the message back would echo the very digits that must not travel.
     */
    private fun localOtpHigh(bundleVersion: String, truncated: Boolean) = AnalysisResult(
        risk = Risk.HIGH,
        score = 1.0,
        signals = listOf(AnalysisSignal(code = "yeu_cau_otp", confidence = 1.0, evidence = "")),
        explanation = "Tin nhắn này đang hỏi mã xác nhận của bác. Đừng đọc mã cho bất kỳ ai.",
        questions = listOf("Tại sao họ cần mã xác nhận của tôi?"),
        verifiedHotline = null,
        actions = listOf("report", "share_to_guardian"),
        engineVersion = LOCAL_ENGINE_VERSION,
        ruleBundleVersion = bundleVersion,
        truncated = truncated,
        decidedOnDevice = true,
    )

    /** Below the gate. "Chưa phát hiện dấu hiệu" — never "an toàn" (I6). */
    private fun localUnknown(bundleVersion: String, truncated: Boolean) = AnalysisResult(
        risk = Risk.UNKNOWN,
        score = 0.0,
        signals = emptyList(),
        explanation = "Chưa phát hiện dấu hiệu.",
        questions = emptyList(),
        verifiedHotline = null,
        actions = emptyList(),
        engineVersion = LOCAL_ENGINE_VERSION,
        ruleBundleVersion = bundleVersion,
        truncated = truncated,
        decidedOnDevice = true,
    )

    private companion object {
        const val SOURCE_ANDROID = "android"
        const val LOCALE = "vi-VN"
        const val LOCAL_ENGINE_VERSION = "l1-local"

        /** The API's `text` bound. Longer content is capped, not rejected. */
        const val MAX_TEXT_LENGTH = 4_000
        const val MAX_LOCAL_SIGNALS = 16
        const val DEFAULT_NO_MATCH = "Chưa có báo cáo về thông tin này."
    }
}
