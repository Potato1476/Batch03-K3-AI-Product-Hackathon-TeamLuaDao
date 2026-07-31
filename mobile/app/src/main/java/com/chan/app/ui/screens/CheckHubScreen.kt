package com.chan.app.ui.screens

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.chan.app.R
import com.chan.app.ui.components.PrimaryCta
import com.chan.app.ui.components.SecondaryButton
import com.chan.app.ui.components.screenContentPadding
import com.chan.app.ui.theme.ChanTheme

@Composable
fun CheckHubScreen(
    onOpenMessage: () -> Unit,
    onOpenLookup: () -> Unit,
) {
    val colors = ChanTheme.colors
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(screenContentPadding()),
    ) {
        Text(
            text = stringResource(R.string.check_hub_title),
            style = ChanTheme.type.pageTitle,
            color = colors.strongHeading,
        )
        Spacer(Modifier.height(8.dp))
        Text(
            text = stringResource(R.string.check_hub_subtitle),
            style = ChanTheme.type.body,
            color = colors.bodyText,
        )
        Spacer(Modifier.height(24.dp))

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
    }
}
