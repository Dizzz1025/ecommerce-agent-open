package com.yourteam.ecommerceguider.ui.screens.chat.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.yourteam.ecommerceguider.R
import com.yourteam.ecommerceguider.data.model.AssistantProcessStageStatus
import com.yourteam.ecommerceguider.data.model.AssistantProcessStageUiModel
import com.yourteam.ecommerceguider.data.model.AssistantThinkingStatus
import com.yourteam.ecommerceguider.data.model.AssistantThinkingUiModel
import com.yourteam.ecommerceguider.data.model.ChatMessageUiModel
import com.yourteam.ecommerceguider.data.model.ProductUiModel
import com.yourteam.ecommerceguider.data.model.RecommendationSectionUiModel
import com.yourteam.ecommerceguider.data.model.SpecSelectionOptionUiModel
import com.yourteam.ecommerceguider.data.model.SpecSelectionUiModel
import com.yourteam.ecommerceguider.theme.EcommerceGuiderTheme
import com.yourteam.ecommerceguider.ui.components.ProductCard
import com.yourteam.ecommerceguider.ui.components.SpatialAccent
import com.yourteam.ecommerceguider.ui.components.SpatialAccentBlue
import com.yourteam.ecommerceguider.ui.components.SpatialAccentMuted
import com.yourteam.ecommerceguider.ui.components.SpatialGlassBorderColor
import com.yourteam.ecommerceguider.ui.components.SpatialGlassColor
import com.yourteam.ecommerceguider.ui.components.SpatialGlassColorDock
import com.yourteam.ecommerceguider.ui.components.SpatialGlassColorSoft
import com.yourteam.ecommerceguider.ui.components.SpatialGlassColorStrong
import com.yourteam.ecommerceguider.ui.components.SpatialGlassControl
import com.yourteam.ecommerceguider.ui.components.SpatialGlassControlMuted
import com.yourteam.ecommerceguider.ui.components.SpatialIconMuted
import com.yourteam.ecommerceguider.ui.components.SpatialIconNeutral
import com.yourteam.ecommerceguider.ui.components.SpatialPrimaryGradient
import com.yourteam.ecommerceguider.ui.components.SpatialTextBody
import com.yourteam.ecommerceguider.ui.components.SpatialTextPrimary
import com.yourteam.ecommerceguider.ui.components.SpatialTextSecondary
import com.yourteam.ecommerceguider.ui.components.formatPrice
import com.yourteam.ecommerceguider.ui.components.spatialGlass
import com.yourteam.ecommerceguider.utils.PreviewData

private val LargeShape = RoundedCornerShape(26.dp)
private val MediumShape = RoundedCornerShape(20.dp)
private val SmallShape = RoundedCornerShape(999.dp)

@Composable
fun GuideTopBar(
    cartItemCount: Int,
    historyCount: Int,
    onHistoryClick: () -> Unit,
    onCartClick: () -> Unit,
    onAddressClick: () -> Unit,
) {
    Surface(
        color = Color.Transparent,
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 12.dp, vertical = 8.dp)
                .spatialGlass(
                    shape = RoundedCornerShape(28.dp),
                    fillColor = SpatialGlassColorDock,
                    elevation = 3.dp,
                )
                .padding(horizontal = 14.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Box(
                modifier = Modifier
                    .size(34.dp)
                    .clip(CircleShape)
                    .background(SpatialPrimaryGradient),
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
                    color = SpatialTextSecondary,
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
                        tint = SpatialIconMuted,
                    )
                }
            }
            IconButton(onClick = onAddressClick) {
                Icon(
                    painter = painterResource(R.drawable.ic_location_24),
                    contentDescription = "地址",
                    tint = SpatialIconMuted,
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
                        tint = SpatialAccentBlue,
                    )
                }
            }
        }
    }
}

