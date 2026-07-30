from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from enum import StrEnum

from .accounting import financial_snapshot
from .scenarios import ScenarioDefinition
from .schema import PUBLISHED_TABLES


class Severity(StrEnum):
    BLOCKING = "blocking"
    WARNING = "warning"
    SCENARIO_FAILURE = "scenario_failure"


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    severity: Severity
    message: str
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class ValidationReport:
    issues: tuple[ValidationIssue, ...]

    @property
    def publishable(self) -> bool:
        return not any(
            issue.severity in (Severity.BLOCKING, Severity.SCENARIO_FAILURE)
            for issue in self.issues
        )


class SandboxValidator:
    @staticmethod
    def empty_report() -> ValidationReport:
        return ValidationReport(())

    def validate(
        self, conn: sqlite3.Connection, scenario: ScenarioDefinition
    ) -> ValidationReport:
        reports = (
            self.validate_journals(conn),
            self.validate_accounting_equation(conn),
            self.validate_inventory(conn),
            self.validate_receivables(conn),
            self.validate_payables(conn),
            self.validate_cash(conn),
            self.validate_lineage(conn),
            self.validate_foreign_keys(conn),
            self.validate_document_dates(conn),
            self.validate_scenario_targets(conn, scenario),
            self.validate_distributions(conn),
        )
        return ValidationReport(
            tuple(issue for report in reports for issue in report.issues)
        )

    def validate_journals(self, conn: sqlite3.Connection) -> ValidationReport:
        rows = conn.execute(
            """
            select voucher_id, sum(debit_cents), sum(credit_cents)
            from fact_journal_entry
            group by voucher_id
            having sum(debit_cents) <> sum(credit_cents)
            """
        ).fetchall()
        if not rows:
            return self.empty_report()
        return self._blocking(
            "journal_unbalanced",
            f"{len(rows)} journal vouchers are unbalanced",
            tuple(row[0] for row in rows[:10]),
        )

    def validate_accounting_equation(
        self, conn: sqlite3.Connection
    ) -> ValidationReport:
        periods = [
            row[0]
            for row in conn.execute(
                "select distinct period from fact_journal_entry order by period"
            )
        ]
        failed = []
        for period in periods:
            snapshot = financial_snapshot(conn, period)
            if snapshot.assets_cents != (
                snapshot.liabilities_cents + snapshot.equity_cents
            ):
                failed.append(period)
        if not failed:
            return self.empty_report()
        return self._blocking(
            "accounting_equation_failed",
            "Assets do not equal liabilities plus equity",
            tuple(failed),
        )

    def validate_inventory(self, conn: sqlite3.Connection) -> ValidationReport:
        negative = conn.execute(
            """
            with balances as (
                select product_id, movement_id,
                       sum(quantity) over (
                           partition by product_id
                           order by movement_date, movement_id
                       ) as running_quantity
                from fact_inventory_movement
            )
            select product_id, min(running_quantity)
            from balances
            group by product_id
            having min(running_quantity) < 0
            """
        ).fetchall()
        if not negative:
            return self.empty_report()
        return self._blocking(
            "inventory_negative",
            f"{len(negative)} products have negative inventory",
            tuple(f"{row[0]}:{row[1]}" for row in negative[:10]),
        )

    def validate_receivables(self, conn: sqlite3.Connection) -> ValidationReport:
        mismatches = conn.execute(
            """
            select invoice_id
            from (
                select invoice_id, sum(revenue_cents) as invoiced
                from fact_sales_invoice group by invoice_id
            ) invoice
            left join (
                select invoice_id, sum(amount_cents) as received
                from fact_cash_receipt group by invoice_id
            ) receipt using (invoice_id)
            where invoiced <> coalesce(received, 0)
            """
        ).fetchall()
        if not mismatches:
            return self.empty_report()
        return self._blocking(
            "receivables_unreconciled",
            f"{len(mismatches)} sales invoices do not reconcile to receipts",
            tuple(row[0] for row in mismatches[:10]),
        )

    def validate_payables(self, conn: sqlite3.Connection) -> ValidationReport:
        mismatches = conn.execute(
            """
            select ap_invoice_id
            from fact_supplier_invoice invoice
            left join (
                select ap_invoice_id, sum(amount_cents) as paid
                from fact_cash_payment group by ap_invoice_id
            ) payment using (ap_invoice_id)
            where invoice.amount_cents <> coalesce(payment.paid, 0)
            """
        ).fetchall()
        if not mismatches:
            return self.empty_report()
        return self._blocking(
            "payables_unreconciled",
            f"{len(mismatches)} supplier invoices do not reconcile to payments",
            tuple(row[0] for row in mismatches[:10]),
        )

    def validate_cash(self, conn: sqlite3.Connection) -> ValidationReport:
        minimum = conn.execute(
            """
            with cash_balance as (
                select sum(debit_cents - credit_cents) over (
                    order by posting_date, entry_line_id
                ) as running_cash
                from fact_journal_entry
                where account_id = '1001'
            )
            select min(running_cash) from cash_balance
            """
        ).fetchone()[0]
        if minimum is None or minimum >= 0:
            return self.empty_report()
        return self._blocking(
            "cash_negative",
            "Cash balance becomes negative",
            (str(minimum),),
        )

    def validate_lineage(self, conn: sqlite3.Connection) -> ValidationReport:
        missing: list[str] = []
        for table in PUBLISHED_TABLES:
            if not table.startswith("fact_"):
                continue
            count = conn.execute(
                f"select count(*) from {table} "
                "where source_event_id is null or source_event_id = ''"
            ).fetchone()[0]
            if count:
                missing.append(f"{table}:{count}")
        if not missing:
            return self.empty_report()
        return self._blocking(
            "lineage_missing",
            "Fact rows are missing source event lineage",
            tuple(missing),
        )

    def validate_foreign_keys(
        self, conn: sqlite3.Connection
    ) -> ValidationReport:
        failures = conn.execute("pragma foreign_key_check").fetchall()
        if not failures:
            return self.empty_report()
        return self._blocking(
            "foreign_key_failed",
            f"{len(failures)} foreign-key violations found",
            tuple(":".join(str(value) for value in row) for row in failures[:10]),
        )

    def validate_document_dates(
        self, conn: sqlite3.Connection
    ) -> ValidationReport:
        sales_failures = conn.execute(
            """
            select so.order_line_id
            from fact_sales_order so
            join fact_sales_delivery sd using (order_line_id)
            join fact_sales_invoice si using (delivery_line_id)
            join fact_cash_receipt cr using (invoice_id)
            where so.order_date > sd.delivery_date
               or sd.delivery_date > si.invoice_date
               or si.invoice_date > cr.receipt_date
            """
        ).fetchall()
        purchase_failures = conn.execute(
            """
            select po.po_line_id
            from fact_purchase_order po
            join fact_goods_receipt gr using (po_line_id)
            join fact_supplier_invoice api using (gr_line_id)
            join fact_cash_payment cp using (ap_invoice_id)
            where po.order_date > gr.receipt_date
               or gr.receipt_date > api.invoice_date
               or api.invoice_date > cp.payment_date
            """
        ).fetchall()
        failures = [
            *(f"sales:{row[0]}" for row in sales_failures[:10]),
            *(f"purchase:{row[0]}" for row in purchase_failures[:10]),
        ]
        if not failures:
            return self.empty_report()
        return self._blocking(
            "document_dates_invalid",
            "Document dates violate process sequence",
            tuple(failures),
        )

    def validate_scenario_targets(
        self, conn: sqlite3.Connection, scenario: ScenarioDefinition
    ) -> ValidationReport:
        actual_revenue = conn.execute(
            "select coalesce(sum(revenue_cents), 0) "
            "from fact_sales_invoice where period between '2025-10' and '2025-12'"
        ).fetchone()[0]
        actual_cogs = conn.execute(
            "select coalesce(sum(quantity * unit_cost_cents), 0) "
            "from fact_sales_delivery where period between '2025-10' and '2025-12'"
        ).fetchone()[0]
        discount_increment = next(
            cause.increment or 0
            for cause in scenario.causes
            if cause.cause_id == "customer_discount_increase"
        )
        rows = conn.execute(
            """
            select p.product_line,
                   sum(so.quantity) as units,
                   1.0 * sum(
                       so.quantity * so.unit_price_cents
                       * (
                           10000 - max(
                               0,
                               so.discount_rate_bps
                               - case when c.is_key_customer = 1 then ? else 0 end
                           )
                       ) / 10000
                   ) / sum(so.quantity) as net_unit_revenue,
                   1.0 * sum(so.quantity * p.base_unit_cost_cents)
                       / sum(so.quantity) as base_unit_cost
            from fact_sales_order so
            join dim_product p using (product_id)
            join dim_customer c using (customer_id)
            where so.period between '2025-10' and '2025-12'
            group by p.product_line
            """,
            (discount_increment,),
        ).fetchall()
        if not rows or actual_revenue <= 0:
            return self._scenario_failure(
                "scenario_data_missing",
                "Scenario periods contain no analyzable sales data",
            )

        total_baseline_units = sum(row[1] for row in rows) / scenario.demand_multiplier
        economics = {
            row[0]: (float(row[2]), float(row[3]))
            for row in rows
        }
        core_revenue, core_cost = economics["CORE"]
        value_revenue, value_cost = economics["VALUE"]
        baseline_revenue = total_baseline_units * (
            0.70 * core_revenue + 0.30 * value_revenue
        )
        baseline_cogs = total_baseline_units * (
            0.70 * core_cost + 0.30 * value_cost
        )
        baseline_profit = baseline_revenue - baseline_cogs
        actual_profit = actual_revenue - actual_cogs
        revenue_growth = actual_revenue / baseline_revenue - 1
        profit_growth = actual_profit / baseline_profit - 1

        failures = []
        if not (
            scenario.target("revenue_growth_min")
            <= revenue_growth
            <= scenario.target("revenue_growth_max")
        ):
            failures.append(f"revenue_growth={revenue_growth:.4f}")
        if not (
            scenario.target("profit_growth_min")
            <= profit_growth
            <= scenario.target("profit_growth_max")
        ):
            failures.append(f"profit_growth={profit_growth:.4f}")
        if not failures:
            return self.empty_report()
        return self._scenario_failure(
            "scenario_target_missed",
            "Generated financial effects are outside configured target ranges",
            tuple(failures),
        )

    def validate_distributions(
        self, conn: sqlite3.Connection
    ) -> ValidationReport:
        dimensions = {
            "customer": ("fact_sales_order", "customer_id"),
            "product": ("fact_sales_order", "product_id"),
            "region": ("fact_sales_order", "region_id"),
            "supplier": ("fact_purchase_order", "supplier_id"),
        }
        issues = []
        for name, (table, column) in dimensions.items():
            total = conn.execute(f"select count(*) from {table}").fetchone()[0]
            largest = conn.execute(
                f"select count(*) from {table} group by {column} "
                "order by count(*) desc limit 1"
            ).fetchone()
            if total and largest and largest[0] / total > 0.70:
                issues.append(
                    ValidationIssue(
                        code="distribution_concentrated",
                        severity=Severity.WARNING,
                        message=f"More than 70% of rows belong to one {name}",
                        evidence=(name, f"{largest[0] / total:.4f}"),
                    )
                )
        return ValidationReport(tuple(issues))

    @staticmethod
    def _blocking(
        code: str, message: str, evidence: tuple[str, ...] = ()
    ) -> ValidationReport:
        return ValidationReport(
            (ValidationIssue(code, Severity.BLOCKING, message, evidence),)
        )

    @staticmethod
    def _scenario_failure(
        code: str, message: str, evidence: tuple[str, ...] = ()
    ) -> ValidationReport:
        return ValidationReport(
            (ValidationIssue(code, Severity.SCENARIO_FAILURE, message, evidence),)
        )
