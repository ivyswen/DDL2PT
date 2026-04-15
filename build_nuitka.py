#!/usr/bin/env python3
"""
Nuitka构建脚本 - 灵活配置版本

这个脚本使用Nuitka将Python GUI应用程序打包为独立的可执行文件。
所有的产品信息（名称、版本、描述等）都可以通过BUILD_CONFIG字典进行配置。

使用方法:
1. 直接运行: python build_nuitka.py
2. 自定义配置后运行:
   - 修改BUILD_CONFIG字典中的值
   - 或者调用update_build_config()函数

配置项说明:
- company_name: 公司名称
- product_name: 产品名称（也用作可执行文件名）
- file_version: 文件版本号
- product_version: 产品版本号
- file_description: 文件描述
- copyright: 版权信息
- main_script: 主Python脚本文件名
- output_dir: 构建输出目录
- resources_dir: 资源文件目录
- windows_icon_png: Windows 图标 PNG 文件名（优先）
- windows_icon_ico: Windows 图标 ICO 文件名（回退）
- executable_name: 最终可执行文件名
- dist_folder_name: dist文件夹名称格式（支持占位符 {product_name}, {file_version} 等）
- data_dirs: 需要复制的额外目录列表（如果目录存在就复制）

Dist文件夹重命名功能:
默认情况下，dist文件夹会被重命名为 "{product_name}_v{file_version}" 格式
支持使用占位符自定义名称：
- {product_name}: 产品名称
- {product_version}: 产品版本
- {file_version}: 文件版本
- {company_name}: 公司名称
- {executable_name}: 可执行文件名

示例:
  dist_folder_name = "{product_name}_v{product_version}_Release"
  结果: pdf-merger_v0.1.0_Release

作者: @心福口福
日期: 2025
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Tuple

try:
    import tomllib
except ModuleNotFoundError:
    tomllib = None


def _load_project_metadata() -> dict:
    """从 pyproject.toml 读取项目元信息，读取失败时返回默认值。"""
    default = {
        "name": "ddl2pt",
        "version": "0.1.0",
        "description": "DDL2PT - ALTER -> pt-online-schema-change 转换工具",
    }

    pyproject = Path(__file__).resolve().parent / "pyproject.toml"
    if not pyproject.exists() or tomllib is None:
        return default

    try:
        with pyproject.open("rb") as f:
            data = tomllib.load(f)
        project = data.get("project", {})
        return {
            "name": str(project.get("name", default["name"])),
            "version": str(project.get("version", default["version"])),
            "description": str(project.get("description", default["description"])),
        }
    except Exception:
        return default


PROJECT_META = _load_project_metadata()

# 构建配置变量
BUILD_CONFIG = {
    "company_name": "@心福口福",
    "product_name": PROJECT_META["name"],
    "file_version": PROJECT_META["version"],
    "product_version": PROJECT_META["version"],
    "file_description": PROJECT_META["description"],
    "copyright": "Copyright 2026 @心福口福",
    "main_script": "main.py",
    "output_dir": "build",
    "resources_dir": "Resources",
    "windows_icon_png": "icon-192.png",  # 优先使用高分辨率 PNG 生成 exe 图标
    "windows_icon_ico": "favicon.ico",   # PNG 处理失败时回退使用
    "executable_name": "DDL2PT",
    "dist_folder_name": "{executable_name}_v{product_version}",  # 重命名后的文件夹名称格式
    "data_dirs": [  # 需要复制的额外目录列表
        "ui/icons",
    ]
}

_MIN_RECOMMENDED_ICON_SIZE = 256


def _read_png_size(png_path: Path) -> Tuple[int, int]:
    """读取 PNG 图片宽高（无需第三方依赖）。"""
    try:
        with png_path.open("rb") as f:
            # PNG 签名 8 字节 + IHDR chunk:
            # 长度(4) + "IHDR"(4) + width(4) + height(4)
            header = f.read(24)
        if len(header) < 24:
            return 0, 0
        if header[:8] != b"\x89PNG\r\n\x1a\n":
            return 0, 0
        if header[12:16] != b"IHDR":
            return 0, 0
        width = int.from_bytes(header[16:20], "big")
        height = int.from_bytes(header[20:24], "big")
        return width, height
    except Exception:
        return 0, 0


def _warn_png_icon_quality(png_path: Path) -> None:
    """检查 PNG 图标质量并输出建议（不阻断构建）。"""
    width, height = _read_png_size(png_path)
    if width <= 0 or height <= 0:
        print(f"⚠️  无法读取 PNG 尺寸: {png_path}")
        return

    if width != height:
        print(f"⚠️  图标非正方形: {png_path.name} ({width}x{height})，Windows 可能自动裁剪或缩放。")

    min_side = min(width, height)
    if min_side < _MIN_RECOMMENDED_ICON_SIZE:
        print(
            "⚠️  图标分辨率偏低: "
            f"{png_path.name} ({width}x{height})。"
            f"建议至少 {_MIN_RECOMMENDED_ICON_SIZE}x{_MIN_RECOMMENDED_ICON_SIZE}，"
            "否则 exe 图标在高 DPI 下可能发糊。"
        )


def _find_best_png_icon(resources_dir: str) -> Optional[Path]:
    """在资源目录中挑选分辨率最高的 PNG 图标。"""
    root = Path(resources_dir)
    if not root.exists():
        return None

    png_files = [p for p in root.iterdir() if p.is_file() and p.suffix.lower() == ".png"]
    if not png_files:
        return None

    best_file: Optional[Path] = None
    best_score = 0
    for png in png_files:
        w, h = _read_png_size(png)
        score = w * h
        if score > best_score:
            best_score = score
            best_file = png

    return best_file


def _prepare_windows_icon(resources_dir: str, output_dir: str) -> Optional[str]:
    """
    为 Nuitka 准备 Windows 图标：
    1) 优先使用高分辨率 PNG 并转换为 ICO
    2) 失败时回退到已有 ICO
    """
    resources_root = Path(resources_dir)
    preferred_png = resources_root / str(BUILD_CONFIG.get("windows_icon_png", "icon-192.png"))
    fallback_ico = resources_root / str(BUILD_CONFIG.get("windows_icon_ico", "favicon.ico"))

    png_icon = preferred_png if preferred_png.exists() else _find_best_png_icon(resources_dir)

    if png_icon and png_icon.exists():
        try:
            from PySide6.QtGui import QImage

            _warn_png_icon_quality(png_icon)
            generated_icon = Path(output_dir) / "_nuitka_icon.ico"
            generated_icon.parent.mkdir(parents=True, exist_ok=True)

            image = QImage(str(png_icon))
            if image.isNull():
                raise RuntimeError(f"PNG 读取失败: {png_icon}")
            if not image.save(str(generated_icon), "ICO"):
                raise RuntimeError("PNG 转 ICO 失败")

            print(f"使用 PNG 生成图标: {png_icon} -> {generated_icon}")
            return str(generated_icon)
        except Exception as e:
            print(f"⚠️  PNG 图标处理失败，改用 ICO 回退: {e}")

    if fallback_ico.exists():
        print(f"使用回退 ICO 图标: {fallback_ico}")
        return str(fallback_ico)

    print("⚠️  未找到可用图标文件（PNG/ICO），将使用默认图标。")
    return None

def add_data_dir(directory: str):
    """添加数据目录到构建配置

    Args:
        directory: 要添加的目录路径
    """
    if "data_dirs" not in BUILD_CONFIG:
        BUILD_CONFIG["data_dirs"] = []

    if directory not in BUILD_CONFIG["data_dirs"]:
        BUILD_CONFIG["data_dirs"].append(directory)
        print(f"✅ 添加数据目录: {directory}")
    else:
        print(f"⚠️  数据目录已存在: {directory}")

def remove_data_dir(directory: str):
    """从构建配置中移除数据目录

    Args:
        directory: 要移除的目录路径
    """
    if "data_dirs" in BUILD_CONFIG and directory in BUILD_CONFIG["data_dirs"]:
        BUILD_CONFIG["data_dirs"].remove(directory)
        print(f"✅ 移除数据目录: {directory}")
    else:
        print(f"⚠️  数据目录不存在: {directory}")

def list_data_dirs():
    """列出当前配置的数据目录"""
    data_dirs = BUILD_CONFIG.get("data_dirs", [])
    if data_dirs:
        print("📁 当前配置的数据目录:")
        for i, data_dir in enumerate(data_dirs, 1):
            exists = "✅" if os.path.exists(data_dir) else "❌"
            print(f"  {i}. {data_dir} {exists}")
    else:
        print("📁 未配置数据目录")

def update_build_config(**kwargs):
    """更新构建配置

    Args:
        **kwargs: 要更新的配置项，可用的键包括：
            - company_name: 公司名称
            - product_name: 产品名称
            - file_version: 文件版本
            - product_version: 产品版本
            - file_description: 文件描述
            - copyright: 版权信息
            - main_script: 主脚本文件名
            - output_dir: 输出目录
            - resources_dir: 资源目录
            - windows_icon_png: Windows 图标 PNG 文件名（优先）
            - windows_icon_ico: Windows 图标 ICO 文件名（回退）
            - executable_name: 可执行文件名
            - dist_folder_name: dist文件夹名称格式（支持占位符）
            - data_dirs: 需要复制的额外目录列表

    Example:
        update_build_config(
            product_name="my-app",
            file_version="2.0.0",
            file_description="我的应用程序",
            dist_folder_name="MyApp_v{product_version}"
        )
    """
    for key, value in kwargs.items():
        if key in BUILD_CONFIG:
            BUILD_CONFIG[key] = value
            print(f"✅ 更新配置: {key} = {value}")
        else:
            print(f"⚠️  警告: 未知的配置项 '{key}'，已忽略")
            print(f"   可用的配置项: {', '.join(BUILD_CONFIG.keys())}")


def generate_dist_folder_name():
    """根据配置生成dist文件夹名称

    支持的占位符：
    - {product_name}: 产品名称
    - {product_version}: 产品版本
    - {file_version}: 文件版本
    - {company_name}: 公司名称
    - {executable_name}: 可执行文件名

    Returns:
        str: 生成的文件夹名称
    """
    template = BUILD_CONFIG.get("dist_folder_name", "{product_name}_v{file_version}")

    # 可用的占位符映射
    format_map = {
        "product_name": BUILD_CONFIG["product_name"],
        "product_version": BUILD_CONFIG["product_version"],
        "file_version": BUILD_CONFIG["file_version"],
        "company_name": BUILD_CONFIG["company_name"],
        "executable_name": BUILD_CONFIG["executable_name"],
    }

    # 生成文件夹名称
    folder_name = template.format(**format_map)

    # 清理不合法的文件名字符
    import re
    # Windows/Linux/macOS 都不允许的字符：< > : " / \\ | ? *
    folder_name = re.sub(r'[<>:"/\\|?*]', '_', folder_name)

    # 避免空名称
    if not folder_name.strip():
        folder_name = BUILD_CONFIG["executable_name"]

    return folder_name

def build_executable():
    """使用Nuitka构建可执行文件"""
    print("开始使用Nuitka构建可执行文件...")

    main_script = BUILD_CONFIG["main_script"]
    if not os.path.exists(main_script):
        print(f"❌ 主脚本不存在: {main_script}")
        sys.exit(1)

    # 检查资源文件
    resources_dir = BUILD_CONFIG["resources_dir"]
    if not os.path.exists(resources_dir):
        print(f"警告: 资源目录 {resources_dir} 不存在，将跳过图标配置。")
    # 不要在这里退出，允许无资源文件夹的构建

    # 确保资源文件已编译
    print("编译资源文件...")
    try:
        if os.path.exists("resources.qrc"):
            subprocess.run(["pyside6-rcc", "resources.qrc", "-o", "resources_rc.py"], check=True)
            print("资源文件编译成功")
        else:
            print("警告: resources.qrc 不存在，跳过资源编译")
    except Exception as e:
        print(f"资源文件编译失败: {e}")
        print("继续构建，但可能缺少资源文件")

    # 创建输出目录
    output_dir = BUILD_CONFIG["output_dir"]
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 构建Nuitka命令
    cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",                # 创建独立的可执行文件
        "--enable-plugin=pyside6",     # 启用PySide6插件
        "--output-dir=" + output_dir,  # 输出目录
        f"--company-name={BUILD_CONFIG['company_name']}",        # 公司名称
        f"--product-name={BUILD_CONFIG['product_name']}",        # 产品名称
        f"--file-version={BUILD_CONFIG['file_version']}",        # 文件版本
        f"--product-version={BUILD_CONFIG['product_version']}", # 产品版本
        f"--file-description={BUILD_CONFIG['file_description']}", # 文件描述
        f"--copyright={BUILD_CONFIG['copyright']}",             # 版权信息
        BUILD_CONFIG["main_script"]                              # 主脚本
    ]

    # Windows特定选项
    if sys.platform == "win32":
        cmd.extend([
            "--windows-console-mode=disable",  # 禁用控制台窗口
        ])

        # 添加图标：优先 PNG 转 ICO，失败则回退到 favicon.ico
        icon_path = _prepare_windows_icon(resources_dir, output_dir)
        if icon_path:
            cmd.append(f"--windows-icon-from-ico={icon_path}")

    # 资源文件已通过 Qt 资源系统嵌入到 resources_rc.py 中，无需复制 Resources 目录

    # 注意：如果有依赖运行时文件的目录，建议在 data_dirs 中配置并在打包后复制
    # Nuitka 的 --include-data-dir 会跳过 .exe/.dll 文件
    # --include-data-files 不支持递归子目录
    # 因此采用打包后复制的方式更可靠

    # 包含配置文件（如果存在）
    if os.path.exists("config.json"):
        cmd.append("--include-data-file=config.json=config.json")
        print("包含配置文件: config.json")

    # 包含changelog（如果存在）
    if os.path.exists("CHANGELOG.md"):
        cmd.append("--include-data-file=CHANGELOG.md=CHANGELOG.md")
        print("包含CHANGELOG: CHANGELOG.md")

    # 执行构建
    print("执行Nuitka构建命令:")
    print(" ".join(cmd))
    print()

    try:
        subprocess.run(cmd, check=True)
        print("Nuitka构建成功！")
    except subprocess.CalledProcessError as e:
        print(f"Nuitka构建失败: {e}")
        sys.exit(1)

    # 重命名可执行文件
    main_script_name = os.path.splitext(BUILD_CONFIG["main_script"])[0]  # 去掉.py扩展名
    executable_name = BUILD_CONFIG["executable_name"]

    if sys.platform == "win32":
        exe_name = f"{main_script_name}.exe"
        new_exe_name = f"{executable_name}.exe"
    else:
        exe_name = main_script_name
        new_exe_name = executable_name

    exe_path = os.path.join(output_dir, f"{main_script_name}.dist", exe_name)
    new_exe_path = os.path.join(output_dir, f"{main_script_name}.dist", new_exe_name)

    if os.path.exists(exe_path):
        shutil.move(exe_path, new_exe_path)
        print(f"✅ 构建完成！可执行文件: {new_exe_path}")

        # 显示文件大小
        size = os.path.getsize(new_exe_path)
        size_mb = size / (1024 * 1024)
        print(f"📦 文件大小: {size_mb:.2f} MB")

        # === 复制额外的数据目录（包含二进制文件）===
        old_dist_dir = os.path.join(output_dir, f"{main_script_name}.dist")
        data_dirs = BUILD_CONFIG.get("data_dirs", [])
        if data_dirs:
            print("\n复制额外数据目录到输出目录:")
            for data_dir in data_dirs:
                if os.path.exists(data_dir):
                    dest_dir = os.path.join(old_dist_dir, data_dir)
                    try:
                        # 如果目标已存在则先删除
                        if os.path.exists(dest_dir):
                            shutil.rmtree(dest_dir)
                        # 复制整个目录（包括子目录和所有文件类型）
                        shutil.copytree(data_dir, dest_dir)
                        # 统计文件数量
                        file_count = sum([len(files) for _, _, files in os.walk(dest_dir)])
                        print(f"  ✅ 已复制: {data_dir} ({file_count} 个文件)")
                    except Exception as e:
                        print(f"  ❌ 复制失败 {data_dir}: {e}")
                else:
                    print(f"  ⚠️  跳过不存在的目录: {data_dir}")

        # === 重命名dist文件夹 ===
        if os.path.exists(old_dist_dir):
            # 生成新的文件夹名称
            new_dist_name = generate_dist_folder_name()
            new_dist_dir = os.path.join(output_dir, new_dist_name)

            try:
                # 检查目标目录是否已存在，如果存在则先删除
                if os.path.exists(new_dist_dir):
                    shutil.rmtree(new_dist_dir)
                    print(f"⚠️  已删除已存在的目标目录: {new_dist_name}")

                # 重命名dist目录
                shutil.move(old_dist_dir, new_dist_dir)
                print(f"✅ 已重命名dist文件夹: {new_dist_name}")
                print(f"📁 完整路径: {new_dist_dir}")

                # 显示最终的目录结构
                print(f"\n📂 构建输出目录 ({output_dir}):")
                if os.path.exists(output_dir):
                    for item in os.listdir(output_dir):
                        item_path = os.path.join(output_dir, item)
                        if os.path.isdir(item_path):
                            print(f"   📁 {item}/")
                            # 显示可执行文件
                            exe_file = os.path.join(item_path, new_exe_name)
                            if os.path.exists(exe_file):
                                size = os.path.getsize(exe_file)
                                size_mb = size / (1024 * 1024)
                                print(f"      └─ {new_exe_name} ({size_mb:.2f} MB)")
                        else:
                            print(f"   📄 {item}")

            except Exception as e:
                print(f"⚠️  重命名dist文件夹失败: {e}")
                print(f"   原目录仍保留在: {old_dist_dir}")
                sys.exit(1)
        else:
            print(f"❌ 未找到dist目录: {old_dist_dir}")
            sys.exit(1)

    else:
        print(f"❌ 构建完成，但未找到可执行文件: {exe_path}")
        print(f"📁 请检查 {output_dir} 目录内容:")

        # 列出构建目录内容
        if os.path.exists(output_dir):
            for root, _, files in os.walk(output_dir):
                level = root.replace(output_dir, '').count(os.sep)
                indent = ' ' * 2 * level
                print(f"{indent}{os.path.basename(root)}/")
                subindent = ' ' * 2 * (level + 1)
                for file in files:
                    print(f"{subindent}{file}")

        sys.exit(1)

def example_custom_build():
    """示例：自定义构建配置"""
    print("📝 示例：自定义构建配置")

    # 自定义基本信息
    update_build_config(
        company_name="您的公司名称",
        product_name="your-app-name",
        file_version="1.0.0",
        product_version="1.0.0",
        file_description="您的应用程序描述",
        copyright="Copyright 2025 您的公司名称",
        executable_name="your-app",
        # 自定义dist文件夹名称格式
        dist_folder_name="YourApp_v{product_version}_final"
    )

    # 添加自定义数据目录
    add_data_dir("custom_data")
    add_data_dir("user_configs")
    add_data_dir("themes")

    # 显示当前配置
    list_data_dirs()

    # 开始构建
    build_executable()


def show_dist_naming_examples():
    """显示dist文件夹命名格式示例"""
    print("\n" + "=" * 60)
    print("📝 Dist文件夹命名格式示例")
    print("=" * 60)

    examples = [
        ("{product_name}_v{file_version}", "使用产品名和文件版本"),
        ("{executable_name}-{product_version}", "使用可执行名和产品版本"),
        ("{product_name}_Release", "使用产品名和固定后缀"),
        ("{company_name}_{product_name}", "使用公司名和产品名"),
        ("v{file_version}_{executable_name}", "使用版本号开头"),
    ]

    print("\n支持的占位符:")
    print("  - {product_name}: 产品名称")
    print("  - {product_version}: 产品版本")
    print("  - {file_version}: 文件版本")
    print("  - {company_name}: 公司名称")
    print("  - {executable_name}: 可执行文件名")
    print("\n示例格式:")

    for template, desc in examples:
        # 使用当前配置预览效果
        preview = template.format(
            product_name=BUILD_CONFIG["product_name"],
            product_version=BUILD_CONFIG["product_version"],
            file_version=BUILD_CONFIG["file_version"],
            company_name=BUILD_CONFIG["company_name"],
            executable_name=BUILD_CONFIG["executable_name"]
        )
        # 清理不合法的文件名字符
        import re
        preview = re.sub(r'[<>:"/\\|?*]', '_', preview)
        print(f"  • {template:30} → {preview:30} ({desc})")

    print("\n" + "=" * 60)
    print("\n使用说明:")
    print("1. 在 BUILD_CONFIG 中设置 dist_folder_name")
    print("2. 或调用 update_build_config(dist_folder_name='格式')")
    print("3. 格式中的占位符将被替换为实际值")
    print("4. 非法字符会自动替换为下划线(_)")
    print("\n" + "=" * 60 + "\n")

if __name__ == "__main__":
    # 示例：自定义构建配置
    # 取消注释下面的代码来使用自定义配置
    # example_custom_build()
    # return

    # 显示dist文件夹命名格式示例
    show_dist_naming_examples()

    print("🚀 开始构建可执行文件...")
    print(f"📋 当前构建配置:")
    for key, value in BUILD_CONFIG.items():
        print(f"   {key}: {value}")
    print()

    # 显示数据目录配置
    list_data_dirs()
    print()

    # 显示dist文件夹名称
    dist_folder = generate_dist_folder_name()
    print(f"📁 Dist文件夹名称: {dist_folder}")
    print()

    build_executable()
