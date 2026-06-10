@file:OptIn(androidx.compose.foundation.layout.ExperimentalLayoutApi::class)

package com.yourteam.ecommerceguider.ui.screens.chat.components

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
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
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
import com.yourteam.ecommerceguider.data.model.asRecommendationTitleOrNull
import com.yourteam.ecommerceguider.data.model.recommendationSectionTitleForRender
import com.yourteam.ecommerceguider.theme.AppColors
import com.yourteam.ecommerceguider.theme.AppDimensions
import com.yourteam.ecommerceguider.theme.AppRadius
import com.yourteam.ecommerceguider.theme.AppSpacing
import com.yourteam.ecommerceguider.theme.AppTypography
import com.yourteam.ecommerceguider.theme.ChatColors
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
    displayName: String?,
    onHistoryClick: () -> Unit,
    onCartClick: () -> Unit,
    onAddressClick: () -> Unit = {},
) {
    val greeting = displayName
        ?.trim()
        ?.takeIf { it.isNotEmpty() }
        ?.let { "你好，$it" }
        ?: "你好"
    Surface(
        color = ChatColors.Surface,
        border = BorderStroke(1.dp, ChatColors.Border),
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
                    text = greeting,
                    style = AppTypography.BodyStrong,
                    color = ChatColors.TextPrimary,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    text = "今天想买点什么呢？",
                    style = AppTypography.BodySmall,
                    color = ChatColors.TextSecondary,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            AppIconButton(
                onClick = onHistoryClick,
                style = AppIconButtonStyle.Surface,
                containerSize = AppDimensions.IconButton,
                iconSize = AppDimensions.IconSmall,
                containerColorOverride = ChatColors.Surface,
                contentColorOverride = ChatColors.TextPrimary,
                borderColorOverride = ChatColors.Border,
            ) {
                Icon(
                    painter = painterResource(R.drawable.ic_history_24),
                    contentDescription = "历史需求",
                )
            }
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
            containerColorOverride = ChatColors.Surface,
            contentColorOverride = ChatColors.TextPrimary,
            borderColorOverride = ChatColors.Border,
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
            TextButton(onClick = onDismiss) {
                Text(
                    text = "关闭",
                    color = ChatColors.WarmAccent,
                )
            }
        },
        title = {
            Text(
                text = "历史需求",
                style = AppTypography.TitleSmall,
                color = ChatColors.TextPrimary,
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
                        color = ChatColors.TextSecondary,
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
        color = ChatColors.Surface,
        border = BorderStroke(1.dp, ChatColors.Border),
    ) {
        Column(
            modifier = Modifier.padding(AppSpacing.Md),
            verticalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
        ) {
            TagChip(text = "第 ${index + 1} 轮", tone = TagChipTone.Neutral)
            HistoryTextBlock(label = "你", text = turn.userMessage.content)
            turn.assistantMessage?.thinking
                ?.takeIf { it.status != AssistantThinkingStatus.Idle && it.stages.isNotEmpty() }
                ?.let { thinking ->
                    HistoryThinkingBlock(
                        turnId = turn.userMessage.turnId,
                        thinking = thinking,
                    )
                }
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
            color = ChatColors.TextSecondary,
        )
        Text(
            text = text,
            style = AppTypography.BodySmall,
            color = ChatColors.TextPrimary,
            maxLines = 6,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

@Composable
private fun HistoryThinkingBlock(
    turnId: String,
    thinking: AssistantThinkingUiModel,
) {
    var expanded by rememberSaveable(turnId, "history-thinking") { mutableStateOf(false) }
    ThinkingProcessCard(
        thinking = thinking,
        isStreaming = false,
        errorMessage = null,
        expanded = expanded,
        onToggle = { expanded = !expanded },
    )
}

@Composable
private fun HistoryRecommendationBlock(
    section: RecommendationSectionUiModel,
    onProductClick: (String) -> Unit,
    onAddToCart: (ProductUiModel, String) -> Unit,
    activeSpecSelection: SpecSelectionUiModel? = null,
    onSpecOptionClick: (SpecSelectionUiModel, SpecSelectionOptionUiModel) -> Unit = { _, _ -> },
) {
    RecommendationSection(
        section = section,
        totalCount = 1,
        onProductClick = onProductClick,
        onAddToCart = onAddToCart,
        activeSpecSelection = activeSpecSelection,
        onSpecOptionClick = onSpecOptionClick,
    )
}

@Composable
fun WelcomeCard() {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = SmallPanelShape,
        color = ChatColors.Surface,
        border = BorderStroke(1.dp, ChatColors.Border),
    ) {
        Column(
            modifier = Modifier.padding(AppSpacing.Md),
            verticalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
        ) {
            Text(
                text = "说出预算、场景或纠结点",
                style = AppTypography.BodyStrong,
                color = ChatColors.TextPrimary,
            )
            Text(
                text = "我会根据真实商品数据给出购买建议、推荐理由和可加购商品。",
                style = AppTypography.BodySmall,
                color = ChatColors.TextSecondary,
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
    val hasError = !errorMessage.isNullOrBlank()
    val hasThinking = thinking.status != AssistantThinkingStatus.Idle &&
        (thinking.stages.isNotEmpty() || isStreaming)
    val hasAnswer = answer.isNotBlank()
    val shouldShowErrorInAnswer = hasError && !isStreaming && (hasAnswer || !hasThinking)

    if (!hasError && !hasThinking && !hasAnswer) {
        return
    }

    Column(
        modifier = Modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
    ) {
        if (hasThinking) {
            ThinkingProcessCard(
                thinking = thinking,
                isStreaming = isStreaming && thinking.status != AssistantThinkingStatus.Done,
                errorMessage = errorMessage.takeIf { hasError && !isStreaming && !hasAnswer },
                expanded = thinkingExpanded,
                onToggle = onToggleThinking,
            )
        }
        if (hasAnswer || shouldShowErrorInAnswer) {
            AssistantAnswerBlock(
                answer = answer,
                errorMessage = errorMessage.takeIf { shouldShowErrorInAnswer },
            )
        }
    }
}

@Composable
private fun AssistantAnswerBlock(
    answer: String,
    errorMessage: String?,
) {
    Column(
        modifier = Modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(AppSpacing.Xs),
    ) {
        Text(
            text = "购买结论",
            style = AppTypography.CaptionStrong,
            color = ChatColors.WarmAccent,
        )
        answer
            .takeIf { it.isNotBlank() }
            ?.let { ParagraphText(text = it) }
        errorMessage?.let {
            InlineError(message = it)
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
        color = ChatColors.Surface,
        border = BorderStroke(1.dp, ChatColors.Border),
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
        AssistantThinkingStatus.Done -> "推荐思考已完成"
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
                tint = ChatColors.Success,
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
                color = ChatColors.WarmAccent,
            )
        }
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = title,
                style = AppTypography.TitleSmall,
                color = ChatColors.TextPrimary,
            )
            if (thinking.status != AssistantThinkingStatus.Done) {
                Text(
                    text = runningStage?.summary?.takeIf { it.isNotBlank() }
                        ?: runningStage?.displayLabel
                        ?: "已完成 $completedCount 个阶段",
                    style = AppTypography.BodySmall,
                    color = ChatColors.TextSecondary,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
        TextButton(onClick = onToggle) {
            Text(
                text = if (expanded) "收起" else "展开",
                color = ChatColors.WarmAccent,
            )
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
            AssistantProcessStageStatus.Completed -> ChatColors.Success
            AssistantProcessStageStatus.Running -> ChatColors.WarmAccent
            AssistantProcessStageStatus.Failed -> AppColors.Danger
            AssistantProcessStageStatus.Pending -> ChatColors.TextTertiary
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
                color = ChatColors.TextPrimary,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            stage.summary?.takeIf { it.isNotBlank() }?.let {
                Text(
                    text = it,
                    style = AppTypography.Caption,
                    color = ChatColors.TextSecondary,
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
        color = ChatColors.Surface,
        border = BorderStroke(1.dp, ChatColors.Border),
    ) {
        Column(
            modifier = Modifier.padding(AppSpacing.Md),
            verticalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
        ) {
            if (selection.completed && completedText != null) {
                Text(
                    text = completedText,
                    style = AppTypography.BodyStrong,
                    color = ChatColors.Success,
                )
            } else {
                Text(
                    text = "请选择规格",
                    style = AppTypography.TitleSmall,
                    color = ChatColors.TextPrimary,
                )
                Text(
                    text = selection.productName,
                    style = AppTypography.BodySmall,
                    color = ChatColors.TextSecondary,
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
                        color = ChatColors.TextTertiary,
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
        color = ChatColors.SurfaceSubtle,
        border = BorderStroke(1.dp, ChatColors.Border),
    ) {
        Column(
            modifier = Modifier.padding(AppSpacing.Md),
            verticalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
        ) {
            Text(
                text = "选择规格",
                style = AppTypography.BodyStrong,
                color = ChatColors.TextPrimary,
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
            enabled -> ChatColors.Surface
            else -> ChatColors.SurfaceSubtle
        },
        border = BorderStroke(1.dp, if (selected) AppColors.Primary else ChatColors.Border),
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
                    color = if (selected) AppColors.OnPrimary else ChatColors.TextPrimary,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                if (option.stock == 0) {
                    Text(
                        text = "暂时无库存",
                        style = AppTypography.Caption,
                        color = if (selected) AppColors.OnPrimary else ChatColors.TextSecondary,
                    )
                }
            }
            Text(
                text = if (selected) "已加入" else "¥${formatPrice(option.price)}",
                style = AppTypography.CaptionStrong,
                color = if (selected) AppColors.OnPrimary else ChatColors.TextPrimary,
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
    val title = product.recommendationDisplayTitle
        ?: product.recommendTitle
        ?: presentation?.title
        ?: presentation?.shortTitle
    val reason = product.recommendReason.orEmpty()
    RecommendationSection(
        section = RecommendationSectionUiModel(
            turnId = "snapshot",
            sectionIndex = index + 1,
            skuId = product.skuId,
            optionLabel = presentation?.optionLabel.orEmpty(),
            displayTitle = title.orEmpty(),
            text = reason,
            displayText = reason,
            recommendReason = reason,
            reason = product.reason ?: presentation?.reason,
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
    val reasonText = section.recommendReason
        .ifBlank { section.displayText }
        .ifBlank { section.text }
    Column(
        modifier = Modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
    ) {
        recommendationSectionTitleForRender(section)?.let { title ->
            Text(
                text = title,
                style = AppTypography.TitleSmall,
                color = ChatColors.TextPrimary,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
        }
        reasonText
            .takeIf { it.isNotBlank() }
            ?.let {
                ExpandableRecommendationReason(
                    text = it,
                    collapsed = section.done,
                )
            }
            ?: if (!section.done) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
                ) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(AppDimensions.IconSmall),
                        strokeWidth = 2.dp,
                        color = ChatColors.WarmAccent,
                    )
                    Text(
                        text = "正在生成推荐理由",
                        style = AppTypography.BodySmall,
                        color = ChatColors.TextSecondary,
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
                    color = ChatColors.SurfaceSubtle,
                ) {
                    Text(
                        text = "需要注意：$tradeOff",
                        modifier = Modifier.padding(AppSpacing.Md),
                        style = AppTypography.BodySmall,
                        color = ChatColors.TextSecondary,
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
                isPrimary = false,
                roleLabel = null,
                showRecommendationReason = false,
                useChatColors = true,
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
private fun ExpandableRecommendationReason(
    text: String,
    collapsed: Boolean,
) {
    val normalizedText = text.lineSequence()
        .map { it.trim() }
        .filter { it.isNotBlank() }
        .joinToString("\n\n")
    val canCollapse = collapsed && (normalizedText.length > 180 || normalizedText.count { it == '\n' } >= 6)
    var expanded by rememberSaveable(normalizedText) { mutableStateOf(false) }

    Column(verticalArrangement = Arrangement.spacedBy(AppSpacing.Xs)) {
        Text(
            text = normalizedText,
            style = AppTypography.Body,
            color = ChatColors.TextPrimary,
            maxLines = if (canCollapse && !expanded) 7 else Int.MAX_VALUE,
            overflow = if (canCollapse && !expanded) TextOverflow.Ellipsis else TextOverflow.Clip,
        )
        if (canCollapse) {
            TextButton(onClick = { expanded = !expanded }) {
                Text(
                    text = if (expanded) "收起" else "展开全文",
                    color = ChatColors.WarmAccent,
                )
            }
        }
    }
}

private fun ProductUiModel.recommendationFallbackTitle(): String {
    val candidates = listOf(
        presentation?.title,
        presentation?.shortTitle,
        shortTitle,
        highlightShort,
        matchedReasons.firstOrNull(),
        spotlight.features.firstOrNull(),
        suitableScenarios.firstOrNull(),
    )
    candidates.firstNotNullOfOrNull { it.cleanRecommendationTitle() }?.let { return it }
    val context = listOf(
        displayReason,
        productHighlight,
        highlightDetail,
        tags.joinToString(" "),
        matchedReasons.joinToString(" "),
        suitableScenarios.joinToString(" "),
        targetUserTags.joinToString(" "),
        category,
        subCategory,
    ).joinToString(" ")
    return when {
        context.hasAny("敏感", "温和") -> "敏感肌更友好的温和选择"
        context.hasAny("补涂", "便携", "随身") -> "适合随身补涂的便携款"
        context.hasAny("通勤", "户外", "运动") -> "通勤户外兼顾的实用选择"
        context.hasAny("清爽", "控油", "不黏") -> "清爽肤感优先的日常选择"
        context.hasAny("预算", "性价比", "平价") -> "预算内更稳妥的选择"
        category.isNotBlank() -> "${category}里的稳妥选择"
        else -> "适合当前需求的稳妥选择"
    }
}

private fun String?.cleanRecommendationTitle(): String? {
    return asRecommendationTitleOrNull()
    val value = this?.trim().orEmpty()
    if (value.isBlank() || value.equals("null", ignoreCase = true)) {
        return null
    }
    val normalized = value.replace(" ", "")
    val mechanical = normalized.matches(Regex("""^方案[一二三四五六七八九十\d]+$""")) ||
        normalized.matches(Regex("""^推荐[一二三四五六七八九十\d]+$""")) ||
        normalized.matches(Regex("""^第[一二三四五六七八九十\d]+个?推荐$""")) ||
        normalized == "首选方案" ||
        normalized == "备选方案"
    if (mechanical) {
        return null
    }
    return value.takeIf { it.length <= 28 }
}

private fun String.hasAny(vararg keywords: String): Boolean {
    return keywords.any { keyword -> contains(keyword, ignoreCase = true) }
}

@Composable
fun FinalComparisonSummary(products: List<ProductUiModel>) {
    if (products.isEmpty()) {
        return
    }
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = PanelShape,
        color = ChatColors.Surface,
        border = BorderStroke(1.dp, ChatColors.Border),
    ) {
        Column(
            modifier = Modifier.padding(AppSpacing.Lg),
            verticalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
        ) {
            Text(
                text = "商品概览",
                style = AppTypography.TitleSmall,
                color = ChatColors.TextPrimary,
            )
            products.take(3).forEach { product ->
                Text(
                    text = "${product.displayTitleShort} · ¥${formatPrice(product.price)}",
                    style = AppTypography.BodySmall,
                    color = ChatColors.TextSecondary,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
    }
}

@Composable
private fun RecommendationTagRow(tags: List<String>) {
    val displayTags = tags
        .map { it.trim() }
        .filter { it.isNotBlank() }
        .distinct()
        .take(3)
    if (displayTags.isEmpty()) {
        return
    }
    FlowRow(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
        verticalArrangement = Arrangement.spacedBy(AppSpacing.Xs),
    ) {
        displayTags.forEach { tag ->
            TagChip(
                text = tag,
                tone = TagChipTone.Warm,
                containerColor = ChatColors.TagBackground,
                contentColor = ChatColors.TagText,
                borderColor = ChatColors.Border,
            )
        }
    }
}

@Composable
fun EmptyProductsCard() {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = PanelShape,
        color = ChatColors.Surface,
        border = BorderStroke(1.dp, ChatColors.Border),
    ) {
        Column(
            modifier = Modifier.padding(AppSpacing.Lg),
            verticalArrangement = Arrangement.spacedBy(AppSpacing.Sm),
        ) {
            Text(
                text = "暂时没有找到完全符合条件的商品",
                style = AppTypography.TitleSmall,
                color = ChatColors.TextPrimary,
            )
            Text(
                text = "可以尝试放宽预算或调整筛选条件。",
                style = AppTypography.Body,
                color = ChatColors.TextSecondary,
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
        color = ChatColors.Surface,
        border = BorderStroke(1.dp, ChatColors.Border),
        modifier = Modifier.clickable(onClick = onClick),
    ) {
        Text(
            text = text,
            modifier = Modifier.padding(horizontal = AppSpacing.Md, vertical = AppSpacing.Sm),
            style = AppTypography.CaptionStrong,
            color = ChatColors.TextPrimary,
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
        color = ChatColors.Surface,
        border = BorderStroke(1.dp, ChatColors.Border),
    ) {
        Column(
            modifier = Modifier.padding(AppSpacing.Lg),
            verticalArrangement = Arrangement.spacedBy(AppSpacing.Md),
        ) {
            Text(
                text = "核心字段对比",
                style = AppTypography.TitleSmall,
                color = ChatColors.TextPrimary,
            )
            products.take(3).forEachIndexed { index, product ->
                Row(horizontalArrangement = Arrangement.spacedBy(AppSpacing.Sm)) {
                    Text(
                        text = "商品 ${index + 1}",
                        style = AppTypography.CaptionStrong,
                        color = ChatColors.TextSecondary,
                    )
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = product.displayTitleShort,
                            style = AppTypography.BodyStrong,
                            color = ChatColors.TextPrimary,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                        Text(
                            text = listOf(product.brand, "¥${formatPrice(product.price)}")
                                .filter { it.isNotBlank() }
                                .joinToString(" · "),
                            style = AppTypography.BodySmall,
                            color = ChatColors.TextSecondary,
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
        color = ChatColors.Surface,
        border = BorderStroke(1.dp, ChatColors.Border),
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
                color = ChatColors.TextPrimary,
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
                    color = ChatColors.TextPrimary,
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
