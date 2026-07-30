package com.chan.app.ui

import androidx.annotation.StringRes
import com.chan.app.R
import com.chan.app.notification.ProtectionHealth

/** Something the protection headline can offer. */
enum class ProtectionAction {
    /** Android's Notification Access list, where the grant is toggled by hand. */
    OPEN_NOTIFICATION_ACCESS,

    /** One more `requestRebind`. A request, never a guarantee. */
    RECONNECT,

    /** CHAN's own notification settings, when warnings are blocked. */
    OPEN_WARNING_SETTINGS,
}

data class ProtectionActionButton(
    val action: ProtectionAction,
    val emphasis: ActionEmphasis,
    @StringRes val labelRes: Int,
    val enabled: Boolean = true,
)

enum class ActionEmphasis { PRIMARY, SECONDARY }

/** The headline card's whole content for one computed state. */
data class ProtectionRecoveryUi(
    @StringRes val headlineRes: Int,
    /** Rules out the causes a user would otherwise assume. */
    @StringRes val reassuranceRes: Int? = null,
    /** What to actually do, in words, above the buttons. */
    @StringRes val instructionRes: Int? = null,
    val buttons: List<ProtectionActionButton> = emptyList(),
    /** True only when a live listener has been confirmed. */
    val presentsAsActive: Boolean = false,
) {
    fun has(action: ProtectionAction): Boolean = buttons.any { it.action == action }

    fun button(action: ProtectionAction): ProtectionActionButton? =
        buttons.firstOrNull { it.action == action }
}

/**
 * What the protection headline says and offers, state by state.
 *
 * The disconnected copy is the reason this exists. On the Xiaomi handset the
 * observed state is: CHAN's process alive, scanning on, Notification Access
 * granted, and CHAN absent from Android's live listener list for minutes at a
 * time, with `requestRebind` ignored. "Bảo vệ Zalo đang mất kết nối" described
 * that as if something had dropped out — which sends a worried person to check
 * their wifi or their Zalo login, neither of which is involved.
 *
 * So the disconnected state names the actor (Android), rules out the two wrong
 * suspicions, and leads with the only remedy that reliably works: toggling the
 * grant off and on again in Notification Access. "Kết nối lại" stays, one step
 * down, because it costs nothing when it does work.
 */
object ProtectionRecoveryPolicy {

    fun forHealth(health: ProtectionHealth): ProtectionRecoveryUi = when (health) {
        ProtectionHealth.OFF -> ProtectionRecoveryUi(
            headlineRes = R.string.protection_state_off,
        )

        ProtectionHealth.ACCESS_REQUIRED -> ProtectionRecoveryUi(
            headlineRes = R.string.protection_state_access_required,
            buttons = listOf(
                ProtectionActionButton(
                    ProtectionAction.OPEN_NOTIFICATION_ACCESS,
                    ActionEmphasis.PRIMARY,
                    R.string.protection_open_access_settings,
                ),
            ),
        )

        ProtectionHealth.CONNECTING -> ProtectionRecoveryUi(
            headlineRes = R.string.protection_state_connecting,
        )

        // The user asked; the request is outstanding. The control stays in
        // place but cannot be tapped again — a second request changes nothing.
        ProtectionHealth.RECONNECTING -> ProtectionRecoveryUi(
            headlineRes = R.string.protection_state_reconnecting,
            buttons = listOf(
                ProtectionActionButton(
                    ProtectionAction.RECONNECT,
                    ActionEmphasis.SECONDARY,
                    R.string.protection_reconnect,
                    enabled = false,
                ),
            ),
        )

        ProtectionHealth.DISCONNECTED -> ProtectionRecoveryUi(
            headlineRes = R.string.protection_state_not_connected,
            reassuranceRes = R.string.protection_not_connected_not_network,
            instructionRes = R.string.protection_not_connected_instruction,
            buttons = listOf(
                // The toggle is the remedy, so it leads.
                ProtectionActionButton(
                    ProtectionAction.OPEN_NOTIFICATION_ACCESS,
                    ActionEmphasis.PRIMARY,
                    R.string.protection_open_access_settings,
                ),
                ProtectionActionButton(
                    ProtectionAction.RECONNECT,
                    ActionEmphasis.SECONDARY,
                    R.string.protection_reconnect,
                ),
            ),
        )

        ProtectionHealth.ACTIVE_WITHOUT_WARNINGS -> ProtectionRecoveryUi(
            headlineRes = R.string.protection_state_active_no_warning,
            buttons = listOf(
                ProtectionActionButton(
                    ProtectionAction.OPEN_WARNING_SETTINGS,
                    ActionEmphasis.SECONDARY,
                    R.string.action_open_settings,
                ),
            ),
        )

        ProtectionHealth.ACTIVE -> ProtectionRecoveryUi(
            headlineRes = R.string.protection_state_active,
            presentsAsActive = true,
        )
    }
}