@Composable
fun HistoryRequestsDialog(
    messages: List<ChatMessageUiModel>,
    recommendationSections: List<RecommendationSectionUiModel>,
    onProductClick: (String) -> Unit,
    onAddToCart: (ProductUiModel, String) -> Unit,
    activeSpecSelection: SpecSelectionUiModel? = null,
    onSpecOptionClick: (SpecSelectionUiModel, SpecSelectionOptionUiModel) -> Unit = { _, _ -> },
    onDismiss: () -> Unit,
) {
    val turns = messages
        .filter { it.isUser }
        .map { userMessage ->
            ChatHistoryTurn(
                userMessage = userMessage,
                assistantMessage = messages.firstOrNull { message ->
                    !message.isUser && message.turnId == userMessage.turnId
                },
                sections = recommendationSections.filter { section ->
                    section.turnId == userMessage.turnId
                },
            )
        }
        .takeLast(12)
    AlertDialog(
        onDismissRequest = onDismiss,
        confirmButton = {
            TextButton(onClick = onDismiss) {
                Text("关闭")
            }
        },
        title = { Text("历史需求") },
        text = {
            Column(
                modifier = Modifier.verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                if (turns.isEmpty()) {
                    Text(
                        text = "还没有历史需求。",
                        style = MaterialTheme.typography.bodyMedium,
                        color = SpatialTextSecondary,
                    )
                } else {
                    turns.forEachIndexed { index, turn ->
                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text(
                                text = "第 ${index + 1} 轮",
                                style = MaterialTheme.typography.labelMedium,
                                fontWeight = FontWeight.SemiBold,
                                color = SpatialAccent,
                            )
                            HistoryTextBlock(label = "用户", text = turn.userMessage.content)
                            turn.assistantMessage?.content
                                ?.takeIf { it.isNotBlank() }
                                ?.let { assistantText ->
                                    HistoryTextBlock(label = "助手", text = assistantText)
                                }
                            turn.sections.forEach { section ->
                                HistoryRecommendationBlock(
                                    section = section,
                                    onProductClick = onProductClick,
                                    onAddToCart = onAddToCart,
                                    activeSpecSelection = activeSpecSelection,
                                    onSpecOptionClick = onSpecOptionClick,
                                )
                            }
                        }
                    }
                }
            }
        },
    )
}

private data class ChatHistoryTurn(
    val userMessage: ChatMessageUiModel,
    val assistantMessage: ChatMessageUiModel?,
    val sections: List<RecommendationSectionUiModel>,
)

@Composable
private fun HistoryTextBlock(
    label: String,
    text: String,
) {
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .spatialGlass(shape = MediumShape, fillColor = SpatialGlassColorSoft, elevation = 4.dp),
        shape = MediumShape,
        color = Color.Transparent,
    ) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(4.dp),
        ) {
            Text(
                text = label,
                style = MaterialTheme.typography.labelSmall,
                fontWeight = FontWeight.SemiBold,
                color = SpatialAccent,
            )
            Text(
                text = text,
                style = MaterialTheme.typography.bodyMedium,
                maxLines = 6,
                overflow = TextOverflow.Ellipsis,
            )
        }
    }
}

@Composable
private fun HistoryRecommendationBlock(
    section: RecommendationSectionUiModel,
    onProductClick: (String) -> Unit,
    onAddToCart: (ProductUiModel, String) -> Unit,
    activeSpecSelection: SpecSelectionUiModel? = null,
    onSpecOptionClick: (SpecSelectionUiModel, SpecSelectionOptionUiModel) -> Unit = { _, _ -> },
) {
    val inlineSpecSelection = activeSpecSelection?.takeIf { selection ->
        selection.source == "product_card" &&
            selection.anchorRecommendationId == section.stableKey
    }
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .spatialGlass(shape = MediumShape, fillColor = SpatialGlassColor, elevation = 4.dp),
        shape = MediumShape,
        color = Color.Transparent,
    ) {
        Column(
            modifier = Modifier.padding(10.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(
                text = section.optionLabel,
                style = MaterialTheme.typography.labelMedium,
                fontWeight = FontWeight.SemiBold,
                color = SpatialAccent,
            )
            section.text
                .takeIf { it.isNotBlank() }
                ?.let { text ->
                    Text(
                        text = text,
                        style = MaterialTheme.typography.bodySmall,
                        color = SpatialTextSecondary,
                    )
                }
            section.tradeOff
                ?.takeIf { it.isNotBlank() && !it.equals("null", ignoreCase = true) }
                ?.let { tradeOff ->
                    Text(
                        text = "需要注意：$tradeOff",
                        style = MaterialTheme.typography.bodySmall,
                        color = SpatialTextSecondary,
                    )
                }
            section.product?.let { product ->
                ProductCard(
                    product = product,
                    onClick = onProductClick,
                    onAddToCart = { selectedProduct -> onAddToCart(selectedProduct, section.stableKey) },
                    rank = section.sectionIndex,
                    isPrimary = false,
                    roleLabel = section.optionLabel,
                    showRecommendationReason = false,
                )
            }
            inlineSpecSelection?.let { selection ->
                InlineSpecSelectionPanel(
                    selection = selection,
                    onOptionClick = { option -> onSpecOptionClick(selection, option) },
                )
            }
        }
    }
}

