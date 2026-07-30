package com.chan.app

import com.chan.app.domain.AnalysisResult
import com.chan.app.domain.AnalysisSignal
import com.chan.app.domain.ChanOutcome
import com.chan.app.domain.ChanRepository
import com.chan.app.domain.FailureReason
import com.chan.app.domain.InputMode
import com.chan.app.domain.LookupResult
import com.chan.app.domain.LookupType
import com.chan.app.domain.Risk

/**
 * Repository double for the state-machine tests.
 *
 * It lives in the test source set on purpose: Sprint 02 removed the demo
 * repository from production code, and a privacy test fails the build if a
 * canned repository ever becomes the app's default again.
 */
class FakeChanRepository(
    var analysis: ChanOutcome<AnalysisResult> = ChanOutcome.Success(HIGH_RISK),
    var lookupOutcome: ChanOutcome<LookupResult> = ChanOutcome.Success(MATCHED_LOOKUP),
) : ChanRepository {

    /** Recorded call arguments. Content is kept only so a test can assert on it. */
    val analyzeCalls = mutableListOf<Triple<String, InputMode, String?>>()
    val lookupCalls = mutableListOf<Pair<LookupType, String>>()

    override suspend fun analyzeMessage(
        message: String,
        inputMode: InputMode,
        appPackage: String?,
        truncated: Boolean,
    ): ChanOutcome<AnalysisResult> {
        analyzeCalls += Triple(message, inputMode, appPackage)
        return analysis
    }

    override suspend fun lookup(type: LookupType, value: String): ChanOutcome<LookupResult> {
        lookupCalls += type to value
        return lookupOutcome
    }

    companion object {
        val HIGH_RISK = AnalysisResult(
            risk = Risk.HIGH,
            score = 1.0,
            signals = listOf(
                AnalysisSignal("mao_danh_tham_quyen", 0.9, "<ACCOUNT>"),
                AnalysisSignal("ap_luc_thoi_gian", 0.8, ""),
                AnalysisSignal("yeu_cau_bi_mat", 1.0, ""),
                AnalysisSignal("tk_ca_nhan", 1.0, ""),
            ),
            explanation = "Tin nhắn tự nhận là cơ quan có thẩm quyền.",
            questions = listOf("Tại sao lại không được nói với người thân?"),
            verifiedHotline = null,
            actions = listOf("report"),
            engineVersion = "ml-test",
            ruleBundleVersion = "rb-test",
        )

        val MATCHED_LOOKUP = LookupResult(
            type = LookupType.ACCOUNT,
            matched = true,
            reportCount = 12,
            lastReportedDaysAgo = 3,
            origin = "community_reviewed",
            noMatchMessage = "Chưa có báo cáo về số tài khoản này.",
            bundleVersion = "rb-test",
        )

        fun failure(reason: FailureReason) = ChanOutcome.Failure(reason)
    }
}
