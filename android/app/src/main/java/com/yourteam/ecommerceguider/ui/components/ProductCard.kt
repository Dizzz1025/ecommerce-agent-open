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
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
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
    onAddToCart: (String) -> Unit,
    modifier: Modifier = Modifier,
    rank: Int = 1,
    isPrimary: Boolean = false,
    totalCount: Int = 1,
    roleLabel: String? = null,
) {
    val metaText = listOf(product.brand, product.subCategory ?: product.category)
        .filter { it.isNotBlank() }
        .distinct()
        .joinToString(" · ")
    val displayRoleLabel = roleLabel ?: when {
        isPrimary -> "首选推荐"
        rank == 2 -> "备选推荐"
        else -> "其他选择"
    }
    val imageWidth = if (isPrimary) 116.dp else 92.dp
    val imageHeight = if (isPrimary) 136.dp else 112.dp
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
            .clickable { onClick(product.skuId) },
        shape = RoundedCornerShape(if (isPrimary) 16.dp else 12.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
        border = BorderStroke(
            width = 1.dp,
            color = if (isPrimary) {
                MaterialTheme.colorScheme.primary.copy(alpha = 0.28f)
            } else {
                MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.45f)
            },
        ),
    ) {
        Row(
            modifier = Modifier.padding(if (isPrimary) 14.dp else 12.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            ProductImage(
                imageUrl = product.imageUrl,
                contentDescription = product.displayTitleShort,
                modifier = Modifier
                    .width(imageWidth)
                    .height(imageHeight),
                cornerRadius = 12.dp,
            )

            Column(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(7.dp),
            ) {
                Surface(
                    shape = RoundedCornerShape(8.dp),
                    color = if (isPrimary) {
                        MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.6f)
                    } else {
                        MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.55f)
                    },
                ) {
                    Text(
                        text = if (isPrimary) displayRoleLabel else displayRoleLabel,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                        style = MaterialTheme.typography.labelSmall,
                        color = if (isPrimary) {
                            MaterialTheme.colorScheme.onPrimaryContainer
                        } else {
                            MaterialTheme.colorScheme.onSurfaceVariant
                        },
                    )
                }
                Text(
                    text = product.displayTitleShort,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                if (metaText.isNotBlank()) {
                    Text(
                        text = metaText,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                Text(
                    text = "¥${formatPrice(product.price)}",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary,
                )
                ProductTagRow(tags = product.displayTags)
                if (isPrimary && product.displayReason.isNotBlank()) {
                    Text(
                        text = product.displayReason,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                Row(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    IconButton(
                        onClick = { onClick(product.skuId) },
                        modifier = Modifier.size(44.dp),
                    ) {
                        Icon(
                            painter = painterResource(R.drawable.ic_chevron_right_20),
                            contentDescription = "查看详情",
                            tint = MaterialTheme.colorScheme.primary,
                        )
                    }
                    Button(
                        onClick = {
                            if (!addCoolingDown) {
                                addCoolingDown = true
                                onAddToCart(product.skuId)
                            }
                        },
                        modifier = Modifier.weight(1f),
                        enabled = !addCoolingDown,
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = Color(0xFF2E7D32),
                        ),
                    ) {
                        Icon(
                            painter = painterResource(
                                if (addCoolingDown) {
                                    R.drawable.ic_check_circle_20
                                } else {
                                    R.drawable.ic_cart_24
                                },
                            ),
                            contentDescription = null,
                            modifier = Modifier.size(18.dp),
                        )
                        androidx.compose.foundation.layout.Spacer(modifier = Modifier.width(6.dp))
                        Text(if (addCoolingDown) "已加入" else "加入购物车", maxLines = 1)
                    }
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
                shape = RoundedCornerShape(8.dp),
                color = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.55f),
            ) {
                Text(
                    text = tag,
                    modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onPrimaryContainer,
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
