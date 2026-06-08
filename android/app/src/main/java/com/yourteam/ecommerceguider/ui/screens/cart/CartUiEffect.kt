package com.yourteam.ecommerceguider.ui.screens.cart

sealed interface CartUiEffect {
    data class ShowMessage(
        val message: String,
        val cartItemId: String? = null,
    ) : CartUiEffect

    data class ItemRemoved(
        val cartItemId: String,
        val message: String = "已删除商品",
    ) : CartUiEffect
}
