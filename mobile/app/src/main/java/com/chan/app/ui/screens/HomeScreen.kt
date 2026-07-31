package com.chan.app.ui.screens

import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
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
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Shield
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.chan.app.R
import com.chan.app.notification.ProtectionHealth
import com.chan.app.ui.components.ChanCard
import com.chan.app.ui.components.Eyebrow
import com.chan.app.ui.components.PrimaryCta
import com.chan.app.ui.components.ProtectionStatusRow
import com.chan.app.ui.components.SecondaryButton
import com.chan.app.ui.components.screenContentPadding
import com.chan.app.ui.theme.ChanTheme

@Composable
fun HomeScreen(
    protectionHealth: ProtectionHealth,
    onOpenMessage: () -> Unit,
    onOpenLookup: () -> Unit,
    onOpenProtection: () -> Unit,
) {
    val colors = ChanTheme.colors
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(screenContentPadding()),
    ) {
        Image(
            painter = painterResource(R.drawable.chan_logo_horizontal),
            contentDescription = stringResource(R.string.app_name),
            modifier = Modifier.size(width = 144.dp, height = 48.dp),
        )
        Spacer(Modifier.height(12.dp))

        Text(
            text = stringResource(R.string.home_greeting),
            style = ChanTheme.type.sectionTitle,
            color = colors.strongHeading,
        )
        Spacer(Modifier.height(20.dp))

        // The live protection state, understandable without opening settings
        // (§B5). Green here means "the listener is connected", never that a
        // message is safe.
        ProtectionStatusRow(health = protectionHealth, onOpenProtection = onOpenProtection)
        Spacer(Modifier.height(22.dp))

        PrimaryCta(
            text = stringResource(R.string.home_action_suspicious_message),
            onClick = onOpenMessage,
        )
        Spacer(Modifier.height(12.dp))
        SecondaryButton(
            text = stringResource(R.string.home_action_lookup),
            onClick = onOpenLookup,
            leadingIcon = Icons.Filled.Search,
        )
        Spacer(Modifier.height(22.dp))

        // CHAN keeps no history of what was checked, so this slot reports the
        // state of passive Zalo protection instead of a list of past messages.
        Eyebrow(text = stringResource(R.string.home_recent_heading))
        Spacer(Modifier.height(10.dp))
        ChanCard(
            borderColor = if (protectionHealth.listenerLive) colors.border else colors.warningBorder,
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    if (protectionHealth.listenerLive) Icons.Filled.Shield else Icons.Filled.Warning,
                    contentDescription = null,
                    tint = if (protectionHealth.listenerLive) colors.success else colors.warning,
                    modifier = Modifier.size(28.dp),
                )
                Spacer(Modifier.width(12.dp))
                Column(Modifier.weight(1f)) {
                    Text(
                        text = stringResource(
                            if (protectionHealth.listenerLive) {
                                R.string.home_zalo_on_title
                            } else {
                                R.string.home_zalo_off_title
                            },
                        ),
                        style = ChanTheme.type.cardTitle,
                        color = colors.secondaryHeading,
                    )
                    Spacer(Modifier.height(4.dp))
                    Text(
                        text = stringResource(
                            if (protectionHealth.listenerLive) {
                                R.string.home_zalo_on_desc
                            } else {
                                R.string.home_zalo_off_desc
                            },
                        ),
                        style = ChanTheme.type.caption,
                        color = colors.mutedText,
                    )
                }
            }
            Spacer(Modifier.height(12.dp))
            SecondaryButton(
                text = stringResource(R.string.home_open_protection),
                onClick = onOpenProtection,
            )
        }
        Spacer(Modifier.height(16.dp))

        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Start) {
            Text(
                text = stringResource(R.string.home_not_stored_note),
                style = ChanTheme.type.caption,
                color = colors.mutedText,
            )
        }
    }
}


