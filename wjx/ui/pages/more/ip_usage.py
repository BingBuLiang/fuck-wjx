"""IP 使用记录页面"""
from __future__ import annotations

import math
import threading

from PySide6.QtCore import Qt, QPointF, QDate, QDateTime, QTime, Signal, QRectF
from PySide6.QtCharts import QChart, QSplineSeries, QChartView, QValueAxis, QDateTimeAxis
from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSizePolicy,
    QToolTip,
    QGraphicsBlurEffect,
)
from qfluentwidgets import (
    ScrollArea,
    TitleLabel,
    CardWidget,
    StrongBodyLabel,
    CaptionLabel,
    BodyLabel,
    IndeterminateProgressRing,
    InfoBar,
    InfoBarPosition,
    isDarkTheme,
    themeColor,
)

class ChartOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._current_x = -1.0
        self._current_y = -1.0
        self.line_visible = False
        self.date_str = ""
        self.ip_count = 0
        self.plot_area = QRectF()

    def update_point(self, x, y, date_str, ip_count, plot_area):
        self.date_str = date_str
        self.ip_count = ip_count
        self.plot_area = plot_area
        self._current_x = float(x)
        self._current_y = float(y)
        self.line_visible = True
        self.update()

    def hide_line(self):
        self.line_visible = False
        self.update()

    def paintEvent(self, event):
        if not self.line_visible or not self.plot_area.isValid():
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        top_y = self.plot_area.top()
        bottom_y = self.plot_area.bottom()
        
        c = themeColor()
        
        # 竖线
        pen = QPen(c, 1.5, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawLine(QPointF(self._current_x, top_y), QPointF(self._current_x, bottom_y))
        
        # 关键点小圆圈
        painter.setPen(QPen(c, 2.5))
        painter.setBrush(QColor(255, 255, 255) if not isDarkTheme() else QColor(30, 30, 30))
        painter.drawEllipse(QPointF(self._current_x, self._current_y), 5, 5)
        
        # 提示内容
        text1 = f"{self.date_str}"
        text2 = f"提取数量: {self.ip_count}"
        
        font = self.font()
        font.setPointSize(10)
        painter.setFont(font)
        fm = painter.fontMetrics()
        w1 = fm.horizontalAdvance(text1)
        w2 = fm.horizontalAdvance(text2)
        box_w = max(w1, w2) + 32
        box_h = fm.height() * 2 + 20
        
        # 计算 tooltip 位置，防越界
        box_x = self._current_x + 12
        if box_x + box_w > self.width() - 10:
            box_x = self._current_x - box_w - 12
            
        box_y = self._current_y - box_h / 2
        if box_y < top_y:
            box_y = top_y
        if box_y + box_h > bottom_y:
            box_y = bottom_y - box_h
            
        dark = isDarkTheme()
        bg_col = QColor(43, 43, 43, 245) if dark else QColor(255, 255, 255, 245)
        border_col = QColor(255, 255, 255, 20) if dark else QColor(0, 0, 0, 20)
        text_col1 = QColor(200, 200, 200) if dark else QColor(100, 100, 100)
        text_col2 = QColor(255, 255, 255) if dark else QColor(30, 30, 30)
        
        # 阴影
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 40 if not dark else 80))
        painter.drawRoundedRect(QRectF(box_x+2, box_y+3, box_w, box_h), 8, 8)
        
        # 背景卡片
        painter.setPen(QPen(border_col, 1))
        painter.setBrush(bg_col)
        painter.drawRoundedRect(QRectF(box_x, box_y, box_w, box_h), 8, 8)
        
        # 文本
        painter.setPen(text_col1)
        painter.drawText(int(box_x + 16), int(box_y + 10 + fm.ascent()), text1)
        
        painter.setPen(text_col2)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(int(box_x + 16), int(box_y + 10 + fm.height() + 6 + fm.ascent()), text2)

