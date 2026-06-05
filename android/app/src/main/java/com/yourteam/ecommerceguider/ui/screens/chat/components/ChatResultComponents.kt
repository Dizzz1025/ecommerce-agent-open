package com.yourteam.ecommerceguider.ui.screens.chat.components

import androidx.compose.animation.Crossfade
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Badge
import androidx.compose.material3.BadgedBox
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.yourteam.ecommerceguider.R
import com.yourteam.ecommerceguider.data.model.AssistantThinkingStatus
import com.yourteam.ecommerceguider.data.model.AssistantThinkingUiModel
import com.yourteam.ecommerceguider.data.model.ChatMessageUiModel
import com.yourteam.ecommerceguider.data.model.ProductUiModel
import com.yourteam.ecommerceguider.theme.EcommerceGuiderTheme
import com.yourteam.ecommerceguider.ui.components.ProductCard
import com.yourteam.ecommerceguider.utils.PreviewData

private val LargeShape = RoundedCornerShape(16.dp)
private val MediumShape = RoundedCornerShape(12.dp)
private val SmallShape = RoundedCornerShape(8.dp)

@Composable
fun GuideTopBar(
    cartItemCount: Int,
    historyCount: Int,
    onHistoryClick: () -> Unit,
    onCartClick: () -> Unit,
    onAddressClick: () -> Unit,
) {
    Surface(
        color = MaterialTheme.colorScheme.surface,
        tonalElevation = 1.dp,
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 9.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Box(
                modifier = Modifier
                    .size(34.dp)
                    .clip(CircleShape)
                    .background(MaterialTheme.colorScheme.primary),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    text = "AI",
                    color = MaterialTheme.colorScheme.onPrimary,
                    style = MaterialTheme.typography.labelLarge,
                    fontWeight = FontWeight.Bold,
                )
            }
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "智能导购",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    maxLines = 1,
                )
                Text(
                    text = "先筛选，再帮你看取舍",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            BadgedBox(
                badge = {
                    if (historyCount > 0) {
                        Badge { Text(historyCount.coerceAtMost(99).toString()) }
                    }
                },
            ) {
                IconButton(onClick = onHistoryClick) {
                    Icon(
                        painter = painterResource(R.drawable.ic_history_24),
                        contentDescription = "历史需求",
                    )
                }
            }
            IconButton(onClick = onAddressClick) {
                Icon(
                    painter = painterResource(R.drawable.ic_location_24),
                    contentDescription = "地址",
                )
            }
            BadgedBox(
                badge = {
                    if (cartItemCount > 0) {
                        Badge { Text(cartItemCount.toString()) }
                    }
                },
            ) {
                IconButton(onClick = onCartClick) {
                    Icon(
                        painter = painterResource(R.drawable.ic_cart_24),
                        contentDescription = "购物车",
                    )
                }
            }
        }
    }
}

@Composable
fun HistoryRequestsDialog(
    messages: List<ChatMessageUiModel>,
    onDismiss: () -> Unit,
) {
    val requests = messages.filter { it.isUser }.takeLast(12)
    AlertDialog(
        onDismissRequest = onDismiss,
        confirmButton = {
            TextButton(onClick = onDismiss) {
                Text("关闭")
            }
        },
        title = { Text("历史需求") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                if (requests.isEmpty()) {
                    Text(
                        text = "还没有历史需求。",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                } else {
                    requests.forEach { message ->
                        Surface(
                            modifier = Modifier.fillMaxWidth(),
                            shape = MediumShape,
                            color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.42f),
                        ) {
                            Text(
                                text = message.content,
                                modifier = Modifier.padding(12.dp),
                                style = MaterialTheme.typography.bodyMedium,
                                maxLines = 3,
                                overflow = TextOverflow.Ellipsis,
                            )
                        }
                    }
                }
            }
        },
    )
}

