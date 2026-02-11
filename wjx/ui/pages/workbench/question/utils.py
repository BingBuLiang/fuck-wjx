"""UI 辅助函数"""
from PySide6.QtGui import QColor, QIntValidator
from qfluentwidgets import BodyLabel, LineEdit

from wjx.ui.widgets.no_wheel import NoWheelSlider


def _shorten_text(text: str, limit: int = 80) -> str:
    if not text:
        return ""
    text = str(text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _apply_label_color(label: BodyLabel, light: str, dark: str) -> None:
    """为标签设置浅色/深色主题颜色。"""
    try:
        label.setTextColor(QColor(light), QColor(dark))
    except Exception:
        style = label.styleSheet() or ""
        style = style.strip()
        if style and not style.endswith(";"):
            style = f"{style};"
        label.setStyleSheet(f"{style}color: {light};")


def _bind_slider_input(slider: NoWheelSlider, edit: LineEdit) -> None:
    """绑定滑块与输入框，避免循环触发。"""
    min_value = int(slider.minimum())
    max_value = int(slider.maximum())
    edit.setValidator(QIntValidator(min_value, max_value, edit))

    def sync_edit(value: int) -> None:
        edit.blockSignals(True)
        edit.setText(str(int(value)))
        edit.blockSignals(False)

    def sync_slider_live(text: str) -> None:
        if not text:
            return
        try:
            value = int(text)
        except Exception:
            return
        if value < min_value or value > max_value:
            return
        slider.blockSignals(True)
        slider.setValue(value)
        slider.blockSignals(False)

    def sync_slider_final() -> None:
        text = edit.text().strip()
        if not text:
            return
        try:
            value = int(text)
        except Exception:
            return
        value = max(min_value, min(max_value, value))
        slider.blockSignals(True)
        slider.setValue(value)
        slider.blockSignals(False)
        edit.blockSignals(True)
        edit.setText(str(value))
        edit.blockSignals(False)

    slider.valueChanged.connect(sync_edit)
    edit.textChanged.connect(sync_slider_live)
    edit.editingFinished.connect(sync_slider_final)