class InteractiveChartView(QChartView):
    def __init__(self, chart, series, point_meta_ref, parent=None):
        super().__init__(chart, parent)
        self.setMouseTracking(True)
        if self.viewport():
            self.viewport().setMouseTracking(True)
        self._series = series
        self._point_meta = point_meta_ref
        self.overlay = ChartOverlay(self)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.overlay.resize(self.size())

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        points = self._series.points()
        if not points:
            self.overlay.hide_line()
            return

        pos = event.position()
        scene_pos = self.mapToScene(pos.toPoint())
        chart_item_pos = self.chart().mapFromScene(scene_pos)
        
        plot_area = self.chart().plotArea()
        # 扩大一点包围盒区域，增加图表边缘处的鼠标捕捉容错范围
        extended_area = plot_area.adjusted(-30, -30, 30, 30)
        
        if not extended_area.contains(chart_item_pos):
            self.overlay.hide_line()
            return
        
        # 抛弃逻辑坐标系计算，直接通过转化到真实屏幕试图 (View) 中的物理像素坐标来计算横向距离
        closest_p = None
        closest_view_pos = None
        min_dist = float('inf')
        
        for p in points:
            # 完整坐标系映射: 逻辑数据 -> QChart 元素 -> QGraphicsScene 场景 -> QChartView 视图组件物理像素
            item_pos = self.chart().mapToPosition(p, self._series)
            scene_pos_point = self.chart().mapToScene(item_pos)
            view_pos = self.mapFromScene(scene_pos_point)
            
            # 使用视口中的纯物理 X 像素坐标做差，获得最直观的跟随
            dist = abs(view_pos.x() - pos.x())
            if dist < min_dist:
                min_dist = dist
                closest_p = p
                closest_view_pos = view_pos
                
        if closest_p:
            # 用于约束实线垂直上下高度的边界矩形，同样映射到当前物理视图
            top_left = self.mapFromScene(self.chart().mapToScene(plot_area.topLeft()))
            bottom_right = self.mapFromScene(self.chart().mapToScene(plot_area.bottomRight()))
            view_plot_area = QRectF(top_left, bottom_right)
            
            ts = int(round(closest_p.x()))
            label, total = self._point_meta.get(ts, (QDateTime.fromMSecsSinceEpoch(ts).toString("yyyy-MM-dd"), int(round(closest_p.y()))))
            
            self.overlay.update_point(closest_view_pos.x(), closest_view_pos.y(), label, total, view_plot_area)
        else:
            self.overlay.hide_line()
            
    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.overlay.hide_line()


