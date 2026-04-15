"""
核心转换模块：将 ALTER TABLE SQL 转换为 pt-online-schema-change 命令
"""
import re
from dataclasses import dataclass, field


@dataclass
class PTConfig:
    """pt-online-schema-change 所有可配置参数"""

    # 数据库连接参数
    user: str = "root"
    host: str = "127.0.0.1"
    port: int = 3306
    charset: str = "utf8mb4"

    # 认证方式：True=交互输入密码, False=使用密码字段
    ask_pass: bool = True
    password: str = ""

    # 延迟相关
    max_lag: int = 10
    check_interval: int = 5
    check_slave_lag: str = ""          # 格式: h=...,u=...,p=...
    recursion_method: str = "processlist"  # none / hosts / processlist / dsn=...

    # 负载限制
    max_load: str = "Threads_running=25"
    critical_load: str = "Threads_running=50"

    # 分块参数
    chunk_size: int = 1000
    chunk_index_columns: str = ""

    # 功能开关
    no_check_replication_filters: bool = True
    no_check_alter: bool = False
    drop_old_table: bool = True
    drop_triggers: bool = True

    # 输出与执行
    print_cmd: bool = True
    execute: bool = True              # False = dry-run 模式

    # 新临时表名（留空则由 pt-osc 自动生成）
    new_table_name: str = ""

    # 附加自定义参数（用户自由输入）
    extra_args: str = ""


class PTConverter:
    """将 ALTER TABLE 语句转换为 pt-online-schema-change 命令"""

    # 支持 schema.table 或单独 table 两种格式
    _PATTERN = re.compile(
        r"(?i)alter\s+table\s+([`'\"]?[\w]+[`'\"]?\.)?[`'\"]?([\w]+)[`'\"]?\s+(.+)",
    )

    def __init__(self, config: PTConfig):
        self.config = config

    def parse_sql(self, sql: str) -> tuple[str, str, str]:
        """
        解析 ALTER TABLE SQL，返回 (schema, table, alter_clause)
        schema 可能为空字符串
        """
        sql = sql.strip().rstrip(";")
        m = self._PATTERN.match(sql)
        if not m:
            raise ValueError("无法解析 ALTER TABLE 语句，请检查 SQL 格式。")

        schema_raw = m.group(1) or ""           # 可能是 "schema." 或空
        table_raw  = m.group(2)
        alter_clause = m.group(3).strip()

        # 去掉 schema 末尾的点和反引号
        schema = schema_raw.strip(".`'\"")
        table  = table_raw.strip("`'\"")

        # 去掉 alter_clause 中的反引号
        alter_clause = alter_clause.replace("`", "")

        return schema, table, alter_clause

    def build_command(self, sql: str) -> str:
        """
        将 SQL 转换为完整 pt-online-schema-change 命令字符串
        """
        schema, table, alter_clause = self.parse_sql(sql)
        cfg = self.config

        parts: list[str] = ["pt-online-schema-change"]

        # ---- 连接参数 ----
        parts.append(f"--user={cfg.user}")
        parts.append(f"--host={cfg.host}")
        parts.append(f"--port={cfg.port}")

        # 认证
        if cfg.ask_pass:
            parts.append("--ask-pass")
        elif cfg.password:
            parts.append(f"--password={cfg.password}")

        # ---- 字符集 ----
        parts.append(f"--charset={cfg.charset}")

        # ---- 延迟 & 从库 ----
        parts.append(f"--max-lag={cfg.max_lag}")
        parts.append(f"--check-interval={cfg.check_interval}")

        if cfg.check_slave_lag:
            parts.append(f"--check-slave-lag={cfg.check_slave_lag}")

        if cfg.recursion_method:
            parts.append(f"--recursion-method={cfg.recursion_method}")

        # ---- 负载限制 ----
        if cfg.max_load:
            parts.append(f"--max-load={cfg.max_load}")
        if cfg.critical_load:
            parts.append(f"--critical-load={cfg.critical_load}")

        # ---- 分块 ----
        parts.append(f"--chunk-size={cfg.chunk_size}")
        if cfg.chunk_index_columns:
            parts.append(f"--chunk-index-columns={cfg.chunk_index_columns}")

        # ---- 功能开关 ----
        if cfg.no_check_replication_filters:
            parts.append("--no-check-replication-filters")
        if cfg.no_check_alter:
            parts.append("--no-check-alter")
        if not cfg.drop_old_table:
            parts.append("--no-drop-old-table")
        if not cfg.drop_triggers:
            parts.append("--no-drop-triggers")

        # ---- 新临时表名（可选）----
        if cfg.new_table_name.strip():
            parts.append(f"--new-table-name={cfg.new_table_name.strip()}")

        # ---- ALTER 内容 ----
        parts.append(f'--alter "{alter_clause}"')

        # ---- DSN 连接字符串 ----
        if schema:
            dsn = f"D={schema},t={table}"
        else:
            dsn = f"t={table}"
        parts.append(dsn)

        # ---- 附加参数 ----
        if cfg.extra_args.strip():
            parts.append(cfg.extra_args.strip())

        # ---- 输出与执行 ----
        if cfg.print_cmd:
            parts.append("--print")
        if cfg.execute:
            parts.append("--execute")
        else:
            parts.append("--dry-run")

        # 格式化：每个参数一行，用 \ 续行
        lines = " \\\n    ".join(parts)
        return lines
