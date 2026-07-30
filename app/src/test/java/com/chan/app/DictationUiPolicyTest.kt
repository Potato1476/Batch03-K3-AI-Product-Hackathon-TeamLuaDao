package com.chan.app

import com.chan.app.speech.RecognizerStage
import com.chan.app.speech.SpeechState
import com.chan.app.ui.DictationUiPolicy
import com.chan.app.ui.MicAction
import com.chan.app.ui.MicEmphasis
import com.chan.app.ui.UserSafeMessages
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * What the microphone card offers, state by state (§A5).
 *
 * The bug this file exists to prevent is small and was very visible on the
 * phone: "Đọc bằng micro" was drawn for every state that was not actively
 * listening, so the explanation of a *failed* microphone appeared underneath a
 * microphone button that would only reproduce the failure. Recovery has to lead
 * with the action that can actually change the outcome.
 */
class DictationUiPolicyTest {

    /** Every state the control can be asked to render. */
    private val allStates = listOf(
        SpeechState.Idle,
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
        SpeechState.TemporaryFailure,
        SpeechState.PermissionDenied,
        SpeechState.LanguageUnavailable,
        SpeechState.OnDeviceUnavailable,
        SpeechState.OnDeviceFailed,
        SpeechState.DeviceServiceUnavailable,
    )

    private fun actions(state: SpeechState) = DictationUiPolicy.forState(state).buttons.map { it.action }

    // --- at rest and after a result -----------------------------------------

    @Test
    fun atRestTheOnlyOfferIsTheMicrophone() {
        assertEquals(listOf(MicAction.START), actions(SpeechState.Idle))
    }

    @Test
    fun afterAResultTheMicrophoneIsOfferedAgain() {
        val ui = DictationUiPolicy.forState(SpeechState.FinalText("bác chuyển giúp cháu"))

        assertEquals(listOf(MicAction.START), ui.buttons.map { it.action })
        // The result is read first, then the option to dictate more.
        assertTrue(ui.statusBeforeActions)
    }

    // --- an active session --------------------------------------------------

    @Test
    fun listeningOffersStopAndCancelAndNeverTheGenericMicrophone() {
        listOf(RecognizerStage.ON_DEVICE, RecognizerStage.DEVICE_SERVICE).forEach { stage ->
            val ui = DictationUiPolicy.forState(SpeechState.Listening(stage))

            assertEquals(listOf(MicAction.STOP, MicAction.CANCEL), ui.buttons.map { it.action })
            assertEquals(MicEmphasis.PRIMARY, ui.buttons.first().emphasis)
            assertFalse("$stage must not offer a second start", ui.has(MicAction.START))
            // The on-device claim is only ever made for the on-device stage.
            assertEquals(stage == RecognizerStage.ON_DEVICE, ui.showOnDeviceNote)
        }
    }

    @Test
    fun aPartialResultKeepsTheSameControlsAndIsDisplayed() {
        val ui = DictationUiPolicy.forState(
            SpeechState.ReceivingPartial("bác chuyển", RecognizerStage.ON_DEVICE),
        )

        assertEquals(listOf(MicAction.STOP, MicAction.CANCEL), ui.buttons.map { it.action })
        assertTrue(ui.showPartial)
    }

    @Test
    fun startingShowsNoStopButtonSoAnImmediateFailureCannotFlicker() {
        // The Xiaomi on-device provider answers within a frame or two. If
        // Starting rendered "Dừng nghe", the button would appear and vanish
        // before it could be read.
        listOf(RecognizerStage.ON_DEVICE, RecognizerStage.DEVICE_SERVICE).forEach { stage ->
            val ui = DictationUiPolicy.forState(SpeechState.Starting(stage))

            assertEquals(listOf(MicAction.PREPARING), ui.buttons.map { it.action })
            assertFalse("A recognizer that is not open yet cannot be stopped", ui.has(MicAction.STOP))
            assertFalse(ui.has(MicAction.START))
            // The control keeps its place in the layout instead of disappearing.
            assertFalse("The placeholder must not be tappable", ui.buttons.single().enabled)
            assertEquals(MicEmphasis.SECONDARY, ui.buttons.single().emphasis)
            assertFalse("Nothing is claimed about the microphone yet", ui.showOnDeviceNote)
        }
    }

    @Test
    fun theButtonSlotSurvivesTheWholeStartSequenceWithoutReappearing() {
        // Tap → Starting → (ready) Listening. The generic microphone button is
        // gone from the moment of the tap and does not come back mid-sequence.
        val sequence = listOf(
            SpeechState.Idle,
            SpeechState.Starting(RecognizerStage.ON_DEVICE),
            SpeechState.Listening(RecognizerStage.ON_DEVICE),
        )
        val startVisibility = sequence.map { DictationUiPolicy.forState(it).has(MicAction.START) }
        assertEquals(listOf(true, false, false), startVisibility)

        // And the failing sequence never shows a stop button at all.
        val failing = listOf(
            SpeechState.Idle,
            SpeechState.Starting(RecognizerStage.ON_DEVICE),
            SpeechState.OnDeviceFailed,
        )
        assertTrue(failing.none { DictationUiPolicy.forState(it).has(MicAction.STOP) })
    }

    // --- the recovery path --------------------------------------------------

