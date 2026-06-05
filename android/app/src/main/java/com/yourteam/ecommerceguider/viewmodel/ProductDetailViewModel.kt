package com.yourteam.ecommerceguider.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.yourteam.ecommerceguider.data.model.ProductUiModel
import com.yourteam.ecommerceguider.data.repository.ShoppingRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class ProductDetailViewModel(
    private val repository: ShoppingRepository = ShoppingRepository(),
) : ViewModel() {
    private val _product = MutableStateFlow<ProductUiModel?>(null)
    val product: StateFlow<ProductUiModel?> = _product.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error.asStateFlow()

    private val _cartMessage = MutableStateFlow<String?>(null)
    val cartMessage: StateFlow<String?> = _cartMessage.asStateFlow()

    private var loadedSkuId: String? = null

    fun loadProduct(skuId: String) {
        if (loadedSkuId == skuId && _product.value != null) {
            return
        }

        loadedSkuId = skuId
        viewModelScope.launch {
            _isLoading.value = true
            runCatching { repository.fetchProduct(skuId) }
                .onSuccess { result ->
                    _product.value = result
                    _error.value = if (result == null) "未找到该商品。" else null
                }
                .onFailure {
                    _product.value = null
                    _error.value = "商品详情加载失败，请检查后端服务。"
                }
            _isLoading.value = false
        }
    }

    fun addToCart(skuId: String) {
        viewModelScope.launch {
            runCatching { repository.addToCart(skuId = skuId) }
                .onSuccess { _cartMessage.value = "已加入购物车" }
                .onFailure { _cartMessage.value = "加购失败，请稍后重试" }
        }
    }

    fun clearCartMessage() {
        _cartMessage.value = null
    }
}
