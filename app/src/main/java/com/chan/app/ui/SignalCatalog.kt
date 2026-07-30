package com.chan.app.ui

import androidx.annotation.StringRes
import com.chan.app.R
import com.chan.app.domain.AnalysisResult
import com.chan.app.domain.AnalysisSignal

/**
 * One row on the result screen: a signal, whether this message triggered it,
 * and the backend's already-redacted excerpt when it did.
 */
data class SignalRowState(
    val code: String,
    @StringRes val labelRes: Int,
    /** Set only for a code this build has no label for; shown verbatim. */
    val fallbackLabel: String?,
    val hit: Boolean,
    val evidence: String?,
)

/**
 * Maps backend signal codes to Vietnamese labels.
 *
 * This mapping lives in the UI layer on purpose: the data layer must stay free
 * of Android resource IDs so the same [AnalysisResult] can drive a screen, a
 * notification decision, and a JVM test.
 *
 * A code this build has never heard of becomes an ordinary labelled row rather
 * than a crash — the backend's taxonomy can grow without the app being
 * reinstalled.
 */
object SignalCatalog {

    /**
     * The eight codes the running backend emits, in its documented weight
     * order. Every one of them gets a row so the screen keeps Sprint 01's
     * "trúng n/8" contract.
     */
    val DISPLAY_ORDER: List<String> = listOf(
        "mao_danh_tham_quyen",
        "yeu_cau_bi_mat",
        "ap_luc_thoi_gian",
        "tk_ca_nhan",
        "cai_app_ngoai",
        "loi_ich_bat_thuong",
        "chuyen_kenh",
        "yeu_cau_otp",
    )

    private val LABELS: Map<String, Int> = mapOf(
        "mao_danh_tham_quyen" to R.string.signal_mao_danh_tham_quyen,
        "yeu_cau_bi_mat" to R.string.signal_yeu_cau_bi_mat,
        "ap_luc_thoi_gian" to R.string.signal_ap_luc_thoi_gian,
        "tk_ca_nhan" to R.string.signal_tk_ca_nhan,
        "cai_app_ngoai" to R.string.signal_cai_app_ngoai,
        "loi_ich_bat_thuong" to R.string.signal_loi_ich_bat_thuong,
        "chuyen_kenh" to R.string.signal_chuyen_kenh,
        "yeu_cau_otp" to R.string.signal_yeu_cau_otp,
        // Codes named in the Sprint 02 brief that this backend build does not
        // emit yet. Labelled anyway so a server-side rename renders correctly.
        "de_doa" to R.string.signal_de_doa,
        "link_gia" to R.string.signal_link_gia,
        "loi_hua_loi_ich" to R.string.signal_loi_ich_bat_thuong,
        "yeu_cau_chuyen_tien" to R.string.signal_tk_ca_nhan,
    )

    @StringRes
    fun labelFor(code: String): Int? = LABELS[code]

    /** The rows to render: the known eight, plus anything else the server sent. */
    fun rowsFor(result: AnalysisResult): List<SignalRowState> {
        val byCode: Map<String, AnalysisSignal> = result.signals.associateBy { it.code }

        val known = DISPLAY_ORDER.map { code ->
            val signal = byCode[code]
            SignalRowState(
                code = code,
                labelRes = LABELS.getValue(code),
                fallbackLabel = null,
                hit = signal != null,
                evidence = signal?.evidence?.takeIf { it.isNotBlank() },
            )
        }

        val extra = result.signals
            .filter { !DISPLAY_ORDER.contains(it.code) }
            .map { signal ->
                SignalRowState(
                    code = signal.code,
                    labelRes = LABELS[signal.code] ?: R.string.signal_unknown_code,
                    // Only shown when there is no localized label at all.
                    fallbackLabel = if (LABELS.containsKey(signal.code)) null else signal.code,
                    hit = true,
                    evidence = signal.evidence.takeIf { it.isNotBlank() },
                )
            }

        return known + extra
    }
}