@Composable
fun WelcomeCard() {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .spatialGlass(shape = LargeShape, fillColor = SpatialGlassColorStrong, elevation = 5.dp),
        shape = LargeShape,
        colors = CardDefaults.cardColors(containerColor = Color.Transparent),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
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
                color = SpatialTextSecondary,
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
        modifier = Modifier
            .fillMaxWidth()
            .spatialGlass(shape = LargeShape, fillColor = SpatialGlassColor, elevation = 4.dp),
        shape = LargeShape,
        color = Color.Transparent,
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
                            color = SpatialAccent,
                    )
                    Text(
                        text = content,
                        style = MaterialTheme.typography.bodyMedium,
                        color = SpatialTextSecondary,
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
                            color = SpatialAccentMuted,
                        ) {
                            Text(
                                text = chip,
                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                                style = MaterialTheme.typography.labelSmall,
                                color = SpatialAccent,
                                maxLines = 1,
                            )
                        }
                    }
                }
            }
        }
    }
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
    val hasAnswer = answer.isNotBlank() || products.isNotEmpty()
    val hasError = !errorMessage.isNullOrBlank()
    val hasThinking = thinking.status != AssistantThinkingStatus.Idle &&
        (thinking.stages.isNotEmpty() || isStreaming || hasAnswer)
    if (!hasError && !hasThinking) {
        return
    }
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .spatialGlass(shape = LargeShape, fillColor = SpatialGlassColorStrong, elevation = 5.dp),
        shape = LargeShape,
        colors = CardDefaults.cardColors(containerColor = Color.Transparent),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
    ) {
        ThinkingProcessContent(
            thinking = thinking,
            expanded = thinkingExpanded,
            onToggle = onToggleThinking,
            finalAnswer = answer,
        )
        if (hasError && !isStreaming) {
            ErrorContent(message = errorMessage.orEmpty(), compact = true)
        }
    }
}

@Composable
fun SpecSelectionCard(
    selection: SpecSelectionUiModel,
    onOptionClick: (SpecSelectionOptionUiModel) -> Unit,
) {
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .spatialGlass(shape = LargeShape, fillColor = SpatialGlassColorStrong, elevation = 5.dp),
        shape = LargeShape,
        color = Color.Transparent,
    ) {
        Column(
            modifier = Modifier.padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text(
                text = "请选择规格",
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.Bold,
            )
            Text(
                text = selection.productName,
                style = MaterialTheme.typography.bodyMedium,
                color = SpatialTextSecondary,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                selection.options.forEach { option ->
                    val chosen = selection.selectedSkuId == option.skuId
                    val locked = selection.selectedSkuId != null
                    val enabled = option.available && option.stock != 0 && !locked
                    OutlinedButton(
                        onClick = { onOptionClick(option) },
                        enabled = enabled,
                        modifier = Modifier.fillMaxWidth(),
                        shape = MediumShape,
                        border = BorderStroke(
                            width = 1.dp,
                            color = if (chosen) {
                                SpatialAccent
                            } else {
                                SpatialGlassBorderColor
                            },
                        ),
                        colors = ButtonDefaults.outlinedButtonColors(
                            containerColor = if (chosen) {
                                SpatialAccentMuted
                            } else {
                                SpatialGlassControl
                            },
                            contentColor = SpatialTextPrimary,
                            disabledContainerColor = SpatialGlassControlMuted,
                        ),
                        contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 12.dp, vertical = 8.dp),
                    ) {
                        Column(
                            modifier = Modifier.weight(1f),
                            verticalArrangement = Arrangement.spacedBy(2.dp),
                        ) {
                            Text(
                                text = option.specText,
                                style = MaterialTheme.typography.labelLarge,
                                maxLines = 2,
                                overflow = TextOverflow.Ellipsis,
                            )
                            if (option.stock == 0) {
                                Text(
                                    text = "暂时无库存",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = SpatialTextSecondary,
                                    maxLines = 1,
                                )
                            }
                        }
                        Text(
                            text = if (chosen) "已加入" else "¥${formatPrice(option.price)}",
                            style = MaterialTheme.typography.labelLarge,
                            color = if (chosen) {
                                SpatialAccent
                            } else {
                                SpatialTextPrimary
                            },
                            maxLines = 1,
                        )
                    }
                }
            }
            Text(
                text = "点击规格后将直接加入购物车",
                style = MaterialTheme.typography.bodySmall,
                color = SpatialTextSecondary,
            )
        }
    }
}

