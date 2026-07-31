package com.chan.app.speech

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.MainScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * Which recognizer produced a callback (§A1).
 *
 * The distinction is not cosmetic. [ON_DEVICE] means the audio stayed on the
 * phone; [DEVICE_SERVICE] means the phone's own speech service handled it and
 * may have sent audio to a provider. The UI is only allowed to claim the former
 * when this says so.
 */
enum class RecognizerStage { ON_DEVICE, DEVICE_SERVICE }

/**
 * Everything the microphone control can be doing (§A1).
 *
 * Platform errors are deliberately *not* collapsed into one "unavailable"
 * state: Sprint 02 shipped that shape and it told a user whose on-device model
 * had simply failed to load the same thing as a user whose phone has no speech
 * support at all.
 */
sealed interface SpeechState {
    data object Idle : SpeechState
    data object RequestingPermission : SpeechState

    /**
     * A recognizer has been asked to start but has not opened the microphone
     * yet (§A5).
     *
     * It exists so the control does not offer "Dừng nghe" for a recognizer that
     * is about to fail. On the Xiaomi handset the on-device provider answers
     * within a frame or two, and without this state the stop button appeared
     * and vanished before the user could read it.
     */
    data class Starting(val stage: RecognizerStage) : SpeechState

    /** Listening right now. [stage] decides which sentence the UI may show. */
    data class Listening(val stage: RecognizerStage) : SpeechState

    /** Words heard so far. Displayed, never copied into the message field. */
    data class ReceivingPartial(val text: String, val stage: RecognizerStage) : SpeechState

    /** The committed utterance, on its way to an editable field. */
    data class FinalText(val text: String) : SpeechState

    data object NoSpeech : SpeechState
    data object RecognizerBusy : SpeechState
    data object PermissionDenied : SpeechState

    /** The phone cannot recognise Vietnamese at all. Paste stays available. */
    data object LanguageUnavailable : SpeechState

    /**
     * The phone exposes no on-device recognizer. Nothing was started: using the
     * device's speech service could stream audio to a provider, so it waits for
     * the user to say yes.
     */
    data object OnDeviceUnavailable : SpeechState

    /**
     * The on-device recognizer started and then failed. The handle is already
     * destroyed and no audio is retained; the device service is offered as an
     * explicit choice (§A2), never taken automatically.
     */
    data object OnDeviceFailed : SpeechState

    /** The consented device speech service does not exist or refuses to start. */
    data object DeviceServiceUnavailable : SpeechState

    /** A provider/network hiccup. Trying again is reasonable. */
    data object TemporaryFailure : SpeechState

    /** The recognizer behind the current state, when one is running. */
    val listeningStage: RecognizerStage?
        get() = when (this) {
            is Starting -> this.stage
            is Listening -> this.stage
            is ReceivingPartial -> this.stage
            else -> null
        }

    /** True while a recognizer of ours is alive, ready or not. */
    val isSessionActive: Boolean get() = listeningStage != null
}

/**
 * Why the recognizer stopped, mapped from the platform's numeric error codes
 * (§A2). The full set available at compile SDK 35 is represented; nothing falls
 * into [OTHER] except a genuinely unknown code.
 */
enum class RecognizerErrorCode {
    NO_SPEECH,
    BUSY,
    PERMISSION,
    AUDIO,
    NETWORK,
    SERVER,
    SERVER_DISCONNECTED,
    CLIENT,
    TOO_MANY_REQUESTS,
    LANGUAGE_NOT_SUPPORTED,
    LANGUAGE_UNAVAILABLE,
    OTHER,
}

/** How the recognizer should listen. One utterance, started by the user. */
data class SpeechRequest(
    val languageTag: String = "vi-VN",
    val partialResults: Boolean = true,
    /**
     * A request to the provider, never a guarantee that audio stays local. It
     * is sent for the on-device attempt and dropped for the consented device
     * service, where pretending would be worse than asking.
     */
    val preferOffline: Boolean = true,
)

/**
 * A **synchronous** platform failure, already reduced to a safe code.
 *
 * The distinction from [RecognitionEvents.onError] matters. A call that fails
 * by returning normally *and* delivering a callback leaves the caller believing
 * it succeeded, which is how a destroyed recognizer used to end up rendered as
 * "Đang nghe trên máy…". An adapter reports a failed `setListener`, `start`,
 * `stop`, or `cancel` by throwing this and by **not** also calling `onError`.
 *
 * The message is the code's own name — never a platform exception string.
 */
