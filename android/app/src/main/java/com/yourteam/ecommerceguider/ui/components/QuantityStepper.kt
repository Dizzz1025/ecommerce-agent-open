package com.yourteam.ecommerceguider.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.yourteam.ecommerceguider.theme.AppColors
import com.yourteam.ecommerceguider.theme.AppDimensions
import com.yourteam.ecommerceguider.theme.AppSpacing
import com.yourteam.ecommerceguider.theme.AppTypography

@Composable
fun QuantityStepper(
    quantity: Int,
    onDecrease: () -> Unit,
    onIncrease: () -> Unit,
    modifier: Modifier = Modifier,
    minimum: Int = 1,
    maximum: Int? = null,
    enabled: Boolean = true,
    loading: Boolean = false,
) {
    val canDecrease = enabled && !loading && quantity > minimum
    val canIncrease = enabled && !loading && maximum?.let { quantity < it } != false

    Row(
        modifier = modifier,
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
    ) {
        StepperControl(
            text = "-",
            enabled = canDecrease,
            onClick = onDecrease,
        )
        Box(
            modifier = Modifier.widthIn(min = AppDimensions.IconButtonSmall),
            contentAlignment = Alignment.Center,
        ) {
            if (loading) {
                CircularProgressIndicator(
                    modifier = Modifier.size(AppDimensions.IconSmall),
                    strokeWidth = 2.dp,
                    color = AppColors.Primary,
                )
            } else {
                Text(
                    text = quantity.coerceAtLeast(minimum).toString(),
                    style = AppTypography.TitleSmall,
                    fontWeight = FontWeight.SemiBold,
                    color = AppColors.TextPrimary,
                    maxLines = 1,
                )
            }
        }
        StepperControl(
            text = "+",
            enabled = canIncrease,
            onClick = onIncrease,
        )
    }
}

@Composable
private fun StepperControl(
    text: String,
    enabled: Boolean,
    onClick: () -> Unit,
) {
    val containerColor = if (enabled) AppColors.SurfaceSoft else AppColors.SurfacePressed
    val textColor = if (enabled) AppColors.TextPrimary else AppColors.TextDisabled

    Box(
        modifier = Modifier
            .size(AppDimensions.IconButtonSmall)
            .clip(CircleShape)
            .background(containerColor)
            .clickable(
                enabled = enabled,
                role = Role.Button,
                onClick = onClick,
            ),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = text,
            style = AppTypography.TitleSmall,
            fontWeight = FontWeight.SemiBold,
            color = textColor,
        )
    }
}
