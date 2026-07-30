package com.chan.app

import com.chan.app.speech.Cancellation
import com.chan.app.speech.DefaultSpeechToTextController
import com.chan.app.speech.RecognitionEvents
import com.chan.app.speech.RecognizerErrorCode
import com.chan.app.speech.RecognizerFailure
import com.chan.app.speech.RecognizerHandle
import com.chan.app.speech.RecognizerProvider
import com.chan.app.speech.RecognizerStage
import com.chan.app.speech.ResultWindow
import com.chan.app.speech.SpeechRequest
import com.chan.app.speech.SpeechState
import com.chan.app.ui.UserSafeMessages
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Dictation (§A1–A3).
 *
 * Three promises are under test. Audio prefers the on-device recognizer and
 * never silently reaches for one that may stream to a provider. A recognizer
 * that fails at runtime is released and replaced only when the user says so.
 * And recognized speech lands in an editable field — CHAN never submits what it
 * heard.
 */
class SpeechToTextControllerTest {

    private class FakeHandle(val label: String) : RecognizerHandle {
        var events: RecognitionEvents? = null
        var startedWith: SpeechRequest? = null
        var stopped = false
        var cancelCount = 0
        var destroyCount = 0
        var listenerSetBeforeStart = false

        /** Raw platform exception from a handle that translates nothing. */
        var throwOnStart = false

        /** A translated synchronous failure, as the real adapter reports one. */
        var failureOnStart: RecognizerErrorCode? = null
        var failureOnStop: RecognizerErrorCode? = null

        /**
         * The pre-fix adapter behaviour: report through the callback and then
         * return normally, so the caller believes the call succeeded.
         */
        var callbackAndReturnFromSetListener: RecognizerErrorCode? = null
        var callbackAndReturnFromStart: RecognizerErrorCode? = null

        /** Some providers deliver a first result inside `startListening`. */
        var partialDuringStart: String? = null

        override fun setListener(events: RecognitionEvents) {
            this.events = events
            callbackAndReturnFromSetListener?.let { events.onError(it) }
        }

        override fun start(request: SpeechRequest) {
            listenerSetBeforeStart = events != null
            startedWith = request
            if (throwOnStart) throw IllegalStateException("platform refused")
            failureOnStart?.let { throw RecognizerFailure(it) }
            callbackAndReturnFromStart?.let { events?.onError(it) }
            partialDuringStart?.let { events?.onPartial(it) }
        }

        override fun stop() {
            stopped = true
            failureOnStop?.let { throw RecognizerFailure(it) }
        }

        override fun cancel() {
            cancelCount++
        }

        override fun destroy() {
            destroyCount++
        }
    }

    private class FakeProvider(
        val onDeviceAvailable: Boolean = true,
        val onDeviceCreates: Boolean = true,
        val deviceServiceCreates: Boolean = true,
        val onDeviceThrowsOnStart: Boolean = false,
        /** Applied to each handle before the controller receives it. */
        val configure: (FakeHandle) -> Unit = {},
    ) : RecognizerProvider {
        var onDeviceCalls = 0
        var deviceServiceCalls = 0
        val handles = mutableListOf<FakeHandle>()

        override fun isOnDeviceAvailable(): Boolean = onDeviceAvailable

        override fun isDeviceServiceAvailable(): Boolean = deviceServiceCreates

        override fun createOnDevice(): RecognizerHandle? {
            onDeviceCalls++
            if (!onDeviceCreates) return null
            return FakeHandle("on-device")
                .also { it.throwOnStart = onDeviceThrowsOnStart }
                .also(configure)
                .also { handles += it }
        }

        override fun createDeviceService(): RecognizerHandle? {
            deviceServiceCalls++
            if (!deviceServiceCreates) return null
            return FakeHandle("device-service").also(configure).also { handles += it }
        }
    }

    /** A result window the test fires by hand. Nothing waits in real time. */
    private class ManualWindow : ResultWindow {
        var pending: (() -> Unit)? = null
        var scheduledDelay: Long? = null
        var cancelled = false

