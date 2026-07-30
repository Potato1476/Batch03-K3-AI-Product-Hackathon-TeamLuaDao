package com.chan.app

import com.chan.app.speech.DefaultSpeechToTextController
import com.chan.app.speech.RecognitionEvents
import com.chan.app.speech.RecognizerErrorCode
import com.chan.app.speech.RecognizerHandle
import com.chan.app.speech.RecognizerProvider
import com.chan.app.speech.SpeechRequest
import com.chan.app.speech.SpeechState
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Dictation (§C2, §C3).
 *
 * Two promises are under test. Audio prefers the on-device recognizer and never
 * silently reaches for one that may stream to a provider. And recognized speech
 * lands in an editable field — CHAN never submits what it heard.
 */
class SpeechToTextControllerTest {

    private class FakeHandle(val label: String) : RecognizerHandle {
        var events: RecognitionEvents? = null
        var startedWith: SpeechRequest? = null
        var stopped = false
        var cancelled = false
        var destroyed = false
        var listenerSetBeforeStart = false

        override fun setListener(events: RecognitionEvents) {
            this.events = events
        }

        override fun start(request: SpeechRequest) {
            listenerSetBeforeStart = events != null
            startedWith = request
        }

        override fun stop() {
            stopped = true
        }

        override fun cancel() {
            cancelled = true
        }

        override fun destroy() {
            destroyed = true
        }
    }

    private class FakeProvider(
        val onDeviceAvailable: Boolean,
        val onDeviceCreates: Boolean = true,
        val deviceServiceCreates: Boolean = true,
    ) : RecognizerProvider {
        var onDeviceCalls = 0
        var deviceServiceCalls = 0
        val handles = mutableListOf<FakeHandle>()

        override fun isOnDeviceAvailable(): Boolean = onDeviceAvailable

        override fun createOnDevice(): RecognizerHandle? {
            onDeviceCalls++
            if (!onDeviceCreates) return null
            return FakeHandle("on-device").also { handles += it }
        }

        override fun createDeviceService(): RecognizerHandle? {
            deviceServiceCalls++
            if (!deviceServiceCreates) return null
            return FakeHandle("device-service").also { handles += it }
        }
    }

    @Test
    fun onDeviceRecognitionIsPreferredWhenAvailable() {
        val provider = FakeProvider(onDeviceAvailable = true)
        val controller = DefaultSpeechToTextController(provider)

        controller.start()

        assertEquals(1, provider.onDeviceCalls)
        assertEquals("The device service must not be touched", 0, provider.deviceServiceCalls)
        assertTrue(controller.usingOnDeviceRecognizer)
        assertEquals(SpeechState.Listening, controller.state.value)

        val handle = provider.handles.single()
        assertTrue("The listener must be attached before listening", handle.listenerSetBeforeStart)
        assertEquals("vi-VN", handle.startedWith?.languageTag)
        assertTrue(handle.startedWith!!.partialResults)
        assertTrue(handle.startedWith!!.preferOffline)
    }

    @Test
    fun theFallbackRecognizerRequiresExplicitConfirmation() {
        val provider = FakeProvider(onDeviceAvailable = false)
        val controller = DefaultSpeechToTextController(provider)

        controller.start(allowDeviceService = false)

        // Nothing was created, so no audio was captured.
        assertEquals(0, provider.deviceServiceCalls)
        assertTrue(provider.handles.isEmpty())
        assertEquals(SpeechState.OnDeviceUnavailable, controller.state.value)

        // Only after the user agrees.
        controller.start(allowDeviceService = true)
        assertEquals(1, provider.deviceServiceCalls)
        assertEquals(SpeechState.Listening, controller.state.value)
        // And the UI must not claim on-device privacy it does not have.
        assertFalse(controller.usingOnDeviceRecognizer)
    }

    @Test
    fun anUnsupportedOnDeviceFactoryFallsBackToTheSameConfirmation() {
        // `isOnDeviceRecognitionAvailable` says yes but the factory refuses.
        val provider = FakeProvider(onDeviceAvailable = true, onDeviceCreates = false)
        val controller = DefaultSpeechToTextController(provider)

        controller.start(allowDeviceService = false)
        assertEquals(SpeechState.OnDeviceUnavailable, controller.state.value)
        assertEquals(0, provider.deviceServiceCalls)
    }

