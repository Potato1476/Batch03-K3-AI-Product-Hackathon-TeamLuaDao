package com.chan.app.ui.screens

import android.content.Intent
import android.net.Uri
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
import androidx.compose.material.icons.filled.Call
import androidx.compose.material.icons.filled.CloudOff
import androidx.compose.material.icons.filled.Error
import androidx.compose.material.icons.filled.HelpOutline
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.PhoneInTalk
import androidx.compose.material.icons.filled.RadioButtonUnchecked
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.unit.dp
import com.chan.app.R
import com.chan.app.domain.AnalysisResult
import com.chan.app.domain.FailureReason
import com.chan.app.domain.Risk
import com.chan.app.ui.SignalCatalog
import com.chan.app.ui.SignalRowState
import com.chan.app.ui.UserSafeMessages
import com.chan.app.ui.components.ChanCard
import com.chan.app.ui.components.Eyebrow
import com.chan.app.ui.components.PrimaryCta
import com.chan.app.ui.components.RiskPill
import com.chan.app.ui.components.SecondaryButton
import com.chan.app.ui.components.screenContentPadding
import com.chan.app.ui.theme.ChanTheme

/**
 * Renders one live analysis, at whatever risk the backend (or the on-device
 * rule layer) returned, preserving Sprint 01's visual contract.
 *
 * `UNKNOWN` deliberately gets the neutral palette and never green: "chưa phát
 * hiện dấu hiệu" is a statement about what was found, not a verdict of safety
 * (invariant I6).
 */
@Composable
fun AnalysisResultScreen(
    result: AnalysisResult?,
    failure: FailureReason?,
    fromNotification: Boolean,
    onRetry: () -> Unit,
    onCheckAnother: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(screenContentPadding()),
    ) {
        when {
            failure != null -> FailureBody(failure, onRetry, onCheckAnother)
            result != null -> ResultBody(result, fromNotification, onCheckAnother)
        }
    }
}

