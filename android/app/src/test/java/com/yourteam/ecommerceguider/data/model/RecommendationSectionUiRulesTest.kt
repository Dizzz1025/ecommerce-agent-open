package com.yourteam.ecommerceguider.data.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class RecommendationSectionUiRulesTest {
    @Test
    fun incomingBlankDisplayTitleDoesNotClearExistingTitle() {
        val displayTitle = "\u901a\u52e4\u4e0e\u6237\u5916\u517c\u987e\u7684\u9ad8\u500d\u9632\u6652"
        val productCardSection = section(displayTitle = displayTitle)
        val reasonDeltaSection = section(displayTitle = "", text = "\u63a8\u8350\u7406\u7531\u589e\u91cf")

        val mergedTitle = mergeRecommendationDisplayTitle(
            existing = productCardSection.displayTitle,
            incoming = reasonDeltaSection.displayTitle,
        )

        assertEquals(displayTitle, mergedTitle)
    }

    @Test
    fun laterProductCardTitleMergesIntoExistingReasonSection() {
        val displayTitle = "\u901a\u52e4\u4e0e\u6237\u5916\u517c\u987e\u7684\u9ad8\u500d\u9632\u6652"
        val reasonDeltaSection = section(displayTitle = "", text = "\u63a8\u8350\u7406\u7531\u589e\u91cf")
        val productCardSection = section(displayTitle = displayTitle)

        val mergedTitle = mergeRecommendationDisplayTitle(
            existing = reasonDeltaSection.displayTitle,
            incoming = productCardSection.displayTitle,
        )

        assertEquals(displayTitle, mergedTitle)
    }

    @Test
    fun sectionTitleForRenderUsesDisplayTitleOnly() {
        val displayTitle = "\u901a\u52e4\u4e0e\u6237\u5916\u517c\u987e\u7684\u9ad8\u500d\u9632\u6652"

        assertEquals(displayTitle, recommendationSectionTitleForRender(section(displayTitle = displayTitle)))
        assertNull(recommendationSectionTitleForRender(section(displayTitle = "")))
    }

    private fun section(
        displayTitle: String,
        text: String = "",
    ): RecommendationSectionUiModel {
        return RecommendationSectionUiModel(
            turnId = "turn_1",
            sectionIndex = 0,
            skuId = "sku_1",
            optionLabel = "",
            displayTitle = displayTitle,
            text = text,
        )
    }
}
