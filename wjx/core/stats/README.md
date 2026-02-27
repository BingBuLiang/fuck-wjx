# 信效度统计模块

## 概述

本模块实现了基于心理测量学的潜变量模型，用于生成符合 Cronbach's Alpha 信度要求的问卷答案。

## 模块结构

```
wjx/core/stats/
├── __init__.py          # 模块导出
├── utils.py             # 数学工具函数
├── psychometric.py      # 潜变量模型核心逻辑
└── README.md            # 本文档
```

## 核心概念

### 潜变量模型

在心理测量学中，潜变量模型假设：
- 每个被试有一个潜在的真实水平 θ (theta)
- 每道题的观测值 = θ + 偏向 + 误差
- 误差大小由目标 Cronbach's Alpha 决定

### Cronbach's Alpha

Cronbach's Alpha 是衡量量表内部一致性的指标：
- α ≥ 0.90：优秀
- 0.80 ≤ α < 0.90：良好
- 0.70 ≤ α < 0.80：可接受
- α < 0.70：不可接受

## 使用方法

### 1. 构建潜变量计划

```python
from wjx.core.stats import build_psychometric_plan

# 定义参与信效度的题目
psycho_items = [
    (0, "scale", 5, "center", None),  # 题目0：5分量表，无偏向
    (1, "scale", 5, "right", None),   # 题目1：5分量表，偏向高分
    (2, "matrix", 5, "center", 0),    # 题目2的第0行：矩阵题
    (2, "matrix", 5, "center", 1),    # 题目2的第1行：矩阵题
]

# 构建计划（目标 Alpha = 0.85）
plan = build_psychometric_plan(psycho_items, target_alpha=0.85)
```

### 2. 在答题时使用

```python
from wjx.core.questions.tendency import get_tendency_index

# 获取答案（会自动使用潜变量模式）
answer = get_tendency_index(
    option_count=5,
    probabilities=None,
    dimension="__reliability__",
    is_reverse=False,
    psycho_plan=plan,        # 传入潜变量计划
    question_index=0,        # 题目索引
    row_index=None,          # 矩阵题行索引（可选）
)
```

### 3. 配置题目

在 `QuestionEntry` 中添加：

```python
entry = QuestionEntry(
    question_type="scale",
    option_count=5,
    # ... 其他配置 ...
    psycho_enabled=True,     # 启用潜变量模式
    psycho_bias="center",    # 偏向：left/center/right
)
```

## 偏向设置

- `"left"`: 偏向低分（选项1方向），bias_shift = -1.0
- `"center"`: 无偏向（默认），bias_shift = 0.0
- `"right"`: 偏向高分（选项N方向），bias_shift = +1.0

## 与简单倾向模式的对比

| 特性 | 简单倾向模式 | 潜变量模式 |
|------|-------------|-----------|
| 实现方式 | 共享基准 ±1 波动 | 统计学模型 |
| Alpha 控制 | 不精确 | 精确控制 |
| 配置复杂度 | 简单 | 中等 |
| 性能 | 极快 | 快（需预计算） |
| 适用场景 | 快速批量生成 | 学术研究 |

## 技术细节

### 误差标准差计算

```python
# 根据目标 Alpha 计算题目间相关系数
rho = alpha / (k - alpha * (k - 1))

# 根据相关系数计算误差标准差
sigma_e = sqrt(1/rho - 1)
```

### Z 分数转换

使用正态分布的分位点将连续值划分为离散类别：

```python
# 5个选项的分界点：-1.28, -0.52, 0.52, 1.28
for j in range(1, option_count):
    threshold = normal_inv(j / option_count)
    if z <= threshold:
        return j - 1
```

## 注意事项

1. **最少题目数**：至少需要2道题启用潜变量模式
2. **题型限制**：仅支持 single, scale, score, dropdown, matrix
3. **反向题**：反向题会在最终答案上翻转，不影响潜变量生成
4. **矩阵题**：每行作为独立的题目项参与计算

## 参考文献

- Cronbach, L. J. (1951). Coefficient alpha and the internal structure of tests.
- Spearman-Brown prophecy formula
- Box-Muller transform for normal distribution sampling
