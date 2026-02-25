"""联系开发者表单组件，可嵌入页面或对话框。"""
import re
import threading
from datetime import datetime
from typing import Optional, Callable, cast
import logging
from wjx.utils.logging.log_utils import log_suppressed_exception


from PySide6.QtCore import Qt, QTimer, Signal, QEvent
from PySide6.QtGui import QDoubleValidator, QIntValidator, QKeySequence, QGuiApplication, QKeyEvent
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFileDialog,
    QLabel,
)
from qfluentwidgets import (
    BodyLabel,
    LineEdit,
    ComboBox,
    PushButton,
    PrimaryPushButton,
    IndeterminateProgressRing,
    InfoBar,
    InfoBarPosition,
    MessageBox,
    Action,
    FluentIcon,
    IconWidget,
    RoundMenu,
    PlainTextEdit,
)

from wjx.ui.widgets.status_polling_mixin import StatusPollingMixin
from wjx.ui.helpers.image_attachments import ImageAttachmentManager
import wjx.network.http_client as http_client
from wjx.utils.app.config import CONTACT_API_URL, EMAIL_VERIFY_ENDPOINT
from wjx.utils.app.version import __VERSION__


class PasteOnlyLineEdit(LineEdit):
    """只显示 Fluent 风格“复制 / 粘贴 / 全选”菜单的 LineEdit。"""



    def __init__(self, parent=None, on_paste: Optional[Callable[[QWidget], bool]] = None):
        super().__init__(parent)
        self._on_paste = on_paste

    def contextMenuEvent(self, e):
        menu = RoundMenu(parent=self)
        copy_action = Action(FluentIcon.COPY, "复制", parent=menu)
        copy_action.setEnabled(self.hasSelectedText())
        copy_action.triggered.connect(self.copy)
        paste_action = Action(FluentIcon.PASTE, "粘贴", parent=menu)

        def _do_paste():
            if self._on_paste and self._on_paste(self):
                return
            self.paste()

        menu.addAction(copy_action)
        paste_action.triggered.connect(_do_paste)
        menu.addAction(paste_action)
        menu.exec(e.globalPos())
        e.accept()


class PasteOnlyPlainTextEdit(PlainTextEdit):
    """只显示 Fluent 风格“复制 / 粘贴 / 全选”菜单的 PlainTextEdit，兼容外部粘贴处理。"""

    def __init__(self, parent=None, on_paste: Optional[Callable[[QWidget], bool]] = None):
        super().__init__(parent)
        self._on_paste = on_paste

    def contextMenuEvent(self, e):
        menu = RoundMenu(parent=self)
        copy_action = Action(FluentIcon.COPY, "复制", parent=menu)
        copy_action.setEnabled(self.textCursor().hasSelection())
        copy_action.triggered.connect(self.copy)
        paste_action = Action(FluentIcon.PASTE, "粘贴", parent=menu)

        def _do_paste():
            if self._on_paste and self._on_paste(self):
                return
            self.paste()

        menu.addAction(copy_action)
        paste_action.triggered.connect(_do_paste)
        menu.addAction(paste_action)
        menu.exec(e.globalPos())
        e.accept()


