#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NEXORA ERP - Master Database Generator (Offline-First Engine)
يقوم هذا السكربت بإنشاء وتهيئة ملف قاعدة البيانات المحلية nexora_master.db
وفق معايير Frappe / ERPNext المحاسبية بدقة متناهية.
"""

import os
import sqlite3
import sys

# تحديد المسارات
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "database")
DB_PATH = os.path.join(DB_DIR, "nexora_master.db")

# أوامر SQL الشاملة للجداول الـ 21 ومحركات الحسابات
MASTER_SCHEMA_SQL = """
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- =========================================================================
-- 1. الهيكل المؤسسي وشجرة الحسابات (Company & Chart of Accounts)
-- =========================================================================
CREATE TABLE IF NOT EXISTS companies (
    id TEXT PRIMARY KEY,
    company_name TEXT NOT NULL UNIQUE,
    abbr TEXT NOT NULL UNIQUE,
    default_currency TEXT NOT NULL,
    country TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS fiscal_years (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    year TEXT NOT NULL,
    year_start_date TEXT NOT NULL,
    year_end_date TEXT NOT NULL,
    is_closed INTEGER DEFAULT 0 CHECK (is_closed IN (0, 1)),
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    account_number TEXT,
    company_id TEXT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    root_type TEXT NOT NULL CHECK (root_type IN ('Asset', 'Liability', 'Equity', 'Income', 'Expense')),
    account_type TEXT,
    parent_account_id TEXT REFERENCES accounts(id),
    is_group INTEGER DEFAULT 0 CHECK (is_group IN (0, 1)),
    currency TEXT NOT NULL,
    lft INTEGER DEFAULT 0,
    rgt INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS cost_centers (
    id TEXT PRIMARY KEY,
    cost_center_name TEXT NOT NULL,
    company_id TEXT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    parent_cost_center_id TEXT REFERENCES cost_centers(id),
    is_group INTEGER DEFAULT 0 CHECK (is_group IN (0, 1)),
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS parties (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    party_type TEXT NOT NULL CHECK (party_type IN ('Customer', 'Supplier', 'Employee')),
    currency TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

-- =========================================================================
-- 2. القيود اليومية ودفتر الأستاذ العام (General Ledger & Journal Entries)
-- =========================================================================
CREATE TABLE IF NOT EXISTS journal_entries (
    id TEXT PRIMARY KEY,
    voucher_no TEXT NOT NULL UNIQUE,
    company_id TEXT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    posting_date TEXT NOT NULL,
    voucher_type TEXT NOT NULL DEFAULT 'Journal Entry',
    total_debit REAL NOT NULL DEFAULT 0,
    total_credit REAL NOT NULL DEFAULT 0,
    docstatus INTEGER DEFAULT 0 CHECK (docstatus IN (0, 1, 2)),
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS journal_entry_lines (
    id TEXT PRIMARY KEY,
    journal_entry_id TEXT NOT NULL REFERENCES journal_entries(id) ON DELETE CASCADE,
    account_id TEXT NOT NULL REFERENCES accounts(id),
    party_id TEXT REFERENCES parties(id),
    cost_center_id TEXT REFERENCES cost_centers(id),
    debit REAL DEFAULT 0,
    credit REAL DEFAULT 0,
    user_remark TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS gl_entries (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    posting_date TEXT NOT NULL,
    account_id TEXT NOT NULL REFERENCES accounts(id),
    party_id TEXT REFERENCES parties(id),
    cost_center_id TEXT REFERENCES cost_centers(id),
    debit REAL DEFAULT 0,
    credit REAL DEFAULT 0,
    voucher_type TEXT NOT NULL,
    voucher_no TEXT NOT NULL,
    is_cancelled INTEGER DEFAULT 0 CHECK (is_cancelled IN (0, 1)),
    created_at TEXT DEFAULT (datetime('now'))
);

-- =========================================================================
-- 3. العمليات البنكية والمطابقة (Banking & Bank Reconciliation)
-- =========================================================================
CREATE TABLE IF NOT EXISTS bank_accounts (
    id TEXT PRIMARY KEY,
    account_name TEXT NOT NULL,
    bank_name TEXT NOT NULL,
    account_id TEXT NOT NULL REFERENCES accounts(id),
    company_id TEXT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    iban TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS bank_transactions (
    id TEXT PRIMARY KEY,
    bank_account_id TEXT NOT NULL REFERENCES bank_accounts(id) ON DELETE CASCADE,
    date TEXT NOT NULL,
    description TEXT,
    debit REAL DEFAULT 0,
    credit REAL DEFAULT 0,
    unallocated_amount REAL DEFAULT 0,
    reference_number TEXT,
    reconciled INTEGER DEFAULT 0 CHECK (reconciled IN (0, 1)),
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS bank_transaction_payments (
    id TEXT PRIMARY KEY,
    bank_transaction_id TEXT NOT NULL REFERENCES bank_transactions(id) ON DELETE CASCADE,
    payment_document_type TEXT NOT NULL,
    payment_document_no TEXT NOT NULL,
    allocated_amount REAL NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

-- =========================================================================
-- 4. سندات القبض والصرف وسجل الدفع والترقيم (Payments & Aging Engine)
-- =========================================================================
CREATE TABLE IF NOT EXISTS payment_entries (
    id TEXT PRIMARY KEY,
    voucher_no TEXT NOT NULL UNIQUE,
    company_id TEXT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    payment_type TEXT NOT NULL CHECK (payment_type IN ('Receive', 'Pay', 'Internal Transfer')),
    posting_date TEXT NOT NULL,
    party_type TEXT CHECK (party_type IN ('Customer', 'Supplier', 'Employee')),
    party_id TEXT REFERENCES parties(id),
    paid_from_account_id TEXT NOT NULL REFERENCES accounts(id),
    paid_to_account_id TEXT NOT NULL REFERENCES accounts(id),
    paid_amount REAL NOT NULL,
    received_amount REAL NOT NULL,
    docstatus INTEGER DEFAULT 0 CHECK (docstatus IN (0, 1, 2)),
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS payment_entry_references (
    id TEXT PRIMARY KEY,
    payment_entry_id TEXT NOT NULL REFERENCES payment_entries(id) ON DELETE CASCADE,
    reference_doctype TEXT NOT NULL,
    reference_name TEXT NOT NULL,
    allocated_amount REAL NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS payment_ledger_entries (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    posting_date TEXT NOT NULL,
    due_date TEXT,
    account_type TEXT NOT NULL CHECK (account_type IN ('Receivable', 'Payable')),
    account_id TEXT NOT NULL REFERENCES accounts(id),
    party_type TEXT NOT NULL CHECK (party_type IN ('Customer', 'Supplier', 'Employee')),
    party_id TEXT NOT NULL REFERENCES parties(id),
    voucher_type TEXT NOT NULL,
    voucher_no TEXT NOT NULL,
    against_voucher_type TEXT,
    against_voucher_no TEXT,
    amount REAL NOT NULL,
    amount_in_account_currency REAL NOT NULL,
    currency TEXT NOT NULL,
    delinked INTEGER DEFAULT 0 CHECK (delinked IN (0, 1)),
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS series_counters (
    prefix TEXT PRIMARY KEY,
    current_val INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT DEFAULT (datetime('now'))
);

-- =========================================================================
-- 5. فواتير المبيعات والمشتريات (Sales & Purchase Invoices)
-- =========================================================================
CREATE TABLE IF NOT EXISTS sales_invoices (
    id TEXT PRIMARY KEY,
    voucher_no TEXT NOT NULL UNIQUE,
    company_id TEXT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    posting_date TEXT NOT NULL,
    due_date TEXT,
    customer_id TEXT NOT NULL REFERENCES parties(id),
    debit_to_account_id TEXT NOT NULL REFERENCES accounts(id),
    net_total REAL NOT NULL DEFAULT 0,
    grand_total REAL NOT NULL DEFAULT 0,
    outstanding_amount REAL NOT NULL DEFAULT 0,
    docstatus INTEGER DEFAULT 0 CHECK (docstatus IN (0, 1, 2)),
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sales_invoice_items (
    id TEXT PRIMARY KEY,
    sales_invoice_id TEXT NOT NULL REFERENCES sales_invoices(id) ON DELETE CASCADE,
    item_name TEXT NOT NULL,
    income_account_id TEXT NOT NULL REFERENCES accounts(id),
    cost_center_id TEXT REFERENCES cost_centers(id),
    qty REAL NOT NULL DEFAULT 1,
    rate REAL NOT NULL DEFAULT 0,
    amount REAL NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS purchase_invoices (
    id TEXT PRIMARY KEY,
    voucher_no TEXT NOT NULL UNIQUE,
    company_id TEXT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    posting_date TEXT NOT NULL,
    due_date TEXT,
    supplier_id TEXT NOT NULL REFERENCES parties(id),
    credit_to_account_id TEXT NOT NULL REFERENCES accounts(id),
    net_total REAL NOT NULL DEFAULT 0,
    grand_total REAL NOT NULL DEFAULT 0,
    outstanding_amount REAL NOT NULL DEFAULT 0,
    docstatus INTEGER DEFAULT 0 CHECK (docstatus IN (0, 1, 2)),
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS purchase_invoice_items (
    id TEXT PRIMARY KEY,
    purchase_invoice_id TEXT NOT NULL REFERENCES purchase_invoices(id) ON DELETE CASCADE,
    item_name TEXT NOT NULL,
    expense_account_id TEXT NOT NULL REFERENCES accounts(id),
    cost_center_id TEXT REFERENCES cost_centers(id),
    qty REAL NOT NULL DEFAULT 1,
    rate REAL NOT NULL DEFAULT 0,
    amount REAL NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

-- =========================================================================
-- 6. نقاط البيع وإدارة الأصول والإهلاك (POS & Assets Engine)
-- =========================================================================
CREATE TABLE IF NOT EXISTS pos_profiles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    company_id TEXT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    income_account_id TEXT REFERENCES accounts(id),
    currency TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS pos_closing_entries (
    id TEXT PRIMARY KEY,
    period_start_date TEXT NOT NULL,
    period_end_date TEXT NOT NULL,
    pos_profile_id TEXT NOT NULL REFERENCES pos_profiles(id),
    grand_total REAL DEFAULT 0,
    net_total REAL DEFAULT 0,
    docstatus INTEGER DEFAULT 0 CHECK (docstatus IN (0, 1, 2)),
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS asset_categories (
    id TEXT PRIMARY KEY,
    category_name TEXT NOT NULL,
    fixed_asset_account_id TEXT REFERENCES accounts(id),
    accumulated_depreciation_account_id TEXT REFERENCES accounts(id),
    depreciation_expense_account_id TEXT REFERENCES accounts(id),
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS assets (
    id TEXT PRIMARY KEY,
    asset_name TEXT NOT NULL,
    asset_category_id TEXT REFERENCES asset_categories(id),
    company_id TEXT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    gross_purchase_amount REAL NOT NULL,
    purchase_date TEXT NOT NULL,
    status TEXT DEFAULT 'Draft',
    docstatus INTEGER DEFAULT 0 CHECK (docstatus IN (0, 1, 2)),
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS depreciation_schedules (
    id TEXT PRIMARY KEY,
    asset_id TEXT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    schedule_date TEXT NOT NULL,
    depreciation_amount REAL NOT NULL,
    accumulated_depreciation_amount REAL NOT NULL,
    journal_entry_id TEXT REFERENCES journal_entries(id),
    created_at TEXT DEFAULT (datetime('now'))
);

-- =========================================================================
-- 7. فهارس تسريع الاستعلامات (Performance Indexes)
-- =========================================================================
CREATE INDEX IF NOT EXISTS idx_gle_acc ON gl_entries(account_id);
CREATE INDEX IF NOT EXISTS idx_gle_date ON gl_entries(posting_date);
CREATE INDEX IF NOT EXISTS idx_gle_voucher ON gl_entries(voucher_type, voucher_no);
CREATE INDEX IF NOT EXISTS idx_ple_party ON payment_ledger_entries(party_type, party_id);
CREATE INDEX IF NOT EXISTS idx_ple_voucher ON payment_ledger_entries(voucher_type, voucher_no);
CREATE INDEX IF NOT EXISTS idx_acc_parent ON accounts(parent_account_id);
CREATE INDEX IF NOT EXISTS idx_sinv_cust ON sales_invoices(customer_id);
CREATE INDEX IF NOT EXISTS idx_pinv_supp ON purchase_invoices(supplier_id);

-- =========================================================================
-- 8. مشغلات الحماية المحاسبية (Accounting Integrity Triggers)
-- =========================================================================
-- منع ترحيل القيد إذا لم يتساوَ مجموع المدين والدائن
CREATE TRIGGER IF NOT EXISTS trg_validate_journal_balance
BEFORE UPDATE OF docstatus ON journal_entries
FOR EACH ROW
WHEN NEW.docstatus = 1
BEGIN
    SELECT CASE
        WHEN ABS(NEW.total_debit - NEW.total_credit) > 0.001 THEN
            RAISE(ABORT, 'لا يمكن اعتماد القيد: إجمالي المدين لا يتطابق مع إجمالي الدائن!')
    END;
END;
"""

def generate_database():
    """تنفيذ بناء ملف قاعدة البيانات الرئيسي"""
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR, exist_ok=True)

    print(f"[*] جاري إنشاء ملف قاعدة البيانات: {DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.executescript(MASTER_SCHEMA_SQL)
        conn.commit()
        print("[✓] تم بنجاح إنشاء ملف nexora_master.db وبناء الجداول الـ 21 وكافة الفهارس ومشغلات الأمان!")
    except Exception as e:
        print(f"[!] خطأ أثناء إنشاء الجداول: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    generate_database()