class RecognizerFailure(val code: RecognizerErrorCode) : Exception(code.name)

/** Callbacks from a recognizer, normalised across platform quirks. */
interface RecognitionEvents {
    /**
     * The microphone is open. Until this arrives CHAN is starting, not
     * listening, and must not say otherwise or offer to stop.
     */
    fun onReady()

    fun onPartial(text: String)
    fun onFinal(text: String)
    fun onError(code: RecognizerErrorCode)

    /** Speech ended. Not a result: the provider still owes us one (§A3). */
    fun onEnd()
}

/**
 * One recognizer instance. Wraps `SpeechRecognizer` in production.
 *
 * Implementations must translate platform exceptions at this boundary and
 * signal a synchronous failure by throwing [RecognizerFailure]. Reporting such
 * a failure through [RecognitionEvents.onError] *and* returning normally is
 * forbidden: the controller cannot then tell a live recognizer from a dead one.
 * [destroy] never throws and is idempotent.
 */
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

    /** True when Android exposes any recognition service at all. */
    fun isDeviceServiceAvailable(): Boolean

    /** Null when the platform refuses (for example `UnsupportedOperationException`). */
    fun createOnDevice(): RecognizerHandle?

    /** The device's speech service, which may send audio to a provider. */
    fun createDeviceService(): RecognizerHandle?
}

/** Cancels a scheduled result window. */
fun interface Cancellation {
    fun cancel()
}

/**
 * A bounded wait for a provider that has ended speech but not answered yet
 * (§A3). Abstracted so the controller stays a JVM unit test.
 */
interface ResultWindow {
    fun schedule(delayMillis: Long, onElapsed: () -> Unit): Cancellation
}

/** Production window: one cancellable coroutine, never an indefinite wait. */
class CoroutineResultWindow(private val scope: CoroutineScope = MainScope()) : ResultWindow {
    override fun schedule(delayMillis: Long, onElapsed: () -> Unit): Cancellation {
        val job = scope.launch {
            delay(delayMillis)
            onElapsed()
        }
        return Cancellation { job.cancel() }
    }
}

/** Lifecycle-aware dictation. Implementations must be used from the main thread. */
interface SpeechToTextController {
    val state: StateFlow<SpeechState>

    /** True only while an on-device recognizer is the one actually running. */
    val usingOnDeviceRecognizer: Boolean

    /** The recognizer currently running, or null when nothing is listening. */
    val activeStage: RecognizerStage?

