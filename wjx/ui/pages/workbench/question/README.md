# 题目配置页面模块

> 重构自原 `question.py`（约 1548 行），按职责拆分为模块化结构，便于扩展和维护。

## 目录结构

```
question/
├── __init__.py          # 模块入口，统一导出所有公共接口（向后兼容）
├── constants.py         # 常量定义与标签函数
├── utils.py             # UI 辅助函数
├── page.py              # QuestionPage 主页面
├── wizard_dialog.py     # QuestionWizardDialog 配置向导弹窗
├── add_dialog.py        # QuestionAddDialog 新增题目弹窗
└── README.md            # 本文件
```

## 文件说明

### constants.py

定义全局常量和标签映射函数。

| 符号 | 说明 |
|------|------|
| `TYPE_CHOICES` | 题目类型选项列表，如 `("single", "单选题")` |
| `STRATEGY_CHOICES` | 填写策略选项列表，如 `("random", "完全随机")` |
| `TYPE_LABEL_MAP` | 类型值 → 中文标签的映射字典，含 `multi_text` 扩展 |
| `_get_entry_type_label(entry)` | 根据 `QuestionEntry` 获取中文类型标签 |
| `_get_type_label(q_type)` | 根据类型字符串获取中文标签 |

### utils.py

与业务无关的 UI 工具函数，可被多个对话框/页面复用。

| 函数 | 说明 |
|------|------|
| `_shorten_text(text, limit=80)` | 截断过长文本，末尾加 `…` |
| `_apply_label_color(label, light, dark)` | 为 `BodyLabel` 设置浅色/深色主题颜色 |
| `_bind_slider_input(slider, edit)` | 绑定 `NoWheelSlider` 与 `LineEdit` 双向同步，防止循环触发 |

### page.py — `QuestionPage`

题目配置的主页面，继承 `ScrollArea`，嵌入工作台标签页中。

核心职责：
- 以表格形式展示所有题目条目（题号、类型、选项数、配置详情）
- 提供「新增题目」「删除选中」「恢复默认」「AI 生成答案」按钮
- 通过 `entriesChanged` 信号通知外部条目数变化

关键方法：
- `set_questions(info, entries)` / `set_entries(entries, info)` — 外部设置题目数据
- `get_entries()` — 获取当前所有条目
- `_generate_ai_answers()` — 调用 AI 为填空题批量生成答案

### wizard_dialog.py — `QuestionWizardDialog`

配置向导弹窗，在用户点击「配置向导」时弹出，用于批量调整已有题目的权重/概率/答案。

核心职责：
- 为每道题生成一张配置卡片（滑块/填空答案编辑/矩阵按行配比）
- 支持取消时恢复原始数据（深拷贝快照机制）
- 填空题支持「启用 AI」开关

关键方法：
- `get_results()` — 返回各题的滑块权重结果
- `get_text_results()` — 返回填空题答案
- `get_ai_flags()` — 返回各填空题的 AI 启用状态

内部按题型拆分了构建方法：
- `_build_text_section()` — 填空题
- `_build_matrix_section()` — 矩阵量表题
- `_build_order_section()` — 排序题
- `_build_slider_section()` — 选择题/滑块题

### add_dialog.py — `QuestionAddDialog`

新增题目弹窗，用户可选择题型、策略，实时预览配置效果。

核心职责：
- 上半部分：基础信息表单（题型、策略、选项数、矩阵行数等）
- 下半部分：实时配置预览（随表单变化自动重建）
- 确认后构建 `QuestionEntry` 返回给 `QuestionPage`

关键方法：
- `get_entry()` — 获取用户确认后的新条目
- `_rebuild_preview()` — 根据当前表单状态重建预览区域
- `_build_entry()` — 从表单状态构造 `QuestionEntry` 对象

## 导入方式

所有外部导入路径保持不变，`__init__.py` 统一转发：

```python
# 推荐：从模块入口导入
from wjx.ui.pages.workbench.question import QuestionPage, QuestionWizardDialog

# 导入常量
from wjx.ui.pages.workbench.question import TYPE_CHOICES, STRATEGY_CHOICES

# 导入标签函数
from wjx.ui.pages.workbench.question import _get_entry_type_label
```

## 维护指南

- 新增题型：在 `constants.py` 的 `TYPE_CHOICES` 中添加，然后在 `wizard_dialog.py` 和 `add_dialog.py` 中补充对应的构建分支
- 新增辅助函数：放入 `utils.py`，保持与业务逻辑解耦
- 修改表格展示逻辑：编辑 `page.py` 中的 `_insert_row()` 和 `_build_detail_text()`
- 修改向导弹窗 UI：编辑 `wizard_dialog.py` 中对应的 `_build_*_section()` 方法
- 修改新增弹窗 UI：编辑 `add_dialog.py` 中对应的 `_rebuild_*_preview()` 方法
