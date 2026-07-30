package com.chan.app

import com.chan.app.notification.DisconnectReason
import com.chan.app.notification.EffectiveProtection
import com.chan.app.notification.InMemoryLastConnectedStore
import com.chan.app.notification.ListenerConnection
import com.chan.app.notification.ListenerRebinder
import com.chan.app.notification.ProtectionHealth
import com.chan.app.notification.ProtectionReconnectController
import com.chan.app.notification.ProtectionRuntimeMonitor
import com.chan.app.notification.ProtectionStatusNotifier
import com.chan.app.notification.ProtectionStatusReconciler
import com.chan.app.notification.ReconnectDecision
import com.chan.app.ui.UserSafeMessages
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Truthful protection health (§B1–B4).
 *
 * The failure this whole area exists to prevent is specific and was seen on a
 * real phone: Notification Access was granted, CHAN's listener was not bound,
 * and every screen said the user was protected. A permission is a setting. A
 * connection is a fact. These tests keep them apart.
 */
class ProtectionHealthTest {

    private class FakeRebinder(val succeeds: Boolean = true) : ListenerRebinder {
        var calls = 0
        override fun requestRebind(): Boolean {
            calls++
            return succeeds
        }
    }

    private class FakeStatusNotifier(var allowed: Boolean = true) : ProtectionStatusNotifier {
        var shows = 0
        var cancels = 0
        var visible = false

        override fun show(): Boolean {
            shows++
            visible = allowed
            return allowed
        }

        override fun cancel() {
            cancels++
            visible = false
        }
    }

    // --- 11, 12, 13: the runtime monitor ------------------------------------

    @Test
    fun aNewProcessStartsWithAnUnknownConnection() {
        // The store already holds a connection from a previous process; it must
        // not be promoted into current health.
        val monitor = ProtectionRuntimeMonitor(InMemoryLastConnectedStore(initial = 1_000L), now = { 5_000L })

        assertEquals(ListenerConnection.Unknown, monitor.connection.value)
        assertFalse(monitor.isConnected)
        assertEquals("History is still readable", 1_000L, monitor.lastConnectedAt)
    }

    @Test
    fun onlyTheListenerConnectedCallbackMarksTheListenerConnected() {
        val monitor = ProtectionRuntimeMonitor(InMemoryLastConnectedStore(), now = { 7_000L })

        monitor.onConnecting()
        assertEquals(ListenerConnection.Connecting(since = 7_000L), monitor.connection.value)
        assertFalse("A bind request is not a connection", monitor.isConnected)

        monitor.onConnected()
        assertEquals(ListenerConnection.Connected(7_000L), monitor.connection.value)
        assertEquals(7_000L, monitor.lastConnectedAt)
    }

    @Test
    fun disconnectAndDestroyRemoveTheConnectedState() {
        val monitor = ProtectionRuntimeMonitor(InMemoryLastConnectedStore(), now = { 7_000L })

        monitor.onConnected()
        monitor.onDisconnected(DisconnectReason.LISTENER_DISCONNECTED)
        assertEquals(
            ListenerConnection.Disconnected(DisconnectReason.LISTENER_DISCONNECTED),
            monitor.connection.value,
        )
        assertFalse(monitor.isConnected)

        monitor.onConnected()
        monitor.onDisconnected(DisconnectReason.SERVICE_DESTROYED)
        assertFalse(monitor.isConnected)
        // The timestamp survives as history, and only as history.
        assertEquals(7_000L, monitor.lastConnectedAt)
    }

    @Test
    fun aLateTimeoutCannotUndoARealConnection() {
        val monitor = ProtectionRuntimeMonitor(InMemoryLastConnectedStore(), now = { 7_000L })

        monitor.onConnecting()
        monitor.onConnected()
        monitor.endAttemptIfUnanswered()

        assertTrue(monitor.isConnected)
    }

    @Test
    fun aRebindThatProducesNoCallbackEndsAsAndroidNotConnectingUs() {
        val monitor = ProtectionRuntimeMonitor(InMemoryLastConnectedStore())

        monitor.onConnecting(rebindRequested = true)
        monitor.endAttemptIfUnanswered()

        assertEquals(
            ListenerConnection.Disconnected(DisconnectReason.REBIND_NOT_ANSWERED),
            monitor.connection.value,
        )
    }

    // --- 14, 15: the effective state ----------------------------------------

    @Test
    fun accessAndPreferenceWithoutAConnectionIsConnectingNotActive() {
        val health = EffectiveProtection.evaluate(
            zaloScanningEnabled = true,
            notificationAccessGranted = true,
            connection = ListenerConnection.Unknown,
            warningsAllowed = true,
        )

        assertEquals(ProtectionHealth.CONNECTING, health)
        assertFalse("Permission alone is not a live listener", health.listenerLive)
    }

