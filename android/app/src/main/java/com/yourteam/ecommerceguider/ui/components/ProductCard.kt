@file:OptIn(androidx.compose.foundation.layout.ExperimentalLayoutApi::class)

package com.yourteam.ecommerceguider.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.yourteam.ecommerceguider.R
import com.yourteam.ecommerceguider.data.model.ProductUiModel
import com.yourteam.ecommerceguider.theme.AppColors
import com.yourteam.ecommerceguider.theme.AppDimensions
import com.yourteam.ecommerceguider.theme.AppRadius
import com.yourteam.ecommerceguider.theme.AppSpacing
import com.yourteam.ecommerceguider.theme.AppTypography
import kotlinx.coroutines.delay

@Composable
fun ProductCard(
    product: ProductUiModel,
    onClick: (String) -> Unit,
    onAddToCart: (ProductUiModel) -> Unit,
    modifier: Modifier = Modifier,
    rank: Int = 1,
    isPrimary: Boolean = false,
    totalCount: Int = 1,
    roleLabel: String? = null,
    showRecommendationReason: Boolean = true,
) {
    val metaText = listOf(product.brand, product.subCategory ?: product.category)
        .filter { it.isNotBlank() }
        .distinct()
        .joinToString(" · ")
    val backendOptionLabel = product.presentation?.optionLabel?.takeIf { it.isNotBlank() }
    val displayRoleLabel = roleLabel ?: when {
        backendOptionLabel != null -> backendOptionLabel
        rank == 1 -> "方案一"
        rank == 2 -> "方案二"
        rank == 3 -> "方案三"
        else -> "方案$rank"
    }
    val imageWidth = if (isPrimary) AppDimensions.RecommendationImageHeight else 96.dp
    val imageHeight = if (isPrimary) AppDimensions.RecommendationImageHeight else 96.dp
    val cardShape = RoundedCornerShape(AppRadius.Card)
    var addCoolingDown by remember(product.skuId) { mutableStateOf(false) }

    LaunchedEffect(addCoolingDown) {
        if (addCoolingDown) {
            delay(1_200)
            addCoolingDown = false
        }
    }

    Surface(
        modifier = modifier
            .fillMaxWidth()
            .clickable { onClick(product.skuId) },
        shape = cardShape,
        color = AppColors.Surface,
        border = BorderStroke(1.dp, AppColors.Border),
    ) {
        Column(
            modifier = Modifier.padding(AppSpacing.Md),
            verticalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.Top,
                horizontalArrangement = Arrangement.spacedBy(AppSpacing.Md),
            ) {
                ProductImage(
                    imageUrl = product.imageUrl,
                    contentDescription = product.displayTitleShort,
                    modifier = Modifier
                        .width(imageWidth)
                        .height(imageHeight),
                    cornerRadius = AppRadius.Large,
                )

                Column(
                    modifier = Modifier.weight(1f),
                    verticalArrangement = Arrangement.spacedBy(AppSpacing.Xs),
                ) {
                    if (showRecommendationReason) {
                        Surface(
                            shape = RoundedCornerShape(AppRadius.Pill),
                            color = if (isPrimary) AppColors.Primary else AppColors.SurfaceSoft,
                            border = BorderStroke(1.dp, if (isPrimary) AppColors.Primary else AppColors.Border),
                        ) {
                            Text(
                                text = displayRoleLabel,
                                modifier = Modifier.padding(horizontal = AppSpacing.Md, vertical = AppSpacing.Xs),
                                style = AppTypography.CaptionStrong,
                                color = if (isPrimary) AppColors.OnPrimary else AppColors.TextSecondary,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis,
                            )
                        }
                    }
                    Text(
                        text = product.displayTitleShort,
                        style = AppTypography.TitleSmall,
                        color = AppColors.TextPrimary,
                        fontWeight = FontWeight.SemiBold,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis,
                    )
                    if (metaText.isNotBlank()) {
                        Text(
                            text = metaText,
                            style = AppTypography.BodySmall,
                            color = AppColors.TextSecondary,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                    }
                    PriceText(price = product.price, level = PriceTextLevel.Normal)
                    ProductTagRow(tags = product.displayTags)
                }
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                SecondaryButton(
                    text = "查看详情",
                    onClick = { onClick(product.skuId) },
                    modifier = Modifier
                        .weight(1f)
                        .heightIn(min = AppDimensions.ButtonSmallHeight),
                    height = AppDimensions.ButtonSmallHeight,
                )
                AppIconButton(
                    onClick = {
                        if (!addCoolingDown) {
                            addCoolingDown = true
                            onAddToCart(product)
                        }
                    },
                    enabled = !addCoolingDown,
                    selected = !addCoolingDown,
                    style = AppIconButtonStyle.Surface,
                    containerSize = AppDimensions.IconButtonSmall,
                    iconSize = AppDimensions.IconSmall,
                ) {
                    Icon(
                        painter = painterResource(
                            R.drawable.ic_cart_24,
                        ),
                        contentDescription = if (addCoolingDown) "正在加购" else "加入购物车",
                    )
                }
            }
        }
    }
}

@Composable
fun ProductTagRow(
    tags: List<String>,
    modifier: Modifier = Modifier,
) {
    val displayTags = tags
        .map { it.trim() }
        .filter { it.isNotBlank() }
        .filterNot { tag ->
            listOf("debug", "trace", "rag", "system", "json").any { token ->
                tag.contains(token, ignoreCase = true)
            }
        }
        .distinct()
        .take(3)

    if (displayTags.isEmpty()) {
        return
    }
    FlowRow(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
        verticalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
    ) {
        displayTags.forEach { tag ->
            TagChip(text = tag)
        }
    }
}

fun formatPrice(value: Double): String {
    return if (value % 1.0 == 0.0) {
        value.toInt().toString()
    } else {
        "%.2f".format(value)
    }
}
