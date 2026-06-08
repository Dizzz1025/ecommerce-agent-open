package com.yourteam.ecommerceguider.ui.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.input.TextFieldValue
import androidx.compose.ui.unit.dp
import com.yourteam.ecommerceguider.R
import com.yourteam.ecommerceguider.theme.AppColors
import com.yourteam.ecommerceguider.theme.AppDimensions
import com.yourteam.ecommerceguider.theme.AppRadius
import com.yourteam.ecommerceguider.theme.AppSpacing
import com.yourteam.ecommerceguider.theme.AppTypography

@Composable
fun ChatInputBar(
    onSend: (String) -> Unit,
    onStop: () -> Unit,
    onImageClick: () -> Unit,
    onVoiceClick: () -> Unit,
    isStreaming: Boolean,
    modifier: Modifier = Modifier,
) {
    var text by remember { mutableStateOf(TextFieldValue("")) }
    val canSend = text.text.isNotBlank() && !isStreaming

    Surface(
        modifier = modifier
            .fillMaxWidth(),
        shape = RoundedCornerShape(AppRadius.Large),
        color = AppColors.Surface,
        border = androidx.compose.foundation.BorderStroke(
            width = 1.dp,
            color = AppColors.Border,
        ),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = AppSpacing.Sm, vertical = AppSpacing.Xs),
            horizontalArrangement = Arrangement.spacedBy(AppSpacing.Xs),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            AppIconButton(
                onClick = onImageClick,
                enabled = !isStreaming,
                style = AppIconButtonStyle.Plain,
                containerSize = AppDimensions.IconButtonSmall,
                iconSize = AppDimensions.IconSmall,
            ) {
                Icon(
                    painter = painterResource(R.drawable.ic_photo_24),
                    contentDescription = "拍图找同款",
                )
            }

            OutlinedTextField(
                value = text,
                onValueChange = { text = it },
                modifier = Modifier
                    .weight(1f)
                    .heightIn(
                        min = AppDimensions.ChatInputMinHeight,
                        max = AppDimensions.ChatInputMaxHeight,
                    ),
                enabled = !isStreaming,
                shape = RoundedCornerShape(AppRadius.Medium),
                maxLines = 4,
                placeholder = {
                    Text(
                        text = "输入你的需求",
                        style = AppTypography.BodySmall,
                        color = AppColors.TextTertiary,
                    )
                },
                textStyle = AppTypography.Body,
                colors = OutlinedTextFieldDefaults.colors(
                    focusedContainerColor = AppColors.SurfaceSoft,
                    unfocusedContainerColor = AppColors.SurfaceSoft,
                    disabledContainerColor = AppColors.SurfacePressed,
                    focusedBorderColor = AppColors.BorderStrong,
                    unfocusedBorderColor = AppColors.Border,
                    disabledBorderColor = AppColors.Border,
                    focusedTextColor = AppColors.TextPrimary,
                    unfocusedTextColor = AppColors.TextPrimary,
                    disabledTextColor = AppColors.TextDisabled,
                    cursorColor = AppColors.Primary,
                ),
            )

            if (isStreaming) {
                SecondaryButton(
                    text = "停止",
                    onClick = onStop,
                    height = AppDimensions.ButtonSmallHeight,
                )
            } else {
                AppIconButton(
                    onClick = onVoiceClick,
                    style = AppIconButtonStyle.Plain,
                    containerSize = AppDimensions.IconButtonSmall,
                    iconSize = AppDimensions.IconSmall,
                ) {
                    Icon(
                        painter = painterResource(R.drawable.ic_mic_24),
                        contentDescription = "语音输入",
                    )
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
                    containerSize = AppDimensions.IconButtonSmall,
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
