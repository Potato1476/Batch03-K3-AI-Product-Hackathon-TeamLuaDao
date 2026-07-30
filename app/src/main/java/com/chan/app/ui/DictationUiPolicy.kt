package com.chan.app.ui

import androidx.annotation.StringRes
import com.chan.app.R
import com.chan.app.speech.RecognizerStage
import com.chan.app.speech.SpeechState

/** Something the microphone area can offer (§A5). */
enum class MicAction {
    /** "Đọc bằng micro" — begin an on-device-first attempt. */
    START,

    /** The same slot, disabled, while a recognizer is starting. */
    PREPARING,

    STOP,
    CANCEL,

    /** Consent to the phone's own speech service for this attempt. */
    USE_DEVICE_SERVICE,

    /** Try the on-device recognizer once more. */
    RETRY_ON_DEVICE,

    /** "Để sau" — leave dictation alone and go back to typing. */
    DISMISS,

    /** Try the same thing again after a transient failure. */
    RETRY,

    /** The system's speech/voice-input settings. */
    OPEN_SPEECH_SETTINGS,

    /** CHAN's own app settings, for a denied microphone permission. */
    OPEN_APP_SETTINGS,
}

enum class MicEmphasis { PRIMARY, SECONDARY }

data class MicButton(
    val action: MicAction,
    val emphasis: MicEmphasis,
    @StringRes val labelRes: Int,
    val enabled: Boolean = true,
)

/** Everything the microphone card renders for one speech state. */
data class DictationUi(
    /** In display order. */
    val buttons: List<MicButton>,
    /** Show the status sentence above the actions rather than below. */
    val statusBeforeActions: Boolean,
    val showPartial: Boolean,
    /** The privacy consequence of the device speech service. */
    val showDeviceServicePrivacy: Boolean,
    /** "Paste or pick a picture instead" — for a recognizer that cannot work. */
    val showAlternativesHint: Boolean,
    /** The on-device claim. Only ever true while on-device is really running. */
    val showOnDeviceNote: Boolean,
) {
    fun has(action: MicAction): Boolean = buttons.any { it.action == action }
}

/**
 * What the microphone control offers, state by state (§A5).
 *
 * Sprint 03's first cut showed the generic "Đọc bằng micro" button for every
 * state that was not actively listening. On the phone that meant a failed
 * on-device recognizer produced a microphone button *above* the explanation of
 * why the microphone had just failed, competing with the three actions that
 * could actually fix it — and tapping it simply reproduced the failure.
 *
 * Two rules follow from that, and this table exists so both are testable:
 *
 *  - the generic start button appears only where starting is the sensible next
 *    move (at rest, or after a result has landed);
 *  - a state that describes a *broken* recognizer leads with the explanation
 *    and offers only the actions that can change the outcome. Where the
 *    recognizer cannot work at all — permission denied, no Vietnamese, no
 *    speech service — retrying it is not offered at all; settings and the
 *    paste/image paths are.
 */
object DictationUiPolicy {

    fun forState(state: SpeechState): DictationUi = when (state) {
        SpeechState.Idle -> at(
            buttons = listOf(start()),
            statusBeforeActions = false,
        )

        // A permission dialog is on screen; nothing here should compete with it.
        SpeechState.RequestingPermission -> at(buttons = emptyList())

        is SpeechState.Starting -> at(
            // The same slot as "Đọc bằng micro", disabled, so an immediate
            // provider answer cannot flash a stop button into existence.
            buttons = listOf(
                MicButton(MicAction.PREPARING, MicEmphasis.SECONDARY, R.string.speech_button_preparing, enabled = false),
            ),
            statusBeforeActions = false,
        )

        is SpeechState.Listening -> at(
            buttons = listOf(stop(), cancel()),
            statusBeforeActions = false,
            showOnDeviceNote = state.stage == RecognizerStage.ON_DEVICE,
        )

        is SpeechState.ReceivingPartial -> at(
            buttons = listOf(stop(), cancel()),
            statusBeforeActions = false,
            showPartial = true,
            showOnDeviceNote = state.stage == RecognizerStage.ON_DEVICE,
        )

        // The result is in the editable field; dictating again is reasonable.
        is SpeechState.FinalText -> at(buttons = listOf(start()))

        // The on-device recognizer is unusable for this attempt. The consented
        // fallback leads, because it is the action most likely to work.
        SpeechState.OnDeviceFailed,
        SpeechState.OnDeviceUnavailable,
        -> at(
            buttons = listOf(
                MicButton(MicAction.USE_DEVICE_SERVICE, MicEmphasis.PRIMARY, R.string.speech_use_device_service),
                MicButton(MicAction.RETRY_ON_DEVICE, MicEmphasis.SECONDARY, R.string.speech_retry_on_device),
                MicButton(MicAction.DISMISS, MicEmphasis.SECONDARY, R.string.speech_later),
            ),
            showDeviceServicePrivacy = true,
        )

        // Nothing is broken; the attempt simply did not produce words.
        SpeechState.NoSpeech,
        SpeechState.RecognizerBusy,
        SpeechState.TemporaryFailure,
        -> at(buttons = listOf(MicButton(MicAction.RETRY, MicEmphasis.SECONDARY, R.string.action_retry)))

        // Retrying cannot help until something outside CHAN changes, so it is
        // not offered: a button that reproduces the same failure reads as a
        // broken app.
        SpeechState.PermissionDenied -> at(
            buttons = listOf(
                MicButton(MicAction.OPEN_APP_SETTINGS, MicEmphasis.SECONDARY, R.string.speech_open_permission_settings),
            ),
            showAlternativesHint = true,
        )

        SpeechState.LanguageUnavailable,
        SpeechState.DeviceServiceUnavailable,
        -> at(
            buttons = listOf(
                MicButton(MicAction.OPEN_SPEECH_SETTINGS, MicEmphasis.SECONDARY, R.string.speech_open_settings),
            ),
            showAlternativesHint = true,
        )
    }

    private fun start() = MicButton(MicAction.START, MicEmphasis.SECONDARY, R.string.speech_button_start)
    private fun stop() = MicButton(MicAction.STOP, MicEmphasis.PRIMARY, R.string.speech_button_stop)
    private fun cancel() = MicButton(MicAction.CANCEL, MicEmphasis.SECONDARY, R.string.action_cancel)

    private fun at(
        buttons: List<MicButton>,
        statusBeforeActions: Boolean = true,
        showPartial: Boolean = false,
        showDeviceServicePrivacy: Boolean = false,
        showAlternativesHint: Boolean = false,
        showOnDeviceNote: Boolean = false,
    ) = DictationUi(
        buttons = buttons,
        statusBeforeActions = statusBeforeActions,
        showPartial = showPartial,
        showDeviceServicePrivacy = showDeviceServicePrivacy,
        showAlternativesHint = showAlternativesHint,
        showOnDeviceNote = showOnDeviceNote,
    )
}
