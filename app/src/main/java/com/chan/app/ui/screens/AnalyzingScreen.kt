package com.chan.app.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Shield
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.chan.app.R
import com.chan.app.ui.components.rememberReducedMotion
import com.chan.app.ui.theme.ChanTheme

@Composable
fun AnalyzingScreen() {
    val colors = ChanTheme.colors
    val reducedMotion = rememberReducedMotion()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        if (reducedMotion) {
            // No infinite animation when the system requests reduced motion.
            Icon(
                Icons.Filled.Shield,
                contentDescription = null,
                tint = colors.brand,
                modifier = Modifier.size(56.dp),
            )
        } else {
            CircularProgressIndicator(
                color = colors.brand,
                strokeWidth = 5.dp,
                modifier = Modifier.size(56.dp),
            )
        }
        Spacer(Modifier.height(24.dp))
        Text(
            text = stringResource(R.string.loading_title),
            style = ChanTheme.type.sectionTitle,
            color = colors.strongHeading,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(10.dp))
        Text(
            text = stringResource(R.string.loading_subtitle),
            style = ChanTheme.type.body,
            color = colors.bodyText,
            textAlign = TextAlign.Center,
        )
    }
}
