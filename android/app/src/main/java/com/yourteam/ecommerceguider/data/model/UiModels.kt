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
    val title: String? = null,
    val shortTitle: String? = null,
    val optionLabel: String? = null,
    val reason: String? = null,
    val tradeOff: String? = null,
    val status: String = "complete",
    val summary: String? = null,
    val advantages: List<String> = emptyList(),
    val suitableFor: String? = null,
    val keyFeatures: List<String> = emptyList(),
    val matchedNeed: String? = null,
    val usageAdvice: String? = null,
    val bundleRole: String? = null,
    val bundleReason: String? = null,
    val planRole: String? = null,
    val schemeRole: String? = null,
    val usageScenario: String? = null,
    val contentSource: String = "",
)

data class ProductUiModel(
    val skuId: String,
    val productId: String? = null,
    val name: String,
    val title: String? = null,
    val shortTitle: String? = null,
    val recommendationDisplayTitle: String? = null,
    val category: String,
    val brand: String,
    val price: Double,
    val basePrice: Double? = null,
    val stock: Int,
    val imageUrl: String = "",
    val detailImageUrl: String? = null,
    val imagePath: String? = null,
    val subCategory: String? = null,
    val reason: String? = null,
    val recommendTitle: String? = null,
    val recommendReason: String? = null,
    val planRole: String? = null,
    val schemeRole: String? = null,
    val planRoleName: String? = null,
    val planCategoryName: String? = null,
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

    val displayPlanRole: String
        get() = listOfNotNull(
            planRole?.takeIf { it.isNotBlank() },
            schemeRole?.takeIf { it.isNotBlank() },
            presentation?.planRole?.takeIf { it.isNotBlank() },
            presentation?.schemeRole?.takeIf { it.isNotBlank() },
            presentation?.bundleReason?.takeIf { presentation?.type == "bundle" && it.isNotBlank() },
            presentation?.reason?.takeIf { presentation?.type == "bundle" && it.isNotBlank() },
        ).firstOrNull().orEmpty()

    val displayPlanRoleName: String
        get() = listOfNotNull(
            planRoleName?.takeIf { it.isNotBlank() },
            presentation?.bundleRole?.takeIf { it.isNotBlank() },
        ).firstOrNull().orEmpty()

    val displayPlanCategoryName: String
        get() = planCategoryName
            ?.takeIf { it.isNotBlank() }
            ?: subCategory?.takeIf { it.isNotBlank() }
            ?: category

    val isScenarioBundleProduct: Boolean
        get() = presentation?.type == "bundle" || displayPlanRole.isNotBlank()

    val displayTags: List<String>
        get() = (tags + suitableScenarios + targetUserTags)
            .filter { it.isNotBlank() }
            .distinct()
            .take(5)

    val recommendationTags: List<String>
        get() = listOfNotNull(
            presentation?.matchedNeed,
            presentation?.usageScenario,
            presentation?.suitableFor,
            presentation?.bundleRole,
        )
            .plus(presentation?.keyFeatures.orEmpty())
            .plus(presentation?.advantages.orEmpty())
            .plus(tags)
            .plus(suitableScenarios)
            .plus(targetUserTags)
            .plus(nonStandardQueryTags)
            .plus(matchedReasons)
            .mapNotNull { it.toRecommendationTagOrNull() }
            .distinct()
            .take(3)
}

private fun String.toRecommendationTagOrNull(): String? {
    val normalized = trim()
        .removePrefix("匹配")
        .removePrefix("适合")
        .removeSuffix("选择")
        .trim(' ', '，', ',', '。', '.', '：', ':')
    if (normalized.isBlank()) {
        return null
    }
    val mechanicalTags = setOf(
        "类目一致",
        "已排除否定条件",
        "已避开指定品牌",
        "匹配度一般，作为备选",
        "匹配度一般",
        "作为备选",
    )
    if (normalized in mechanicalTags) {
        return null
    }
    if (normalized.length > 12) {
        return null
    }
    return normalized
}

