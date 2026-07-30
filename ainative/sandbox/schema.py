from __future__ import annotations

import sqlite3
from pathlib import Path


PUBLISHED_TABLES = (
    "dim_organization",
    "dim_customer",
    "dim_supplier",
    "dim_product",
    "dim_account",
    "fact_sales_order",
    "fact_sales_delivery",
    "fact_sales_invoice",
    "fact_cash_receipt",
    "fact_purchase_order",
    "fact_goods_receipt",
    "fact_supplier_invoice",
    "fact_cash_payment",
    "fact_inventory_movement",
    "fact_journal_entry",
)


SCHEMA_SQL = """
create table dim_organization (
    organization_id text primary key,
    organization_name text not null,
    organization_type text not null,
    parent_organization_id text references dim_organization(organization_id)
);

create table dim_customer (
    customer_id text primary key,
    customer_name text not null,
    region_id text not null references dim_organization(organization_id),
    customer_tier text not null,
    credit_term_days integer not null check (credit_term_days > 0),
    is_key_customer integer not null check (is_key_customer in (0, 1))
);

create table dim_supplier (
    supplier_id text primary key,
    supplier_name text not null,
    supplier_category text not null,
    credit_term_days integer not null check (credit_term_days > 0)
);

create table dim_product (
    product_id text primary key,
    product_name text not null,
    product_line text not null check (product_line in ('CORE', 'VALUE')),
    base_sale_price_cents integer not null check (base_sale_price_cents > 0),
    base_unit_cost_cents integer not null check (base_unit_cost_cents > 0),
    preferred_supplier_id text not null references dim_supplier(supplier_id)
);

create table dim_account (
    account_id text primary key,
    account_name text not null,
    account_type text not null
);

create table fact_sales_order (
    order_line_id text primary key,
    order_id text not null,
    order_date text not null,
    period text not null,
    organization_id text not null references dim_organization(organization_id),
    region_id text not null references dim_organization(organization_id),
    customer_id text not null references dim_customer(customer_id),
    product_id text not null references dim_product(product_id),
    quantity integer not null check (quantity > 0),
    unit_price_cents integer not null check (unit_price_cents >= 0),
    discount_rate_bps integer not null check (discount_rate_bps between 0 and 10000),
    net_amount_cents integer not null check (net_amount_cents >= 0),
    source_event_id text not null
);

create table fact_sales_delivery (
    delivery_line_id text primary key,
    delivery_id text not null,
    order_line_id text not null references fact_sales_order(order_line_id),
    delivery_date text not null,
    period text not null,
    product_id text not null references dim_product(product_id),
    quantity integer not null check (quantity > 0),
    unit_cost_cents integer not null check (unit_cost_cents >= 0),
    source_event_id text not null
);

create table fact_sales_invoice (
    invoice_line_id text primary key,
    invoice_id text not null,
    delivery_line_id text not null references fact_sales_delivery(delivery_line_id),
    invoice_date text not null,
    period text not null,
    customer_id text not null references dim_customer(customer_id),
    product_id text not null references dim_product(product_id),
    quantity integer not null check (quantity > 0),
    revenue_cents integer not null check (revenue_cents >= 0),
    due_date text not null,
    source_event_id text not null
);

create table fact_cash_receipt (
    receipt_id text primary key,
    invoice_id text not null,
    receipt_date text not null,
    period text not null,
    customer_id text not null references dim_customer(customer_id),
    amount_cents integer not null check (amount_cents >= 0),
    source_event_id text not null
);

create table fact_purchase_order (
    po_line_id text primary key,
    po_id text not null,
    order_date text not null,
    period text not null,
    supplier_id text not null references dim_supplier(supplier_id),
    product_id text not null references dim_product(product_id),
    quantity integer not null check (quantity > 0),
    unit_price_cents integer not null check (unit_price_cents >= 0),
    source_event_id text not null
);

create table fact_goods_receipt (
    gr_line_id text primary key,
    gr_id text not null,
    po_line_id text not null references fact_purchase_order(po_line_id),
    receipt_date text not null,
    period text not null,
    supplier_id text not null references dim_supplier(supplier_id),
    product_id text not null references dim_product(product_id),
    quantity integer not null check (quantity > 0),
    unit_price_cents integer not null check (unit_price_cents >= 0),
    source_event_id text not null
);

create table fact_supplier_invoice (
    ap_invoice_id text primary key,
    gr_line_id text not null references fact_goods_receipt(gr_line_id),
    invoice_date text not null,
    period text not null,
    supplier_id text not null references dim_supplier(supplier_id),
    amount_cents integer not null check (amount_cents >= 0),
    due_date text not null,
    source_event_id text not null
);

create table fact_cash_payment (
    payment_id text primary key,
    ap_invoice_id text not null references fact_supplier_invoice(ap_invoice_id),
    payment_date text not null,
    period text not null,
    supplier_id text not null references dim_supplier(supplier_id),
    amount_cents integer not null check (amount_cents >= 0),
    source_event_id text not null
);

create table fact_inventory_movement (
    movement_id text primary key,
    movement_date text not null,
    period text not null,
    product_id text not null references dim_product(product_id),
    movement_type text not null,
    quantity integer not null,
    unit_cost_cents integer not null check (unit_cost_cents >= 0),
    source_document_type text not null,
    source_document_id text not null,
    source_event_id text not null
);

create table fact_journal_entry (
    entry_line_id text primary key,
    voucher_id text not null,
    posting_date text not null,
    period text not null,
    account_id text not null references dim_account(account_id),
    debit_cents integer not null default 0 check (debit_cents >= 0),
    credit_cents integer not null default 0 check (credit_cents >= 0),
    source_document_type text not null,
    source_document_id text not null,
    source_event_id text not null,
    check ((debit_cents = 0) <> (credit_cents = 0))
);
"""


def create_database(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("pragma foreign_keys = on")
    conn.executescript(SCHEMA_SQL)
    return conn
