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
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.RadioButtonUnchecked
import androidx.compose.material.icons.filled.Rule
import androidx.compose.material.icons.filled.Shield
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
import androidx.compose.ui.unit.dp
import com.chan.app.R
import com.chan.app.ui.SystemStatus
import com.chan.app.ui.components.ChanCard
import com.chan.app.ui.components.Eyebrow
import com.chan.app.ui.components.PrimaryCta
import com.chan.app.ui.components.SecondaryButton
import com.chan.app.ui.components.screenContentPadding
import com.chan.app.ui.theme.ChanTheme

/**
 * What is protecting the user right now, layer by layer (§B2, UI changes).
 *
 * Each card reports one Android layer, read from the platform every time the
 * app comes forward — opening the settings screen is not treated as consent,
 * only the system's own answer is.
 *
 * Green on these cards means "this layer is switched on". It is never used to
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
    onStopSharing: () -> Unit,
) {
    val colors = ChanTheme.colors
    var showConfirm by remember { mutableStateOf(false) }

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

        // 2. Android's Notification Access grant plus the in-app switch.
        LayerCard(
            icon = Icons.Filled.Shield,
            title = stringResource(R.string.protection_layer_zalo_title),
            status = stringResource(zaloStatusRes(status)),
            active = status.scanningActive,
        )
        Spacer(Modifier.height(10.dp))

        // 3. Whether CHAN may show the warning it would produce.
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
                        text = stringResource(zaloStatusRes(status)),
                        style = ChanTheme.type.caption,
                        color = if (status.scanningActive) colors.successStrong else colors.mutedText,
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
 * The four states the Zalo layer can be in. "Đã tắt trong cài đặt máy" is the
 * one that matters most: the user turned CHAN on and Android turned it off.
 */
private fun zaloStatusRes(status: SystemStatus): Int = when {
    status.scanningActive -> R.string.protection_zalo_status_on
    status.zaloScanningEnabled && !status.notificationAccessGranted ->
        R.string.protection_zalo_status_system_off
    status.notificationAccessGranted && !status.zaloScanningEnabled ->
        R.string.protection_zalo_status_paused
    else -> R.string.protection_zalo_status_off
}

@Composable
private fun LayerCard(icon: ImageVector, title: String, status: String, active: Boolean) {
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
                if (active) Icons.Filled.CheckCircle else Icons.Filled.RadioButtonUnchecked,
                contentDescription = null,
                tint = if (active) colors.success else colors.disabled,
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
