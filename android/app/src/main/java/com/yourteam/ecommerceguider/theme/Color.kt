package com.yourteam.ecommerceguider.theme

import androidx.compose.ui.graphics.Color

object AppColors {
    val Background = Color(0xFFFAF7F1)
    val BackgroundElevated = Color(0xFFFCFAF6)

    val Surface = Color(0xFFFFFFFF)
    val SurfaceSoft = Color(0xFFF6F1E9)
    val SurfacePressed = Color(0xFFF0EAE1)

    val TextPrimary = Color(0xFF151515)
    val TextSecondary = Color(0xFF746F67)
    val TextTertiary = Color(0xFFA9A196)
    val TextDisabled = Color(0xFFC8C0B6)
    val TextInverse = Color(0xFFFFFFFF)

    val Border = Color(0xFFEEE7DC)
    val BorderStrong = Color(0xFFE0D7CB)
    val Divider = Color(0xFFF4EEE5)

    val Primary = Color(0xFF151515)
    val PrimaryPressed = Color(0xFF30302E)
    val OnPrimary = Color(0xFFFFFFFF)

    val SecondaryButton = Color(0xFFFFFFFF)
    val SecondaryButtonPressed = Color(0xFFF4EFE7)

    val AccentWarm = Color(0xFFA77A5D)
    val AccentWarmSoft = Color(0xFFF7EFE6)

    val Danger = Color(0xFFB65A50)
    val DangerSoft = Color(0xFFF8EFED)

    val Success = Color(0xFF6F8A73)
    val SuccessSoft = Color(0xFFF0F5EF)

    val OverlayLight = Color(0x26000000)
    val OverlayMedium = Color(0x52000000)
    val OverlayStrong = Color(0x80000000)

    val HeroText = Color(0xFFFFFFFF)
    val HeroIconBackground = Color(0xCCFFFFFF)
    val HeroIcon = Color(0xFF1A1A1A)
}

object ChatColors {
    val Background = Color(0xFFFAF8F4)
    val Surface = Color(0xFFFFFFFF)
    val SurfaceSubtle = Color(0xFFF6F2EB)
    val Border = Color(0xFFE8E2D8)
    val TextPrimary = Color(0xFF171717)
    val TextSecondary = Color(0xFF777168)
    val TextTertiary = Color(0xFFA09A91)
    val WarmAccent = Color(0xFFB88763)
    val Success = Color(0xFF6F9476)
    val SuccessSoft = Color(0xFFEAF1EB)
    val TagBackground = Color(0xFFF5F1EA)
    val TagText = Color(0xFF6D675F)
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
