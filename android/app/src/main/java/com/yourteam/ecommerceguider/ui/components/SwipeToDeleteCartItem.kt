package com.yourteam.ecommerceguider.ui.components

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.Orientation
import androidx.compose.foundation.gestures.draggable
import androidx.compose.foundation.gestures.rememberDraggableState
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.zIndex
import com.yourteam.ecommerceguider.R
import com.yourteam.ecommerceguider.theme.AppColors
import com.yourteam.ecommerceguider.theme.AppDimensions
import com.yourteam.ecommerceguider.theme.AppMotion
import com.yourteam.ecommerceguider.theme.AppRadius
import kotlinx.coroutines.launch
import kotlin.math.roundToInt

@Composable
fun SwipeToDeleteCartItem(
    isOpen: Boolean,
    onOpenRequest: () -> Unit,
    onCloseRequest: () -> Unit,
    onDeleteClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    shape: Shape = RoundedCornerShape(AppRadius.Card),
    content: @Composable BoxScope.() -> Unit,
) {
    val scope = rememberCoroutineScope()
    val actionWidthPx = with(LocalDensity.current) { AppDimensions.SwipeDeleteActionWidth.toPx() }
    val offsetX = remember { Animatable(0f) }
    var isDragging by remember { mutableStateOf(false) }

    LaunchedEffect(isOpen, actionWidthPx) {
        if (!isDragging) {
            offsetX.animateTo(
                targetValue = if (isOpen) -actionWidthPx else 0f,
                animationSpec = tween(
                    durationMillis = AppMotion.Normal,
                    easing = AppMotion.StandardEasing,
                ),
            )
        }
    }

    val draggableState = rememberDraggableState { delta ->
        if (!enabled) {
            return@rememberDraggableState
        }
        scope.launch {
            offsetX.snapTo((offsetX.value + delta).coerceIn(-actionWidthPx, 0f))
        }
    }

    Box(
        modifier = modifier
            .fillMaxWidth()
            .clip(shape),
    ) {
        Box(
            modifier = Modifier.matchParentSize(),
            contentAlignment = Alignment.CenterEnd,
        ) {
            CompactDeleteAction(
                onClick = onDeleteClick,
                enabled = enabled,
                modifier = Modifier
                    .width(AppDimensions.SwipeDeleteActionWidth)
                    .fillMaxHeight(),
            )
        }

        Box(
            modifier = Modifier
                .fillMaxWidth()
                .zIndex(1f)
                .offset { IntOffset(offsetX.value.roundToInt(), 0) }
                .draggable(
                    state = draggableState,
                    orientation = Orientation.Horizontal,
                    enabled = enabled,
                    onDragStarted = {
                        isDragging = true
                        onOpenRequest()
                    },
                    onDragStopped = {
                        isDragging = false
                        scope.launch {
                            val shouldOpen = offsetX.value <= -actionWidthPx / 2f
                            if (shouldOpen) {
                                onOpenRequest()
                                offsetX.animateTo(
                                    targetValue = -actionWidthPx,
                                    animationSpec = tween(
                                        durationMillis = AppMotion.Normal,
                                        easing = AppMotion.StandardEasing,
                                    ),
                                )
                            } else {
                                onCloseRequest()
                                offsetX.animateTo(
                                    targetValue = 0f,
                                    animationSpec = tween(
                                        durationMillis = AppMotion.Normal,
                                        easing = AppMotion.StandardEasing,
                                    ),
                                )
                            }
                        }
                    },
                ),
            content = content,
        )
    }
}

@Composable
fun CompactDeleteAction(
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
) {
    Box(
        modifier = modifier
            .background(AppColors.DangerSoft),
        contentAlignment = Alignment.Center,
    ) {
        Box(
            modifier = Modifier
                .size(AppDimensions.MinimumTouchTarget)
                .clickable(
                    enabled = enabled,
                    role = Role.Button,
                    onClick = onClick,
                ),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                painter = painterResource(R.drawable.ic_trash_20),
                contentDescription = "删除商品",
                tint = AppColors.Danger,
                modifier = Modifier.size(AppDimensions.SwipeDeleteIconSize),
            )
        }
    }
}
