package com.chan.app

import com.chan.app.notification.DisconnectReason
import com.chan.app.notification.EffectiveProtection
import com.chan.app.notification.InMemoryLastConnectedStore
import com.chan.app.notification.ListenerConnection
import com.chan.app.notification.ListenerRebinder
import com.chan.app.notification.ProtectionHealth
import com.chan.app.notification.ProtectionReconnectController
import com.chan.app.notification.ProtectionRuntimeMonitor
import com.chan.app.notification.ReconnectDecision
import com.chan.app.ui.ActionEmphasis
import com.chan.app.ui.ProtectionAction
import com.chan.app.ui.ProtectionRecoveryPolicy
import com.chan.app.ui.UserSafeMessages
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Listener recovery: what CHAN says, and what it offers, when Android will not
 * connect it.
 *
 * The physical evidence this is written against, from the Xiaomi on Android 15:
 * the process alive, scanning on, Notification Access granted, and CHAN absent
 * from the system's live listener list for over thirty seconds, with
 * `requestRebind` producing no callback. The old copy — "Bảo vệ Zalo đang mất
 * kết nối" — described that as a connection dropping, which points a worried
 * person at their wifi or their Zalo account. Neither is involved.
 */
class ProtectionRecoveryPolicyTest {

    private class FakeRebinder(val succeeds: Boolean = true) : ListenerRebinder {
        var calls = 0
        override fun requestRebind(): Boolean {
            calls++
            return succeeds
        }
    }

    private fun monitor(now: () -> Long = { 1_000L }) =
        ProtectionRuntimeMonitor(InMemoryLastConnectedStore(), now)

    // --- the disconnected copy ---------------------------------------------

    @Test
    fun theDisconnectedHeadlineNamesAndroidRatherThanASeveredConnection() {
        val ui = ProtectionRecoveryPolicy.forHealth(ProtectionHealth.DISCONNECTED)

        assertEquals(R.string.protection_state_not_connected, ui.headlineRes)
        // The headline the screens show is the policy's, so they cannot drift.
        assertEquals(
            ui.headlineRes,
            UserSafeMessages.protectionHeadline(ProtectionHealth.DISCONNECTED),
        )
    }

    @Test
    fun theDisconnectedStateRulesOutTheTwoWrongSuspicions() {
        val ui = ProtectionRecoveryPolicy.forHealth(ProtectionHealth.DISCONNECTED)

        assertEquals(R.string.protection_not_connected_not_network, ui.reassuranceRes)
    }

    @Test
    fun theDisconnectedStateLeadsWithTheSettingsRemedyAndExplainsTheSteps() {
        val ui = ProtectionRecoveryPolicy.forHealth(ProtectionHealth.DISCONNECTED)

        val primary = ui.buttons.first()
        assertEquals(ProtectionAction.OPEN_NOTIFICATION_ACCESS, primary.action)
        assertEquals(ActionEmphasis.PRIMARY, primary.emphasis)
        assertEquals(R.string.protection_open_access_settings, primary.labelRes)
        assertTrue(primary.enabled)

        // Opening the screen is not enough on its own: the user has to toggle.
        assertEquals(R.string.protection_not_connected_instruction, ui.instructionRes)
    }

    @Test
    fun reconnectRemainsAvailableAsASecondaryAttempt() {
        val ui = ProtectionRecoveryPolicy.forHealth(ProtectionHealth.DISCONNECTED)
        val reconnect = ui.button(ProtectionAction.RECONNECT)

        assertNotNull("Kết nối lại must still be offered", reconnect)
        assertEquals(ActionEmphasis.SECONDARY, reconnect!!.emphasis)
        assertEquals(R.string.protection_reconnect, reconnect.labelRes)
        assertTrue(reconnect.enabled)
        // Below the remedy, not above it.
        assertTrue(
            ui.buttons.indexOf(reconnect) >
                ui.buttons.indexOfFirst { it.action == ProtectionAction.OPEN_NOTIFICATION_ACCESS },
        )
    }

    // --- the pending attempt ------------------------------------------------

