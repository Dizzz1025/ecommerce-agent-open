package com.yourteam.ecommerceguider.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.input.TextFieldValue
import androidx.compose.ui.unit.dp
import com.yourteam.ecommerceguider.R

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

    Row(
        modifier = modifier
            .fillMaxWidth()
            .spatialGlass(
                shape = RoundedCornerShape(30.dp),
                fillColor = SpatialGlassColorDock,
                elevation = 4.dp,
            )
            .padding(horizontal = 11.dp, vertical = 9.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        IconButton(
            onClick = onImageClick,
            enabled = !isStreaming,
            modifier = Modifier
                .size(44.dp)
                .background(SpatialGlassControl, RoundedCornerShape(16.dp)),
        ) {
            Icon(
                painter = painterResource(R.drawable.ic_photo_24),
                contentDescription = "拍图找同款",
                tint = if (isStreaming) {
                    SpatialTextPlaceholder
                } else {
                    SpatialIconNeutral
                },
            )
        }
        OutlinedTextField(
            value = text,
            onValueChange = { text = it },
            modifier = Modifier.weight(1f),
            enabled = !isStreaming,
            shape = RoundedCornerShape(20.dp),
            maxLines = 4,
            placeholder = { Text("输入你的需求") },
            colors = OutlinedTextFieldDefaults.colors(
                focusedContainerColor = SpatialGlassControl,
                unfocusedContainerColor = SpatialGlassControlMuted,
                disabledContainerColor = SpatialGlassControlDisabled,
                focusedBorderColor = SpatialAccentBlue.copy(alpha = 0.32f),
                unfocusedBorderColor = SpatialGlassBorderColor,
                disabledBorderColor = SpatialGlassControl,
                focusedTextColor = SpatialTextBody,
                unfocusedTextColor = SpatialTextBody,
                cursorColor = SpatialAccent,
            ),
        )
        if (isStreaming) {
            OutlinedButton(
                onClick = onStop,
                shape = RoundedCornerShape(18.dp),
                colors = ButtonDefaults.outlinedButtonColors(
                    containerColor = SpatialGlassControl,
                    contentColor = SpatialAccent,
                ),
            ) {
                Text("停止")
            }
        } else {
            IconButton(
                onClick = onVoiceClick,
                modifier = Modifier
                    .size(44.dp)
                    .background(SpatialGlassControl, RoundedCornerShape(16.dp)),
            ) {
                Icon(
                    painter = painterResource(R.drawable.ic_mic_24),
                    contentDescription = "语音输入",
                    tint = SpatialIconNeutral,
                )
            }
            IconButton(
                enabled = canSend,
                onClick = {
                    val content = text.text.trim()
                    if (content.isNotBlank()) {
                        onSend(content)
                        text = TextFieldValue("")
                    }
                },
                modifier = if (canSend) {
                    Modifier
                        .size(44.dp)
                        .background(SpatialPrimaryGradient, CircleShape)
                } else {
                    Modifier
                        .size(44.dp)
                        .background(SpatialGlassControl, CircleShape)
                },
            ) {
                Icon(
                    painter = painterResource(R.drawable.ic_send_24),
                    contentDescription = "发送",
                    tint = if (canSend) {
                        Color.White
                    } else {
                        SpatialTextPlaceholder
                    },
                )
            }
        }
    }
}
