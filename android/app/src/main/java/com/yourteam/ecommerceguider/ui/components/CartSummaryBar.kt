package com.yourteam.ecommerceguider.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.yourteam.ecommerceguider.theme.AppColors
import com.yourteam.ecommerceguider.theme.AppDimensions
import com.yourteam.ecommerceguider.theme.AppElevation
import com.yourteam.ecommerceguider.theme.AppSpacing
import com.yourteam.ecommerceguider.theme.AppTypography

@Composable
fun CartSummaryBar(
    totalQuantity: Int,
    totalPrice: Double,
    onCheckoutClick: () -> Unit,
    modifier: Modifier = Modifier,
    originalTotalPrice: Double? = null,
    enabled: Boolean = true,
) {
    Surface(
        modifier = modifier.navigationBarsPadding(),
        color = AppColors.Surface,
        shadowElevation = AppElevation.None,
    ) {
        Column(
            modifier = Modifier.fillMaxWidth(),
        ) {
            Spacer(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(1.dp)
                    .background(AppColors.Divider),
            )
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(
                        PaddingValues(
                            horizontal = AppSpacing.Lg,
                            vertical = AppSpacing.Sm,
                        ),
                    ),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(AppSpacing.Md),
            ) {
                Column(
                    modifier = Modifier.weight(1f),
                    verticalArrangement = Arrangement.spacedBy(AppSpacing.Xs),
                ) {
                    Text(
                        text = "共 $totalQuantity 件",
                        style = AppTypography.BodySmall,
                        color = AppColors.TextSecondary,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                    Row(
                        verticalAlignment = Alignment.Bottom,
                        horizontalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
                    ) {
                        PriceText(
                            price = totalPrice,
                            level = PriceTextLevel.Highlight,
                            modifier = Modifier.weight(1f, fill = false),
                        )
                        originalTotalPrice
                            ?.takeIf { it > totalPrice }
                            ?.let { original ->
                                OriginalPriceText(price = original)
                            }
                    }
                }
                PrimaryButton(
                    text = "去结算",
                    onClick = onCheckoutClick,
                    enabled = enabled && totalQuantity > 0,
                    height = AppDimensions.ButtonHeight,
                    modifier = Modifier.widthIn(min = 112.dp),
                )
            }
        }
    }
}
