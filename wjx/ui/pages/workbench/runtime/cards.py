"""运行参数页 - 专属设置卡片组件（随机IP、随机UA、定时模式等）"""
import logging
from typing import Optional

from PySide6.QtCore import Qt, QStringListModel, Signal
from PySide6.QtGui import QDoubleValidator, QIntValidator
from PySide6.QtWidgets import QCompleter, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    Action,
    BodyLabel,
    ComboBox,
    EditableComboBox,
    ExpandGroupSettingCard,
    FluentIcon,
    HyperlinkButton,
    IndicatorPosition,
    IndeterminateProgressRing,
    InfoBar,
    InfoBarPosition,
    LineEdit,
    PushButton,
    RoundMenu,
    SettingCard,
    SwitchButton,
    TransparentToolButton,
)
from wjx.ui.widgets.no_wheel import NoWheelSpinBox
from wjx.ui.widgets.kuaidaili_area_select import KuaidailiAreaSelectWidget


class SearchableComboBox(EditableComboBox):
    """带搜索过滤的下拉框：聚焦时展开全量列表，打字时按包含关系过滤。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._str_model = QStringListModel(self)
        completer = QCompleter(self._str_model, self)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setCompleter(completer)

    def addItem(self, text, icon=None, userData=None):
        super().addItem(text, icon, userData)
        self._sync_model()

    def clear(self):
        super().clear()
        self._sync_model()

    def _sync_model(self):
        self._str_model.setStringList([item.text for item in self.items])

    def _onComboTextChanged(self, text: str):
        # 打字时关闭全量菜单，交给 completer 过滤
        if text:
            self._closeComboMenu()
        super()._onComboTextChanged(text)


# 直辖市省级编码：这些地区用"市辖区"代替"全省/全市"
_MUNICIPALITY_PROVINCE_CODES = {"110000", "120000", "310000", "500000"}


class RandomIPSettingCard(ExpandGroupSettingCard):
    """随机IP设置卡 - 包含代理源选择"""

    def __init__(self, parent=None):
        super().__init__(FluentIcon.GLOBE, "随机 IP", "使用代理 IP 来模拟不同地区的访问，并绕过智能验证", parent)

        # 开关
        self.switchButton = SwitchButton(self, IndicatorPosition.RIGHT)
        self.switchButton.setOnText("开")
        self.switchButton.setOffText("关")
        self.addWidget(self.switchButton)

        # 代理源选择容器
        self._groupContainer = QWidget()
        layout = QVBoxLayout(self._groupContainer)
        layout.setContentsMargins(48, 12, 48, 12)
        layout.setSpacing(12)

        # 代理源下拉框
        source_row = QHBoxLayout()
        source_label = BodyLabel("代理源", self._groupContainer)
        self.proxyCombo = ComboBox(self._groupContainer)
        self.proxyCombo.addItem("默认", userData="default")
        self.proxyCombo.addItem("皮卡丘代理站 (中国大陆)", userData="pikachu")
        self.proxyCombo.addItem("快代理", userData="kuaidaili")
        self.proxyCombo.addItem("自定义", userData="custom")
        self.proxyCombo.setMinimumWidth(200)
        source_row.addWidget(source_label)
        source_row.addStretch(1)
        self.proxyTrialLink = HyperlinkButton(
            FluentIcon.LINK, "https://www.ipzan.com?pid=v6bf6iabg",
            "API免费试用", self._groupContainer
        )
        self.proxyTrialLink.hide()
        source_row.addWidget(self.proxyTrialLink)
        source_row.addWidget(self.proxyCombo)
        layout.addLayout(source_row)

        # 地区选择（仅默认代理源）
        self.areaRow = QWidget(self._groupContainer)
        area_layout = QHBoxLayout(self.areaRow)
        area_layout.setContentsMargins(0, 0, 0, 0)
        area_label = BodyLabel("指定地区", self.areaRow)
        self.provinceCombo = SearchableComboBox(self.areaRow)
        self.cityCombo = SearchableComboBox(self.areaRow)
        self.provinceCombo.setMinimumWidth(160)
        self.cityCombo.setMinimumWidth(200)
        area_layout.addWidget(area_label)
        area_layout.addStretch(1)
        area_layout.addWidget(self.provinceCombo)
        area_layout.addWidget(self.cityCombo)
        layout.addWidget(self.areaRow)

        # 自定义API输入
        self.customApiRow = QWidget(self._groupContainer)
        api_layout = QHBoxLayout(self.customApiRow)
        api_layout.setContentsMargins(0, 0, 0, 0)
        api_label = BodyLabel("API 地址", self.customApiRow)
        api_hint = BodyLabel("*仅支持json返回格式", self.customApiRow)
        api_hint.setStyleSheet("color: red; font-size: 11px;")
        self.customApiEdit = LineEdit(self.customApiRow)
        self.customApiEdit.setPlaceholderText("请输入代理api地址")
        self.customApiEdit.setMinimumWidth(420)

        # 检测按钮容器（包含按钮、加载动画、状态图标）
        self.testBtnContainer = QWidget(self.customApiRow)
        test_btn_layout = QHBoxLayout(self.testBtnContainer)
        test_btn_layout.setContentsMargins(0, 0, 0, 0)
        test_btn_layout.setSpacing(4)

        self.testApiBtn = PushButton("检测", self.testBtnContainer)
        self.testApiBtn.setFixedWidth(60)
        self.testApiBtn.clicked.connect(self._on_test_api_clicked)

        self.testApiSpinner = IndeterminateProgressRing(self.testBtnContainer)
        self.testApiSpinner.setFixedSize(20, 20)
        self.testApiSpinner.hide()

        self.testApiStatus = BodyLabel("", self.testBtnContainer)
        self.testApiStatus.setFixedWidth(20)
        self.testApiStatus.hide()

        test_btn_layout.addWidget(self.testApiBtn)
        test_btn_layout.addWidget(self.testApiSpinner)
        test_btn_layout.addWidget(self.testApiStatus)

        api_layout.addWidget(api_label)
        api_layout.addWidget(api_hint)
        api_layout.addStretch(1)
        api_layout.addWidget(self.customApiEdit)
        api_layout.addWidget(self.testBtnContainer)
        self.customApiRow.hide()
        layout.addWidget(self.customApiRow)

        # 快代理配置面板
        self.kuaidailiPanel = QWidget(self._groupContainer)
        self._build_kuaidaili_panel()
        self.kuaidailiPanel.hide()
        layout.addWidget(self.kuaidailiPanel)

        self._area_updating = False
        self._area_data = []
        self._supported_area_codes = set()
        self._supported_has_all = False
        self._cities_by_province = {}
        self._province_index_by_code = {}
        self._load_area_options()
        self.areaRow.setVisible(True)
        self.provinceCombo.currentIndexChanged.connect(self._on_province_changed)
        self.cityCombo.currentIndexChanged.connect(self._on_city_changed)

        self.addGroupWidget(self._groupContainer)
        self.setExpand(True)

        # 代理源变化时显示/隐藏自定义API
        self.proxyCombo.currentIndexChanged.connect(self._on_source_changed)
        # API地址输入完成时同步到全局变量
        self.customApiEdit.editingFinished.connect(self._on_api_edit_finished)
        # 开关联动：关闭时禁用展开内容
        self.switchButton.checkedChanged.connect(self._sync_ip_enabled)
        self._sync_ip_enabled(False)

    def _on_source_changed(self):
        idx = self.proxyCombo.currentIndex()
        source = str(self.proxyCombo.itemData(idx)) if idx >= 0 else "default"
        self.customApiRow.setVisible(source == "custom")
        self.proxyTrialLink.setVisible(source == "custom")
        self.areaRow.setVisible(source == "default")
        self.kuaidailiPanel.setVisible(source == "kuaidaili")
        # TODO: 快代理配置UI（Secret ID、Secret Key、地区选择等）
        # 当前快代理配置通过代码设置，后续可添加UI界面
        if source != "default":
            self._apply_area_override(None)
        else:
            self._apply_area_override(self.get_area_code())
        # 刷新布局 - 重新触发展开/收起来更新高度
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self._refreshLayout)

    def _load_area_options(self):
        try:
            from wjx.core.services.area_service import load_area_codes
            from wjx.core.services.area_service import load_supported_area_codes
            self._supported_area_codes, self._supported_has_all = load_supported_area_codes()
            self._area_data = load_area_codes(supported_only=True)
            if not self._area_data:
                logging.warning("地区数据加载为空，可能是数据文件损坏或格式错误")
        except Exception as e:
            logging.error(f"加载地区数据失败: {e}", exc_info=True)
            self._area_data = []
            self._supported_area_codes = set()
            self._supported_has_all = False
        self._cities_by_province = {}
        self._province_index_by_code = {}

        self.provinceCombo.clear()
        if self._supported_has_all or not self._supported_area_codes:
            self.provinceCombo.addItem("不限制", userData="")
        for item in self._area_data:
            code = str(item.get("code") or "")
            name = str(item.get("name") or "")
            if not code or not name:
                continue
            self._cities_by_province[code] = list(item.get("cities") or [])
            self.provinceCombo.addItem(name, userData=code)
            self._province_index_by_code[code] = self.provinceCombo.count() - 1

        self.cityCombo.clear()
        self.cityCombo.setEnabled(False)

    def _populate_cities(self, province_code: str, preferred_city_code: Optional[str] = None) -> None:
        self.cityCombo.clear()
        is_municipality = province_code in _MUNICIPALITY_PROVINCE_CODES
        # 直辖市不显示"全省/全市"，直接用"市辖区"代表全市
        if not is_municipality and province_code and province_code in self._supported_area_codes:
            self.cityCombo.addItem("全省/全市", userData=province_code)
        cities = self._cities_by_province.get(province_code, [])
        for city in cities:
            code = str(city.get("code") or "")
            name = str(city.get("name") or "")
            if code and name:
                self.cityCombo.addItem(name, userData=code)
        self.cityCombo.setEnabled(bool(cities))
        if preferred_city_code:
            idx = self.cityCombo.findData(preferred_city_code)
            if idx >= 0:
                self.cityCombo.setCurrentIndex(idx)
            elif is_municipality and self.cityCombo.count() > 0:
                # 直辖市找不到 preferred_city_code（如省级码110000）时，回退到第一项（市辖区）
                self.cityCombo.setCurrentIndex(0)

    def _on_province_changed(self):
        if self._area_updating:
            return
        province_code = self.provinceCombo.currentData()
        self._area_updating = True
        if not province_code:
            self.cityCombo.clear()
            self.cityCombo.setEnabled(False)
            self._area_updating = False
            self._apply_area_override("")
            return
        self._populate_cities(province_code)
        self._area_updating = False
        self._apply_area_override(self.cityCombo.currentData())

    def _on_city_changed(self):
        if self._area_updating:
            return
        if not self.cityCombo.isEnabled():
            self._apply_area_override("")
            return
        self._apply_area_override(self.cityCombo.currentData())

    def _apply_area_override(self, area_code: Optional[str]) -> None:
        from wjx.network.proxy import set_proxy_area_code
        if not self.areaRow.isVisible():
            set_proxy_area_code(None)
            return
        if area_code is None:
            set_proxy_area_code(None)
            return
        set_proxy_area_code(str(area_code))

    def get_area_code(self) -> Optional[str]:
        if not self.areaRow.isVisible():
            return None
        province_code = self.provinceCombo.currentData()
        if not province_code:
            return ""
        city_code = self.cityCombo.currentData()
        return str(city_code or "")

    def set_area_code(self, area_code: Optional[str]) -> None:
        from wjx.network.proxy import get_default_proxy_area_code
        if area_code is None:
            area_code = get_default_proxy_area_code()
        area_code = str(area_code or "").strip()
        self._area_updating = True
        if not area_code:
            self.provinceCombo.setCurrentIndex(0)
            self.cityCombo.clear()
            self.cityCombo.setEnabled(False)
            self._area_updating = False
            self._apply_area_override("")
            return
        province_code = f"{area_code[:2]}0000" if len(area_code) >= 2 else ""
        province_index = self._province_index_by_code.get(province_code)
        if province_index is None:
            self.provinceCombo.setCurrentIndex(0)
            self.cityCombo.clear()
            self.cityCombo.setEnabled(False)
            self._area_updating = False
            self._apply_area_override("")
            return
        self.provinceCombo.setCurrentIndex(province_index)
        self._populate_cities(province_code, preferred_city_code=area_code)
        self._area_updating = False
        self._apply_area_override(self.cityCombo.currentData())

    def _refreshLayout(self):
        """刷新展开卡片的布局"""
        # 通过重新设置展开状态来刷新高度
        if self.isExpand:
            self._adjustViewSize()

    def _on_test_api_clicked(self):
        """检测API按钮点击事件"""
        from PySide6.QtCore import QThread, Signal, QObject

        api_url = self.customApiEdit.text().strip()
        if not api_url:
            InfoBar.warning("", "请先输入API地址", parent=self.window(), position=InfoBarPosition.TOP, duration=3000)
            return

        # 显示加载状态
        self.testApiBtn.hide()
        self.testApiStatus.hide()
        self.testApiSpinner.show()

        # 创建工作线程
        class TestWorker(QObject):
            finished = Signal(bool, str, list)

            def __init__(self, url):
                super().__init__()
                self.url = url

            def run(self):
                from wjx.network.proxy import test_custom_proxy_api
                success, error, proxies = test_custom_proxy_api(self.url)
                self.finished.emit(success, error, proxies)

        self._test_thread = QThread()
        self._test_worker = TestWorker(api_url)
        self._test_worker.moveToThread(self._test_thread)
        self._test_thread.started.connect(self._test_worker.run)
        self._test_worker.finished.connect(self._on_test_finished)
        self._test_worker.finished.connect(self._test_thread.quit)
        self._test_worker.finished.connect(self._test_worker.deleteLater)
        self._test_thread.finished.connect(self._test_thread.deleteLater)
        self._test_thread.start()

    def _on_test_finished(self, success: bool, error: str, proxies: list):
        """检测完成回调"""
        self.testApiSpinner.hide()
        self.testApiStatus.show()

        if success:
            if error:
                self.testApiStatus.setText("⚠")
                self.testApiStatus.setStyleSheet("color: orange; font-size: 16px; font-weight: bold;")
                logging.warning(f"API检测成功但有警告: {error}")
                InfoBar.warning("API检测警告", error, parent=self.window(), position=InfoBarPosition.TOP, duration=5000)
            else:
                self.testApiStatus.setText("✔")
                self.testApiStatus.setStyleSheet("color: green; font-size: 16px; font-weight: bold;")
                logging.info(f"API检测成功，获取到 {len(proxies)} 个代理")
        else:
            self.testApiStatus.setText("✖")
            self.testApiStatus.setStyleSheet("color: red; font-size: 16px; font-weight: bold;")
            logging.error(f"API检测失败: {error}")
            InfoBar.error("API检测失败", error, parent=self.window(), position=InfoBarPosition.TOP, duration=5000)

        # 3秒后恢复按钮
        from PySide6.QtCore import QTimer
        QTimer.singleShot(3000, self._reset_test_button)

    def _reset_test_button(self):
        """重置检测按钮状态"""
        self.testApiStatus.hide()
        self.testApiBtn.show()

    def _on_api_edit_finished(self):
        """API地址输入完成时同步到全局变量"""
        from wjx.network.proxy import set_proxy_api_override
        api_url = self.customApiEdit.text().strip()
        set_proxy_api_override(api_url if api_url else None)

    def isChecked(self):
        return self.switchButton.isChecked()

    def setChecked(self, checked):
        self.switchButton.setChecked(checked)

    def _sync_ip_enabled(self, enabled: bool):
        """开关联动：开启时启用展开内容，关闭时仅灰掉地区/自定义API行。
        代理源选择始终可用，方便用户在额度耗尽时切换到自定义代理源。
        """
        from PySide6.QtWidgets import QGraphicsOpacityEffect
        self.areaRow.setEnabled(bool(enabled))
        self.proxyCombo.setEnabled(True)
        self.customApiRow.setEnabled(True)
        # 清除容器级别的透明度，避免代理源行也变灰
        self._groupContainer.setGraphicsEffect(None)
        # 只对地区行加半透明效果（指定地区在开关关闭时无意义）
        eff = self.areaRow.graphicsEffect()
        if eff is None:
            eff = QGraphicsOpacityEffect(self.areaRow)
            self.areaRow.setGraphicsEffect(eff)
        eff.setOpacity(1.0 if enabled else 0.4)

    def _build_kuaidaili_panel(self):
        """构建快代理配置面板"""
        from PySide6.QtWidgets import QFrame
        from PySide6.QtCore import Signal as QtSignal
        from qfluentwidgets import TransparentToolButton, IndeterminateProgressRing
        
        panel_layout = QVBoxLayout(self.kuaidailiPanel)
        panel_layout.setContentsMargins(0, 8, 0, 0)
        panel_layout.setSpacing(12)

        # Secret ID
        id_row = QHBoxLayout()
        id_row.addWidget(BodyLabel("Secret ID"))
        id_row.addStretch()
        self.kuaidailiSecretIdEdit = LineEdit()
        self.kuaidailiSecretIdEdit.setMinimumWidth(300)
        self.kuaidailiSecretIdEdit.setPlaceholderText("请输入快代理 Secret ID")
        id_row.addWidget(self.kuaidailiSecretIdEdit)
        panel_layout.addLayout(id_row)

        # Secret Key (密码模式)
        key_row = QHBoxLayout()
        key_row.addWidget(BodyLabel("Secret Key"))
        key_row.addStretch()
        self.kuaidailiSecretKeyEdit = LineEdit()
        self.kuaidailiSecretKeyEdit.setMinimumWidth(300)
        self.kuaidailiSecretKeyEdit.setEchoMode(LineEdit.EchoMode.Password)
        self.kuaidailiSecretKeyEdit.setPlaceholderText("请输入快代理 Secret Key")
        # 显示/隐藏密码按钮
        self.kuaidailiShowKeyBtn = TransparentToolButton(FluentIcon.VIEW)
        self.kuaidailiShowKeyBtn.setToolTip("显示/隐藏密钥")
        self.kuaidailiShowKeyBtn.clicked.connect(self._toggle_kuaidaili_key_visibility)
        key_row.addWidget(self.kuaidailiSecretKeyEdit)
        key_row.addWidget(self.kuaidailiShowKeyBtn)
        panel_layout.addLayout(key_row)

        # 认证方式
        auth_row = QHBoxLayout()
        auth_row.addWidget(BodyLabel("认证方式"))
        auth_row.addStretch()
        self.kuaidailiAuthModeCombo = ComboBox()
        self.kuaidailiAuthModeCombo.addItem("密钥令牌（推荐）", userData="token")
        self.kuaidailiAuthModeCombo.addItem("数字签名（最安全）", userData="signature")
        self.kuaidailiAuthModeCombo.setMinimumWidth(200)
        auth_row.addWidget(self.kuaidailiAuthModeCombo)
        panel_layout.addLayout(auth_row)

        # 分隔线
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.Shape.HLine)
        separator1.setStyleSheet("background-color: #e0e0e0;")
        separator1.setFixedHeight(1)
        panel_layout.addWidget(separator1)

        # 地区选择（多选）
        area_row = QHBoxLayout()
        area_row.addWidget(BodyLabel("地区选择"))
        area_hint = BodyLabel("(留空表示全国随机)")
        area_hint.setStyleSheet("color: gray; font-size: 11px;")
        area_row.addWidget(area_hint)
        area_row.addStretch()
        self.kuaidailiAreaSelect = KuaidailiAreaSelectWidget()
        self.kuaidailiAreaSelect.areasChanged.connect(self._on_kuaidaili_areas_changed)
        area_row.addWidget(self.kuaidailiAreaSelect)
        panel_layout.addLayout(area_row)

        # 分隔线
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setStyleSheet("background-color: #e0e0e0;")
        separator2.setFixedHeight(1)
        panel_layout.addWidget(separator2)

        # 本机IP + 白名单操作
        ip_row = QHBoxLayout()
        ip_row.addWidget(BodyLabel("本机IP"))
        ip_row.addStretch()
        self.kuaidailiPublicIpLabel = BodyLabel("点击刷新获取")
        self.kuaidailiPublicIpLabel.setStyleSheet("color: gray;")
        self.kuaidailiRefreshIpBtn = TransparentToolButton(FluentIcon.SYNC)
        self.kuaidailiRefreshIpBtn.setToolTip("刷新本机公网IP")
        self.kuaidailiRefreshIpBtn.clicked.connect(self._refresh_kuaidaili_public_ip)
        self.kuaidailiAddWhitelistBtn = PushButton("添加到白名单")
        self.kuaidailiAddWhitelistBtn.clicked.connect(self._on_add_kuaidaili_whitelist_clicked)
        ip_row.addWidget(self.kuaidailiPublicIpLabel)
        ip_row.addWidget(self.kuaidailiRefreshIpBtn)
        ip_row.addWidget(self.kuaidailiAddWhitelistBtn)
        panel_layout.addLayout(ip_row)

        # 分隔线
        separator3 = QFrame()
        separator3.setFrameShape(QFrame.Shape.HLine)
        separator3.setStyleSheet("background-color: #e0e0e0;")
        separator3.setFixedHeight(1)
        panel_layout.addWidget(separator3)

        # 测试连接
        test_row = QHBoxLayout()
        test_row.addStretch()
        self.kuaidailiLoadLocalBtn = PushButton("本地读取加载")
        self.kuaidailiLoadLocalBtn.clicked.connect(self._on_load_local_credentials_clicked)
        self.kuaidailiFetchAuthBtn = PushButton("获取代理鉴权")
        self.kuaidailiFetchAuthBtn.setToolTip("获取代理用户名密码，用于跨设备使用")
        self.kuaidailiFetchAuthBtn.clicked.connect(self._on_fetch_proxy_auth_clicked)
        self.kuaidailiTestBtn = PushButton("测试连接")
        self.kuaidailiTestBtn.clicked.connect(self._on_test_kuaidaili_clicked)
        self.kuaidailiTestSpinner = IndeterminateProgressRing()
        self.kuaidailiTestSpinner.setFixedSize(20, 20)
        self.kuaidailiTestSpinner.hide()
        test_row.addWidget(self.kuaidailiLoadLocalBtn)
        test_row.addWidget(self.kuaidailiFetchAuthBtn)
        test_row.addWidget(self.kuaidailiTestBtn)
        test_row.addWidget(self.kuaidailiTestSpinner)
        panel_layout.addLayout(test_row)

        # 状态显示
        self.kuaidailiStatusLabel = BodyLabel("")
        self.kuaidailiStatusLabel.setWordWrap(True)
        panel_layout.addWidget(self.kuaidailiStatusLabel)

    def _toggle_kuaidaili_key_visibility(self):
        """切换快代理密钥显示/隐藏"""
        if self.kuaidailiSecretKeyEdit.echoMode() == LineEdit.EchoMode.Password:
            self.kuaidailiSecretKeyEdit.setEchoMode(LineEdit.EchoMode.Normal)
            self.kuaidailiShowKeyBtn.setIcon(FluentIcon.HIDE)
        else:
            self.kuaidailiSecretKeyEdit.setEchoMode(LineEdit.EchoMode.Password)
            self.kuaidailiShowKeyBtn.setIcon(FluentIcon.VIEW)

    def _on_test_kuaidaili_clicked(self):
        """测试快代理连接"""
        from PySide6.QtCore import QThread, Signal as QtSignal, QObject
        
        secret_id = self.kuaidailiSecretIdEdit.text().strip()
        secret_key = self.kuaidailiSecretKeyEdit.text().strip()
        if not secret_id or not secret_key:
            InfoBar.warning("", "请先输入 Secret ID 和 Secret Key", parent=self.window(), position=InfoBarPosition.TOP, duration=3000)
            return

        auth_mode = self.kuaidailiAuthModeCombo.currentData() or "token"
        areas = self.kuaidailiAreaSelect.get_selected_areas()

        self.kuaidailiTestBtn.hide()
        self.kuaidailiTestSpinner.show()
        self.kuaidailiStatusLabel.setText("正在测试连接...")
        self.kuaidailiStatusLabel.setStyleSheet("color: gray;")

        class TestWorker(QObject):
            finished = QtSignal(bool, str, int)  # success, message, proxy_count

            def __init__(self, secret_id, secret_key, auth_mode, areas):
                super().__init__()
                self.secret_id = secret_id
                self.secret_key = secret_key
                self.auth_mode = auth_mode
                self.areas = areas

            def run(self):
                try:
                    # 临时设置配置
                    from wjx.network.proxy.kuaidaili_config import set_kuaidaili_config
                    set_kuaidaili_config(
                        secret_id=self.secret_id,
                        secret_key=self.secret_key,
                        auth_mode=self.auth_mode,
                        areas=self.areas
                    )
                    
                    # 测试连接
                    from wjx.network.proxy.kuaidaili_adapter import test_kuaidaili_connection
                    result = test_kuaidaili_connection()
                    success = result.get("success", False)
                    message = result.get("message", "")
                    proxy_count = result.get("proxy_count", 0)
                    self.finished.emit(success, message, proxy_count)
                except Exception as e:
                    self.finished.emit(False, str(e), 0)

        self._kuaidaili_test_thread = QThread()
        self._kuaidaili_test_worker = TestWorker(secret_id, secret_key, auth_mode, areas)
        self._kuaidaili_test_worker.moveToThread(self._kuaidaili_test_thread)
        self._kuaidaili_test_thread.started.connect(self._kuaidaili_test_worker.run)
        self._kuaidaili_test_worker.finished.connect(self._on_kuaidaili_test_finished)
        self._kuaidaili_test_worker.finished.connect(self._kuaidaili_test_thread.quit)
        self._kuaidaili_test_worker.finished.connect(self._kuaidaili_test_worker.deleteLater)
        self._kuaidaili_test_thread.finished.connect(self._kuaidaili_test_thread.deleteLater)
        self._kuaidaili_test_thread.start()

    def _on_kuaidaili_test_finished(self, success: bool, message: str, proxy_count: int):
        """快代理测试完成回调"""
        self.kuaidailiTestSpinner.hide()
        self.kuaidailiTestBtn.show()

        if success:
            self.kuaidailiStatusLabel.setText(f"✔ 连接成功，获取到 {proxy_count} 个代理")
            self.kuaidailiStatusLabel.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.kuaidailiStatusLabel.setText(f"✖ {message}")
            self.kuaidailiStatusLabel.setStyleSheet("color: red;")

    def _refresh_kuaidaili_public_ip(self):
        """刷新本机公网IP"""
        from PySide6.QtCore import QThread, Signal as QtSignal, QObject
        
        self.kuaidailiPublicIpLabel.setText("获取中...")
        self.kuaidailiPublicIpLabel.setStyleSheet("color: gray;")
        self.kuaidailiRefreshIpBtn.setEnabled(False)

        class IpWorker(QObject):
            finished = QtSignal(str, str)  # ip, error

            def run(self):
                try:
                    from wjx.network.proxy.kuaidaili import get_public_ip
                    ip = get_public_ip()
                    self.finished.emit(ip, "")
                except Exception as e:
                    self.finished.emit("", str(e))

        self._ip_thread = QThread()
        self._ip_worker = IpWorker()
        self._ip_worker.moveToThread(self._ip_thread)
        self._ip_thread.started.connect(self._ip_worker.run)
        self._ip_worker.finished.connect(self._on_public_ip_fetched)
        self._ip_worker.finished.connect(self._ip_thread.quit)
        self._ip_worker.finished.connect(self._ip_worker.deleteLater)
        self._ip_thread.finished.connect(self._ip_thread.deleteLater)
        self._ip_thread.start()

    def _on_public_ip_fetched(self, ip: str, error: str):
        """公网IP获取完成回调"""
        self.kuaidailiRefreshIpBtn.setEnabled(True)
        if ip:
            self.kuaidailiPublicIpLabel.setText(ip)
            self.kuaidailiPublicIpLabel.setStyleSheet("color: black;")
        else:
            self.kuaidailiPublicIpLabel.setText("获取失败")
            self.kuaidailiPublicIpLabel.setStyleSheet("color: red;")
            if error:
                logging.error(f"获取公网IP失败: {error}")

    def _on_add_kuaidaili_whitelist_clicked(self):
        """添加本机IP到快代理白名单"""
        from PySide6.QtCore import QThread, Signal as QtSignal, QObject
        
        ip = self.kuaidailiPublicIpLabel.text()
        if not ip or ip in ("点击刷新获取", "获取中...", "获取失败"):
            InfoBar.warning("", "请先获取本机公网IP", parent=self.window(), position=InfoBarPosition.TOP, duration=3000)
            return

        secret_id = self.kuaidailiSecretIdEdit.text().strip()
        secret_key = self.kuaidailiSecretKeyEdit.text().strip()
        if not secret_id or not secret_key:
            InfoBar.warning("", "请先输入 Secret ID 和 Secret Key", parent=self.window(), position=InfoBarPosition.TOP, duration=3000)
            return

        auth_mode = self.kuaidailiAuthModeCombo.currentData() or "token"

        self.kuaidailiAddWhitelistBtn.setEnabled(False)
        self.kuaidailiAddWhitelistBtn.setText("添加中...")

        class WhitelistWorker(QObject):
            finished = QtSignal(bool, str)  # success, message

            def __init__(self, secret_id, secret_key, ip, auth_mode):
                super().__init__()
                self.secret_id = secret_id
                self.secret_key = secret_key
                self.ip = ip
                self.auth_mode = auth_mode

            def run(self):
                try:
                    from wjx.network.proxy.kuaidaili import KuaidailiAuth, add_ip_to_whitelist
                    auth = KuaidailiAuth(self.secret_id, self.secret_key)
                    success = add_ip_to_whitelist(auth, self.ip, self.auth_mode)
                    if success:
                        self.finished.emit(True, f"IP {self.ip} 已添加到白名单")
                    else:
                        self.finished.emit(False, "添加白名单失败")
                except Exception as e:
                    self.finished.emit(False, str(e))

        self._whitelist_thread = QThread()
        self._whitelist_worker = WhitelistWorker(secret_id, secret_key, ip, auth_mode)
        self._whitelist_worker.moveToThread(self._whitelist_thread)
        self._whitelist_thread.started.connect(self._whitelist_worker.run)
        self._whitelist_worker.finished.connect(self._on_whitelist_added)
        self._whitelist_worker.finished.connect(self._whitelist_thread.quit)
        self._whitelist_worker.finished.connect(self._whitelist_worker.deleteLater)
        self._whitelist_thread.finished.connect(self._whitelist_thread.deleteLater)
        self._whitelist_thread.start()

    def _on_whitelist_added(self, success: bool, message: str):
        """白名单添加完成回调"""
        self.kuaidailiAddWhitelistBtn.setEnabled(True)
        self.kuaidailiAddWhitelistBtn.setText("添加到白名单")
        if success:
            InfoBar.success("", message, parent=self.window(), position=InfoBarPosition.TOP, duration=3000)
        else:
            # 检查是否是 -108 错误（IP不在API调用授权白名单）
            if "-108" in message or "whitelist not match" in message.lower():
                InfoBar.error(
                    "API调用授权白名单错误", 
                    "当前IP不在API调用授权白名单中，请先登录快代理后台手动添加",
                    parent=self.window(), 
                    position=InfoBarPosition.TOP, 
                    duration=8000
                )
                self.kuaidailiStatusLabel.setText(
                    "⚠ 请先在快代理后台添加本机IP到API调用授权白名单：\n"
                    "登录快代理 → API接口 → 密钥管理 → API调用授权 → 添加IP"
                )
                self.kuaidailiStatusLabel.setStyleSheet("color: orange;")
            else:
                InfoBar.error("添加白名单失败", message, parent=self.window(), position=InfoBarPosition.TOP, duration=5000)

    def _on_load_local_credentials_clicked(self):
        """从本地 credentials.yml 加载快代理凭证"""
        from wjx.utils.io.kuaidaili_credentials import load_kuaidaili_credentials
        
        credentials = load_kuaidaili_credentials()
        if credentials.secret_id or credentials.secret_key:
            self.kuaidailiSecretIdEdit.setText(credentials.secret_id)
            self.kuaidailiSecretKeyEdit.setText(credentials.secret_key)
            InfoBar.success("", "凭证加载成功", parent=self.window(), position=InfoBarPosition.TOP, duration=2000)
        else:
            InfoBar.warning("", "未找到本地凭证或凭证为空", parent=self.window(), position=InfoBarPosition.TOP, duration=3000)

    def _on_fetch_proxy_auth_clicked(self):
        """获取代理鉴权信息（用户名密码）并保存"""
        from PySide6.QtCore import QThread, Signal as QtSignal, QObject
        
        secret_id = self.kuaidailiSecretIdEdit.text().strip()
        secret_key = self.kuaidailiSecretKeyEdit.text().strip()
        if not secret_id or not secret_key:
            InfoBar.warning("", "请先输入 Secret ID 和 Secret Key", parent=self.window(), position=InfoBarPosition.TOP, duration=3000)
            return

        auth_mode = self.kuaidailiAuthModeCombo.currentData() or "token"

        self.kuaidailiFetchAuthBtn.setEnabled(False)
        self.kuaidailiFetchAuthBtn.setText("获取中...")

        class FetchAuthWorker(QObject):
            finished = QtSignal(bool, str, str, str)  # success, message, username, password

            def __init__(self, secret_id, secret_key, auth_mode):
                super().__init__()
                self.secret_id = secret_id
                self.secret_key = secret_key
                self.auth_mode = auth_mode

            def run(self):
                try:
                    from wjx.network.proxy.kuaidaili import KuaidailiAuth, get_proxy_authorization
                    auth = KuaidailiAuth(self.secret_id, self.secret_key)
                    # plaintext=1 获取明文密码
                    result = get_proxy_authorization(auth, self.auth_mode, plaintext=1)
                    username = result.get("username", "")
                    password = result.get("password", "")
                    if username and password:
                        self.finished.emit(True, "获取成功", username, password)
                    else:
                        self.finished.emit(False, "返回的鉴权信息为空", "", "")
                except Exception as e:
                    self.finished.emit(False, str(e), "", "")

        self._fetch_auth_thread = QThread()
        self._fetch_auth_worker = FetchAuthWorker(secret_id, secret_key, auth_mode)
        self._fetch_auth_worker.moveToThread(self._fetch_auth_thread)
        self._fetch_auth_thread.started.connect(self._fetch_auth_worker.run)
        self._fetch_auth_worker.finished.connect(self._on_proxy_auth_fetched)
        self._fetch_auth_worker.finished.connect(self._fetch_auth_thread.quit)
        self._fetch_auth_worker.finished.connect(self._fetch_auth_worker.deleteLater)
        self._fetch_auth_thread.finished.connect(self._fetch_auth_thread.deleteLater)
        self._fetch_auth_thread.start()

    def _on_proxy_auth_fetched(self, success: bool, message: str, username: str, password: str):
        """代理鉴权信息获取完成回调"""
        self.kuaidailiFetchAuthBtn.setEnabled(True)
        self.kuaidailiFetchAuthBtn.setText("获取代理鉴权")
        
        if success:
            # 保存到凭证文件
            from wjx.utils.io.kuaidaili_credentials import (
                KuaidailiCredentials,
                load_kuaidaili_credentials,
                save_kuaidaili_credentials,
            )
            existing = load_kuaidaili_credentials()
            save_kuaidaili_credentials(KuaidailiCredentials(
                secret_id=self.kuaidailiSecretIdEdit.text().strip() or existing.secret_id,
                secret_key=self.kuaidailiSecretKeyEdit.text().strip() or existing.secret_key,
                proxy_username=username,
                proxy_password=password,
            ))
            InfoBar.success("", f"代理鉴权已保存 (用户名: {username[:4]}***)", parent=self.window(), position=InfoBarPosition.TOP, duration=3000)
        else:
            InfoBar.error("获取代理鉴权失败", message, parent=self.window(), position=InfoBarPosition.TOP, duration=5000)

    def _on_kuaidaili_areas_changed(self, areas: list):
        """快代理地区选择变化时同步到代理模块"""
        try:
            from wjx.network.proxy.kuaidaili_config import set_kuaidaili_config
            # 只更新地区，保留其他配置
            set_kuaidaili_config(areas=areas)
            logging.debug(f"快代理地区已更新: {areas}")
        except Exception as e:
            logging.error(f"同步快代理地区配置失败: {e}")

    def get_kuaidaili_config(self) -> dict:
        """获取快代理配置"""
        return {
            "secret_id": self.kuaidailiSecretIdEdit.text().strip(),
            "secret_key": self.kuaidailiSecretKeyEdit.text().strip(),
            "auth_mode": self.kuaidailiAuthModeCombo.currentData() or "token",
            "areas": self.kuaidailiAreaSelect.get_selected_areas(),
        }

    def set_kuaidaili_config(self, secret_id: str = "", secret_key: str = "", auth_mode: str = "token", areas: Optional[list] = None):
        """设置快代理配置"""
        self.kuaidailiSecretIdEdit.setText(secret_id)
        self.kuaidailiSecretKeyEdit.setText(secret_key)
        
        # 设置认证方式
        auth_idx = self.kuaidailiAuthModeCombo.findData(auth_mode)
        if auth_idx >= 0:
            self.kuaidailiAuthModeCombo.setCurrentIndex(auth_idx)
        
        # 设置地区
        self.kuaidailiAreaSelect.set_selected_areas(areas)


class TimedModeSettingCard(SettingCard):
    """定时模式设置卡 - 带帮助按钮"""

    def __init__(self, icon, title, content, parent=None):
        super().__init__(icon, title, content, parent)
        from PySide6.QtCore import QSize
        self.helpButton = TransparentToolButton(FluentIcon.INFO, self)
        self.helpButton.setFixedSize(18, 18)
        self.helpButton.setIconSize(QSize(14, 14))
        self.helpButton.setCursor(Qt.CursorShape.PointingHandCursor)
        # 创建标题行布局，把图标放在标题右边
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(4)
        self.vBoxLayout.removeWidget(self.titleLabel)
        title_row.addWidget(self.titleLabel)
        title_row.addWidget(self.helpButton)
        title_row.addStretch()
        self.vBoxLayout.insertLayout(0, title_row)
        self.switchButton = SwitchButton(self, IndicatorPosition.RIGHT)
        self.switchButton.setOnText("开")
        self.switchButton.setOffText("关")
        self.hBoxLayout.addWidget(self.switchButton, 0, Qt.AlignmentFlag.AlignRight)
        self.hBoxLayout.addSpacing(16)

    def isChecked(self):
        return self.switchButton.isChecked()

    def setChecked(self, checked):
        self.switchButton.setChecked(checked)


class RandomUASettingCard(ExpandGroupSettingCard):
    """随机UA设置卡 - 包含设备类型占比配置"""

    def __init__(self, parent=None):
        super().__init__(FluentIcon.ROBOT, "随机 UA", "模拟不同的 User-Agent，例如微信环境或浏览器直链环境", parent)

        # 开关
        self.switchButton = SwitchButton(self, IndicatorPosition.RIGHT)
        self.switchButton.setOnText("开")
        self.switchButton.setOffText("关")
        self.addWidget(self.switchButton)

        # 设备占比配置容器
        self._groupContainer = QWidget()
        layout = QVBoxLayout(self._groupContainer)
        layout.setContentsMargins(48, 12, 48, 12)
        layout.setSpacing(16)

        # 提示信息
        hint_label = BodyLabel("配置不同设备类型的访问占比，三个滑块占比总和必须为 100%", self._groupContainer)
        hint_label.setStyleSheet("color: #606060; font-size: 12px;")
        layout.addWidget(hint_label)

        # 三联动占比滑块
        from wjx.ui.widgets.ratio_slider import RatioSlider
        self.ratioSlider = RatioSlider(
            labels={
                "wechat": "微信访问占比",
                "mobile": "手机访问占比",
                "pc": "链接访问占比",
            },
            parent=self._groupContainer
        )
        layout.addWidget(self.ratioSlider)

        self.addGroupWidget(self._groupContainer)
        self.setExpand(True)
        # 开关联动：关闭时禁用展开内容
        self.switchButton.checkedChanged.connect(self.setUAEnabled)
        self.setUAEnabled(False)

    def isChecked(self):
        return self.switchButton.isChecked()

    def setChecked(self, checked):
        self.switchButton.setChecked(checked)

    def setUAEnabled(self, enabled):
        from PySide6.QtWidgets import QGraphicsOpacityEffect
        self._groupContainer.setEnabled(bool(enabled))
        effect = self._groupContainer.graphicsEffect()
        if effect is None:
            effect = QGraphicsOpacityEffect(self._groupContainer)
            self._groupContainer.setGraphicsEffect(effect)
        effect.setOpacity(1.0 if enabled else 0.4)

    def getRatios(self) -> dict:
        """获取当前设备占比配置"""
        return self.ratioSlider.getValues()

    def setRatios(self, ratios: dict):
        """设置设备占比配置"""
        self.ratioSlider.setValues(ratios)


class ReliabilitySettingCard(ExpandGroupSettingCard):
    """信效度设置卡 - 开关 + 目标 Alpha 输入框

    使用 ExpandGroupSettingCard 承载一个总开关和一行数值输入：
    - 开关：控制是否启用信效度优化
    - 输入框：目标 Cronbach's Alpha 系数，范围 0.70-0.95
    """

    def __init__(self, parent=None):
        super().__init__(
            FluentIcon.CERTIFICATE,
            "提升问卷信效度",
            "启用后量表/矩阵/评价题将共享答题倾向，针对信效度优化作答策略",
            parent,
        )

        # 顶部开关
        self.switchButton = SwitchButton(self, IndicatorPosition.RIGHT)
        self.switchButton.setOnText("开")
        self.switchButton.setOffText("关")
        self.addWidget(self.switchButton)

        # 展开区域容器
        self._groupContainer = QWidget(self)
        layout = QVBoxLayout(self._groupContainer)
        layout.setContentsMargins(48, 12, 48, 12)
        layout.setSpacing(12)

        # 目标信度 Alpha 行
        alpha_row = QHBoxLayout()
        alpha_row.setContentsMargins(0, 0, 0, 0)
        alpha_row.setSpacing(8)

        alpha_label = BodyLabel("目标 Cronbach's α 系数", self._groupContainer)
        self.alphaEdit = LineEdit(self._groupContainer)
        self.alphaEdit.setPlaceholderText("0.70 - 0.95（默认 0.85）")
        self.alphaEdit.setFixedWidth(120)
        self.alphaEdit.setFixedHeight(36)

        # 仅允许 0.70 - 0.95 的两位小数
        validator = QDoubleValidator(0.70, 0.95, 2, self.alphaEdit)
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.alphaEdit.setValidator(validator)

        alpha_row.addWidget(alpha_label)
        alpha_row.addStretch(1)
        alpha_row.addWidget(self.alphaEdit)

        layout.addLayout(alpha_row)

        self.addGroupWidget(self._groupContainer)
        self.setExpand(True)

        # 开关联动：关闭时禁用展开内容
        self.switchButton.checkedChanged.connect(self._sync_enabled)
        self._sync_enabled(False)

    def _sync_enabled(self, enabled: bool) -> None:
        """根据开关状态启用/禁用内部控件。"""

        self._groupContainer.setEnabled(bool(enabled))

    def isChecked(self) -> bool:
        return self.switchButton.isChecked()

    def setChecked(self, checked: bool) -> None:
        self.switchButton.setChecked(bool(checked))

    def get_alpha(self) -> float:
        """读取并裁剪目标 Alpha 值，落在 0.70-0.95 之间。

        输入非法或为空时回退到 0.85。
        """

        text = (self.alphaEdit.text() or "").strip()
        try:
            value = float(text)
        except Exception:
            value = 0.85

        if value != value:  # NaN 兜底
            value = 0.85

        value = max(0.70, min(0.95, value))
        return value

    def set_alpha(self, value: float) -> None:
        """设置目标 Alpha，并同步到输入框文本。"""

        try:
            num = float(value)
        except Exception:
            num = 0.85
        num = max(0.70, min(0.95, num))
        # 保留两位小数，去掉多余 0
        text = f"{num:.2f}".rstrip("0").rstrip(".")
        if not text:
            text = "0.85"
        if self.alphaEdit.text() != text:
            self.alphaEdit.setText(text)


class TimeRangeSettingCard(SettingCard):
    """时间设置卡 - 使用普通数字输入框（秒）"""

    valueChanged = Signal(int)

    def __init__(self, icon, title, content, max_seconds: int = 300, parent=None):
        super().__init__(icon, title, content, parent)

        self.max_seconds = max_seconds
        self._current_value = 0

        self._input_container = QWidget(self)
        input_layout = QHBoxLayout(self._input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(8)

        self.inputEdit = LineEdit(self._input_container)
        self.inputEdit.setValidator(QIntValidator(0, max_seconds, self.inputEdit))
        self.inputEdit.setFixedWidth(128)
        self.inputEdit.setFixedHeight(36)
        self.inputEdit.setText("0")
        self.inputEdit.setToolTip(f"允许范围：0-{max_seconds} 秒")
        self.inputEdit.textChanged.connect(self._on_text_changed)
        self.inputEdit.editingFinished.connect(self._normalize_text)

        sec_label = BodyLabel("秒", self._input_container)
        sec_label.setStyleSheet("color: #606060;")

        input_layout.addWidget(self.inputEdit)
        input_layout.addWidget(sec_label)

        self.value_edit.editingFinished.connect(self._normalize_inputs)
        self.setValue(0)

        self.hBoxLayout.addWidget(self._input_container, 0, Qt.AlignmentFlag.AlignRight)
        self.hBoxLayout.addSpacing(16)

    def _clamp_value(self, value: int) -> int:
        return max(0, min(int(value), self.max_seconds))

    @staticmethod
    def _parse_digits(text: str, fallback: int) -> int:
        raw = str(text or "").strip()
        return int(raw) if raw.isdigit() else int(fallback)

    def _on_text_changed(self, text: str):
        value = self._clamp_value(self._parse_digits(text, fallback=0))
        if value != self._current_value:
            self._current_value = value
            self.valueChanged.emit(value)

    def _normalize_text(self):
        self.setValue(self.getValue())

    def setEnabled(self, enabled):
        super().setEnabled(enabled)
        self.inputEdit.setEnabled(enabled)

    def getValue(self) -> int:
        """获取当前秒数"""
        value = self._clamp_value(self._parse_digits(self.inputEdit.text(), fallback=self._current_value))
        self._current_value = value
        return value

    def setValue(self, value: int):
        """设置当前秒数"""
        value = self._clamp_value(value)
        previous = self._current_value
        self._current_value = value
        display = str(value)
        if self.inputEdit.text() != display:
            self.inputEdit.blockSignals(True)
            self.inputEdit.setText(display)
            self.inputEdit.blockSignals(False)
        if value != previous:
            self.valueChanged.emit(value)

    def getRange(self) -> tuple:
        """兼容调用方：返回 (秒数, 秒数)"""
        sec = self.getValue()
        return sec, sec

    def setRange(self, min_sec: int, max_sec: int):
        """兼容调用方：仅使用 min_sec 作为固定秒数"""
        self.setValue(min_sec)


