package com.chan.app.ui

import androidx.annotation.StringRes
import com.chan.app.R
import com.chan.app.domain.FailureReason
import com.chan.app.domain.Risk
import com.chan.app.speech.SpeechState

/**
 * Turns internal states into normal language (§A7).
 *
 * Nothing here can produce a status code, a JSON fragment, an exception name,
 * or an internal identifier — the mapping is total and every branch is a
 * sentence written for someone who is worried about their money.
 */
object UserSafeMessages {

    @StringRes
    fun forFailure(reason: FailureReason): Int = when (reason) {
        FailureReason.OFFLINE -> R.string.error_offline
        FailureReason.TIMEOUT -> R.string.error_timeout
        FailureReason.RATE_LIMITED -> R.string.error_rate_limited
        FailureReason.BACKEND_UNAVAILABLE -> R.string.error_backend_unavailable
        FailureReason.BUNDLE_MISMATCH -> R.string.error_bundle_mismatch
        FailureReason.INVALID_INPUT -> R.string.error_invalid_input
        FailureReason.UNEXPECTED -> R.string.error_unexpected
    }

    /** The risk headline. `UNKNOWN` says what was found, never that it is safe. */
    @StringRes
    fun riskTitle(risk: Risk): Int = when (risk) {
        Risk.HIGH -> R.string.result_high_title
        Risk.MEDIUM -> R.string.result_medium_title
        Risk.UNKNOWN -> R.string.result_unknown_title
    }

    @StringRes
    fun riskPill(risk: Risk): Int = when (risk) {
        Risk.HIGH -> R.string.pill_high_risk
        Risk.MEDIUM -> R.string.pill_caution
        Risk.UNKNOWN -> R.string.pill_unknown
    }

    @StringRes
    fun riskInstruction(risk: Risk): Int = when (risk) {
        Risk.HIGH -> R.string.result_high_instruction
        Risk.MEDIUM -> R.string.result_medium_instruction
        Risk.UNKNOWN -> R.string.result_unknown_instruction
    }

    /** Status line under the microphone button. Null while there is nothing to say. */
    @StringRes
    fun forSpeech(state: SpeechState): Int? = when (state) {
        SpeechState.Idle -> null
        SpeechState.RequestingPermission -> R.string.speech_requesting_permission
        SpeechState.Listening -> R.string.speech_listening
        is SpeechState.ReceivingPartial -> R.string.speech_listening
        is SpeechState.FinalText -> R.string.speech_final
        SpeechState.NoSpeech -> R.string.speech_no_speech
        SpeechState.RecognizerBusy -> R.string.speech_busy
        SpeechState.ProviderUnavailable -> R.string.speech_provider_unavailable
        SpeechState.PermissionDenied -> R.string.speech_permission_denied
        SpeechState.OnDeviceUnavailable -> R.string.speech_on_device_unavailable
    }
}
