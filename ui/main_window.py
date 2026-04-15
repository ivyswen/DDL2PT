"""
主窗口模块：PySide6 重构版 alter2pt UI
支持所有 pt-online-schema-change 参数配置，并自动记忆 UI 状态
"""
from __future__ import annotations
from pathlib import Path

from PySide6.QtCore import QSettings, QSize, QTimer, Qt
from PySide6.QtGui import QClipboard, QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.converter import PTConfig, PTConverter

# QSettings 存储标识
_ORG  = "DDL2PT"
_APP  = "alter2pt"


def _hint_label(text: str) -> QLabel:
    """生成灰色中文提示标签，显示在输入控件右侧"""
    lbl = QLabel(text)
    lbl.setStyleSheet("color: #6c7086; font-size: 11px; padding-left: 6px;")
    lbl.setWordWrap(False)
    return lbl


def _with_hint(widget: QWidget, hint: str) -> QWidget:
    """将输入控件与注释文字垂直组合：控件在上，灰色注释在下独占一行"""
    container = QWidget()
    col = QVBoxLayout(container)
    col.setContentsMargins(0, 0, 0, 2)
    col.setSpacing(2)
    # 将控件本身单独放一行（保持其原始宽度）
    widget_row = QHBoxLayout()
    widget_row.setContentsMargins(0, 0, 0, 0)
    # 统一提升输入控件可用宽度，避免在表单布局中显得过窄
    if isinstance(widget, QLineEdit):
        widget.setMinimumWidth(320)
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    elif isinstance(widget, QComboBox):
        widget.setMinimumWidth(320)
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    elif isinstance(widget, QSpinBox):
        widget.setMinimumWidth(180)
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    widget_row.addWidget(widget, stretch=1)
    col.addLayout(widget_row)
    # 注释文字独占下一行，可充分利用列宽
    lbl = _hint_label(hint)
    lbl.setWordWrap(True)
    col.addWidget(lbl)
    return container