@Composable
private fun ResultBody(result: AnalysisResult, fromNotification: Boolean, onCheckAnother: () -> Unit) {
    val colors = ChanTheme.colors
    val context = LocalContext.current
    val palette = paletteFor(result.risk)
    val rows = SignalCatalog.rowsFor(result)

    RiskPill(
        risk = result.risk,
        text = stringResource(UserSafeMessages.riskPill(result.risk)),
        icon = when (result.risk) {
            Risk.HIGH -> Icons.Filled.Error
            Risk.MEDIUM -> Icons.Filled.Warning
            Risk.UNKNOWN -> Icons.Filled.Info
        },
    )
    Spacer(Modifier.height(16.dp))
    Text(
        text = stringResource(UserSafeMessages.riskTitle(result.risk)),
        style = ChanTheme.type.riskHero,
        color = palette.heading,
    )
    Spacer(Modifier.height(16.dp))

    // First, most important instruction.
    ChanCard(borderColor = palette.border, backgroundColor = palette.surface) {
        Text(
            text = stringResource(UserSafeMessages.riskInstruction(result.risk)),
            style = ChanTheme.type.cardTitle,
            color = palette.heading,
        )
    }
    Spacer(Modifier.height(12.dp))

    // A shortened notification is called out: the verdict was formed on less
    // than the whole message.
    if (result.truncated) {
        ChanCard(borderColor = colors.warningBorder, backgroundColor = colors.warningSurface) {
            Text(
                text = stringResource(R.string.result_truncated_note),
                style = ChanTheme.type.body,
                color = colors.warningStrong,
            )
        }
        Spacer(Modifier.height(12.dp))
    }

    ChanCard {
        Eyebrow(text = stringResource(R.string.result_source_eyebrow))
        Spacer(Modifier.height(4.dp))
        Text(
            text = stringResource(
                if (fromNotification) R.string.result_source_notification else R.string.result_source_manual,
            ),
            style = ChanTheme.type.body,
            color = colors.bodyText,
        )
        if (result.decidedOnDevice) {
            Spacer(Modifier.height(6.dp))
            Text(
                text = stringResource(R.string.result_on_device_note),
                style = ChanTheme.type.caption,
                color = colors.mutedText,
            )
        }
    }

    if (result.explanation.isNotBlank()) {
        Spacer(Modifier.height(12.dp))
        ChanCard {
            Text(
                text = stringResource(R.string.result_explanation_heading),
                style = ChanTheme.type.cardTitle,
                color = colors.secondaryHeading,
            )
            Spacer(Modifier.height(8.dp))
            Text(text = result.explanation, style = ChanTheme.type.body, color = colors.bodyText)
        }
    }

    Spacer(Modifier.height(22.dp))
    Text(
        text = stringResource(
            R.string.result_signals_heading,
            rows.count { it.hit },
            rows.size,
        ),
        style = ChanTheme.type.sectionTitle,
        color = colors.strongHeading,
    )
    Spacer(Modifier.height(12.dp))

    rows.forEach { row ->
        SignalRow(row)
        Spacer(Modifier.height(10.dp))
    }

    if (result.questions.isNotEmpty()) {
        Spacer(Modifier.height(12.dp))
        ChanCard(borderColor = colors.border, backgroundColor = colors.infoTint) {
            Text(
                text = stringResource(R.string.result_questions_heading),
                style = ChanTheme.type.cardTitle,
                color = colors.secondaryHeading,
            )
            result.questions.forEach { question ->
                Spacer(Modifier.height(8.dp))
                Text(text = question, style = ChanTheme.type.body, color = colors.bodyText)
            }
        }
    }

    Spacer(Modifier.height(12.dp))
    ChanCard(borderColor = colors.border, backgroundColor = colors.infoTint) {
        Text(
            text = stringResource(R.string.result_recommendation_heading),
            style = ChanTheme.type.cardTitle,
            color = colors.secondaryHeading,
        )
        Spacer(Modifier.height(8.dp))
        Text(
            text = stringResource(R.string.result_recommendation_body),
            style = ChanTheme.type.body,
            color = colors.bodyText,
        )
    }

    // A number the user dials themselves is the antidote to a spoofed caller.
    result.verifiedHotline?.let { hotline ->
        Spacer(Modifier.height(12.dp))
        ChanCard(borderColor = colors.border) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(min = 56.dp)
                    .clickable(role = Role.Button) {
                        runCatching {
                            context.startActivity(Intent(Intent.ACTION_DIAL, Uri.parse("tel:${hotline.number}")))
                        }
                    },
            ) {
                Icon(Icons.Filled.PhoneInTalk, contentDescription = null, tint = colors.brand, modifier = Modifier.size(28.dp))
                Spacer(Modifier.width(12.dp))
                Column(Modifier.weight(1f)) {
                    Text(text = hotline.name, style = ChanTheme.type.bodyStrong, color = colors.secondaryHeading)
                    Text(
                        text = stringResource(R.string.result_hotline_verified, hotline.number),
                        style = ChanTheme.type.caption,
                        color = colors.mutedText,
                    )
                }
            }
        }
    }

    Spacer(Modifier.height(12.dp))
    ChanCard(borderColor = colors.border) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 56.dp)
                .clickable(role = Role.Button) {
                    runCatching {
                        context.startActivity(Intent(Intent.ACTION_DIAL, Uri.parse("tel:156")))
                    }
                },
        ) {
            Icon(Icons.Filled.Call, contentDescription = null, tint = colors.brand, modifier = Modifier.size(28.dp))
            Spacer(Modifier.width(12.dp))
            Column(Modifier.weight(1f)) {
                Text(
                    text = stringResource(R.string.result_hotline_title),
                    style = ChanTheme.type.bodyStrong,
                    color = colors.secondaryHeading,
                )
                Text(
                    text = stringResource(R.string.result_hotline_subtitle),
                    style = ChanTheme.type.caption,
                    color = colors.mutedText,
                )
            }
            Text(text = "156", style = ChanTheme.type.sectionTitle.copy(color = colors.brand))
        }
    }
    Spacer(Modifier.height(20.dp))

    SecondaryButton(
        text = stringResource(R.string.result_check_another),
        onClick = onCheckAnother,
    )
}

