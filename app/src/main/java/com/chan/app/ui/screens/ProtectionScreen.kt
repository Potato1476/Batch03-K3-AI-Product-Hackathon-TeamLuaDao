package com.chan.app.ui.screens

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.HourglassEmpty
import androidx.compose.material.icons.filled.Link
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.RadioButtonUnchecked
import androidx.compose.material.icons.filled.Rule
import androidx.compose.material.icons.filled.Shield
import androidx.compose.material.icons.filled.Tune
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Icon
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import com.chan.app.R
import com.chan.app.notification.ProtectionHealth
import com.chan.app.ui.ActionEmphasis
import com.chan.app.ui.ProtectionAction
import com.chan.app.ui.ProtectionRecoveryPolicy
import com.chan.app.ui.SystemStatus
import com.chan.app.ui.TimeOfDay
import com.chan.app.ui.UserSafeMessages
import com.chan.app.ui.components.ChanCard
import com.chan.app.ui.components.Eyebrow
import com.chan.app.ui.components.PrimaryCta
import com.chan.app.ui.components.SecondaryButton
import com.chan.app.ui.components.screenContentPadding
import com.chan.app.ui.theme.ChanTheme

/**
 * What is protecting the user right now, layer by layer (§B5).
 *
 * Sprint 03 splits what Sprint 02 merged. The Notification Access grant and the
 * live listener connection are two rows, not one, because on a real phone they
 * disagreed: the permission was on, the listener was not bound, and every
 * screen still showed green. A single switch must not be able to hide a broken
 * layer underneath it.
 *
 * Green on these rows means "this layer is switched on". It is never used to
 * say a Zalo message is safe.
 */
