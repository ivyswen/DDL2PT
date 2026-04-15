"""
程序入口：初始化 PySide6 应用并启动主窗口
"""
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

import resources_rc
from ui.main_window import MainWindow
from ui.style import MAIN_STYLE


def main() -> None:
    # 创建 QApplication 实例
    app = QApplication(sys.argv)
    app.setApplicationName("DDL2PT")
    app.setOrganizationName("DDL2PT")
    app.setWindowIcon(QIcon(":/Resources/favicon.ico"))

    # 应用全局 QSS 深色主题
    app.setStyleSheet(MAIN_STYLE)

    # 实例化并显示主窗口
    window = MainWindow()
    window.setWindowIcon(QIcon(":/Resources/favicon.ico"))
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