@Composable
private fun InlineSpecSelectionPanel(
    selection: SpecSelectionUiModel,
    onOptionClick: (SpecSelectionOptionUiModel) -> Unit,
) {
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 2.dp)
            .spatialGlass(shape = MediumShape, fillColor = SpatialGlassColorSoft, elevation = 3.dp),
        shape = MediumShape,
        color = Color.Transparent,
    ) {
        Column(
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 11.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(
                text = "选择规格",
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.SemiBold,
                color = SpatialTextPrimary,
            )
            selection.options.forEach { option ->
                val chosen = selection.selectedSkuId == option.skuId
                val enabled = option.available && option.stock != 0 && selection.selectedSkuId == null
                OutlinedButton(
                    onClick = { onOptionClick(option) },
                    enabled = enabled,
                    modifier = Modifier.fillMaxWidth(),
                    shape = MediumShape,
                    border = BorderStroke(
                        width = 1.dp,
                        color = if (chosen) SpatialAccent else SpatialGlassBorderColor,
                    ),
                    colors = ButtonDefaults.outlinedButtonColors(
                        containerColor = if (chosen) SpatialAccentMuted else SpatialGlassControl,
                        contentColor = SpatialTextPrimary,
                        disabledContainerColor = SpatialGlassControlMuted,
                    ),
                    contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 12.dp, vertical = 8.dp),
                ) {
                    Text(
                        text = option.specText,
                        modifier = Modifier.weight(1f),
                        style = MaterialTheme.typography.labelLarge,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis,
                    )
                    Text(
                        text = if (option.stock == 0) "暂无库存" else "¥${formatPrice(option.price)}",
                        style = MaterialTheme.typography.labelLarge,
                        color = if (option.stock == 0) SpatialTextSecondary else SpatialTextPrimary,
                        maxLines = 1,
                    )
                }
            }
        }
    }
}

