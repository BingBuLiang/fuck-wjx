package com.wjx.filler.core

import android.os.Handler
import android.os.Looper
import android.webkit.WebView
import com.wjx.filler.model.ExecutionResult
import com.wjx.filler.model.ExecutionStatus
import com.wjx.filler.model.QuestionEntry
import com.wjx.filler.model.SurveyConfig
import kotlinx.coroutines.*
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicInteger
import kotlin.random.Random

/**
 * 问卷执行器
 * 负责管理问卷填写任务的执行
 */
class SurveyExecutor(
    private val config: SurveyConfig,
    private val onStatusChange: (ExecutionStatus) -> Unit = {},
    private val onProgressUpdate: (ExecutionResult) -> Unit = {},
    private val onLog: (String, LogLevel) -> Unit = { _, _ -> }
) {

    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())
    private val mainHandler = Handler(Looper.getMainLooper())
    
    private var status = ExecutionStatus.IDLE
    private val stopRequested = AtomicBoolean(false)
    private val successCount = AtomicInteger(0)
    private val failedCount = AtomicInteger(0)
    
    private val filler = SurveyFiller(config.questions)

    /**
     * 开始执行
     */
    fun start(webViewProvider: () -> WebView) {
        if (status == ExecutionStatus.RUNNING) {
            log("任务已在运行中", LogLevel.WARNING)
            return
        }

        stopRequested.set(false)
        successCount.set(0)
        failedCount.set(0)
        
        updateStatus(ExecutionStatus.RUNNING)
        log("开始执行任务，目标: ${config.targetCount}份", LogLevel.INFO)

        scope.launch {
            executeTask(webViewProvider)
        }
    }

    /**
     * 停止执行
     */
    fun stop() {
        if (status != ExecutionStatus.RUNNING) return
        
        stopRequested.set(true)
        updateStatus(ExecutionStatus.STOPPED)
        log("任务已停止", LogLevel.WARNING)
    }

    /**
     * 执行任务
     */
    private suspend fun executeTask(webViewProvider: () -> WebView) {
        val targetCount = config.targetCount
        
        while (!stopRequested.get() && (successCount.get() + failedCount.get()) < targetCount) {
            if (stopRequested.get()) break
            
            try {
                val webView = webViewProvider()
                val success = executeSingleFill(webView)
                
                if (success) {
                    val count = successCount.incrementAndGet()
                    log("[成功] 已完成 $count/${targetCount} 份", LogLevel.SUCCESS)
                } else {
                    val count = failedCount.incrementAndGet()
                    log("[失败] 失败 $count 次", LogLevel.ERROR)
                }
                
                updateProgress()
                
                // 检查是否达到目标
                if (successCount.get() >= targetCount) {
                    break
                }
                
                // 间隔等待
                if (!stopRequested.get() && config.intervalMax > 0) {
                    val interval = if (config.intervalMin == config.intervalMax) {
                        config.intervalMin
                    } else {
                        Random.nextInt(config.intervalMin, config.intervalMax + 1)
                    }
                    if (interval > 0) {
                        log("等待 ${interval} 秒后继续...", LogLevel.INFO)
                        delay(interval * 1000L)
                    }
                }
                
            } catch (e: Exception) {
                failedCount.incrementAndGet()
                log("执行出错: ${e.message}", LogLevel.ERROR)
                updateProgress()
            }
        }
        
        // 完成
        if (!stopRequested.get()) {
            updateStatus(ExecutionStatus.COMPLETED)
            log("任务完成！成功: ${successCount.get()}, 失败: ${failedCount.get()}", LogLevel.SUCCESS)
        }
    }

    /**
     * 执行单次填写
     */
    private suspend fun executeSingleFill(webView: WebView): Boolean = withContext(Dispatchers.Main) {
        try {
            // 加载页面
            loadPage(webView, config.url)
            delay(2000)  // 等待页面加载
            
            // 检查页面状态
            val initialStatus = checkPageStatus(webView)
            if (initialStatus == "quota_exceeded") {
                log("检测到设备已达到最大填写次数", LogLevel.WARNING)
                return@withContext true  // 视为成功
            }
            
            // 填写问卷
            val fillResult = fillSurvey(webView)
            if (!fillResult.startsWith("filled:")) {
                log("填写失败: $fillResult", LogLevel.ERROR)
                return@withContext false
            }
            
            delay(500)
            
            // 点击下一页/提交
            var attempts = 0
            while (attempts < 10 && !stopRequested.get()) {
                val nextResult = clickNext(webView)
                delay(1000)
                
                val status = checkPageStatus(webView)
                if (status == "completed") {
                    return@withContext true
                }
                
                if (nextResult == "submit") {
                    delay(2000)
                    val finalStatus = checkPageStatus(webView)
                    return@withContext finalStatus == "completed"
                }
                
                if (nextResult == "next") {
                    // 继续填写下一页
                    val pageFillResult = fillSurvey(webView)
                    delay(500)
                }
                
                attempts++
            }
            
            false
        } catch (e: Exception) {
            log("填写异常: ${e.message}", LogLevel.ERROR)
            false
        }
    }

    /**
     * 加载页面
     */
    private fun loadPage(webView: WebView, url: String) {
        webView.loadUrl(url)
    }

    /**
     * 填写问卷
     */
    private suspend fun fillSurvey(webView: WebView): String = suspendCancellableCoroutine { cont ->
        val script = filler.generateFillScript()
        webView.evaluateJavascript(script) { result ->
            cont.resume(result?.replace("\"", "") ?: "error:unknown") {}
        }
    }

    /**
     * 点击下一页/提交
     */
    private suspend fun clickNext(webView: WebView): String = suspendCancellableCoroutine { cont ->
        val script = filler.generateNextPageScript()
        webView.evaluateJavascript(script) { result ->
            cont.resume(result?.replace("\"", "") ?: "not_found") {}
        }
    }

    /**
     * 检查页面状态
     */
    private suspend fun checkPageStatus(webView: WebView): String = suspendCancellableCoroutine { cont ->
        val script = filler.generateCheckStatusScript()
        webView.evaluateJavascript(script) { result ->
            cont.resume(result?.replace("\"", "") ?: "unknown") {}
        }
    }

    /**
     * 更新状态
     */
    private fun updateStatus(newStatus: ExecutionStatus) {
        status = newStatus
        mainHandler.post { onStatusChange(newStatus) }
    }

    /**
     * 更新进度
     */
    private fun updateProgress() {
        val result = ExecutionResult(
            success = successCount.get(),
            failed = failedCount.get(),
            total = config.targetCount
        )
        mainHandler.post { onProgressUpdate(result) }
    }

    /**
     * 记录日志
     */
    private fun log(message: String, level: LogLevel) {
        mainHandler.post { onLog(message, level) }
    }

    /**
     * 释放资源
     */
    fun release() {
        stopRequested.set(true)
        scope.cancel()
    }

    /**
     * 获取当前状态
     */
    fun getStatus(): ExecutionStatus = status

    /**
     * 获取当前结果
     */
    fun getResult(): ExecutionResult = ExecutionResult(
        success = successCount.get(),
        failed = failedCount.get(),
        total = config.targetCount
    )
}

/**
 * 日志级别
 */
enum class LogLevel {
    INFO,
    SUCCESS,
    WARNING,
    ERROR
}