        override fun schedule(delayMillis: Long, onElapsed: () -> Unit): Cancellation {
            scheduledDelay = delayMillis
            pending = onElapsed
            cancelled = false
            return Cancellation {
                cancelled = true
                pending = null
            }
        }

        fun elapse() {
            val action = pending ?: return
            pending = null
            action()
        }
    }

    private fun controller(
        provider: FakeProvider,
        window: ManualWindow = ManualWindow(),
    ) = DefaultSpeechToTextController(provider, resultWindow = window)

    // --- 1, 2: on-device first, and never a silent fallback -----------------

    @Test
    fun onDeviceRecognitionIsPreferredWhenAvailable() {
        val provider = FakeProvider()
        val controller = controller(provider)

        controller.start()

        assertEquals(1, provider.onDeviceCalls)
        assertEquals("The device service must not be touched", 0, provider.deviceServiceCalls)
        assertTrue(controller.usingOnDeviceRecognizer)
        // Starting, not listening: the microphone is not open until the
        // recognizer reports itself ready.
        assertEquals(SpeechState.Starting(RecognizerStage.ON_DEVICE), controller.state.value)

        val handle = provider.handles.single()
        handle.events?.onReady()
        assertEquals(SpeechState.Listening(RecognizerStage.ON_DEVICE), controller.state.value)

        assertTrue("The listener must be attached before listening", handle.listenerSetBeforeStart)
        assertEquals("vi-VN", handle.startedWith?.languageTag)
        assertTrue(handle.startedWith!!.partialResults)
        assertTrue("The on-device attempt asks to stay offline", handle.startedWith!!.preferOffline)
    }

    @Test
    fun theDeviceServiceIsNeverCreatedWithoutExplicitConsent() {
        val provider = FakeProvider(onDeviceAvailable = false)
        val controller = controller(provider)

        controller.start(allowDeviceService = false)

        // Nothing was created, so no audio was captured.
        assertEquals(0, provider.deviceServiceCalls)
        assertTrue(provider.handles.isEmpty())
        assertEquals(SpeechState.OnDeviceUnavailable, controller.state.value)

        // Only after the user agrees.
        controller.start(allowDeviceService = true)
        assertEquals(1, provider.deviceServiceCalls)
        assertEquals(SpeechState.Starting(RecognizerStage.DEVICE_SERVICE), controller.state.value)
        provider.handles.single().events?.onReady()
        assertEquals(SpeechState.Listening(RecognizerStage.DEVICE_SERVICE), controller.state.value)
        // And the UI must not claim on-device privacy it does not have.
        assertFalse(controller.usingOnDeviceRecognizer)
        // `EXTRA_PREFER_OFFLINE` is not sent as a promise CHAN cannot keep.
        assertFalse(provider.handles.single().startedWith!!.preferOffline)
    }

    @Test
    fun anUnsupportedOnDeviceFactoryStillAsksBeforeUsingTheDeviceService() {
        // `isOnDeviceRecognitionAvailable` says yes but the factory refuses.
        val provider = FakeProvider(onDeviceCreates = false)
        val controller = controller(provider)

        controller.start(allowDeviceService = false)
        assertEquals(SpeechState.OnDeviceUnavailable, controller.state.value)
        assertEquals(0, provider.deviceServiceCalls)
    }

    // --- 3, 4, 5: the runtime failure path ----------------------------------

