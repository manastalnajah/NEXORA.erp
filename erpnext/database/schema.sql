-- database/schema.sql
PRAGMA foreign_keys = ON;

-- 1. الهيكل المؤسسي وشجرة الحسابات
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
    company_id TEXT REFERENCES companies(id) ON DELETE CASCADE,
    year TEXT NOT NULL,
    year_start_date TEXT NOT NULL,
    year_end_date TEXT NOT NULL,
    is_closed INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    account_number TEXT,
    company_id TEXT REFERENCES companies(id) ON DELETE CASCADE,
    root_type TEXT NOT NULL,
    account_type TEXT,
    parent_account_id TEXT REFERENCES accounts(id),
    is_group INTEGER DEFAULT 0,
    currency TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS cost_centers (
    id TEXT PRIMARY KEY,
    cost_center_name TEXT NOT NULL,
    company_id TEXT REFERENCES companies(id) ON DELETE CASCADE,
    parent_cost_center_id TEXT REFERENCES cost_centers(id),
    is_group INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS parties (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    party_type TEXT NOT NULL,
    currency TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

-- 2. القيود ودفتر الأستاذ العام
CREATE TABLE IF NOT EXISTS journal_entries (
    id TEXT PRIMARY KEY,
    voucher_no TEXT NOT NULL UNIQUE,
    company_id TEXT REFERENCES companies(id) ON DELETE CASCADE,
    posting_date TEXT NOT NULL,
    voucher_type TEXT NOT NULL DEFAULT 'Journal Entry',
    total_debit REAL NOT NULL DEFAULT 0,
    total_credit REAL NOT NULL DEFAULT 0,
    docstatus INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS journal_entry_lines (
    id TEXT PRIMARY KEY,
    journal_entry_id TEXT REFERENCES journal_entries(id) ON DELETE CASCADE,
    account_id TEXT REFERENCES accounts(id) NOT NULL,
    party_id TEXT REFERENCES parties(id),
    cost_center_id TEXT REFERENCES cost_centers(id),
    debit REAL DEFAULT 0,
    credit REAL DEFAULT 0,
    user_remark TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS gl_entries (
    id TEXT PRIMARY KEY,
    company_id TEXT REFERENCES companies(id) ON DELETE CASCADE,
    posting_date TEXT NOT NULL,
    account_id TEXT REFERENCES accounts(id) NOT NULL,
    party_id TEXT REFERENCES parties(id),
    cost_center_id TEXT REFERENCES cost_centers(id),
    debit REAL DEFAULT 0,
    credit REAL DEFAULT 0,
    voucher_type TEXT NOT NULL,
    voucher_no TEXT NOT NULL,
    is_cancelled INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

-- 3. العمليات البنكية
CREATE TABLE IF NOT EXISTS bank_accounts (
    id TEXT PRIMARY KEY,
    account_name TEXT NOT NULL,
    bank_name TEXT NOT NULL,
    account_id TEXT REFERENCES accounts(id),
    company_id TEXT REFERENCES companies(id) ON DELETE CASCADE,
    iban TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS bank_transactions (
    id TEXT PRIMARY KEY,
    bank_account_id TEXT REFERENCES bank_accounts(id) ON DELETE CASCADE,
    date TEXT NOT NULL,
    description TEXT,
    debit REAL DEFAULT 0,
    credit REAL DEFAULT 0,
    unallocated_amount REAL DEFAULT 0,
    reference_number TEXT,
    reconciled INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS bank_transaction_payments (
    id TEXT PRIMARY KEY,
    bank_transaction_id TEXT REFERENCES bank_transactions(id) ON DELETE CASCADE,
    payment_document_type TEXT NOT NULL,
    payment_document_no TEXT NOT NULL,
    allocated_amount REAL NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

-- 4. المدفوعات والذمم والترقيم
CREATE TABLE IF NOT EXISTS payment_entries (
    id TEXT PRIMARY KEY,
    voucher_no TEXT NOT NULL UNIQUE,
    company_id TEXT REFERENCES companies(id) ON DELETE CASCADE,
    payment_type TEXT NOT NULL,
    posting_date TEXT NOT NULL,
    party_type TEXT,
    party_id TEXT REFERENCES parties(id),
    paid_from_account_id TEXT REFERENCES accounts(id) NOT NULL,
    paid_to_account_id TEXT REFERENCES accounts(id) NOT NULL,
    paid_amount REAL NOT NULL,
    received_amount REAL NOT NULL,
    docstatus INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS payment_entry_references (
    id TEXT PRIMARY KEY,
    payment_entry_id TEXT REFERENCES payment_entries(id) ON DELETE CASCADE,
    reference_doctype TEXT NOT NULL,
    reference_name TEXT NOT NULL,
    allocated_amount REAL NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS payment_ledger_entries (
    id TEXT PRIMARY KEY,
    company_id TEXT REFERENCES companies(id) ON DELETE CASCADE,
    posting_date TEXT NOT NULL,
    due_date TEXT,
    account_type TEXT NOT NULL,
    account_id TEXT REFERENCES accounts(id) NOT NULL,
    party_type TEXT NOT NULL,
    party_id TEXT REFERENCES parties(id) NOT NULL,
    voucher_type TEXT NOT NULL,
    voucher_no TEXT NOT NULL,
    against_voucher_type TEXT,
    against_voucher_no TEXT,
    amount REAL NOT NULL,
    amount_in_account_currency REAL NOT NULL,
    currency TEXT NOT NULL,
    delinked INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS series_counters (
    prefix TEXT PRIMARY KEY,
    current_val INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT DEFAULT (datetime('now'))
);

-- 5. فواتير المبيعات والمشتريات
CREATE TABLE IF NOT EXISTS sales_invoices (
    id TEXT PRIMARY KEY,
    voucher_no TEXT NOT NULL UNIQUE,
    company_id TEXT REFERENCES companies(id) ON DELETE CASCADE,
    posting_date TEXT NOT NULL,
    due_date TEXT,
    customer_id TEXT REFERENCES parties(id) NOT NULL,
    debit_to_account_id TEXT REFERENCES accounts(id) NOT NULL,
    net_total REAL NOT NULL DEFAULT 0,
    grand_total REAL NOT NULL DEFAULT 0,
    outstanding_amount REAL NOT NULL DEFAULT 0,
    docstatus INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sales_invoice_items (
    id TEXT PRIMARY KEY,
    sales_invoice_id TEXT REFERENCES sales_invoices(id) ON DELETE CASCADE,
    item_name TEXT NOT NULL,
    income_account_id TEXT REFERENCES accounts(id) NOT NULL,
    cost_center_id TEXT REFERENCES cost_centers(id),
    qty REAL NOT NULL DEFAULT 1,
    rate REAL NOT NULL DEFAULT 0,
    amount REAL NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS purchase_invoices (
    id TEXT PRIMARY KEY,
    voucher_no TEXT NOT NULL UNIQUE,
    company_id TEXT REFERENCES companies(id) ON DELETE CASCADE,
    posting_date TEXT NOT NULL,
    due_date TEXT,
    supplier_id TEXT REFERENCES parties(id) NOT NULL,
    credit_to_account_id TEXT REFERENCES accounts(id) NOT NULL,
    net_total REAL NOT NULL DEFAULT 0,
    grand_total REAL NOT NULL DEFAULT 0,
    outstanding_amount REAL NOT NULL DEFAULT 0,
    docstatus INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS purchase_invoice_items (
    id TEXT PRIMARY KEY,
    purchase_invoice_id TEXT REFERENCES purchase_invoices(id) ON DELETE CASCADE,
    item_name TEXT NOT NULL,
    expense_account_id TEXT REFERENCES accounts(id) NOT NULL,
    cost_center_id TEXT REFERENCES cost_centers(id),
    qty REAL NOT NULL DEFAULT 1,
    rate REAL NOT NULL DEFAULT 0,
    amount REAL NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

-- 6. الأصول ونقاط البيع
CREATE TABLE IF NOT EXISTS pos_profiles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    company_id TEXT REFERENCES companies(id) ON DELETE CASCADE,
    income_account_id TEXT REFERENCES accounts(id),
    currency TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS assets (
    id TEXT PRIMARY KEY,
    asset_name TEXT NOT NULL,
    company_id TEXT REFERENCES companies(id) ON DELETE CASCADE,
    gross_purchase_amount REAL NOT NULL,
    purchase_date TEXT NOT NULL,
    status TEXT DEFAULT 'Draft',
    docstatus INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

-- فهارس الأداء
CREATE INDEX IF NOT EXISTS idx_gle_acc ON gl_entries(account_id);
CREATE INDEX IF NOT EXISTS idx_gle_date ON gl_entries(posting_date);
CREATE INDEX IF NOT EXISTS idx_ple_party ON payment_ledger_entries(party_type, party_id);
