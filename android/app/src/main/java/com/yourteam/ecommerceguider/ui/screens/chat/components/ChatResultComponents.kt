@file:OptIn(androidx.compose.foundation.layout.ExperimentalLayoutApi::class)

package com.yourteam.ecommerceguider.ui.screens.chat.components

import androidx.compose.animation.Crossfade
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
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
import com.yourteam.ecommerceguider.data.model.AssistantProcessStageStatus
import com.yourteam.ecommerceguider.data.model.AssistantProcessStageUiModel
import com.yourteam.ecommerceguider.data.model.AssistantThinkingStatus
import com.yourteam.ecommerceguider.data.model.AssistantThinkingUiModel
import com.yourteam.ecommerceguider.data.model.ChatMessageUiModel
import com.yourteam.ecommerceguider.data.model.ProductUiModel
import com.yourteam.ecommerceguider.data.model.RecommendationSectionUiModel
import com.yourteam.ecommerceguider.data.model.SpecSelectionOptionUiModel
import com.yourteam.ecommerceguider.data.model.SpecSelectionUiModel
import com.yourteam.ecommerceguider.theme.AppColors
import com.yourteam.ecommerceguider.theme.AppDimensions
import com.yourteam.ecommerceguider.theme.AppMotion
import com.yourteam.ecommerceguider.theme.AppRadius
import com.yourteam.ecommerceguider.theme.AppSpacing
import com.yourteam.ecommerceguider.theme.AppTypography
import com.yourteam.ecommerceguider.theme.EcommerceGuiderTheme
import com.yourteam.ecommerceguider.ui.components.AppIconButton
import com.yourteam.ecommerceguider.ui.components.AppIconButtonStyle
import com.yourteam.ecommerceguider.ui.components.PrimaryButton
import com.yourteam.ecommerceguider.ui.components.ProductCard
import com.yourteam.ecommerceguider.ui.components.SecondaryButton
import com.yourteam.ecommerceguider.ui.components.TagChip
import com.yourteam.ecommerceguider.ui.components.TagChipTone
import com.yourteam.ecommerceguider.ui.components.formatPrice
import com.yourteam.ecommerceguider.utils.PreviewData

private val PanelShape = RoundedCornerShape(AppRadius.Card)
private val SmallPanelShape = RoundedCornerShape(AppRadius.Large)

@Composable
fun GuideTopBar(
    cartItemCount: Int,
    historyCount: Int,
    onHistoryClick: () -> Unit,
    onCartClick: () -> Unit,
    onAddressClick: () -> Unit = {},
) {
    Surface(
        color = AppColors.Surface,
        border = BorderStroke(1.dp, AppColors.Divider),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = AppSpacing.Lg, vertical = AppSpacing.Sm),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
        ) {
            Box(
                modifier = Modifier
                    .size(AppDimensions.IconButton)
                    .clip(CircleShape)
                    .background(AppColors.Primary),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    text = "你",
                    color = AppColors.OnPrimary,
                    style = AppTypography.CaptionStrong,
                    fontWeight = FontWeight.Bold,
                )
            }
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "你好",
                    style = AppTypography.BodyStrong,
                    color = AppColors.TextPrimary,
                    maxLines = 1,
                )
                Text(
                    text = "今天想买点什么呢？",
                    style = AppTypography.BodySmall,
                    color = AppColors.TextSecondary,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            BadgeIconButton(
                count = historyCount,
                contentDescription = "历史需求",
                iconRes = R.drawable.ic_history_24,
                onClick = onHistoryClick,
            )
            BadgeIconButton(
                count = cartItemCount,
                contentDescription = "购物车",
                iconRes = R.drawable.ic_cart_24,
                onClick = onCartClick,
            )
        }
    }
}