class MainWindow(QMainWindow):
    """主窗口：包含参数面板和转换输出区域"""

    def __init__(self) -> None:
        super().__init__()
        # QSettings 用于持久化 UI 参数
        self._settings = QSettings(_ORG, _APP)

        self.setWindowTitle("ALTER → pt-online-schema-change 转换工具")
        self.setMinimumSize(860, 700)
        self.resize(980, 780)

        # 构建 UI
        self._build_ui()
        # 从持久化读取上次参数
        self._load_settings()

    # ─────────────────────────────────────────────────────────────────
    # UI 构建
    # ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        """构建整体布局"""
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(16, 16, 16, 12)
        root_layout.setSpacing(12)

        # ── 顶部：SQL 输入区
        root_layout.addWidget(self._build_input_group())

        # ── 中部：参数面板（可滚动）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        params_widget = QWidget()
        params_layout = QGridLayout(params_widget)
        params_layout.setContentsMargins(0, 0, 0, 0)
        params_layout.setSpacing(10)

        # 使用网格布局分栏排列：左列分布 db_group 和 flags_group，右侧分布 pt_group，底部跨两列为 extra_group
        params_layout.addWidget(self._build_db_group(), 0, 0)
        params_layout.addWidget(self._build_pt_group(), 0, 1, 2, 1)
        params_layout.addWidget(self._build_flags_group(), 1, 0)
        params_layout.addWidget(self._build_extra_group(), 2, 0, 1, 2)
        
        # 将两列宽度均匀分布
        params_layout.setColumnStretch(0, 1)
        params_layout.setColumnStretch(1, 1)
        
        # 让底部占据可能的剩余空间，避免组件被拉伸导致空隙过大
        params_layout.setRowStretch(3, 1)

        scroll.setWidget(params_widget)
        scroll.setMinimumHeight(280)
        root_layout.addWidget(scroll, stretch=1)

        # ── 底部：操作按钮 + 输出区
        root_layout.addWidget(self._build_action_bar())
        root_layout.addWidget(self._build_output_group())

        # ── 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")

    # ── SQL 输入 ─────────────────────────────────────────────────────

    def _build_input_group(self) -> QGroupBox:
        grp = QGroupBox("ALTER TABLE SQL 语句")
        layout = QVBoxLayout(grp)
        layout.setSpacing(6)

        hint = QLabel("支持格式：ALTER TABLE schema.table ... 或 ALTER TABLE table ...")
        hint.setObjectName("inputHint")
        hint.setStyleSheet("color: #6c7086; font-size: 11px;")
        layout.addWidget(hint)

        self.input_sql = QPlainTextEdit()
        self.input_sql.setPlaceholderText(
            "例：alter table tmsp.order_track modify `status` tinyint NOT NULL DEFAULT 0 COMMENT '状态';"
        )
        self.input_sql.setFixedHeight(72)
        self.input_sql.setFont(QFont("Consolas", 12))
        layout.addWidget(self.input_sql)
        return grp

    # ── 数据库连接参数 ────────────────────────────────────────────────

    def _build_db_group(self) -> QGroupBox:
        grp = QGroupBox("数据库连接参数")
        form = QFormLayout(grp)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(8)

        # Host
        self.db_host = QLineEdit("127.0.0.1")
        self.db_host.setPlaceholderText("主机地址")
        form.addRow("Host：", _with_hint(self.db_host, "目标 MySQL 服务器 IP 或主机名"))

        # Port
        self.db_port = QSpinBox()
        self.db_port.setRange(1, 65535)
        self.db_port.setValue(3306)
        form.addRow("Port：", _with_hint(self.db_port, "MySQL 端口，默认 3306"))

        # User
        self.db_user = QLineEdit("root")
        self.db_user.setPlaceholderText("数据库用户名")
        form.addRow("User：", _with_hint(self.db_user, "连接数据库使用的账号，需有 ALTER/CREATE/DROP 权限"))

        # 认证方式
        auth_widget = QWidget()
        auth_layout = QHBoxLayout(auth_widget)
        auth_layout.setContentsMargins(0, 0, 0, 0)
        auth_layout.setSpacing(12)

        self.radio_askpass = QRadioButton("交互输入密码 (--ask-pass)")
        self.radio_askpass.setChecked(True)
        self.radio_askpass.setToolTip("运行时在终端提示输入密码，密码不会出现在命令行中（更安全）")
        self.radio_password = QRadioButton("使用密码：")
        self.radio_password.setToolTip("将密码明文写入命令行（不推荐，仅用于自动化脚本）")
        auth_layout.addWidget(self.radio_askpass)
        auth_layout.addWidget(self.radio_password)
        auth_layout.addWidget(_hint_label("推荐使用 --ask-pass 避免密码明文暴露"))
        auth_layout.addStretch()
        form.addRow("认证方式：", auth_widget)

        self.db_password = QLineEdit()
        self.db_password.setPlaceholderText("仅当选择「使用密码」时有效")
        self.db_password.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("密码：", _with_hint(self.db_password, "选择「使用密码」时此处填写，留空则不传 --password"))

        # Charset
        self.db_charset = QComboBox()
        self.db_charset.addItems(["utf8mb4", "utf8", "latin1", "gbk", "utf16"])
        self.db_charset.setEditable(True)
        form.addRow("Charset：", _with_hint(self.db_charset, "连接字符集，含中文字段建议使用 utf8mb4"))

        return grp

    # ── pt-osc 运行参数 ───────────────────────────────────────────────

    def _build_pt_group(self) -> QGroupBox:
        grp = QGroupBox("pt-online-schema-change 运行参数")
        form = QFormLayout(grp)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(8)

        # max-lag
        self.pt_max_lag = QSpinBox()
        self.pt_max_lag.setRange(1, 3600)
        self.pt_max_lag.setValue(10)
        self.pt_max_lag.setSuffix(" 秒")
        form.addRow("--max-lag：", _with_hint(
            self.pt_max_lag,
            "从库复制延迟阈值，超过此值则暂停变更，等待从库追上后继续"
        ))

        # check-interval
        self.pt_check_interval = QSpinBox()
        self.pt_check_interval.setRange(1, 600)
        self.pt_check_interval.setValue(5)
        self.pt_check_interval.setSuffix(" 秒")
        form.addRow("--check-interval：", _with_hint(
            self.pt_check_interval,
            "每隔多少秒检查一次从库延迟和系统负载"
        ))

        # check-slave-lag
        self.pt_slave_lag = QLineEdit()
        self.pt_slave_lag.setPlaceholderText("h=10.11.12.29,u=root,p=xxx  （留空则不添加此参数）")
        form.addRow("--check-slave-lag：", _with_hint(
            self.pt_slave_lag,
            "指定要监控延迟的从库 DSN，格式：h=IP,u=用户,p=密码；留空则自动发现所有从库"
        ))

        # recursion-method
        self.pt_recursion = QComboBox()
        self.pt_recursion.addItems(["processlist", "hosts", "none", "dsn=..."])
        self.pt_recursion.setEditable(True)
        form.addRow("--recursion-method：", _with_hint(
            self.pt_recursion,
            "发现从库的方法：processlist=查进程列表，hosts=SHOW SLAVE HOSTS，none=不检查从库"
        ))

        # max-load
        self.pt_max_load = QLineEdit("Threads_running=25")
        self.pt_max_load.setPlaceholderText("例：Threads_running=25")
        form.addRow("--max-load：", _with_hint(
            self.pt_max_load,
            "负载上限，超过此值则暂停；格式：状态变量=阈值，可用逗号分隔多个"
        ))

        # critical-load
        self.pt_critical_load = QLineEdit("Threads_running=50")
        self.pt_critical_load.setPlaceholderText("例：Threads_running=50")
        form.addRow("--critical-load：", _with_hint(
            self.pt_critical_load,
            "紧急负载上限，超过此值则立即终止 pt-osc 并退出"
        ))

        # chunk-size
        self.pt_chunk_size = QSpinBox()
        self.pt_chunk_size.setRange(1, 1000000)
        self.pt_chunk_size.setValue(1000)
        self.pt_chunk_size.setSingleStep(500)
        form.addRow("--chunk-size：", _with_hint(
            self.pt_chunk_size,
            "每批次拷贝的行数，值越大单批耗时越长，建议 1000~5000"
        ))

        # chunk-index-columns
        self.pt_chunk_index = QLineEdit()
        self.pt_chunk_index.setPlaceholderText("可选：指定分块时使用的索引列名")
        form.addRow("--chunk-index-columns：", _with_hint(
            self.pt_chunk_index,
            "强制使用指定列做分块，默认由 pt-osc 自动选择最优索引"
        ))

        # new-table-name
        self.pt_new_table_name = QLineEdit()
        self.pt_new_table_name.setPlaceholderText("可选：留空则自动生成（如 _table_new）")
        form.addRow("--new-table-name：", _with_hint(
            self.pt_new_table_name,
            "变更过程中创建的临时新表的名称，留空由 pt-osc 自动命名"
        ))

        return grp

    # ── 功能标志位 ────────────────────────────────────────────────────

    def _build_flags_group(self) -> QGroupBox:
        grp = QGroupBox("功能开关 (Flags)")
        layout = QVBoxLayout(grp)
        layout.setSpacing(8)

        # 第一行复选框
        row1 = QHBoxLayout()
        self.chk_no_replication_filters = QCheckBox("--no-check-replication-filters")
        self.chk_no_replication_filters.setChecked(True)
        self.chk_no_replication_filters.setToolTip("跳过复制过滤器检查，环境有 binlog-do-db/ignore-db 时必须勾选")
        self.chk_no_check_alter = QCheckBox("--no-check-alter")
        self.chk_no_check_alter.setToolTip("跳过对 ALTER 语句的预检查（默认会验证 ALTER 语法合法性）")
        self.chk_print = QCheckBox("--print")
        self.chk_print.setChecked(True)
        self.chk_print.setToolTip("打印执行过程中的 SQL 语句，方便调试和审计")
        row1.addWidget(self.chk_no_replication_filters)
        row1.addWidget(self.chk_no_check_alter)
        row1.addWidget(self.chk_print)
        row1.addStretch()
        layout.addLayout(row1)

        # 第二行复选框
        row2 = QHBoxLayout()
        self.chk_drop_old_table = QCheckBox("--drop-old-table  （完成后删除旧表）")
        self.chk_drop_old_table.setChecked(True)
        self.chk_drop_old_table.setToolTip("变更完成后自动删除重命名的旧表（_old 后缀），取消勾选可在出错时快速回滚")
        self.chk_drop_triggers = QCheckBox("--drop-triggers  （完成后删除触发器）")
        self.chk_drop_triggers.setChecked(True)
        self.chk_drop_triggers.setToolTip("变更完成后删除 pt-osc 创建的临时触发器，正常情况下保持勾选")
        row2.addWidget(self.chk_drop_old_table)
        row2.addWidget(self.chk_drop_triggers)
        row2.addStretch()
        layout.addLayout(row2)

        # 执行模式单选
        exec_row = QHBoxLayout()
        exec_label = QLabel("执行模式：")
        self.radio_execute = QRadioButton("--execute  （真实执行，实际修改表结构）")
        self.radio_execute.setChecked(True)
        self.radio_execute.setToolTip("真正执行 ALTER，会对生产表产生影响，请确认参数无误后再选此项")
        self.radio_dryrun = QRadioButton("--dry-run  （试运行，仅验证不变更）")
        self.radio_dryrun.setToolTip("只创建新表和触发器做验证，不实际拷贝数据，用于测试参数是否正确")
        exec_row.addWidget(exec_label)
        exec_row.addWidget(self.radio_execute)
        exec_row.addWidget(self.radio_dryrun)
        exec_row.addStretch()
        layout.addLayout(exec_row)

        return grp

    # ── 自定义附加参数 ────────────────────────────────────────────────

    def _build_extra_group(self) -> QGroupBox:
        grp = QGroupBox("自定义附加参数（追加到命令末尾）")
        layout = QVBoxLayout(grp)
        self.extra_args = QLineEdit()
        self.extra_args.setPlaceholderText("例：--slave-user=repl --slave-password=xxx")
        layout.addWidget(self.extra_args)
        return grp

    # ── 操作按钮栏 ────────────────────────────────────────────────────

    def _build_action_bar(self) -> QWidget:
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.btn_convert = QPushButton("⇒  转换")
        self.btn_convert.setObjectName("btnConvert")
        self.btn_convert.setMinimumHeight(38)
        self.btn_convert.clicked.connect(self._on_convert)

        self._copy_button_default_text = "复制命令"
        self.btn_copy = QPushButton(self._copy_button_default_text)
        self.btn_copy.setObjectName("btnCopy")
        self.btn_copy.setMinimumHeight(38)
        copy_icon_path = Path(__file__).resolve().parent / "icons" / "copy.svg"
        self.btn_copy.setIcon(QIcon(str(copy_icon_path)))
        self.btn_copy.setIconSize(QSize(16, 16))
        self.btn_copy.clicked.connect(self._on_copy)

        self.btn_clear = QPushButton("✕  清空")
        self.btn_clear.setObjectName("btnClear")
        self.btn_clear.setMinimumHeight(38)
        self.btn_clear.clicked.connect(self._on_clear)

        self.btn_reset = QPushButton("↺  重置参数")
        self.btn_reset.setObjectName("btnReset")
        self.btn_reset.setMinimumHeight(38)
        self.btn_reset.clicked.connect(self._on_reset)

        # 去除按钮焦点框，避免点击后出现矩形高亮
        for btn in (self.btn_convert, self.btn_copy, self.btn_clear, self.btn_reset):
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        layout.addWidget(self.btn_convert, stretch=2)
        layout.addWidget(self.btn_copy, stretch=1)
        layout.addWidget(self.btn_clear, stretch=1)
        layout.addWidget(self.btn_reset, stretch=1)
        return bar

    # ── 输出区 ────────────────────────────────────────────────────────

    def _build_output_group(self) -> QGroupBox:
        grp = QGroupBox("生成的 pt-online-schema-change 命令")
        layout = QVBoxLayout(grp)
        self.output_text = QPlainTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Consolas", 12))
        self.output_text.setFixedHeight(160)
        layout.addWidget(self.output_text)
        return grp

    # ─────────────────────────────────────────────────────────────────
    # 事件处理
    # ─────────────────────────────────────────────────────────────────

    def _on_convert(self) -> None:
        """执行转换"""
        sql = self.input_sql.toPlainText().strip()
        if not sql:
            self.status_bar.showMessage("请先输入 ALTER TABLE 语句")
            return

        try:
            cfg = self._collect_config()
            converter = PTConverter(cfg)
            cmd = converter.build_command(sql)
            self.output_text.setPlainText(cmd)
            # 转换成功后保存参数
            self._save_settings()
            self.status_bar.showMessage("转换成功 ✓  参数已自动保存")
        except ValueError as e:
            self.output_text.setPlainText(f"[错误] {e}")
            self.status_bar.showMessage(f"转换失败：{e}")
        except Exception as e:
            self.output_text.setPlainText(f"[未知错误] {e}")
            self.status_bar.showMessage(f"错误：{e}")

    def _on_copy(self) -> None:
        """复制输出到剪贴板"""
        text = self.output_text.toPlainText()
        if not text:
            self.status_bar.showMessage("输出为空，无可复制内容")
            return
        QApplication.clipboard().setText(text)
        self.status_bar.showMessage("命令已复制到剪贴板 ✓")
        self.btn_copy.setText("已复制")
        self.btn_copy.setEnabled(False)
        QTimer.singleShot(1500, self._reset_copy_button_state)

    def _reset_copy_button_state(self) -> None:
        """复制反馈结束后恢复按钮状态"""
        self.btn_copy.setText(self._copy_button_default_text)
        self.btn_copy.setEnabled(True)

    def _on_clear(self) -> None:
        """清空输入和输出"""
        self.input_sql.clear()
        self.output_text.clear()
        self.status_bar.showMessage("已清空")

    def _on_reset(self) -> None:
        """重置所有参数为默认值"""
        reply = QMessageBox.question(
            self,
            "确认重置",
            "是否将所有参数恢复为默认值？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._apply_defaults()
            self.status_bar.showMessage("参数已重置为默认值")

    # ─────────────────────────────────────────────────────────────────
    # 参数收集与默认值
    # ─────────────────────────────────────────────────────────────────

    def _collect_config(self) -> PTConfig:
        """从 UI 控件收集参数，构建 PTConfig"""
        return PTConfig(
            # 连接
            user=self.db_user.text().strip(),
            host=self.db_host.text().strip(),
            port=self.db_port.value(),
            charset=self.db_charset.currentText().strip(),
            ask_pass=self.radio_askpass.isChecked(),
            password=self.db_password.text(),
            # 延迟
            max_lag=self.pt_max_lag.value(),
            check_interval=self.pt_check_interval.value(),
            check_slave_lag=self.pt_slave_lag.text().strip(),
            recursion_method=self.pt_recursion.currentText().strip(),
            # 负载
            max_load=self.pt_max_load.text().strip(),
            critical_load=self.pt_critical_load.text().strip(),
            # 分块
            chunk_size=self.pt_chunk_size.value(),
            chunk_index_columns=self.pt_chunk_index.text().strip(),
            new_table_name=self.pt_new_table_name.text().strip(),
            # 开关
            no_check_replication_filters=self.chk_no_replication_filters.isChecked(),
            no_check_alter=self.chk_no_check_alter.isChecked(),
            drop_old_table=self.chk_drop_old_table.isChecked(),
            drop_triggers=self.chk_drop_triggers.isChecked(),
            print_cmd=self.chk_print.isChecked(),
            execute=self.radio_execute.isChecked(),
            # 附加
            extra_args=self.extra_args.text().strip(),
        )

    def _apply_defaults(self) -> None:
        """将所有 UI 控件恢复为默认值"""
        defaults = PTConfig()
        self.db_host.setText(defaults.host)
        self.db_port.setValue(defaults.port)
        self.db_user.setText(defaults.user)
        self.db_password.clear()
        self.radio_askpass.setChecked(defaults.ask_pass)
        self.radio_password.setChecked(not defaults.ask_pass)

        idx = self.db_charset.findText(defaults.charset)
        self.db_charset.setCurrentIndex(idx if idx >= 0 else 0)

        self.pt_max_lag.setValue(defaults.max_lag)
        self.pt_check_interval.setValue(defaults.check_interval)
        self.pt_slave_lag.setText(defaults.check_slave_lag)

        idx = self.pt_recursion.findText(defaults.recursion_method)
        self.pt_recursion.setCurrentIndex(idx if idx >= 0 else 0)

        self.pt_max_load.setText(defaults.max_load)
        self.pt_critical_load.setText(defaults.critical_load)
        self.pt_chunk_size.setValue(defaults.chunk_size)
        self.pt_chunk_index.setText(defaults.chunk_index_columns)
        self.pt_new_table_name.setText(defaults.new_table_name)

        self.chk_no_replication_filters.setChecked(defaults.no_check_replication_filters)
        self.chk_no_check_alter.setChecked(defaults.no_check_alter)
        self.chk_drop_old_table.setChecked(defaults.drop_old_table)
        self.chk_drop_triggers.setChecked(defaults.drop_triggers)
        self.chk_print.setChecked(defaults.print_cmd)

        self.radio_execute.setChecked(defaults.execute)
        self.radio_dryrun.setChecked(not defaults.execute)
        self.extra_args.setText(defaults.extra_args)

    # ─────────────────────────────────────────────────────────────────
    # QSettings 持久化
    # ─────────────────────────────────────────────────────────────────

    def _save_settings(self) -> None:
        """将当前所有 UI 参数保存到 QSettings"""
        s = self._settings
        s.setValue("db/host",     self.db_host.text())
        s.setValue("db/port",     self.db_port.value())
        s.setValue("db/user",     self.db_user.text())
        s.setValue("db/password", self.db_password.text())
        s.setValue("db/ask_pass", self.radio_askpass.isChecked())
        s.setValue("db/charset",  self.db_charset.currentText())

        s.setValue("pt/max_lag",        self.pt_max_lag.value())
        s.setValue("pt/check_interval", self.pt_check_interval.value())
        s.setValue("pt/slave_lag",      self.pt_slave_lag.text())
        s.setValue("pt/recursion",      self.pt_recursion.currentText())
        s.setValue("pt/max_load",       self.pt_max_load.text())
        s.setValue("pt/critical_load",  self.pt_critical_load.text())
        s.setValue("pt/chunk_size",     self.pt_chunk_size.value())
        s.setValue("pt/chunk_index",    self.pt_chunk_index.text())
        s.setValue("pt/new_table_name", self.pt_new_table_name.text())

        s.setValue("flags/no_replication_filters", self.chk_no_replication_filters.isChecked())
        s.setValue("flags/no_check_alter",         self.chk_no_check_alter.isChecked())
        s.setValue("flags/drop_old_table",         self.chk_drop_old_table.isChecked())
        s.setValue("flags/drop_triggers",          self.chk_drop_triggers.isChecked())
        s.setValue("flags/print",                  self.chk_print.isChecked())
        s.setValue("flags/execute",                self.radio_execute.isChecked())

        s.setValue("extra/args", self.extra_args.text())

        # 窗口几何
        s.setValue("window/geometry", self.saveGeometry())

    def _load_settings(self) -> None:
        """从 QSettings 恢复上次 UI 参数；若无记录则保持默认值"""
        s = self._settings

        # 若没有任何存储记录则跳过（保持默认值）
        if not s.contains("db/host"):
            return

        self.db_host.setText(s.value("db/host",  "127.0.0.1"))
        self.db_port.setValue(int(s.value("db/port", 3306)))
        self.db_user.setText(s.value("db/user",  "root"))
        self.db_password.setText(s.value("db/password", ""))

        ask_pass = s.value("db/ask_pass", True, type=bool)
        self.radio_askpass.setChecked(ask_pass)
        self.radio_password.setChecked(not ask_pass)

        charset = s.value("db/charset", "utf8mb4")
        idx = self.db_charset.findText(charset)
        if idx >= 0:
            self.db_charset.setCurrentIndex(idx)
        else:
            self.db_charset.setCurrentText(charset)

        self.pt_max_lag.setValue(int(s.value("pt/max_lag", 10)))
        self.pt_check_interval.setValue(int(s.value("pt/check_interval", 5)))
        self.pt_slave_lag.setText(s.value("pt/slave_lag", ""))

        recursion = s.value("pt/recursion", "processlist")
        idx = self.pt_recursion.findText(recursion)
        if idx >= 0:
            self.pt_recursion.setCurrentIndex(idx)
        else:
            self.pt_recursion.setCurrentText(recursion)

        self.pt_max_load.setText(s.value("pt/max_load",      "Threads_running=25"))
        self.pt_critical_load.setText(s.value("pt/critical_load", "Threads_running=50"))
        self.pt_chunk_size.setValue(int(s.value("pt/chunk_size", 1000)))
        self.pt_chunk_index.setText(s.value("pt/chunk_index", ""))
        self.pt_new_table_name.setText(s.value("pt/new_table_name", ""))

        self.chk_no_replication_filters.setChecked(s.value("flags/no_replication_filters", True,  type=bool))
        self.chk_no_check_alter.setChecked(        s.value("flags/no_check_alter",         False, type=bool))
        self.chk_drop_old_table.setChecked(        s.value("flags/drop_old_table",         True,  type=bool))
        self.chk_drop_triggers.setChecked(         s.value("flags/drop_triggers",          True,  type=bool))
        self.chk_print.setChecked(                 s.value("flags/print",                  True,  type=bool))

        execute = s.value("flags/execute", True, type=bool)
        self.radio_execute.setChecked(execute)
        self.radio_dryrun.setChecked(not execute)

        self.extra_args.setText(s.value("extra/args", ""))

        # 恢复窗口几何
        geom = s.value("window/geometry")
        if geom:
            self.restoreGeometry(geom)

    # 关闭时自动保存
    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._save_settings()
        super().closeEvent(event)