    @Test
    fun aRuntimeFailureOfTheOnDeviceRecognizerOffersTheFallbackChoice() {
        val runtimeFailures = listOf(
            RecognizerErrorCode.SERVER,
            RecognizerErrorCode.SERVER_DISCONNECTED,
            RecognizerErrorCode.CLIENT,
            RecognizerErrorCode.LANGUAGE_UNAVAILABLE,
            RecognizerErrorCode.NETWORK,
            RecognizerErrorCode.OTHER,
        )
        runtimeFailures.forEach { code ->
            val provider = FakeProvider()
            val controller = controller(provider)
            controller.start()
            val handle = provider.handles.single()

            handle.events?.onError(code)

            assertEquals("error $code", SpeechState.OnDeviceFailed, controller.state.value)
            // The failed handle is released before anything is offered.
            assertEquals("error $code destroys once", 1, handle.destroyCount)
            // Nothing was reached for on CHAN's own initiative.
            assertEquals("error $code must not auto-fallback", 0, provider.deviceServiceCalls)
        }
    }

    @Test
    fun aFailureToEvenStartTheOnDeviceRecognizerOffersTheSameChoice() {
        val provider = FakeProvider(onDeviceThrowsOnStart = true)
        val controller = controller(provider)

        controller.start()

        assertEquals(SpeechState.OnDeviceFailed, controller.state.value)
        assertEquals(1, provider.handles.single().destroyCount)
        assertEquals(0, provider.deviceServiceCalls)
    }

    @Test
    fun aRecognizerThatReportsThroughOnErrorAndReturnsNormallyNeverLooksAlive() {
        // The shipped adapter used to catch an exception from
        // `setRecognitionListener`, call `onError`, and return as if the call
        // had worked. The controller then published "Đang nghe trên máy…" over
        // the failure and waited forever on a destroyed recognizer.
        val provider = FakeProvider(
            configure = { it.callbackAndReturnFromSetListener = RecognizerErrorCode.CLIENT },
        )
        val controller = controller(provider)

        controller.start()

        val handle = provider.handles.single()
        assertEquals(SpeechState.OnDeviceFailed, controller.state.value)
        assertEquals("The dead recognizer is released once", 1, handle.destroyCount)
        assertNull("Nothing may be listening", controller.activeStage)
        // The listener was never attached to a working recognizer, so the
        // failed handle must not have been asked to listen.
        assertNull(handle.startedWith)
    }

    @Test
    fun aStartThatReportsThroughOnErrorAndReturnsNormallyNeverLooksAlive() {
        val provider = FakeProvider(
            configure = { it.callbackAndReturnFromStart = RecognizerErrorCode.SERVER_DISCONNECTED },
        )
        val controller = controller(provider)

        controller.start()

        assertEquals(SpeechState.OnDeviceFailed, controller.state.value)
        assertEquals(1, provider.handles.single().destroyCount)
        assertNull(controller.activeStage)
        assertFalse(controller.usingOnDeviceRecognizer)
    }

    @Test
    fun aTranslatedSynchronousFailureKeepsItsMeaning() {
        // The adapter throws RecognizerFailure rather than reporting twice, so
        // a refused permission is not flattened into "on-device failed".
        val provider = FakeProvider(
            configure = { it.failureOnStart = RecognizerErrorCode.PERMISSION },
        )
        val controller = controller(provider)

        controller.start()

        assertEquals(SpeechState.PermissionDenied, controller.state.value)
        assertEquals(1, provider.handles.single().destroyCount)
        assertNull(controller.activeStage)
    }

    @Test
    fun aFailureWhileStoppingDoesNotLeaveTheUserListeningForever() {
        val provider = FakeProvider(
            configure = { it.failureOnStop = RecognizerErrorCode.CLIENT },
        )
        val controller = controller(provider)
        controller.start()

        controller.stop()

        assertEquals(SpeechState.OnDeviceFailed, controller.state.value)
        assertEquals(1, provider.handles.single().destroyCount)
        assertNull(controller.activeStage)
    }

