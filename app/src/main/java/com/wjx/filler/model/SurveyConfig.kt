package com.wjx.filler.model

import java.io.Serializable

/**
 * 问卷配置数据类
 */
data class SurveyConfig(
    var url: String = "",
    var targetCount: Int = 10,
    var threadCount: Int = 2,
    var intervalMin: Int = 0,
    var intervalMax: Int = 0,
    var questions: MutableList<QuestionEntry> = mutableListOf()
) : Serializable {

    companion object {
        private const val serialVersionUID = 1L
        
        // 最大线程数限制
        const val MAX_THREADS = 12
    }

    /**
     * 验证配置是否有效
     */
    fun isValid(): Boolean {
        return url.isNotBlank() && 
               isValidWjxUrl(url) && 
               targetCount > 0 && 
               threadCount in 1..MAX_THREADS
    }

    /**
     * 检查是否为有效的问卷星链接
     */
    private fun isValidWjxUrl(url: String): Boolean {
        val trimmed = url.trim().lowercase()
        return trimmed.contains("wjx.cn") || trimmed.contains("wjx.top")
    }
}

/**
 * 执行状态
 */
enum class ExecutionStatus {
    IDLE,       // 空闲
    RUNNING,    // 运行中
    PAUSED,     // 暂停
    STOPPED,    // 已停止
    COMPLETED   // 已完成
}

/**
 * 执行结果
 */
data class ExecutionResult(
    val success: Int = 0,
    val failed: Int = 0,
    val total: Int = 0
) {
    val progress: Int
        get() = if (total > 0) ((success + failed) * 100 / total) else 0
}