@Composable
private fun ThinkingProcessContent(
    thinking: AssistantThinkingUiModel,
    expanded: Boolean,
    onToggle: () -> Unit,
    finalAnswer: String,
) {
    val stages = thinking.stages
    val completedCount = stages.count { it.status == AssistantProcessStageStatus.Completed }
        .takeIf { it > 0 }
        ?: stages.count { it.status != AssistantProcessStageStatus.Pending }
    val runningStage = stages.firstOrNull { it.status == AssistantProcessStageStatus.Running }
    val elapsedText = formatDuration(thinking.totalElapsedMs, total = true)
    val isDone = thinking.status == AssistantThinkingStatus.Done
    val isFailed = thinking.status == AssistantThinkingStatus.Failed
    val isGenerating = thinking.status == AssistantThinkingStatus.Generating || thinking.isGeneratingResponse
    val title = when {
        isFailed -> "分析未完成 · 已用时 $elapsedText"
        isDone -> "已完成分析 · 用时 $elapsedText"
        isGenerating -> "正在生成推荐结论 · $elapsedText"
        else -> "正在分析 · $elapsedText"
    }
    val subtitle = when {
        isDone -> "共完成 $completedCount 步"
        isFailed -> "已完成 $completedCount 步"
        isGenerating -> if (thinking.responseStreamSupported) "正在生成推荐结论" else "正在生成推荐结论"
        else -> runningStage?.displayLabel ?: "正在理解你的需求"
    }
    Column(
        modifier = Modifier.padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            if (isDone) {
                Box(
                    modifier = Modifier
                        .size(28.dp)
                        .clip(CircleShape)
                        .background(SpatialPrimaryGradient),
                    contentAlignment = Alignment.Center,
                ) {
                    Icon(
                        painter = painterResource(R.drawable.ic_check_circle_20),
                        contentDescription = "已完成分析",
                        tint = Color.White,
                        modifier = Modifier.size(18.dp),
                    )
                }
            } else if (isFailed) {
                Box(
                    modifier = Modifier
                        .size(28.dp)
                        .clip(CircleShape)
                        .background(MaterialTheme.colorScheme.error.copy(alpha = 0.12f)),
                    contentAlignment = Alignment.Center,
                ) {
                    Text(
                        text = "!",
                        style = MaterialTheme.typography.labelLarge,
                        color = MaterialTheme.colorScheme.error,
                        fontWeight = FontWeight.Bold,
                    )
                }
            } else {
                CircularProgressIndicator(
                    modifier = Modifier.size(18.dp),
                    strokeWidth = 2.dp,
                    color = SpatialAccent,
                )
            }
            Column(
                modifier = Modifier
                    .weight(1f)
                    .padding(start = 10.dp),
            ) {
                Text(
                    text = title,
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold,
                )
                Text(
                    text = subtitle,
                    style = MaterialTheme.typography.bodySmall,
                    color = SpatialTextSecondary,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            TextButton(
                onClick = onToggle,
                shape = SmallShape,
            ) {
                Text(if (expanded) "收起" else "查看过程")
            }
        }

        if (isGenerating) {
            GenerationPreview(
                text = thinking.previewText,
                streamSupported = thinking.responseStreamSupported,
            )
        }

        if (isDone && finalAnswer.isNotBlank()) {
            AnswerPreviewText(text = finalAnswer)
        }

        if (expanded) {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                stages.forEach { stage ->
                    ProcessStageRow(stage = stage)
                }
            }
        }
    }
}

@Composable
private fun ProcessStageRow(stage: AssistantProcessStageUiModel) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        when (stage.status) {
            AssistantProcessStageStatus.Running -> {
                CircularProgressIndicator(
                    modifier = Modifier.size(15.dp),
                    strokeWidth = 2.dp,
                    color = SpatialAccentBlue,
                )
            }
            AssistantProcessStageStatus.Completed -> {
                Icon(
                    painter = painterResource(R.drawable.ic_check_circle_20),
                    contentDescription = "已完成",
                    tint = SpatialTextSecondary,
                    modifier = Modifier.size(15.dp),
                )
            }
            AssistantProcessStageStatus.Failed -> {
                Box(
                    modifier = Modifier
                        .size(15.dp)
                        .clip(CircleShape)
                        .background(MaterialTheme.colorScheme.error.copy(alpha = 0.16f)),
                    contentAlignment = Alignment.Center,
                ) {
                    Text("!", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.error)
                }
            }
            AssistantProcessStageStatus.Pending -> {
                Box(
                    modifier = Modifier
                        .size(7.dp)
                        .clip(CircleShape)
                        .background(SpatialTextSecondary.copy(alpha = 0.35f)),
                )
            }
        }
        Text(
            text = stage.displayLabel,
            modifier = Modifier.weight(1f),
            style = MaterialTheme.typography.bodySmall,
            color = if (stage.status == AssistantProcessStageStatus.Running) {
                SpatialTextPrimary
            } else {
                SpatialTextSecondary
            },
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
        stage.durationMs?.let { duration ->
            Text(
                text = formatDuration(duration),
                style = MaterialTheme.typography.bodySmall,
                color = SpatialTextSecondary,
                maxLines = 1,
            )
        }
    }
}