    @Test
    fun theWholeTruthTableIsCovered() {
        fun evaluate(
            scanning: Boolean,
            access: Boolean,
            connection: ListenerConnection,
            warnings: Boolean = true,
        ) = EffectiveProtection.evaluate(scanning, access, connection, warnings)

        assertEquals(
            ProtectionHealth.OFF,
            evaluate(scanning = false, access = true, connection = ListenerConnection.Connected(1L)),
        )
        assertEquals(
            ProtectionHealth.ACCESS_REQUIRED,
            evaluate(scanning = true, access = false, connection = ListenerConnection.Unknown),
        )
        assertEquals(
            ProtectionHealth.CONNECTING,
            evaluate(scanning = true, access = true, connection = ListenerConnection.Connecting(since = 1L)),
        )
        assertEquals(
            ProtectionHealth.DISCONNECTED,
            evaluate(scanning = true, access = true, connection = ListenerConnection.Disconnected()),
        )
        assertEquals(
            ProtectionHealth.ACTIVE,
            evaluate(scanning = true, access = true, connection = ListenerConnection.Connected(1L)),
        )
        assertEquals(
            ProtectionHealth.ACTIVE_WITHOUT_WARNINGS,
            evaluate(
                scanning = true,
                access = true,
                connection = ListenerConnection.Connected(1L),
                warnings = false,
            ),
        )
    }

    @Test
    fun clearedAppDataRendersProtectionOffEvenWhenAndroidKeepsTheGrant() {
        // Clearing app data resets the in-app preference to its default of off.
        // Android may still list CHAN under Notification Access, and the
        // listener may even be bound — CHAN must not resume reading anything.
        val health = EffectiveProtection.evaluate(
            zaloScanningEnabled = false,
            notificationAccessGranted = true,
            connection = ListenerConnection.Connected(1L),
            warningsAllowed = true,
        )

        assertEquals(ProtectionHealth.OFF, health)
        assertFalse(health.listenerLive)
        assertFalse(ProtectionStatusReconciler.shouldShow(health))
    }

    @Test
    fun everyProtectionStateHasUserSafeCopy() {
        ProtectionHealth.entries.forEach { health ->
            assertNotNull("$health has no headline", UserSafeMessages.protectionHeadline(health))
            assertNotNull("$health has no home label", UserSafeMessages.protectionHomeLabel(health))
        }
    }

    // --- 16: the bounded rebind ---------------------------------------------

    @Test
    fun theAutomaticRebindHappensAtMostOncePerForegroundEvent() {
        val monitor = ProtectionRuntimeMonitor(InMemoryLastConnectedStore())
        val rebinder = FakeRebinder()
        val controller = ProtectionReconnectController(monitor, rebinder)

        controller.onForeground()
        assertEquals(ReconnectDecision.REQUESTED, controller.requestAutomatic(true, true))
        assertEquals(
            ReconnectDecision.ALREADY_ATTEMPTED,
            controller.requestAutomatic(true, true),
        )
        assertEquals("Exactly one rebind per foreground event", 1, rebinder.calls)
        assertTrue(monitor.connection.value is ListenerConnection.Connecting)
        assertTrue(monitor.attemptPending)

        // A new foreground event re-arms the single attempt, but only once the
        // outstanding one has ended: two requests in flight help nobody.
        controller.onForeground()
        assertEquals(ReconnectDecision.IN_FLIGHT, controller.requestAutomatic(true, true))
        assertEquals(1, rebinder.calls)

        monitor.endAttemptIfUnanswered()
        controller.onForeground()
        assertEquals(ReconnectDecision.REQUESTED, controller.requestAutomatic(true, true))
        assertEquals(2, rebinder.calls)
    }

    @Test
    fun aUserTappedReconnectMayTryAgainOnceTheLastAttemptEnded() {
        val monitor = ProtectionRuntimeMonitor(InMemoryLastConnectedStore())
        val rebinder = FakeRebinder()
        val controller = ProtectionReconnectController(monitor, rebinder)

        controller.onForeground()
        controller.requestAutomatic(true, true)
        // While the request is outstanding the control is disabled, and the
        // model refuses anyway.
        assertEquals(ReconnectDecision.IN_FLIGHT, controller.requestManual(true, true))

        monitor.endAttemptIfUnanswered()
        assertEquals(ReconnectDecision.REQUESTED, controller.requestManual(true, true))

        assertEquals(2, rebinder.calls)
    }

