package com.yourteam.ecommerceguider.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.yourteam.ecommerceguider.data.model.ProductSkuUiModel
import com.yourteam.ecommerceguider.data.model.ProductUiModel
import com.yourteam.ecommerceguider.data.repository.ShoppingRepository
import com.yourteam.ecommerceguider.ui.screens.product.ProductDetailUiEffect
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
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

    private val _cartItemCount = MutableStateFlow(0)
    val cartItemCount: StateFlow<Int> = _cartItemCount.asStateFlow()

    private val _isAddingToCart = MutableStateFlow(false)
    val isAddingToCart: StateFlow<Boolean> = _isAddingToCart.asStateFlow()

    private val _effects = MutableSharedFlow<ProductDetailUiEffect>(extraBufferCapacity = 1)
    val effects: SharedFlow<ProductDetailUiEffect> = _effects.asSharedFlow()

    private var loadedSkuId: String? = null

    init {
        refreshCartCount()
    }

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

    fun addToCart(product: ProductUiModel, selectedSku: ProductSkuUiModel?) {
        if (_isAddingToCart.value) {
            return
        }
        if (product.stock <= 0) {
            _effects.tryEmit(ProductDetailUiEffect.ShowMessage("暂时缺货"))
            return
        }
        if (product.skus.isNotEmpty() && selectedSku == null) {
            _effects.tryEmit(ProductDetailUiEffect.ShowMessage("请选择商品规格"))
            return
        }
        val selectedSpecs = selectedSku?.properties.orEmpty()
        val specSummary = selectedSpecs.toSpecSummary()
        viewModelScope.launch {
            _isAddingToCart.value = true
            runCatching {
                repository.addToCart(
                    skuId = product.skuId,
                    selectedSkuId = selectedSku?.skuId,
                    selectedSpecs = selectedSpecs,
                    unitPrice = selectedSku?.price ?: product.price,
                    productName = product.displayTitle,
                    imageUrl = product.imageUrl,
                    specSummary = specSummary,
                )
            }
                .onSuccess { snapshot ->
                    _cartItemCount.value = snapshot.totalItems
                    _cartMessage.value = "已加入购物车"
                    _effects.tryEmit(ProductDetailUiEffect.ShowMessage("已加入购物车"))
                }
                .onFailure {
                    _cartMessage.value = "加购失败，请稍后重试"
                    _effects.tryEmit(ProductDetailUiEffect.ShowMessage("加购失败，请稍后重试"))
                }
            _isAddingToCart.value = false
        }
    }

    fun clearCartMessage() {
        _cartMessage.value = null
    }

    private fun refreshCartCount() {
        viewModelScope.launch {
            _cartItemCount.value = runCatching { repository.getCart().totalItems }.getOrDefault(0)
        }
    }

    private fun Map<String, String>.toSpecSummary(): String? {
        return entries
            .filter { it.key.isNotBlank() && it.value.isNotBlank() }
            .sortedBy { it.key }
            .joinToString(" · ") { it.value.trim() }
            .takeIf { it.isNotBlank() }
    }
}
