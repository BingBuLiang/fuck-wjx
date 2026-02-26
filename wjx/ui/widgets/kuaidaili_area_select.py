"""快代理地区多选组件

提供省份+城市+区县三级选择功能，支持：
- 级联下拉选择（省份 → 城市 → 区县）
- 标签列表展示已选地区
- 支持选择整个省份、整个城市或精确到区县
"""
from typing import List, Optional, Dict, Any

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QFrame,
)
from qfluentwidgets import (
    PushButton,
    ComboBox,
    FlyoutViewBase,
    Flyout,
    FlyoutAnimationType,
    BodyLabel,
    FlowLayout,
    TransparentToolButton,
    FluentIcon,
)

from wjx.data.kuaidaili_area_codes import (
    build_hierarchical_data,
    code_to_name,
    get_province_by_code,
)


def _truncate_name(name: str, max_len: int = 5) -> str:
    """截断过长的名称用于下拉框显示"""
    if len(name) > max_len:
        return name[:max_len] + ".."
    return name


class AreaTag(QFrame):
    """地区标签组件"""
    
    removed = Signal(str)
    
    def __init__(self, code: str, display_text: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.code = code
        self._setup_ui(display_text)
    
    def _setup_ui(self, display_text: str):
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            AreaTag {
                background-color: #e3f2fd;
                border: 1px solid #90caf9;
                border-radius: 4px;
                padding: 2px;
            }
            AreaTag:hover {
                background-color: #bbdefb;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 4, 4)
        layout.setSpacing(4)
        
        label = BodyLabel(display_text)
        label.setStyleSheet("font-size: 12px; background: transparent; border: none;")
        layout.addWidget(label)
        
        close_btn = TransparentToolButton(FluentIcon.CLOSE)
        close_btn.setFixedSize(16, 16)
        close_btn.setIconSize(close_btn.size())
        close_btn.clicked.connect(lambda: self.removed.emit(self.code))
        layout.addWidget(close_btn)


class KuaidailiAreaSelectWidget(QWidget):
    """快代理地区多选组件（三级选择）"""
    
    areasChanged = Signal(list)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._selected_codes: List[str] = []
        self._hierarchical_data = build_hierarchical_data()
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.selectBtn = PushButton("全国随机")
        self.selectBtn.setMinimumWidth(200)
        self.selectBtn.clicked.connect(self._show_flyout)
        layout.addWidget(self.selectBtn)
    
    def _show_flyout(self):
        view = KuaidailiAreaFlyoutView(self._hierarchical_data, self._selected_codes, self)
        view.areasConfirmed.connect(self._on_areas_confirmed)
        
        Flyout.make(
            view,
            self.selectBtn,
            self.window(),
            FlyoutAnimationType.DROP_DOWN,
            isDeleteOnClose=True
        )
    
    def _on_areas_confirmed(self, codes: List[str]):
        self._selected_codes = codes
        self._update_button_text()
        self.areasChanged.emit(codes)
    
    def _update_button_text(self):
        if not self._selected_codes:
            self.selectBtn.setText("全国随机")
        else:
            names = []
            for code in self._selected_codes[:2]:
                name = self._format_area_name(code)
                names.append(name)
            
            if len(self._selected_codes) <= 2:
                self.selectBtn.setText(", ".join(names))
            else:
                self.selectBtn.setText(f"{names[0]}等{len(self._selected_codes)}个地区")
    
    def _format_area_name(self, code: str) -> str:
        """格式化地区名称"""
        if len(code) == 2:
            # 省份
            for p in self._hierarchical_data:
                if p["code"] == code:
                    return f"{p['name']}(全省)"
            return code
        else:
            # 城市或区县
            province_code = code[:2]
            for p in self._hierarchical_data:
                if p["code"] == province_code:
                    # 检查是否是地级市
                    for city in p.get("cities", []):
                        if city["code"] == code:
                            return f"{p['name']}-{city['name']}"
                        # 检查区县
                        for dist in city.get("districts", []):
                            if dist["code"] == code:
                                return f"{city['name']}-{dist['name']}"
                    # 直辖市的区
                    for dist in p.get("districts", []):
                        if dist["code"] == code:
                            return f"{p['name']}-{dist['name']}"
            return code_to_name(code)
    
    def get_selected_areas(self) -> List[str]:
        return self._selected_codes.copy()
    
    def set_selected_areas(self, codes: Optional[List[str]]):
        self._selected_codes = list(codes) if codes else []
        self._update_button_text()


class KuaidailiAreaFlyoutView(FlyoutViewBase):
    """地区选择弹出视图（三级选择）"""
    
    areasConfirmed = Signal(list)
    
    def __init__(
        self,
        hierarchical_data: List[Dict[str, Any]],
        selected_codes: List[str],
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.hierarchical_data = hierarchical_data
        self.selected_codes = list(selected_codes)
        self._province_map = {p["code"]: p for p in hierarchical_data}
        self._setup_ui()
        self._refresh_tags()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 12, 16, 12)
        
        # 标题
        title = BodyLabel("选择地区")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)
        
        hint = BodyLabel("不选择任何地区表示全国随机")
        hint.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(hint)
        
        self._add_separator(layout)
        
        # 三级级联选择
        select_row = QHBoxLayout()
        select_row.setSpacing(6)
        
        # 省份
        self.provinceCombo = ComboBox()
        self.provinceCombo.setMinimumWidth(100)
        self.provinceCombo.addItem("选择省份", userData="")
        for p in self.hierarchical_data:
            self.provinceCombo.addItem(p["name"], userData=p["code"])
        self.provinceCombo.currentIndexChanged.connect(self._on_province_changed)
        select_row.addWidget(self.provinceCombo)
        
        # 城市
        self.cityCombo = ComboBox()
        self.cityCombo.setMinimumWidth(110)
        self.cityCombo.addItem("全省", userData="")
        self.cityCombo.setEnabled(False)
        self.cityCombo.currentIndexChanged.connect(self._on_city_changed)
        select_row.addWidget(self.cityCombo)
        
        # 区县
        self.districtCombo = ComboBox()
        self.districtCombo.setMinimumWidth(110)
        self.districtCombo.addItem("全市", userData="")
        self.districtCombo.setEnabled(False)
        select_row.addWidget(self.districtCombo)
        
        # 添加按钮
        self.addBtn = PushButton("+ 添加")
        self.addBtn.setFixedWidth(65)
        self.addBtn.clicked.connect(self._on_add_clicked)
        self.addBtn.setEnabled(False)
        select_row.addWidget(self.addBtn)
        
        layout.addLayout(select_row)
        
        self._add_separator(layout)
        
        # 已选地区
        tags_label = BodyLabel("已选地区：")
        tags_label.setStyleSheet("font-size: 12px; color: #666;")
        layout.addWidget(tags_label)
        
        self.tagsScroll = QScrollArea()
        self.tagsScroll.setWidgetResizable(True)
        self.tagsScroll.setFrameShape(QFrame.Shape.NoFrame)
        self.tagsScroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tagsScroll.setMinimumHeight(50)
        self.tagsScroll.setMaximumHeight(100)
        
        self.tagsContainer = QWidget()
        self.tagsLayout = FlowLayout(self.tagsContainer, needAni=False)
        self.tagsLayout.setContentsMargins(0, 0, 0, 0)
        self.tagsLayout.setHorizontalSpacing(6)
        self.tagsLayout.setVerticalSpacing(6)
        
        self.tagsScroll.setWidget(self.tagsContainer)
        layout.addWidget(self.tagsScroll)
        
        self.emptyHint = BodyLabel("暂未选择任何地区")
        self.emptyHint.setStyleSheet("color: #999; font-size: 11px;")
        self.emptyHint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.emptyHint)
        
        self._add_separator(layout)
        
        # 底部按钮
        btn_row = QHBoxLayout()
        self.clearBtn = PushButton("清空")
        self.clearBtn.setFixedWidth(60)
        self.clearBtn.clicked.connect(self._clear_all)
        btn_row.addWidget(self.clearBtn)
        btn_row.addStretch()
        self.confirmBtn = PushButton("确定")
        self.confirmBtn.setFixedWidth(60)
        self.confirmBtn.clicked.connect(self._confirm)
        btn_row.addWidget(self.confirmBtn)
        layout.addLayout(btn_row)
        
        self.setMinimumWidth(480)
    
    def _add_separator(self, layout):
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #e0e0e0;")
        sep.setFixedHeight(1)
        layout.addWidget(sep)
    
    def _on_province_changed(self):
        province_code = self.provinceCombo.currentData()
        
        # 阻塞信号，避免 clear() 触发级联更新导致卡顿
        self.cityCombo.blockSignals(True)
        self.districtCombo.blockSignals(True)
        
        # 重置城市和区县
        self.cityCombo.clear()
        self.districtCombo.clear()
        self.districtCombo.addItem("全市", userData="")
        self.districtCombo.setEnabled(False)
        
        if not province_code:
            self.cityCombo.addItem("全省", userData="")
            self.cityCombo.setEnabled(False)
            self.addBtn.setEnabled(False)
            self.cityCombo.blockSignals(False)
            self.districtCombo.blockSignals(False)
            return
        
        province = self._province_map.get(province_code)
        if not province:
            self.cityCombo.blockSignals(False)
            self.districtCombo.blockSignals(False)
            return
        
        self.cityCombo.addItem("全省", userData="")
        
        if province.get("is_municipality"):
            # 直辖市：城市下拉框显示区列表
            for dist in province.get("districts", []):
                display_name = _truncate_name(dist["name"])
                self.cityCombo.addItem(display_name, userData=dist["code"])
            self.cityCombo.setEnabled(True)
            self.districtCombo.setEnabled(False)  # 直辖市无第三级
        else:
            # 普通省份：显示地级市
            for city in province.get("cities", []):
                display_name = _truncate_name(city["name"])
                self.cityCombo.addItem(display_name, userData=city["code"])
            self.cityCombo.setEnabled(True)
        
        self.addBtn.setEnabled(True)
        
        # 恢复信号
        self.cityCombo.blockSignals(False)
        self.districtCombo.blockSignals(False)
    
    def _on_city_changed(self):
        province_code = self.provinceCombo.currentData()
        city_code = self.cityCombo.currentData()
        
        # 阻塞信号，避免 clear() 触发不必要的更新
        self.districtCombo.blockSignals(True)
        
        self.districtCombo.clear()
        self.districtCombo.addItem("全市", userData="")
        
        if not province_code or not city_code:
            self.districtCombo.setEnabled(False)
            self.districtCombo.blockSignals(False)
            return
        
        province = self._province_map.get(province_code)
        if not province or province.get("is_municipality"):
            # 直辖市无第三级
            self.districtCombo.setEnabled(False)
            self.districtCombo.blockSignals(False)
            return
        
        # 查找城市的区县
        for city in province.get("cities", []):
            if city["code"] == city_code:
                districts = city.get("districts", [])
                if districts:
                    for dist in districts:
                        display_name = _truncate_name(dist["name"])
                        self.districtCombo.addItem(display_name, userData=dist["code"])
                    self.districtCombo.setEnabled(True)
                else:
                    self.districtCombo.setEnabled(False)
                self.districtCombo.blockSignals(False)
                return
        
        self.districtCombo.setEnabled(False)
        self.districtCombo.blockSignals(False)
    
    def _on_add_clicked(self):
        province_code = self.provinceCombo.currentData()
        city_code = self.cityCombo.currentData()
        district_code = self.districtCombo.currentData()
        
        if not province_code:
            return
        
        province = self._province_map.get(province_code)
        is_municipality = province.get("is_municipality", False) if province else False
        
        # 确定要添加的编码
        if district_code:
            code_to_add = district_code
        elif city_code:
            code_to_add = city_code
        else:
            code_to_add = province_code
        
        if code_to_add in self.selected_codes:
            return
        
        # 智能去重
        if len(code_to_add) == 2:
            # 添加省份，移除该省下所有城市和区县
            self.selected_codes = [c for c in self.selected_codes if not c.startswith(province_code)]
        elif self._is_city_code(code_to_add):
            # 添加地级市，检查是否已选全省
            if province_code in self.selected_codes:
                return
            # 移除该市下所有区县
            city_prefix = self._get_city_prefix(code_to_add)
            self.selected_codes = [
                c for c in self.selected_codes 
                if not (c.startswith(city_prefix) and c != code_to_add)
            ]
        else:
            # 添加区县，检查是否已选全省或全市
            if province_code in self.selected_codes:
                return
            if not is_municipality:
                city_prefix = self._get_city_prefix(code_to_add)
                for c in self.selected_codes:
                    if self._is_city_code(c) and self._get_city_prefix(c) == city_prefix:
                        return  # 已选全市
        
        self.selected_codes.append(code_to_add)
        self._refresh_tags()
        
        # 重置下拉框
        self.provinceCombo.setCurrentIndex(0)
    
    def _is_city_code(self, code: str) -> bool:
        """判断是否是地级市编码"""
        # 普通地级市：6位，后两位00
        if len(code) == 6 and code.endswith("00"):
            return True
        # 省直辖县级行政区划：7位，后四位0000
        if len(code) == 7 and code.endswith("0000"):
            return True
        return False
    
    def _get_city_prefix(self, code: str) -> str:
        """获取城市前缀用于匹配区县"""
        # 省直辖县级（如 4190000 或 419001）
        if len(code) >= 3 and code[2] == "9":
            return code[:3]
        # 普通编码
        return code[:4]
        
    
    def _remove_area(self, code: str):
        if code in self.selected_codes:
            self.selected_codes.remove(code)
            self._refresh_tags()
    
    def _refresh_tags(self):
        # 清除现有标签
        while self.tagsLayout.count():
            item = self.tagsLayout.takeAt(0)
            if item is not None:
                if hasattr(item, 'deleteLater'):
                    item.deleteLater()
                elif hasattr(item, 'widget') and item.widget():
                    item.widget().deleteLater()
        
        # 添加新标签
        for code in self.selected_codes:
            display_text = self._format_display_text(code)
            tag = AreaTag(code, display_text)
            tag.removed.connect(self._remove_area)
            self.tagsLayout.addWidget(tag)
        
        has_tags = len(self.selected_codes) > 0
        self.emptyHint.setVisible(not has_tags)
        self.tagsScroll.setVisible(has_tags)
    
    def _format_display_text(self, code: str) -> str:
        """格式化标签显示"""
        if len(code) == 2:
            # 省份
            province = self._province_map.get(code)
            return f"{province['name']} 全省" if province else code
        
        province_code = code[:2]
        province = self._province_map.get(province_code)
        if not province:
            return code
        
        province_name = province["name"]
        
        if province.get("is_municipality"):
            # 直辖市的区
            for dist in province.get("districts", []):
                if dist["code"] == code:
                    return f"{province_name} {dist['name']}"
            return code
        
        # 普通省份 - 查找城市和区县
        for city in province.get("cities", []):
            city_code = city["code"]
            city_name = city["name"]
            
            # 检查是否是地级市本身
            if city_code == code:
                return f"{province_name} {city_name} 全市"
            
            # 检查是否是该市下的区县
            # 处理省直辖县级（3位前缀）和普通地级市（4位前缀）
            if len(city_code) == 7:
                # 省直辖县级行政区划（如 4190000）
                city_prefix = city_code[:3]
            else:
                city_prefix = city_code[:4]
            
            code_prefix = code[:3] if (len(code) >= 3 and code[2] == "9") else code[:4]
            
            if city_prefix == code_prefix:
                for dist in city.get("districts", []):
                    if dist["code"] == code:
                        return f"{province_name} {city_name} {dist['name']}"
        
        return code
    
    def _clear_all(self):
        self.selected_codes.clear()
        self._refresh_tags()
    
    def _confirm(self):
        self.areasConfirmed.emit(self.selected_codes.copy())
        self.close()
