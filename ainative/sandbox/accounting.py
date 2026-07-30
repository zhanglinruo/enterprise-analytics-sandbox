from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta

from .events import BusinessEvent


@dataclass(frozen=True)
class FinancialSnapshot:
    period: str
    revenue_cents: int
    cogs_cents: int
    gross_profit_cents: int
    cash_cents: int
    accounts_receivable_cents: int
    inventory_cents: int
    accounts_payable_cents: int
    assets_cents: int
    liabilities_cents: int
    equity_cents: int


class AccountingProjector:
    def project(
        self, conn: sqlite3.Connection, events: tuple[BusinessEvent, ...]
    ) -> None:
        customer_terms = dict(
            conn.execute(
                "select customer_id, credit_term_days from dim_customer"
            ).fetchall()
        )
        supplier_terms = dict(
            conn.execute(
                "select supplier_id, credit_term_days from dim_supplier"
            ).fetchall()
        )
        customer_regions = dict(
            conn.execute("select customer_id, region_id from dim_customer").fetchall()
        )
        documents: dict[str, str] = {}
        counters: dict[str, int] = {}
        journal_line = 0
        voucher_number = 0
        movement_number = 0

        def next_id(kind: str, prefix: str) -> str:
            counters[kind] = counters.get(kind, 0) + 1
            return f"{prefix}{counters[kind]:08d}"

        def attributes(event: BusinessEvent) -> dict[str, str]:
            return dict(event.attributes)

        def post(
            event: BusinessEvent,
            source_type: str,
            source_id: str,
            debit_account: str,
            credit_account: str,
            amount_cents: int,
        ) -> None:
            nonlocal journal_line, voucher_number
            if amount_cents <= 0:
                return
            voucher_number += 1
            voucher_id = f"VOU{voucher_number:08d}"
            lines = []
            for account_id, debit, credit in (
                (debit_account, amount_cents, 0),
                (credit_account, 0, amount_cents),
            ):
                journal_line += 1
                lines.append(
                    (
                        f"JE{journal_line:010d}",
                        voucher_id,
                        event.event_date,
                        event.period,
                        account_id,
                        debit,
                        credit,
                        source_type,
                        source_id,
                        event.event_id,
                    )
                )
            conn.executemany(
                "insert into fact_journal_entry values "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                lines,
            )

        def move_inventory(
            event: BusinessEvent,
            movement_type: str,
            quantity: int,
            source_type: str,
            source_id: str,
        ) -> None:
            nonlocal movement_number
            movement_number += 1
            conn.execute(
                "insert into fact_inventory_movement values "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    f"IM{movement_number:010d}",
                    event.event_date,
                    event.period,
                    event.product_id,
                    movement_type,
                    quantity,
                    event.unit_price_cents or 0,
                    source_type,
                    source_id,
                    event.event_id,
                ),
            )

        with conn:
            for event in events:
                attrs = attributes(event)
                quantity = event.quantity or 0
                unit_price = event.unit_price_cents or 0
                amount = quantity * unit_price

                if event.event_type == "opening_capitalization":
                    source_id = next_id("opening", "OPEN")
                    post(
                        event,
                        "opening_capitalization",
                        source_id,
                        "1001",
                        "4001",
                        unit_price,
                    )
                elif event.event_type == "opening_inventory":
                    source_id = next_id("opening_inventory", "OPENINV")
                    move_inventory(
                        event,
                        "opening_finished_goods",
                        quantity,
                        "opening_inventory",
                        source_id,
                    )
                    post(
                        event,
                        "opening_inventory",
                        source_id,
                        "1406",
                        "4001",
                        amount,
                    )
                elif event.event_type == "purchase_order":
                    po_line_id = next_id("po_line", "POL")
                    po_id = f"PO{po_line_id[3:]}"
                    conn.execute(
                        "insert into fact_purchase_order values "
                        "(?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            po_line_id,
                            po_id,
                            event.event_date,
                            event.period,
                            event.counterparty_id,
                            event.product_id,
                            quantity,
                            unit_price,
                            event.event_id,
                        ),
                    )
                    documents[event.event_id] = po_line_id
                elif event.event_type == "goods_receipt":
                    po_line_id = documents[attrs["purchase_order_event_id"]]
                    gr_line_id = next_id("gr_line", "GRL")
                    gr_id = f"GR{gr_line_id[3:]}"
                    conn.execute(
                        "insert into fact_goods_receipt values "
                        "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            gr_line_id,
                            gr_id,
                            po_line_id,
                            event.event_date,
                            event.period,
                            event.counterparty_id,
                            event.product_id,
                            quantity,
                            unit_price,
                            event.event_id,
                        ),
                    )
                    documents[event.event_id] = gr_line_id
                    move_inventory(
                        event,
                        "raw_material_receipt",
                        quantity,
                        "goods_receipt",
                        gr_id,
                    )
                    post(event, "goods_receipt", gr_id, "1405", "2203", amount)
                elif event.event_type == "supplier_invoice":
                    gr_line_id = documents[attrs["goods_receipt_event_id"]]
                    ap_invoice_id = next_id("ap_invoice", "API")
                    invoice_date = date.fromisoformat(event.event_date)
                    due_date = invoice_date + timedelta(
                        days=supplier_terms[event.counterparty_id]
                    )
                    conn.execute(
                        "insert into fact_supplier_invoice values "
                        "(?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            ap_invoice_id,
                            gr_line_id,
                            event.event_date,
                            event.period,
                            event.counterparty_id,
                            amount,
                            due_date.isoformat(),
                            event.event_id,
                        ),
                    )
                    documents[event.event_id] = ap_invoice_id
                    post(
                        event,
                        "supplier_invoice",
                        ap_invoice_id,
                        "2203",
                        "2202",
                        amount,
                    )
                elif event.event_type == "cash_payment":
                    ap_invoice_id = documents[
                        attrs["supplier_invoice_event_id"]
                    ]
                    payment_id = next_id("payment", "PAY")
                    conn.execute(
                        "insert into fact_cash_payment values "
                        "(?, ?, ?, ?, ?, ?, ?)",
                        (
                            payment_id,
                            ap_invoice_id,
                            event.event_date,
                            event.period,
                            event.counterparty_id,
                            amount,
                            event.event_id,
                        ),
                    )
                    post(event, "cash_payment", payment_id, "2202", "1001", amount)
                elif event.event_type == "manufacturing_completion":
                    completion_id = next_id("completion", "MFG")
                    move_inventory(
                        event,
                        "raw_material_issue",
                        -quantity,
                        "manufacturing_completion",
                        completion_id,
                    )
                    move_inventory(
                        event,
                        "finished_goods_receipt",
                        quantity,
                        "manufacturing_completion",
                        completion_id,
                    )
                    post(
                        event,
                        "manufacturing_completion",
                        completion_id,
                        "1406",
                        "1405",
                        amount,
                    )
                elif event.event_type == "sales_order":
                    order_line_id = next_id("order_line", "SOL")
                    order_id = f"SO{order_line_id[3:]}"
                    discount_bps = int(attrs["discount_rate_bps"])
                    net_amount = amount * (10_000 - discount_bps) // 10_000
                    conn.execute(
                        "insert into fact_sales_order values "
                        "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            order_line_id,
                            order_id,
                            event.event_date,
                            event.period,
                            event.organization_id,
                            customer_regions[event.counterparty_id],
                            event.counterparty_id,
                            event.product_id,
                            quantity,
                            unit_price,
                            discount_bps,
                            net_amount,
                            event.event_id,
                        ),
                    )
                    documents[event.event_id] = order_line_id
                elif event.event_type == "sales_delivery":
                    order_line_id = documents[attrs["sales_order_event_id"]]
                    delivery_line_id = next_id("delivery_line", "SDL")
                    delivery_id = f"SD{delivery_line_id[3:]}"
                    conn.execute(
                        "insert into fact_sales_delivery values "
                        "(?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            delivery_line_id,
                            delivery_id,
                            order_line_id,
                            event.event_date,
                            event.period,
                            event.product_id,
                            quantity,
                            unit_price,
                            event.event_id,
                        ),
                    )
                    documents[event.event_id] = delivery_line_id
                    move_inventory(
                        event,
                        "sales_issue",
                        -quantity,
                        "sales_delivery",
                        delivery_id,
                    )
                    post(
                        event,
                        "sales_delivery",
                        delivery_id,
                        "5401",
                        "1406",
                        amount,
                    )
                elif event.event_type == "sales_invoice":
                    delivery_line_id = documents[
                        attrs["sales_delivery_event_id"]
                    ]
                    invoice_line_id = next_id("invoice_line", "SIL")
                    invoice_id = f"SI{invoice_line_id[3:]}"
                    discount_bps = int(attrs["discount_rate_bps"])
                    revenue = amount * (10_000 - discount_bps) // 10_000
                    invoice_date = date.fromisoformat(event.event_date)
                    due_date = invoice_date + timedelta(
                        days=customer_terms[event.counterparty_id]
                    )
                    conn.execute(
                        "insert into fact_sales_invoice values "
                        "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            invoice_line_id,
                            invoice_id,
                            delivery_line_id,
                            event.event_date,
                            event.period,
                            event.counterparty_id,
                            event.product_id,
                            quantity,
                            revenue,
                            due_date.isoformat(),
                            event.event_id,
                        ),
                    )
                    documents[event.event_id] = invoice_id
                    post(
                        event,
                        "sales_invoice",
                        invoice_id,
                        "1122",
                        "5001",
                        revenue,
                    )
                elif event.event_type == "cash_receipt":
                    invoice_id = documents[attrs["sales_invoice_event_id"]]
                    receipt_id = next_id("receipt", "REC")
                    discount_bps = int(attrs["discount_rate_bps"])
                    receipt_amount = (
                        amount * (10_000 - discount_bps) // 10_000
                    )
                    conn.execute(
                        "insert into fact_cash_receipt values "
                        "(?, ?, ?, ?, ?, ?, ?)",
                        (
                            receipt_id,
                            invoice_id,
                            event.event_date,
                            event.period,
                            event.counterparty_id,
                            receipt_amount,
                            event.event_id,
                        ),
                    )
                    post(
                        event,
                        "cash_receipt",
                        receipt_id,
                        "1001",
                        "1122",
                        receipt_amount,
                    )


