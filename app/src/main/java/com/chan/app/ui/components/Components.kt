package com.chan.app.ui.components

import android.provider.Settings
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.chan.app.domain.Risk
import com.chan.app.ui.theme.ChanTheme

/**
 * True when the system requests reduced motion (animator duration scale of 0).
 * Used to avoid infinite animation on the loading screen.
 */
@Composable
fun rememberReducedMotion(): Boolean {
    val context = LocalContext.current
    val scale = Settings.Global.getFloat(
        context.contentResolver,
        Settings.Global.ANIMATOR_DURATION_SCALE,
        1f,
    )
    return scale == 0f
}

/** Full-width primary call-to-action. Minimum 64 dp tall, 16 dp corners. */
@Composable
fun PrimaryCta(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    leadingIcon: ImageVector? = null,
) {
    val colors = ChanTheme.colors
    val dimens = ChanTheme.dimens
    val bg = if (enabled) colors.brandFilled else colors.disabledButton
    val fg = if (enabled) colors.onBrandFilled else colors.card
    androidx.compose.material3.Surface(
        onClick = onClick,
        enabled = enabled,
        shape = RoundedCornerShape(dimens.ctaCorner),
        color = bg,
        modifier = modifier
            .fillMaxWidth()
            .heightIn(min = dimens.primaryCtaMinHeight),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 20.dp, vertical = 14.dp),
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            if (leadingIcon != null) {
                Icon(leadingIcon, contentDescription = null, tint = fg, modifier = Modifier.size(24.dp))
                Spacer(Modifier.width(10.dp))
            }
            Text(
                text = text,
                style = ChanTheme.type.button,
                color = fg,
                textAlign = TextAlign.Center,
            )
        }
    }
}

/**
 * Outlined secondary action. Minimum 54 dp tall.
 *
 * [enabled] keeps a button in place while it is temporarily unavailable — a
 * control that vanishes and returns is harder to follow than one that greys out.
 */
@Composable
fun SecondaryButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    leadingIcon: ImageVector? = null,
    enabled: Boolean = true,
) {
    val colors = ChanTheme.colors
    val dimens = ChanTheme.dimens
    val contentColor = if (enabled) colors.brand else colors.disabled
    androidx.compose.material3.Surface(
        onClick = onClick,
        enabled = enabled,
        shape = RoundedCornerShape(dimens.ctaCorner),
        color = colors.card,
        border = BorderStroke(1.5.dp, if (enabled) colors.border else colors.disabled),
        modifier = modifier
            .fillMaxWidth()
            .heightIn(min = dimens.secondaryButtonMinHeight),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 20.dp, vertical = 12.dp),
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            if (leadingIcon != null) {
                Icon(leadingIcon, contentDescription = null, tint = contentColor, modifier = Modifier.size(22.dp))
                Spacer(Modifier.width(10.dp))
            }
            Text(
                text = text,
                style = ChanTheme.type.button.copy(color = contentColor),
                textAlign = TextAlign.Center,
            )
        }
    }
}

/** A generic card surface with default 16 dp corners. */
@Composable
fun ChanCard(
    modifier: Modifier = Modifier,
    borderColor: Color = ChanTheme.colors.border,
    backgroundColor: Color = ChanTheme.colors.card,
    content: @Composable ColumnScope.() -> Unit,
) {
    val dimens = ChanTheme.dimens
    androidx.compose.material3.Surface(
        shape = RoundedCornerShape(dimens.cardCorner),
        color = backgroundColor,
        border = BorderStroke(1.dp, borderColor),
        modifier = modifier.fillMaxWidth(),
    ) {
        Column(modifier = Modifier.padding(dimens.innerPadding), content = content)
    }
}

/**
 * Risk pill. State is never communicated by color alone — always an icon plus
 * text. Colors carry semantic meaning: red = HIGH, amber = MEDIUM/caution.
 */
@Composable
fun RiskPill(risk: Risk, text: String, icon: ImageVector) {
    val colors = ChanTheme.colors
    val (bg, border, fg) = when (risk) {
        Risk.HIGH -> Triple(colors.dangerSurface, colors.dangerBorder, colors.danger)
        Risk.MEDIUM -> Triple(colors.warningSurface, colors.warningBorder, colors.warning)
        Risk.UNKNOWN -> Triple(colors.infoTint, colors.border, colors.bodyText)
    }
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier
            .background(bg, RoundedCornerShape(999.dp))
            .border(1.5.dp, border, RoundedCornerShape(999.dp))
            .heightIn(min = 40.dp)
            .padding(horizontal = 16.dp, vertical = 8.dp),
    ) {
        Icon(icon, contentDescription = null, tint = fg, modifier = Modifier.size(22.dp))
        Spacer(Modifier.width(8.dp))
        Text(text = text, style = ChanTheme.type.cardTitle.copy(color = fg))
    }
}

/** Privacy/information box: info tint background, lock/shield icon plus text. */
@Composable
fun PrivacyBox(text: String, icon: ImageVector, modifier: Modifier = Modifier) {
    val colors = ChanTheme.colors
    Row(
        verticalAlignment = Alignment.Top,
        modifier = modifier
            .fillMaxWidth()
            .background(colors.infoTint, RoundedCornerShape(ChanTheme.dimens.cardCorner))
            .padding(16.dp),
    ) {
        Icon(icon, contentDescription = null, tint = colors.brand, modifier = Modifier.size(24.dp))
        Spacer(Modifier.width(12.dp))
        Text(text = text, style = ChanTheme.type.body, color = colors.bodyText)
    }
}

/** Small uppercase eyebrow label. */
@Composable
fun Eyebrow(text: String, color: Color = ChanTheme.colors.mutedText, modifier: Modifier = Modifier) {
    Text(text = text, style = ChanTheme.type.eyebrow, color = color, modifier = modifier)
}

/** A titled meta row (label + value) used for demo statistics. */
@Composable
fun MetaRow(label: String, value: String) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Text(label, style = ChanTheme.type.caption, color = ChanTheme.colors.mutedText)
        Text(value, style = ChanTheme.type.caption.copy(color = ChanTheme.colors.secondaryHeading))
    }
}

/** Hidden, accessible label helper. */
@Composable
fun ScreenTitle(text: String, modifier: Modifier = Modifier) {
    Text(
        text = text,
        style = ChanTheme.type.pageTitle,
        color = ChanTheme.colors.strongHeading,
        modifier = modifier,
    )
}

/** Convenience for content padding at standard horizontal screen padding. */
fun screenContentPadding(extraTop: Int = 0, extraBottom: Int = 24): PaddingValues =
    PaddingValues(start = 20.dp, end = 20.dp, top = (16 + extraTop).dp, bottom = extraBottom.dp)

/** Applies content descriptions cleanly for decorative-vs-labeled content. */
@Composable
fun LabeledIcon(icon: ImageVector, description: String?, tint: Color, size: Int = 24) {
    if (description == null) {
        Icon(icon, contentDescription = null, tint = tint, modifier = Modifier.size(size.dp))
    } else {
        Box(Modifier.clearAndSetSemantics { }) {
            Icon(icon, contentDescription = description, tint = tint, modifier = Modifier.size(size.dp))
        }
    }
}
