from __future__ import annotations

import csv
import json
import shutil
import sqlite3
import tempfile
import zipfile
from pathlib import Path

from .schema import PUBLISHED_TABLES
from .service import GenerationResult


PRIVATE_TOKENS = (
    "ground_truth",
    "raw_material_price_increase",
    "low_margin_product_mix",
    "customer_discount_increase",
    "forbidden_claims",
    "contribution",
)


class PrivateDataLeak(RuntimeError):
    pass


class ExamPackageBuilder:
    def build(self, result: GenerationResult, destination: Path) -> Path:
        if not result.validation.publishable:
            raise ValueError("Cannot package a non-publishable benchmark")
        destination.mkdir(parents=True, exist_ok=True)
        archive_path = destination / f"{result.spec.benchmark_id}.zip"

        with tempfile.TemporaryDirectory(prefix="exam-package-") as tmp:
            package_root = Path(tmp)
            self._prepare_directories(package_root)
            database_copy = package_root / "data" / "enterprise.db"
            shutil.copy2(result.database_path, database_copy)

            conn = sqlite3.connect(database_copy)
            try:
                self._assert_public_database(conn)
                self._export_csv(conn, package_root / "data" / "csv")
                self._write_dictionary(
                    conn, package_root / "schema" / "data_dictionary.md"
                )
                self._write_relationships(
                    conn, package_root / "schema" / "relationships.md"
                )
            finally:
                conn.close()

            project_root = Path(__file__).resolve().parents[2]
            shutil.copy2(
                project_root / "config" / "sandbox" / "metrics.json",
                package_root / "semantic" / "metrics.json",
            )
            (package_root / "task" / "analysis_question.md").write_text(
                "# 制造企业经营分析任务\n\n"
                "请识别本期最重要的经营异常，量化异常影响，使用数据证据解释主要原因，"
                "并明确列出仅凭现有数据无法确认、需要业务人员补充的信息。"
                "所有确定性结论必须注明数据来源。\n",
                encoding="utf-8",
            )
            manifest = {
                "benchmark_id": result.spec.benchmark_id,
                "database_sha256": result.database_sha256,
                "generator_version": result.spec.generator_version,
                "scenario_version": result.spec.scenario_version,
                "effective_seed": result.spec.seed,
                "published_tables": list(PUBLISHED_TABLES),
            }
            (package_root / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self._scan_for_leaks(package_root)
            self._write_zip(package_root, archive_path)

        return archive_path

    @staticmethod
    def _prepare_directories(root: Path) -> None:
        for relative in ("data/csv", "schema", "semantic", "task"):
            (root / relative).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _assert_public_database(conn: sqlite3.Connection) -> None:
        tables = {
            row[0]
            for row in conn.execute(
                "select name from sqlite_master "
                "where type='table' and name not like 'sqlite_%'"
            )
        }
        private_tables = tables - set(PUBLISHED_TABLES)
        missing_tables = set(PUBLISHED_TABLES) - tables
        if private_tables or missing_tables:
            raise PrivateDataLeak(
                f"Unexpected database tables: private={sorted(private_tables)}, "
                f"missing={sorted(missing_tables)}"
            )

    @staticmethod
    def _export_csv(conn: sqlite3.Connection, destination: Path) -> None:
        for table in PUBLISHED_TABLES:
            columns = [
                row[1] for row in conn.execute(f"pragma table_info({table})")
            ]
            primary_keys = [
                row[1]
                for row in conn.execute(f"pragma table_info({table})")
                if row[5]
            ]
            order_by = ", ".join(primary_keys or columns[:1])
            rows = conn.execute(
                f"select * from {table} order by {order_by}"
            )
            with (destination / f"{table}.csv").open(
                "w", encoding="utf-8-sig", newline=""
            ) as stream:
                writer = csv.writer(stream)
                writer.writerow(columns)
                writer.writerows(rows)

    @staticmethod
    def _write_dictionary(conn: sqlite3.Connection, path: Path) -> None:
        lines = [
            "# 经营分析沙盒数据字典",
            "",
            "所有数据均为虚构。金额字段使用人民币分，日期采用 ISO 8601 格式。",
            "",
        ]
        for table in PUBLISHED_TABLES:
            lines.extend(
                [
                    f"## `{table}`",
                    "",
                    "| 字段 | SQLite 类型 | 约束 |",
                    "|---|---|---|",
                ]
            )
            for _, name, column_type, not_null, _, primary_key in conn.execute(
                f"pragma table_info({table})"
            ):
                constraints = []
                if primary_key:
                    constraints.append("PK")
                if not_null:
                    constraints.append("NOT NULL")
                lines.append(
                    f"| `{name}` | {column_type} | {', '.join(constraints) or '-'} |"
                )
            lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")

    @staticmethod
    def _write_relationships(conn: sqlite3.Connection, path: Path) -> None:
        lines = ["# 数据关系", "", "| 子表字段 | 父表字段 |", "|---|---|"]
        for table in PUBLISHED_TABLES:
            for row in conn.execute(f"pragma foreign_key_list({table})"):
                parent_table = row[2]
                child_column = row[3]
                parent_column = row[4]
                lines.append(
                    f"| `{table}.{child_column}` | "
                    f"`{parent_table}.{parent_column}` |"
                )
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    @staticmethod
    def _scan_for_leaks(root: Path) -> None:
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix == ".db":
                continue
            content = path.read_text(encoding="utf-8-sig").lower()
            for token in PRIVATE_TOKENS:
                if token.lower() in content or token.lower() in path.as_posix().lower():
                    raise PrivateDataLeak(
                        f"Private token {token!r} found in {path.name}"
                    )

    @staticmethod
    def _write_zip(root: Path, archive_path: Path) -> None:
        with zipfile.ZipFile(
            archive_path, "w", compression=zipfile.ZIP_DEFLATED
        ) as archive:
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(root).as_posix())
