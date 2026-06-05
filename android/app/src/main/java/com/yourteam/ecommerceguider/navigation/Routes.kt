package com.yourteam.ecommerceguider.navigation

sealed class Routes(val route: String) {
    data object Chat : Routes("chat")
    data object ProductDetail : Routes("product/{skuId}") {
        fun create(skuId: String) = "product/$skuId"
    }

    data object Cart : Routes("cart")
    data object Checkout : Routes("checkout")
    data object OrderResult : Routes("order-result")
    data object ImageSearch : Routes("image-search")
    data object Address : Routes("address")
}