    @Test
    fun anOutstandingAttemptIsItsOwnStateAndCannotBeTappedAgain() {
        val ui = ProtectionRecoveryPolicy.forHealth(ProtectionHealth.RECONNECTING)

        assertEquals(R.string.protection_state_reconnecting, ui.headlineRes)
        val reconnect = ui.button(ProtectionAction.RECONNECT)
        assertNotNull(reconnect)
        assertFalse("A second request changes nothing", reconnect!!.enabled)
        assertTrue(ProtectionHealth.RECONNECTING.attemptPending)
    }

    @Test
    fun aUserRequestedRebindShowsAsReconnectingAndAnOrdinaryBindDoesNot() {
        val requested = EffectiveProtection.evaluate(
            zaloScanningEnabled = true,
            notificationAccessGranted = true,
            connection = ListenerConnection.Connecting(since = 1L, rebindRequested = true),
            warningsAllowed = true,
        )
        assertEquals(ProtectionHealth.RECONNECTING, requested)

        val ordinary = EffectiveProtection.evaluate(
            zaloScanningEnabled = true,
            notificationAccessGranted = true,
            connection = ListenerConnection.Connecting(since = 1L),
            warningsAllowed = true,
        )
        assertEquals(ProtectionHealth.CONNECTING, ordinary)
    }

    @Test
    fun repeatedReconnectTapsProduceExactlyOneRequest() {
        val monitor = monitor()
        val rebinder = FakeRebinder()
        val controller = ProtectionReconnectController(monitor, rebinder)

        assertEquals(ReconnectDecision.REQUESTED, controller.requestManual(true, true))
        assertEquals(ReconnectDecision.IN_FLIGHT, controller.requestManual(true, true))
        assertEquals(ReconnectDecision.IN_FLIGHT, controller.requestManual(true, true))

        assertEquals("Android is already ignoring one request", 1, rebinder.calls)
        assertTrue(monitor.attemptPending)
    }

    @Test
    fun aNewAttemptIsAllowedOnceTheWindowHasEnded() {
        val monitor = monitor()
        val rebinder = FakeRebinder()
        val controller = ProtectionReconnectController(monitor, rebinder)

        controller.requestManual(true, true)
        monitor.endAttemptIfUnanswered()

        assertFalse(monitor.attemptPending)
        assertEquals(ReconnectDecision.REQUESTED, controller.requestManual(true, true))
        assertEquals(2, rebinder.calls)
    }

    // --- the staged failure -------------------------------------------------

    @Test
    fun anUnansweredRequestIsReportedAsAndroidNotConnectingUs() {
        val monitor = monitor()
        ProtectionReconnectController(monitor, FakeRebinder()).requestManual(true, true)

        monitor.endAttemptIfUnanswered()

        assertEquals(
            ListenerConnection.Disconnected(DisconnectReason.REBIND_NOT_ANSWERED),
            monitor.connection.value,
        )
        val health = EffectiveProtection.evaluate(true, true, monitor.connection.value, true)
        assertEquals(ProtectionHealth.DISCONNECTED, health)
        // And that state leads with the manual remedy, not with another wait.
        assertEquals(
            ProtectionAction.OPEN_NOTIFICATION_ACCESS,
            ProtectionRecoveryPolicy.forHealth(health).buttons.first().action,
        )
    }

    @Test
    fun theWindowOnlyBoundsTheClaimAndIsNotSoldAsAFix() {
        // A short bound is the point: an ignored requestRebind is not ignored
        // any less after thirty seconds, so the window must not be long enough
        // to look like waiting is the strategy.
        assertTrue(ProtectionReconnectController.REBIND_WINDOW_MILLIS <= 10_000L)

        // Ending the window changes what CHAN says, not what Android did.
        val monitor = monitor()
        val rebinder = FakeRebinder()
        ProtectionReconnectController(monitor, rebinder).requestManual(true, true)
        monitor.endAttemptIfUnanswered()

        assertEquals("No extra rebind is fired by the window ending", 1, rebinder.calls)
    }

