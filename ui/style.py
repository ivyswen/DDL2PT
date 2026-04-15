"""
QSS 样式表：现代深色主题
"""

MAIN_STYLE = """
QMainWindow, QDialog {
    background-color: #1e1e2e;
}

QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: "Segoe UI", "Microsoft YaHei UI", sans-serif;
    font-size: 13px;
}

/* ── 分组框 ── */
QGroupBox {
    border: 1px solid #45475a;
    border-radius: 8px;
    margin-top: 14px;
    padding: 12px 10px 10px 10px;
    background-color: #24273a;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    color: #89b4fa;
    font-weight: bold;
    font-size: 13px;
}

/* ── 标签 ── */
QLabel {
    color: #bac2de;
    background: transparent;
}

/* ── 单行输入框 ── */
QLineEdit {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 5px 8px;
    color: #cdd6f4;
    selection-background-color: #89b4fa;
    selection-color: #1e1e2e;
}
QLineEdit:focus {
    border-color: #89b4fa;
}
QLineEdit:hover {
    border-color: #7f849c;
}

/* ── 数字输入框 ── */
QSpinBox {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 4px 8px;
    color: #cdd6f4;
}
QSpinBox:focus {
    border-color: #89b4fa;
}
QSpinBox::up-button, QSpinBox::down-button {
    background-color: #45475a;
    border-radius: 3px;
    width: 18px;
}
QSpinBox::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    border-top-right-radius: 6px;
}
QSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    border-bottom-right-radius: 6px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background-color: #585b70;
}
QSpinBox::up-arrow {
    image: url("ui/icons/chevron-up.svg");
    width: 10px;
    height: 6px;
}
QSpinBox::down-arrow {
    image: url("ui/icons/chevron-down.svg");
    width: 10px;
    height: 6px;
}

/* ── 下拉框 ── */
QComboBox {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 5px 8px;
    color: #cdd6f4;
}
QComboBox:focus {
    border-color: #89b4fa;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox::down-arrow {
    image: url("ui/icons/chevron-down.svg");
    width: 10px;
    height: 6px;
    margin-right: 4px;
}
QComboBox QAbstractItemView {
    background-color: #313244;
    border: 1px solid #45475a;
    selection-background-color: #89b4fa;
    selection-color: #1e1e2e;
    outline: none;
}

/* ── 复选框 ── */
QCheckBox {
    spacing: 8px;
    color: #cdd6f4;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #45475a;
    border-radius: 4px;
    background-color: #313244;
}
QCheckBox::indicator:checked {
    background-color: #89b4fa;
    border-color: #89b4fa;
    image: none;
}
QCheckBox::indicator:hover {
    border-color: #89b4fa;
}

/* ── 单选按钮 ── */
QRadioButton {
    spacing: 8px;
    color: #cdd6f4;
}
QRadioButton::indicator {
    width: 14px;
    height: 14px;
    border: 1px solid #45475a;
    border-radius: 7px;
    background-color: #313244;
}
QRadioButton::indicator:checked {
    background-color: #a6e3a1;
    border-color: #a6e3a1;
}

/* ── 多行文本框 ── */
QTextEdit, QPlainTextEdit {
    background-color: #181825;
    border: 1px solid #45475a;
    border-radius: 8px;
    padding: 8px;
    color: #cdd6f4;
    font-family: "Consolas", "Cascadia Code", monospace;
    font-size: 12px;
    selection-background-color: #89b4fa;
    selection-color: #1e1e2e;
}
QTextEdit:focus, QPlainTextEdit:focus {
    border-color: #89b4fa;
}

/* ── 按钮 ── */
QPushButton {
    background-color: #89b4fa;
    color: #1e1e2e;
    border: none;
    border-radius: 8px;
    padding: 8px 22px;
    font-weight: bold;
    font-size: 13px;
}
QPushButton:hover {
    background-color: #b4befe;
}
QPushButton:focus {
    outline: none;
}
QPushButton:pressed {
    background-color: #74c7ec;
}
QPushButton#btnCopy {
    background-color: #a6e3a1;
    color: #1e1e2e;
}
QPushButton#btnCopy:hover {
    background-color: #94d1a0;
}
QPushButton#btnClear {
    background-color: #45475a;
    color: #cdd6f4;
}
QPushButton#btnClear:hover {
    background-color: #585b70;
}
QPushButton#btnReset {
    background-color: #f38ba8;
    color: #1e1e2e;
}
QPushButton#btnReset:hover {
    background-color: #eba0ac;
}

/* ── 滚动条 ── */
QScrollBar:vertical {
    background-color: #1e1e2e;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background-color: #45475a;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background-color: #585b70;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background-color: #1e1e2e;
    height: 10px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background-color: #45475a;
    border-radius: 5px;
    min-width: 30px;
}

/* ── 分割线 ── */
QFrame[frameShape="4"], QFrame[frameShape="5"] {
    color: #45475a;
}

/* ── 状态栏 ── */
QStatusBar {
    background-color: #181825;
    color: #6c7086;
    font-size: 11px;
}
"""
