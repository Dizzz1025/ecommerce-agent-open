package com.yourteam.ecommerceguider.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.yourteam.ecommerceguider.data.model.ChatMessageUiModel
import com.yourteam.ecommerceguider.theme.AppRadius
import com.yourteam.ecommerceguider.theme.AppSpacing
import com.yourteam.ecommerceguider.theme.AppTypography
import com.yourteam.ecommerceguider.theme.ChatColors

@Composable
fun ChatBubble(
    message: ChatMessageUiModel,
    modifier: Modifier = Modifier,
) {
    val alignment = if (message.isUser) Alignment.CenterEnd else Alignment.CenterStart
    val shape = RoundedCornerShape(
        topStart = AppRadius.Card,
        topEnd = AppRadius.Card,
        bottomStart = if (message.isUser) AppRadius.Card else AppRadius.Small,
        bottomEnd = if (message.isUser) AppRadius.Small else AppRadius.Card,
    )

    BoxWithConstraints(
        modifier = modifier.fillMaxWidth(),
        contentAlignment = alignment,
    ) {
        val maxBubbleWidth = maxWidth * if (message.isUser) 0.76f else 0.84f
        Surface(
            modifier = Modifier.widthIn(max = maxBubbleWidth),
            shape = shape,
            color = if (message.isUser) ChatColors.SurfaceSubtle else ChatColors.Surface,
            border = BorderStroke(1.dp, ChatColors.Border),
        ) {
            Box(
                modifier = Modifier.padding(horizontal = AppSpacing.Md, vertical = 6.dp),
            ) {
                Text(
                    text = message.content,
                    style = AppTypography.Body,
                    color = ChatColors.TextPrimary,
                )
            }
        }
    }
}