@Composable
private fun FailureBody(failure: FailureReason, onRetry: () -> Unit, onCheckAnother: () -> Unit) {
    val colors = ChanTheme.colors
    Row(verticalAlignment = Alignment.CenterVertically) {
        Icon(Icons.Filled.CloudOff, contentDescription = null, tint = colors.warning, modifier = Modifier.size(32.dp))
        Spacer(Modifier.width(12.dp))
        Text(
            text = stringResource(R.string.error_heading),
            style = ChanTheme.type.sectionTitle,
            color = colors.strongHeading,
        )
    }
    Spacer(Modifier.height(16.dp))
    ChanCard(borderColor = colors.warningBorder, backgroundColor = colors.warningSurface) {
        Text(
            text = stringResource(UserSafeMessages.forFailure(failure)),
            style = ChanTheme.type.body,
            color = colors.warningStrong,
        )
    }
    Spacer(Modifier.height(20.dp))
    // A retry is always the user's decision: analysis is not idempotent.
    PrimaryCta(text = stringResource(R.string.action_retry), onClick = onRetry)
    Spacer(Modifier.height(12.dp))
    SecondaryButton(text = stringResource(R.string.result_check_another), onClick = onCheckAnother)
}

@Composable
private fun SignalRow(row: SignalRowState) {
    val colors = ChanTheme.colors
    val borderColor = if (row.hit) colors.dangerBorder else colors.border
    ChanCard(borderColor = borderColor) {
        Row(verticalAlignment = Alignment.Top) {
            // Never rely on color alone: hit vs miss also differ by icon + text.
            if (row.hit) {
                Icon(Icons.Filled.Error, contentDescription = null, tint = colors.danger, modifier = Modifier.size(26.dp))
            } else {
                Icon(Icons.Filled.RadioButtonUnchecked, contentDescription = null, tint = colors.disabled, modifier = Modifier.size(26.dp))
            }
            Spacer(Modifier.width(12.dp))
            Column(Modifier.weight(1f)) {
                Text(
                    text = stringResource(row.labelRes),
                    style = ChanTheme.type.bodyStrong,
                    color = if (row.hit) colors.dangerStrong else colors.bodyText,
                )
                // A code this build has no label for still reads as a real row.
                row.fallbackLabel?.let { code ->
                    Spacer(Modifier.height(2.dp))
                    Text(text = code, style = ChanTheme.type.caption, color = colors.mutedText)
                }
                Spacer(Modifier.height(2.dp))
                Text(
                    text = stringResource(
                        if (row.hit) R.string.signal_state_hit else R.string.signal_state_miss,
                    ),
                    style = ChanTheme.type.caption,
                    color = if (row.hit) colors.danger else colors.mutedText,
                )
                // Evidence arrives already redacted by the backend and is shown
                // exactly as received: placeholders are never "restored".
                row.evidence?.let { evidence ->
                    Spacer(Modifier.height(8.dp))
                    Text(
                        text = evidence,
                        style = ChanTheme.type.body,
                        color = colors.bodyText,
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
            }
        }
    }
}

private data class RiskPalette(val heading: Color, val surface: Color, val border: Color)

@Composable
private fun paletteFor(risk: Risk): RiskPalette {
    val colors = ChanTheme.colors
    return when (risk) {
        Risk.HIGH -> RiskPalette(colors.dangerStrong, colors.dangerSurface, colors.dangerBorder)
        Risk.MEDIUM -> RiskPalette(colors.warningStrong, colors.warningSurface, colors.warningBorder)
        // Neutral, never the success palette.
        Risk.UNKNOWN -> RiskPalette(colors.strongHeading, colors.infoTint, colors.border)
    }
}
