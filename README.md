# DDL2PT

`DDL2PT` 是一个基于 PySide6 的桌面工具，用于把 `ALTER TABLE` 语句快速转换为 `pt-online-schema-change` 命令，减少手工拼接参数的错误。

## 功能特性

- 图形化配置 `pt-online-schema-change` 常用参数
- 支持 `ALTER TABLE schema.table ...` 和 `ALTER TABLE table ...`
- 支持执行模式切换：`--execute` / `--dry-run`
- 支持复制生成命令到剪贴板
- 自动记忆上次输入参数（`QSettings`）
- 支持“参数只读锁定”总开关，防止误改配置
- 内置深色主题与中文参数说明
- 主窗体支持应用图标（`Resources/favicon.ico`）

## 项目结构

```text
DDL2PT/
├─ main.py                  # 程序入口
├─ core/
│  └─ converter.py          # SQL -> pt-osc 命令转换核心
├─ ui/
│  ├─ main_window.py        # 主界面
│  ├─ style.py              # QSS 样式
│  └─ icons/                # 运行时图标资源（按钮/箭头）
├─ Resources/
│  ├─ favicon.ico           # 主窗体图标 / 打包回退图标
│  └─ icon-512.png          # 打包优先图标源（推荐高分辨率）
├─ build_nuitka.py          # Nuitka 打包脚本
└─ pyproject.toml
```

## 环境要求

- Python 3.11+
- Windows（当前项目主要在 Windows 环境使用）
- 已安装 `pt-online-schema-change`（该工具仅负责生成命令，不负责安装 pt-osc）

## 安装依赖

### 使用 uv（推荐）

```bash
uv sync
```

### 使用 pip

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -U pip
pip install pyside6
```

## 启动方式

```bash
python main.py
```

打开界面后：

1. 在顶部输入 `ALTER TABLE` 语句。
2. 配置数据库连接和 `pt-online-schema-change` 参数。
3. 可勾选“参数只读锁定”避免误改。
4. 点击“转换”生成命令。
5. 点击“复制命令”复制到剪贴板。

## 支持的 SQL 格式

支持以下两类输入：

```sql
ALTER TABLE schema_name.table_name ADD COLUMN c1 INT;
ALTER TABLE table_name MODIFY status TINYINT NOT NULL DEFAULT 0;
```

## 默认行为说明

- 默认使用 `--ask-pass`（更安全，不在命令行明文显示密码）
- 默认连接字符集为 `utf8mb4`（推荐，可避免中文/emoji 场景的编码问题）
- 默认启用 `--no-check-replication-filters`
- 默认启用 `--print`
- 默认执行模式为 `--execute`
- 参数锁定状态下，仅当参数内容已改动时，解锁才会弹出二次确认提示

## 打包（Nuitka）

项目提供了适配当前工程的打包脚本：[build_nuitka.py](build_nuitka.py)

### 1. 安装打包依赖

```bash
pip install nuitka ordered-set zstandard
```

如需资源重新编译，还需要：

```bash
pip install pyside6
```

### 2. 执行打包

```bash
python build_nuitka.py
```

### 3. 输出结果

- 输出目录默认在 `build/`
- 默认将 dist 重命名为：`DDL2PT_v<version>`
- 可执行文件名默认：`DDL2PT.exe`
- Windows 图标优先使用 `Resources/icon-512.png`，自动转换为 ICO 后写入 exe
- 若 PNG 处理失败，自动回退 `Resources/favicon.ico`

## 可配置项（打包）

可在 `build_nuitka.py` 的 `BUILD_CONFIG` 中调整：

- `company_name`
- `product_name`
- `file_version`
- `product_version`
- `file_description`
- `copyright`
- `resources_dir`
- `windows_icon_png`
- `windows_icon_ico`
- `executable_name`
- `dist_folder_name`
- `data_dirs`

其中 `product_name / version / description` 会优先从 `pyproject.toml` 自动读取。

## 常见问题

### 1) 复制按钮或下拉箭头图标不显示

请确认打包输出中包含 `ui/icons` 目录（脚本默认已复制）。

### 2) exe 图标发糊

请优先使用高分辨率正方形 PNG（建议至少 `256x256`，推荐 `512x512`），并放在 `Resources/` 中作为 `windows_icon_png` 配置项。

### 3) 提示无法解析 ALTER TABLE 语句

请检查 SQL 是否为标准 `ALTER TABLE ...` 形式，且表名/库名没有非常规语法。

### 4) 命令能生成但执行失败

这是数据库环境问题（权限、主从状态、pt-osc 可执行路径等），请在目标环境单独排查。

## 免责声明

本工具仅用于命令生成与参数辅助，不会直接执行数据库变更。请在生产环境执行前先使用 `--dry-run` 验证。