    @Test
    fun rebindIsNotRequestedWhenThereIsNothingToReconnect() {
        val monitor = ProtectionRuntimeMonitor(InMemoryLastConnectedStore(), now = { 1L })
        val rebinder = FakeRebinder()
        val controller = ProtectionReconnectController(monitor, rebinder)

        controller.onForeground()
        assertEquals(
            ReconnectDecision.SCANNING_DISABLED,
            controller.requestAutomatic(zaloScanningEnabled = false, notificationAccessGranted = true),
        )
        // Missing access opens settings instead; a rebind would do nothing.
        assertEquals(
            ReconnectDecision.ACCESS_MISSING,
            controller.requestAutomatic(zaloScanningEnabled = true, notificationAccessGranted = false),
        )

        monitor.onConnected()
        assertEquals(
            ReconnectDecision.ALREADY_CONNECTED,
            controller.requestManual(zaloScanningEnabled = true, notificationAccessGranted = true),
        )
        assertEquals(0, rebinder.calls)
    }

    @Test
    fun aRefusedRebindIsReportedAsDisconnectedRatherThanConnecting() {
        val monitor = ProtectionRuntimeMonitor(InMemoryLastConnectedStore())
        val controller = ProtectionReconnectController(monitor, FakeRebinder(succeeds = false))

        controller.onForeground()

        assertEquals(ReconnectDecision.REFUSED, controller.requestAutomatic(true, true))
        assertFalse(monitor.isConnected)
        assertTrue(monitor.connection.value is ListenerConnection.Disconnected)
    }

    // --- 17, 18, 19: the ongoing status indicator ---------------------------

    @Test
    fun theStatusNotificationIsPublishedOnlyFromARealConnectedState() {
        val notifier = FakeStatusNotifier()

        assertTrue(ProtectionStatusReconciler.reconcile(ProtectionHealth.ACTIVE, notifier))
        assertEquals(1, notifier.shows)
        assertTrue(notifier.visible)
    }

    @Test
    fun theStatusNotificationIsCancelledForEveryInactivePrerequisite() {
        ProtectionHealth.entries
            .filter { it != ProtectionHealth.ACTIVE }
            .forEach { health ->
                val notifier = FakeStatusNotifier()
                // Something was showing from an earlier, healthier moment.
                notifier.show()

                val visible = ProtectionStatusReconciler.reconcile(health, notifier)

                assertFalse("$health must not show the indicator", visible)
                assertEquals("$health must cancel it", 1, notifier.cancels)
                assertFalse(notifier.visible)
            }
    }

    @Test
    fun aStaleIndicatorIsCancelledBeforeAnyConnectionIsReported() {
        // Exactly the app-startup case: a killed process left an indicator, and
        // the monitor is Unknown until a listener callback arrives.
        val monitor = ProtectionRuntimeMonitor(InMemoryLastConnectedStore(initial = 1_000L))
        val notifier = FakeStatusNotifier()

        val health = EffectiveProtection.evaluate(
            zaloScanningEnabled = true,
            notificationAccessGranted = true,
            connection = monitor.connection.value,
            warningsAllowed = true,
        )
        ProtectionStatusReconciler.reconcile(health, notifier)

        assertEquals(ProtectionHealth.CONNECTING, health)
        assertEquals(1, notifier.cancels)
        assertEquals(0, notifier.shows)

        // Only a real callback may put it back.
        monitor.onConnected()
        val afterCallback = EffectiveProtection.evaluate(true, true, monitor.connection.value, true)
        ProtectionStatusReconciler.reconcile(afterCallback, notifier)
        assertEquals(1, notifier.shows)
    }

    @Test
    fun theStatusNotificationHasNowhereToPutSourceContent() {
        // `show()` takes no arguments at all: there is no parameter through
        // which a sender, message, or analysis could reach the indicator.
        val showParameters = ProtectionStatusNotifier::class.java
            .getMethod("show")
            .parameterTypes
        assertEquals(0, showParameters.size)

        val cancelParameters = ProtectionStatusNotifier::class.java
            .getMethod("cancel")
            .parameterTypes
        assertEquals(0, cancelParameters.size)

        // And the reconciler's only input is the computed state enum.
        val reconcilerInputs = ProtectionStatusReconciler::class.java
            .getMethod("shouldShow", ProtectionHealth::class.java)
        assertNotNull(reconcilerInputs)
    }

    @Test
    fun aStatusNotifierThatIsNotAllowedToPostReportsFailureRatherThanPretending() {
        val notifier = FakeStatusNotifier(allowed = false)

        assertFalse(ProtectionStatusReconciler.reconcile(ProtectionHealth.ACTIVE, notifier))
        assertFalse(notifier.visible)
    }
}