    @Test
    fun aRecognizerThatFailsBeforeOpeningTheMicrophoneNeverReportsListening() {
        // The Xiaomi on-device provider answers within a frame or two. The
        // control must go from "đang chuẩn bị" straight to the explanation,
        // without a stop button appearing in between.
        val provider = FakeProvider()
        val controller = controller(provider)
        val seen = mutableListOf<SpeechState>()

        controller.start()
        seen += controller.state.value
        provider.handles.single().events?.onError(RecognizerErrorCode.SERVER)
        seen += controller.state.value

        assertEquals(
            listOf(SpeechState.Starting(RecognizerStage.ON_DEVICE), SpeechState.OnDeviceFailed),
            seen,
        )
        assertTrue("Listening was never claimed", seen.none { it is SpeechState.Listening })
    }

    @Test
    fun onlyTheRecognizerCanPromoteStartingToListening() {
        val provider = FakeProvider()
        val controller = controller(provider)
        controller.start()
        val handle = provider.handles.single()

        assertEquals(SpeechState.Starting(RecognizerStage.ON_DEVICE), controller.state.value)

        handle.events?.onReady()
        assertEquals(SpeechState.Listening(RecognizerStage.ON_DEVICE), controller.state.value)

        // A late second `onReadyForSpeech` cannot undo a partial result.
        handle.events?.onPartial("bác ơi")
        handle.events?.onReady()
        assertEquals(
            SpeechState.ReceivingPartial("bác ơi", RecognizerStage.ON_DEVICE),
            controller.state.value,
        )
    }

    @Test
    fun aStaleReadyCallbackCannotReviveAnOldSession() {
        val provider = FakeProvider()
        val controller = controller(provider)
        controller.start()
        val first = provider.handles.single()
        controller.cancel()

        first.events?.onReady()

        assertEquals(SpeechState.Idle, controller.state.value)
    }

    @Test
    fun aPartialDeliveredInsideStartIsNotWalkedBackToListening() {
        val provider = FakeProvider(configure = { it.partialDuringStart = "bác ơi" })
        val controller = controller(provider)

        controller.start()

        assertEquals(
            SpeechState.ReceivingPartial("bác ơi", RecognizerStage.ON_DEVICE),
            controller.state.value,
        )
    }

    @Test
    fun consentingAfterAFailureCreatesExactlyOneDeviceServiceAttempt() {
        val provider = FakeProvider()
        val controller = controller(provider)
        controller.start()
        provider.handles.single().events?.onError(RecognizerErrorCode.SERVER)
        assertEquals(SpeechState.OnDeviceFailed, controller.state.value)

        controller.start(allowDeviceService = true)

        assertEquals(1, provider.deviceServiceCalls)
        assertEquals("The on-device factory is not tried again", 1, provider.onDeviceCalls)
        assertEquals(SpeechState.Starting(RecognizerStage.DEVICE_SERVICE), controller.state.value)
    }

    @Test
    fun aFailingDeviceServiceDoesNotLoopBackToOnDevice() {
        val provider = FakeProvider()
        val controller = controller(provider)
        controller.start(allowDeviceService = true)
        val handle = provider.handles.single()

        handle.events?.onError(RecognizerErrorCode.SERVER)

        assertEquals(SpeechState.TemporaryFailure, controller.state.value)
        assertEquals("No second provider is created", 1, provider.handles.size)
        assertEquals(0, provider.onDeviceCalls)
    }

    @Test
    fun aMissingDeviceServiceIsItsOwnStateRatherThanAGenericFailure() {
        val provider = FakeProvider(onDeviceAvailable = false, deviceServiceCreates = false)
        val controller = controller(provider)

        controller.start(allowDeviceService = true)

        assertEquals(SpeechState.DeviceServiceUnavailable, controller.state.value)
    }

    @Test
    fun platformErrorsKeepTheirDistinctMeanings() {
        val expected = mapOf(
            RecognizerErrorCode.NO_SPEECH to SpeechState.NoSpeech,
            RecognizerErrorCode.BUSY to SpeechState.RecognizerBusy,
            RecognizerErrorCode.PERMISSION to SpeechState.PermissionDenied,
            RecognizerErrorCode.LANGUAGE_NOT_SUPPORTED to SpeechState.LanguageUnavailable,
            RecognizerErrorCode.AUDIO to SpeechState.TemporaryFailure,
            RecognizerErrorCode.TOO_MANY_REQUESTS to SpeechState.TemporaryFailure,
        )
        expected.forEach { (code, state) ->
            val provider = FakeProvider()
            val controller = controller(provider)
            controller.start()
            provider.handles.single().events?.onError(code)
            assertEquals("error $code", state, controller.state.value)
        }
    }