@Composable
private fun GenerationPreview(
    text: String,
    streamSupported: Boolean,
) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = MediumShape,
        color = SpatialGlassColorSoft,
        border = BorderStroke(1.dp, SpatialGlassBorderColor),
    ) {
        Column(
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 11.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(
                text = "正在生成推荐结论",
                style = MaterialTheme.typography.labelMedium,
                fontWeight = FontWeight.SemiBold,
                color = SpatialAccentBlue,
            )
            if (text.isNotBlank()) {
                AnswerPreviewText(text = text)
            } else {
                StaticSkeletonPreview(streamSupported = streamSupported)
            }
        }
    }
}

@Composable
private fun StaticSkeletonPreview(streamSupported: Boolean) {
    Column(verticalArrangement = Arrangement.spacedBy(7.dp)) {
        Text(
            text = if (streamSupported) "结论生成中" else "模型正在整理最终回复",
            style = MaterialTheme.typography.bodySmall,
            color = SpatialTextSecondary,
        )
        listOf(0.96f, 0.78f, 0.58f).forEach { fraction ->
            Box(
                modifier = Modifier
                    .fillMaxWidth(fraction)
                    .height(8.dp)
                    .clip(SmallShape)
                    .background(SpatialGlassControlMuted),
            )
        }
    }
}

@Composable
private fun AnswerPreviewText(text: String) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        text.lineSequence()
            .map { it.trim() }
            .filter { it.isNotBlank() }
            .forEach { paragraph ->
                Text(
                    text = paragraph,
                    style = MaterialTheme.typography.bodyMedium,
                    color = SpatialTextBody,
                )
            }
    }
}