data class CartItemUiModel(
    val cartItemId: String,
    val skuId: String,
    val selectedSkuId: String? = null,
    val selectedSpecs: Map<String, String> = emptyMap(),
    val name: String,
    val price: Double,
    val originalPrice: Double? = null,
    val quantity: Int,
    val imageUrl: String = "",
    val specSummary: String? = null,
    val stock: Int? = null,
) {
    val lineTotal: Double
        get() = price * quantity
}

data class CartItemRestoreSnapshotUiModel(
    val cartItemId: String,
    val skuId: String,
    val selectedSkuId: String? = null,
    val selectedSpecs: Map<String, String> = emptyMap(),
    val name: String,
    val price: Double,
    val originalPrice: Double? = null,
    val quantity: Int,
    val imageUrl: String = "",
    val specSummary: String? = null,
    val stock: Int? = null,
)

fun CartItemUiModel.toRestoreSnapshot(): CartItemRestoreSnapshotUiModel {
    return CartItemRestoreSnapshotUiModel(
        cartItemId = cartItemId,
        skuId = skuId,
        selectedSkuId = selectedSkuId,
        selectedSpecs = selectedSpecs,
        name = name,
        price = price,
        originalPrice = originalPrice,
        quantity = quantity,
        imageUrl = imageUrl,
        specSummary = specSummary,
        stock = stock,
    )
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
    val thinking: AssistantThinkingUiModel? = null,
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
    val displayTitle: String = "",
    val text: String = "",
    val displayText: String = "",
    val recommendReason: String = "",
    val reason: String? = null,
    val tradeOff: String? = null,
    val recommendationTags: List<String> = emptyList(),
    val productName: String? = null,
    val brand: String? = null,
    val product: ProductUiModel? = null,
    val done: Boolean = false,
) {
    val stableKey: String
        get() = "$turnId-$sectionIndex-$skuId"
}

data class RecommendationCopyUiModel(
    val title: String = "",
    val reason: String = "",
)

data class ScenarioPlanItemUiModel(
    val roleName: String,
    val categoryName: String,
    val skuId: String? = null,
    val planRole: String = "",
)

data class ScenarioBundleItemUiModel(
    val role: String,
    val shortReason: String,
    val product: ProductUiModel,
    val roleName: String = role,
    val categoryName: String = product.displayPlanCategoryName,
    val skuId: String = product.skuId,
    val planRole: String = shortReason,
)

data class ScenarioBundleUiModel(
    val turnId: String = "turn_current",
    val title: String = "",
    val summary: String = "",
    val planItems: List<ScenarioPlanItemUiModel> = emptyList(),
    val items: List<ScenarioBundleItemUiModel> = emptyList(),
) {
    val stableKey: String
        get() = "$turnId-scenario-bundle"

    val compositionItems: List<ScenarioPlanItemUiModel>
        get() = planItems.ifEmpty {
            items.map { item ->
                ScenarioPlanItemUiModel(
                    roleName = item.roleName,
                    categoryName = item.categoryName,
                    skuId = item.skuId,
                    planRole = item.planRole,
                )
            }
        }
}

sealed interface VoiceInputState {
    data object Idle : VoiceInputState
    data object Recording : VoiceInputState
    data object Transcribing : VoiceInputState
    data object Sending : VoiceInputState
    data class Error(val message: String) : VoiceInputState
}

sealed interface TtsPlaybackState {
    data object Idle : TtsPlaybackState
    data object Preparing : TtsPlaybackState
    data object Playing : TtsPlaybackState
    data class Error(val message: String) : TtsPlaybackState
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
    val completed: Boolean = false,
    val successText: String? = null,
    val errorText: String? = null,
    val hideOptions: Boolean = false,
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
    val totalDurationMs: Long? = null,
    val responseStreamSupported: Boolean? = null,
    val products: List<ProductUiModel> = emptyList(),
    val cart: CartSnapshotUiModel? = null,
    val errorMessage: String? = null,
    val navigation: BackendNavigationUiModel? = null,
    val product: ProductUiModel? = null,
    val recommendationSection: RecommendationSectionUiModel? = null,
    val scenarioBundle: ScenarioBundleUiModel? = null,
    val specSelection: SpecSelectionUiModel? = null,
)
