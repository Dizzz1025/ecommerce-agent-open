package com.yourteam.ecommerceguider.data.model

internal fun mergeRecommendationDisplayTitle(existing: String, incoming: String): String {
    val normalizedIncoming = incoming.trim()
    return normalizedIncoming.ifBlank { existing }
}

internal fun recommendationSectionTitleForRender(section: RecommendationSectionUiModel): String? {
    return section.displayTitle.asRecommendationTitleOrNull()
}
