package com.yourteam.ecommerceguider.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.LocalContentColor
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.yourteam.ecommerceguider.theme.AppColors
import com.yourteam.ecommerceguider.theme.AppDimensions
import com.yourteam.ecommerceguider.theme.AppRadius
import com.yourteam.ecommerceguider.theme.AppSpacing
import com.yourteam.ecommerceguider.theme.AppTypography

enum class AppIconButtonStyle {
    Plain,
    Surface,
    Hero,
}

@Composable
fun AppIconButton(
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    selected: Boolean = false,
    style: AppIconButtonStyle = AppIconButtonStyle.Surface,
    containerSize: Dp = AppDimensions.IconButton,
    hitAreaSize: Dp = containerSize.coerceAtLeast(AppDimensions.IconButton),
    iconSize: Dp = AppDimensions.IconMedium,
    icon: @Composable BoxScope.() -> Unit,
) {
    val shape = CircleShape
    val containerColor = when {
        !enabled -> AppColors.SurfaceSoft
        selected && style != AppIconButtonStyle.Hero -> AppColors.Primary
        style == AppIconButtonStyle.Plain -> Color.Transparent
        style == AppIconButtonStyle.Hero -> AppColors.HeroIconBackground
        else -> AppColors.Surface
    }
    val contentColor = when {
        !enabled -> AppColors.TextDisabled
        selected && style != AppIconButtonStyle.Hero -> AppColors.OnPrimary
        selected && style == AppIconButtonStyle.Hero -> AppColors.Primary
        style == AppIconButtonStyle.Hero -> AppColors.HeroIcon
        else -> AppColors.TextPrimary
    }
    val borderColor = when {
        !enabled -> AppColors.Border
        selected || style == AppIconButtonStyle.Plain || style == AppIconButtonStyle.Hero -> Color.Transparent
        else -> AppColors.Border
    }
    val touchSize = hitAreaSize
        .coerceAtLeast(AppDimensions.IconButton)
        .coerceAtLeast(containerSize)

    Box(
        modifier = modifier
            .size(touchSize)
            .clickable(
                enabled = enabled,
                role = Role.Button,
                onClick = onClick,
            ),
        contentAlignment = Alignment.Center,
    ) {
        Box(
            modifier = Modifier
                .size(containerSize)
                .clip(shape)
                .background(containerColor)
                .then(
                    if (borderColor == Color.Transparent) {
                        Modifier
                    } else {
                        Modifier.border(BorderStroke(1.dp, borderColor), shape)
                    }
                ),
            contentAlignment = Alignment.Center,
        ) {
            CompositionLocalProvider(LocalContentColor provides contentColor) {
                Box(
                    modifier = Modifier.size(iconSize),
                    contentAlignment = Alignment.Center,
                    content = icon,
                )
            }
        }
    }
}

@Composable
fun PrimaryButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    loading: Boolean = false,
    height: Dp = AppDimensions.ButtonHeight,
) {
    Button(
        onClick = onClick,
        enabled = enabled && !loading,
        modifier = modifier
            .heightIn(min = height)
            .defaultMinSize(minHeight = height),
        shape = RoundedCornerShape(AppRadius.Large),
        colors = ButtonDefaults.buttonColors(
            containerColor = AppColors.Primary,
            contentColor = AppColors.OnPrimary,
            disabledContainerColor = AppColors.SurfacePressed,
            disabledContentColor = AppColors.TextDisabled,
        ),
        contentPadding = PaddingValues(horizontal = AppSpacing.Lg, vertical = AppSpacing.Sm),
    ) {
        ButtonContent(
            text = text,
            loading = loading,
            indicatorColor = AppColors.OnPrimary,
        )
    }
}

@Composable
fun SecondaryButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    loading: Boolean = false,
    height: Dp = AppDimensions.ButtonHeight,
) {
    OutlinedButton(
        onClick = onClick,
        enabled = enabled && !loading,
        modifier = modifier
            .heightIn(min = height)
            .defaultMinSize(minHeight = height),
        shape = RoundedCornerShape(AppRadius.Large),
        border = BorderStroke(1.dp, if (enabled) AppColors.BorderStrong else AppColors.Border),
        colors = ButtonDefaults.outlinedButtonColors(
            containerColor = AppColors.SecondaryButton,
            contentColor = AppColors.TextPrimary,
            disabledContainerColor = AppColors.SurfaceSoft,
            disabledContentColor = AppColors.TextDisabled,
        ),
        contentPadding = PaddingValues(horizontal = AppSpacing.Lg, vertical = AppSpacing.Sm),
    ) {
        ButtonContent(
            text = text,
            loading = loading,
            indicatorColor = AppColors.Primary,
        )
    }
}

@Composable
private fun ButtonContent(
    text: String,
    loading: Boolean,
    indicatorColor: Color,
) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
    ) {
        if (loading) {
            CircularProgressIndicator(
                modifier = Modifier.size(AppDimensions.IconSmall),
                strokeWidth = 2.dp,
                color = indicatorColor,
            )
        }
        Text(
            text = text,
            style = AppTypography.Button,
            maxLines = 2,
            overflow = TextOverflow.Clip,
            textAlign = TextAlign.Center,
        )
    }
}
