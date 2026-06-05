package com.yourteam.ecommerceguider.data.model

data class SpotlightUiModel(
    val skinType: List<String> = emptyList(),
    val features: List<String> = emptyList(),
    val exclude: List<String> = emptyList(),
    val description: String = "",
)

data class ProductSkuUiModel(
    val skuId: String,
    val properties: Map<String, String> = emptyMap(),
    val price: Double = 0.0,
)

data class ProductUiModel(
    val skuId: String,
    val productId: String? = null,
    val name: String,
    val title: String? = null,
    val category: String,
    val brand: String,
    val price: Double,
    val basePrice: Double? = null,
    val stock: Int,
    val imageUrl: String = "",
    val imagePath: String? = null,
    val subCategory: String? = null,
    val reason: String? = null,
    val highlightShort: String = "",
    val highlightDetail: String = "",
    val productHighlight: String = "",
    val reviewsSummary: String = "",
    val suitableScenarios: List<String> = emptyList(),
    val targetUserTags: List<String> = emptyList(),
    val nonStandardQueryTags: List<String> = emptyList(),
    val tags: List<String> = emptyList(),
    val matchedReasons: List<String> = emptyList(),
    val skus: List<ProductSkuUiModel> = emptyList(),
    val ragKnowledge: Map<String, String> = emptyMap(),
    val score: Double? = null,
    val spotlight: SpotlightUiModel = SpotlightUiModel(),
) {
    val displayTitle: String
        get() = title?.takeIf { it.isNotBlank() } ?: name

    val displayTitleShort: String
        get() {
            val raw = displayTitle
            return raw
                .replace(Regex("""\d{1,3}\+\d{1,4}GB"""), "")
                .replace(Regex("""\d{1,4}(g|ml|GB|TB|L|kg|颗装|条装|包|片装|粒|盒|英寸)(?![a-zA-Z])"""), "")
                .replace(Regex("""\s{2,}"""), " ")
                .trim()
                .takeIf { it.isNotBlank() } ?: raw
        }

    val displayReason: String
        get() = listOfNotNull(
            reason,
            highlightShort.takeIf { it.isNotBlank() },
            spotlight.description.takeIf { it.isNotBlank() },
            reviewsSummary.takeIf { it.isNotBlank() },
        ).firstOrNull().orEmpty()

    val displayTags: List<String>
        get() = (tags + suitableScenarios + targetUserTags + matchedReasons)
            .filter { it.isNotBlank() }
            .distinct()
            .take(5)
}

data class CartItemUiModel(
    val skuId: String,
    val name: String,
    val price: Double,
    val quantity: Int,
    val imageUrl: String = "",
) {
    val lineTotal: Double
        get() = price * quantity
}

data class CartSnapshotUiModel(
    val items: List<CartItemUiModel> = emptyList(),
    val totalPrice: Double = 0.0,
    val totalItems: Int = 0,
)

enum class AssistantThinkingStatus {
    Idle,
    Started,
    Streaming,
    Done,
}

data class AssistantThinkingUiModel(
    val status: AssistantThinkingStatus = AssistantThinkingStatus.Idle,
    val lines: List<String> = emptyList(),
    val expanded: Boolean = true,
)

data class ChatMessageUiModel(
    val id: String,
    val content: String,
    val isUser: Boolean,
)

data class BackendNavigationUiModel(
    val targetPage: String,
    val skuId: String? = null,
)

data class ChatStreamEvent(
    val event: String,
    val text: String? = null,
    val progressText: String? = null,
    val products: List<ProductUiModel> = emptyList(),
    val cart: CartSnapshotUiModel? = null,
    val errorMessage: String? = null,
    val navigation: BackendNavigationUiModel? = null,
    val product: ProductUiModel? = null,
)