@Composable
fun ProtectionScreen(
    status: SystemStatus,
    guardianSharingEnabled: Boolean,
    onEnableZaloProtection: () -> Unit,
    onDisableZaloProtection: () -> Unit,
    onOpenNotificationAccessSettings: () -> Unit,
    onOpenWarningSettings: () -> Unit,
    onOpenZaloNotificationSettings: () -> Unit,
    onReconnect: () -> Unit,
    onStopSharing: () -> Unit,
) {
    val colors = ChanTheme.colors
    var showConfirm by remember { mutableStateOf(false) }
    val health = status.protectionHealth

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(screenContentPadding()),
    ) {
        Text(
            text = stringResource(R.string.protection_title),
            style = ChanTheme.type.pageTitle,
            color = colors.strongHeading,
        )
        Spacer(Modifier.height(16.dp))

        // --- The one headline state ---------------------------------------
        HeadlineCard(
            health = health,
            lastConnectedAt = status.lastConnectedAt,
            onReconnect = onReconnect,
            onOpenNotificationAccessSettings = onOpenNotificationAccessSettings,
            onOpenWarningSettings = onOpenWarningSettings,
            canReconnect = status.canRequestReconnect,
        )
        Spacer(Modifier.height(22.dp))

        Eyebrow(text = stringResource(R.string.protection_layers_heading))
        Spacer(Modifier.height(10.dp))

        // 1. The on-device rule layer, which works with or without a network.
        LayerCard(
            icon = Icons.Filled.Rule,
            title = stringResource(R.string.protection_layer_rules_title),
            status = stringResource(
                if (status.rulesFromServer) {
                    R.string.protection_layer_rules_on
                } else {
                    R.string.protection_layer_rules_offline
                },
            ),
            active = true,
        )
        Spacer(Modifier.height(10.dp))

        // 2. The in-app switch. Cleared app data returns this to off.
        LayerCard(
            icon = Icons.Filled.Tune,
            title = stringResource(R.string.protection_layer_preference_title),
            status = stringResource(
                if (status.zaloScanningEnabled) {
                    R.string.protection_layer_preference_on
                } else {
                    R.string.protection_layer_preference_off
                },
            ),
            active = status.zaloScanningEnabled,
        )
        Spacer(Modifier.height(10.dp))

        // 3. Android's Notification Access grant — a setting, not a connection.
        LayerCard(
            icon = Icons.Filled.Shield,
            title = stringResource(R.string.protection_layer_access_title),
            status = stringResource(
                if (status.notificationAccessGranted) {
                    R.string.protection_layer_access_on
                } else {
                    R.string.protection_layer_access_off
                },
            ),
            active = status.notificationAccessGranted,
        )
        Spacer(Modifier.height(10.dp))

        // 4. Whether the listener is bound in this process, right now.
        LayerCard(
            icon = Icons.Filled.Link,
            title = stringResource(R.string.protection_layer_listener_title),
            status = stringResource(listenerStatusRes(health)),
            active = status.listenerConnected,
            pending = health == ProtectionHealth.CONNECTING || health == ProtectionHealth.RECONNECTING,
        )
        Spacer(Modifier.height(10.dp))

        // 5. Whether CHAN may show the warning it would produce.
        LayerCard(
            icon = Icons.Filled.Notifications,
            title = stringResource(R.string.protection_layer_warning_title),
            status = stringResource(
                if (status.warningsAllowed) {
                    R.string.protection_layer_warning_on
                } else {
                    R.string.protection_layer_warning_off
                },
            ),
            active = status.warningsAllowed,
        )
        Spacer(Modifier.height(10.dp))

        Text(
            text = stringResource(R.string.protection_layers_note),
            style = ChanTheme.type.caption,
            color = colors.mutedText,
        )
        Spacer(Modifier.height(22.dp))

        // --- Recent activity: times and nothing else ----------------------
        ActivityCard(status = status)
        Spacer(Modifier.height(22.dp))

        // --- Zalo consent -------------------------------------------------
        ChanCard {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text(
                        text = stringResource(R.string.protection_layer_zalo_title),
                        style = ChanTheme.type.cardTitle,
                        color = colors.secondaryHeading,
                    )
                    Spacer(Modifier.height(4.dp))
                    Text(
                        text = stringResource(UserSafeMessages.protectionHeadline(health)),
                        style = ChanTheme.type.caption,
                        color = if (health == ProtectionHealth.ACTIVE) colors.successStrong else colors.mutedText,
                    )
                }
                Spacer(Modifier.width(12.dp))
                Switch(
                    checked = status.zaloScanningEnabled,
                    onCheckedChange = { enabled ->
                        if (enabled) onEnableZaloProtection() else onDisableZaloProtection()
                    },
                )
            }
            Spacer(Modifier.height(12.dp))
            // Shown before the user ever leaves the app for system settings.
            Text(
                text = stringResource(R.string.protection_zalo_explanation),
                style = ChanTheme.type.body,
                color = colors.bodyText,
            )
            Spacer(Modifier.height(6.dp))
            Text(
                text = stringResource(R.string.protection_zalo_only_note),
                style = ChanTheme.type.caption,
                color = colors.mutedText,
            )
            Spacer(Modifier.height(12.dp))

            if (!status.notificationAccessGranted) {
                PrimaryCta(
                    text = stringResource(R.string.protection_zalo_open_settings),
                    onClick = onOpenNotificationAccessSettings,
                )
            } else {
                SecondaryButton(
                    text = stringResource(R.string.protection_zalo_turn_off),
                    onClick = onDisableZaloProtection,
                )
            }

            // Scanning continues if the user left it on, but CHAN says plainly
            // that it cannot show the warning it would produce.
            if (status.scanningWithoutWarnings) {
                Spacer(Modifier.height(12.dp))
                Text(
                    text = stringResource(R.string.protection_zalo_scanning_no_warning),
                    style = ChanTheme.type.bodyStrong,
                    color = colors.warningStrong,
                )
                Spacer(Modifier.height(8.dp))
                SecondaryButton(
                    text = stringResource(R.string.action_open_settings),
                    onClick = onOpenWarningSettings,
                )
            }
        }
        Spacer(Modifier.height(22.dp))

        // --- What to check when nothing is arriving ------------------------
        ChanCard {
            Text(
                text = stringResource(R.string.protection_no_events_title),
                style = ChanTheme.type.cardTitle,
                color = colors.secondaryHeading,
            )
            Spacer(Modifier.height(8.dp))
            // CHAN cannot read another app's notification settings, so it says
            // what to look at rather than inventing a detected state.
            Text(
                text = stringResource(R.string.protection_no_events_body),
                style = ChanTheme.type.body,
                color = colors.bodyText,
            )
            Spacer(Modifier.height(12.dp))
            SecondaryButton(
                text = stringResource(R.string.protection_open_zalo_settings),
                onClick = onOpenZaloNotificationSettings,
            )
        }
        Spacer(Modifier.height(22.dp))

        Eyebrow(text = stringResource(R.string.protection_commitments_heading))
        Spacer(Modifier.height(10.dp))
        ChanCard {
            Commitment(stringResource(R.string.protection_commit_1))
            Spacer(Modifier.height(10.dp))
            Commitment(stringResource(R.string.protection_commit_2))
            Spacer(Modifier.height(10.dp))
            Commitment(stringResource(R.string.protection_commit_3))
            Spacer(Modifier.height(10.dp))
            Commitment(stringResource(R.string.protection_commit_4))
        }
        Spacer(Modifier.height(22.dp))

        Eyebrow(text = stringResource(R.string.protection_guardian_heading))
        Spacer(Modifier.height(10.dp))
        ChanCard {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Filled.Person, contentDescription = null, tint = colors.brand, modifier = Modifier.size(32.dp))
                Spacer(Modifier.width(12.dp))
                Column(Modifier.weight(1f)) {
                    Text(
                        text = stringResource(R.string.protection_guardian_name),
                        style = ChanTheme.type.cardTitle,
                        color = colors.secondaryHeading,
                    )
                    Text(
                        text = stringResource(R.string.protection_guardian_desc),
                        style = ChanTheme.type.caption,
                        color = colors.mutedText,
                    )
                }
            }
            Spacer(Modifier.height(12.dp))
            if (guardianSharingEnabled) {
                SecondaryButton(
                    text = stringResource(R.string.protection_stop_sharing),
                    onClick = { showConfirm = true },
                )
            } else {
                Text(
                    text = stringResource(R.string.protection_sharing_stopped),
                    style = ChanTheme.type.bodyStrong,
                    color = colors.mutedText,
                )
            }
        }
    }

    if (showConfirm) {
        AlertDialog(
            onDismissRequest = { showConfirm = false },
            title = { Text(stringResource(R.string.protection_stop_confirm_title), style = ChanTheme.type.cardTitle) },
            text = { Text(stringResource(R.string.protection_stop_confirm_body), style = ChanTheme.type.body) },
            confirmButton = {
                TextButton(onClick = {
                    showConfirm = false
                    onStopSharing()
                }) { Text(stringResource(R.string.protection_stop_confirm_ok), style = ChanTheme.type.button.copy(color = colors.danger)) }
            },
            dismissButton = {
                TextButton(onClick = { showConfirm = false }) {
                    Text(stringResource(R.string.action_cancel), style = ChanTheme.type.button.copy(color = colors.brand))
                }
            },
        )
    }
}

