"""随机IP额度申请对话框。"""
import logging
import webbrowser
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    FluentIcon,
    IconWidget,
    IndeterminateProgressRing,
    MessageBox,
    PushButton,
    StrongBodyLabel,
    TitleLabel,
)

from wjx.network.proxy import _format_status_payload, get_status
from wjx.ui.pages.more.donate import DonatePage
from wjx.ui.widgets import StatusPollingMixin
from wjx.utils.app.version import ISSUE_FEEDBACK_URL
from wjx.utils.logging.log_utils import log_suppressed_exception


class QuotaRequestDialog(StatusPollingMixin, QDialog):
    """随机IP额度申请说明窗。"""

    _statusLoaded = Signal(str, str)  # text, color

    def __init__(self, parent=None, status_fetcher=None, status_formatter=None, contact_handler=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.setWindowTitle("申请随机IP额度")
        self.resize(720, 340)
        self.setMinimumSize(600, 320)

        self._contact_handler = contact_handler if callable(contact_handler) else None
        self._validation_result: Optional[bool] = None
        self._init_status_polling(status_fetcher, status_formatter)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(24)

        header_layout = QVBoxLayout()
        header_layout.setSpacing(12)

        title_row = QHBoxLayout()
        title_row.setSpacing(12)
        title_icon = IconWidget(FluentIcon.EXPRESSIVE_INPUT_ENTRY, self)
        title_icon.setFixedSize(28, 28)
        title = TitleLabel("申请随机IP额度", self)
        title_row.addWidget(title_icon)
        title_row.addWidget(title)
        title_row.addStretch(1)
        header_layout.addLayout(title_row)

        desc = BodyLabel(
            "维持随机 IP 代理池与软件的持续迭代需要一定成本，因此目前对随机ip启用了额度模式。"
            "如果您觉得本项目对您有帮助，欢迎赞助支持。提交申请后，开发者会为您补充专属额度。",
            self,
        )
        desc.setWordWrap(True)
        header_layout.addWidget(desc)
        layout.addLayout(header_layout)

        steps_card = CardWidget(self)
        steps_layout = QVBoxLayout(steps_card)
        steps_layout.setContentsMargins(24, 20, 24, 20)
        steps_layout.setSpacing(12)

        steps_title = StrongBodyLabel("申请流程", steps_card)
        steps_layout.addWidget(steps_title)
        for step_text in (
            "1. 先点击下方“赞助支持”，请被奶茶喝吧😭🙏",
            "2. 点击“前往申请”填写邮箱地址、刚刚的捐助金额、需要的额度",
            "3. 开发者看到后会人工补充额度，并以邮件形式通知您（通常在8小时内）",
        ):
            steps_layout.addWidget(BodyLabel(step_text, steps_card))
        layout.addWidget(steps_card)

        support_row = QHBoxLayout()
        support_row.setSpacing(12)

        self.contact_btn = PushButton("前往申请", self, FluentIcon.CHAT)
        self.donate_btn = PushButton("赞助支持", self, FluentIcon.HEART)
        support_row.addWidget(self.donate_btn)
        support_row.addWidget(self.contact_btn)
        support_row.addSpacing(16)

        status_row = QHBoxLayout()
        status_row.setSpacing(6)
        self.status_spinner = IndeterminateProgressRing(self)
        self.status_spinner.setFixedSize(16, 16)
        self.status_spinner.setStrokeWidth(2)
        self.status_icon = IconWidget(FluentIcon.INFO, self)
        self.status_icon.setFixedSize(16, 16)
        self.status_icon.hide()
        self.status_label = BodyLabel("获取在线状态中...", self)
        self.status_label.setStyleSheet("color:#BA8303;")
        status_row.addWidget(self.status_spinner)
        status_row.addWidget(self.status_icon)
        status_row.addWidget(self.status_label)

        support_row.addLayout(status_row)
        support_row.addStretch(1)
        layout.addLayout(support_row)
        self.contact_btn.clicked.connect(self._open_contact)
        self.donate_btn.clicked.connect(self._open_donate)
        self._start_status_polling()

    def closeEvent(self, event):
        self._stop_status_polling()
        super().closeEvent(event)

    def reject(self):
        self._stop_status_polling()
        super().reject()

    def accept(self):
        self._stop_status_polling()
        super().accept()

    def _on_status_loaded(self, text: str, color: str):
        try:
            self.status_spinner.hide()
            self.status_icon.show()
            if color.lower() == "#228b22":
                self.status_icon.setIcon(FluentIcon.ACCEPT)
            elif color.lower() == "#cc0000":
                self.status_icon.setIcon(FluentIcon.REMOVE_FROM)
            else:
                self.status_icon.setIcon(FluentIcon.INFO)
            self.status_label.setText(text)
            self.status_label.setStyleSheet(f"color:{color};")
        except RuntimeError as exc:
            log_suppressed_exception("_on_status_loaded: self.status_spinner.hide()", exc, level=logging.WARNING)

    def _open_contact(self):
        try:
            if self._contact_handler is not None:
                if self._contact_handler():
                    self._validation_result = True
                    self.accept()
                return
            from wjx.ui.dialogs import ContactDialog

            dlg = ContactDialog(
                self.window() or self,
                default_type="额度申请",
                status_fetcher=self._status_fetcher or get_status,
                status_formatter=self._status_formatter or _format_status_payload,
            )
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self._validation_result = True
                self.accept()
        except Exception:
            webbrowser.open(ISSUE_FEEDBACK_URL)

    def _open_donate(self):
        confirm_box = MessageBox(
            "确认捐助",
            "请确保已经在本地充分测试并确认功能可正常使用后，再申请随机IP额度。\n\n是否继续打开捐助页？",
            self,
        )
        try:
            confirm_box.yesButton.setText("继续")
            confirm_box.cancelButton.setText("取消")
        except Exception as exc:
            log_suppressed_exception("_open_donate: set button text", exc, level=logging.WARNING)
        if not confirm_box.exec():
            return
        try:
            donate_dialog = QDialog(self)
            donate_dialog.setWindowTitle("支持作者")
            donate_dialog.resize(800, 600)
            layout = QVBoxLayout(donate_dialog)
            layout.setContentsMargins(0, 0, 0, 0)
            donate_page = DonatePage(donate_dialog)
            layout.addWidget(donate_page)
            donate_dialog.exec()
        except Exception as exc:
            log_suppressed_exception("_open_donate: show donate dialog", exc, level=logging.WARNING)
            webbrowser.open("https://github.com/hungryM0/fuck-wjx")

    def get_validation_result(self) -> Optional[bool]:
        return self._validation_result
