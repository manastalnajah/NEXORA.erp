import { createClient } from '@supabase/supabase-js';

// قراءة بيانات الاتصال بـ Supabase من ملف البيئة
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || '';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || '';

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

// خريطة مطابقة الكيانات إلى الجداول التي أنشأناها في Supabase
const tableMap: Record<string, string> = {
  'Bank Account': 'bank_accounts',
  'Bank Transaction': 'bank_transactions',
  'Bank Transaction Payments': 'bank_transaction_payments',
  'Payment Entry': 'payment_entries',
  'Payment Entry Reference': 'payment_entry_references',
  'Journal Entry': 'journal_entries',
  'Journal Entry Account': 'journal_entry_lines',
  'GL Entry': 'gl_entries',
  'Sales Invoice': 'sales_invoices',
  'Sales Invoice Item': 'sales_invoice_items',
  'Purchase Invoice': 'purchase_invoices',
  'Purchase Invoice Item': 'purchase_invoice_items',
  'Company': 'companies',
  'Fiscal Year': 'fiscal_years',
  'Account': 'accounts',
  'Party': 'parties',
  'Cost Center': 'cost_centers',
  'Asset': 'assets',
  'Asset Category': 'asset_categories'
};

function getTableName(doctype: string): string {
  return tableMap[doctype] || doctype.toLowerCase().replace(/ /g, '_');
}

/**
 * كائن المحاكاة frappe: 
 * يمنح الواجهات نفس الوظائف تماماً ولكن يتصل مباشرة بـ Supabase
 */
export const frappe = {
  db: {
    // 1. جلب قائمة السجلات
    async getDocList(doctype: string, args: any = {}) {
      const tableName = getTableName(doctype);
      const fields = args.fields && Array.isArray(args.fields) ? args.fields.join(',') : '*';
      let query = supabase.from(tableName).select(fields);

      if (args.filters) {
        if (Array.isArray(args.filters)) {
          args.filters.forEach(([_, field, op, val]: any) => {
            if (op === '=') query = query.eq(field, val);
            else if (op === '!=') query = query.neq(field, val);
            else if (op === 'like') query = query.ilike(field, val.replace(/%/g, '%'));
            else if (op === 'in') query = query.in(field, Array.isArray(val) ? val : [val]);
            else if (op === '>=') query = query.gte(field, val);
            else if (op === '<=') query = query.lte(field, val);
          });
        } else if (typeof args.filters === 'object') {
          Object.entries(args.filters).forEach(([key, val]: any) => {
            if (Array.isArray(val)) query = query.in(key, val);
            else query = query.eq(key, val);
          });
        }
      }

      if (args.order_by) {
        const [col, dir] = args.order_by.split(' ');
        query = query.order(col, { ascending: dir?.toLowerCase() !== 'desc' });
      }

      if (args.limit) {
        query = query.limit(args.limit);
      }

      const { data, error } = await query;
      if (error) throw error;
      return data;
    },

    // 2. جلب مستند واحد
    async getDoc(doctype: string, name: string) {
      const tableName = getTableName(doctype);
      const { data, error } = await supabase
        .from(tableName)
        .select('*')
        .or(`id.eq.${name},voucher_no.eq.${name}`)
        .single();

      if (error) throw error;
      return data;
    },

    // 3. إنشاء مستند جديد
    async createDoc(doctype: string, payload: any) {
      const tableName = getTableName(doctype);
      const { data, error } = await supabase
        .from(tableName)
        .insert(payload)
        .select()
        .single();

      if (error) throw error;
      return data;
    },

    // 4. تعديل مستند
    async updateDoc(doctype: string, name: string, updates: any) {
      const tableName = getTableName(doctype);
      const { data, error } = await supabase
        .from(tableName)
        .update(updates)
        .or(`id.eq.${name},voucher_no.eq.${name}`)
        .select()
        .single();

      if (error) throw error;
      return data;
    },

    // 5. حذف مستند
    async deleteDoc(doctype: string, name: string) {
      const tableName = getTableName(doctype);
      const { error } = await supabase
        .from(tableName)
        .delete()
        .or(`id.eq.${name},voucher_no.eq.${name}`);

      if (error) throw error;
      return true;
    }
  },

  // استدعاء الدوال الحسابية المباشرة في الداتابيس (RPC)
  async call(method: string, args: any = {}) {
    const fnName = method.split('.').pop() || method;
    const { data, error } = await supabase.rpc(fnName, args);
    if (error) {
      console.warn(`RPC call [${fnName}] skipped:`, error.message);
      return { message: null };
    }
    return { message: data };
  }
};