/**
 * The state in one sentence, the reason it is not the user's fault, and the
 * action that actually fixes it.
 *
 * All of that comes from [ProtectionRecoveryPolicy], which is unit tested, so
 * the copy cannot drift from the state it describes. Colour is never the only
 * carrier: an icon and a spoken description say the same thing.
 */
@Composable
private fun HeadlineCard(
    health: ProtectionHealth,
    lastConnectedAt: Long?,
    canReconnect: Boolean,
    onReconnect: () -> Unit,
    onOpenNotificationAccessSettings: () -> Unit,
    onOpenWarningSettings: () -> Unit,
) {
    val colors = ChanTheme.colors
    val ui = ProtectionRecoveryPolicy.forHealth(health)
    val headline = stringResource(ui.headlineRes)
    val waiting = health == ProtectionHealth.CONNECTING || health == ProtectionHealth.RECONNECTING

    ChanCard(
        borderColor = if (ui.presentsAsActive) colors.successSurface else colors.border,
        backgroundColor = if (ui.presentsAsActive) colors.successSurface else colors.card,
        modifier = Modifier.semantics { contentDescription = headline },
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(
                when {
                    ui.presentsAsActive -> Icons.Filled.CheckCircle
                    waiting -> Icons.Filled.HourglassEmpty
                    else -> Icons.Filled.RadioButtonUnchecked
                },
                contentDescription = null,
                tint = when {
                    ui.presentsAsActive -> colors.success
                    waiting -> colors.brand
                    else -> colors.mutedText
                },
                modifier = Modifier.size(30.dp),
            )
            Spacer(Modifier.width(12.dp))
            Text(
                text = headline,
                style = ChanTheme.type.cardTitle,
                color = if (ui.presentsAsActive) colors.successStrong else colors.secondaryHeading,
                modifier = Modifier.weight(1f),
            )
        }

        // Rules out what a worried person would otherwise go and check.
        ui.reassuranceRes?.let { res ->
            Spacer(Modifier.height(8.dp))
            Text(
                text = stringResource(res),
                style = ChanTheme.type.body,
                color = colors.bodyText,
            )
        }

        if (lastConnectedAt != null && !ui.presentsAsActive) {
            Spacer(Modifier.height(8.dp))
            // History, clearly marked as history.
            Text(
                text = stringResource(R.string.protection_last_connected, TimeOfDay.format(lastConnectedAt)),
                style = ChanTheme.type.caption,
                color = colors.mutedText,
            )
        }

        // The steps, in words, before the button that opens the screen.
        ui.instructionRes?.let { res ->
            Spacer(Modifier.height(12.dp))
            Text(
                text = stringResource(res),
                style = ChanTheme.type.bodyStrong,
                color = colors.secondaryHeading,
            )
        }

        ui.buttons.forEach { button ->
            // A reconnect offer is pointless when there is nothing to reconnect.
            if (button.action == ProtectionAction.RECONNECT && !canReconnect) return@forEach
            Spacer(Modifier.height(12.dp))
            val label = stringResource(button.labelRes)
            val onClick: () -> Unit = when (button.action) {
                ProtectionAction.OPEN_NOTIFICATION_ACCESS -> onOpenNotificationAccessSettings
                ProtectionAction.RECONNECT -> onReconnect
                ProtectionAction.OPEN_WARNING_SETTINGS -> onOpenWarningSettings
            }
            when (button.emphasis) {
                ActionEmphasis.PRIMARY -> PrimaryCta(
                    text = label,
                    onClick = onClick,
                    enabled = button.enabled,
                )
                // Disabled rather than hidden while an attempt is outstanding:
                // the control keeps its place instead of blinking out.
                ActionEmphasis.SECONDARY -> SecondaryButton(
                    text = label,
                    onClick = onClick,
                    enabled = button.enabled,
                )
            }
        }
    }
}

