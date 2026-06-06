package com.yourteam.ecommerceguider.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val LightColors = lightColorScheme(
    primary = Forest,
    onPrimary = Color.White,
    primaryContainer = Color(0xFFECEEFF),
    onPrimaryContainer = Color(0xFF29305F),
    secondary = Clay,
    secondaryContainer = Color(0xFFF2E9FF),
    onSecondaryContainer = Color(0xFF33294E),
    background = Canvas,
    surface = Mist,
    surfaceVariant = Color(0xFFF0F3FC),
    outlineVariant = Color(0xFFC9D2EA),
    onSecondary = Mist,
    onBackground = Ink,
    onSurface = Ink,
    onSurfaceVariant = Color(0xFF65708B),
)

private val DarkColors = darkColorScheme(
    primary = Clay,
    secondary = Forest,
)

@Composable
fun EcommerceGuiderTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = LightColors,
        typography = AppTypography,
        content = content,
    )
}
