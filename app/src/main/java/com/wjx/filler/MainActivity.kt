package com.wjx.filler

import android.Manifest
import android.annotation.SuppressLint
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Bundle
import android.text.SpannableStringBuilder
import android.text.style.ForegroundColorSpan
import android.view.LayoutInflater
import android.view.Menu
import android.view.MenuItem
import android.view.View
import android.webkit.WebChromeClient
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.*
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.google.android.material.textfield.TextInputEditText
import com.google.zxing.BinaryBitmap
import com.google.zxing.MultiFormatReader
import com.google.zxing.RGBLuminanceSource
import com.google.zxing.common.HybridBinarizer
import com.google.zxing.integration.android.IntentIntegrator
import com.wjx.filler.adapter.QuestionAdapter
import com.wjx.filler.core.LogLevel
import com.wjx.filler.core.SurveyExecutor
import com.wjx.filler.core.SurveyParser
import com.wjx.filler.databinding.ActivityMainBinding
import com.wjx.filler.model.*
import kotlinx.coroutines.*
import java.text.SimpleDateFormat
import java.util.*

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())
    
    private val config = SurveyConfig()
    private val questionAdapter = QuestionAdapter(
        onEdit = { position -> editQuestion(position) },
        onDelete = { position -> deleteQuestion(position) }
    )
    
    private var executor: SurveyExecutor? = null
    private var webView: WebView? = null
    private var threadCount = 2

    private val imagePickerLauncher = registerForActivityResult(
        ActivityResultContracts.GetContent()
    ) { uri ->
        uri?.let { decodeQRCodeFromUri(it) }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setupToolbar()
        setupViews()
        setupRecyclerView()
        initWebView()
    }

    private fun setupToolbar() {
        setSupportActionBar(binding.toolbar)
    }

    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menuInflater.inflate(R.menu.main_menu, menu)
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        return when (item.itemId) {
            R.id.action_settings -> {
                showSettingsDialog()
                true
            }
            R.id.action_about -> {
                showAboutDialog()
                true
            }
            else -> super.onOptionsItemSelected(item)
        }
    }

    private fun setupViews() {
        // URL输入
        binding.urlEditText.setText(config.url)

        // 扫描二维码
        binding.btnScanQR.setOnClickListener {
            checkCameraPermissionAndScan()
        }

        // 上传二维码图片
        binding.btnUploadQR.setOnClickListener {
            imagePickerLauncher.launch("image/*")
        }

        // 自动配置
        binding.btnAutoConfig.setOnClickListener {
            autoConfigSurvey()
        }

        // 目标份数
        binding.targetCountEditText.setText(config.targetCount.toString())

        // 线程数控制
        binding.threadCountText.text = threadCount.toString()
        binding.btnThreadMinus.setOnClickListener {
            if (threadCount > 1) {
                threadCount--
                binding.threadCountText.text = threadCount.toString()
            }
        }
        binding.btnThreadPlus.setOnClickListener {
            if (threadCount < SurveyConfig.MAX_THREADS) {
                threadCount++
                binding.threadCountText.text = threadCount.toString()
            }
        }

        // 间隔设置
        binding.intervalMinEditText.setText(config.intervalMin.toString())
        binding.intervalMaxEditText.setText(config.intervalMax.toString())

        // 添加题目
        binding.btnAddQuestion.setOnClickListener {
            showAddQuestionDialog()
        }

        // 开始执行
        binding.btnStart.setOnClickListener {
            startExecution()
        }

        // 停止执行
        binding.btnStop.setOnClickListener {
            stopExecution()
        }

        // 清空日志
        binding.btnClearLog.setOnClickListener {
            binding.logTextView.text = ""
        }
    }

    private fun setupRecyclerView() {
        binding.questionRecyclerView.apply {
            layoutManager = LinearLayoutManager(this@MainActivity)
            adapter = questionAdapter
        }
        updateQuestionList()
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun initWebView() {
        webView = WebView(this).apply {
            settings.apply {
                javaScriptEnabled = true
                domStorageEnabled = true
                useWideViewPort = true
                loadWithOverviewMode = true
                cacheMode = WebSettings.LOAD_NO_CACHE
                userAgentString = "Mozilla/5.0 (Linux; Android 13; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36"
            }
            webViewClient = WebViewClient()
            webChromeClient = WebChromeClient()
        }
    }

    private fun checkCameraPermissionAndScan() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) 
            != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(
                this,
                arrayOf(Manifest.permission.CAMERA),
                CAMERA_PERMISSION_REQUEST
            )
        } else {
            startQRScanner()
        }
    }

    private fun startQRScanner() {
        IntentIntegrator(this)
            .setDesiredBarcodeFormats(IntentIntegrator.QR_CODE)
            .setPrompt("扫描问卷二维码")
            .setCameraId(0)
            .setBeepEnabled(true)
            .setBarcodeImageEnabled(false)
            .initiateScan()
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == CAMERA_PERMISSION_REQUEST) {
            if (grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                startQRScanner()
            } else {
                Toast.makeText(this, "需要相机权限才能扫描二维码", Toast.LENGTH_SHORT).show()
            }
        }
    }

    @Deprecated("Deprecated in Java")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        val result = IntentIntegrator.parseActivityResult(requestCode, resultCode, data)
        if (result != null) {
            if (result.contents != null) {
                binding.urlEditText.setText(result.contents)
                log("扫描成功: ${result.contents}", LogLevel.SUCCESS)
            }
        } else {
            super.onActivityResult(requestCode, resultCode, data)
        }
    }

    private fun decodeQRCodeFromUri(uri: Uri) {
        try {
            val inputStream = contentResolver.openInputStream(uri)
            val bitmap = BitmapFactory.decodeStream(inputStream)
            inputStream?.close()

            if (bitmap != null) {
                val width = bitmap.width
                val height = bitmap.height
                val pixels = IntArray(width * height)
                bitmap.getPixels(pixels, 0, width, 0, 0, width, height)

                val source = RGBLuminanceSource(width, height, pixels)
                val binaryBitmap = BinaryBitmap(HybridBinarizer(source))
                val reader = MultiFormatReader()
                
                try {
                    val result = reader.decode(binaryBitmap)
                    binding.urlEditText.setText(result.text)
                    log("二维码解析成功: ${result.text}", LogLevel.SUCCESS)
                } catch (e: Exception) {
                    Toast.makeText(this, "无法识别二维码", Toast.LENGTH_SHORT).show()
                    log("二维码解析失败", LogLevel.ERROR)
                }
            }
        } catch (e: Exception) {
            Toast.makeText(this, "读取图片失败: ${e.message}", Toast.LENGTH_SHORT).show()
            log("读取图片失败: ${e.message}", LogLevel.ERROR)
        }
    }

    private fun autoConfigSurvey() {
        val url = binding.urlEditText.text.toString().trim()
        if (url.isBlank()) {
            Toast.makeText(this, "请先输入问卷链接", Toast.LENGTH_SHORT).show()
            return
        }

        if (!isValidWjxUrl(url)) {
            Toast.makeText(this, "请输入有效的问卷星链接", Toast.LENGTH_SHORT).show()
            return
        }

        binding.btnAutoConfig.isEnabled = false
        log("正在解析问卷...", LogLevel.INFO)

        scope.launch {
            val parser = SurveyParser()
            val result = parser.parseFromUrl(url)
            
            result.onSuccess { questions ->
                config.url = url
                config.questions.clear()
                config.questions.addAll(questions)
                updateQuestionList()
                log("解析成功，共 ${questions.size} 道题目", LogLevel.SUCCESS)
                Toast.makeText(this@MainActivity, "解析成功，共 ${questions.size} 道题目", Toast.LENGTH_SHORT).show()
            }.onFailure { e ->
                log("解析失败: ${e.message}", LogLevel.ERROR)
                Toast.makeText(this@MainActivity, "解析失败: ${e.message}", Toast.LENGTH_SHORT).show()
            }
            
            binding.btnAutoConfig.isEnabled = true
        }
    }

    private fun showAddQuestionDialog(editPosition: Int = -1) {
        val dialogView = LayoutInflater.from(this).inflate(R.layout.dialog_add_question, null)
        val isEdit = editPosition >= 0
        val existingEntry = if (isEdit) config.questions[editPosition] else null

        val questionTypeSpinner = dialogView.findViewById<AutoCompleteTextView>(R.id.questionTypeSpinner)
        val optionCountLayout = dialogView.findViewById<LinearLayout>(R.id.optionCountLayout)
        val optionCountText = dialogView.findViewById<TextView>(R.id.optionCountText)
        val btnOptionMinus = dialogView.findViewById<Button>(R.id.btnOptionMinus)
        val btnOptionPlus = dialogView.findViewById<Button>(R.id.btnOptionPlus)
        val matrixRowsLayout = dialogView.findViewById<LinearLayout>(R.id.matrixRowsLayout)
        val rowCountText = dialogView.findViewById<TextView>(R.id.rowCountText)
        val btnRowMinus = dialogView.findViewById<Button>(R.id.btnRowMinus)
        val btnRowPlus = dialogView.findViewById<Button>(R.id.btnRowPlus)
        val distributionRadioGroup = dialogView.findViewById<RadioGroup>(R.id.distributionRadioGroup)
        val radioRandom = dialogView.findViewById<RadioButton>(R.id.radioRandom)
        val radioCustom = dialogView.findViewById<RadioButton>(R.id.radioCustom)
        val weightsLayout = dialogView.findViewById<View>(R.id.weightsLayout)
        val weightsEditText = dialogView.findViewById<TextInputEditText>(R.id.weightsEditText)
        val fillTextLayout = dialogView.findViewById<View>(R.id.fillTextLayout)
        val fillTextEditText = dialogView.findViewById<TextInputEditText>(R.id.fillTextEditText)
        val multipleOptionsLayout = dialogView.findViewById<LinearLayout>(R.id.multipleOptionsLayout)

        var optionCount = existingEntry?.optionCount ?: 4
        var rowCount = existingEntry?.rows ?: 3

        // 题型列表
        val questionTypes = QuestionType.values().map { it.displayName }
        val typeAdapter = ArrayAdapter(this, android.R.layout.simple_dropdown_item_1line, questionTypes)
        questionTypeSpinner.setAdapter(typeAdapter)
        questionTypeSpinner.setText(existingEntry?.questionType?.displayName ?: QuestionType.SINGLE.displayName, false)

        // 更新UI显示
        fun updateUI() {
            val selectedType = QuestionType.fromDisplayName(questionTypeSpinner.text.toString())
            
            optionCountLayout.visibility = when (selectedType) {
                QuestionType.TEXT, QuestionType.MULTI_TEXT, QuestionType.LOCATION -> View.GONE
                else -> View.VISIBLE
            }
            
            matrixRowsLayout.visibility = if (selectedType == QuestionType.MATRIX) View.VISIBLE else View.GONE
            
            fillTextLayout.visibility = when (selectedType) {
                QuestionType.TEXT, QuestionType.MULTI_TEXT, QuestionType.LOCATION -> View.VISIBLE
                else -> View.GONE
            }
            
            multipleOptionsLayout.visibility = if (selectedType == QuestionType.MULTIPLE) View.VISIBLE else View.GONE
            
            val showDistribution = selectedType !in listOf(
                QuestionType.TEXT, QuestionType.MULTI_TEXT, QuestionType.LOCATION, QuestionType.MULTIPLE
            )
            dialogView.findViewById<TextView>(R.id.distributionLabel).visibility = 
                if (showDistribution) View.VISIBLE else View.GONE
            distributionRadioGroup.visibility = if (showDistribution) View.VISIBLE else View.GONE
        }

        questionTypeSpinner.setOnItemClickListener { _, _, _, _ -> updateUI() }

        // 选项数量控制
        optionCountText.text = optionCount.toString()
        btnOptionMinus.setOnClickListener {
            if (optionCount > 2) {
                optionCount--
                optionCountText.text = optionCount.toString()
            }
        }
        btnOptionPlus.setOnClickListener {
            optionCount++
            optionCountText.text = optionCount.toString()
        }

        // 矩阵行数控制
        rowCountText.text = rowCount.toString()
        btnRowMinus.setOnClickListener {
            if (rowCount > 1) {
                rowCount--
                rowCountText.text = rowCount.toString()
            }
        }
        btnRowPlus.setOnClickListener {
            rowCount++
            rowCountText.text = rowCount.toString()
        }

        // 分布方式
        distributionRadioGroup.setOnCheckedChangeListener { _, checkedId ->
            weightsLayout.visibility = if (checkedId == R.id.radioCustom) View.VISIBLE else View.GONE
        }

        // 初始化已有数据
        if (existingEntry != null) {
            when (existingEntry.distributionMode) {
                DistributionMode.RANDOM -> radioRandom.isChecked = true
                DistributionMode.CUSTOM -> {
                    radioCustom.isChecked = true
                    weightsLayout.visibility = View.VISIBLE
                    weightsEditText.setText(existingEntry.customWeights?.joinToString(":") ?: "")
                }
                else -> radioRandom.isChecked = true
            }
            fillTextEditText.setText(existingEntry.texts?.joinToString("|") ?: "")
        }

        updateUI()

        MaterialAlertDialogBuilder(this)
            .setTitle(if (isEdit) "编辑题目" else "添加题目")
            .setView(dialogView)
            .setPositiveButton("保存") { _, _ ->
                val selectedType = QuestionType.fromDisplayName(questionTypeSpinner.text.toString())
                val distributionMode = if (radioCustom.isChecked) DistributionMode.CUSTOM else DistributionMode.RANDOM
                
                val entry = QuestionEntry(
                    questionType = selectedType,
                    optionCount = optionCount,
                    rows = rowCount,
                    distributionMode = distributionMode,
                    customWeights = if (distributionMode == DistributionMode.CUSTOM) {
                        weightsEditText.text.toString().split(":").mapNotNull { it.toFloatOrNull() }
                    } else null,
                    texts = if (selectedType in listOf(QuestionType.TEXT, QuestionType.MULTI_TEXT, QuestionType.LOCATION)) {
                        fillTextEditText.text.toString().split("|").filter { it.isNotBlank() }.ifEmpty { listOf("无") }
                    } else null,
                    questionNum = if (isEdit) existingEntry!!.questionNum else config.questions.size + 1,
                    isLocation = selectedType == QuestionType.LOCATION
                )

                if (isEdit) {
                    config.questions[editPosition] = entry
                } else {
                    config.questions.add(entry)
                }
                updateQuestionList()
                log("${if (isEdit) "编辑" else "添加"}题目成功", LogLevel.SUCCESS)
            }
            .setNegativeButton("取消", null)
            .show()
    }

    private fun editQuestion(position: Int) {
        showAddQuestionDialog(position)
    }

    private fun deleteQuestion(position: Int) {
        MaterialAlertDialogBuilder(this)
            .setTitle("删除确认")
            .setMessage("确定要删除第 ${position + 1} 题吗？")
            .setPositiveButton("删除") { _, _ ->
                config.questions.removeAt(position)
                updateQuestionList()
                log("删除题目成功", LogLevel.INFO)
            }
            .setNegativeButton("取消", null)
            .show()
    }

    private fun updateQuestionList() {
        questionAdapter.submitList(config.questions.toList())
        binding.questionCountText.text = "已配置 ${config.questions.size} 道题目"
        
        if (config.questions.isEmpty()) {
            binding.questionRecyclerView.visibility = View.GONE
            binding.emptyQuestionText.visibility = View.VISIBLE
        } else {
            binding.questionRecyclerView.visibility = View.VISIBLE
            binding.emptyQuestionText.visibility = View.GONE
        }
    }

    private fun startExecution() {
        // 收集配置
        config.url = binding.urlEditText.text.toString().trim()
        config.targetCount = binding.targetCountEditText.text.toString().toIntOrNull() ?: 10
        config.threadCount = threadCount
        config.intervalMin = binding.intervalMinEditText.text.toString().toIntOrNull() ?: 0
        config.intervalMax = binding.intervalMaxEditText.text.toString().toIntOrNull() ?: 0

        // 验证配置
        if (config.url.isBlank()) {
            Toast.makeText(this, "请输入问卷链接", Toast.LENGTH_SHORT).show()
            return
        }

        if (!isValidWjxUrl(config.url)) {
            Toast.makeText(this, "请输入有效的问卷星链接", Toast.LENGTH_SHORT).show()
            return
        }

        if (config.questions.isEmpty()) {
            Toast.makeText(this, "请先配置题目", Toast.LENGTH_SHORT).show()
            return
        }

        // 更新UI状态
        binding.btnStart.isEnabled = false
        binding.btnStop.isEnabled = true
        binding.progressBar.progress = 0
        binding.progressText.text = "0%"
        binding.statusText.text = "运行中..."

        log("开始执行任务", LogLevel.INFO)

        // 创建执行器
        executor = SurveyExecutor(
            config = config,
            onStatusChange = { status ->
                runOnUiThread {
                    when (status) {
                        ExecutionStatus.RUNNING -> {
                            binding.statusText.text = "运行中..."
                        }
                        ExecutionStatus.STOPPED -> {
                            binding.statusText.text = "已停止"
                            binding.btnStart.isEnabled = true
                            binding.btnStop.isEnabled = false
                        }
                        ExecutionStatus.COMPLETED -> {
                            binding.statusText.text = "已完成"
                            binding.btnStart.isEnabled = true
                            binding.btnStop.isEnabled = false
                        }
                        else -> {}
                    }
                }
            },
            onProgressUpdate = { result ->
                runOnUiThread {
                    binding.progressBar.progress = result.progress
                    binding.progressText.text = "${result.progress}%"
                    binding.statusText.text = "成功: ${result.success} / 失败: ${result.failed}"
                }
            },
            onLog = { message, level ->
                log(message, level)
            }
        )

        executor?.start { webView!! }
    }

    private fun stopExecution() {
        executor?.stop()
        binding.btnStart.isEnabled = true
        binding.btnStop.isEnabled = false
        binding.statusText.text = "已停止"
        log("任务已停止", LogLevel.WARNING)
    }

    private fun log(message: String, level: LogLevel) {
        runOnUiThread {
            val timestamp = SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date())
            val color = when (level) {
                LogLevel.INFO -> ContextCompat.getColor(this, R.color.log_info)
                LogLevel.SUCCESS -> ContextCompat.getColor(this, R.color.log_success)
                LogLevel.WARNING -> ContextCompat.getColor(this, R.color.log_warning)
                LogLevel.ERROR -> ContextCompat.getColor(this, R.color.log_error)
            }
            
            val logText = "[$timestamp] $message\n"
            val spannable = SpannableStringBuilder(logText)
            spannable.setSpan(ForegroundColorSpan(color), 0, logText.length, 0)
            
            binding.logTextView.append(spannable)
            
            // 自动滚动到底部
            val scrollView = binding.logTextView.parent as? ScrollView
            scrollView?.post { scrollView.fullScroll(View.FOCUS_DOWN) }
        }
    }

    private fun isValidWjxUrl(url: String): Boolean {
        val trimmed = url.trim().lowercase()
        return trimmed.contains("wjx.cn") || trimmed.contains("wjx.top")
    }

    private fun showSettingsDialog() {
        MaterialAlertDialogBuilder(this)
            .setTitle("设置")
            .setMessage("更多设置功能开发中...")
            .setPositiveButton("确定", null)
            .show()
    }

    private fun showAboutDialog() {
        MaterialAlertDialogBuilder(this)
            .setTitle("关于")
            .setMessage("问卷星速填 v1.0.0\n\n自动填写问卷星问卷的工具\n\n仅供学习交流使用")
            .setPositiveButton("确定", null)
            .show()
    }

    override fun onDestroy() {
        super.onDestroy()
        executor?.release()
        webView?.destroy()
        scope.cancel()
    }

    companion object {
        private const val CAMERA_PERMISSION_REQUEST = 100
    }
}