def financial_snapshot(
    conn: sqlite3.Connection, period: str
) -> FinancialSnapshot:
    balances = {
        account_id: debit - credit
        for account_id, debit, credit in conn.execute(
            """
            select account_id, sum(debit_cents), sum(credit_cents)
            from fact_journal_entry
            where period <= ?
            group by account_id
            """,
            (period,),
        )
    }
    cash = balances.get("1001", 0)
    receivables = balances.get("1122", 0)
    inventory = balances.get("1405", 0) + balances.get("1406", 0)
    payables = -balances.get("2202", 0)
    accruals = -balances.get("2203", 0)
    revenue = -balances.get("5001", 0)
    cogs = balances.get("5401", 0)
    gross_profit = revenue - cogs
    assets = cash + receivables + inventory
    liabilities = payables + accruals
    paid_in_capital = -balances.get("4001", 0)
    equity = paid_in_capital + gross_profit
    return FinancialSnapshot(
        period=period,
        revenue_cents=revenue,
        cogs_cents=cogs,
        gross_profit_cents=gross_profit,
        cash_cents=cash,
        accounts_receivable_cents=receivables,
        inventory_cents=inventory,
        accounts_payable_cents=payables,
        assets_cents=assets,
        liabilities_cents=liabilities,
        equity_cents=equity,
    )