@Composable
fun WelcomeCard() {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = LargeShape,
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
    ) {
        Column(
            modifier = Modifier.padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text(
                text = "说出预算、场景或纠结点",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
            )
            Text(
                text = "我会根据真实商品数据给出首选、备选和可以继续追问的方向。",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
fun RequirementSummaryCard(
    content: String,
    onModifyClick: () -> Unit,
) {
    val chips = requirementChips(content)
    if (content.isBlank() && chips.isEmpty()) {
        return
    }
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = LargeShape,
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.28f)),
    ) {
        Column(
            modifier = Modifier.padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = "当前需求",
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.primary,
                    )
                    Text(
                        text = content,
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurface,
                        maxLines = 3,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                TextButton(onClick = onModifyClick) {
                    Text("修改条件")
                }
            }
            if (chips.isNotEmpty()) {
                Row(
                    modifier = Modifier.horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    chips.forEach { chip ->
                        Surface(
                            shape = SmallShape,
                            color = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.42f),
                        ) {
                            Text(
                                text = chip,
                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onPrimaryContainer,
                                maxLines = 1,
                            )
                        }
                    }
                }
            }
        }
    }
}

private enum class AssistantStage {
    Thinking,
    Answer,
    Error,
}

@Composable
fun AssistantAnswerIntroCard(
    thinking: AssistantThinkingUiModel,
    isStreaming: Boolean,
    answer: String,
    errorMessage: String?,
    products: List<ProductUiModel>,
    thinkingExpanded: Boolean,
    onToggleThinking: () -> Unit,
) {
    val hasAnswer = answer.isNotBlank()
    val hasError = !errorMessage.isNullOrBlank() && !hasAnswer
    val showThinking = !hasAnswer && !hasError && isStreaming
    if (!hasAnswer && !hasError && !showThinking) {
        return
    }
    val stage = when {
        hasAnswer -> AssistantStage.Answer
        hasError -> AssistantStage.Error
        else -> AssistantStage.Thinking
    }
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = LargeShape,
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
    ) {
        Crossfade(
            targetState = stage,
            label = "assistant-answer-stage",
        ) { target ->
            when (target) {
                AssistantStage.Thinking -> ThinkingProcessContent(
                    thinking = thinking,
                    expanded = thinkingExpanded,
                    onToggle = onToggleThinking,
                    compactWhenDone = false,
                )

                AssistantStage.Answer -> AnswerIntroContent(
                    answer = answer,
                    products = products,
                    thinking = thinking,
                    thinkingExpanded = thinkingExpanded,
                    onToggleThinking = onToggleThinking,
                )

                AssistantStage.Error -> ErrorContent(errorMessage.orEmpty())
            }
        }
    }
}

@Composable
private fun ThinkingProcessContent(
    thinking: AssistantThinkingUiModel,
    expanded: Boolean,
    onToggle: () -> Unit,
    compactWhenDone: Boolean,
) {
    val steps = thinking.lines.ifEmpty { listOf("正在理解你的需求") }.takeLast(8)
    val current = steps.lastOrNull().orEmpty()
    Column(
        modifier = Modifier.padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            if (compactWhenDone) {
                Icon(
                    painter = painterResource(R.drawable.ic_check_circle_20),
                    contentDescription = "已完成分析",
                    tint = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.size(20.dp),
                )
            } else {
                CircularProgressIndicator(
                    modifier = Modifier.size(18.dp),
                    strokeWidth = 2.dp,
                )
            }
            Column(
                modifier = Modifier
                    .weight(1f)
                    .padding(start = 10.dp),
            ) {
                Text(
                    text = if (compactWhenDone) "已完成分析" else "AI 正在为你挑选",
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold,
                )
                Text(
                    text = if (compactWhenDone) {
                        "共完成 ${steps.size} 步"
                    } else {
                        current.ifBlank { "正在分析" }
                    },
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            TextButton(onClick = onToggle) {
                Text(if (expanded) "收起" else "过程")
            }
        }
        if (expanded) {
            steps.forEachIndexed { index, step ->
                val isLatest = !compactWhenDone && index == steps.lastIndex
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    if (isLatest) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(16.dp),
                            strokeWidth = 2.dp,
                        )
                    } else {
                        Icon(
                            painter = painterResource(R.drawable.ic_check_circle_20),
                            contentDescription = "已完成",
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.size(16.dp),
                        )
                    }
                    Text(
                        text = step,
                        style = MaterialTheme.typography.bodySmall,
                        color = if (isLatest) {
                            MaterialTheme.colorScheme.onSurface
                        } else {
                            MaterialTheme.colorScheme.onSurfaceVariant
                        },
                    )
                }
            }
        }
    }
}