    @Test
    fun aFailedOnDeviceRecognizerLeadsWithTheConsentedFallback() {
        listOf(SpeechState.OnDeviceFailed, SpeechState.OnDeviceUnavailable).forEach { state ->
            val ui = DictationUiPolicy.forState(state)

            assertEquals(
                "$state must offer exactly the three documented actions",
                listOf(MicAction.USE_DEVICE_SERVICE, MicAction.RETRY_ON_DEVICE, MicAction.DISMISS),
                ui.buttons.map { it.action },
            )
            assertEquals(MicEmphasis.PRIMARY, ui.buttons.first().emphasis)
            assertTrue("Secondary and tertiary", ui.buttons.drop(1).all { it.emphasis == MicEmphasis.SECONDARY })

            // The generic microphone button would compete with these three and
            // only reproduce the failure.
            assertFalse("$state must hide the generic microphone", ui.has(MicAction.START))
            // The explanation comes before the decision, with the privacy
            // consequence attached to it.
            assertTrue(ui.statusBeforeActions)
            assertTrue(ui.showDeviceServicePrivacy)
        }
    }

    @Test
    fun aTransientFailureOffersAClearlyLabelledRetry() {
        listOf(
            SpeechState.NoSpeech,
            SpeechState.RecognizerBusy,
            SpeechState.TemporaryFailure,
        ).forEach { state ->
            val ui = DictationUiPolicy.forState(state)

            assertEquals("$state", listOf(MicAction.RETRY), ui.buttons.map { it.action })
            assertEquals(
                "$state must say 'Thử lại', not 'Đọc bằng micro'",
                R.string.action_retry,
                ui.buttons.single().labelRes,
            )
            assertFalse(ui.has(MicAction.START))
            assertTrue("The reason is read before the retry", ui.statusBeforeActions)
        }
    }

    @Test
    fun aBrokenRecognizerIsNeverImmediatelyRetried() {
        // Permission denied, no Vietnamese, no speech service: tapping anything
        // that starts a recognizer would fail again in the same way.
        val cannotWork = mapOf(
            SpeechState.PermissionDenied to MicAction.OPEN_APP_SETTINGS,
            SpeechState.LanguageUnavailable to MicAction.OPEN_SPEECH_SETTINGS,
            SpeechState.DeviceServiceUnavailable to MicAction.OPEN_SPEECH_SETTINGS,
        )
        cannotWork.forEach { (state, expected) ->
            val ui = DictationUiPolicy.forState(state)

            assertEquals("$state", listOf(expected), ui.buttons.map { it.action })
            listOf(
                MicAction.START,
                MicAction.RETRY,
                MicAction.RETRY_ON_DEVICE,
                MicAction.USE_DEVICE_SERVICE,
            ).forEach { forbidden ->
                assertFalse("$state must not offer $forbidden", ui.has(forbidden))
            }
            // Paste and the image picker are still there and are pointed at.
            assertTrue("$state must keep the alternatives visible", ui.showAlternativesHint)
            assertTrue(ui.statusBeforeActions)
        }
    }

    @Test
    fun aPendingPermissionDialogOffersNothingBehindIt() {
        assertTrue(DictationUiPolicy.forState(SpeechState.RequestingPermission).buttons.isEmpty())
    }

    // --- table-wide invariants ----------------------------------------------

    @Test
    fun onlyRestAndResultOfferTheGenericMicrophoneButton() {
        val offering = allStates.filter { DictationUiPolicy.forState(it).has(MicAction.START) }

        assertEquals(
            listOf<SpeechState>(SpeechState.Idle, SpeechState.FinalText("bác ơi")),
            offering,
        )
    }

    @Test
    fun everyStateRendersSomethingTheUserCanReadAndActOn() {
        allStates.forEach { state ->
            val ui = DictationUiPolicy.forState(state)

            // Every state has a sentence…
            if (state != SpeechState.Idle) {
                assertNotNull("$state has no status copy", UserSafeMessages.forSpeech(state))
            }
            // …every button has a real label…
            ui.buttons.forEach { button ->
                assertTrue("$state: ${button.action} has no label", button.labelRes != 0)
            }
            // …no state repeats an action…
            assertEquals(
                "$state offers a duplicated action",
                ui.buttons.map { it.action }.size,
                ui.buttons.map { it.action }.toSet().size,
            )
            // …and at most one action is emphasised.
            assertTrue(
                "$state emphasises more than one action",
                ui.buttons.count { it.emphasis == MicEmphasis.PRIMARY } <= 1,
            )
        }
    }

    @Test
    fun onlyAnActiveSessionCanBeStoppedOrCancelled() {
        allStates.forEach { state ->
            val ui = DictationUiPolicy.forState(state)
            val offersSessionControls = ui.has(MicAction.STOP) || ui.has(MicAction.CANCEL)
            val isListening = state is SpeechState.Listening || state is SpeechState.ReceivingPartial

            assertEquals("$state", isListening, offersSessionControls)
        }
    }

    @Test
    fun theOnDeviceClaimIsNeverMadeOutsideALiveOnDeviceSession() {
        allStates.filter { DictationUiPolicy.forState(it).showOnDeviceNote }.forEach { state ->
            assertEquals(
                "$state must not claim on-device processing",
                RecognizerStage.ON_DEVICE,
                state.listeningStage,
            )
            assertTrue("$state is not a live session", state is SpeechState.Listening || state is SpeechState.ReceivingPartial)
        }
    }
}
