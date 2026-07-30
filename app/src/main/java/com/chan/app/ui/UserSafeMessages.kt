package com.chan.app.ui

import androidx.annotation.StringRes
import com.chan.app.R
import com.chan.app.domain.FailureReason
import com.chan.app.domain.Risk
import com.chan.app.notification.ProtectionHealth
import com.chan.app.speech.RecognizerStage
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

    /**
     * Status line under the microphone button. Null only for [SpeechState.Idle],
     * where there is genuinely nothing to say.
     *
     * The two listening sentences are different on purpose (§A5): a user who
     * agreed to the phone's speech service is entitled to see that it, and not
     * the on-device recognizer, is the one hearing them.
     */
    @StringRes
    fun forSpeech(state: SpeechState): Int? = when (state) {
        SpeechState.Idle -> null
        SpeechState.RequestingPermission -> R.string.speech_requesting_permission
        // Starting is not listening: the microphone may not be open yet.
        is SpeechState.Starting -> R.string.speech_preparing
        is SpeechState.Listening -> listeningRes(state.stage)
        is SpeechState.ReceivingPartial -> listeningRes(state.stage)
        is SpeechState.FinalText -> R.string.speech_final
        SpeechState.NoSpeech -> R.string.speech_no_speech
        SpeechState.RecognizerBusy -> R.string.speech_busy
        SpeechState.PermissionDenied -> R.string.speech_permission_denied
        SpeechState.LanguageUnavailable -> R.string.speech_language_unavailable
        SpeechState.OnDeviceUnavailable -> R.string.speech_on_device_unavailable
        SpeechState.OnDeviceFailed -> R.string.speech_on_device_failed
        SpeechState.DeviceServiceUnavailable -> R.string.speech_device_service_unavailable
        SpeechState.TemporaryFailure -> R.string.speech_temporary_failure
    }

    @StringRes
    private fun listeningRes(stage: RecognizerStage): Int = when (stage) {
        RecognizerStage.ON_DEVICE -> R.string.speech_listening_on_device
        RecognizerStage.DEVICE_SERVICE -> R.string.speech_listening_device_service
    }

    /**
     * The headline for the whole protection stack (§B2). It is the same
     * sentence the recovery card leads with, so Home and Bảo vệ cannot drift.
     */
    @StringRes
    fun protectionHeadline(health: ProtectionHealth): Int =
        ProtectionRecoveryPolicy.forHealth(health).headlineRes

    /** The short form used by the Home status row. */
    @StringRes
    fun protectionHomeLabel(health: ProtectionHealth): Int = when (health) {
        ProtectionHealth.OFF -> R.string.home_protection_off
        ProtectionHealth.ACCESS_REQUIRED -> R.string.home_protection_needs_setup
        // Android, not the network, is what has not connected.
        ProtectionHealth.DISCONNECTED -> R.string.home_protection_not_connected
        ProtectionHealth.CONNECTING -> R.string.home_protection_connecting
        ProtectionHealth.RECONNECTING -> R.string.home_protection_reconnecting
        ProtectionHealth.ACTIVE_WITHOUT_WARNINGS -> R.string.protection_state_active_no_warning
        ProtectionHealth.ACTIVE -> R.string.home_protection_active
    }
}
