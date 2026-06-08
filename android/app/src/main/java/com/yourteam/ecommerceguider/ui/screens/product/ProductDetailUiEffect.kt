package com.yourteam.ecommerceguider.ui.screens.product

sealed interface ProductDetailUiEffect {
    data class ShowMessage(val message: String) : ProductDetailUiEffect
}
