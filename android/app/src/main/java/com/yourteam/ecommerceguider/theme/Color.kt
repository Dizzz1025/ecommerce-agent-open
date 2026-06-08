package com.yourteam.ecommerceguider.theme

import androidx.compose.ui.graphics.Color

object AppColors {
    val Background = Color(0xFFF7F7F5)
    val BackgroundElevated = Color(0xFFFAFAF8)

    val Surface = Color(0xFFFFFFFF)
    val SurfaceSoft = Color(0xFFF4F4F1)
    val SurfacePressed = Color(0xFFEEEEEA)

    val TextPrimary = Color(0xFF151515)
    val TextSecondary = Color(0xFF6F6F6B)
    val TextTertiary = Color(0xFFA0A09B)
    val TextDisabled = Color(0xFFC3C3BE)
    val TextInverse = Color(0xFFFFFFFF)

    val Border = Color(0xFFE8E8E4)
    val BorderStrong = Color(0xFFD8D8D3)
    val Divider = Color(0xFFF0F0EC)

    val Primary = Color(0xFF151515)
    val PrimaryPressed = Color(0xFF30302E)
    val OnPrimary = Color(0xFFFFFFFF)

    val SecondaryButton = Color(0xFFFFFFFF)
    val SecondaryButtonPressed = Color(0xFFF2F2EF)

    val AccentWarm = Color(0xFFB7835F)
    val AccentWarmSoft = Color(0xFFF6EEE8)

    val Danger = Color(0xFFB65A50)
    val DangerSoft = Color(0xFFF8EFED)

    val Success = Color(0xFF4F7A5D)
    val SuccessSoft = Color(0xFFEDF4EF)

    val OverlayLight = Color(0x26000000)
    val OverlayMedium = Color(0x52000000)
    val OverlayStrong = Color(0x80000000)

    val HeroText = Color(0xFFFFFFFF)
    val HeroIconBackground = Color(0xCCFFFFFF)
    val HeroIcon = Color(0xFF1A1A1A)
}

@Deprecated("Use AppColors.Background instead.", ReplaceWith("AppColors.Background"))
val Canvas = AppColors.Background

@Deprecated("Use AppColors.Primary instead.", ReplaceWith("AppColors.Primary"))
val Forest = AppColors.Primary

@Deprecated("Use AppColors.AccentWarm instead.", ReplaceWith("AppColors.AccentWarm"))
val Clay = AppColors.AccentWarm

@Deprecated("Use AppColors.TextPrimary instead.", ReplaceWith("AppColors.TextPrimary"))
val Ink = AppColors.TextPrimary

@Deprecated("Use AppColors.Surface instead.", ReplaceWith("AppColors.Surface"))
val Mist = AppColors.Surface
