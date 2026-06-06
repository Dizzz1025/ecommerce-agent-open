package com.yourteam.ecommerceguider.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.yourteam.ecommerceguider.data.model.ChatMessageUiModel

@Composable
fun ChatBubble(
    message: ChatMessageUiModel,
    modifier: Modifier = Modifier,
) {
    val alignment = if (message.isUser) Alignment.CenterEnd else Alignment.CenterStart
    val shape = RoundedCornerShape(
        topStart = 22.dp,
        topEnd = 22.dp,
        bottomStart = if (message.isUser) 22.dp else 8.dp,
        bottomEnd = if (message.isUser) 8.dp else 22.dp,
    )

    BoxWithConstraints(
        modifier = modifier.fillMaxWidth(),
        contentAlignment = alignment,
    ) {
        val maxBubbleWidth = maxWidth * if (message.isUser) 0.78f else 0.86f
        val bubbleModifier = if (message.isUser) {
            Modifier
                .widthIn(max = maxBubbleWidth)
                .background(SpatialPrimaryGradient, shape)
        } else {
            Modifier
                .widthIn(max = maxBubbleWidth)
                .spatialGlass(shape = shape, fillColor = SpatialGlassColorSoft, elevation = 3.dp)
        }
        Surface(
            modifier = bubbleModifier,
            shape = shape,
            color = Color.Transparent,
            border = if (message.isUser) {
                BorderStroke(1.dp, SpatialGlassBorderColor)
            } else {
                null
            },
        ) {
            Box(
                modifier = Modifier.padding(horizontal = 15.dp, vertical = 11.dp),
            ) {
                Text(
                    text = message.content,
                    style = androidx.compose.material3.MaterialTheme.typography.bodyMedium,
                    color = if (message.isUser) Color.White else SpatialTextBody,
                )
            }
        }
    }
}
