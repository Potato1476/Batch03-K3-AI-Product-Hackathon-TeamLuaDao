package com.chan.app.ui.theme

import androidx.compose.runtime.Immutable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

/**
 * Spacing and sizing tokens. Heights are MINIMUM heights (via heightIn) so that
 * enlarged text is never clipped — never fixed heights.
 */
@Immutable
data class ChanDimens(
    val screenPadding: Dp = 20.dp,
    val sectionGap: Dp = 22.dp,
    val cardGap: Dp = 12.dp,
    val cardCorner: Dp = 16.dp,
    val sheetCorner: Dp = 24.dp,
    val primaryCtaMinHeight: Dp = 64.dp,
    val secondaryButtonMinHeight: Dp = 54.dp,
    val minTouchTarget: Dp = 48.dp,
    val bottomNavItemMinHeight: Dp = 56.dp,
    val ctaCorner: Dp = 16.dp,
    val innerPadding: Dp = 16.dp,
)

val LocalChanDimens = staticCompositionLocalOf { ChanDimens() }
