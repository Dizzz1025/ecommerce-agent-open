package com.yourteam.ecommerceguider.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable

private val LightColors = lightColorScheme(
    primary = Forest,
    secondary = Clay,
    background = Canvas,
    surface = Mist,
    onPrimary = Mist,
    onSecondary = Mist,
    onBackground = Ink,
    onSurface = Ink,
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

