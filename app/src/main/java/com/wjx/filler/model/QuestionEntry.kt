package com.wjx.filler.model

import java.io.Serializable

/**
 * 题目配置数据类
 */
data class QuestionEntry(
    var questionType: QuestionType = QuestionType.SINGLE,
    var optionCount: Int = 4,
    var rows: Int = 1,  // 矩阵题行数
    var distributionMode: DistributionMode = DistributionMode.RANDOM,
    var customWeights: List<Float>? = null,  // 自定义权重
    var probabilities: List<Float>? = null,  // 多选题各选项概率
    var texts: List<String>? = null,  // 填空题答案列表
    var questionNum: Int = 0,  // 题号
    var isLocation: Boolean = false  // 是否为位置题
) : Serializable {

    /**
     * 获取题目摘要描述
     */
    fun getSummary(): String {
        return when (questionType) {
            QuestionType.TEXT, QuestionType.MULTI_TEXT -> {
                val samples = texts?.take(3)?.joinToString(" | ") ?: "未设置"
                if (isLocation) "位置题: $samples" else "填空题: $samples"
            }
            QuestionType.MATRIX -> {
                val modeText = distributionMode.displayName
                "${rows}行 × ${optionCount}列 - $modeText"
            }
            QuestionType.MULTIPLE -> {
                if (distributionMode == DistributionMode.RANDOM) {
                    "${optionCount}个选项 - 随机多选"
                } else {
                    val weights = probabilities?.map { "${it.toInt()}%" }?.joinToString(",") ?: ""
                    "${optionCount}个选项 - 权重 $weights"
                }
            }
            else -> {
                val modeText = distributionMode.displayName
                if (distributionMode == DistributionMode.CUSTOM && customWeights != null) {
                    val weightsStr = customWeights!!.map { 
                        if (it == it.toInt().toFloat()) it.toInt().toString() 
                        else String.format("%.1f", it) 
                    }.joinToString(":")
                    "${optionCount}个选项 - 配比 $weightsStr"
                } else {
                    "${optionCount}个选项 - $modeText"
                }
            }
        }
    }

    companion object {
        private const val serialVersionUID = 1L
    }
}

/**
 * 题目类型枚举
 */
enum class QuestionType(val displayName: String, val code: String) {
    SINGLE("单选题", "single"),
    MULTIPLE("多选题", "multiple"),
    DROPDOWN("下拉题", "dropdown"),
    MATRIX("矩阵题", "matrix"),
    SCALE("量表题", "scale"),
    TEXT("填空题", "text"),
    MULTI_TEXT("多项填空题", "multi_text"),
    LOCATION("位置题", "location");

    companion object {
        fun fromCode(code: String): QuestionType {
            return values().find { it.code == code } ?: SINGLE
        }

        fun fromDisplayName(name: String): QuestionType {
            return values().find { it.displayName == name } ?: SINGLE
        }
    }
}

/**
 * 分布模式枚举
 */
enum class DistributionMode(val displayName: String) {
    RANDOM("完全随机"),
    EQUAL("平均分配"),
    CUSTOM("自定义配比")
}