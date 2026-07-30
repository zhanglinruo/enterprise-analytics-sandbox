from __future__ import annotations

import calendar
import random
import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Callable

from .spec import ScenarioSpec


SEASONALITY = (0.85, 0.88, 0.95, 1.00, 1.04, 1.08, 0.92, 0.94, 1.03, 1.08, 1.20, 1.35)


@dataclass(frozen=True)
class BusinessEvent:
    event_id: str
    event_type: str
    event_date: str
    period: str
    organization_id: str
    counterparty_id: str | None
    product_id: str | None
    quantity: int | None
    unit_price_cents: int | None
    attributes: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class OperatingParameters:
    period: str
    demand_multiplier: float
    value_product_demand_share: float
    core_material_purchase_price_multiplier: float
    key_customer_discount_increment_bps: int


def normal_parameters(period: str) -> OperatingParameters:
    return OperatingParameters(
        period=period,
        demand_multiplier=1.0,
        value_product_demand_share=0.30,
        core_material_purchase_price_multiplier=1.0,
        key_customer_discount_increment_bps=0,
    )


class EventSimulator:
    def __init__(
        self,
        spec: ScenarioSpec,
        parameter_resolver: Callable[[str], OperatingParameters],
    ):
        self.spec = spec
        self.parameter_resolver = parameter_resolver

    def generate(self, conn: sqlite3.Connection) -> tuple[BusinessEvent, ...]:
        rng = random.Random(self.spec.seed)
        customers = conn.execute(
            "select customer_id, credit_term_days, is_key_customer "
            "from dim_customer order by customer_id"
        ).fetchall()
        suppliers = {
            row[0]: (row[1],)
            for row in conn.execute(
                "select supplier_id, credit_term_days "
                "from dim_supplier order by supplier_id"
            )
        }
        products = [
            {
                "product_id": row[0],
                "product_line": row[1],
                "sale_price": row[2],
                "unit_cost": row[3],
                "supplier_id": row[4],
            }
            for row in conn.execute(
                "select product_id, product_line, base_sale_price_cents, "
                "base_unit_cost_cents, preferred_supplier_id "
                "from dim_product order by product_id"
            )
        ]
        core_products = [row for row in products if row["product_line"] == "CORE"]
        value_products = [row for row in products if row["product_line"] == "VALUE"]
        events: list[BusinessEvent] = []

        def emit(
            event_type: str,
            event_date: date,
            period: str,
            *,
            counterparty_id: str | None = None,
            product_id: str | None = None,
            quantity: int | None = None,
            unit_price_cents: int | None = None,
            attributes: dict[str, str | int] | None = None,
        ) -> str:
            event_id = f"EVT{len(events) + 1:08d}"
            events.append(
                BusinessEvent(
                    event_id=event_id,
                    event_type=event_type,
                    event_date=event_date.isoformat(),
                    period=period,
                    organization_id="COMP001",
                    counterparty_id=counterparty_id,
                    product_id=product_id,
                    quantity=quantity,
                    unit_price_cents=unit_price_cents,
                    attributes=tuple(
                        sorted(
                            (key, str(value))
                            for key, value in (attributes or {}).items()
                        )
                    ),
                )
            )
            return event_id

        first_period = self.spec.periods()[0]
        first_day = self._period_date(first_period, 1)
        emit(
            "opening_capitalization",
            first_day,
            first_period,
            unit_price_cents=30_000_000_000,
        )
        for product in products:
            emit(
                "opening_inventory",
                first_day,
                first_period,
                product_id=product["product_id"],
                quantity=2_000,
                unit_price_cents=product["unit_cost"],
            )

        for month_index, period in enumerate(self.spec.periods()):
            params = self.parameter_resolver(period)
            seasonality = SEASONALITY[month_index]
            month_start = self._period_date(period, 1)

            for product in products:
                purchase_quantity = max(
                    1,
                    round(
                        (230 + rng.randint(0, 90))
                        * seasonality
                        * params.demand_multiplier
                    ),
                )
                purchase_multiplier = (
                    params.core_material_purchase_price_multiplier
                    if product["product_line"] == "CORE"
                    else 1.0
                )
                purchase_price = round(product["unit_cost"] * purchase_multiplier)
                supplier_id = product["supplier_id"]
                supplier_term = suppliers[supplier_id][0]
                po_date = month_start + timedelta(days=rng.randint(0, 5))
                po_event = emit(
                    "purchase_order",
                    po_date,
                    period,
                    counterparty_id=supplier_id,
                    product_id=product["product_id"],
                    quantity=purchase_quantity,
                    unit_price_cents=purchase_price,
                )
                gr_date = po_date + timedelta(days=rng.randint(5, 20))
                gr_event = emit(
                    "goods_receipt",
                    gr_date,
                    period,
                    counterparty_id=supplier_id,
                    product_id=product["product_id"],
                    quantity=purchase_quantity,
                    unit_price_cents=purchase_price,
                    attributes={"purchase_order_event_id": po_event},
                )
                invoice_date = gr_date + timedelta(days=rng.randint(0, 5))
                ap_event = emit(
                    "supplier_invoice",
                    invoice_date,
                    period,
                    counterparty_id=supplier_id,
                    product_id=product["product_id"],
                    quantity=purchase_quantity,
                    unit_price_cents=purchase_price,
                    attributes={"goods_receipt_event_id": gr_event},
                )
                emit(
                    "cash_payment",
                    invoice_date
                    + timedelta(days=supplier_term + rng.randint(-2, 5)),
                    period,
                    counterparty_id=supplier_id,
                    product_id=product["product_id"],
                    quantity=purchase_quantity,
                    unit_price_cents=purchase_price,
                    attributes={"supplier_invoice_event_id": ap_event},
                )
                emit(
                    "manufacturing_completion",
                    gr_date + timedelta(days=1),
                    period,
                    product_id=product["product_id"],
                    quantity=purchase_quantity,
                    unit_price_cents=purchase_price,
                    attributes={"goods_receipt_event_id": gr_event},
                )

            sales_line_count = rng.randint(600, 800)
            for _ in range(sales_line_count):
                customer_id, credit_term, is_key_customer = rng.choice(customers)
                product_pool = (
                    value_products
                    if rng.random() < params.value_product_demand_share
                    else core_products
                )
                product = rng.choice(product_pool)
                quantity = max(
                    1,
                    round(
                        rng.randint(3, 15)
                        * seasonality
                        * params.demand_multiplier
                    ),
                )
                base_discount = rng.choice((0, 100, 200, 300))
                discount_bps = min(
                    9_000,
                    base_discount
                    + (
                        params.key_customer_discount_increment_bps
                        if is_key_customer
                        else 0
                    ),
                )
                order_day = rng.randint(1, 18)
                order_date = self._period_date(period, order_day)
                order_event = emit(
                    "sales_order",
                    order_date,
                    period,
                    counterparty_id=customer_id,
                    product_id=product["product_id"],
                    quantity=quantity,
                    unit_price_cents=product["sale_price"],
                    attributes={"discount_rate_bps": discount_bps},
                )
                delivery_date = order_date + timedelta(days=rng.randint(2, 10))
                delivery_event = emit(
                    "sales_delivery",
                    delivery_date,
                    period,
                    counterparty_id=customer_id,
                    product_id=product["product_id"],
                    quantity=quantity,
                    unit_price_cents=round(
                        product["unit_cost"]
                        * (
                            1.0
                            + (
                                params.core_material_purchase_price_multiplier
                                - 1.0
                            )
                            * 0.36
                            if product["product_line"] == "CORE"
                            else 1.0
                        )
                    ),
                    attributes={"sales_order_event_id": order_event},
                )
                invoice_date = delivery_date + timedelta(days=rng.randint(0, 3))
                invoice_event = emit(
                    "sales_invoice",
                    invoice_date,
                    period,
                    counterparty_id=customer_id,
                    product_id=product["product_id"],
                    quantity=quantity,
                    unit_price_cents=product["sale_price"],
                    attributes={
                        "sales_delivery_event_id": delivery_event,
                        "discount_rate_bps": discount_bps,
                    },
                )
                emit(
                    "cash_receipt",
                    invoice_date
                    + timedelta(days=credit_term + rng.randint(-3, 12)),
                    period,
                    counterparty_id=customer_id,
                    product_id=product["product_id"],
                    quantity=quantity,
                    unit_price_cents=product["sale_price"],
                    attributes={
                        "sales_invoice_event_id": invoice_event,
                        "discount_rate_bps": discount_bps,
                    },
                )

        return tuple(events)

    @staticmethod
    def _period_date(period: str, day: int) -> date:
        year, month = (int(value) for value in period.split("-"))
        return date(year, month, min(day, calendar.monthrange(year, month)[1]))