@Composable
private fun AnswerIntroContent(
    answer: String,
    products: List<ProductUiModel>,
    thinking: AssistantThinkingUiModel,
    thinkingExpanded: Boolean,
    onToggleThinking: () -> Unit,
) {
    Column(
        modifier = Modifier.padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        ThinkingProcessContent(
            thinking = thinking,
            expanded = thinkingExpanded,
            onToggle = onToggleThinking,
            compactWhenDone = true,
        )
        val category = products.firstNotNullOfOrNull { it.category.takeIf(String::isNotBlank) }
        Text(
            text = if (products.isNotEmpty()) {
                "为你筛选了 ${products.size} 款${category.orEmpty()}"
            } else {
                "导购建议"
            },
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.Bold,
        )
        answer
            .lineSequence()
            .map { it.trim() }
            .filter { it.isNotBlank() }
            .take(3)
            .forEach { paragraph ->
                Text(
                    text = paragraph,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface,
                )
            }
    }
}

@Composable
private fun ErrorContent(message: String) {
    Column(
        modifier = Modifier.padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Text(
            text = "请求失败",
            style = MaterialTheme.typography.titleSmall,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.error,
        )
        Text(
            text = message,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurface,
        )
    }
}

@Composable
fun RecommendationSection(
    product: ProductUiModel,
    index: Int,
    totalCount: Int,
    onProductClick: (String) -> Unit,
    onAddToCart: (String) -> Unit,
) {
    val isPrimary = index == 0
    val roleLabel = when {
        isPrimary -> "首选推荐"
        index == 1 -> "另一款备选"
        else -> "更多选择"
    }
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Column(
            modifier = Modifier.padding(horizontal = 2.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Text(
                text = roleLabel,
                style = MaterialTheme.typography.labelLarge,
                color = MaterialTheme.colorScheme.primary,
                fontWeight = FontWeight.Bold,
            )
            Text(
                text = if (isPrimary) {
                    "可以先看 ${product.brand} ${product.displayTitleShort}"
                } else {
                    "${roleLabel}：${product.brand} ${product.displayTitleShort}"
                },
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.SemiBold,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
            val reason = product.displayReason.ifBlank {
                product.displayTags.take(3).joinToString(" · ").takeIf { it.isNotBlank() }.orEmpty()
            }
            if (reason.isNotBlank()) {
                Text(
                    text = reason,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 3,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
        ProductCard(
            product = product,
            onClick = onProductClick,
            onAddToCart = onAddToCart,
            rank = index + 1,
            totalCount = totalCount,
            isPrimary = isPrimary,
            roleLabel = roleLabel,
        )
    }
}

@Composable
fun FinalComparisonSummary(products: List<ProductUiModel>) {
    if (products.isEmpty()) {
        return
    }
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = LargeShape,
        color = MaterialTheme.colorScheme.surface,
    ) {
        Column(
            modifier = Modifier.padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Text(
                text = "一句话对比",
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.Bold,
            )
            val names = products.take(3).map { it.brand.ifBlank { it.displayTitleShort } }
            Text(
                text = when (names.size) {
                    1 -> "可以先查看 ${names[0]} 的详情，再决定是否加入购物车。"
                    2 -> "首选先看 ${names[0]}，也可以把 ${names[1]} 作为备选一起比较。"
                    else -> "首选先看 ${names[0]}，备选可比较 ${names.drop(1).joinToString("、")}。"
                },
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
fun EmptyProductsCard() {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = LargeShape,
        color = MaterialTheme.colorScheme.surface,
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Text(
                text = "暂时没有找到完全符合条件的商品",
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.Bold,
            )
            Text(
                text = "可以尝试放宽预算或调整筛选条件。",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
fun FollowUpSuggestionChips(
    products: List<ProductUiModel>,
    onSend: (String) -> Unit,
    onCompare: () -> Unit,
) {
    if (products.isEmpty()) {
        return
    }
    val prompts = buildFollowUpPrompts(products)
    Row(
        modifier = Modifier.horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        prompts.forEach { action ->
            val isCompare = action.text == "对比这几款"
            Surface(
                shape = SmallShape,
                color = MaterialTheme.colorScheme.surface,
                border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.28f)),
                modifier = Modifier.clickable {
                    if (isCompare) onCompare() else onSend(action.text)
                },
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 10.dp, vertical = 7.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    Icon(
                        painter = painterResource(action.iconRes),
                        contentDescription = action.text,
                        modifier = Modifier.size(16.dp),
                        tint = MaterialTheme.colorScheme.primary,
                    )
                    Text(
                        text = action.text,
                        style = MaterialTheme.typography.labelMedium,
                        maxLines = 1,
                    )
                }
            }
        }
    }
}

@Composable
fun ProductCompareCard(products: List<ProductUiModel>) {
    if (products.size < 2) {
        return
    }
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = LargeShape,
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
    ) {
        Column(
            modifier = Modifier.padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text(
                text = "核心字段对比",
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.Bold,
            )
            products.take(3).forEachIndexed { index, product ->
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text(
                        text = "${index + 1}",
                        style = MaterialTheme.typography.labelLarge,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.primary,
                    )
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = product.displayTitleShort,
                            style = MaterialTheme.typography.bodyMedium,
                            fontWeight = FontWeight.SemiBold,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                        Text(
                            text = listOf(product.brand, "¥${com.yourteam.ecommerceguider.ui.components.formatPrice(product.price)}")
                                .filter { it.isNotBlank() }
                                .joinToString(" · "),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            maxLines = 1,
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun CartCheckoutBar(
    cartItemCount: Int,
    onCartClick: () -> Unit,
    onCheckoutClick: () -> Unit,
) {
    if (cartItemCount <= 0) {
        return
    }
    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = MaterialTheme.colorScheme.surface,
        tonalElevation = 1.dp,
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(
                text = "已选 $cartItemCount 件",
                modifier = Modifier.weight(1f),
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.SemiBold,
            )
            OutlinedButton(onClick = onCartClick, shape = MediumShape) {
                Text("查看购物车")
            }
            Button(
                onClick = onCheckoutClick,
                shape = MediumShape,
                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary),
            ) {
                Text("去结算")
            }
        }
    }
}

private data class FollowUpAction(
    val text: String,
    val iconRes: Int,
)

private fun requirementChips(content: String): List<String> {
    val blocked = setOf("换一批", "再来一批", "重新推荐", "对比这几款", "查看差异")
    return content
        .split("，", ",", "。", "；", ";", "|", "｜", " ")
        .map { it.trim() }
        .filter { it.length in 2..14 }
        .filterNot { it in blocked }
        .filterNot { it.startsWith("正在") || it.contains("分析") || it.contains("商品库") }
        .distinct()
        .take(4)
}

private fun buildFollowUpPrompts(products: List<ProductUiModel>): List<FollowUpAction> {
    val hasPrice = products.any { it.price > 0.0 }
    return buildList {
        add(FollowUpAction("换一批", R.drawable.ic_refresh_20))
        if (hasPrice) add(FollowUpAction("更看重性价比", R.drawable.ic_attach_money_20))
        add(FollowUpAction("对比这几款", R.drawable.ic_compare_20))
    }.take(3)
}

@Preview(showBackground = true)
@Composable
private fun AssistantThinkingPreview() {
    EcommerceGuiderTheme {
        AssistantAnswerIntroCard(
            thinking = AssistantThinkingUiModel(
                status = AssistantThinkingStatus.Streaming,
                lines = listOf("正在理解你的需求", "正在商品库中查找", "正在比较候选商品"),
            ),
            isStreaming = true,
            answer = "",
            errorMessage = null,
            products = emptyList(),
            thinkingExpanded = true,
            onToggleThinking = {},
        )
    }
}

@Preview(showBackground = true)
@Composable
private fun RecommendationSectionPreview() {
    EcommerceGuiderTheme {
        RecommendationSection(
            product = PreviewData.sampleProducts.first(),
            index = 0,
            totalCount = 3,
            onProductClick = {},
            onAddToCart = {},
        )
    }
}
