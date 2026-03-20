"""Database skill pack — SQLite, PostgreSQL, MySQL query and management."""

from tools.base_tool import BaseTool


class SQLiteQueryTool(BaseTool):
    name = "sqlite_query"
    description = "Execute a SQL query on a SQLite database file. Returns results as text table."
    parameters = {"type": "object", "properties": {
        "db_path": {"type": "string", "description": "Path to SQLite database file"},
        "query": {"type": "string", "description": "SQL query to execute"},
        "max_rows": {"type": "integer", "default": 50},
    }, "required": ["db_path", "query"]}

    def run(self, db_path: str, query: str, max_rows: int = 50) -> str:
        import sqlite3
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(query)

            if query.strip().upper().startswith("SELECT") or query.strip().upper().startswith("PRAGMA"):
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                rows = cursor.fetchmany(max_rows)
                conn.close()
                if not rows:
                    return "Query returned 0 rows."
                header = " | ".join(columns)
                sep = "-+-".join("-" * max(len(c), 5) for c in columns)
                lines = [header, sep]
                for row in rows:
                    lines.append(" | ".join(str(v)[:50] for v in row))
                return "\n".join(lines)
            else:
                conn.commit()
                affected = cursor.rowcount
                conn.close()
                return f"Query executed. Rows affected: {affected}"
        except Exception as e:
            return f"SQL Error: {e}"


class SQLiteInfoTool(BaseTool):
    name = "sqlite_info"
    description = "Show tables, columns, and schema of a SQLite database."
    parameters = {"type": "object", "properties": {
        "db_path": {"type": "string"},
        "table": {"type": "string", "default": "", "description": "Specific table to inspect (leave empty for all tables)"},
    }, "required": ["db_path"]}

    def run(self, db_path: str, table: str = "") -> str:
        import sqlite3
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            if table:
                # Validate table name to prevent injection (PRAGMA doesn't support params)
                import re
                if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table):
                    conn.close()
                    return "Invalid table name."
                cursor.execute(f"PRAGMA table_info([{table}])")
                cols = cursor.fetchall()
                conn.close()
                lines = [f"Table: {table}", "cid | name | type | notnull | default | pk"]
                for c in cols:
                    lines.append(f"{c[0]} | {c[1]} | {c[2]} | {c[3]} | {c[4]} | {c[5]}")
                return "\n".join(lines)
            else:
                cursor.execute("SELECT name, type FROM sqlite_master WHERE type IN ('table', 'view') ORDER BY name")
                items = cursor.fetchall()
                conn.close()
                if not items:
                    return "No tables found."
                return "Tables:\n" + "\n".join(f"  {name} ({typ})" for name, typ in items)
        except Exception as e:
            return f"Error: {e}"


class PostgreSQLQueryTool(BaseTool):
    name = "postgres_query"
    description = "Execute a SQL query on a PostgreSQL database. Requires psycopg2."
    parameters = {"type": "object", "properties": {
        "query": {"type": "string"},
        "host": {"type": "string", "default": "localhost"},
        "port": {"type": "integer", "default": 5432},
        "database": {"type": "string", "default": "postgres"},
        "user": {"type": "string", "default": "postgres"},
        "password": {"type": "string", "default": ""},
        "max_rows": {"type": "integer", "default": 50},
    }, "required": ["query"]}

    def run(self, query: str, host: str = "localhost", port: int = 5432,
            database: str = "postgres", user: str = "postgres",
            password: str = "", max_rows: int = 50) -> str:
        import os
        pwd = password or os.environ.get("POSTGRES_PASSWORD", "")
        try:
            import psycopg2
            conn = psycopg2.connect(host=host, port=port, dbname=database, user=user, password=pwd)
            cursor = conn.cursor()
            cursor.execute(query)

            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchmany(max_rows)
                conn.close()
                header = " | ".join(columns)
                lines = [header]
                for row in rows:
                    lines.append(" | ".join(str(v)[:50] for v in row))
                return "\n".join(lines)
            else:
                conn.commit()
                affected = cursor.rowcount
                conn.close()
                return f"Executed. Rows affected: {affected}"
        except ImportError:
            return "Requires: pip install psycopg2-binary"
        except Exception as e:
            return f"Error: {e}"


class MySQLQueryTool(BaseTool):
    name = "mysql_query"
    description = "Execute a SQL query on a MySQL database. Requires mysql-connector-python."
    parameters = {"type": "object", "properties": {
        "query": {"type": "string"},
        "host": {"type": "string", "default": "localhost"},
        "port": {"type": "integer", "default": 3306},
        "database": {"type": "string", "default": ""},
        "user": {"type": "string", "default": "root"},
        "password": {"type": "string", "default": ""},
        "max_rows": {"type": "integer", "default": 50},
    }, "required": ["query"]}

    def run(self, query: str, host: str = "localhost", port: int = 3306,
            database: str = "", user: str = "root",
            password: str = "", max_rows: int = 50) -> str:
        import os
        pwd = password or os.environ.get("MYSQL_PASSWORD", "")
        try:
            import mysql.connector
            conn = mysql.connector.connect(host=host, port=port, database=database, user=user, password=pwd)
            cursor = conn.cursor()
            cursor.execute(query)

            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchmany(max_rows)
                conn.close()
                header = " | ".join(columns)
                lines = [header]
                for row in rows:
                    lines.append(" | ".join(str(v)[:50] for v in row))
                return "\n".join(lines)
            else:
                conn.commit()
                affected = cursor.rowcount
                conn.close()
                return f"Executed. Rows affected: {affected}"
        except ImportError:
            return "Requires: pip install mysql-connector-python"
        except Exception as e:
            return f"Error: {e}"
