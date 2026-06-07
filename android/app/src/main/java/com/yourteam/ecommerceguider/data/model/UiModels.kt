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

data class ProductReviewUiModel(
    val rating: Double? = null,
    val nickname: String? = null,
    val createdAt: String? = null,
    val userTags: List<String> = emptyList(),
    val purchased: Boolean? = null,
    val content: String = "",
)

data class ProductPresentationUiModel(
    val type: String = "",
    val optionLabel: String? = null,
    val reason: String? = null,
    val tradeOff: String? = null,
    val status: String = "complete",
    val summary: String? = null,
    val advantages: List<String> = emptyList(),
    val suitableFor: String? = null,
    val contentSource: String = "",
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
    val reviews: List<ProductReviewUiModel> = emptyList(),
    val ragKnowledge: Map<String, String> = emptyMap(),
    val score: Double? = null,
    val spotlight: SpotlightUiModel = SpotlightUiModel(),
    val presentation: ProductPresentationUiModel? = null,
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
            presentation?.reason?.takeIf { it.isNotBlank() },
            presentation?.summary?.takeIf { it.isNotBlank() },
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
    val cartItemId: String,
    val skuId: String,
    val selectedSkuId: String? = null,
    val selectedSpecs: Map<String, String> = emptyMap(),
    val name: String,
    val price: Double,
    val quantity: Int,
    val imageUrl: String = "",
    val specSummary: String? = null,
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
    Running,
    Generating,
    Done,
    Failed,
}

enum class AssistantProcessStageStatus {
    Pending,
    Running,
    Completed,
    Failed,
}

data class AssistantProcessStageUiModel(
    val stageId: String,
    val displayLabel: String,
    val status: AssistantProcessStageStatus = AssistantProcessStageStatus.Pending,
    val startedElapsedMs: Long? = null,
    val durationMs: Long? = null,
    val summary: String? = null,
)

data class AssistantThinkingUiModel(
    val status: AssistantThinkingStatus = AssistantThinkingStatus.Idle,
    val stages: List<AssistantProcessStageUiModel> = emptyList(),
    val expanded: Boolean = true,
    val previewText: String = "",
    val totalElapsedMs: Long = 0L,
    val isGeneratingResponse: Boolean = false,
    val responseStreamSupported: Boolean = false,
)

data class ChatMessageUiModel(
    val id: String,
    val turnId: String = "",
    val content: String,
    val isUser: Boolean,
    val isStreaming: Boolean = false,
    val timestamp: Long = System.currentTimeMillis(),
)

data class BackendNavigationUiModel(
    val targetPage: String,
    val skuId: String? = null,
)

data class RecommendationSectionUiModel(
    val eventId: String? = null,
    val requestId: String? = null,
    val sequence: Long? = null,
    val turnId: String,
    val sectionIndex: Int,
    val skuId: String,
    val optionLabel: String,
    val text: String = "",
    val displayText: String = "",
    val reason: String? = null,
    val tradeOff: String? = null,
    val productName: String? = null,
    val brand: String? = null,
    val product: ProductUiModel? = null,
    val done: Boolean = false,
) {
    val stableKey: String
        get() = "$turnId-$sectionIndex-$skuId"
}

data class SpecSelectionOptionUiModel(
    val productId: String,
    val skuId: String,
    val specText: String,
    val selectedSpecs: Map<String, String> = emptyMap(),
    val price: Double = 0.0,
    val stock: Int? = null,
    val available: Boolean = true,
)

data class SpecSelectionUiModel(
    val id: String,
    val turnId: String,
    val productId: String,
    val productName: String,
    val imageUrl: String = "",
    val quantity: Int = 1,
    val options: List<SpecSelectionOptionUiModel> = emptyList(),
    val selectedSkuId: String? = null,
    val source: String = "chat_intent",
    val anchorProductId: String? = null,
    val anchorSkuId: String? = null,
    val anchorRecommendationId: String? = null,
) {
    val stableKey: String
        get() = "$turnId-$id"
}

data class ChatStreamEvent(
    val event: String,
    val requestId: String? = null,
    val sequence: Long? = null,
    val text: String? = null,
    val progressText: String? = null,
    val progressStageId: String? = null,
    val progressDisplayLabel: String? = null,
    val progressSummary: String? = null,
    val stageDurationMs: Long? = null,
    val totalDurationMs: Long? = null,
    val responseStreamSupported: Boolean? = null,
    val products: List<ProductUiModel> = emptyList(),
    val cart: CartSnapshotUiModel? = null,
    val errorMessage: String? = null,
    val navigation: BackendNavigationUiModel? = null,
    val product: ProductUiModel? = null,
    val recommendationSection: RecommendationSectionUiModel? = null,
    val specSelection: SpecSelectionUiModel? = null,
)
