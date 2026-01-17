"""界面设置页面"""
import sys
import subprocess

from PySide6.QtCore import Qt, QSettings
from PySide6.QtWidgets import QWidget, QVBoxLayout, QApplication
from qfluentwidgets import (
    ScrollArea,
    SettingCardGroup,
    SettingCard,
    PushSettingCard,
    FluentIcon,
    InfoBar,
    InfoBarPosition,
    MessageBox,
    ComboBox,
    LineEdit,
    PasswordLineEdit,
    TextEdit,
)

from wjx.ui.pages.runtime import SwitchSettingCard
from wjx.utils.config import GITHUB_MIRROR_SOURCES, DEFAULT_GITHUB_MIRROR
from wjx.utils.ai_service import AI_PROVIDERS, get_ai_settings, save_ai_settings, test_connection, DEFAULT_SYSTEM_PROMPT


class SettingsPage(ScrollArea):
    """界面设置页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.view = QWidget(self)
        self.view.setStyleSheet("background: transparent;")
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self.view)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # 从设置中读取配置
        settings = QSettings("FuckWjx", "Settings")

        # 界面设置组
        self.ui_group = SettingCardGroup("界面设置", self.view)

        # 侧边栏展开设置卡片
        self.sidebar_card = SwitchSettingCard(
            FluentIcon.MENU,
            "始终展开侧边栏",
            "开启后侧边栏将始终保持展开状态",
            self.ui_group
        )
        self.sidebar_card.setChecked(True)
        self.ui_group.addSettingCard(self.sidebar_card)

        # 窗口置顶设置卡片
        self.topmost_card = SwitchSettingCard(
            FluentIcon.PIN,
            "窗口置顶",
            "开启后程序窗口将始终保持在最上层",
            self.ui_group
        )
        self.topmost_card.setChecked(settings.value("window_topmost", False, type=bool))
        self.ui_group.addSettingCard(self.topmost_card)

        # 重启程序设置卡片
        self.restart_card = PushSettingCard(
            text="重启",
            icon=FluentIcon.SYNC,
            title="重新启动程序",
            content="重启程序以应用某些设置更改",
            parent=self.ui_group
        )
        self.ui_group.addSettingCard(self.restart_card)

        layout.addWidget(self.ui_group)

        # 软件更新组
        self.update_group = SettingCardGroup("软件更新", self.view)

        # 启动时检查更新开关
        self.auto_update_card = SwitchSettingCard(
            FluentIcon.UPDATE,
            "在应用程序启动时检查更新",
            "新版本将更加稳定并拥有更多功能（建议启用此选项）",
            self.update_group
        )
        # 从设置中读取，默认开启
        settings = QSettings("FuckWjx", "Settings")
        self.auto_update_card.setChecked(settings.value("auto_check_update", True, type=bool))
        self.update_group.addSettingCard(self.auto_update_card)

        # 下载镜像源选择
        self.mirror_card = SettingCard(
            FluentIcon.DOWNLOAD,
            "下载镜像源",
            "国内用户建议使用镜像加速下载",
            self.update_group
        )
        self.mirror_combo = ComboBox(self.mirror_card)
        self.mirror_combo.setMinimumWidth(180)
        for key, source in GITHUB_MIRROR_SOURCES.items():
            self.mirror_combo.addItem(source["label"], userData=key)
        # 读取保存的镜像源设置
        saved_mirror = settings.value("github_mirror", DEFAULT_GITHUB_MIRROR, type=str)
        idx = self.mirror_combo.findData(saved_mirror)
        if idx >= 0:
            self.mirror_combo.setCurrentIndex(idx)
        self.mirror_card.hBoxLayout.addWidget(self.mirror_combo, 0, Qt.AlignmentFlag.AlignRight)
        self.mirror_card.hBoxLayout.addSpacing(16)
        self.update_group.addSettingCard(self.mirror_card)

        layout.addWidget(self.update_group)

        # AI 配置组
        self.ai_group = SettingCardGroup("AI 填空助手", self.view)
        ai_config = get_ai_settings()

        # AI 功能开关
        self.ai_enabled_card = SwitchSettingCard(
            FluentIcon.ROBOT,
            "启用 AI 填空",
            "开启后可使用 AI 自动生成填空题答案",
            self.ai_group
        )
        self.ai_enabled_card.setChecked(ai_config["enabled"])
        self.ai_group.addSettingCard(self.ai_enabled_card)

        # AI 服务提供商选择
        self.ai_provider_card = SettingCard(
            FluentIcon.CLOUD,
            "AI 服务提供商",
            "选择 AI 服务，自定义模式支持任意 OpenAI 兼容接口",
            self.ai_group
        )
        self.ai_provider_combo = ComboBox(self.ai_provider_card)
        self.ai_provider_combo.setMinimumWidth(200)
        for key, provider in AI_PROVIDERS.items():
            self.ai_provider_combo.addItem(provider["label"], userData=key)
        saved_provider = ai_config["provider"]
        idx = self.ai_provider_combo.findData(saved_provider)
        if idx >= 0:
            self.ai_provider_combo.setCurrentIndex(idx)
        self.ai_provider_card.hBoxLayout.addWidget(self.ai_provider_combo, 0, Qt.AlignmentFlag.AlignRight)
        self.ai_provider_card.hBoxLayout.addSpacing(16)
        self.ai_group.addSettingCard(self.ai_provider_card)

        # API Key 输入
        self.ai_apikey_card = SettingCard(
            FluentIcon.FINGERPRINT,
            "API Key",
            "输入对应服务的 API 密钥",
            self.ai_group
        )
        self.ai_apikey_edit = PasswordLineEdit(self.ai_apikey_card)
        self.ai_apikey_edit.setMinimumWidth(280)
        self.ai_apikey_edit.setPlaceholderText("sk-...")
        self.ai_apikey_edit.setText(ai_config["api_key"])
        self.ai_apikey_card.hBoxLayout.addWidget(self.ai_apikey_edit, 0, Qt.AlignmentFlag.AlignRight)
        self.ai_apikey_card.hBoxLayout.addSpacing(16)
        self.ai_group.addSettingCard(self.ai_apikey_card)

        # 自定义 Base URL（仅自定义模式显示）
        self.ai_baseurl_card = SettingCard(
            FluentIcon.LINK,
            "Base URL",
            "自定义模式下的 API 地址（如 https://api.example.com/v1）",
            self.ai_group
        )
        self.ai_baseurl_edit = LineEdit(self.ai_baseurl_card)
        self.ai_baseurl_edit.setMinimumWidth(280)
        self.ai_baseurl_edit.setPlaceholderText("https://api.example.com/v1")
        self.ai_baseurl_edit.setText(ai_config["base_url"])
        self.ai_baseurl_card.hBoxLayout.addWidget(self.ai_baseurl_edit, 0, Qt.AlignmentFlag.AlignRight)
        self.ai_baseurl_card.hBoxLayout.addSpacing(16)
        self.ai_group.addSettingCard(self.ai_baseurl_card)

        # 模型选择
        self.ai_model_card = SettingCard(
            FluentIcon.DEVELOPER_TOOLS,
            "模型",
            "选择或输入模型名称",
            self.ai_group
        )
        self.ai_model_edit = LineEdit(self.ai_model_card)
        self.ai_model_edit.setMinimumWidth(200)
        self.ai_model_edit.setPlaceholderText("gpt-3.5-turbo")
        self.ai_model_edit.setText(ai_config["model"])
        self.ai_model_card.hBoxLayout.addWidget(self.ai_model_edit, 0, Qt.AlignmentFlag.AlignRight)
        self.ai_model_card.hBoxLayout.addSpacing(16)
        self.ai_group.addSettingCard(self.ai_model_card)

        # 测试连接按钮
        self.ai_test_card = PushSettingCard(
            text="测试",
            icon=FluentIcon.SEND,
            title="测试 AI 连接",
            content="验证 API 配置是否正确",
            parent=self.ai_group
        )
        self.ai_group.addSettingCard(self.ai_test_card)

        layout.addWidget(self.ai_group)
        self._update_ai_visibility()

        layout.addStretch(1)

        # 绑定事件
        self.sidebar_card.switchButton.checkedChanged.connect(self._on_sidebar_toggled)
        self.topmost_card.switchButton.checkedChanged.connect(self._on_topmost_toggled)
        self.restart_card.clicked.connect(self._restart_program)
        self.auto_update_card.switchButton.checkedChanged.connect(self._on_auto_update_toggled)
        self.mirror_combo.currentIndexChanged.connect(self._on_mirror_changed)
        # AI 相关事件
        self.ai_enabled_card.switchButton.checkedChanged.connect(self._on_ai_enabled_toggled)
        self.ai_provider_combo.currentIndexChanged.connect(self._on_ai_provider_changed)
        self.ai_apikey_edit.editingFinished.connect(self._on_ai_apikey_changed)
        self.ai_baseurl_edit.editingFinished.connect(self._on_ai_baseurl_changed)
        self.ai_model_edit.editingFinished.connect(self._on_ai_model_changed)
        self.ai_test_card.clicked.connect(self._on_ai_test_clicked)

    def _on_sidebar_toggled(self, checked: bool):
        """侧边栏展开切换"""
        win = self.window()
        nav = getattr(win, "navigationInterface", None)
        if nav is not None:
            try:
                if checked:
                    nav.setCollapsible(False)
                    nav.expand()
                else:
                    nav.setCollapsible(True)
                InfoBar.success(
                    "",
                    f"侧边栏已设置为{'始终展开' if checked else '可折叠'}",
                    parent=win,
                    position=InfoBarPosition.TOP,
                    duration=2000
                )
            except Exception:
                pass

    def _restart_program(self):
        """重启程序"""
        box = MessageBox(
            "重启程序",
            "确定要重新启动程序吗？\n未保存的配置将会丢失。",
            self.window() or self
        )
        box.yesButton.setText("确定")
        box.cancelButton.setText("取消")
        if box.exec():
            try:
                win = self.window()
                if hasattr(win, '_skip_save_on_close'):
                    setattr(win, '_skip_save_on_close', True)
                subprocess.Popen([sys.executable] + sys.argv)
                QApplication.quit()
            except Exception as exc:
                InfoBar.error(
                    "",
                    f"重启失败：{exc}",
                    parent=self.window(),
                    position=InfoBarPosition.TOP,
                    duration=3000
                )

    def _on_auto_update_toggled(self, checked: bool):
        """自动检查更新开关切换"""
        settings = QSettings("FuckWjx", "Settings")
        settings.setValue("auto_check_update", checked)
        InfoBar.success(
            "",
            f"启动时检查更新已{'开启' if checked else '关闭'}",
            parent=self.window(),
            position=InfoBarPosition.TOP,
            duration=2000
        )

    def _on_topmost_toggled(self, checked: bool):
        """窗口置顶切换"""
        settings = QSettings("FuckWjx", "Settings")
        settings.setValue("window_topmost", checked)
        win = self.window()
        if win:
            from PySide6.QtCore import Qt
            win.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, checked)
            win.show()
        InfoBar.success(
            "",
            f"窗口置顶已{'开启' if checked else '关闭'}",
            parent=win,
            position=InfoBarPosition.TOP,
            duration=2000
        )

    def _on_mirror_changed(self):
        """镜像源选择变化"""
        idx = self.mirror_combo.currentIndex()
        mirror_key = str(self.mirror_combo.itemData(idx)) if idx >= 0 else DEFAULT_GITHUB_MIRROR
        settings = QSettings("FuckWjx", "Settings")
        settings.setValue("github_mirror", mirror_key)
        mirror_label = GITHUB_MIRROR_SOURCES.get(mirror_key, {}).get("label", mirror_key)
        InfoBar.success(
            "",
            f"下载镜像源已切换为：{mirror_label}",
            parent=self.window(),
            position=InfoBarPosition.TOP,
            duration=2000
        )

    def _update_ai_visibility(self):
        """根据选择的提供商更新 AI 配置项的可见性"""
        idx = self.ai_provider_combo.currentIndex()
        provider_key = str(self.ai_provider_combo.itemData(idx)) if idx >= 0 else "openai"
        is_custom = provider_key == "custom"
        self.ai_baseurl_card.setVisible(is_custom)

    def _on_ai_enabled_toggled(self, checked: bool):
        """AI 功能开关切换"""
        save_ai_settings(enabled=checked)
        InfoBar.success(
            "",
            f"AI 填空功能已{'开启' if checked else '关闭'}",
            parent=self.window(),
            position=InfoBarPosition.TOP,
            duration=2000
        )

    def _on_ai_provider_changed(self):
        """AI 提供商选择变化"""
        idx = self.ai_provider_combo.currentIndex()
        provider_key = str(self.ai_provider_combo.itemData(idx)) if idx >= 0 else "openai"
        save_ai_settings(provider=provider_key)
        self._update_ai_visibility()
        # 更新模型占位符
        provider_config = AI_PROVIDERS.get(provider_key, {})
        default_model = provider_config.get("default_model", "")
        self.ai_model_edit.setPlaceholderText(default_model or "模型名称")
        InfoBar.success(
            "",
            f"AI 服务已切换为：{provider_config.get('label', provider_key)}",
            parent=self.window(),
            position=InfoBarPosition.TOP,
            duration=2000
        )

    def _on_ai_apikey_changed(self):
        """API Key 变化"""
        save_ai_settings(api_key=self.ai_apikey_edit.text())

    def _on_ai_baseurl_changed(self):
        """Base URL 变化"""
        save_ai_settings(base_url=self.ai_baseurl_edit.text())

    def _on_ai_model_changed(self):
        """模型变化"""
        save_ai_settings(model=self.ai_model_edit.text())

    def _on_ai_test_clicked(self):
        """测试 AI 连接"""
        # 先保存当前配置
        save_ai_settings(
            enabled=True,  # 临时启用以测试
            api_key=self.ai_apikey_edit.text(),
            base_url=self.ai_baseurl_edit.text(),
            model=self.ai_model_edit.text(),
        )
        InfoBar.info(
            "",
            "正在测试连接...",
            parent=self.window(),
            position=InfoBarPosition.TOP,
            duration=1500
        )
        try:
            result = test_connection()
            if "成功" in result:
                InfoBar.success("", result, parent=self.window(), position=InfoBarPosition.TOP, duration=3000)
            else:
                InfoBar.error("", result, parent=self.window(), position=InfoBarPosition.TOP, duration=5000)
        except Exception as e:
            InfoBar.error("", f"测试失败: {e}", parent=self.window(), position=InfoBarPosition.TOP, duration=5000)
        # 恢复原来的启用状态
        save_ai_settings(enabled=self.ai_enabled_card.isChecked())
