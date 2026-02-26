"""快代理配置面板组件"""
import logging
from typing import List, Optional

from PySide6.QtCore import Qt, QThread, QObject, Signal as QtSignal
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget, QFrame
from qfluentwidgets import (
    BodyLabel,
    ComboBox,
    FluentIcon,
    IndeterminateProgressRing,
    InfoBar,
    InfoBarPosition,
    LineEdit,
    PushButton,
    TransparentToolButton,
)

from wjx.ui.widgets.kuaidaili_area_select import KuaidailiAreaSelectWidget


class KuaidailiConfigPanel(QWidget):
    """快代理配置面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        """构建快代理配置面板"""
        panel_layout = QVBoxLayout(self)
        panel_layout.setContentsMargins(0, 8, 0, 0)
        panel_layout.setSpacing(12)

        # Secret ID
        id_row = QHBoxLayout()
        id_row.addWidget(BodyLabel("Secret ID"))
        id_row.addStretch()
        self.secretIdEdit = LineEdit()
        self.secretIdEdit.setMinimumWidth(300)
        self.secretIdEdit.setPlaceholderText("请输入快代理 Secret ID")
        id_row.addWidget(self.secretIdEdit)
        panel_layout.addLayout(id_row)

        # Secret Key (密码模式)
        key_row = QHBoxLayout()
        key_row.addWidget(BodyLabel("Secret Key"))
        key_row.addStretch()
        self.secretKeyEdit = LineEdit()
        self.secretKeyEdit.setMinimumWidth(300)
        self.secretKeyEdit.setEchoMode(LineEdit.EchoMode.Password)
        self.secretKeyEdit.setPlaceholderText("请输入快代理 Secret Key")
        # 显示/隐藏密码按钮
        self.showKeyBtn = TransparentToolButton(FluentIcon.VIEW)
        self.showKeyBtn.setToolTip("显示/隐藏密钥")
        self.showKeyBtn.clicked.connect(self._toggle_key_visibility)
        key_row.addWidget(self.secretKeyEdit)
        key_row.addWidget(self.showKeyBtn)
        panel_layout.addLayout(key_row)

        # 认证方式
        auth_row = QHBoxLayout()
        auth_row.addWidget(BodyLabel("认证方式"))
        auth_row.addStretch()
        self.authModeCombo = ComboBox()
        self.authModeCombo.addItem("密钥令牌（推荐）", userData="token")
        self.authModeCombo.addItem("数字签名（最安全）", userData="signature")
        self.authModeCombo.setMinimumWidth(200)
        auth_row.addWidget(self.authModeCombo)
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
        self.areaSelect = KuaidailiAreaSelectWidget()
        area_row.addWidget(self.areaSelect)
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
        self.publicIpLabel = BodyLabel("点击刷新获取")
        self.publicIpLabel.setStyleSheet("color: gray;")
        self.refreshIpBtn = TransparentToolButton(FluentIcon.SYNC)
        self.refreshIpBtn.setToolTip("刷新本机公网IP")
        self.refreshIpBtn.clicked.connect(self._refresh_public_ip)
        self.addWhitelistBtn = PushButton("添加到白名单")
        self.addWhitelistBtn.clicked.connect(self._on_add_whitelist_clicked)
        ip_row.addWidget(self.publicIpLabel)
        ip_row.addWidget(self.refreshIpBtn)
        ip_row.addWidget(self.addWhitelistBtn)
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
        self.loadLocalBtn = PushButton("本地读取加载")
        self.loadLocalBtn.clicked.connect(self._on_load_local_credentials_clicked)
        self.fetchAuthBtn = PushButton("获取代理鉴权")
        self.fetchAuthBtn.setToolTip("获取代理用户名密码，用于跨设备使用")
        self.fetchAuthBtn.clicked.connect(self._on_fetch_proxy_auth_clicked)
        self.testBtn = PushButton("测试连接")
        self.testBtn.clicked.connect(self._on_test_clicked)
        self.testSpinner = IndeterminateProgressRing()
        self.testSpinner.setFixedSize(20, 20)
        self.testSpinner.hide()
        test_row.addWidget(self.loadLocalBtn)
        test_row.addWidget(self.fetchAuthBtn)
        test_row.addWidget(self.testBtn)
        test_row.addWidget(self.testSpinner)
        panel_layout.addLayout(test_row)

        # 状态显示
        self.statusLabel = BodyLabel("")
        self.statusLabel.setWordWrap(True)
        panel_layout.addWidget(self.statusLabel)

    def _toggle_key_visibility(self):
        """切换快代理密钥显示/隐藏"""
        if self.secretKeyEdit.echoMode() == LineEdit.EchoMode.Password:
            self.secretKeyEdit.setEchoMode(LineEdit.EchoMode.Normal)
            self.showKeyBtn.setIcon(FluentIcon.HIDE)
        else:
            self.secretKeyEdit.setEchoMode(LineEdit.EchoMode.Password)
            self.showKeyBtn.setIcon(FluentIcon.VIEW)

    def _refresh_public_ip(self):
        """刷新本机公网IP"""
        self.publicIpLabel.setText("获取中...")
        self.publicIpLabel.setStyleSheet("color: gray;")
        self.refreshIpBtn.setEnabled(False)

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
        self.refreshIpBtn.setEnabled(True)
        if ip:
            self.publicIpLabel.setText(ip)
            self.publicIpLabel.setStyleSheet("color: black;")
        else:
            self.publicIpLabel.setText("获取失败")
            self.publicIpLabel.setStyleSheet("color: red;")
            if error:
                logging.error(f"获取公网IP失败: {error}")

    def _on_add_whitelist_clicked(self):
        """添加本机IP到快代理白名单"""
        ip = self.publicIpLabel.text()
        if not ip or ip in ("点击刷新获取", "获取中...", "获取失败"):
            InfoBar.warning("", "请先获取本机公网IP", parent=self.window(), position=InfoBarPosition.TOP, duration=3000)
            return

        secret_id = self.secretIdEdit.text().strip()
        secret_key = self.secretKeyEdit.text().strip()
        if not secret_id or not secret_key:
            InfoBar.warning("", "请先输入 Secret ID 和 Secret Key", parent=self.window(), position=InfoBarPosition.TOP, duration=3000)
            return

        auth_mode = self.authModeCombo.currentData() or "token"

        self.addWhitelistBtn.setEnabled(False)
        self.addWhitelistBtn.setText("添加中...")

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
        self.addWhitelistBtn.setEnabled(True)
        self.addWhitelistBtn.setText("添加到白名单")
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
                self.statusLabel.setText(
                    "⚠ 请先在快代理后台添加本机IP到API调用授权白名单：\n"
                    "登录快代理 → API接口 → 密钥管理 → API调用授权 → 添加IP"
                )
                self.statusLabel.setStyleSheet("color: orange;")
            else:
                InfoBar.error("添加白名单失败", message, parent=self.window(), position=InfoBarPosition.TOP, duration=5000)

    def _on_load_local_credentials_clicked(self):
        """从本地 credentials.yml 加载快代理凭证"""
        from wjx.utils.io.kuaidaili_credentials import load_kuaidaili_credentials

        credentials = load_kuaidaili_credentials()
        if credentials.secret_id or credentials.secret_key:
            self.secretIdEdit.setText(credentials.secret_id)
            self.secretKeyEdit.setText(credentials.secret_key)
            InfoBar.success("", "凭证加载成功", parent=self.window(), position=InfoBarPosition.TOP, duration=2000)
        else:
            InfoBar.warning("", "未找到本地凭证或凭证为空", parent=self.window(), position=InfoBarPosition.TOP, duration=3000)

    def _on_fetch_proxy_auth_clicked(self):
        """获取代理鉴权信息（用户名密码）并保存"""
        secret_id = self.secretIdEdit.text().strip()
        secret_key = self.secretKeyEdit.text().strip()
        if not secret_id or not secret_key:
            InfoBar.warning("", "请先输入 Secret ID 和 Secret Key", parent=self.window(), position=InfoBarPosition.TOP, duration=3000)
            return

        auth_mode = self.authModeCombo.currentData() or "token"

        self.fetchAuthBtn.setEnabled(False)
        self.fetchAuthBtn.setText("获取中...")

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
        self.fetchAuthBtn.setEnabled(True)
        self.fetchAuthBtn.setText("获取代理鉴权")

        if success:
            # 保存到凭证文件
            from wjx.utils.io.kuaidaili_credentials import (
                KuaidailiCredentials,
                load_kuaidaili_credentials,
                save_kuaidaili_credentials,
            )
            existing = load_kuaidaili_credentials()
            save_kuaidaili_credentials(KuaidailiCredentials(
                secret_id=self.secretIdEdit.text().strip() or existing.secret_id,
                secret_key=self.secretKeyEdit.text().strip() or existing.secret_key,
                proxy_username=username,
                proxy_password=password,
            ))
            InfoBar.success("", f"代理鉴权已保存 (用户名: {username[:4]}***)", parent=self.window(), position=InfoBarPosition.TOP, duration=3000)
        else:
            InfoBar.error("获取代理鉴权失败", message, parent=self.window(), position=InfoBarPosition.TOP, duration=5000)

    def _on_test_clicked(self):
        """测试快代理连接"""
        secret_id = self.secretIdEdit.text().strip()
        secret_key = self.secretKeyEdit.text().strip()
        if not secret_id or not secret_key:
            InfoBar.warning("", "请先输入 Secret ID 和 Secret Key", parent=self.window(), position=InfoBarPosition.TOP, duration=3000)
            return

        auth_mode = self.authModeCombo.currentData() or "token"
        areas = self.areaSelect.get_selected_areas()

        self.testBtn.hide()
        self.testSpinner.show()
        self.statusLabel.setText("正在测试连接...")
        self.statusLabel.setStyleSheet("color: gray;")

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
                    from wjx.network.proxy.kuaidaili import KuaidailiAuth, check_kuaidaili_connection
                    auth = KuaidailiAuth(self.secret_id, self.secret_key)
                    result = check_kuaidaili_connection(auth, self.auth_mode, self.areas)
                    success = result.get("success", False)
                    message = result.get("message", "")
                    proxies = result.get("proxies", [])
                    self.finished.emit(success, message, len(proxies) if proxies else 0)
                except Exception as e:
                    self.finished.emit(False, str(e), 0)

        self._test_thread = QThread()
        self._test_worker = TestWorker(secret_id, secret_key, auth_mode, areas)
        self._test_worker.moveToThread(self._test_thread)
        self._test_thread.started.connect(self._test_worker.run)
        self._test_worker.finished.connect(self._on_test_finished)
        self._test_worker.finished.connect(self._test_thread.quit)
        self._test_worker.finished.connect(self._test_worker.deleteLater)
        self._test_thread.finished.connect(self._test_thread.deleteLater)
        self._test_thread.start()

    def _on_test_finished(self, success: bool, message: str, proxy_count: int):
        """快代理测试完成回调"""
        self.testSpinner.hide()
        self.testBtn.show()

        if success:
            self.statusLabel.setText(f"✔ 连接成功，获取到 {proxy_count} 个代理")
            self.statusLabel.setStyleSheet("color: green; font-weight: bold;")
            # 保存凭证到本地
            self._save_credentials_to_local()
        else:
            self.statusLabel.setText(f"✖ {message}")
            self.statusLabel.setStyleSheet("color: red;")

    def _save_credentials_to_local(self):
        """保存凭证到本地文件"""
        try:
            from wjx.utils.io.kuaidaili_credentials import (
                KuaidailiCredentials,
                load_kuaidaili_credentials,
                save_kuaidaili_credentials,
            )
            existing = load_kuaidaili_credentials()
            save_kuaidaili_credentials(KuaidailiCredentials(
                secret_id=self.secretIdEdit.text().strip(),
                secret_key=self.secretKeyEdit.text().strip(),
                proxy_username=existing.proxy_username,
                proxy_password=existing.proxy_password,
            ))
            logging.debug("快代理凭证已保存到本地")
        except Exception as e:
            logging.error(f"保存快代理凭证失败: {e}")

    # 配置访问方法
    def get_config(self) -> dict:
        """获取快代理配置"""
        return {
            "secret_id": self.secretIdEdit.text().strip(),
            "secret_key": self.secretKeyEdit.text().strip(),
            "auth_mode": self.authModeCombo.currentData() or "token",
            "areas": self.areaSelect.get_selected_areas(),
        }

    def set_config(self, secret_id: str = "", secret_key: str = "", auth_mode: str = "token", areas: Optional[List[str]] = None):
        """设置快代理配置"""
        self.secretIdEdit.setText(secret_id)
        self.secretKeyEdit.setText(secret_key)

        # 设置认证方式
        auth_idx = self.authModeCombo.findData(auth_mode)
        if auth_idx >= 0:
            self.authModeCombo.setCurrentIndex(auth_idx)

        # 设置地区
        if areas:
            self.areaSelect.set_selected_areas(areas)
