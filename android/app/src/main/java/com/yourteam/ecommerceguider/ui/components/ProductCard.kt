@file:OptIn(androidx.compose.foundation.layout.ExperimentalLayoutApi::class)

package com.yourteam.ecommerceguider.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
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
import androidx.compose.ui.unit.sp
import com.yourteam.ecommerceguider.R
import com.yourteam.ecommerceguider.data.model.ProductUiModel
import com.yourteam.ecommerceguider.theme.AppColors
import com.yourteam.ecommerceguider.theme.AppDimensions
import com.yourteam.ecommerceguider.theme.AppRadius
import com.yourteam.ecommerceguider.theme.AppSpacing
import com.yourteam.ecommerceguider.theme.AppTypography
import com.yourteam.ecommerceguider.theme.ChatColors
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
    useChatColors: Boolean = false,
) {
    val metaText = listOf(product.brand, product.subCategory ?: product.category)
        .filter { it.isNotBlank() }
        .distinct()
        .joinToString(" · ")
    val backendOptionLabel = product.presentation?.optionLabel?.takeIf { it.isNotBlank() }
    val displayRoleLabel = roleLabel
        ?.takeIf { it.isNotBlank() && !it.isMechanicalRecommendationLabel() }
        ?: backendOptionLabel?.takeUnless { it.isMechanicalRecommendationLabel() }
    val imageWidth = if (isPrimary) AppDimensions.RecommendationImageHeight else 96.dp
    val imageHeight = if (isPrimary) AppDimensions.RecommendationImageHeight else 96.dp
    val cardShape = RoundedCornerShape(AppRadius.Card)
    val cardSurface = if (useChatColors) ChatColors.Surface else AppColors.Surface
    val cardBorder = if (useChatColors) ChatColors.Border else AppColors.Border
    val cardTextPrimary = if (useChatColors) ChatColors.TextPrimary else AppColors.TextPrimary
    val cardTextSecondary = if (useChatColors) ChatColors.TextSecondary else AppColors.TextSecondary
    val cardTagBackground = if (useChatColors) ChatColors.TagBackground else AppColors.SurfaceSoft
    val cardTagText = if (useChatColors) ChatColors.TagText else AppColors.TextSecondary
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
        color = cardSurface,
        border = BorderStroke(1.dp, cardBorder),
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
                    if (showRecommendationReason && displayRoleLabel != null) {
                        Surface(
                            shape = RoundedCornerShape(AppRadius.Pill),
                            color = if (isPrimary) AppColors.Primary else cardTagBackground,
                            border = BorderStroke(1.dp, if (isPrimary) AppColors.Primary else cardBorder),
                        ) {
                            Box(
                                modifier = Modifier
                                    .heightIn(min = 28.dp)
                                    .padding(horizontal = AppSpacing.Md),
                                contentAlignment = Alignment.Center,
                            ) {
                                Text(
                                    text = displayRoleLabel,
                                    style = AppTypography.CaptionStrong.copy(lineHeight = 14.sp),
                                    color = if (isPrimary) AppColors.OnPrimary else cardTagText,
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis,
                                )
                            }
                        }
                    }
                    Text(
                        text = product.displayTitleShort,
                        style = AppTypography.TitleSmall,
                        color = cardTextPrimary,
                        fontWeight = FontWeight.SemiBold,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis,
                    )
                    if (metaText.isNotBlank()) {
                        Text(
                            text = metaText,
                            style = AppTypography.BodySmall,
                            color = cardTextSecondary,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                    }
                    PriceText(
                        price = product.price,
                        level = PriceTextLevel.Normal,
                        color = cardTextPrimary,
                    )
                    ProductTagRow(tags = product.displayTags, useChatColors = useChatColors)
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
    useChatColors: Boolean = false,
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
        .take(2)

    if (displayTags.isEmpty()) {
        return
    }
    FlowRow(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
        verticalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
    ) {
        displayTags.forEach { tag ->
            TagChip(
                text = tag,
                containerColor = if (useChatColors) ChatColors.TagBackground else null,
                contentColor = if (useChatColors) ChatColors.TagText else null,
                borderColor = if (useChatColors) ChatColors.Border else null,
            )
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

private fun String.isMechanicalRecommendationLabel(): Boolean {
    val normalized = trim().replace(" ", "")
    return normalized.matches(Regex("""^方案[一二三四五六七八九十\d]+$""")) ||
        normalized.matches(Regex("""^推荐[一二三四五六七八九十\d]+$""")) ||
        normalized.matches(Regex("""^第[一二三四五六七八九十\d]+个?推荐$""")) ||
        normalized == "首选方案" ||
        normalized == "备选方案"
}
