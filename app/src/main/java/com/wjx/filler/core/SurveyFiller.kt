package com.wjx.filler.core

import android.webkit.JavascriptInterface
import android.webkit.WebView
import com.wjx.filler.model.DistributionMode
import com.wjx.filler.model.QuestionEntry
import com.wjx.filler.model.QuestionType
import kotlin.random.Random

/**
 * 问卷填写核心引擎
 * 负责在WebView中自动填写问卷
 */
class SurveyFiller(
    private val questions: List<QuestionEntry>,
    private val onLog: (String) -> Unit = {},
    private val onComplete: (Boolean) -> Unit = {}
) {

    private var currentQuestionIndex = 0
    private var singleIndex = 0
    private var multipleIndex = 0
    private var dropdownIndex = 0
    private var matrixIndex = 0
    private var scaleIndex = 0
    private var textIndex = 0

    /**
     * 生成填写问卷的JavaScript代码
     */
    fun generateFillScript(): String {
        return buildString {
            append("(function() {\n")
            append("  try {\n")
            append("    var questions = document.querySelectorAll('#divQuestion fieldset > div[topic]');\n")
            append("    var filled = 0;\n")
            append("    \n")
            
            // 遍历所有题目
            append("    questions.forEach(function(q, index) {\n")
            append("      var type = q.getAttribute('type');\n")
            append("      var topic = q.getAttribute('topic');\n")
            append("      \n")
            
            // 根据题型填写
            append("      switch(type) {\n")
            
            // 填空题 (type 1, 2)
            append("        case '1':\n")
            append("        case '2':\n")
            append("          fillTextQuestion(q, topic);\n")
            append("          filled++;\n")
            append("          break;\n")
            
            // 单选题 (type 3)
            append("        case '3':\n")
            append("          fillSingleChoice(q, topic);\n")
            append("          filled++;\n")
            append("          break;\n")
            
            // 多选题 (type 4)
            append("        case '4':\n")
            append("          fillMultipleChoice(q, topic);\n")
            append("          filled++;\n")
            append("          break;\n")
            
            // 量表题 (type 5)
            append("        case '5':\n")
            append("          fillScaleQuestion(q, topic);\n")
            append("          filled++;\n")
            append("          break;\n")
            
            // 矩阵题 (type 6)
            append("        case '6':\n")
            append("          fillMatrixQuestion(q, topic);\n")
            append("          filled++;\n")
            append("          break;\n")
            
            // 下拉题 (type 7)
            append("        case '7':\n")
            append("          fillDropdownQuestion(q, topic);\n")
            append("          filled++;\n")
            append("          break;\n")
            
            // 滑块题 (type 8)
            append("        case '8':\n")
            append("          fillSliderQuestion(q, topic);\n")
            append("          filled++;\n")
            append("          break;\n")
            
            // 排序题 (type 11)
            append("        case '11':\n")
            append("          fillOrderQuestion(q, topic);\n")
            append("          filled++;\n")
            append("          break;\n")
            
            append("      }\n")
            append("    });\n")
            append("    \n")
            append("    return 'filled:' + filled;\n")
            append("  } catch(e) {\n")
            append("    return 'error:' + e.message;\n")
            append("  }\n")
            append("})();\n")
            append("\n")
            
            // 填空题函数
            append(generateTextFillFunction())
            
            // 单选题函数
            append(generateSingleChoiceFunction())
            
            // 多选题函数
            append(generateMultipleChoiceFunction())
            
            // 量表题函数
            append(generateScaleFunction())
            
            // 矩阵题函数
            append(generateMatrixFunction())
            
            // 下拉题函数
            append(generateDropdownFunction())
            
            // 滑块题函数
            append(generateSliderFunction())
            
            // 排序题函数
            append(generateOrderFunction())
        }
    }

    /**
     * 生成填空题填写函数
     */
    private fun generateTextFillFunction(): String {
        val textQuestions = questions.filter { 
            it.questionType == QuestionType.TEXT || 
            it.questionType == QuestionType.MULTI_TEXT ||
            it.questionType == QuestionType.LOCATION
        }
        
        return buildString {
            append("function fillTextQuestion(q, topic) {\n")
            append("  var inputs = q.querySelectorAll('input[type=\"text\"], textarea');\n")
            append("  var texts = ${generateTextArray(textQuestions)};\n")
            append("  var idx = parseInt(topic) - 1;\n")
            append("  if (idx >= 0 && idx < texts.length && texts[idx]) {\n")
            append("    var answers = texts[idx];\n")
            append("    var answer = answers[Math.floor(Math.random() * answers.length)];\n")
            append("    inputs.forEach(function(input, i) {\n")
            append("      if (answer.indexOf('||') > -1) {\n")
            append("        var parts = answer.split('||');\n")
            append("        input.value = parts[i] || parts[0];\n")
            append("      } else {\n")
            append("        input.value = answer;\n")
            append("      }\n")
            append("      input.dispatchEvent(new Event('input', {bubbles: true}));\n")
            append("      input.dispatchEvent(new Event('change', {bubbles: true}));\n")
            append("    });\n")
            append("  } else {\n")
            append("    inputs.forEach(function(input) {\n")
            append("      input.value = '无';\n")
            append("      input.dispatchEvent(new Event('input', {bubbles: true}));\n")
            append("    });\n")
            append("  }\n")
            append("}\n\n")
        }
    }

    /**
     * 生成单选题填写函数
     */
    private fun generateSingleChoiceFunction(): String {
        val singleQuestions = questions.filter { it.questionType == QuestionType.SINGLE }
        
        return buildString {
            append("function fillSingleChoice(q, topic) {\n")
            append("  var options = q.querySelectorAll('.ui-controlgroup > div');\n")
            append("  if (options.length === 0) return;\n")
            append("  var configs = ${generateProbabilityArray(singleQuestions)};\n")
            append("  var idx = parseInt(topic) - 1;\n")
            append("  var selected;\n")
            append("  if (idx >= 0 && idx < configs.length && configs[idx]) {\n")
            append("    selected = weightedRandom(configs[idx]);\n")
            append("  } else {\n")
            append("    selected = Math.floor(Math.random() * options.length);\n")
            append("  }\n")
            append("  if (selected < options.length) {\n")
            append("    options[selected].click();\n")
            append("  }\n")
            append("}\n\n")
            
            // 加权随机函数
            append("function weightedRandom(weights) {\n")
            append("  if (!weights || weights.length === 0) return 0;\n")
            append("  var total = weights.reduce(function(a, b) { return a + b; }, 0);\n")
            append("  if (total <= 0) return Math.floor(Math.random() * weights.length);\n")
            append("  var r = Math.random() * total;\n")
            append("  var sum = 0;\n")
            append("  for (var i = 0; i < weights.length; i++) {\n")
            append("    sum += weights[i];\n")
            append("    if (r <= sum) return i;\n")
            append("  }\n")
            append("  return weights.length - 1;\n")
            append("}\n\n")
        }
    }

    /**
     * 生成多选题填写函数
     */
    private fun generateMultipleChoiceFunction(): String {
        val multipleQuestions = questions.filter { it.questionType == QuestionType.MULTIPLE }
        
        return buildString {
            append("function fillMultipleChoice(q, topic) {\n")
            append("  var options = q.querySelectorAll('.ui-controlgroup > div');\n")
            append("  if (options.length === 0) return;\n")
            append("  var configs = ${generateMultipleProbabilityArray(multipleQuestions)};\n")
            append("  var idx = parseInt(topic) - 1;\n")
            append("  var selected = [];\n")
            append("  if (idx >= 0 && idx < configs.length && configs[idx]) {\n")
            append("    var probs = configs[idx];\n")
            append("    for (var i = 0; i < Math.min(probs.length, options.length); i++) {\n")
            append("      if (Math.random() * 100 < probs[i]) {\n")
            append("        selected.push(i);\n")
            append("      }\n")
            append("    }\n")
            append("  }\n")
            append("  if (selected.length === 0) {\n")
            append("    selected.push(Math.floor(Math.random() * options.length));\n")
            append("  }\n")
            append("  selected.forEach(function(i) {\n")
            append("    if (i < options.length) options[i].click();\n")
            append("  });\n")
            append("}\n\n")
        }
    }

    /**
     * 生成量表题填写函数
     */
    private fun generateScaleFunction(): String {
        val scaleQuestions = questions.filter { it.questionType == QuestionType.SCALE }
        
        return buildString {
            append("function fillScaleQuestion(q, topic) {\n")
            append("  var options = q.querySelectorAll('.scale-rating li, .ui-controlgroup li');\n")
            append("  if (options.length === 0) return;\n")
            append("  var configs = ${generateProbabilityArray(scaleQuestions)};\n")
            append("  var idx = parseInt(topic) - 1;\n")
            append("  var selected;\n")
            append("  if (idx >= 0 && idx < configs.length && configs[idx]) {\n")
            append("    selected = weightedRandom(configs[idx]);\n")
            append("  } else {\n")
            append("    selected = Math.floor(Math.random() * options.length);\n")
            append("  }\n")
            append("  if (selected < options.length) {\n")
            append("    options[selected].click();\n")
            append("  }\n")
            append("}\n\n")
        }
    }

    /**
     * 生成矩阵题填写函数
     */
    private fun generateMatrixFunction(): String {
        val matrixQuestions = questions.filter { it.questionType == QuestionType.MATRIX }
        
        return buildString {
            append("function fillMatrixQuestion(q, topic) {\n")
            append("  var rows = q.querySelectorAll('tbody tr[rowindex]');\n")
            append("  var configs = ${generateProbabilityArray(matrixQuestions)};\n")
            append("  var idx = parseInt(topic) - 1;\n")
            append("  rows.forEach(function(row) {\n")
            append("    var cells = row.querySelectorAll('td');\n")
            append("    if (cells.length <= 1) return;\n")
            append("    var selected;\n")
            append("    if (idx >= 0 && idx < configs.length && configs[idx]) {\n")
            append("      selected = weightedRandom(configs[idx]) + 1;\n")
            append("    } else {\n")
            append("      selected = Math.floor(Math.random() * (cells.length - 1)) + 1;\n")
            append("    }\n")
            append("    if (selected < cells.length) {\n")
            append("      cells[selected].click();\n")
            append("    }\n")
            append("  });\n")
            append("}\n\n")
        }
    }

    /**
     * 生成下拉题填写函数
     */
    private fun generateDropdownFunction(): String {
        val dropdownQuestions = questions.filter { it.questionType == QuestionType.DROPDOWN }
        
        return buildString {
            append("function fillDropdownQuestion(q, topic) {\n")
            append("  var select = q.querySelector('select');\n")
            append("  if (!select) return;\n")
            append("  var options = select.querySelectorAll('option');\n")
            append("  if (options.length <= 1) return;\n")
            append("  var configs = ${generateProbabilityArray(dropdownQuestions)};\n")
            append("  var idx = parseInt(topic) - 1;\n")
            append("  var selected;\n")
            append("  if (idx >= 0 && idx < configs.length && configs[idx]) {\n")
            append("    selected = weightedRandom(configs[idx]) + 1;\n")
            append("  } else {\n")
            append("    selected = Math.floor(Math.random() * (options.length - 1)) + 1;\n")
            append("  }\n")
            append("  if (selected < options.length) {\n")
            append("    select.selectedIndex = selected;\n")
            append("    select.dispatchEvent(new Event('change', {bubbles: true}));\n")
            append("  }\n")
            append("}\n\n")
        }
    }

    /**
     * 生成滑块题填写函数
     */
    private fun generateSliderFunction(): String {
        return buildString {
            append("function fillSliderQuestion(q, topic) {\n")
            append("  var input = q.querySelector('input[type=\"hidden\"], input[type=\"text\"]');\n")
            append("  if (!input) return;\n")
            append("  var value = Math.floor(Math.random() * 100) + 1;\n")
            append("  input.value = value;\n")
            append("  input.dispatchEvent(new Event('input', {bubbles: true}));\n")
            append("  input.dispatchEvent(new Event('change', {bubbles: true}));\n")
            append("}\n\n")
        }
    }

    /**
     * 生成排序题填写函数
     */
    private fun generateOrderFunction(): String {
        return buildString {
            append("function fillOrderQuestion(q, topic) {\n")
            append("  var items = q.querySelectorAll('ul > li');\n")
            append("  if (items.length === 0) return;\n")
            append("  var indices = [];\n")
            append("  for (var i = 0; i < items.length; i++) indices.push(i);\n")
            append("  // Fisher-Yates shuffle\n")
            append("  for (var i = indices.length - 1; i > 0; i--) {\n")
            append("    var j = Math.floor(Math.random() * (i + 1));\n")
            append("    var temp = indices[i];\n")
            append("    indices[i] = indices[j];\n")
            append("    indices[j] = temp;\n")
            append("  }\n")
            append("  indices.forEach(function(idx) {\n")
            append("    if (idx < items.length) items[idx].click();\n")
            append("  });\n")
            append("}\n\n")
        }
    }

    /**
     * 生成文本答案数组
     */
    private fun generateTextArray(textQuestions: List<QuestionEntry>): String {
        if (textQuestions.isEmpty()) return "[]"
        
        val arrays = textQuestions.map { q ->
            val texts = q.texts ?: listOf("无")
            texts.joinToString(",") { "\"${escapeJs(it)}\"" }
        }
        return "[${arrays.joinToString(",") { "[$it]" }}]"
    }

    /**
     * 生成概率数组（单选、量表、矩阵、下拉）
     */
    private fun generateProbabilityArray(questions: List<QuestionEntry>): String {
        if (questions.isEmpty()) return "[]"
        
        val arrays = questions.map { q ->
            when (q.distributionMode) {
                DistributionMode.RANDOM -> "null"
                DistributionMode.EQUAL -> {
                    val weight = 1.0f / q.optionCount
                    (1..q.optionCount).map { weight }.joinToString(",")
                }
                DistributionMode.CUSTOM -> {
                    q.customWeights?.joinToString(",") ?: "null"
                }
            }
        }
        return "[${arrays.joinToString(",") { if (it == "null") "null" else "[$it]" }}]"
    }

    /**
     * 生成多选题概率数组
     */
    private fun generateMultipleProbabilityArray(questions: List<QuestionEntry>): String {
        if (questions.isEmpty()) return "[]"
        
        val arrays = questions.map { q ->
            val probs = q.probabilities ?: (1..q.optionCount).map { 50f }
            probs.joinToString(",")
        }
        return "[${arrays.joinToString(",") { "[$it]" }}]"
    }

    /**
     * 转义JavaScript字符串
     */
    private fun escapeJs(str: String): String {
        return str.replace("\\", "\\\\")
            .replace("\"", "\\\"")
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t")
    }

    /**
     * 生成点击下一页/提交的JavaScript
     */
    fun generateNextPageScript(): String {
        return """
            (function() {
                var nextBtn = document.querySelector('#divNext, #ctlNext, .next-btn');
                if (nextBtn) {
                    nextBtn.click();
                    return 'next';
                }
                var submitBtn = document.querySelector('#submit_button, #divSubmit, #ctlNext, #SM_BTN_1');
                if (submitBtn) {
                    submitBtn.click();
                    return 'submit';
                }
                return 'not_found';
            })();
        """.trimIndent()
    }

    /**
     * 生成检测页面状态的JavaScript
     */
    fun generateCheckStatusScript(): String {
        return """
            (function() {
                var url = window.location.href;
                if (url.indexOf('complete') > -1 || url.indexOf('finish') > -1) {
                    return 'completed';
                }
                var body = document.body.innerText || '';
                if (body.indexOf('答卷已经提交') > -1 || body.indexOf('感谢您的参与') > -1) {
                    return 'completed';
                }
                if (body.indexOf('设备已达到最大填写次数') > -1) {
                    return 'quota_exceeded';
                }
                return 'in_progress';
            })();
        """.trimIndent()
    }
}