# 贡献指南

感谢愿意改进本项目！在开始之前，请先阅读 [行为准则](https://github.com/hungryM0/SurveyController/blob/main/CODE_OF_CONDUCT.md)，确保所作的改进能够遵守行为准则。

## 交流渠道
- **Bug/功能建议**：首选 GitHub Issues。
- **快速反馈**：QQ群（见 README）。

## 开发环境与依赖
- 操作系统：仅考虑对 Windows 10/11 的支持
- Python：3.8+
- 安装依赖：`pip install -r requirements.txt`。
- 从源码运行：`python SurveyController.py`。
- 导入检测：`python test_wjx_imports.py`（扫描 `wjx/`、`software/`、`tencent/` 下所有 `.py` 文件的 `import` 是否报错）。
- 死代码检测：`python test_wjx_deadcode.py`（基于 vulture，扫描 `wjx/`、`software/`、`tencent/` 下未引用的死代码）。

## 仓库根目录

```markdown
仓库根目录
├── .github/
│   ├── workflows/
│   │   └── release-to-r2.yml  # CI/CD 自动发布到 R2
│   └── ISSUE_TEMPLATE/        # Issue 模板（报错反馈、新功能请求）
├── SurveyController.py
├── rthook_pyside6.py     # PySide6 打包钩子
├── test_wjx_imports.py   # 导入检测脚本
├── test_wjx_deadcode.py  # 死代码检测脚本
├── software/             # 软件基础设施目录
├── tencent/              # 腾讯问卷 provider 目录
└── wjx/                  # 主代码目录（问卷核心 + 问卷星 provider）
```

## 目录结构（`wjx/`、`software/`、`tencent/`）

```markdown
wjx/
├── main.py                # GUI 程序入口
├── boot.py                # 启动流程相关
├── assets/                # 静态资源（地区行政编码、法律文本等）
│   └── legal/             # 法律文本（service_terms.txt、privacy_statement.txt）
├── core/                  # 平台无关核心（共享业务）
│   ├── task_context.py
│   ├── engine/            # 共享引擎编排（run/answering/submission/runtime_control 等）
│   ├── survey/            # 问卷结构解析能力（parser）
│   ├── questions/         # 题目配置与题型实现
│   │   └── types/
│   ├── captcha/
│   ├── ai/
│   ├── psychometrics/
│   ├── persona/
│   └── services/
├── providers/             # 平台专属实现（provider 分层）
│   ├── common.py
│   ├── registry.py
│   └── wjx/               # 问卷星专属解析/运行时
├── ui/                    # GUI 相关实现（含 theme.json）
├── network/               # 网络能力（代理池、会话策略）
├── utils/                 # 通用工具（配置、持久化、事件总线等）
├── modes/                 # 运行模式控制（timed_mode/duration_control）
├── event_bus.py           # 全局事件总线
└── __pycache__/           # 运行时缓存文件，不应提交到仓库

software/
├── app/
├── integrations/
├── io/
├── logging/
├── network/
├── system/
├── ui/
└── update/

tencent/
├── parser.py              # 腾讯问卷解析
└── runtime.py             # 腾讯问卷运行时
```

## PR 流程（推荐）
1. Fork 仓库本仓库
2. 开发时遵守三层分层：共享业务放 `wjx/core`，问卷平台专属放 `wjx/providers` + `tencent`，软件基础设施放 `software`；`wjx/ui`、`wjx/network`、`wjx/utils` 内新增代码时需保持职责清晰、避免跨层耦合
3. 自测：运行 `python test_wjx_imports.py` 检查 import 和语法错误；至少手动跑一次核心流程（启动、加载问卷、配置、开始运行），确保无报错
4. 提交：保持清晰提交信息，必要时补充中文注释和变更说明
5. PR 描述：写明变更目的、主要改动点、测试方式与结果，关联相关 Issue（如有）

## 代码与文档风格
- 维持现有命名与目录结构，不要把无关功能塞进同一文件
- GUI 优先使用 `QfluentWidgets` 原生组件
- 文档、提示信息优先使用小白也能看懂的中文

## 行为要求
- 严禁将本项目用于伪造学术数据、非法刷问卷或任何污染他人数据的行为。
- 如发现违规，请邮件 `mail@hungrym0.top` 举报。

欢迎提交 PR 改进问卷解析、题型支持、性能优化、界面体验等内容。谢谢！
