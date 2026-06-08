package com.yourteam.ecommerceguider.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Icon
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import com.yourteam.ecommerceguider.R
import com.yourteam.ecommerceguider.theme.AppColors
import com.yourteam.ecommerceguider.theme.AppDimensions
import com.yourteam.ecommerceguider.theme.AppElevation
import com.yourteam.ecommerceguider.theme.AppSpacing
import com.yourteam.ecommerceguider.theme.AppTypography

@Composable
fun ProductBottomActionBar(
    price: Double?,
    cartItemCount: Int,
    inStock: Boolean,
    onCartClick: () -> Unit,
    onAddToCart: () -> Unit,
    onBuyNow: () -> Unit,
    modifier: Modifier = Modifier,
    originalPrice: Double? = null,
    addToCartLoading: Boolean = false,
) {
    Surface(
        modifier = modifier.navigationBarsPadding(),
        color = AppColors.Surface,
        shadowElevation = AppElevation.None,
    ) {
        Column(modifier = Modifier.fillMaxWidth()) {
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
                horizontalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Box {
                    AppIconButton(
                        onClick = onCartClick,
                        style = AppIconButtonStyle.Surface,
                        containerSize = AppDimensions.IconButtonLarge,
                        iconSize = AppDimensions.IconSmall,
                    ) {
                        Icon(
                            painter = painterResource(R.drawable.ic_cart_24),
                            contentDescription = "购物车",
                        )
                    }
                    if (cartItemCount > 0) {
                        Box(
                            modifier = Modifier
                                .align(Alignment.TopEnd)
                                .size(18.dp)
                                .clip(androidx.compose.foundation.shape.CircleShape)
                                .background(AppColors.Primary),
                            contentAlignment = Alignment.Center,
                        ) {
                            Text(
                                text = cartItemCount.coerceAtMost(99).toString(),
                                style = AppTypography.Caption,
                                color = AppColors.OnPrimary,
                                maxLines = 1,
                            )
                        }
                    }
                }

                SecondaryButton(
                    text = if (inStock) "加入购物车" else "暂时缺货",
                    onClick = onAddToCart,
                    enabled = inStock && price != null,
                    loading = addToCartLoading,
                    height = AppDimensions.ButtonHeight,
                    modifier = Modifier.weight(1f),
                )
                PrimaryButton(
                    text = "立即购买",
                    onClick = onBuyNow,
                    enabled = inStock && price != null && !addToCartLoading,
                    height = AppDimensions.ButtonHeight,
                    modifier = Modifier.weight(1f),
                )
            }
        }
    }
}
