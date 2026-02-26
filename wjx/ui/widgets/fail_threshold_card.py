"""失败阈值设置卡片 - 独立组件"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import QHBoxLayout, QWidget
from qfluentwidgets import BodyLabel, FluentIcon, LineEdit, SettingCard


class FailThresholdSettingCard(SettingCard):
    """失败阈值设置卡 - 允许用户自定义连续失败多少次后自动停止"""

    def __init__(self, parent=None):
        super().__init__(
            FluentIcon.CANCEL_MEDIUM,
            "失败阈值",
            "连续失败达到此次数时自动停止运行（0或留空表示使用默认值：目标份数÷4+1）",
            parent
        )

        # 创建输入容器
        self._input_container = QWidget(self)
        input_layout = QHBoxLayout(self._input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(8)

        # 失败次数输入框
        self.lineEdit = LineEdit(self._input_container)
        self.lineEdit.setPlaceholderText("0（自动）")
        self.lineEdit.setFixedWidth(100)
        # 只允许输入数字
        validator = QIntValidator(0, 9999, self.lineEdit)
        self.lineEdit.setValidator(validator)
        self.lineEdit.setText("0")

        # 单位标签
        unit_label = BodyLabel("次", self._input_container)
        unit_label.setStyleSheet("color: #606060;")

        input_layout.addWidget(self.lineEdit)
        input_layout.addWidget(unit_label)

        self.hBoxLayout.addWidget(self._input_container, 0, Qt.AlignmentFlag.AlignRight)
        self.hBoxLayout.addSpacing(16)

    def getValue(self) -> int:
        """获取当前失败阈值（0表示自动）"""
        text = self.lineEdit.text().strip()
        if not text:
            return 0
        try:
            return max(0, int(text))
        except ValueError:
            return 0

    def setValue(self, value: int):
        """设置失败阈值"""
        self.lineEdit.setText(str(max(0, int(value))))

    def setEnabled(self, enabled: bool):
        """启用/禁用控件"""
        super().setEnabled(enabled)
        self.lineEdit.setEnabled(enabled)
