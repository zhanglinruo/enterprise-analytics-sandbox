from __future__ import annotations

import random
import sqlite3

from .spec import ScenarioSpec


ACCOUNTS = (
    ("1001", "Bank", "asset"),
    ("1122", "Accounts Receivable", "asset"),
    ("1405", "Raw Material Inventory", "asset"),
    ("1406", "Finished Goods Inventory", "asset"),
    ("2202", "Accounts Payable", "liability"),
    ("2203", "Goods Receipt Accrual", "liability"),
    ("4001", "Paid-in Capital", "equity"),
    ("5001", "Main Operating Revenue", "revenue"),
    ("5401", "Cost of Goods Sold", "expense"),
)


class MasterDataGenerator:
    def __init__(self, spec: ScenarioSpec):
        self.spec = spec

    def populate(self, conn: sqlite3.Connection) -> None:
        rng = random.Random(self.spec.seed)
        with conn:
            self._populate_organizations(conn)
            self._populate_suppliers(conn, rng)
            self._populate_customers(conn, rng)
            self._populate_products(conn, rng)
            conn.executemany(
                "insert into dim_account(account_id, account_name, account_type) "
                "values (?, ?, ?)",
                ACCOUNTS,
            )

    def _populate_organizations(self, conn: sqlite3.Connection) -> None:
        organizations = [
            ("COMP001", "华辰智能制造有限公司", "company", None),
            ("BU001", "核心产品事业部", "business_unit", "COMP001"),
            ("BU002", "价值产品事业部", "business_unit", "COMP001"),
            ("PLANT001", "苏州工厂", "plant", "BU001"),
            ("PLANT002", "合肥工厂", "plant", "BU001"),
            ("PLANT003", "成都工厂", "plant", "BU002"),
            ("REGION001", "华东区域", "sales_region", "COMP001"),
            ("REGION002", "华南区域", "sales_region", "COMP001"),
            ("REGION003", "华北区域", "sales_region", "COMP001"),
            ("REGION004", "西部区域", "sales_region", "COMP001"),
        ]
        conn.executemany(
            "insert into dim_organization("
            "organization_id, organization_name, organization_type, "
            "parent_organization_id) values (?, ?, ?, ?)",
            organizations,
        )

    def _populate_suppliers(
        self, conn: sqlite3.Connection, rng: random.Random
    ) -> None:
        rows = [
            (
                f"SUP{index:04d}",
                f"华源供应商{index:03d}号",
                "core_material" if index <= 30 else "general_material",
                rng.choice((30, 45, 60)),
            )
            for index in range(1, self.spec.supplier_count + 1)
        ]
        conn.executemany(
            "insert into dim_supplier("
            "supplier_id, supplier_name, supplier_category, credit_term_days"
            ") values (?, ?, ?, ?)",
            rows,
        )

    def _populate_customers(
        self, conn: sqlite3.Connection, rng: random.Random
    ) -> None:
        tiers = ("A", "B", "C")
        rows = [
            (
                f"CUST{index:04d}",
                f"远景客户{index:03d}号",
                f"REGION{((index - 1) % self.spec.sales_region_count) + 1:03d}",
                tiers[(index - 1) % len(tiers)],
                rng.choice((30, 45, 60)),
                1 if index <= 15 else 0,
            )
            for index in range(1, self.spec.customer_count + 1)
        ]
        conn.executemany(
            "insert into dim_customer("
            "customer_id, customer_name, region_id, customer_tier, "
            "credit_term_days, is_key_customer) values (?, ?, ?, ?, ?, ?)",
            rows,
        )

    def _populate_products(
        self, conn: sqlite3.Connection, rng: random.Random
    ) -> None:
        rows = []
        for index in range(1, self.spec.product_count + 1):
            product_line = "CORE" if index <= 70 else "VALUE"
            sale_price = rng.randrange(18_000, 80_001, 100)
            gross_margin = 0.32 if product_line == "CORE" else 0.14
            unit_cost = round(sale_price * (1 - gross_margin))
            supplier_index = ((index - 1) % self.spec.supplier_count) + 1
            rows.append(
                (
                    f"PROD{index:04d}",
                    f"{'核心' if product_line == 'CORE' else '价值'}产品{index:03d}号",
                    product_line,
                    sale_price,
                    unit_cost,
                    f"SUP{supplier_index:04d}",
                )
            )
        conn.executemany(
            "insert into dim_product("
            "product_id, product_name, product_line, base_sale_price_cents, "
            "base_unit_cost_cents, preferred_supplier_id"
            ") values (?, ?, ?, ?, ?, ?)",
            rows,
        )