@Composable
private fun BadgeIconButton(
    count: Int,
    contentDescription: String,
    iconRes: Int,
    onClick: () -> Unit,
) {
    Box {
        AppIconButton(
            onClick = onClick,
            style = AppIconButtonStyle.Surface,
            containerSize = AppDimensions.IconButton,
            iconSize = AppDimensions.IconSmall,
        ) {
            Icon(
                painter = painterResource(iconRes),
                contentDescription = contentDescription,
            )
        }
        if (count > 0) {
            Box(
                modifier = Modifier
                    .align(Alignment.TopEnd)
                    .size(18.dp)
                    .clip(CircleShape)
                    .background(AppColors.Primary),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    text = count.coerceAtMost(99).toString(),
                    style = AppTypography.Caption,
                    color = AppColors.OnPrimary,
                    maxLines = 1,
                )
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
            TextButton(onClick = onDismiss) { Text("关闭") }
        },
        title = {
            Text(
                text = "历史需求",
                style = AppTypography.TitleSmall,
                color = AppColors.TextPrimary,
            )
        },
        text = {
            Column(
                modifier = Modifier.verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(AppSpacing.Md),
            ) {
                if (turns.isEmpty()) {
                    Text(
                        text = "还没有历史需求。",
                        style = AppTypography.Body,
                        color = AppColors.TextSecondary,
                    )
                } else {
                    turns.forEachIndexed { index, turn ->
                        HistoryTurnBlock(
                            index = index,
                            turn = turn,
                            onProductClick = onProductClick,
                            onAddToCart = onAddToCart,
                            activeSpecSelection = activeSpecSelection,
                            onSpecOptionClick = onSpecOptionClick,
                        )
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
private fun HistoryTurnBlock(
    index: Int,
    turn: ChatHistoryTurn,
    onProductClick: (String) -> Unit,
    onAddToCart: (ProductUiModel, String) -> Unit,
    activeSpecSelection: SpecSelectionUiModel?,
    onSpecOptionClick: (SpecSelectionUiModel, SpecSelectionOptionUiModel) -> Unit,
) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = PanelShape,
        color = AppColors.Surface,
        border = BorderStroke(1.dp, AppColors.Border),
    ) {
        Column(
            modifier = Modifier.padding(AppSpacing.Md),
            verticalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
        ) {
            TagChip(text = "第 ${index + 1} 轮", tone = TagChipTone.Neutral)
            HistoryTextBlock(label = "你", text = turn.userMessage.content)
            turn.assistantMessage?.content
                ?.takeIf { it.isNotBlank() }
                ?.let { HistoryTextBlock(label = "导购回复", text = it) }
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

@Composable
private fun HistoryTextBlock(
    label: String,
    text: String,
) {
    Column(verticalArrangement = Arrangement.spacedBy(AppSpacing.Xs)) {
        Text(
            text = label,
            style = AppTypography.CaptionStrong,
            color = AppColors.TextSecondary,
        )
        Text(
            text = text,
            style = AppTypography.BodySmall,
            color = AppColors.TextPrimary,
            maxLines = 6,
            overflow = TextOverflow.Ellipsis,
        )
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
    Column(verticalArrangement = Arrangement.spacedBy(AppSpacing.Sm)) {
        section.displayText.ifBlank { section.text }
            .takeIf { it.isNotBlank() }
            ?.let { text ->
                Text(
                    text = text,
                    style = AppTypography.BodySmall,
                    color = AppColors.TextSecondary,
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

@Composable
fun WelcomeCard() {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = SmallPanelShape,
        color = AppColors.Surface,
        border = BorderStroke(1.dp, AppColors.Border),
    ) {
        Column(
            modifier = Modifier.padding(AppSpacing.Md),
            verticalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
        ) {
            Text(
                text = "说出预算、场景或纠结点",
                style = AppTypography.BodyStrong,
                color = AppColors.TextPrimary,
            )
            Text(
                text = "我会根据真实商品数据给出购买建议、推荐理由和可加购商品。",
                style = AppTypography.BodySmall,
                color = AppColors.TextSecondary,
            )
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
    val hasFormalOutput = answer.isNotBlank() || products.isNotEmpty()
    val hasError = !errorMessage.isNullOrBlank()
    val hasThinking = thinking.status != AssistantThinkingStatus.Idle &&
        (thinking.stages.isNotEmpty() || isStreaming)

    if (hasFormalOutput && answer.isBlank()) {
        return
    }
    if (!hasError && !hasThinking && answer.isBlank()) {
        return
    }

    Crossfade(
        targetState = answer.isNotBlank(),
        animationSpec = tween(durationMillis = AppMotion.Normal),
        label = "assistant-message-crossfade",
    ) { showFormalAnswer ->
        if (showFormalAnswer) {
            AssistantAnswerBlock(
                answer = answer,
                errorMessage = errorMessage.takeIf { hasError && !isStreaming },
            )
        } else {
            ThinkingProcessCard(
                thinking = thinking,
                isStreaming = isStreaming,
                errorMessage = errorMessage.takeIf { hasError && !isStreaming },
                expanded = thinkingExpanded,
                onToggle = onToggleThinking,
            )
        }
    }
}

@Composable
private fun AssistantAnswerBlock(
    answer: String,
    errorMessage: String?,
) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = SmallPanelShape,
        color = AppColors.Surface,
        border = BorderStroke(1.dp, AppColors.Border),
    ) {
        Column(
            modifier = Modifier.padding(AppSpacing.Md),
            verticalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
        ) {
            Text(
                text = "购买结论",
                style = AppTypography.CaptionStrong,
                color = AppColors.TextSecondary,
            )
            ParagraphText(text = answer)
            errorMessage?.let {
                InlineError(message = it)
            }
        }
    }
}

@Composable
private fun ThinkingProcessCard(
    thinking: AssistantThinkingUiModel,
    isStreaming: Boolean,
    errorMessage: String?,
    expanded: Boolean,
    onToggle: () -> Unit,
) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = SmallPanelShape,
        color = AppColors.Surface,
        border = BorderStroke(1.dp, AppColors.Border),
    ) {
        Column(
            modifier = Modifier.padding(AppSpacing.Md),
            verticalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
        ) {
            ThinkingProcessContent(
                thinking = thinking,
                isStreaming = isStreaming,
                expanded = expanded,
                onToggle = onToggle,
            )
            errorMessage?.let { InlineError(message = it) }
        }
    }
}

@Composable
private fun ThinkingProcessContent(
    thinking: AssistantThinkingUiModel,
    isStreaming: Boolean,
    expanded: Boolean,
    onToggle: () -> Unit,
) {
    val stages = thinking.stages
    val runningStage = stages.firstOrNull { it.status == AssistantProcessStageStatus.Running }
    val completedCount = stages.count { it.status == AssistantProcessStageStatus.Completed }
    val title = when (thinking.status) {
        AssistantThinkingStatus.Failed -> "推荐思路未完成"
        AssistantThinkingStatus.Done -> "推荐思路已完成"
        AssistantThinkingStatus.Generating -> "正在整理回复"
        AssistantThinkingStatus.Running -> "推荐思路"
        AssistantThinkingStatus.Idle -> "推荐思路"
    }
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
    ) {
        when {
            thinking.status == AssistantThinkingStatus.Done -> Icon(
                painter = painterResource(R.drawable.ic_check_circle_20),
                contentDescription = null,
                tint = AppColors.Success,
                modifier = Modifier.size(AppDimensions.IconSmall),
            )
            thinking.status == AssistantThinkingStatus.Failed -> Text(
                text = "!",
                style = AppTypography.CaptionStrong,
                color = AppColors.Danger,
            )
            isStreaming -> CircularProgressIndicator(
                modifier = Modifier.size(AppDimensions.IconSmall),
                strokeWidth = 2.dp,
                color = AppColors.Primary,
            )
        }
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = title,
                style = AppTypography.TitleSmall,
                color = AppColors.TextPrimary,
            )
            Text(
                text = runningStage?.summary?.takeIf { it.isNotBlank() }
                    ?: runningStage?.displayLabel
                    ?: "已完成 $completedCount 个阶段",
                style = AppTypography.BodySmall,
                color = AppColors.TextSecondary,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
        TextButton(onClick = onToggle) {
            Text(if (expanded) "收起" else "展开")
        }
    }
    if (expanded) {
        Column(verticalArrangement = Arrangement.spacedBy(AppSpacing.Sm)) {
            stages.forEach { stage ->
                ProcessStageRow(stage = stage)
            }
        }
    }
}

@Composable
private fun ProcessStageRow(stage: AssistantProcessStageUiModel) {
    Row(
        verticalAlignment = Alignment.Top,
        horizontalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
    ) {
        val dotColor = when (stage.status) {
            AssistantProcessStageStatus.Completed -> AppColors.Success
            AssistantProcessStageStatus.Running -> AppColors.Primary
            AssistantProcessStageStatus.Failed -> AppColors.Danger
            AssistantProcessStageStatus.Pending -> AppColors.TextDisabled
        }
        Box(
            modifier = Modifier
                .padding(top = 6.dp)
                .size(8.dp)
                .clip(CircleShape)
                .background(dotColor),
        )
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = stage.displayLabel,
                style = AppTypography.BodySmall,
                color = AppColors.TextPrimary,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            stage.summary?.takeIf { it.isNotBlank() }?.let {
                Text(
                    text = it,
                    style = AppTypography.Caption,
                    color = AppColors.TextSecondary,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
    }
}

@Composable
fun SpecSelectionCard(
    selection: SpecSelectionUiModel,
    onOptionClick: (SpecSelectionOptionUiModel) -> Unit,
) {
    val completedText = selection.successText
        ?.takeIf { it.isNotBlank() }
        ?: if (selection.completed) "已加入购物车：${selection.productName}" else null
    val errorText = selection.errorText?.takeIf { it.isNotBlank() }
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = SmallPanelShape,
        color = AppColors.Surface,
        border = BorderStroke(1.dp, AppColors.Border),
    ) {
        Column(
            modifier = Modifier.padding(AppSpacing.Md),
            verticalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
        ) {
            if (selection.completed && completedText != null) {
                Text(
                    text = completedText,
                    style = AppTypography.BodyStrong,
                    color = AppColors.Success,
                )
            } else {
                Text(
                    text = "请选择规格",
                    style = AppTypography.TitleSmall,
                    color = AppColors.TextPrimary,
                )
                Text(
                    text = selection.productName,
                    style = AppTypography.BodySmall,
                    color = AppColors.TextSecondary,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                errorText?.let { InlineError(message = it) }
                if (!selection.hideOptions) {
                    Column(verticalArrangement = Arrangement.spacedBy(AppSpacing.Sm)) {
                        selection.options.forEach { option ->
                            SpecOptionButton(
                                option = option,
                                selected = selection.selectedSkuId == option.skuId,
                                locked = selection.selectedSkuId != null,
                                onClick = { onOptionClick(option) },
                            )
                        }
                    }
                    Text(
                        text = "点击规格后将直接加入购物车",
                        style = AppTypography.Caption,
                        color = AppColors.TextTertiary,
                    )
                }
            }
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
            .padding(top = AppSpacing.Xs),
        shape = SmallPanelShape,
        color = AppColors.SurfaceSoft,
        border = BorderStroke(1.dp, AppColors.Border),
    ) {
        Column(
            modifier = Modifier.padding(AppSpacing.Md),
            verticalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
        ) {
            Text(
                text = "选择规格",
                style = AppTypography.BodyStrong,
                color = AppColors.TextPrimary,
            )
            selection.options.forEach { option ->
                SpecOptionButton(
                    option = option,
                    selected = selection.selectedSkuId == option.skuId,
                    locked = selection.selectedSkuId != null,
                    onClick = { onOptionClick(option) },
                )
            }
        }
    }
}

@Composable
private fun SpecOptionButton(
    option: SpecSelectionOptionUiModel,
    selected: Boolean,
    locked: Boolean,
    onClick: () -> Unit,
) {
    val enabled = option.available && option.stock != 0 && !locked
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = AppDimensions.ButtonSmallHeight)
            .clickable(enabled = enabled, onClick = onClick),
        shape = RoundedCornerShape(AppRadius.Large),
        color = when {
            selected -> AppColors.Primary
            enabled -> AppColors.Surface
            else -> AppColors.SurfacePressed
        },
        border = BorderStroke(1.dp, if (selected) AppColors.Primary else AppColors.BorderStrong),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = AppSpacing.Md, vertical = AppSpacing.Sm),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = option.specText,
                    style = AppTypography.BodyStrong,
                    color = if (selected) AppColors.OnPrimary else AppColors.TextPrimary,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                if (option.stock == 0) {
                    Text(
                        text = "暂时无库存",
                        style = AppTypography.Caption,
                        color = if (selected) AppColors.OnPrimary else AppColors.TextSecondary,
                    )
                }
            }
            Text(
                text = if (selected) "已加入" else "¥${formatPrice(option.price)}",
                style = AppTypography.CaptionStrong,
                color = if (selected) AppColors.OnPrimary else AppColors.TextPrimary,
                maxLines = 1,
            )
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
    val roleLabel = presentation?.optionLabel?.takeIf { it.isNotBlank() } ?: "推荐 ${index + 1}"
    RecommendationSection(
        section = RecommendationSectionUiModel(
            turnId = "snapshot",
            sectionIndex = index + 1,
            skuId = product.skuId,
            optionLabel = roleLabel,
            text = product.displayReason,
            displayText = product.displayReason,
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
    val roleLabel = section.optionLabel.ifBlank { "推荐 ${section.sectionIndex}" }
    val reasonText = section.displayText
        .ifBlank { section.reason.orEmpty() }
        .ifBlank { section.text }

    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = SmallPanelShape,
        color = AppColors.Surface,
        border = BorderStroke(1.dp, AppColors.Border),
    ) {
        Column(
            modifier = Modifier.padding(AppSpacing.Md),
            verticalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
        ) {
            TagChip(text = roleLabel, tone = if (section.sectionIndex == 1) TagChipTone.Warm else TagChipTone.Neutral)
            reasonText
                .takeIf { it.isNotBlank() }
                ?.let { ParagraphText(text = it) }
                ?: if (!section.done) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
                    ) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(AppDimensions.IconSmall),
                            strokeWidth = 2.dp,
                            color = AppColors.Primary,
                        )
                        Text(
                            text = "正在生成推荐理由",
                            style = AppTypography.BodySmall,
                            color = AppColors.TextSecondary,
                        )
                    }
                } else {
                    null
                }
            section.tradeOff
                ?.takeIf { it.isNotBlank() && !it.equals("null", ignoreCase = true) }
                ?.let { tradeOff ->
                    Surface(
                        shape = RoundedCornerShape(AppRadius.Large),
                        color = AppColors.SurfaceSoft,
                    ) {
                        Text(
                            text = "需要注意：$tradeOff",
                            modifier = Modifier.padding(AppSpacing.Md),
                            style = AppTypography.BodySmall,
                            color = AppColors.TextSecondary,
                        )
                    }
                }
            product?.let {
                ProductCard(
                    product = it,
                    onClick = onProductClick,
                    onAddToCart = { selectedProduct -> onAddToCart(selectedProduct, section.stableKey) },
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
        modifier = Modifier.fillMaxWidth(),
        shape = PanelShape,
        color = AppColors.Surface,
        border = BorderStroke(1.dp, AppColors.Border),
    ) {
        Column(
            modifier = Modifier.padding(AppSpacing.Lg),
            verticalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
        ) {
            Text(
                text = "商品概览",
                style = AppTypography.TitleSmall,
                color = AppColors.TextPrimary,
            )
            products.take(3).forEach { product ->
                Text(
                    text = "${product.displayTitleShort} · ¥${formatPrice(product.price)}",
                    style = AppTypography.BodySmall,
                    color = AppColors.TextSecondary,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
    }
}

@Composable
fun EmptyProductsCard() {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = PanelShape,
        color = AppColors.Surface,
        border = BorderStroke(1.dp, AppColors.Border),
    ) {
        Column(
            modifier = Modifier.padding(AppSpacing.Lg),
            verticalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
        ) {
            Text(
                text = "暂时没有找到完全符合条件的商品",
                style = AppTypography.TitleSmall,
                color = AppColors.TextPrimary,
            )
            Text(
                text = "可以尝试放宽预算或调整筛选条件。",
                style = AppTypography.Body,
                color = AppColors.TextSecondary,
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
    Row(
        modifier = Modifier.horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
    ) {
        FollowUpChip(text = "换一批", onClick = { onSend("换一批") })
        FollowUpChip(text = "对比这几款", onClick = onCompare)
    }
}

@Composable
private fun FollowUpChip(
    text: String,
    onClick: () -> Unit,
) {
    Surface(
        shape = RoundedCornerShape(AppRadius.Pill),
        color = AppColors.Surface,
        border = BorderStroke(1.dp, AppColors.BorderStrong),
        modifier = Modifier.clickable(onClick = onClick),
    ) {
        Text(
            text = text,
            modifier = Modifier.padding(horizontal = AppSpacing.Md, vertical = AppSpacing.Sm),
            style = AppTypography.CaptionStrong,
            color = AppColors.TextPrimary,
        )
    }
}

@Composable
fun ProductCompareCard(products: List<ProductUiModel>) {
    if (products.size < 2) {
        return
    }
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = PanelShape,
        color = AppColors.Surface,
        border = BorderStroke(1.dp, AppColors.Border),
    ) {
        Column(
            modifier = Modifier.padding(AppSpacing.Lg),
            verticalArrangement = Arrangement.spacedBy(AppSpacing.Md),
        ) {
            Text(
                text = "核心字段对比",
                style = AppTypography.TitleSmall,
                color = AppColors.TextPrimary,
            )
            products.take(3).forEachIndexed { index, product ->
                Row(horizontalArrangement = Arrangement.spacedBy(AppSpacing.Sm)) {
                    Text(
                        text = "商品 ${index + 1}",
                        style = AppTypography.CaptionStrong,
                        color = AppColors.TextSecondary,
                    )
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = product.displayTitleShort,
                            style = AppTypography.BodyStrong,
                            color = AppColors.TextPrimary,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                        Text(
                            text = listOf(product.brand, "¥${formatPrice(product.price)}")
                                .filter { it.isNotBlank() }
                                .joinToString(" · "),
                            style = AppTypography.BodySmall,
                            color = AppColors.TextSecondary,
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
        modifier = Modifier
            .fillMaxWidth()
            .padding(bottom = AppSpacing.Sm),
        shape = PanelShape,
        color = AppColors.Surface,
        border = BorderStroke(1.dp, AppColors.Border),
    ) {
        Row(
            modifier = Modifier.padding(AppSpacing.Md),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
        ) {
            Text(
                text = "已选 $cartItemCount 件",
                modifier = Modifier.weight(1f),
                style = AppTypography.BodyStrong,
                color = AppColors.TextPrimary,
            )
            SecondaryButton(text = "购物车", onClick = onCartClick)
            PrimaryButton(text = "结算", onClick = onCheckoutClick)
        }
    }
}

@Composable
private fun ParagraphText(text: String) {
    Column(verticalArrangement = Arrangement.spacedBy(AppSpacing.Sm)) {
        text.lineSequence()
            .map { it.trim() }
            .filter { it.isNotBlank() }
            .forEach { paragraph ->
                Text(
                    text = paragraph,
                    style = AppTypography.Body,
                    color = AppColors.TextPrimary,
                )
            }
    }
}

@Composable
private fun InlineError(message: String) {
    Surface(
        shape = RoundedCornerShape(AppRadius.Large),
        color = AppColors.DangerSoft,
    ) {
        Text(
            text = message,
            modifier = Modifier.padding(AppSpacing.Md),
            style = AppTypography.BodySmall,
            color = AppColors.Danger,
        )
    }
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
                    ),
                    AssistantProcessStageUiModel(
                        stageId = "product_filtering",
                        displayLabel = "筛选符合条件的商品",
                        status = AssistantProcessStageStatus.Running,
                        summary = "正在商品库中筛选",
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