class ContactForm(StatusPollingMixin, QWidget):
    """联系开发者表单，负责消息发送、状态轮询和附件处理。"""

    _statusLoaded = Signal(str, str)  # text, color
    _sendFinished = Signal(bool, str)  # success, message
    _verifyCodeFinished = Signal(bool, str, str)  # success, message, email

    sendSucceeded = Signal()
    cancelRequested = Signal()

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        default_type: str = "报错反馈",
        status_fetcher: Optional[Callable] = None,
        status_formatter: Optional[Callable] = None,
        show_cancel_button: bool = False,
        auto_clear_on_success: bool = True,
        manage_polling: bool = True,
    ):
        super().__init__(parent)
        self._sendFinished.connect(self._on_send_finished)
        self._verifyCodeFinished.connect(self._on_verify_code_finished)
        self._init_status_polling(status_fetcher, status_formatter)
        self._attachments = ImageAttachmentManager(max_count=3, max_size_bytes=10 * 1024 * 1024)
        self._current_message_type: str = ""
        self._current_has_email: bool = False
        self._verify_code_requested: bool = False
        self._verify_code_requested_email: str = ""
        self._verify_code_sending: bool = False
        self._cooldown_timer: Optional[QTimer] = None
        self._cooldown_remaining: int = 0
        self._polling_started = False
        self._auto_clear_on_success = auto_clear_on_success
        self._manage_polling = manage_polling

        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.setSpacing(16)

        # 顶部表单区
        form_layout = QVBoxLayout()
        form_layout.setSpacing(12)
        form_layout.setContentsMargins(0, 0, 0, 0)

        LABEL_WIDTH = 75

        # 1. 消息类型
        type_row = QHBoxLayout()
        self.type_label_static = BodyLabel("消息类型：", self)
        self.type_label_static.setFixedWidth(LABEL_WIDTH)
        self.type_combo = ComboBox(self)
        self.base_options = ["报错反馈", "卡密获取", "新功能建议", "纯聊天"]
        for item in self.base_options:
            self.type_combo.addItem(item, item)
        self.type_combo.setMinimumWidth(160)
        type_row.addWidget(self.type_label_static)
        type_row.addWidget(self.type_combo)
        type_row.addStretch(1)
        form_layout.addLayout(type_row)

        # 2. 邮箱 + 验证码（同一行）
        email_row = QHBoxLayout()
        self.email_label = BodyLabel("联系邮箱：", self)
        self.email_label.setFixedWidth(LABEL_WIDTH)
        self.email_edit = PasteOnlyLineEdit(self)
        self.email_edit.setPlaceholderText("name@example.com")
        email_row.addWidget(self.email_label)
        email_row.addWidget(self.email_edit)

        self.verify_code_edit = LineEdit(self)
        self.verify_code_edit.setPlaceholderText("6位验证码")
        self.verify_code_edit.setMaxLength(6)
        self.verify_code_edit.setValidator(QIntValidator(0, 999999, self))
        self.verify_code_edit.setMaximumWidth(120)

        self.send_verify_btn = PushButton("发送验证码", self)
        self.verify_send_spinner = IndeterminateProgressRing(self)
        self.verify_send_spinner.setFixedSize(16, 16)
        self.verify_send_spinner.setStrokeWidth(2)
        self.verify_send_spinner.hide()

        email_row.addSpacing(4)
        email_row.addWidget(self.send_verify_btn)
        email_row.addWidget(self.verify_send_spinner)
        email_row.addWidget(self.verify_code_edit)
        form_layout.addLayout(email_row)

        self.verify_code_edit.hide()
        self.send_verify_btn.hide()
        self.verify_send_spinner.hide()

        # 4. 卡密参数
        self.amount_row = QHBoxLayout()
        self.amount_label = BodyLabel("捐(施)助(舍)金额：￥", self)
        self.amount_edit = LineEdit(self)
        self.amount_edit.setPlaceholderText("🙏😭🙏")
        self.amount_edit.setMaximumWidth(100)
        validator = QDoubleValidator(0.0, 9999.99, 2, self)
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.amount_edit.setValidator(validator)
        self.amount_edit.textChanged.connect(self._on_amount_changed)

        self.quantity_label = BodyLabel("大概需求份数：", self)
        self.quantity_edit = LineEdit(self)
        self.quantity_edit.setPlaceholderText("1~9999")
        self.quantity_edit.setMaximumWidth(110)
        self.quantity_edit.setValidator(QIntValidator(1, 9999, self))
        self.quantity_edit.textChanged.connect(self._on_quantity_changed)

        self.urgency_label = BodyLabel("紧急程度：", self)
        self.urgency_combo = ComboBox(self)
        self.urgency_combo.setMaximumWidth(100)
        for urgency in ["低", "中", "高", "紧急"]:
            self.urgency_combo.addItem(urgency, urgency)
        urgency_default_index = self.urgency_combo.findText("中")
        if urgency_default_index >= 0:
            self.urgency_combo.setCurrentIndex(urgency_default_index)
        self.urgency_combo.currentIndexChanged.connect(lambda _: self._on_urgency_changed())

        self.amount_row.addWidget(self.amount_label)
        self.amount_row.addWidget(self.amount_edit)
        self.amount_row.addSpacing(16)
        self.amount_row.addWidget(self.quantity_label)
        self.amount_row.addWidget(self.quantity_edit)
        self.amount_row.addSpacing(16)
        self.amount_row.addWidget(self.urgency_label)
        self.amount_row.addWidget(self.urgency_combo)
        self.amount_row.addStretch(1)
        form_layout.addLayout(self.amount_row)

        self.amount_label.hide()
        self.amount_edit.hide()
        self.quantity_label.hide()
        self.quantity_edit.hide()
        self.urgency_label.hide()
        self.urgency_combo.hide()

        # 第二部分：消息内容
        msg_layout = QVBoxLayout()
        msg_layout.setSpacing(6)
        msg_label_row = QHBoxLayout()
        self.message_label = BodyLabel("消息内容：", self)
        msg_label_row.addWidget(self.message_label)
        msg_label_row.addStretch(1)

        self.message_edit = PasteOnlyPlainTextEdit(self, self._on_context_paste)
        self.message_edit.setPlaceholderText("请详细描述您的问题、需求或留言…")
        self.message_edit.setMinimumHeight(140)
        self.message_edit.installEventFilter(self)

        msg_layout.addLayout(msg_label_row)
        msg_layout.addWidget(self.message_edit, 1)

        # 第三部分：图片附件
        attachments_box = QVBoxLayout()
        attachments_box.setSpacing(6)

        attach_toolbar = QHBoxLayout()
        attach_title = BodyLabel("图片附件 (最多3张，支持Ctrl+V粘贴，单张≤10MB):", self)

        self.attach_add_btn = PushButton(FluentIcon.ADD, "添加图片", self)
        self.attach_clear_btn = PushButton(FluentIcon.DELETE, "清空附件", self)

        attach_toolbar.addWidget(attach_title)
        attach_toolbar.addStretch(1)
        attach_toolbar.addWidget(self.attach_add_btn)
        attach_toolbar.addWidget(self.attach_clear_btn)

        attachments_box.addLayout(attach_toolbar)

        self.attach_list_layout = QHBoxLayout()
        self.attach_list_layout.setSpacing(12)
        self.attach_list_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.attach_list_container = QWidget(self)
        self.attach_list_container.setLayout(self.attach_list_layout)

        self.attach_placeholder = BodyLabel("暂无附件", self)
        self.attach_placeholder.setStyleSheet("color: #888; padding: 6px;")

        attachments_box.addWidget(self.attach_list_container)
        attachments_box.addWidget(self.attach_placeholder)

        # 组装表单、消息、附件
        wrapper.addLayout(form_layout)
        wrapper.addLayout(msg_layout, 1) # 给消息框最大的 stretch
        wrapper.addLayout(attachments_box)

        # 第四部分：底部状态与按钮
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 8, 0, 0)

        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        self.status_spinner = IndeterminateProgressRing(self)
        self.status_spinner.setFixedSize(16, 16)
        self.status_spinner.setStrokeWidth(2)
        self.status_icon = IconWidget(FluentIcon.INFO, self)
        self.status_icon.setFixedSize(16, 16)
        self.status_icon.hide()
        self.online_label = BodyLabel("作者当前在线状态：查询中...", self)
        self.online_label.setStyleSheet("color:#BA8303;")
        status_row.addWidget(self.status_spinner)
        status_row.addWidget(self.status_icon)
        status_row.addWidget(self.online_label)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self.cancel_btn: Optional[PushButton] = None
        if show_cancel_button:
            self.cancel_btn = PushButton("取消", self)
            btn_row.addWidget(self.cancel_btn)
        self.send_btn = PrimaryPushButton("发送", self)
        self.send_spinner = IndeterminateProgressRing(self)
        self.send_spinner.setFixedSize(20, 20)
        self.send_spinner.setStrokeWidth(3)
        self.send_spinner.hide()
        btn_row.addWidget(self.send_spinner)
        btn_row.addWidget(self.send_btn)

        bottom_layout.addLayout(status_row)
        bottom_layout.addStretch(1)
        bottom_layout.addLayout(btn_row)
        wrapper.addLayout(bottom_layout)

        self.type_combo.currentIndexChanged.connect(lambda _: self._on_type_changed())
        QTimer.singleShot(0, self._on_type_changed)
        if default_type:
            idx = self.type_combo.findText(default_type)
            if idx >= 0:
                self.type_combo.setCurrentIndex(idx)

        self.send_btn.clicked.connect(self._on_send_clicked)
        self.send_verify_btn.clicked.connect(self._on_send_verify_clicked)
        self.attach_add_btn.clicked.connect(self._on_choose_files)
        self.attach_clear_btn.clicked.connect(self._on_clear_attachments)
        if self.cancel_btn is not None:
            self.cancel_btn.clicked.connect(self.cancelRequested.emit)

    def eventFilter(self, watched, event):
        if watched is self.message_edit and event.type() == QEvent.Type.KeyPress:
            key_event = cast(QKeyEvent, event)
            if key_event.matches(QKeySequence.StandardKey.Paste):
                if self._handle_clipboard_image():
                    return True
        return super().eventFilter(watched, event)

    def _on_context_paste(self, target: QWidget) -> bool:
        """右键菜单触发粘贴时的特殊处理，返回 True 表示已处理。"""
        if target is self.message_edit:
            # 优先尝试粘贴图片到附件
            if self._handle_clipboard_image():
                return True
        return False

    def showEvent(self, event):
        super().showEvent(event)
        if self._manage_polling:
            self.start_status_polling()

    def hideEvent(self, event):
        if self._manage_polling:
            self.stop_status_polling()
        super().hideEvent(event)

    def closeEvent(self, event):
        """关闭事件：停止轮询、关闭所有 InfoBar 并断开信号"""
        self.stop_status_polling()
        self._stop_cooldown()

        # 关闭所有可能存在的 InfoBar，避免其内部线程导致崩溃
        self._close_all_infobars()

        # 断开所有信号连接以避免回调析构警告
        try:
            self._sendFinished.disconnect()
            self._verifyCodeFinished.disconnect()
            self._statusLoaded.disconnect()
        except Exception as exc:
            log_suppressed_exception("closeEvent: disconnect signals", exc, level=logging.WARNING)
        super().closeEvent(event)

    def __del__(self):
        """析构函数：确保线程被清理"""
        try:
            self.stop_status_polling()
        except Exception:
            pass

    def _close_all_infobars(self):
        """关闭所有子 InfoBar 组件，避免线程泄漏"""
        try:
            from qfluentwidgets import InfoBar
            # 遍历所有子组件，找到 InfoBar 并关闭
            for child in self.findChildren(InfoBar):
                try:
                    child.close()
                    child.deleteLater()
                except Exception:
                    pass
        except Exception as exc:
            log_suppressed_exception("_close_all_infobars", exc, level=logging.WARNING)


    def start_status_polling(self):
        if self._polling_started:
            return
        self._polling_started = True
        self.status_spinner.show()
        self.status_icon.hide()
        self.online_label.setText("作者当前在线状态：查询中...")
        self.online_label.setStyleSheet("color:#BA8303;")
        self._start_status_polling()

    def stop_status_polling(self):
        if not self._polling_started:
            return
        self._polling_started = False
        self._stop_status_polling()

    def _render_attachments_ui(self):
        """重新渲染附件列表。"""
        while self.attach_list_layout.count():
            item = self.attach_list_layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not self._attachments.attachments:
            self.attach_list_container.setVisible(False)
            self.attach_placeholder.setVisible(True)
            self.attach_clear_btn.setEnabled(False)
            return

        self.attach_list_container.setVisible(True)
        self.attach_placeholder.setVisible(False)
        self.attach_clear_btn.setEnabled(True)

        for idx, att in enumerate(self._attachments.attachments):
            card_widget = QWidget(self)
            card_layout = QVBoxLayout(card_widget)
            card_layout.setContentsMargins(0, 0, 0, 0)
            card_layout.setSpacing(6)

            thumb_label = QLabel(self)
            thumb_label.setFixedSize(96, 96)
            thumb_label.setScaledContents(True)
            thumb_label.setStyleSheet("border: 1px solid #E0E0E0; border-radius: 4px;")
            if att.pixmap and not att.pixmap.isNull():
                thumb_label.setPixmap(att.pixmap)
            card_layout.addWidget(thumb_label)
            
            size_label = BodyLabel(f"{round(len(att.data) / 1024, 1)} KB", self)
            size_label.setStyleSheet("color: #666; font-size: 11px;")
            size_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(size_label)

            remove_btn = PushButton("移除", self)
            remove_btn.setFixedWidth(96)
            remove_btn.clicked.connect(lambda _=False, i=idx: self._remove_attachment(i))
            card_layout.addWidget(remove_btn)

            self.attach_list_layout.addWidget(card_widget)
        self.attach_list_layout.addStretch(1)

    def _remove_attachment(self, index: int):
        self._attachments.remove_at(index)
        self._render_attachments_ui()

    def _on_clear_attachments(self):
        self._attachments.clear()
        self._render_attachments_ui()

    def _handle_clipboard_image(self) -> bool:
        """处理 Ctrl+V 粘贴图片，返回是否消费了事件。"""
        clipboard = QGuiApplication.clipboard()
        mime = clipboard.mimeData()
        if mime is None or not mime.hasImage():
            return False

        image = clipboard.image()
        ok, msg = self._attachments.add_qimage(image, "clipboard.png")
        if ok:
            InfoBar.success("", "已添加粘贴的图片", parent=self, position=InfoBarPosition.TOP, duration=2000)
            self._render_attachments_ui()
        else:
            InfoBar.error("", msg, parent=self, position=InfoBarPosition.TOP, duration=2500)
        return True

    def _on_choose_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "选择图片",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;所有文件 (*.*)",
        )
        if not paths:
            return
        for path in paths:
            ok, msg = self._attachments.add_file_path(path)
            if not ok:
                InfoBar.error("", msg, parent=self, position=InfoBarPosition.TOP, duration=2500)
                break
        self._render_attachments_ui()

    def _on_type_changed(self):
        current_type = self.type_combo.currentText()

        # 控制金额行显示/隐藏
        if current_type == "卡密获取":
            self.amount_label.show()
            self.amount_edit.show()
            self.quantity_label.show()
            self.quantity_edit.show()
            self.urgency_label.show()
            self.urgency_combo.show()
            self.verify_code_edit.show()
            self.send_verify_btn.show()
            self.email_edit.setPlaceholderText("name@example.com")
            self.message_label.setText("消息内容：")
            self._sync_card_request_message_meta()
        else:
            self.amount_label.hide()
            self.amount_edit.hide()
            self.quantity_label.hide()
            self.quantity_edit.hide()
            self.urgency_label.hide()
            self.urgency_combo.hide()
            self.verify_code_edit.hide()
            self.send_verify_btn.hide()
            self.verify_send_spinner.hide()
            self.verify_code_edit.clear()
            self._verify_code_requested = False
            self._verify_code_requested_email = ""
            self._verify_code_sending = False
            self._stop_cooldown()
            self.email_edit.setPlaceholderText("name@example.com")
            self.message_label.setText("消息内容：")

    def _set_verify_code_sending(self, sending: bool):
        self._verify_code_sending = sending
        self.send_verify_btn.setEnabled(not sending)
        self.send_verify_btn.setText("发送中..." if sending else "发送验证码")
        self.verify_send_spinner.setVisible(sending)

    def _start_cooldown(self):
        """发送成功后启动30秒冷却，期间按钮不可点击并显示倒计时。"""
        self._cooldown_remaining = 30
        self.send_verify_btn.setEnabled(False)
        self.send_verify_btn.setText(f"重新发送({self._cooldown_remaining}s)")
        self._cooldown_timer = QTimer(self)
        self._cooldown_timer.setInterval(1000)
        self._cooldown_timer.timeout.connect(self._on_cooldown_tick)
        self._cooldown_timer.start()

    def _on_cooldown_tick(self):
        self._cooldown_remaining -= 1
        if self._cooldown_remaining <= 0:
            if self._cooldown_timer is not None:
                self._cooldown_timer.stop()
            self._cooldown_timer = None
            self.send_verify_btn.setEnabled(True)
            self.send_verify_btn.setText("发送验证码")
        else:
            self.send_verify_btn.setText(f"重新发送({self._cooldown_remaining}s)")

    def _stop_cooldown(self):
        """停止冷却计时器并重置按钮状态。"""
        if self._cooldown_timer is not None:
            self._cooldown_timer.stop()
            self._cooldown_timer = None
        self._cooldown_remaining = 0
        self.send_verify_btn.setEnabled(True)
        self.send_verify_btn.setText("发送验证码")

    def _on_send_verify_clicked(self):
        if self._verify_code_sending:
            return

        email = (self.email_edit.text() or "").strip()
        if not email:
            InfoBar.warning("", "请先填写邮箱地址", parent=self, position=InfoBarPosition.TOP, duration=2000)
            return
        if not self._validate_email(email):
            InfoBar.warning("", "邮箱格式不正确，请先检查", parent=self, position=InfoBarPosition.TOP, duration=2000)
            return

        if not EMAIL_VERIFY_ENDPOINT:
            InfoBar.error("", "验证码接口未配置", parent=self, position=InfoBarPosition.TOP, duration=2500)
            return

        self._verify_code_requested = False
        self._verify_code_requested_email = ""
        self._set_verify_code_sending(True)

        def _send_verify():
            try:
                resp = http_client.post(
                    EMAIL_VERIFY_ENDPOINT,
                    headers={"Content-Type": "application/json"},
                    json={"email": email},
                    timeout=10,
                )
                data = None
                try:
                    data = resp.json()
                except Exception:
                    data = None

                if resp.status_code == 200 and isinstance(data, dict) and bool(data.get("ok")):
                    self._verifyCodeFinished.emit(True, "", email)
                    return

                if isinstance(data, dict):
                    error_msg = str(data.get("error") or f"发送失败：{resp.status_code}")
                else:
                    error_msg = f"发送失败：{resp.status_code}"
                self._verifyCodeFinished.emit(False, error_msg, email)
            except Exception as exc:
                self._verifyCodeFinished.emit(False, f"发送失败：{exc}", email)

        threading.Thread(target=_send_verify, daemon=True).start()

    def _on_verify_code_finished(self, success: bool, error_msg: str, email: str):
        self._set_verify_code_sending(False)

        if success:
            self._verify_code_requested = True
            self._verify_code_requested_email = email
            InfoBar.success("", "验证码已发送，请查收并输入验证码", parent=self, position=InfoBarPosition.TOP, duration=2200)
            self._start_cooldown()
            return

        self._verify_code_requested = False
        self._verify_code_requested_email = ""
        normalized = (error_msg or "").strip().lower()
        if normalized == "invalid request":
            ui_msg = "邮箱参数无效，请检查邮箱后重试"
        elif normalized == "send mail failed":
            ui_msg = "邮件发送失败，请稍后重试"
        else:
            ui_msg = error_msg or "验证码发送失败，请稍后重试"
        InfoBar.error("", ui_msg, parent=self, position=InfoBarPosition.TOP, duration=2500)

    def _on_amount_changed(self, text: str):
        """金额输入框文本改变时同步卡密获取的元信息到消息框"""
        self._sync_card_request_message_meta()

    def _on_quantity_changed(self, text: str):
        """份数输入框文本改变时同步卡密获取的元信息到消息框"""
        self._sync_card_request_message_meta()

    def _on_urgency_changed(self):
        """紧急程度改变时同步卡密获取的元信息到消息框"""
        self._sync_card_request_message_meta()

    @staticmethod
    def _strip_card_request_meta_prefix_lines(message: str) -> str:
        """移除消息顶部连续的卡密元信息前缀行，避免重复叠加。"""
        lines = message.split('\n')
        idx = 0
        while idx < len(lines):
            line = lines[idx]
            if (
                line.startswith("捐助金额：￥")
                or line.startswith("需求份数：")
                or line.startswith("紧急程度：")
            ):
                idx += 1
                continue
            break
        return '\n'.join(lines[idx:])

    def _sync_card_request_message_meta(self):
        """将卡密获取的金额/份数/紧急程度同步为消息前置行。"""
        if self.type_combo.currentText() != "卡密获取":
            return

        current_msg = self.message_edit.toPlainText()
        body = self._strip_card_request_meta_prefix_lines(current_msg)

        amount_text = (self.amount_edit.text() or "").strip()
        quantity_text = (self.quantity_edit.text() or "").strip()
        urgency_text = (self.urgency_combo.currentText() or "").strip()

        meta_lines = []
        if amount_text:
            meta_lines.append(f"捐助金额：￥{amount_text}")
        if quantity_text:
            meta_lines.append(f"需求份数：{quantity_text}份")
        if (amount_text or quantity_text) and urgency_text:
            meta_lines.append(f"紧急程度：{urgency_text}")

        if meta_lines:
            new_msg = '\n'.join(meta_lines + ([body] if body else []))
        else:
            new_msg = body

        if new_msg != current_msg:
            self.message_edit.setPlainText(new_msg)

    def _on_status_loaded(self, text: str, color: str):
        """信号槽：在主线程更新状态标签"""
        try:
            self.status_spinner.hide()
            self.status_icon.show()
            if color.lower() == "#228b22":
                self.status_icon.setIcon(FluentIcon.ACCEPT)
            elif color.lower() == "#cc0000":
                self.status_icon.setIcon(FluentIcon.REMOVE_FROM)
            else:
                self.status_icon.setIcon(FluentIcon.INFO)
            self.online_label.setText(text)
            self.online_label.setStyleSheet(f"color:{color};")
        except RuntimeError as exc:
            log_suppressed_exception("_on_status_loaded: self.status_spinner.hide()", exc, level=logging.WARNING)

    def _validate_email(self, email: str) -> bool:
        if not email:
            return True
        pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
        return re.match(pattern, email) is not None

    def _on_send_clicked(self):
        email = (self.email_edit.text() or "").strip()
        self._current_has_email = bool(email)

        QTimer.singleShot(10, lambda: self._clear_email_selection())
        QTimer.singleShot(10, lambda: self._focus_send_button())

        mtype = self.type_combo.currentText() or "报错反馈"

        if mtype == "卡密获取":
            try:
                from wjx.utils.system.registry_manager import RegistryManager
                if RegistryManager.read_submit_count() <= 0:
                    InfoBar.warning(
                        "", "你都还没开始用呢，咋就来申请了😡",
                        parent=self, position=InfoBarPosition.TOP, duration=3000,
                    )
                    return
            except Exception as exc:
                log_suppressed_exception("_on_send_clicked: from wjx.utils.system.registry_manager import RegistryManager", exc, level=logging.WARNING)

        if mtype == "卡密获取":
            amount_text = (self.amount_edit.text() or "").strip()
            quantity_text = (self.quantity_edit.text() or "").strip()
            verify_code = (self.verify_code_edit.text() or "").strip()

            if not amount_text:
                InfoBar.warning("", "请输入捐助金额", parent=self, position=InfoBarPosition.TOP, duration=2000)
                return
            if not quantity_text:
                InfoBar.warning("", "请输入大概需求份数", parent=self, position=InfoBarPosition.TOP, duration=2000)
                return
            if not quantity_text.isdigit() or int(quantity_text) <= 0:
                InfoBar.warning("", "需求份数必须为正整数", parent=self, position=InfoBarPosition.TOP, duration=2000)
                return
            if int(quantity_text) > 9999:
                InfoBar.warning("", "需求份数不能超过 9999", parent=self, position=InfoBarPosition.TOP, duration=2000)
                return
            if not self._verify_code_requested:
                InfoBar.warning("", "请先点击发送验证码", parent=self, position=InfoBarPosition.TOP, duration=2000)
                return
            if email != self._verify_code_requested_email:
                InfoBar.warning("", "邮箱已变更，请重新发送验证码", parent=self, position=InfoBarPosition.TOP, duration=2200)
                return
            if verify_code != "114514":
                InfoBar.warning("", "验证码错误，请重试", parent=self, position=InfoBarPosition.TOP, duration=2200)
                return
            self._sync_card_request_message_meta()

        message = (self.message_edit.toPlainText() or "").strip()
        if mtype == "卡密获取":
            if not message or not message.startswith("捐助金额：￥"):
                InfoBar.warning("", "请输入捐助金额", parent=self, position=InfoBarPosition.TOP, duration=2000)
                return
        else:
            if not message:
                InfoBar.warning("", "请输入消息内容", parent=self, position=InfoBarPosition.TOP, duration=2000)
                return

        if mtype == "卡密获取" and not email:
            InfoBar.warning("", "卡密获取必须填写邮箱地址", parent=self, position=InfoBarPosition.TOP, duration=2000)
            return

        if mtype == "卡密获取":
            confirm_email_box = MessageBox(
                "确认邮箱地址",
                f"当前输入的邮箱地址是：{email}\n\n如果邮箱输入错误，将无法收到卡密内容。请确认无误后再发送。",
                self.window() or self,
            )
            confirm_email_box.yesButton.setText("确认发送")
            confirm_email_box.cancelButton.setText("返回检查")
            if not confirm_email_box.exec():
                return

        if mtype != "卡密获取" and not email:
            confirm_box = MessageBox(
                "未填写邮箱",
                "当前未输入邮箱地址，开发者可能无法联系你回复处理进度。是否继续发送？",
                self.window() or self,
            )
            confirm_box.yesButton.setText("继续发送")
            confirm_box.cancelButton.setText("返回填写")
            if not confirm_box.exec():
                return

        if email and not self._validate_email(email):
            InfoBar.warning("", "邮箱格式不正确", parent=self, position=InfoBarPosition.TOP, duration=2000)
            return

        version_str = __VERSION__
        full_message = f"来源：fuck-wjx v{version_str}\n类型：{mtype}\n"
        if email:
            full_message += f"联系邮箱： {email}\n"
        full_message += f"消息：{message}"

        api_url = CONTACT_API_URL
        if not api_url:
            InfoBar.error("", "联系API未配置", parent=self, position=InfoBarPosition.TOP, duration=3000)
            return
        payload = {"message": full_message, "timestamp": datetime.now().isoformat()}
        files_payload = self._attachments.files_payload()

        self.send_btn.setFocus()

        self.send_btn.setEnabled(False)
        self.send_btn.setText("发送中...")
        self.send_spinner.show()

        self._current_message_type = mtype

        def _send():
            try:
                multipart_fields: list[tuple[str, tuple[None, str] | tuple[str, bytes, str]]] = [
                    ("message", (None, payload["message"])),
                    ("timestamp", (None, payload["timestamp"])),
                ]
                if files_payload:
                    multipart_fields.extend(files_payload)
                timeout = 20 if files_payload else 10
                resp = http_client.post(api_url, files=multipart_fields, timeout=timeout)
                if resp.status_code == 200:
                    self._sendFinished.emit(True, "")
                else:
                    self._sendFinished.emit(False, f"发送失败：{resp.status_code}")
            except Exception as exc:
                self._sendFinished.emit(False, f"发送失败：{exc}")

        threading.Thread(target=_send, daemon=True).start()

    def _clear_email_selection(self):
        """清除邮箱选择（由QTimer调用）"""
        try:
            self.email_edit.setSelection(0, 0)
        except (RuntimeError, AttributeError) as exc:
            log_suppressed_exception("_clear_email_selection: self.email_edit.setSelection(0, 0)", exc, level=logging.WARNING)

    def _focus_send_button(self):
        """聚焦发送按钮（由QTimer调用）"""
        try:
            self.send_btn.setFocus()
        except (RuntimeError, AttributeError) as exc:
            log_suppressed_exception("_focus_send_button: self.send_btn.setFocus()", exc, level=logging.WARNING)

    def _on_send_finished(self, success: bool, error_msg: str):
        """发送完成回调（在主线程执行）"""
        self.send_spinner.hide()
        self.send_btn.setEnabled(True)
        self.send_btn.setText("发送")

        if success:
            current_type = getattr(self, "_current_message_type", "")
            if current_type == "卡密获取":
                msg = "发送成功！请留意邮件信息！"
            else:
                msg = "消息已成功发送！"
            if getattr(self, "_current_has_email", False):
                msg += " 开发者将于6小时内回复"
            InfoBar.success("", msg, parent=self, position=InfoBarPosition.TOP, duration=2500)
            if self._auto_clear_on_success:
                self.amount_edit.clear()
                self.quantity_edit.clear()
                self.verify_code_edit.clear()
                self._verify_code_requested = False
                self._verify_code_requested_email = ""
                urgency_default_index = self.urgency_combo.findText("中")
                if urgency_default_index >= 0:
                    self.urgency_combo.setCurrentIndex(urgency_default_index)
                self.message_edit.clear()
                self._attachments.clear()
                self._render_attachments_ui()
            self.sendSucceeded.emit()
        else:
            InfoBar.error("", error_msg, parent=self, position=InfoBarPosition.TOP, duration=3000)

    def _find_controller_host(self) -> Optional[QWidget]:
        widget: Optional[QWidget] = self
        while widget is not None:
            if hasattr(widget, "controller"):
                return widget
            widget = widget.parentWidget()
        win = self.window()
        if isinstance(win, QWidget) and hasattr(win, "controller"):
            return win
        return None