/**
 * Times and one outcome word (§D3). No sender, message, account, link, or
 * request body can reach this card: the whole input is three timestamps and an
 * enum.
 */
@Composable
private fun ActivityCard(status: SystemStatus) {
    val colors = ChanTheme.colors
    val activity = status.activity

    ChanCard {
        Text(
            text = stringResource(R.string.protection_activity_title),
            style = ChanTheme.type.cardTitle,
            color = colors.secondaryHeading,
        )
        Spacer(Modifier.height(8.dp))
        Text(
            text = activity.lastCallbackAt?.let {
                stringResource(R.string.protection_activity_last, TimeOfDay.format(it))
            } ?: stringResource(R.string.protection_activity_none),
            style = ChanTheme.type.body,
            color = colors.bodyText,
        )
        activity.lastAlertAt?.let {
            Spacer(Modifier.height(4.dp))
            Text(
                text = stringResource(R.string.protection_activity_alert, TimeOfDay.format(it)),
                style = ChanTheme.type.body,
                color = colors.bodyText,
            )
        }
        if (com.chan.app.BuildConfig.DEBUG) {
            activity.lastOutcome?.let { outcome ->
                Spacer(Modifier.height(6.dp))
                // Debug builds only, and still only a category name.
                Text(
                    text = stringResource(R.string.protection_activity_debug_outcome, outcome.name),
                    style = ChanTheme.type.caption,
                    color = colors.mutedText,
                )
            }
        }
    }
}

/** What the listener row says for each computed state. */
private fun listenerStatusRes(health: ProtectionHealth): Int = when (health) {
    ProtectionHealth.ACTIVE, ProtectionHealth.ACTIVE_WITHOUT_WARNINGS ->
        R.string.protection_layer_listener_connected
    ProtectionHealth.CONNECTING -> R.string.protection_layer_listener_connecting
    ProtectionHealth.RECONNECTING -> R.string.protection_layer_listener_reconnecting
    ProtectionHealth.DISCONNECTED -> R.string.protection_layer_listener_not_connected
    else -> R.string.protection_layer_listener_idle
}

@Composable
private fun LayerCard(
    icon: ImageVector,
    title: String,
    status: String,
    active: Boolean,
    pending: Boolean = false,
) {
    val colors = ChanTheme.colors
    ChanCard(
        borderColor = if (active) colors.successSurface else colors.border,
        backgroundColor = if (active) colors.successSurface else colors.card,
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.fillMaxWidth()) {
            Icon(
                icon,
                contentDescription = null,
                tint = if (active) colors.success else colors.mutedText,
                modifier = Modifier.size(28.dp),
            )
            Spacer(Modifier.width(12.dp))
            Column(Modifier.weight(1f)) {
                Text(
                    text = title,
                    style = ChanTheme.type.bodyStrong,
                    color = if (active) colors.successStrong else colors.bodyText,
                )
                Text(text = status, style = ChanTheme.type.caption, color = colors.mutedText)
            }
            // State is never carried by color alone.
            Icon(
                when {
                    active -> Icons.Filled.CheckCircle
                    pending -> Icons.Filled.HourglassEmpty
                    else -> Icons.Filled.RadioButtonUnchecked
                },
                contentDescription = null,
                tint = when {
                    active -> colors.success
                    pending -> colors.brand
                    else -> colors.disabled
                },
                modifier = Modifier.size(24.dp),
            )
        }
    }
}

@Composable
private fun Commitment(text: String) {
    val colors = ChanTheme.colors
    Row(verticalAlignment = Alignment.Top) {
        Icon(Icons.Filled.Check, contentDescription = null, tint = colors.success, modifier = Modifier.size(24.dp))
        Spacer(Modifier.width(12.dp))
        Text(text = text, style = ChanTheme.type.body, color = colors.bodyText, modifier = Modifier.weight(1f))
    }
}
