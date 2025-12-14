package com.wjx.filler.core

import com.wjx.filler.model.DistributionMode
import com.wjx.filler.model.QuestionEntry
import com.wjx.filler.model.QuestionType
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.jsoup.Jsoup
import org.jsoup.nodes.Document
import org.jsoup.nodes.Element
import java.util.concurrent.TimeUnit

/**
 * 问卷解析器
 * 负责从问卷URL解析题目结构
 */
class SurveyParser {

    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .followRedirects(true)
        .build()

    /**
     * 解析问卷URL，返回题目列表
     */
    suspend fun parseFromUrl(url: String): Result<List<QuestionEntry>> = withContext(Dispatchers.IO) {
        try {
            val html = fetchHtml(url)
            val questions = parseHtml(html)
            Result.success(questions)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * 获取问卷HTML内容
     */
    private fun fetchHtml(url: String): String {
        val request = Request.Builder()
            .url(url)
            .header("User-Agent", USER_AGENT)
            .header("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
            .header("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8")
            .build()

        val response = client.newCall(request).execute()
        if (!response.isSuccessful) {
            throw Exception("HTTP请求失败: ${response.code}")
        }
        return response.body?.string() ?: throw Exception("响应内容为空")
    }

    /**
     * 解析HTML内容，提取题目信息
     */
    private fun parseHtml(html: String): List<QuestionEntry> {
        val document = Jsoup.parse(html)
        val questions = mutableListOf<QuestionEntry>()

        // 查找问卷容器
        val container = document.selectFirst("#divQuestion") ?: return questions

        // 查找所有题目
        val questionDivs = container.select("div[topic]")

        for (div in questionDivs) {
            val question = parseQuestionDiv(div, document)
            if (question != null) {
                questions.add(question)
            }
        }

        return questions
    }

    /**
     * 解析单个题目div
     */
    private fun parseQuestionDiv(div: Element, document: Document): QuestionEntry? {
        val topicAttr = div.attr("topic")
        val typeAttr = div.attr("type")

        if (topicAttr.isBlank()) return null

        val questionNum = topicAttr.toIntOrNull() ?: return null
        val typeCode = typeAttr.trim()

        return when (typeCode) {
            "1", "2" -> parseTextQuestion(div, questionNum, typeCode)
            "3" -> parseSingleChoiceQuestion(div, questionNum)
            "4" -> parseMultipleChoiceQuestion(div, questionNum)
            "5" -> parseScaleQuestion(div, questionNum)
            "6" -> parseMatrixQuestion(div, questionNum, document)
            "7" -> parseDropdownQuestion(div, questionNum, document)
            "8" -> parseSliderQuestion(div, questionNum)
            "11" -> parseOrderQuestion(div, questionNum)
            else -> parseUnknownQuestion(div, questionNum, typeCode)
        }
    }

    /**
     * 解析填空题
     */
    private fun parseTextQuestion(div: Element, questionNum: Int, typeCode: String): QuestionEntry {
        val isLocation = div.selectFirst(".get_Local") != null ||
                div.select("input[verify]").any { 
                    it.attr("verify").contains("地图") || 
                    it.attr("verify").lowercase().contains("map") 
                }

        val inputCount = div.select("input[type='text'], textarea").size

        return QuestionEntry(
            questionType = if (inputCount > 1) QuestionType.MULTI_TEXT else QuestionType.TEXT,
            questionNum = questionNum,
            isLocation = isLocation,
            texts = listOf("无")
        )
    }

    /**
     * 解析单选题
     */
    private fun parseSingleChoiceQuestion(div: Element, questionNum: Int): QuestionEntry {
        val options = div.select(".ui-controlgroup > div")
        val optionCount = options.size.coerceAtLeast(2)

        return QuestionEntry(
            questionType = QuestionType.SINGLE,
            questionNum = questionNum,
            optionCount = optionCount,
            distributionMode = DistributionMode.RANDOM
        )
    }

    /**
     * 解析多选题
     */
    private fun parseMultipleChoiceQuestion(div: Element, questionNum: Int): QuestionEntry {
        val options = div.select(".ui-controlgroup > div")
        val optionCount = options.size.coerceAtLeast(2)

        // 默认每个选项50%概率
        val probabilities = (1..optionCount).map { 50f }

        return QuestionEntry(
            questionType = QuestionType.MULTIPLE,
            questionNum = questionNum,
            optionCount = optionCount,
            probabilities = probabilities,
            distributionMode = DistributionMode.RANDOM
        )
    }

    /**
     * 解析量表题
     */
    private fun parseScaleQuestion(div: Element, questionNum: Int): QuestionEntry {
        val options = div.select(".scale-rating li, .ui-controlgroup li, .ui-controlgroup > div")
        val optionCount = options.size.coerceAtLeast(2)

        return QuestionEntry(
            questionType = QuestionType.SCALE,
            questionNum = questionNum,
            optionCount = optionCount,
            distributionMode = DistributionMode.RANDOM
        )
    }

    /**
     * 解析矩阵题
     */
    private fun parseMatrixQuestion(div: Element, questionNum: Int, document: Document): QuestionEntry {
        // 查找矩阵表格
        val table = document.selectFirst("#divRefTab$questionNum")
        
        var rows = 0
        var columns = 0

        if (table != null) {
            rows = table.select("tr[rowindex]").size
            val headerRow = document.selectFirst("#drv${questionNum}_1")
            if (headerRow != null) {
                columns = headerRow.select("td").size - 1  // 减去第一列标题
            }
        }

        return QuestionEntry(
            questionType = QuestionType.MATRIX,
            questionNum = questionNum,
            optionCount = columns.coerceAtLeast(2),
            rows = rows.coerceAtLeast(1),
            distributionMode = DistributionMode.RANDOM
        )
    }

    /**
     * 解析下拉题
     */
    private fun parseDropdownQuestion(div: Element, questionNum: Int, document: Document): QuestionEntry {
        val select = div.selectFirst("select") ?: document.selectFirst("#q$questionNum")
        val options = select?.select("option") ?: emptyList()
        
        // 过滤掉第一个"请选择"选项
        val validOptions = options.filter { 
            val value = it.attr("value").trim()
            value.isNotEmpty() && value != "0"
        }

        return QuestionEntry(
            questionType = QuestionType.DROPDOWN,
            questionNum = questionNum,
            optionCount = validOptions.size.coerceAtLeast(2),
            distributionMode = DistributionMode.RANDOM
        )
    }

    /**
     * 解析滑块题
     */
    private fun parseSliderQuestion(div: Element, questionNum: Int): QuestionEntry {
        return QuestionEntry(
            questionType = QuestionType.SCALE,  // 滑块题当作量表题处理
            questionNum = questionNum,
            optionCount = 100,
            distributionMode = DistributionMode.RANDOM
        )
    }

    /**
     * 解析排序题
     */
    private fun parseOrderQuestion(div: Element, questionNum: Int): QuestionEntry {
        val items = div.select("ul > li")
        
        return QuestionEntry(
            questionType = QuestionType.SCALE,  // 排序题特殊处理
            questionNum = questionNum,
            optionCount = items.size.coerceAtLeast(2),
            distributionMode = DistributionMode.RANDOM
        )
    }

    /**
     * 解析未知类型题目
     */
    private fun parseUnknownQuestion(div: Element, questionNum: Int, typeCode: String): QuestionEntry? {
        // 尝试检测是否有输入框
        val inputs = div.select("input[type='text'], textarea")
        if (inputs.isNotEmpty()) {
            return QuestionEntry(
                questionType = QuestionType.TEXT,
                questionNum = questionNum,
                texts = listOf("无")
            )
        }

        // 尝试检测是否有选项
        val options = div.select(".ui-controlgroup > div")
        if (options.isNotEmpty()) {
            return QuestionEntry(
                questionType = QuestionType.SINGLE,
                questionNum = questionNum,
                optionCount = options.size,
                distributionMode = DistributionMode.RANDOM
            )
        }

        return null
    }

    /**
     * 提取问卷标题
     */
    fun extractTitle(html: String): String? {
        val document = Jsoup.parse(html)
        
        val selectors = listOf(
            "#divTitle h1",
            "#divTitle",
            ".surveytitle",
            ".survey-title",
            ".htitle",
            "#htitle",
            "title"
        )

        for (selector in selectors) {
            val element = document.selectFirst(selector)
            if (element != null) {
                val text = element.text().trim()
                if (text.isNotBlank()) {
                    return text.replace(Regex("[-|]\\s*问卷星.*$"), "").trim()
                }
            }
        }

        return null
    }

    companion object {
        private const val USER_AGENT = "Mozilla/5.0 (Linux; Android 13; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36"
    }
}