@Composable
private fun ErrorContent(message: String, compact: Boolean = false) {
    Column(
        modifier = Modifier.padding(horizontal = 16.dp, vertical = if (compact) 0.dp else 16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        if (!compact) {
            Text(
                text = "请求失败",
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.error,
            )
        }
        Text(
            text = message,
            style = MaterialTheme.typography.bodyMedium,
            color = SpatialTextPrimary,
        )
    }
}

private fun formatDuration(durationMs: Long, total: Boolean = false): String {
    return if (durationMs < 1_000L) {
        "$durationMs 毫秒"
    } else {
        val seconds = durationMs / 1000.0
        if (total) {
            String.format("%.1f 秒", seconds)
        } else {
            String.format("%.1f 秒", seconds)
        }
    }
}

@Composable
fun RecommendationSection(
    product: ProductUiModel,
    index: Int,
    totalCount: Int,
    onProductClick: (String) -> Unit,
    onAddToCart: (ProductUiModel, String) -> Unit,
    activeSpecSelection: SpecSelectionUiModel? = null,
    onSpecOptionClick: (SpecSelectionUiModel, SpecSelectionOptionUiModel) -> Unit = { _, _ -> },
) {
    val presentation = product.presentation
    val roleLabel = presentation?.optionLabel?.takeIf { it.isNotBlank() } ?: when (index) {
        0 -> "方案一"
        1 -> "方案二"
        2 -> "方案三"
        else -> "方案${index + 1}"
    }
    RecommendationSection(
        section = RecommendationSectionUiModel(
            turnId = "snapshot",
            sectionIndex = index + 1,
            skuId = product.skuId,
            optionLabel = roleLabel,
            text = product.displayReason,
            reason = presentation?.reason,
            tradeOff = presentation?.tradeOff,
            productName = product.displayTitleShort,
            brand = product.brand,
            product = product,
            done = true,
        ),
        totalCount = totalCount,
        onProductClick = onProductClick,
        onAddToCart = onAddToCart,
        activeSpecSelection = activeSpecSelection,
        onSpecOptionClick = onSpecOptionClick,
    )
}

@Composable
fun RecommendationSection(
    section: RecommendationSectionUiModel,
    totalCount: Int,
    onProductClick: (String) -> Unit,
    onAddToCart: (ProductUiModel, String) -> Unit,
    activeSpecSelection: SpecSelectionUiModel? = null,
    onSpecOptionClick: (SpecSelectionUiModel, SpecSelectionOptionUiModel) -> Unit = { _, _ -> },
) {
    val product = section.product
    val inlineSpecSelection = activeSpecSelection?.takeIf { selection ->
        selection.source == "product_card" &&
            selection.anchorRecommendationId == section.stableKey
    }
    val roleLabel = section.optionLabel.ifBlank {
        when (section.sectionIndex) {
            1 -> "方案一"
            2 -> "方案二"
            3 -> "方案三"
            else -> "方案${section.sectionIndex}"
        }
    }
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .spatialGlass(
                shape = LargeShape,
                fillColor = if (section.sectionIndex == 1) {
                    SpatialGlassColorStrong
                } else {
                    SpatialGlassColor
                },
                elevation = if (section.sectionIndex == 1) 6.dp else 4.dp,
            ),
        shape = LargeShape,
        color = Color.Transparent,
    ) {
        Column(
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 17.dp),
            verticalArrangement = Arrangement.spacedBy(13.dp),
        ) {
            Surface(
                shape = SmallShape,
                color = Color.Transparent,
                modifier = Modifier.background(SpatialPrimaryGradient, SmallShape),
            ) {
                Text(
                    text = roleLabel,
                    modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp),
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = FontWeight.Bold,
                    color = Color.White,
                    maxLines = 1,
                )
            }
            val title = section.productName
                ?: product?.displayTitleShort
                ?: section.brand
            if (!title.isNullOrBlank()) {
                Text(
                    text = title,
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.SemiBold,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            section.text
                .lineSequence()
                .map { it.trim() }
                .filter { it.isNotBlank() }
                .forEach { paragraph ->
                    Text(
                        text = paragraph,
                        style = MaterialTheme.typography.bodyMedium,
                        color = SpatialTextBody,
                    )
                }
            section.tradeOff
                ?.takeIf { it.isNotBlank() && !it.equals("null", ignoreCase = true) }
                ?.let { tradeOff ->
                    Text(
                        text = "需要注意：$tradeOff",
                        style = MaterialTheme.typography.bodyMedium,
                        color = SpatialTextSecondary,
                    )
                }
            if (!section.done && product == null) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(14.dp),
                        strokeWidth = 2.dp,
                    )
                    Text(
                        text = "正在继续生成",
                        style = MaterialTheme.typography.bodySmall,
                        color = SpatialTextSecondary,
                    )
                }
            }
            product?.let {
                ProductCard(
                    product = it,
                    onClick = onProductClick,
                    onAddToCart = { selectedProduct ->
                        onAddToCart(selectedProduct, section.stableKey)
                    },
                    rank = section.sectionIndex,
                    totalCount = totalCount,
                    isPrimary = section.sectionIndex == 1,
                    roleLabel = roleLabel,
                    showRecommendationReason = false,
                )
            }
            inlineSpecSelection?.let { selection ->
                InlineSpecSelectionPanel(
                    selection = selection,
                    onOptionClick = { option -> onSpecOptionClick(selection, option) },
                )
            }
        }
    }
}

@Composable
fun FinalComparisonSummary(products: List<ProductUiModel>) {
    if (products.isEmpty()) {
        return
    }
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .spatialGlass(shape = LargeShape, fillColor = SpatialGlassColor, elevation = 4.dp),
        shape = LargeShape,
        color = Color.Transparent,
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(
                text = "一句话对比",
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.Bold,
                color = SpatialTextPrimary,
            )
            val names = products.take(3).map { it.brand.ifBlank { it.displayTitleShort } }
            Text(
                text = when (names.size) {
                    1 -> "可以先查看 ${names[0]} 的详情，再决定是否加入购物车。"
                    2 -> "${names[0]} 和 ${names[1]} 可以放在一起比较价格、亮点和适用场景。"
                    else -> "这几款可以从价格、亮点和适用场景一起比较：${names.joinToString("、")}。"
                },
                style = MaterialTheme.typography.bodyMedium,
                color = SpatialTextSecondary,
            )
        }
    }
}