    @Test
    fun aLateConnectionDuringTheWindowStillWins() {
        val monitor = monitor()
        ProtectionReconnectController(monitor, FakeRebinder()).requestManual(true, true)

        monitor.onConnected()
        monitor.endAttemptIfUnanswered()

        assertTrue(monitor.isConnected)
        assertEquals(
            ProtectionHealth.ACTIVE,
            EffectiveProtection.evaluate(true, true, monitor.connection.value, true),
        )
    }

    // --- never active without the callback ----------------------------------

    @Test
    fun nothingShortOfOnListenerConnectedEverPresentsAsActive() {
        val notConnected = listOf(
            ListenerConnection.Unknown,
            ListenerConnection.Connecting(since = 1L),
            ListenerConnection.Connecting(since = 1L, rebindRequested = true),
            ListenerConnection.Disconnected(DisconnectReason.LISTENER_DISCONNECTED),
            ListenerConnection.Disconnected(DisconnectReason.SERVICE_DESTROYED),
            ListenerConnection.Disconnected(DisconnectReason.REBIND_NOT_ANSWERED),
        )
        notConnected.forEach { connection ->
            val health = EffectiveProtection.evaluate(true, true, connection, true)
            val ui = ProtectionRecoveryPolicy.forHealth(health)

            assertFalse("$connection must not present as active", ui.presentsAsActive)
            assertFalse(health.listenerLive)
            assertTrue(
                "$connection must not use the active headline",
                ui.headlineRes != R.string.protection_state_active,
            )
        }

        // Only the real callback flips it.
        val monitor = monitor()
        monitor.onConnecting(rebindRequested = true)
        assertFalse(ProtectionRecoveryPolicy.forHealth(ProtectionHealth.RECONNECTING).presentsAsActive)
        monitor.onConnected()
        val active = EffectiveProtection.evaluate(true, true, monitor.connection.value, true)
        assertTrue(ProtectionRecoveryPolicy.forHealth(active).presentsAsActive)
    }

    // --- table-wide invariants ----------------------------------------------

    @Test
    fun everyHealthStateHasAHeadlineAndNoDuplicatedAction() {
        ProtectionHealth.entries.forEach { health ->
            val ui = ProtectionRecoveryPolicy.forHealth(health)

            assertTrue("$health has no headline", ui.headlineRes != 0)
            ui.buttons.forEach { button ->
                assertTrue("$health: ${button.action} has no label", button.labelRes != 0)
            }
            assertEquals(
                "$health repeats an action",
                ui.buttons.size,
                ui.buttons.map { it.action }.toSet().size,
            )
            assertTrue(
                "$health emphasises more than one action",
                ui.buttons.count { it.emphasis == ActionEmphasis.PRIMARY } <= 1,
            )
        }
    }

    @Test
    fun onlyTheDisconnectedStateExplainsTheManualToggle() {
        val withInstruction = ProtectionHealth.entries
            .filter { ProtectionRecoveryPolicy.forHealth(it).instructionRes != null }

        assertEquals(listOf(ProtectionHealth.DISCONNECTED), withInstruction)
    }

    @Test
    fun aHealthyStateOffersNothingToFix() {
        val active = ProtectionRecoveryPolicy.forHealth(ProtectionHealth.ACTIVE)

        assertTrue(active.buttons.isEmpty())
        assertNull(active.instructionRes)
        assertNull(active.reassuranceRes)
        assertTrue(active.presentsAsActive)
    }

    @Test
    fun everyHealthStateHasAHomeLabelAndTheyStayDistinct() {
        val labels = ProtectionHealth.entries.associateWith {
            UserSafeMessages.protectionHomeLabel(it)
        }
        labels.forEach { (health, res) -> assertTrue("$health", res != 0) }
        // Connecting and reconnecting must not read identically on Home.
        assertTrue(
            labels.getValue(ProtectionHealth.CONNECTING) !=
                labels.getValue(ProtectionHealth.RECONNECTING),
        )
        assertTrue(
            labels.getValue(ProtectionHealth.DISCONNECTED) !=
                labels.getValue(ProtectionHealth.ACCESS_REQUIRED),
        )
    }
}
