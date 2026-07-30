package com.chan.app.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Shield
import androidx.compose.material3.Icon
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.unit.dp
import com.chan.app.R
import com.chan.app.ui.SystemStatus
import com.chan.app.ui.components.ChanCard
import com.chan.app.ui.components.Eyebrow
import com.chan.app.ui.components.PrivacyBox
import com.chan.app.ui.components.screenContentPadding
import com.chan.app.ui.theme.ChanTheme

/**
 * Settings, with the three permissions that matter shown as live state.
 *
 * Every row opens the right destination — Android's Notification Access list,
 * CHAN's notification settings, or the app details page for the microphone.
 * None of them is requested at first launch.
 */
@Composable
fun SettingsScreen(
    darkMode: Boolean,
    status: SystemStatus,
    onDarkModeChange: (Boolean) -> Unit,
    onOpenNotificationAccessSettings: () -> Unit,
    onOpenWarningSettings: () -> Unit,
    onOpenMicrophoneSettings: () -> Unit,
) {
    val colors = ChanTheme.colors
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(screenContentPadding()),
    ) {
        Text(
            text = stringResource(R.string.settings_title),
            style = ChanTheme.type.pageTitle,
            color = colors.strongHeading,
        )
        Spacer(Modifier.height(16.dp))

        ChanCard {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text(
                        text = stringResource(R.string.settings_dark_mode),
                        style = ChanTheme.type.cardTitle,
                        color = colors.secondaryHeading,
                    )
                    Spacer(Modifier.height(4.dp))
                    Text(
                        text = stringResource(R.string.settings_dark_mode_desc),
                        style = ChanTheme.type.caption,
                        color = colors.mutedText,
                    )
                }
                Spacer(Modifier.width(12.dp))
                Switch(checked = darkMode, onCheckedChange = onDarkModeChange)
            }
        }
        Spacer(Modifier.height(22.dp))

        Eyebrow(text = stringResource(R.string.settings_permissions_heading))
        Spacer(Modifier.height(10.dp))
        ChanCard {
            PermissionRow(
                icon = Icons.Filled.Shield,
                title = stringResource(R.string.settings_perm_notification_access),
                granted = status.notificationAccessGranted,
                onClick = onOpenNotificationAccessSettings,
            )
            Spacer(Modifier.height(12.dp))
            PermissionRow(
                icon = Icons.Filled.Notifications,
                title = stringResource(R.string.settings_perm_warnings),
                granted = status.warningsAllowed,
                onClick = onOpenWarningSettings,
            )
            Spacer(Modifier.height(12.dp))
            PermissionRow(
                icon = Icons.Filled.Mic,
                title = stringResource(R.string.settings_perm_mic),
                granted = status.microphoneGranted,
                onClick = onOpenMicrophoneSettings,
            )
        }
        Spacer(Modifier.height(10.dp))
        Text(
            text = stringResource(R.string.settings_no_permission_at_launch),
            style = ChanTheme.type.caption,
            color = colors.mutedText,
        )
        Spacer(Modifier.height(22.dp))

        PrivacyBox(text = stringResource(R.string.settings_privacy_box), icon = Icons.Filled.Lock)
    }
}

@Composable
private fun PermissionRow(icon: ImageVector, title: String, granted: Boolean, onClick: () -> Unit) {
    val colors = ChanTheme.colors
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 48.dp)
            .clickable(role = Role.Button, onClick = onClick),
    ) {
        Icon(
            icon,
            contentDescription = null,
            tint = if (granted) colors.success else colors.mutedText,
            modifier = Modifier.size(26.dp),
        )
        Spacer(Modifier.width(12.dp))
        Text(text = title, style = ChanTheme.type.body, color = colors.bodyText, modifier = Modifier.weight(1f))
        Text(
            text = stringResource(
                if (granted) R.string.settings_perm_granted else R.string.settings_perm_not_granted,
            ),
            style = ChanTheme.type.caption,
            color = if (granted) colors.successStrong else colors.mutedText,
        )
        Spacer(Modifier.width(8.dp))
        Text(
            text = stringResource(R.string.settings_perm_open),
            style = ChanTheme.type.caption.copy(color = colors.brand),
        )
    }
}