    /**
     * Begins one user-initiated utterance.
     *
     * @param allowDeviceService the user has explicitly agreed to the device's
     *   speech service for this attempt. Without it, the on-device recognizer
     *   is the only one that can be created, and a phone lacking one ends in
     *   [SpeechState.OnDeviceUnavailable] with no audio captured.
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
 * The default controller (§A1–A3).
 *
 * Three rules shape it. Recognition never starts in the background — only
 * [start] begins it, and only from a tap. An utterance is never analysed: the
 * final text is handed to the caller, who puts it in an editable field and
 * waits for the user to press "Kiểm tra ngay". And a recognizer that fails at
 * runtime is destroyed on the spot; the device service that might replace it is
 * created only when the user asks for it by name.
 *
 * Every attempt carries a session id. A callback from an older recognizer —
 * Android does deliver those after `destroy()` — is dropped rather than allowed
 * to overwrite a newer attempt.
 */
class DefaultSpeechToTextController(
    private val provider: RecognizerProvider,
    private val request: SpeechRequest = SpeechRequest(),
    private val resultWindow: ResultWindow = CoroutineResultWindow(),
    private val resultWindowMillis: Long = DEFAULT_RESULT_WINDOW_MILLIS,
) : SpeechToTextController {

    private val _state = MutableStateFlow<SpeechState>(SpeechState.Idle)
    override val state: StateFlow<SpeechState> = _state.asStateFlow()

    private var handle: RecognizerHandle? = null
    private var currentStage: RecognizerStage? = null
    private var sessionId = 0L
    private var pendingWindow: Cancellation? = null

    override val usingOnDeviceRecognizer: Boolean
        get() = currentStage == RecognizerStage.ON_DEVICE

    override val activeStage: RecognizerStage? get() = currentStage

    override fun start(allowDeviceService: Boolean) {
        // Whatever ran before is released first, and its session invalidated.
        closeSession(cancelFirst = true)

        if (allowDeviceService) {
            // Reached only from the explicit "Dùng dịch vụ giọng nói của máy"
            // action, never from an internal decision.
            val service = provider.createDeviceServiceOrNull()
            if (service == null) {
                _state.value = SpeechState.DeviceServiceUnavailable
                return
            }
            begin(service, RecognizerStage.DEVICE_SERVICE)
            return
        }

        val onDevice = if (provider.isOnDeviceAvailable()) provider.createOnDeviceOrNull() else null
        if (onDevice == null) {
            // Nothing was created, so no audio was captured. The user decides
            // whether the device service may be used at all.
            _state.value = SpeechState.OnDeviceUnavailable
            return
        }
        begin(onDevice, RecognizerStage.ON_DEVICE)
    }

    override fun stop() {
        // Stopping asks for the result; the recognizer stays alive until it
        // answers or the bounded window expires.
        val current = handle ?: return
        val session = sessionId
        val stage = currentStage ?: return
        try {
            current.stop()
        } catch (failure: RecognizerFailure) {
            if (isCurrent(session)) failWith(failure.code, stage)
        } catch (error: RuntimeException) {
            if (isCurrent(session)) failToStart(stage)
        }
    }

    override fun cancel() {
        closeSession(cancelFirst = true)
        _state.value = SpeechState.Idle
    }

    override fun dispose() {
        val hadSession = _state.value.isSessionActive
        closeSession(cancelFirst = true)
        if (hadSession) _state.value = SpeechState.Idle
    }

    override fun onPermissionDenied() {
        closeSession(cancelFirst = true)
        _state.value = SpeechState.PermissionDenied
    }

    override fun acknowledge() {
        _state.value = SpeechState.Idle
    }

    // --- session plumbing --------------------------------------------------

    private fun begin(chosen: RecognizerHandle, stage: RecognizerStage) {
        val session = ++sessionId
        handle = chosen
        currentStage = stage

        try {
            // The listener is attached before listening begins, or the first
            // partial result can arrive with nowhere to go.
            chosen.setListener(SessionEvents(session, stage))
            // Attaching can itself fail through a callback. Asking a recognizer
            // that has just been destroyed to start listening is how a platform
            // crash gets built.
            if (!isCurrent(session)) return
            chosen.start(request.copy(preferOffline = stage == RecognizerStage.ON_DEVICE))
        } catch (failure: RecognizerFailure) {
            if (isCurrent(session)) failWith(failure.code, stage)
            return
        } catch (error: RuntimeException) {
            // A handle that does not translate its own failures still must not
            // leave a destroyed recognizer looking alive.
            if (isCurrent(session)) failToStart(stage)
            return
        }

        // A recognizer may report a failure through `onError` during the calls
        // above — some platform implementations do, and Sprint 03's first cut
        // then overwrote that failure with "listening". If the session is gone,
        // its terminal state is already published and must stand.
        if (!isCurrent(session)) return
        // Nor may a result that has already arrived be walked back.
        if (_state.value is SpeechState.ReceivingPartial) return
        if (_state.value is SpeechState.Listening) return
        // Starting, not listening: the microphone is not open until the
        // recognizer says so (§A5).
        _state.value = SpeechState.Starting(stage)
    }

    /** A recognizer that cannot even be started is released immediately. */
    private fun failToStart(stage: RecognizerStage) {
        closeSession(cancelFirst = false)
        _state.value = when (stage) {
            RecognizerStage.ON_DEVICE -> SpeechState.OnDeviceFailed
            RecognizerStage.DEVICE_SERVICE -> SpeechState.DeviceServiceUnavailable
        }
    }

    /** Releases the handle and publishes the meaning of a translated failure. */
    private fun failWith(code: RecognizerErrorCode, stage: RecognizerStage) {
        closeSession(cancelFirst = false)
        _state.value = stateFor(code, stage)
    }

    /**
     * Releases the active recognizer exactly once and invalidates its session.
     * Callbacks that arrive afterwards carry a stale id and are dropped.
     */
    private fun closeSession(cancelFirst: Boolean) {
        pendingWindow?.cancel()
        pendingWindow = null

        val current = handle ?: run {
            currentStage = null
            return
        }
        handle = null
        currentStage = null
        sessionId++
        if (cancelFirst) runCatching { current.cancel() }
        runCatching { current.destroy() }
    }

    private fun isCurrent(session: Long) = session == sessionId && handle != null

    /**
     * Maps a platform failure to something a worried person can act on. The
     * on-device column is the only one that may offer the device service, and
     * the device-service column never points back at on-device: looping between
     * providers would look like the app is broken (§A2).
     */
    private fun stateFor(code: RecognizerErrorCode, stage: RecognizerStage): SpeechState = when (code) {
        RecognizerErrorCode.NO_SPEECH -> SpeechState.NoSpeech
        RecognizerErrorCode.BUSY -> SpeechState.RecognizerBusy
        RecognizerErrorCode.PERMISSION -> SpeechState.PermissionDenied
        RecognizerErrorCode.LANGUAGE_NOT_SUPPORTED -> SpeechState.LanguageUnavailable
        RecognizerErrorCode.AUDIO,
        RecognizerErrorCode.TOO_MANY_REQUESTS,
        -> SpeechState.TemporaryFailure

        // The recognizer that was chosen cannot run this request: its service
        // disconnected, its language model is missing, or it rejected us.
        RecognizerErrorCode.NETWORK,
        RecognizerErrorCode.SERVER,
        RecognizerErrorCode.SERVER_DISCONNECTED,
        RecognizerErrorCode.CLIENT,
        RecognizerErrorCode.LANGUAGE_UNAVAILABLE,
        RecognizerErrorCode.OTHER,
        -> when (stage) {
            RecognizerStage.ON_DEVICE -> SpeechState.OnDeviceFailed
            RecognizerStage.DEVICE_SERVICE ->
                if (code == RecognizerErrorCode.LANGUAGE_UNAVAILABLE) {
                    SpeechState.LanguageUnavailable
                } else {
                    SpeechState.TemporaryFailure
                }
        }
    }

    /** One recognizer's callbacks, tagged with the attempt that created it. */
    private inner class SessionEvents(
        private val session: Long,
        private val stage: RecognizerStage,
    ) : RecognitionEvents {

        override fun onReady() {
            if (!isCurrent(session)) return
            // Only a starting session graduates; a partial has already said
            // more than "ready" does.
            if (_state.value is SpeechState.Starting) _state.value = SpeechState.Listening(stage)
        }

        override fun onPartial(text: String) {
            if (!isCurrent(session)) return
            val trimmed = text.trim()
            if (trimmed.isNotEmpty()) _state.value = SpeechState.ReceivingPartial(trimmed, stage)
        }

        override fun onFinal(text: String) {
            if (!isCurrent(session)) return
            val trimmed = text.trim()
            // §A3: the handle is released before the result is published, so
            // the field the user edits is never backed by a live recognizer.
            closeSession(cancelFirst = false)
            _state.value = if (trimmed.isEmpty()) SpeechState.NoSpeech else SpeechState.FinalText(trimmed)
        }

        override fun onError(code: RecognizerErrorCode) {
            if (!isCurrent(session)) return
            closeSession(cancelFirst = false)
            _state.value = stateFor(code, stage)
        }

        override fun onEnd() {
            if (!isCurrent(session)) return
            // A provider can end speech without ever reporting itself ready.
            if (!_state.value.isSessionActive) return

            // Speech ended, the result has not arrived. Wait a bounded moment
            // rather than replacing a pending answer with "chưa nghe rõ".
            pendingWindow?.cancel()
            pendingWindow = resultWindow.schedule(resultWindowMillis) {
                if (!isCurrent(session)) return@schedule
                closeSession(cancelFirst = true)
                _state.value = SpeechState.NoSpeech
            }
        }
    }

    private fun RecognizerProvider.createOnDeviceOrNull(): RecognizerHandle? =
        runCatching { createOnDevice() }.getOrNull()

    private fun RecognizerProvider.createDeviceServiceOrNull(): RecognizerHandle? =
        runCatching { createDeviceService() }.getOrNull()

    companion object {
        /** How long a provider may take to answer after `onEndOfSpeech`. */
        const val DEFAULT_RESULT_WINDOW_MILLIS = 3_000L
    }
}