class IpUsagePage(ScrollArea):
    _dataLoaded = Signal(list, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dataLoaded.connect(self._on_data_loaded)
        self._load_requested_once = False
        self._last_load_failed = False
        self._loading = False
        self._point_meta: dict[int, tuple[str, int]] = {}
        self.view = QWidget(self)
        self.view.setObjectName("view")
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.enableTransparentBackground()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self.view)
        layout.setContentsMargins(36, 20, 36, 20)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title_row = QHBoxLayout()
        title_row.addWidget(TitleLabel("IP 使用记录", self))
        title_row.addStretch(1)
        layout.addLayout(title_row)

        card = CardWidget(self)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(8)
        card_layout.addWidget(StrongBodyLabel("每日提取 IP 数", self))

        self._series = QSplineSeries()
        self._chart = QChart()
        self._chart.addSeries(self._series)
        self._chart.legend().hide()

        self._axis_x = QDateTimeAxis()
        self._axis_x.setFormat("MM-dd")
        self._axis_x.setTickCount(3)
        self._chart.addAxis(self._axis_x, Qt.AlignmentFlag.AlignBottom)
        self._series.attachAxis(self._axis_x)

        self._axis_y = QValueAxis()
        self._axis_y.setRange(0, 1000)
        self._axis_y.setLabelFormat("%d")
        self._axis_y.setTickType(QValueAxis.TickType.TicksDynamic)
        self._axis_y.setTickAnchor(0)
        self._axis_y.setTickInterval(1000)
        self._axis_y.setMinorTickCount(0)
        self._chart.addAxis(self._axis_y, Qt.AlignmentFlag.AlignLeft)
        self._series.attachAxis(self._axis_y)

        self._series.setPointsVisible(True)

        self._chart_view = InteractiveChartView(self._chart, self._series, self._point_meta)
        self._chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._chart_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._chart_view.setMinimumHeight(400)

        card_layout.addWidget(self._chart_view, 1)

        self._date_label = CaptionLabel("", self)
        self._date_label.setStyleSheet("color: #888;")
        card_layout.addWidget(self._date_label)

        layout.addWidget(card)
        layout.addStretch(1)

        self._page_blur_effect = QGraphicsBlurEffect(self.view)
        self._page_blur_effect.setBlurRadius(8.0)

        self._loading_overlay = QWidget(self.viewport())
        self._loading_overlay.setStyleSheet("background-color: rgba(255, 255, 255, 175);")
        overlay_layout = QVBoxLayout(self._loading_overlay)
        overlay_layout.setContentsMargins(0, 0, 0, 0)
        overlay_layout.setSpacing(8)
        overlay_layout.addStretch(1)
        self._loading_ring = IndeterminateProgressRing(self._loading_overlay)
        self._loading_ring.setFixedSize(44, 44)
        self._loading_ring.setStrokeWidth(3.4)
        overlay_layout.addWidget(self._loading_ring, 0, Qt.AlignmentFlag.AlignHCenter)
        overlay_layout.addWidget(
            BodyLabel("正在加载 IP 使用记录...", self._loading_overlay),
            0,
            Qt.AlignmentFlag.AlignHCenter,
        )
        overlay_layout.addStretch(1)
        self._loading_overlay.hide()
        self._update_overlay_geometry()

    def _load_data(self):
        if self._loading:
            return
        self._set_loading(True)

        def _do():
            try:
                from wjx.utils.io.ip_usage_log import get_usage_history
                records = get_usage_history()
                self._dataLoaded.emit(records, "")
            except Exception as exc:
                self._dataLoaded.emit([], str(exc))

        threading.Thread(target=_do, daemon=True).start()

    def _on_data_loaded(self, records: list, error: str):
        self._set_loading(False)
        self._last_load_failed = bool(error)
        if error:
            InfoBar.error("", f"获取失败：{error}", parent=self.window(), position=InfoBarPosition.TOP, duration=4000)
            self._date_label.setText("加载失败，请切换页面后重试")
            return

        self._series.clear()
        self._point_meta.clear()
        if not records:
            self._date_label.setText("暂无数据")
            self._axis_y.setRange(0, 1000)
            now = QDateTime.currentDateTime()
            self._axis_x.setRange(now.addDays(-1), now.addDays(1))
            return

        points: list[tuple[int, int, str]] = []
        for r in records:
            label = str(r.get("label", "")).strip()
            date = QDate.fromString(label, "yyyy-MM-dd")
            if not date.isValid():
                continue
            total = self._to_int(r.get("total", 0))
            ts = int(QDateTime(date, QTime(0, 0)).toMSecsSinceEpoch())
            points.append((ts, total, label))

        if not points:
            self._date_label.setText("暂无有效日期数据")
            self._axis_y.setRange(0, 1000)
            now = QDateTime.currentDateTime()
            self._axis_x.setRange(now.addDays(-1), now.addDays(1))
            return

        for ts, total, label in points:
            self._series.append(QPointF(float(ts), float(total)))
            self._point_meta[ts] = (label, total)

        x_values = [p[0] for p in points]
        y_values = [p[1] for p in points]
        min_x = min(x_values)
        max_x = max(x_values)
        if min_x == max_x:
            center = QDateTime.fromMSecsSinceEpoch(min_x)
            self._axis_x.setRange(center.addDays(-1), center.addDays(1))
            self._axis_x.setTickCount(3)
        else:
            total_days = max(2, round((max_x - min_x) / 86400000))
            if total_days % 2 != 0:
                total_days += 1  # 补齐到偶数天，保证每 2 天一个刻度精确对齐
            self._axis_x.setRange(
                QDateTime.fromMSecsSinceEpoch(min_x),
                QDateTime.fromMSecsSinceEpoch(min_x + total_days * 86400000),
            )
            self._axis_x.setTickCount(total_days // 2 + 1)

        max_val = max(y_values)
        top = max(1000, int(math.ceil(max_val / 1000.0) * 1000))
        if top == max_val:
            top += 1000
        self._axis_y.setRange(0, top)
        self._axis_y.setTickAnchor(0.0)
        self._axis_y.setTickInterval(1000.0)

        self._date_label.setText(f"{points[0][2]} ~ {points[-1][2]}")

    @staticmethod
    def _to_int(raw: object) -> int:
        try:
            return int(raw)
        except Exception:
            try:
                return int(float(str(raw).strip()))
            except Exception:
                return 0

    def _set_loading(self, loading: bool) -> None:
        self._loading = bool(loading)
        if loading:
            self.view.setGraphicsEffect(self._page_blur_effect)
            self._update_overlay_geometry()
            self._loading_overlay.show()
        else:
            self._loading_overlay.hide()
            self.view.setGraphicsEffect(None)

    def _update_chart_height(self) -> None:
        viewport_height = max(self.viewport().height(), 480)
        target_height = max(400, int(viewport_height * 0.65))
        self._chart_view.setMinimumHeight(target_height)

    def _update_overlay_geometry(self) -> None:
        self._loading_overlay.setGeometry(self.viewport().rect())
        self._loading_overlay.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_chart_height()
        self._update_overlay_geometry()

    def showEvent(self, event):
        super().showEvent(event)
        self._update_chart_height()
        self._update_overlay_geometry()
        if (not self._load_requested_once) or self._last_load_failed:
            self._load_requested_once = True
            self._load_data()