    // --- 6: exactly one destroy at every terminal boundary ------------------

    @Test
    fun finalErrorCancelAndDisposeEachDestroyTheHandleExactlyOnce() {
        fun handleAfter(action: (DefaultSpeechToTextController, FakeHandle) -> Unit): FakeHandle {
            val provider = FakeProvider()
            val controller = controller(provider)
            controller.start()
            val handle = provider.handles.single()
            action(controller, handle)
            return handle
        }

        val onFinal = handleAfter { _, handle -> handle.events?.onFinal("bác chuyển tiền") }
        assertEquals("final", 1, onFinal.destroyCount)

        val onError = handleAfter { _, handle -> handle.events?.onError(RecognizerErrorCode.NO_SPEECH) }
        assertEquals("error", 1, onError.destroyCount)

        val onCancel = handleAfter { controller, _ -> controller.cancel() }
        assertEquals("cancel", 1, onCancel.destroyCount)
        assertEquals(1, onCancel.cancelCount)

        val onDispose = handleAfter { controller, _ -> controller.dispose() }
        assertEquals("dispose", 1, onDispose.destroyCount)

        // And a second terminal call never destroys twice.
        val doubled = handleAfter { controller, handle ->
            handle.events?.onFinal("xong")
            controller.dispose()
            controller.cancel()
        }
        assertEquals("no double destroy", 1, doubled.destroyCount)
    }

    @Test
    fun startingAgainReleasesThePreviousRecognizer() {
        val provider = FakeProvider()
        val controller = controller(provider)
        controller.start()
        controller.start()

        assertEquals(2, provider.handles.size)
        assertEquals("The first recognizer must not be left alive", 1, provider.handles.first().destroyCount)
    }

    // --- 7: stale callbacks -------------------------------------------------

    @Test
    fun aCallbackFromAPreviousSessionIsIgnored() {
        val provider = FakeProvider()
        val controller = controller(provider)
        controller.start()
        val first = provider.handles.single()

        controller.start()
        val second = provider.handles.last()
        second.events?.onReady()

        // Android does deliver callbacks after `destroy()`.
        first.events?.onReady()
        first.events?.onPartial("nội dung cũ")
        first.events?.onFinal("kết quả cũ")
        first.events?.onError(RecognizerErrorCode.SERVER)

        assertEquals(
            "A dead recognizer must not overwrite the new attempt",
            SpeechState.Listening(RecognizerStage.ON_DEVICE),
            controller.state.value,
        )

        second.events?.onFinal("kết quả mới")
        assertEquals(SpeechState.FinalText("kết quả mới"), controller.state.value)
    }

    // --- 8: the bounded result window ---------------------------------------

    @Test
    fun endOfSpeechWaitsABoundedMomentForTheResult() {
        val window = ManualWindow()
        val provider = FakeProvider()
        val controller = controller(provider, window)
        controller.start()
        val handle = provider.handles.single()
        handle.events?.onReady()

        handle.events?.onEnd()

        // Still listening: `onEndOfSpeech` is not a result.
        assertEquals(SpeechState.Listening(RecognizerStage.ON_DEVICE), controller.state.value)
        assertNotNull("A bounded wait must be scheduled", window.scheduledDelay)
        assertTrue("The wait must be finite", window.scheduledDelay!! in 1..10_000)

        // The result arrives inside the window.
        handle.events?.onFinal("bác chuyển giúp cháu")
        assertEquals(SpeechState.FinalText("bác chuyển giúp cháu"), controller.state.value)
        assertTrue("The timer is cancelled by a real result", window.cancelled)
    }

