package com.yourteam.ecommerceguider.data.model

private val RecommendationSplitters = setOf('。', '！', '？', '；', '：', '!', '?', ';', ':', '、', '，', ',')

fun parseRecommendationCopy(raw: String?): RecommendationCopyUiModel {
    val text = raw
        ?.replace(Regex("""\s+"""), " ")
        ?.trim()
        ?.removeRecommendationLeadLabel()
        .orEmpty()
    if (text.isBlank()) {
        return RecommendationCopyUiModel()
    }

    val splitIndex = text.indexOfFirstRecommendationSplitter()
    if (splitIndex >= 0) {
        val title = text.substring(0, splitIndex).trim()
        val reason = text.substring(splitIndex + 1).trim()
        if (title.isUsableRecommendationTitle() && reason.isNotBlank()) {
            return RecommendationCopyUiModel(title = title, reason = reason)
        }
        if (reason.isNotBlank()) {
            return parseRecommendationCopy(reason)
        }
    }

    return if (text.isUsableRecommendationTitle()) {
        RecommendationCopyUiModel(title = text)
    } else {
        RecommendationCopyUiModel(reason = text)
    }
}

fun String?.asRecommendationTitleOrNull(): String? {
    val value = this
        ?.replace(Regex("""\s+"""), " ")
        ?.trim()
        .orEmpty()
    return value.takeIf { it.isUsableRecommendationTitle() }
}

fun String?.sanitizeRecommendReason(): String {
    var result = this
        ?.replace(Regex("""\s+"""), " ")
        ?.trim()
        .orEmpty()
    if (result.isBlank()) {
        return ""
    }
    val redundantSuffixes = listOf(
        "适合优先放进候选卡片里查看。",
        "适合优先放进候选卡片里查看",
        "建议优先放进候选卡片里查看。",
        "建议优先放进候选卡片里查看",
        "可以继续看卡片细节。",
        "可以继续看卡片细节",
        "可以先查看卡片细节。",
        "可以先查看卡片细节",
        "适合点开继续查看。",
        "适合点开继续查看",
        "建议点开卡片确认细节。",
        "建议点开卡片确认细节",
        "下单前可以再看一下卡片细节。",
        "下单前可以再看一下卡片细节",
    )
    redundantSuffixes.forEach { suffix ->
        if (result.endsWith(suffix)) {
            result = result
                .removeSuffix(suffix)
                .trimEnd(' ', '，', ',', '。', '.', '；', ';')
                .trim()
        }
    }
    return result
}

private fun String.indexOfFirstRecommendationSplitter(): Int {
    for (index in indices) {
        val char = this[index]
        if (char == '.' && index > 0 && index < lastIndex && this[index - 1].isDigit() && this[index + 1].isDigit()) {
            continue
        }
        if (char in RecommendationSplitters || char == '.') {
            return index
        }
    }
    return -1
}

private fun String.removeRecommendationLeadLabel(): String {
    return replace(Regex("""^\s*(推荐理由|推荐原因|推荐逻辑|理由|推荐)\s*[:：]\s*"""), "")
        .trim()
}

private fun String.isUsableRecommendationTitle(): Boolean {
    val value = trim()
    if (value.isBlank() || value.equals("null", ignoreCase = true)) {
        return false
    }
    if (value.length !in 4..32) {
        return false
    }
    val normalized = value.replace(Regex("""\s+"""), "")
    if (normalized.startsWith("这款商品") ||
        normalized.startsWith("推荐理由") ||
        normalized.startsWith("为什么适合你")
    ) {
        return false
    }
    if (normalized.matches(Regex("""^方案[一二三四五六七八九十\d]+$""")) ||
        normalized.matches(Regex("""^推荐[一二三四五六七八九十\d]+$""")) ||
        normalized.matches(Regex("""^第[一二三四五六七八九十\d]+个?推荐$"""))
    ) {
        return false
    }
    val blockedTitles = setOf(
        "防晒",
        "手机",
        "护肤",
        "服装",
        "商品推荐",
        "推荐商品",
        "首选方案",
        "备选方案",
        "稳妥选择",
    )
    return normalized !in blockedTitles
}
