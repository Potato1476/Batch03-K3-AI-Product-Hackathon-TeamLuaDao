package com.chan.app.ui.theme

import android.app.Activity
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.ReadOnlyComposable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

/**
 * Entry point for CHAN theming. Provides semantic color, type, and dimension
 * tokens plus a minimal Material 3 color scheme (so Material components pick up
 * sensible defaults). Screens should read tokens through [ChanTheme].
 */
@Composable
fun ChanTheme(
    darkTheme: Boolean,
    content: @Composable () -> Unit,
) {
    val colors = if (darkTheme) DarkChanColors else LightChanColors

    val material = if (darkTheme) {
        darkColorScheme(
            primary = colors.brandFilled,
            onPrimary = colors.onBrandFilled,
            background = colors.screenBackground,
            surface = colors.card,
            error = colors.danger,
        )
    } else {
        lightColorScheme(
            primary = colors.brandFilled,
            onPrimary = colors.onBrandFilled,
            background = colors.screenBackground,
            surface = colors.card,
            error = colors.danger,
        )
    }

    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as? Activity)?.window ?: return@SideEffect
            WindowCompat.getInsetsController(window, view).isAppearanceLightStatusBars = !darkTheme
        }
    }

    CompositionLocalProvider(
        LocalChanColors provides colors,
        LocalChanTypography provides ChanTypography(),
        LocalChanDimens provides ChanDimens(),
    ) {
        MaterialTheme(
            colorScheme = material,
            typography = Typography(),
            content = content,
        )
    }
}

/** Convenience accessors so screens read `ChanTheme.colors`, etc. */
object ChanTheme {
    val colors: ChanColors
        @Composable @ReadOnlyComposable get() = LocalChanColors.current
    val type: ChanTypography
        @Composable @ReadOnlyComposable get() = LocalChanTypography.current
    val dimens: ChanDimens
        @Composable @ReadOnlyComposable get() = LocalChanDimens.current
}