@Composable
fun EmptyProductsCard() {
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .spatialGlass(shape = LargeShape, fillColor = SpatialGlassColor, elevation = 4.dp),
        shape = LargeShape,
        color = Color.Transparent,
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
                color = SpatialTextSecondary,
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
                color = SpatialGlassControl,
                border = BorderStroke(1.dp, SpatialGlassBorderColor),
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
                        tint = SpatialIconNeutral,
                    )
                    Text(
                        text = action.text,
                        style = MaterialTheme.typography.labelMedium,
                        color = SpatialTextPrimary,
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
        modifier = Modifier
            .fillMaxWidth()
            .spatialGlass(shape = LargeShape, fillColor = SpatialGlassColor, elevation = 4.dp),
        shape = LargeShape,
        colors = CardDefaults.cardColors(containerColor = Color.Transparent),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
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
                val presentation = product.presentation?.takeIf { it.type == "comparison" }
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text(
                        text = "商品${index + 1}",
                        style = MaterialTheme.typography.labelLarge,
                        fontWeight = FontWeight.Bold,
                        color = SpatialAccent,
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
                            color = SpatialTextSecondary,
                            maxLines = 1,
                        )
                        presentation?.summary?.takeIf { it.isNotBlank() }?.let { summary ->
                            Text(
                                text = summary,
                                style = MaterialTheme.typography.bodySmall,
                                color = SpatialTextSecondary,
                                maxLines = 2,
                                overflow = TextOverflow.Ellipsis,
                            )
                        }
                        if (!presentation?.advantages.isNullOrEmpty()) {
                            Text(
                                text = "优势：${presentation?.advantages.orEmpty().take(3).joinToString(" · ")}",
                                style = MaterialTheme.typography.bodySmall,
                                color = SpatialTextSecondary,
                                maxLines = 2,
                                overflow = TextOverflow.Ellipsis,
                            )
                        }
                        presentation?.suitableFor?.takeIf { it.isNotBlank() }?.let { suitable ->
                            Text(
                                text = "适合：$suitable",
                                style = MaterialTheme.typography.bodySmall,
                                color = SpatialTextSecondary,
                                maxLines = 2,
                                overflow = TextOverflow.Ellipsis,
                            )
                        }
                        presentation?.tradeOff?.takeIf { it.isNotBlank() }?.let { tradeOff ->
                            Text(
                                text = "取舍：$tradeOff",
                                style = MaterialTheme.typography.bodySmall,
                                color = SpatialTextSecondary,
                                maxLines = 2,
                                overflow = TextOverflow.Ellipsis,
                            )
                        }
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
        modifier = Modifier
            .fillMaxWidth()
            .padding(bottom = 8.dp)
            .spatialGlass(shape = MediumShape, fillColor = SpatialGlassColorDock, elevation = 4.dp),
        color = Color.Transparent,
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
            OutlinedButton(
                onClick = onCartClick,
                shape = MediumShape,
                border = BorderStroke(1.dp, SpatialGlassBorderColor),
                colors = ButtonDefaults.outlinedButtonColors(
                    containerColor = SpatialGlassControl,
                    contentColor = SpatialAccent,
                ),
            ) {
                Text("查看购物车")
            }
            Button(
                onClick = onCheckoutClick,
                shape = MediumShape,
                modifier = Modifier.background(SpatialPrimaryGradient, MediumShape),
                colors = ButtonDefaults.buttonColors(containerColor = Color.Transparent),
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
                status = AssistantThinkingStatus.Running,
                stages = listOf(
                    AssistantProcessStageUiModel(
                        stageId = "need_understanding",
                        displayLabel = "理解你的需求",
                        status = AssistantProcessStageStatus.Completed,
                        durationMs = 320,
                    ),
                    AssistantProcessStageUiModel(
                        stageId = "constraint_confirmation",
                        displayLabel = "确认预算和使用场景",
                        status = AssistantProcessStageStatus.Completed,
                        durationMs = 240,
                    ),
                    AssistantProcessStageUiModel(
                        stageId = "product_filtering",
                        displayLabel = "筛选符合条件的商品",
                        status = AssistantProcessStageStatus.Running,
                        startedElapsedMs = 560,
                    ),
                ),
                totalElapsedMs = 1500,
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
            onAddToCart = { _, _ -> },
        )
    }
}
