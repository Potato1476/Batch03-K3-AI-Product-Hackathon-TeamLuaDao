package com.chan.app.ui.components

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.HourglassEmpty
import androidx.compose.material.icons.filled.PauseCircle
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import com.chan.app.R
import com.chan.app.notification.ProtectionHealth
import com.chan.app.ui.UserSafeMessages
import com.chan.app.ui.theme.ChanTheme

/**
 * The compact protection state on Home (§B5).
 *
 * Understandable without opening settings, and never carried by colour alone:
 * every state has its own icon, its own sentence, and a spoken description.
 * Tapping it opens the detailed screen, where the individual layers are shown
 * separately.
 */
@Composable
fun ProtectionStatusRow(
    health: ProtectionHealth,
    onOpenProtection: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = ChanTheme.colors
    val label = stringResource(UserSafeMessages.protectionHomeLabel(health))
    val detail = stringResource(protectionDetailRes(health))
    val spoken = "$label. $detail"

    val icon: ImageVector
    val tint: Color
    val background: Color
    when (health) {
        ProtectionHealth.ACTIVE -> {
            icon = Icons.Filled.CheckCircle
            tint = colors.success
            background = colors.successSurface
        }
        ProtectionHealth.CONNECTING, ProtectionHealth.RECONNECTING -> {
            icon = Icons.Filled.HourglassEmpty
            tint = colors.brand
            background = colors.infoTint
        }
        ProtectionHealth.ACCESS_REQUIRED,
        ProtectionHealth.DISCONNECTED,
        ProtectionHealth.ACTIVE_WITHOUT_WARNINGS,
        -> {
            icon = Icons.Filled.Warning
            tint = colors.warning
            background = colors.warningSurface
        }
        ProtectionHealth.OFF -> {
            icon = Icons.Filled.PauseCircle
            tint = colors.mutedText
            background = colors.card
        }
    }

    ChanCard(
        modifier = modifier
            .heightIn(min = 56.dp)
            .semantics { contentDescription = spoken }
            .clickable(role = Role.Button, onClick = onOpenProtection),
        borderColor = if (health == ProtectionHealth.ACTIVE) colors.successSurface else colors.border,
        backgroundColor = background,
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.fillMaxWidth()) {
            Icon(icon, contentDescription = null, tint = tint, modifier = Modifier.size(28.dp))
            Spacer(Modifier.width(12.dp))
            Column(Modifier.weight(1f)) {
                Text(
                    text = label,
                    style = ChanTheme.type.cardTitle,
                    color = if (health == ProtectionHealth.ACTIVE) colors.successStrong else colors.secondaryHeading,
                )
                Spacer(Modifier.height(4.dp))
                Text(text = detail, style = ChanTheme.type.caption, color = colors.mutedText)
            }
        }
    }
}

/** One plain sentence explaining what the state means for the user. */
private fun protectionDetailRes(health: ProtectionHealth): Int = when (health) {
    ProtectionHealth.OFF -> R.string.home_protection_off_desc
    ProtectionHealth.ACCESS_REQUIRED -> R.string.home_protection_access_desc
    ProtectionHealth.CONNECTING -> R.string.home_protection_connecting_desc
    ProtectionHealth.RECONNECTING -> R.string.home_protection_reconnecting_desc
    ProtectionHealth.DISCONNECTED -> R.string.home_protection_disconnected_desc
    ProtectionHealth.ACTIVE_WITHOUT_WARNINGS -> R.string.home_protection_no_warning_desc
    ProtectionHealth.ACTIVE -> R.string.home_protection_active_desc
}
