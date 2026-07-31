package com.chan.app.ui.screens

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CloudOff
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.chan.app.R
import com.chan.app.domain.FailureReason
import com.chan.app.domain.LookupResult
import com.chan.app.domain.Risk
import com.chan.app.ui.UserSafeMessages
import com.chan.app.ui.components.ChanCard
import com.chan.app.ui.components.PrimaryCta
import com.chan.app.ui.components.RiskPill
import com.chan.app.ui.components.SecondaryButton
import com.chan.app.ui.components.screenContentPadding
import com.chan.app.ui.theme.ChanTheme

/**
 * The outcome of a k-anonymity lookup.
 *
 * "No report" is rendered as its own neutral state with the disclaimer intact —
 * never as a green all-clear. Nobody having reported an account yet says
 * nothing about whether it is a scam.
 */
@Composable
fun LookupResultScreen(
    result: LookupResult?,
    failure: FailureReason?,
    onRetry: () -> Unit,
    onLookupDifferent: () -> Unit,
) {
    val colors = ChanTheme.colors
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(screenContentPadding()),
    ) {
        if (failure != null) {
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
            PrimaryCta(text = stringResource(R.string.action_retry), onClick = onRetry)
            Spacer(Modifier.height(12.dp))
            SecondaryButton(
                text = stringResource(R.string.caution_lookup_different),
                onClick = onLookupDifferent,
            )
            return@Column
        }

        if (result == null) return@Column

        val matched = result.matched
        RiskPill(
            risk = result.risk,
            text = stringResource(
                if (matched) R.string.pill_caution else R.string.pill_unknown,
            ),
            icon = if (matched) Icons.Filled.Warning else Icons.Filled.Info,
        )
        Spacer(Modifier.height(16.dp))
        Text(
            text = stringResource(
                if (matched) R.string.caution_title else R.string.lookup_no_match_title,
            ),
            style = ChanTheme.type.riskHero,
            color = if (matched) colors.warningStrong else colors.strongHeading,
        )
        Spacer(Modifier.height(16.dp))

        ChanCard(
            borderColor = if (matched) colors.warningBorder else colors.border,
            backgroundColor = if (matched) colors.warningSurface else colors.infoTint,
        ) {
            Text(
                text = stringResource(
                    if (matched) R.string.caution_instruction else R.string.lookup_no_match_instruction,
                ),
                style = ChanTheme.type.cardTitle,
                color = if (matched) colors.warningStrong else colors.secondaryHeading,
            )
        }
        Spacer(Modifier.height(12.dp))

        if (matched) {
            ChanCard {
                Text(
                    text = stringResource(R.string.caution_stat_reports, result.reportCount),
                    style = ChanTheme.type.cardTitle,
                    color = colors.secondaryHeading,
                )
                Spacer(Modifier.height(6.dp))
                Text(
                    text = result.lastReportedDaysAgo
                        ?.let { stringResource(R.string.caution_stat_recent, it) }
                        ?: stringResource(R.string.caution_stat_recent_unknown),
                    style = ChanTheme.type.body,
                    color = colors.bodyText,
                )
            }
            Spacer(Modifier.height(12.dp))
        } else {
            // The server's own wording for "nothing reported". It never says safe.
            ChanCard {
                Text(text = result.noMatchMessage, style = ChanTheme.type.body, color = colors.bodyText)
            }
            Spacer(Modifier.height(12.dp))
        }

        ChanCard(borderColor = colors.border, backgroundColor = colors.infoTint) {
            Text(
                text = stringResource(R.string.caution_recommendation_heading),
                style = ChanTheme.type.cardTitle,
                color = colors.secondaryHeading,
            )
            Spacer(Modifier.height(8.dp))
            Text(
                text = stringResource(R.string.caution_recommendation_body),
                style = ChanTheme.type.body,
                color = colors.bodyText,
            )
        }
        Spacer(Modifier.height(12.dp))

        // Required disclaimer, verbatim, on both the match and no-match paths.
        ChanCard {
            Text(
                text = stringResource(R.string.lookup_caution_disclaimer),
                style = ChanTheme.type.body,
                color = colors.bodyText,
            )
        }
        Spacer(Modifier.height(20.dp))

        SecondaryButton(
            text = stringResource(R.string.caution_lookup_different),
            onClick = onLookupDifferent,
        )
    }
}
