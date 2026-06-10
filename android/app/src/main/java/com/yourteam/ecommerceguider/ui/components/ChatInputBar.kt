package com.yourteam.ecommerceguider.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.material3.Icon
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.input.TextFieldValue
import androidx.compose.ui.unit.dp
import com.yourteam.ecommerceguider.R
import com.yourteam.ecommerceguider.data.model.VoiceInputState
import com.yourteam.ecommerceguider.theme.AppColors
import com.yourteam.ecommerceguider.theme.AppDimensions
import com.yourteam.ecommerceguider.theme.AppRadius
import com.yourteam.ecommerceguider.theme.AppSpacing
import com.yourteam.ecommerceguider.theme.AppTypography
import com.yourteam.ecommerceguider.theme.ChatColors

@Composable
fun ChatInputBar(
    onSend: (String) -> Unit,
    onStop: () -> Unit,
    onImageClick: () -> Unit,
    onVoiceClick: () -> Unit,
    isStreaming: Boolean,
    modifier: Modifier = Modifier,
    voiceInputState: VoiceInputState = VoiceInputState.Idle,
) {
    var text by remember { mutableStateOf(TextFieldValue("")) }
    val isVoiceBusy = voiceInputState is VoiceInputState.Recording ||
        voiceInputState is VoiceInputState.Transcribing ||
        voiceInputState is VoiceInputState.Sending
    val canSend = text.text.isNotBlank() && !isStreaming && !isVoiceBusy
    val compactIconContainer = 36.dp
    val compactIconTouch = 42.dp

    Surface(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(AppRadius.Large),
        color = ChatColors.Surface,
        border = BorderStroke(width = 1.dp, color = ChatColors.Border),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = AppSpacing.Sm, vertical = 3.dp),
            horizontalArrangement = Arrangement.spacedBy(AppSpacing.Xs),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            AppIconButton(
                onClick = onImageClick,
                enabled = !isStreaming && !isVoiceBusy,
                style = AppIconButtonStyle.Plain,
                containerSize = compactIconContainer,
                hitAreaSize = compactIconTouch,
                minimumTouchSize = compactIconTouch,
                iconSize = AppDimensions.IconSmall,
                contentColorOverride = ChatColors.TextSecondary,
            ) {
                Icon(
                    painter = painterResource(R.drawable.ic_photo_24),
                    contentDescription = "拍图找同款",
                )
            }

            BasicTextField(
                value = text,
                onValueChange = { text = it },
                modifier = Modifier
                    .weight(1f)
                    .heightIn(
                        min = AppDimensions.ChatInputMinHeight,
                        max = AppDimensions.ChatInputMaxHeight,
                    ),
                enabled = !isStreaming && !isVoiceBusy,
                maxLines = 4,
                textStyle = AppTypography.Body.copy(
                    color = if (!isStreaming && !isVoiceBusy) ChatColors.TextPrimary else ChatColors.TextTertiary,
                ),
                cursorBrush = SolidColor(ChatColors.WarmAccent),
                decorationBox = { innerTextField ->
                    Surface(
                        modifier = Modifier
                            .fillMaxWidth()
                            .heightIn(
                                min = AppDimensions.ChatInputMinHeight,
                                max = AppDimensions.ChatInputMaxHeight,
                        ),
                        shape = RoundedCornerShape(AppRadius.Medium),
                        color = ChatColors.SurfaceSubtle,
                        border = BorderStroke(1.dp, ChatColors.Border),
                    ) {
                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(horizontal = AppSpacing.Md, vertical = 3.dp),
                            contentAlignment = Alignment.CenterStart,
                        ) {
                            if (text.text.isBlank()) {
                                Text(
                                    text = "输入你的需求...",
                                    style = AppTypography.BodySmall,
                                    color = ChatColors.TextTertiary,
                                )
                            }
                            innerTextField()
                        }
                    }
                },
            )

            if (isStreaming) {
                SecondaryButton(
                    text = "停止",
                    onClick = onStop,
                    height = AppDimensions.ButtonSmallHeight,
                )
            } else {
                when (voiceInputState) {
                    VoiceInputState.Recording -> {
                        SecondaryButton(
                            text = "发送语音",
                            onClick = onVoiceClick,
                            height = AppDimensions.ButtonSmallHeight,
                        )
                    }

                    VoiceInputState.Transcribing -> {
                        SecondaryButton(
                            text = "识别中",
                            onClick = {},
                            enabled = false,
                            loading = true,
                            height = AppDimensions.ButtonSmallHeight,
                        )
                    }

                    VoiceInputState.Sending -> {
                        SecondaryButton(
                            text = "发送中",
                            onClick = {},
                            enabled = false,
                            loading = true,
                            height = AppDimensions.ButtonSmallHeight,
                        )
                    }

                    VoiceInputState.Idle,
                    is VoiceInputState.Error -> {
                        AppIconButton(
                            onClick = onVoiceClick,
                            style = AppIconButtonStyle.Plain,
                            containerSize = compactIconContainer,
                            hitAreaSize = compactIconTouch,
                            minimumTouchSize = compactIconTouch,
                            iconSize = AppDimensions.IconSmall,
                            contentColorOverride = ChatColors.TextSecondary,
                        ) {
                            Icon(
                                painter = painterResource(R.drawable.ic_mic_24),
                                contentDescription = "语音输入",
                            )
                        }
                    }
                }
                AppIconButton(
                    enabled = canSend,
                    selected = canSend,
                    onClick = {
                        val content = text.text.trim()
                        if (content.isNotBlank()) {
                            onSend(content)
                            text = TextFieldValue("")
                        }
                    },
                    style = AppIconButtonStyle.Surface,
                    containerSize = compactIconContainer,
                    hitAreaSize = compactIconTouch,
                    minimumTouchSize = compactIconTouch,
                    iconSize = AppDimensions.IconSmall,
                ) {
                    Icon(
                        painter = painterResource(R.drawable.ic_send_24),
                        contentDescription = "发送",
                    )
                }
            }
        }
    }
}
