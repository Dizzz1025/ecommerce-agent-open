package com.yourteam.ecommerceguider.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

val SpatialBackgroundBrush = Brush.verticalGradient(
    colors = listOf(
        Color(0xFFF7FAFF),
        Color(0xFFEEF5FF),
        Color(0xFFF8F5FF),
    ),
)

val SpatialPrimaryGradient = Brush.linearGradient(
    colors = listOf(
        Color(0xFF6D7CFF),
        Color(0xFF9B6DFF),
    ),
)

val SpatialAmbientBlue = Brush.radialGradient(
    colors = listOf(
        Color(0xFFDCEBFF).copy(alpha = 0.35f),
        Color(0xFFDCEBFF).copy(alpha = 0.12f),
        Color(0xFFDCEBFF).copy(alpha = 0.00f),
    ),
)

val SpatialAmbientViolet = Brush.radialGradient(
    colors = listOf(
        Color(0xFFE9DDFF).copy(alpha = 0.28f),
        Color(0xFFE9DDFF).copy(alpha = 0.10f),
        Color(0xFFE9DDFF).copy(alpha = 0.00f),
    ),
)

val SpatialAmbientSilver = Brush.radialGradient(
    colors = listOf(
        Color.White.copy(alpha = 0.64f),
        Color(0xFFF7FAFF).copy(alpha = 0.18f),
        Color.White.copy(alpha = 0.00f),
    ),
)

val SpatialGlassColor = Color.White.copy(alpha = 0.66f)
val SpatialGlassColorStrong = Color.White.copy(alpha = 0.76f)
val SpatialGlassColorSoft = Color.White.copy(alpha = 0.62f)
val SpatialGlassColorDock = Color.White.copy(alpha = 0.72f)
val SpatialGlassControl = Color.White.copy(alpha = 0.45f)
val SpatialGlassControlMuted = Color.White.copy(alpha = 0.40f)
val SpatialGlassControlDisabled = Color.White.copy(alpha = 0.36f)
val SpatialGlassBorderColor = Color.White.copy(alpha = 0.65f)
val SpatialShadowColor = Color(0xFF9DB7E8).copy(alpha = 0.12f)
val SpatialAccent = Color(0xFF6D7CFF)
val SpatialAccentBlue = Color(0xFF5E8CFF)
val SpatialAccentViolet = Color(0xFF9B6DFF)
val SpatialAccentDisabled = Color(0xFF6D7CFF).copy(alpha = 0.36f)
val SpatialAccentMuted = Color(0xFFEFF4FF)
val SpatialAccentMutedViolet = Color(0xFFF3EEFF)
val SpatialIconNeutral = Color(0xFF6B7280)
val SpatialIconMuted = Color(0xFF7A8194)
val SpatialTextPrimary = Color(0xFF111827)
val SpatialTextBody = Color(0xFF374151)
val SpatialTextSecondary = Color(0xFF6B7280)
val SpatialTextPlaceholder = Color(0xFF9CA3AF)

fun Modifier.spatialGlass(
    shape: Shape = RoundedCornerShape(24.dp),
    fillColor: Color = SpatialGlassColor,
    borderColor: Color = SpatialGlassBorderColor,
    elevation: Dp = 4.dp,
): Modifier = this
    .shadow(
        elevation = elevation,
        shape = shape,
        clip = false,
        ambientColor = SpatialShadowColor,
        spotColor = SpatialShadowColor,
    )
    .clip(shape)
    .background(fillColor)
    .background(
        Brush.linearGradient(
            colors = listOf(
                Color.White.copy(alpha = 0.28f),
                Color(0xFFF7FAFF).copy(alpha = 0.12f),
                Color.Transparent,
            ),
        ),
    )
    .border(BorderStroke(1.dp, borderColor), shape)