    @Test
    fun aWindowThatExpiresWithoutAResultEndsAtTheEditableField() {
        val window = ManualWindow()
        val provider = FakeProvider()
        val controller = controller(provider, window)
        controller.start()
        val handle = provider.handles.single()

        handle.events?.onEnd()
        window.elapse()

        assertEquals(SpeechState.NoSpeech, controller.state.value)
        assertEquals("The silent recognizer is released", 1, handle.destroyCount)
    }

    // --- 9: the result is never submitted -----------------------------------

    @Test
    fun finalTextIsExposedForReviewAndNeverAnalyzedAutomatically() {
        val provider = FakeProvider()
        val controller = controller(provider)
        controller.start()
        val handle = provider.handles.single()

        handle.events?.onPartial("bác chuyển")
        assertEquals(
            SpeechState.ReceivingPartial("bác chuyển", RecognizerStage.ON_DEVICE),
            controller.state.value,
        )

        handle.events?.onFinal("  bác chuyển giúp cháu 5 triệu  ")

        // The controller's whole output is a string in a state — it has no way
        // to start an analysis, by construction.
        val state = controller.state.value
        assertTrue(state is SpeechState.FinalText)
        assertEquals("bác chuyển giúp cháu 5 triệu", (state as SpeechState.FinalText).text)
    }

    @Test
    fun stoppingAsksForTheResultRatherThanDiscardingIt() {
        val provider = FakeProvider()
        val controller = controller(provider)
        controller.start()
        val handle = provider.handles.single()

        controller.stop()

        assertTrue(handle.stopped)
        assertEquals("The recognizer stays alive until it answers", 0, handle.destroyCount)
        handle.events?.onFinal("xin chào")
        assertEquals(SpeechState.FinalText("xin chào"), controller.state.value)
    }

    @Test
    fun aDeniedMicrophoneIsItsOwnStateAndReleasesTheRecognizer() {
        val provider = FakeProvider()
        val controller = controller(provider)
        controller.start()

        controller.onPermissionDenied()

        assertEquals(SpeechState.PermissionDenied, controller.state.value)
        assertEquals(1, provider.handles.single().destroyCount)
    }

    // --- 10: every state has a sentence -------------------------------------

    @Test
    fun everySpeechStateHasUserSafeCopy() {
        val states = listOf(
            SpeechState.RequestingPermission,
            SpeechState.Starting(RecognizerStage.ON_DEVICE),
            SpeechState.Starting(RecognizerStage.DEVICE_SERVICE),
            SpeechState.Listening(RecognizerStage.ON_DEVICE),
            SpeechState.Listening(RecognizerStage.DEVICE_SERVICE),
            SpeechState.ReceivingPartial("bác ơi", RecognizerStage.ON_DEVICE),
            SpeechState.ReceivingPartial("bác ơi", RecognizerStage.DEVICE_SERVICE),
            SpeechState.FinalText("bác ơi"),
            SpeechState.NoSpeech,
            SpeechState.RecognizerBusy,
            SpeechState.PermissionDenied,
            SpeechState.LanguageUnavailable,
            SpeechState.OnDeviceUnavailable,
            SpeechState.OnDeviceFailed,
            SpeechState.DeviceServiceUnavailable,
            SpeechState.TemporaryFailure,
        )
        states.forEach { state ->
            assertNotNull("$state has no user-facing copy", UserSafeMessages.forSpeech(state))
        }
        // Idle is the only state with nothing to say.
        assertNull(UserSafeMessages.forSpeech(SpeechState.Idle))

        // The two listening sentences are distinct: a consented device-service
        // attempt must not be described as on-device.
        assertTrue(
            UserSafeMessages.forSpeech(SpeechState.Listening(RecognizerStage.ON_DEVICE)) !=
                UserSafeMessages.forSpeech(SpeechState.Listening(RecognizerStage.DEVICE_SERVICE)),
        )
    }
}
