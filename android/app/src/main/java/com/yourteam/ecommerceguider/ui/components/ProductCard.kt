@file:OptIn(androidx.compose.foundation.layout.ExperimentalLayoutApi::class)

package com.yourteam.ecommerceguider.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
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
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.yourteam.ecommerceguider.R
import com.yourteam.ecommerceguider.data.model.ProductUiModel
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
    val imageWidth = if (isPrimary) 116.dp else 92.dp
    val imageHeight = if (isPrimary) 136.dp else 112.dp
    val cardShape = RoundedCornerShape(if (isPrimary) 28.dp else 24.dp)
    var addCoolingDown by remember(product.skuId) { mutableStateOf(false) }

    LaunchedEffect(addCoolingDown) {
        if (addCoolingDown) {
            delay(1_200)
            addCoolingDown = false
        }
    }

    Card(
        modifier = modifier
            .fillMaxWidth()
            .spatialGlass(
                shape = cardShape,
                fillColor = if (isPrimary) {
                    SpatialGlassColorStrong
                } else {
                    SpatialGlassColor
                },
                elevation = if (isPrimary) 4.dp else 2.dp,
            )
            .clickable { onClick(product.skuId) },
        shape = cardShape,
        colors = CardDefaults.cardColors(containerColor = Color.Transparent),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
    ) {
        Column(
            modifier = Modifier.padding(if (isPrimary) 16.dp else 14.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.Top,
                horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                ProductImage(
                    imageUrl = product.imageUrl,
                    contentDescription = product.displayTitleShort,
                    modifier = Modifier
                        .width(imageWidth)
                        .height(imageHeight),
                    cornerRadius = 20.dp,
                )

                Column(
                    modifier = Modifier.weight(1f),
                    verticalArrangement = Arrangement.spacedBy(7.dp),
                ) {
                    Surface(
                        shape = RoundedCornerShape(999.dp),
                        color = Color.Transparent,
                        modifier = Modifier.background(
                            if (isPrimary) SpatialPrimaryGradient else Brush.linearGradient(
                                listOf(
                                    SpatialAccentMuted,
                                    SpatialAccentMutedViolet,
                                )
                            ),
                            RoundedCornerShape(999.dp),
                        ),
                    ) {
                        Text(
                            text = displayRoleLabel,
                            modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp),
                            style = MaterialTheme.typography.labelSmall,
                            color = if (isPrimary) Color.White else SpatialAccent,
                        )
                    }
                    Text(
                        text = product.displayTitleShort,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold,
                        maxLines = 3,
                        overflow = TextOverflow.Ellipsis,
                    )
                    if (metaText.isNotBlank()) {
                        Text(
                            text = metaText,
                            style = MaterialTheme.typography.bodySmall,
                            color = SpatialTextSecondary,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                    }
                    Text(
                        text = "¥${formatPrice(product.price)}",
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold,
                        color = SpatialTextPrimary,
                    )
                    ProductTagRow(tags = product.displayTags)
                }
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                OutlinedButton(
                    onClick = { onClick(product.skuId) },
                    modifier = Modifier
                        .weight(1f)
                        .heightIn(min = 46.dp),
                    shape = RoundedCornerShape(18.dp),
                    contentPadding = PaddingValues(horizontal = 6.dp),
                    border = BorderStroke(1.dp, SpatialGlassBorderColor),
                    colors = ButtonDefaults.outlinedButtonColors(
                        containerColor = SpatialGlassControl,
                        contentColor = SpatialTextPrimary,
                    ),
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        Text("查看详情", maxLines = 1, softWrap = false)
                    }
                }
                Button(
                    onClick = {
                        if (!addCoolingDown) {
                            addCoolingDown = true
                            onAddToCart(product)
                        }
                    },
                    modifier = Modifier
                        .weight(1.4f)
                        .background(SpatialPrimaryGradient, RoundedCornerShape(18.dp))
                        .heightIn(min = 46.dp),
                    enabled = !addCoolingDown,
                    shape = RoundedCornerShape(18.dp),
                    contentPadding = PaddingValues(horizontal = 8.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = Color.Transparent,
                        disabledContainerColor = SpatialAccentDisabled,
                    ),
                ) {
                    Icon(
                        painter = painterResource(
                            R.drawable.ic_cart_24,
                        ),
                        contentDescription = null,
                        modifier = Modifier.size(17.dp),
                    )
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(
                        text = if (addCoolingDown) "处理中" else "加入购物车",
                        maxLines = 1,
                        softWrap = false,
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
        horizontalArrangement = Arrangement.spacedBy(6.dp),
        verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        displayTags.forEach { tag ->
            Surface(
                shape = RoundedCornerShape(999.dp),
                color = SpatialAccentMuted,
                border = BorderStroke(1.dp, SpatialGlassBorderColor),
            ) {
                Text(
                    text = tag,
                    modifier = Modifier.padding(horizontal = 9.dp, vertical = 5.dp),
                    style = MaterialTheme.typography.labelSmall,
                    color = SpatialAccent,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
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
