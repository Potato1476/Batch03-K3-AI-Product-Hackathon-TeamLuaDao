package com.chan.app.ui.theme

import androidx.compose.runtime.Immutable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color

// ---------------------------------------------------------------------------
// Raw palette. Screens must NOT reference these directly; use ChanColors tokens.
// ---------------------------------------------------------------------------

// Light
private val ScreenBgLight = Color(0xFFF5F8FE)
private val InfoTintLight = Color(0xFFEAF0FC)
private val DividerLight = Color(0xFFDCE6F8)
private val BorderLight = Color(0xFFC3D2EE)
private val DisabledLight = Color(0xFF93A6CC)
private val MutedTextLight = Color(0xFF6B7C9E)
private val BodyTextLight = Color(0xFF4A5B85)
private val SecondaryHeadingLight = Color(0xFF33436B)
private val BrandLight = Color(0xFF26339E)
private val RaisedBrandLight = Color(0xFF3A49C0)

// Dark
private val ScreenBgDark = Color(0xFF0B1220)
private val CardDark = Color(0xFF17223C)
private val InnerSurfaceDark = Color(0xFF111B31)
private val InfoTintDark = Color(0xFF243252)
private val BorderDark = Color(0xFF2E3D61)
private val BrandHeadingDark = Color(0xFFBACDF8)
private val StrongHeadingDark = Color(0xFFE3EAF9)
private val BodyDark = Color(0xFFBCC9E2)
private val MutedDark = Color(0xFF8EA0C2)
private val PrimaryButtonDark = Color(0xFF3B4BD4)
private val DisabledButtonDark = Color(0xFF3A4A70)

// Semantic risk colors (shared roles, tuned per mode where needed).
private val Danger = Color(0xFFDC2626)
private val DangerDark = Color(0xFF991B1B)
private val DangerSurfaceLight = Color(0xFFFEF2F2)
private val DangerBorderLight = Color(0xFFFCA5A5)

private val Warning = Color(0xFFD97706)
private val WarningDeep = Color(0xFF92400E)
private val WarningSurfaceLight = Color(0xFFFFFBEB)
private val WarningBorderLight = Color(0xFFFCD34D)

private val Success = Color(0xFF059669)
private val SuccessDeep = Color(0xFF065F46)
private val SuccessSurfaceLight = Color(0xFFECFDF5)
private val SuccessBorderLight = Color(0xFF6EE7B7)

/**
 * Semantic color tokens consumed by every screen. Never scatter raw hex values
 * through UI code — add a token here instead.
 */
@Immutable
data class ChanColors(
    val screenBackground: Color,
    val card: Color,
    val innerSurface: Color,
    val infoTint: Color,
    val divider: Color,
    val border: Color,
    val disabled: Color,
    val mutedText: Color,
    val bodyText: Color,
    val secondaryHeading: Color,
    val strongHeading: Color,
    val brand: Color,
    // The filled-brand surface (buttons). Dark mode must NOT use #26339E here.
    val brandFilled: Color,
    val onBrandFilled: Color,
    val disabledButton: Color,
    // Risk: red = HIGH only.
    val danger: Color,
    val dangerStrong: Color,
    val dangerSurface: Color,
    val dangerBorder: Color,
    // Risk: amber = MEDIUM/caution only.
    val warning: Color,
    val warningStrong: Color,
    val warningSurface: Color,
    val warningBorder: Color,
    // Green = system/on-device protection status only. Never "safe" for content.
    val success: Color,
    val successStrong: Color,
    val successSurface: Color,
    val successBorder: Color,
    val isDark: Boolean,
)

val LightChanColors = ChanColors(
    screenBackground = ScreenBgLight,
    card = Color.White,
    innerSurface = InfoTintLight,
    infoTint = InfoTintLight,
    divider = DividerLight,
    border = BorderLight,
    disabled = DisabledLight,
    mutedText = MutedTextLight,
    bodyText = BodyTextLight,
    secondaryHeading = SecondaryHeadingLight,
    strongHeading = SecondaryHeadingLight,
    brand = BrandLight,
    brandFilled = BrandLight,
    onBrandFilled = Color.White,
    disabledButton = DisabledLight,
    danger = Danger,
    dangerStrong = DangerDark,
    dangerSurface = DangerSurfaceLight,
    dangerBorder = DangerBorderLight,
    warning = Warning,
    warningStrong = WarningDeep,
    warningSurface = WarningSurfaceLight,
    warningBorder = WarningBorderLight,
    success = Success,
    successStrong = SuccessDeep,
    successSurface = SuccessSurfaceLight,
    successBorder = SuccessBorderLight,
    isDark = false,
)

val DarkChanColors = ChanColors(
    screenBackground = ScreenBgDark,
    card = CardDark,
    innerSurface = InnerSurfaceDark,
    infoTint = InfoTintDark,
    divider = BorderDark,
    border = BorderDark,
    disabled = MutedDark,
    mutedText = MutedDark,
    bodyText = BodyDark,
    secondaryHeading = BrandHeadingDark,
    strongHeading = StrongHeadingDark,
    brand = BrandHeadingDark,
    // Dark mode filled-brand surface uses #3B4BD4, never #26339E.
    brandFilled = PrimaryButtonDark,
    onBrandFilled = Color.White,
    disabledButton = DisabledButtonDark,
    danger = Color(0xFFF87171),
    dangerStrong = Color(0xFFFCA5A5),
    dangerSurface = Color(0xFF2A1416),
    dangerBorder = Color(0xFF7F1D1D),
    warning = Color(0xFFFBBF24),
    warningStrong = Color(0xFFFCD34D),
    warningSurface = Color(0xFF2A2110),
    warningBorder = Color(0xFF92400E),
    success = Color(0xFF34D399),
    successStrong = Color(0xFF6EE7B7),
    successSurface = Color(0xFF0F241C),
    successBorder = SuccessDeep,
    isDark = true,
)

val LocalChanColors = staticCompositionLocalOf { LightChanColors }
