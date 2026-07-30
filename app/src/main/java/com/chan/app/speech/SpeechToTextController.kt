package com.chan.app.speech

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/** Everything the microphone control can be doing (§C3). */
sealed interface SpeechState {
    data object Idle : SpeechState
    data object RequestingPermission : SpeechState
    data object Listening : SpeechState
    data class ReceivingPartial(val text: String) : SpeechState
    data class FinalText(val text: String) : SpeechState
    data object NoSpeech : SpeechState
    data object RecognizerBusy : SpeechState
    data object ProviderUnavailable : SpeechState
    data object PermissionDenied : SpeechState

    /**
     * The phone has no on-device recognizer. Nothing has been started: using the
     * device's speech service could stream audio to a provider, so it waits for
     * the user to say yes.
     */
    data object OnDeviceUnavailable : SpeechState
}

/** Why the recognizer stopped. Mapped from the platform's numeric error codes. */
enum class RecognizerErrorCode {
    NO_SPEECH,
    BUSY,
    PERMISSION,
    NETWORK_OR_PROVIDER,
    OTHER,
}

/** How the recognizer should listen. One utterance, started by the user. */
data class SpeechRequest(
    val languageTag: String = "vi-VN",
    val partialResults: Boolean = true,
    /** A request to the provider, never a guarantee that audio stays local. */
    val preferOffline: Boolean = true,
)

/** Callbacks from a recognizer, normalised across platform quirks. */
interface RecognitionEvents {
    fun onPartial(text: String)
    fun onFinal(text: String)
    fun onError(code: RecognizerErrorCode)
    fun onEnd()
}

/** One recognizer instance. Wraps `SpeechRecognizer` in production. */
interface RecognizerHandle {
    fun setListener(events: RecognitionEvents)
    fun start(request: SpeechRequest)
    fun stop()
    fun cancel()
    fun destroy()
}

/** Creates recognizers. The seam that lets the controller be unit tested. */
interface RecognizerProvider {
    fun isOnDeviceAvailable(): Boolean

    /** Null when the platform refuses (for example `UnsupportedOperationException`). */
    fun createOnDevice(): RecognizerHandle?

    /** The device's speech service, which may send audio to a provider. */
    fun createDeviceService(): RecognizerHandle?
}

/** Lifecycle-aware dictation. Implementations must be used from the main thread. */
interface SpeechToTextController {
    val state: StateFlow<SpeechState>

    /** True only while an on-device recognizer is the one actually running. */
    val usingOnDeviceRecognizer: Boolean

    /**
     * Begins one user-initiated utterance.
     *
     * @param allowDeviceService the user has explicitly agreed to the device's
     *   speech service for this attempt. Without it, a phone lacking on-device
     *   recognition ends in [SpeechState.OnDeviceUnavailable] and no audio is
     *   captured.
     */
    fun start(allowDeviceService: Boolean = false)

    /** Finish listening and take whatever was heard. */
    fun stop()

    /** Abandon listening and keep nothing. */
    fun cancel()

    /** Called when the screen is left or the app backgrounds. */
    fun dispose()

    /** Records a denied RECORD_AUDIO grant so the UI can offer the fallbacks. */
    fun onPermissionDenied()

    /** Puts the control back to rest after the UI has consumed a final result. */
    fun acknowledge()
}

/**
 * The default controller (§C2, §C3).
 *
 * Two rules shape it. Recognition never starts in the background — only
 * [start] begins it, and only from a tap. And an utterance is never analysed:
 * the final text is handed to the caller, who puts it in an editable field and
 * waits for the user to press "Kiểm tra ngay".
 */
class DefaultSpeechToTextController(
    private val provider: RecognizerProvider,
    private val request: SpeechRequest = SpeechRequest(),
) : SpeechToTextController, RecognitionEvents {

    private val _state = MutableStateFlow<SpeechState>(SpeechState.Idle)
    override val state: StateFlow<SpeechState> = _state.asStateFlow()

    private var handle: RecognizerHandle? = null
    private var onDevice = false

    override val usingOnDeviceRecognizer: Boolean get() = onDevice

    override fun start(allowDeviceService: Boolean) {
        dispose()

        val onDeviceHandle = if (provider.isOnDeviceAvailable()) provider.createOnDevice() else null
        val chosen = when {
            onDeviceHandle != null -> onDeviceHandle.also { onDevice = true }
            // No on-device recognizer and no explicit consent: stop here rather
            // than quietly reaching for a recognizer that may stream audio out.
            !allowDeviceService -> {
                _state.value = SpeechState.OnDeviceUnavailable
                return
            }
            else -> provider.createDeviceService()?.also { onDevice = false }
        }

        if (chosen == null) {
            _state.value = SpeechState.ProviderUnavailable
            return
        }

        handle = chosen
        // The listener is attached before listening begins, or the first partial
        // result can arrive with nowhere to go.
        chosen.setListener(this)
        _state.value = SpeechState.Listening
        chosen.start(request)
    }

    override fun stop() {
        handle?.stop()
    }

    override fun cancel() {
        handle?.cancel()
        _state.value = SpeechState.Idle
    }

    override fun dispose() {
        handle?.let {
            it.cancel()
            it.destroy()
        }
        handle = null
        onDevice = false
        if (_state.value is SpeechState.Listening || _state.value is SpeechState.ReceivingPartial) {
            _state.value = SpeechState.Idle
        }
    }

    override fun onPermissionDenied() {
        dispose()
        _state.value = SpeechState.PermissionDenied
    }

    override fun acknowledge() {
        _state.value = SpeechState.Idle
    }

    // --- RecognitionEvents -------------------------------------------------

    override fun onPartial(text: String) {
        if (text.isNotBlank()) _state.value = SpeechState.ReceivingPartial(text.trim())
    }

    override fun onFinal(text: String) {
        val trimmed = text.trim()
        // The result goes to an editable field; nothing is submitted from here.
        _state.value = if (trimmed.isEmpty()) SpeechState.NoSpeech else SpeechState.FinalText(trimmed)
    }

    override fun onError(code: RecognizerErrorCode) {
        _state.value = when (code) {
            RecognizerErrorCode.NO_SPEECH -> SpeechState.NoSpeech
            RecognizerErrorCode.BUSY -> SpeechState.RecognizerBusy
            RecognizerErrorCode.PERMISSION -> SpeechState.PermissionDenied
            RecognizerErrorCode.NETWORK_OR_PROVIDER -> SpeechState.ProviderUnavailable
            RecognizerErrorCode.OTHER -> SpeechState.ProviderUnavailable
        }
    }

    override fun onEnd() {
        // A recognizer that ends without a result leaves the user at the text field.
        if (_state.value is SpeechState.Listening || _state.value is SpeechState.ReceivingPartial) {
            _state.value = SpeechState.NoSpeech
        }
    }
}