    @Test
    fun finalTextIsExposedForReviewAndNeverAnalyzedAutomatically() {
        val provider = FakeProvider(onDeviceAvailable = true)
        val controller = DefaultSpeechToTextController(provider)
        controller.start()
        val handle = provider.handles.single()

        handle.events?.onPartial("bác chuyển")
        assertEquals(SpeechState.ReceivingPartial("bác chuyển"), controller.state.value)

        handle.events?.onFinal("  bác chuyển giúp cháu 5 triệu  ")

        // The controller's whole output is a string in a state — it has no way
        // to start an analysis, by construction.
        val state = controller.state.value
        assertTrue(state is SpeechState.FinalText)
        assertEquals("bác chuyển giúp cháu 5 triệu", (state as SpeechState.FinalText).text)
        assertFalse("Listening ended, nothing was submitted", handle.destroyed)
    }

    @Test
    fun leavingTheScreenCancelsAndDestroysTheRecognizer() {
        val provider = FakeProvider(onDeviceAvailable = true)
        val controller = DefaultSpeechToTextController(provider)
        controller.start()
        val handle = provider.handles.single()

        controller.dispose()

        assertTrue("Listening must stop", handle.cancelled)
        assertTrue("The recognizer must be released", handle.destroyed)
        assertEquals(SpeechState.Idle, controller.state.value)
        assertFalse(controller.usingOnDeviceRecognizer)
    }

    @Test
    fun startingAgainReleasesThePreviousRecognizer() {
        val provider = FakeProvider(onDeviceAvailable = true)
        val controller = DefaultSpeechToTextController(provider)
        controller.start()
        controller.start()

        assertEquals(2, provider.handles.size)
        assertTrue("The first recognizer must not be left alive", provider.handles.first().destroyed)
    }

    @Test
    fun everyRecognizerErrorLeavesTheUserAtAnEditableField() {
        val provider = FakeProvider(onDeviceAvailable = true)
        val controller = DefaultSpeechToTextController(provider)

        val expected = mapOf(
            RecognizerErrorCode.NO_SPEECH to SpeechState.NoSpeech,
            RecognizerErrorCode.BUSY to SpeechState.RecognizerBusy,
            RecognizerErrorCode.PERMISSION to SpeechState.PermissionDenied,
            RecognizerErrorCode.NETWORK_OR_PROVIDER to SpeechState.ProviderUnavailable,
            RecognizerErrorCode.OTHER to SpeechState.ProviderUnavailable,
        )
        expected.forEach { (code, state) ->
            controller.start()
            provider.handles.last().events?.onError(code)
            assertEquals("error $code", state, controller.state.value)
            // Never a terminal state the user cannot leave.
            assertNull(UserSafeMessagesProbe.missing(controller.state.value))
        }
    }

    @Test
    fun aDeniedMicrophoneIsItsOwnStateAndReleasesTheRecognizer() {
        val provider = FakeProvider(onDeviceAvailable = true)
        val controller = DefaultSpeechToTextController(provider)
        controller.start()

        controller.onPermissionDenied()

        assertEquals(SpeechState.PermissionDenied, controller.state.value)
        assertTrue(provider.handles.single().destroyed)
    }

    @Test
    fun aProviderThatCannotBeCreatedIsReportedRatherThanIgnored() {
        val provider = FakeProvider(
            onDeviceAvailable = false,
            deviceServiceCreates = false,
        )
        val controller = DefaultSpeechToTextController(provider)

        controller.start(allowDeviceService = true)
        assertEquals(SpeechState.ProviderUnavailable, controller.state.value)
    }
}

/** Every speech state must map to a sentence the user can read. */
private object UserSafeMessagesProbe {
    fun missing(state: SpeechState): String? =
        if (state == SpeechState.Idle || com.chan.app.ui.UserSafeMessages.forSpeech(state) != null) {
            null
        } else {
            state.toString()
        }
}
