package com.yourteam.ecommerceguider.theme

import android.app.Activity
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat
import androidx.compose.ui.graphics.Color

private val LightColors = lightColorScheme(
    primary = AppColors.Primary,
    onPrimary = AppColors.OnPrimary,
    primaryContainer = AppColors.SurfacePressed,
    onPrimaryContainer = AppColors.TextPrimary,
    secondary = AppColors.AccentWarm,
    onSecondary = AppColors.TextInverse,
    secondaryContainer = AppColors.AccentWarmSoft,
    onSecondaryContainer = AppColors.TextPrimary,
    tertiary = AppColors.Success,
    onTertiary = AppColors.TextInverse,
    tertiaryContainer = AppColors.SuccessSoft,
    onTertiaryContainer = AppColors.TextPrimary,
    background = AppColors.Background,
    onBackground = AppColors.TextPrimary,
    surface = AppColors.Surface,
    onSurface = AppColors.TextPrimary,
    surfaceVariant = AppColors.SurfaceSoft,
    onSurfaceVariant = AppColors.TextSecondary,
    surfaceTint = Color.Transparent,
    outline = AppColors.BorderStrong,
    outlineVariant = AppColors.Border,
    error = AppColors.Danger,
    onError = AppColors.TextInverse,
    errorContainer = AppColors.DangerSoft,
    onErrorContainer = AppColors.TextPrimary,
    inverseSurface = AppColors.TextPrimary,
    inverseOnSurface = AppColors.TextInverse,
    inversePrimary = AppColors.TextInverse,
    scrim = AppColors.OverlayStrong,
)

private val DarkColors = darkColorScheme(
    primary = Color(0xFFE8E8E4),
    onPrimary = Color(0xFF151515),
    primaryContainer = Color(0xFF30302E),
    onPrimaryContainer = Color(0xFFF7F7F5),
    secondary = AppColors.AccentWarm,
    onSecondary = Color(0xFF151515),
    secondaryContainer = Color(0xFF5A4435),
    onSecondaryContainer = Color(0xFFF6EEE8),
    background = Color(0xFF151515),
    onBackground = Color(0xFFF7F7F5),
    surface = Color(0xFF1E1E1C),
    onSurface = Color(0xFFF7F7F5),
    surfaceVariant = Color(0xFF30302E),
    onSurfaceVariant = Color(0xFFD8D8D3),
    outline = Color(0xFF5E5E58),
    outlineVariant = Color(0xFF40403C),
    error = Color(0xFFE8B4AC),
    onError = Color(0xFF151515),
    errorContainer = Color(0xFF5E2D28),
    onErrorContainer = Color(0xFFF8EFED),
)

@Composable
fun EcommerceGuiderTheme(
    darkTheme: Boolean = false,
    content: @Composable () -> Unit,
) {
    val colorScheme = if (darkTheme) DarkColors else LightColors
    val view = LocalView.current

    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as? Activity)?.window ?: return@SideEffect
            window.statusBarColor = AppColors.Background.toArgb()
            window.navigationBarColor = AppColors.Surface.toArgb()
            WindowCompat.getInsetsController(window, view).apply {
                isAppearanceLightStatusBars = !darkTheme
                isAppearanceLightNavigationBars = !darkTheme
            }
        }
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = AppMaterialTypography,
        content = content,
    )
}
