import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import api from '../../services/api'
import usePermissions from '../../hooks/usePermissions'
import AmountInput from '../../components/ui/AmountInput'
import JalaliDateInput from '../../components/ui/JalaliDateInput'
import SearchSelect from '../../components/ui/SearchSelect'
import { formatDate } from '../../utils/date'
import { jalaliToGregorian, gregorianToJalali, JALALI_MONTHS } from '../../utils/jalali'

function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }

const METHODS = [
  { value: 'transfer', label: 'واریز بانک' },
  { value: 'cash', label: 'نقدی' },
  { value: 'cheque', label: 'اسناد (چک)' },
  { value: 'discount', label: 'تخفیف' },
]

// حساب‌های صندوق/تنخواه — نقدی و اسناد فقط به این‌ها می‌روند؛ واریز بانک فقط به حساب‌های بانکی
const CASH_ACCOUNT_TYPES = ['cash', 'petty']

// انواع طرف حساب — فیلتر انتخاب طرف حساب در فرم پرداخت/دریافت
const CONTACT_TYPE_OPTIONS = [
  { value: '', label: 'همه' },
  { value: 'staff', label: 'کارمند / فروشنده' },
  { value: 'customer', label: 'مشتری' },
  { value: 'partner', label: 'همکار' },
  { value: 'supplier_cn', label: 'تامین‌کننده چینی' },
  { value: 'clearance', label: 'ترخیص‌کار' },
  { value: 'shipping_co', label: 'شرکت حمل' },
  { value: 'other', label: 'سایر' },
  // شبه‌نوع‌ها — نوع تماس واقعی نیستند؛ فقط حالت فرم را عوض می‌کنند (فیلتر contact_type ندارند)
  { value: 'expense', label: '➕ ثبت هزینه' },
  { value: 'investor', label: '💰 سرمایه‌گذار' },
]

// برچسب منبع هزینه باز — نمایش کنار عنوان در انتخابگر هزینه
const CHARGE_SOURCE_LABEL = { recurring: 'تکرارشونده', general: 'متفرقه', investor: 'سود مشارکت' }

// ─── فرم ثبت پرداخت/دریافت ───────────────────────────────────
export function PaymentForm({ direction, editing = null, onClose, onSuccess }) {
  const isReceive = direction === 'in'
  const qc = useQueryClient()

  const { data: contacts = [] } = useQuery({
    queryKey: ['contacts-plain'],
    queryFn: () => api.get('/accounting/contacts/').then(r => r.data),
  })
  const { data: accounts = [] } = useQuery({
    queryKey: ['accounts'],
    queryFn: () => api.get('/accounting/accounts/').then(r => r.data),
  })

  const [form, setForm] = useState({
    contact_id: editing?.contact_id ?? '',
    contact_type: '',   // فیلتر نوع طرف حساب — هنگام ویرایش از روی آبجکت طرف حساب پر می‌شود
    from_account_id: editing?.from_account_id ?? '',
    to_account_id: editing?.to_account_id ?? '',
    payment_type: editing?.payment_type ?? 'transfer',
    currency: editing?.currency ?? 'IRR',
    amount: editing?.amount ?? '',
    rate_irr: editing?.rate_irr ?? '',
    account_amount: '',  // مبلغ برداشت/واریز به ارز حساب (فقط بین‌ارزی — دستی قابل تغییر)
    date: editing?.date ?? new Date().toISOString().split('T')[0],
    reference: editing?.reference ?? '',
    payslip_id: editing?.payslip_id ?? '',
    expense_charge_id: editing?.expense_charge_id ?? '',
    expense_category_id: editing?.expense_category_id ?? '',
    expense_title: editing?.expense_title ?? '',
    investor_mode: 'profit',   // فقط حالت سرمایه‌گذار: 'profit' | 'withdraw'
    note: editing?.note ?? '',
  })
  const [msg, setMsg] = useState(null)
  const [dupPayload, setDupPayload] = useState(null)   // تراکنشی که با هشدار تکراری (۴۰۹) رد شد
  // عملیات ارزی طرف حساب انتخاب‌شده — بدون فلگ، گزینه/فیلدهای یوانی نمایش داده نمی‌شوند
  const selectedContact = contacts.find(c => String(c.id) === String(form.contact_id))
  const contactHasFx = !selectedContact || selectedContact.has_fx !== false
  // حالت‌های شبه‌نوع — فقط در پرداخت ریالی معنی دارند؛ در دریافت مثل «همه» رفتار می‌شوند
  const pseudoType = !isReceive && form.currency === 'IRR' ? form.contact_type : ''
  const modeExpense = pseudoType === 'expense'
  const modeInvestor = pseudoType === 'investor'
  // فهرست سرمایه‌گذاران — پایه فیلتر طرف حساب در حالت سرمایه‌گذار
  const { data: investors = [] } = useQuery({
    queryKey: ['investors-list'],
    queryFn: () => api.get('/expenses/investors/').then(r => r.data),
    enabled: pseudoType === 'investor',
  })
  const investorContactIds = new Set(investors.map(i => String(i.contact)))
  // طرف حساب‌های مرتبط با سر فصل انتخاب‌شده (از هزینه‌های گذشته) — فیلتر انتخابگر طرف حساب در حالت ثبت هزینه
  const { data: categoryContacts = [], isFetched: categoryContactsFetched } = useQuery({
    queryKey: ['category-contacts', form.expense_category_id],
    queryFn: () => api.get(`/expenses/categories/${form.expense_category_id}/contacts/`).then(r => r.data),
    enabled: modeExpense && !!form.expense_category_id,
  })
  const categoryContactIds = new Set(categoryContacts.map(c => String(c.id)))
  // فهرست طرف حساب‌ها با اعمال فیلتر — نوع واقعی بر اساس contact_type؛ سرمایه‌گذار بر اساس فهرست سرمایه‌گذاران؛ ثبت هزینه بر اساس سر فصل انتخاب‌شده
  const filteredContacts = (() => {
    if (pseudoType === 'investor') return contacts.filter(c => investorContactIds.has(String(c.id)))
    if (pseudoType === 'expense') {
      return form.expense_category_id ? contacts.filter(c => categoryContactIds.has(String(c.id))) : contacts
    }
    if (pseudoType) return contacts.filter(c => c.contact_type === pseudoType)
    return contacts
  })()
  // در حالت ثبت هزینه، طرف حساب انتخاب‌شده باید زیر سر فصل انتخاب‌شده باشد؛ وگرنه پاک می‌شود (بعد از لود فهرست)
  useEffect(() => {
    if (modeExpense && form.expense_category_id && categoryContactsFetched && form.contact_id
      && !categoryContactIds.has(String(form.contact_id))) {
      setForm(f => ({ ...f, contact_id: '' }))
    }
  }, [modeExpense, form.expense_category_id, form.contact_id, categoryContactsFetched, categoryContactIds])
  // تغییر نوع/طرف حساب، حالت عملیات سرمایه‌گذار را به پیش‌فرض (سود) برمی‌گرداند
  useEffect(() => {
    setForm(f => (f.investor_mode === 'profit' ? f : { ...f, investor_mode: 'profit' }))
  }, [pseudoType, form.contact_id])
  // هنگام ویرایش، نوع طرف حساب از روی آبجکت contact (اگر لود شده) پر می‌شود
  useEffect(() => {
    if (editing && !form.contact_type && selectedContact) {
      setForm(f => ({ ...f, contact_type: selectedContact.contact_type || '' }))
    }
  }, [editing, selectedContact, form.contact_type])
  useEffect(() => {
    if (selectedContact && selectedContact.has_fx === false && form.currency === 'CNY') {
      setForm(f => ({ ...f, currency: 'IRR' }))
    }
  }, [selectedContact, form.currency])
  // فیش‌های حقوقی باز پرسنل — پرداخت ریالی به پرسنل را می‌توان به فیش حقوقی لینک کرد (ردیابی پرداخت جزئی)
  const isStaffContact = selectedContact?.contact_type === 'staff'
  const showPayslips = !isReceive && isStaffContact && form.currency === 'IRR' && !modeExpense && !modeInvestor
  const { data: openPayslips = [] } = useQuery({
    queryKey: ['open-payslips', form.contact_id],
    queryFn: () => api.get(`/payroll/payslips/open/?contact_id=${form.contact_id}`).then(r => r.data),
    enabled: showPayslips && !!form.contact_id,
  })
  // اگر فیلد باید مخفی باشد (دریافت / غیرپرسنل / غیرریالی / حالت ثبت هزینه یا سرمایه‌گذار) یا فیش انتخاب‌شده دیگر در فهرست نیست، مقدارش پاک می‌شود
  useEffect(() => {
    if (!showPayslips && form.payslip_id) {
      setForm(f => ({ ...f, payslip_id: '' }))
    }
  }, [showPayslips, form.payslip_id])
  useEffect(() => {
    if (showPayslips && form.payslip_id && !openPayslips.some(p => String(p.id) === String(form.payslip_id))) {
      setForm(f => ({ ...f, payslip_id: '' }))
    }
  }, [showPayslips, form.payslip_id, openPayslips])
  const selectedPayslip = openPayslips.find(p => String(p.id) === String(form.payslip_id))
  const payslipLabel = (p) => {
    const [jy, jm] = gregorianToJalali(p.year, p.month, 1)
    return `فیش ${JALALI_MONTHS[jm - 1]} ${jy.toLocaleString('fa-IR')} — مانده: ${fmt(p.remaining_amount)} ریال`
  }
  // هزینه‌های باز طرف حساب — در حالت ثبت هزینه مخفی؛ در حالت سرمایه‌گذار فقط برای پرداخت سود
  const showCharges = !isReceive && !!form.contact_id && form.currency === 'IRR' && !modeExpense && (!modeInvestor || form.investor_mode === 'profit')
  const { data: openCharges = [] } = useQuery({
    queryKey: ['open-expense-charges', form.contact_id],
    queryFn: () => api.get(`/expenses/charges/open/?contact_id=${form.contact_id}`).then(r => r.data),
    enabled: showCharges,
  })
  // پاک‌سازی هزینه — همان قواعد فیش: مخفی شدن فیلد یا نبودن گزینه در فهرست
  useEffect(() => {
    if (!showCharges && form.expense_charge_id) {
      setForm(f => ({ ...f, expense_charge_id: '' }))
    }
  }, [showCharges, form.expense_charge_id])
  useEffect(() => {
    if (showCharges && form.expense_charge_id && !openCharges.some(c => String(c.id) === String(form.expense_charge_id))) {
      setForm(f => ({ ...f, expense_charge_id: '' }))
    }
  }, [showCharges, form.expense_charge_id, openCharges])
  const selectedCharge = openCharges.find(c => String(c.id) === String(form.expense_charge_id))
  const chargeLabel = (c) => `[${CHARGE_SOURCE_LABEL[c.source] || c.source}] ${c.title} — مانده: ${fmt(c.remaining_amount)} ریال`
  // سر فصل هزینه متفرقه — فقط از مسیر حالت «ثبت هزینه»؛ پرداخت ریالی با ثبت همزمان هزینه پرداخت‌شده
  const showCategories = modeExpense
  const { data: expenseCategories = [] } = useQuery({
    queryKey: ['expense-categories'],
    queryFn: () => api.get('/expenses/categories/', { params: { type: 'general' } }).then(r => r.data),
  })
  // پاک‌سازی سر فصل — مخفی شدن فیلد یا نبودن گزینه در فهرست (عنوان هم همراهش پاک می‌شود)
  useEffect(() => {
    if (!showCategories && (form.expense_category_id || form.expense_title)) {
      setForm(f => ({ ...f, expense_category_id: '', expense_title: '' }))
    }
  }, [showCategories, form.expense_category_id, form.expense_title])
  useEffect(() => {
    if (showCategories && form.expense_category_id && !expenseCategories.some(c => String(c.id) === String(form.expense_category_id))) {
      setForm(f => ({ ...f, expense_category_id: '', expense_title: '' }))
    }
  }, [showCategories, form.expense_category_id, expenseCategories])
  const selectedCategory = expenseCategories.find(c => String(c.id) === String(form.expense_category_id))
  // ردیف‌های چک — برای روش «اسناد»؛ مبلغ تراکنش = مجموع مبالغ چک‌ها
  const [cheques, setCheques] = useState(
    editing?.cheques?.length ? editing.cheques : []
  )

  const isCash = form.payment_type === 'cash'
  const isCheque = form.payment_type === 'cheque'
  const isDiscount = form.payment_type === 'discount'
  // حالت اسناد در «پرداخت»: صدور چک از حساب جاری خودمان / واگذاری چک‌های موجود صندوق
  const [chequeMode, setChequeMode] = useState('issued')
  const [selectedChequeIds, setSelectedChequeIds] = useState([])
  // چک‌های موجود در صندوق انتخاب‌شده — برای واگذاری
  const pettyAccId = isReceive ? form.to_account_id : form.from_account_id
  const { data: availCheques = [] } = useQuery({
    queryKey: ['avail-cheques', pettyAccId],
    queryFn: () => api.get('/accounting/cheques/available/', { params: { account_id: pettyAccId } }).then(r => r.data),
    enabled: isCheque && !isReceive && chequeMode === 'endorse' && !!pettyAccId,
  })
  const selectedChequeTotal = availCheques
    .filter(ch => selectedChequeIds.includes(ch.id))
    .reduce((s, ch) => s + Number(ch.amount), 0)
  // فاکتورهای باز طرف حساب — برای لینک چک دریافتی به فاکتور مشخص (اختیاری)
  const { data: openInvoices = [] } = useQuery({
    queryKey: ['contact-open-invoices', form.contact_id],
    queryFn: () => api.get('/accounting/sale-invoices/', { params: { contact_id: form.contact_id } }).then(r => r.data),
    enabled: isCheque && isReceive && !!form.contact_id,
  })
  // نقدی و اسناد (دریافت/واگذاری) فقط صندوق؛ صدور چک فقط حساب جاری؛ واریز بانک فقط حساب بانکی
  const accountOptions = (() => {
    if (isCash) return accounts.filter(a => CASH_ACCOUNT_TYPES.includes(a.account_type))
    if (isCheque) {
      if (isReceive || chequeMode === 'endorse') return accounts.filter(a => CASH_ACCOUNT_TYPES.includes(a.account_type))
      return accounts.filter(a => a.account_type === 'bank')
    }
    return accounts.filter(a => !CASH_ACCOUNT_TYPES.includes(a.account_type))
  })()
  const chequeTotal = isCheque && !isReceive && chequeMode === 'endorse'
    ? selectedChequeTotal
    : cheques.reduce((s, c) => s + (Number(String(c.amount).replace(/[^\d]/g, '')) || 0), 0)

  // نرخ یوان مرجع روز — پیش‌پر کردن نرخ تبدیل برای پرداخت یوانی
  const { data: rateData } = useQuery({
    queryKey: ['exchange-rate'],
    queryFn: () => api.get('/catalog/exchange-rate/').then(r => r.data),
    staleTime: 60000,
  })
  useEffect(() => {
    if (!editing && form.currency === 'CNY' && rateData?.rate_cny_to_irt) {
      setForm(f => f.rate_irr ? f : { ...f, rate_irr: String(rateData.rate_cny_to_irt) })
    }
  }, [rateData, form.currency, editing])

  // حساب فعال در جریان (مبدا در پرداخت / مقصد در دریافت)
  const activeAccId = isReceive ? form.to_account_id : form.from_account_id
  const activeAcc = accounts.find(a => String(a.id) === String(activeAccId))
  const crossCurrency = !!(activeAcc && activeAcc.currency !== form.currency)

  // تبدیل دومسیره (الگوی Odoo/QuickBooks): مبلغ × نرخ = برداشت — تغییر هر یک بقیه را حساب می‌کند
  const computedDeduction = () => {
    const amt = Number(form.amount) || 0
    const rate = Number(form.rate_irr) || 0
    if (!crossCurrency || !amt || !rate) return ''
    return activeAcc.currency === 'IRR'
      ? String(Math.round(amt * rate))
      : String(Math.round((amt / rate) * 100) / 100)
  }
  const onAmountChange = (e) => setForm(f => ({ ...f, amount: e.target.value, account_amount: '' }))
  const onRateChange = (e) => setForm(f => ({ ...f, rate_irr: e.target.value, account_amount: '' }))
  const onDeductionChange = (e) => {
    const v = e.target.value
    const amt = Number(form.amount) || 0
    const ded = Number(v) || 0
    // نرخ از روی برداشت دستی برمی‌گردد محاسبه شود
    const newRate = amt > 0 && ded > 0
      ? (activeAcc.currency === 'IRR'
          ? String(Math.round(ded / amt))
          : String(Math.round((amt / ded) * 1000000) / 1000000))
      : form.rate_irr
    setForm(f => ({ ...f, account_amount: v, rate_irr: newRate }))
  }
  const deductionValue = form.account_amount !== '' ? form.account_amount : computedDeduction()

  const mut = useMutation({
    mutationFn: (d) => editing
      ? api.patch(`/accounting/payments/${editing.id}/`, d).then(r => r.data)
      : api.post('/accounting/payments/', d).then(r => r.data),
    onSuccess: (r) => {
      qc.invalidateQueries(['payments-list'])
      qc.invalidateQueries(['accounts'])
      qc.invalidateQueries(['contacts-all'])
      qc.invalidateQueries(['contact-kardex'])
      qc.invalidateQueries(['open-payslips'])
      qc.invalidateQueries(['open-expense-charges'])
      qc.invalidateQueries(['expenses-charges'])
      setDupPayload(null)
      // اگر دریافت به‌صورت خودکار به فاکتورهای باز مشتری تخصیص یافت، خلاصه‌اش را نشان بده
      let text = editing ? 'تراکنش به‌روز شد' : 'پرداخت ثبت شد'
      if (!editing && r?.fifo) {
        const parts = (r.allocated || []).map(a => `${Number(a.amount).toLocaleString('fa-IR')} ← فاکتور ${a.invoice_number}`)
        text = 'دریافت ثبت و تخصیص یافت'
        if (parts.length) text += ': ' + parts.join('، ')
        if (r.leftover > 0) text += ` — مازاد ${Number(r.leftover).toLocaleString('fa-IR')} ریال به بستانکاری مشتری رفت`
      }
      setMsg({ type: 'success', text })
      setTimeout(() => onSuccess?.(), r?.fifo ? 4000 : 800)
    },
    onError: (e) => {
      // 409 = احتمال ثبت تکراری — پی‌لود را نگه می‌داریم تا با «ثبت قطعی» دوباره ارسال شود
      if (e.response?.status === 409 && e.response?.data?.duplicate) {
        setDupPayload(e.config?.data ? JSON.parse(e.config.data) : null)
        setMsg({ type: 'error', text: e.response.data.error })
      } else {
        setMsg({ type: 'error', text: e.response?.data?.error || 'خطا' })
      }
    },
  })

  const isEndorseMode = isCheque && !isReceive && chequeMode === 'endorse'
  function handleSubmit() {
    // در حالت ثبت هزینه طرف حساب اختیاری است و سر فصل الزامی
    if (!modeExpense && !form.contact_id) return setMsg({ type: 'error', text: 'طرف حساب را انتخاب کنید' })
    if (modeExpense && !form.expense_category_id) return setMsg({ type: 'error', text: 'سر فصل هزینه را انتخاب کنید' })
    if (modeInvestor && form.investor_mode === 'profit' && !form.expense_charge_id) {
      return setMsg({ type: 'error', text: 'سود باز سرمایه‌گذار را انتخاب کنید' })
    }
    if (isCheque && !isEndorseMode) {
      if (!cheques.length) return setMsg({ type: 'error', text: 'حداقل یک چک اضافه کنید' })
      for (const ch of cheques) {
        if (!ch.serial_number?.trim()) return setMsg({ type: 'error', text: 'شماره چک همه ردیف‌ها الزامی است' })
        if (!ch.cheque_date) return setMsg({ type: 'error', text: 'تاریخ چک همه ردیف‌ها الزامی است' })
        if (!(Number(String(ch.amount).replace(/[^\d]/g, '')) > 0)) return setMsg({ type: 'error', text: 'مبلغ چک همه ردیف‌ها الزامی است' })
      }
      if (!chequeTotal) return setMsg({ type: 'error', text: 'مجموع مبلغ چک‌ها صفر است' })
    } else if (isEndorseMode) {
      if (!selectedChequeIds.length) return setMsg({ type: 'error', text: 'حداقل یک چک از اسناد صندوق انتخاب کنید' })
    } else if (!form.amount) {
      return setMsg({ type: 'error', text: 'مبلغ را وارد کنید' })
    }
    // تخفیف بدون حساب بانکی است؛ بقیه روش‌ها حساب می‌خواهند
    if (!isDiscount) {
      const accLabel = isCheque && !isReceive && chequeMode === 'issued' ? 'حساب جاری صادرکننده'
        : (isCash || isCheque) ? 'صندوق' : 'حساب'
      if (isReceive && !form.to_account_id) return setMsg({ type: 'error', text: `${accLabel} مقصد را انتخاب کنید` })
      if (!isReceive && !form.from_account_id) return setMsg({ type: 'error', text: `${accLabel} مبدا را انتخاب کنید` })
    }
    if (crossCurrency && !(Number(form.rate_irr) > 0)) {
      return setMsg({ type: 'error', text: 'نرخ تبدیل را وارد کنید (یا مبلغ برداشت را دستی وارد کنید تا نرخ محاسبه شود)' })
    }

    mut.mutate({
      ...form,
      direction: isReceive ? 'in' : 'out',
      amount: isCheque ? chequeTotal : Number(form.amount),
      currency: isCheque ? 'IRR' : form.currency,   // چک همیشه ریالی
      rate_irr: Number(form.rate_irr) || 0,
      contact: form.contact_id,
      payslip_id: form.payslip_id || null,
      expense_charge_id: form.expense_charge_id || null,
      // سر فصل/عنوان فقط در حالت ثبت هزینه و برداشت اصل فقط در حالت سرمایه‌گذار+برداشت ارسال می‌شود
      expense_category_id: modeExpense ? (form.expense_category_id || null) : null,
      expense_title: modeExpense ? (form.expense_title || null) : null,
      investor_withdraw: (modeInvestor && form.investor_mode === 'withdraw') || null,
      from_account: isDiscount ? null : (form.from_account_id || null),
      to_account: isDiscount ? null : (form.to_account_id || null),
      ...(isEndorseMode && !editing && {
        cheque_mode: 'endorsed',
        cheque_ids: selectedChequeIds,
      }),
      ...(isCheque && !isEndorseMode && !editing && {
        cheque_mode: isReceive ? 'received' : 'issued',
        cheques: cheques.map(c => ({
          serial_number: c.serial_number, account_number: c.account_number || '',
          bank_branch: c.bank_branch || '', cheque_date: c.cheque_date,
          amount: Number(String(c.amount).replace(/[^\d]/g, '')) || 0,
          sale_invoice_id: c.sale_invoice_id || null,
        })),
      }),
    })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="card p-6 w-full max-w-lg max-h-[92vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-bold text-white text-lg">
            {editing ? '✏️ ویرایش تراکنش' : isReceive ? '💚 ثبت دریافت' : '🔴 ثبت پرداخت'}
          </h2>
          <button onClick={onClose} className="text-gray-steel hover:text-white text-2xl">×</button>
        </div>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label text-xs mb-1 block">نوع طرف حساب</label>
              <select value={form.contact_type}
                onChange={e => setForm(f => {
                  const t = e.target.value
                  // تعویض نوع، هر سه لینک و حالت عملیات سرمایه‌گذار را پاک می‌کند
                  const base = { ...f, contact_type: t, investor_mode: 'profit', payslip_id: '', expense_charge_id: '', expense_category_id: '', expense_title: '' }
                  if (!f.contact_id) return base
                  const cur = contacts.find(c => String(c.id) === String(f.contact_id))
                  // اعتبار طرف حساب انتخاب‌شده زیر فیلتر/حالت جدید — ناسازگار = پاک شدن انتخاب
                  const valid = !cur ? false
                    : t === '' || t === 'expense' ? true
                    : t === 'investor' ? investorContactIds.has(String(cur.id))
                    : cur.contact_type === t
                  return valid ? base : { ...base, contact_id: '' }
                })}
                className="input text-sm mb-1.5">
                {CONTACT_TYPE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
              <label className="label text-xs mb-1 block">طرف حساب{!modeExpense && ' *'}</label>
              <SearchSelect
                value={form.contact_id}
                onChange={v => setForm(f => ({ ...f, contact_id: v }))}
                placeholder="جستجو و انتخاب طرف حساب..."
                options={filteredContacts.map(c => ({ value: c.id, label: `${c.name} (${c.contact_type_display})`, sub: c.phone }))}
              />
              {pseudoType === 'investor' && investors.length === 0 && (
                <div className="text-[10px] text-gray-steel mt-1">سرمایه‌گذاری تعریف نشده — از صفحه هزینه‌ها اضافه کنید.</div>
              )}
              {modeExpense && form.expense_category_id && categoryContactsFetched && categoryContacts.length === 0 && (
                <div className="text-[10px] text-gray-steel mt-1">طرفی برای این سر فصل ثبت نشده — بدون طرف حساب ثبت می‌شود.</div>
              )}
            </div>
            <div>
              <label className="label text-xs mb-1 block">روش پرداخت</label>
              <select value={form.payment_type}
                onChange={e => setForm(f => ({
                  ...f,
                  payment_type: e.target.value,
                  // چک همیشه ریالی است؛ با تعویض روش، حساب انتخاب‌شده قبلی پاک می‌شود تا فیلتر جدید اعمال شود
                  ...(e.target.value === 'cheque' && { currency: 'IRR' }),
                  from_account_id: '', to_account_id: '',
                }))}
                className="input text-sm">
                {METHODS.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label text-xs mb-1 block">ارز</label>
              <select value={form.currency} onChange={e => setForm(f => ({ ...f, currency: e.target.value }))}
                className="input text-sm" disabled={isCheque}>
                <option value="IRR">ریال (IRR)</option>
                {contactHasFx && <option value="CNY">یوان (CNY)</option>}
              </select>
            </div>
            <div>
              <label className="label text-xs mb-1 block">مبلغ * ({form.currency === 'CNY' ? 'یوان' : 'ریال'})</label>
              {isCheque ? (
                <div className="input text-sm bg-white/5 text-white font-bold flex items-center">
                  {fmt(chequeTotal)} <span className="text-[10px] text-gray-steel mr-1">(جمع چک‌ها)</span>
                </div>
              ) : (
                <AmountInput value={form.amount}
                  onChange={onAmountChange}
                  className="input text-sm" placeholder="0" />
              )}
              {selectedPayslip && (
                <div className="text-[10px] text-brand mt-1">مانده فیش: {fmt(selectedPayslip.remaining_amount)} ریال</div>
              )}
              {selectedCharge && (
                <div className="text-[10px] text-brand mt-1">مانده هزینه: {fmt(selectedCharge.remaining_amount)} ریال</div>
              )}
            </div>
          </div>

          {/* نوع عملیات سرمایه‌گذار — سود مشارکت (لینک به هزینه باز سود) یا برداشت اصل سرمایه */}
          {modeInvestor && selectedContact && investorContactIds.has(String(selectedContact.id)) && (
            <div>
              <label className="label text-xs mb-1 block">نوع عملیات</label>
              <select value={form.investor_mode} onChange={e => setForm(f => ({ ...f, investor_mode: e.target.value }))}
                className="input text-sm">
                <option value="profit">پرداخت سود مشارکت</option>
                <option value="withdraw">برداشت اصل سرمایه</option>
              </select>
              {form.investor_mode === 'profit' && (
                <div className="text-[10px] text-gray-steel mt-1">سود باز سرمایه‌گذار را انتخاب کنید</div>
              )}
            </div>
          )}

          {/* لینک پرداخت به فیش حقوقی باز پرسنل — فقط در پرداخت ریالی به پرسنل */}
          {showPayslips && (
            <div>
              <label className="label text-xs mb-1 block">فیش حقوقی (اختیاری)</label>
              <select value={form.payslip_id}
                onChange={e => setForm(f => ({ ...f, payslip_id: e.target.value, ...(e.target.value && { expense_charge_id: '', expense_category_id: '', expense_title: '' }) }))}
                className="input text-sm">
                <option value="">— بدون فیش (پرداخت عادی) —</option>
                {openPayslips.map(p => <option key={p.id} value={p.id}>{payslipLabel(p)}</option>)}
              </select>
              {openPayslips.length === 0 && (
                <div className="text-[10px] text-gray-steel mt-1">فیش حقوقی باز برای این پرسنل نیست.</div>
              )}
            </div>
          )}

          {/* لینک پرداخت به هزینه باز — هر نوع طرف حساب، فقط پرداخت ریالی؛ با فیش حقوقی انحصاری است */}
          {showCharges && (
            <div>
              <label className="label text-xs mb-1 block">هزینه باز (اختیاری)</label>
              <select value={form.expense_charge_id}
                onChange={e => setForm(f => ({ ...f, expense_charge_id: e.target.value, ...(e.target.value && { payslip_id: '', expense_category_id: '', expense_title: '' }) }))}
                className="input text-sm">
                <option value="">— بدون هزینه (پرداخت عادی) —</option>
                {openCharges.map(c => <option key={c.id} value={c.id}>{chargeLabel(c)}</option>)}
              </select>
              {openCharges.length === 0 && (
                <div className="text-[10px] text-gray-steel mt-1">هزینه باز برای این طرف حساب نیست.</div>
              )}
            </div>
          )}

          {/* ثبت همزمان هزینه متفرقه پرداخت‌شده زیر یک سر فصل — فقط پرداخت ریالی؛ با فیش/هزینه باز انحصاری است */}
          {showCategories && (
            <div>
              <label className="label text-xs mb-1 block">سر فصل هزینه (اختیاری)</label>
              <select value={form.expense_category_id}
                onChange={e => setForm(f => {
                  const v = e.target.value
                  return {
                    ...f,
                    expense_category_id: v,
                    // انتخاب سر فصل، دو لینک دیگر را پاک می‌کند؛ لغو انتخاب، عنوان را هم پاک می‌کند
                    ...(v ? { payslip_id: '', expense_charge_id: '' } : { expense_title: '' }),
                  }
                })}
                className="input text-sm">
                <option value="">— بدون سر فصل (پرداخت عادی) —</option>
                {expenseCategories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
              {form.expense_category_id && (
                <input value={form.expense_title} onChange={e => setForm(f => ({ ...f, expense_title: e.target.value }))}
                  className="input text-sm mt-2" placeholder={`عنوان هزینه (اختیاری) — خالی = «${selectedCategory?.name || ''}»`} />
              )}
              {expenseCategories.length === 0 && (
                <div className="text-[10px] text-gray-steel mt-1">سر فصل متفرقه‌ای تعریف نشده — از صفحه هزینه‌ها اضافه کنید.</div>
              )}
            </div>
          )}

          {isDiscount && (
            <div className="bg-brand/10 border border-brand/30 rounded-xl px-4 py-3 text-xs text-brand leading-5">
              💸 تخفیف هیچ حسابی را تغییر نمی‌دهد —
              {isReceive
                ? ' در دریافت: مستقیم از سود کم می‌شود (تخفیف داده‌شده به مشتری)'
                : ' در پرداخت: مستقیم به سود اضافه می‌شود (تخفیف گرفته‌شده از تأمین‌کننده)'}
            </div>
          )}

          {/* پنل تبدیل ارز — فقط وقتی ارز حساب با ارز پرداخت فرق دارد */}
          {crossCurrency && (
            <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4 space-y-3">
              <div className="text-xs font-bold text-blue-300">
                💱 تبدیل ارز — {form.currency === 'CNY' ? 'یوان' : 'ریال'} ← {activeAcc.currency === 'CNY' ? 'یوان' : 'ریال'}
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="label text-xs mb-1 block">نرخ تبدیل (ریال به ازای هر یوان) *</label>
                  <AmountInput value={form.rate_irr}
                    onChange={onRateChange}
                    className="input text-sm" placeholder="مثلاً 280000" />
                </div>
                <div>
                  <label className="label text-xs mb-1 block">
                    {isReceive ? 'واریز به حساب' : 'برداشت از حساب'} ({activeAcc.currency === 'CNY' ? 'یوان' : 'ریال'}) *
                  </label>
                  <AmountInput value={deductionValue}
                    onChange={onDeductionChange}
                    className="input text-sm" placeholder="خودکار" />
                </div>
              </div>
              <div className="text-[10px] text-blue-300/80 leading-5">
                فیلدها به هم لینک هستند: مبلغ یا نرخ را عوض کنی برداشت محاسبه می‌شود؛ برداشت را دستی عوض کنی نرخ برمی‌گردد محاسبه می‌شود.
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            {!isReceive && !isDiscount && (
              <div>
                <label className="label text-xs mb-1 block">
                  {isCheque && chequeMode === 'issued' ? 'صدور از حساب جاری *'
                    : (isCash || isCheque) ? 'پرداخت از صندوق *' : 'پرداخت از حساب *'}
                </label>
                <select value={form.from_account_id} onChange={e => setForm(f => ({ ...f, from_account_id: e.target.value }))} className="input text-sm">
                  <option value="">انتخاب کنید...</option>
                  {accountOptions.map(a => (
                    <option key={a.id} value={a.id}>{a.name} ({a.currency})</option>
                  ))}
                </select>
                {accountOptions.length === 0 && (
                  <div className="text-[10px] text-red-400 mt-1">
                    {isCheque && !isReceive && chequeMode === 'issued'
                      ? 'حساب جاری بانکی تعریف نشده — اول در مدیریت بانک بسازید'
                      : 'صندوقی تعریف نشده — اول در مدیریت بانک یک حساب با نوع «صندوق نقد» بسازید'}
                  </div>
                )}
              </div>
            )}
            {isReceive && !isDiscount && (
              <div>
                <label className="label text-xs mb-1 block">
                  {(isCash || isCheque) ? 'دریافت در صندوق *' : 'دریافت در حساب *'}
                </label>
                <select value={form.to_account_id} onChange={e => setForm(f => ({ ...f, to_account_id: e.target.value }))} className="input text-sm">
                  <option value="">انتخاب کنید...</option>
                  {accountOptions.map(a => (
                    <option key={a.id} value={a.id}>{a.name} ({a.currency})</option>
                  ))}
                </select>
                {accountOptions.length === 0 && (
                  <div className="text-[10px] text-red-400 mt-1">
                    {isCheque && !isReceive && chequeMode === 'issued'
                      ? 'حساب جاری بانکی تعریف نشده — اول در مدیریت بانک بسازید'
                      : 'صندوقی تعریف نشده — اول در مدیریت بانک یک حساب با نوع «صندوق نقد» بسازید'}
                  </div>
                )}
              </div>
            )}
            <div>
              <label className="label text-xs mb-1 block">تاریخ</label>
              <JalaliDateInput value={form.date} onChange={v => setForm(f => ({ ...f, date: v }))} className="input text-sm" />
            </div>
          </div>

          {/* ویرایشگر/انتخابگر چک‌ها — فقط برای روش «اسناد» */}
          {isCheque && (
            <div className="bg-white/5 border border-white/10 rounded-xl p-4 space-y-3">
              {/* حالت اسناد در پرداخت: صدور از حساب خودمان یا واگذاری اسناد صندوق */}
              {!isReceive && (
                <div className="flex gap-1 bg-white/5 rounded-lg p-1">
                  {[['issued', '📝 صدور چک از حساب ما'], ['endorse', '🗃 پرداخت از اسناد صندوق']].map(([k, label]) => (
                    <button key={k} type="button"
                      onClick={() => { setChequeMode(k); setForm(f => ({ ...f, from_account_id: '' })); setSelectedChequeIds([]) }}
                      className={`flex-1 text-xs px-2 py-1.5 rounded-md transition-all ${chequeMode === k ? 'bg-brand/20 text-brand' : 'text-gray-steel hover:text-white'}`}>
                      {label}
                    </button>
                  ))}
                </div>
              )}

              {/* واگذاری: لیست چک‌های موجود در صندوق با چک‌باکس */}
              {isEndorseMode ? (
                <div className="space-y-2">
                  <div className="text-xs font-bold text-white">🗃 چک‌های موجود در صندوق</div>
                  {!form.from_account_id ? (
                    <div className="text-[11px] text-gray-steel">اول صندوق را انتخاب کنید تا چک‌هایش نمایش داده شود.</div>
                  ) : availCheques.length === 0 ? (
                    <div className="text-[11px] text-gray-steel">چکی در این صندوق نیست.</div>
                  ) : (
                    availCheques.map(ch => (
                      <label key={ch.id} className="flex items-center gap-2 border border-white/10 rounded-lg px-3 py-2 cursor-pointer hover:bg-white/5">
                        <input type="checkbox" checked={selectedChequeIds.includes(ch.id)}
                          onChange={e => setSelectedChequeIds(ids => e.target.checked ? [...ids, ch.id] : ids.filter(x => x !== ch.id))}
                          className="accent-[#FBC02D]" />
                        <span className="text-xs flex-1">
                          چک <b dir="ltr">{ch.serial_number}</b>
                          {ch.bank_branch && <span className="text-gray-steel"> — {ch.bank_branch}</span>}
                          {ch.from_contact && <span className="text-gray-steel"> (از: {ch.from_contact})</span>}
                        </span>
                        <span className="text-[10px] text-gray-steel whitespace-nowrap">{formatDate(ch.cheque_date)}</span>
                        <span className="text-xs font-bold text-white whitespace-nowrap">{fmt(ch.amount)} ریال</span>
                      </label>
                    ))
                  )}
                  {selectedChequeIds.length > 0 && (
                    <div className="text-xs text-white font-bold text-left">جمع انتخاب‌شده: {fmt(selectedChequeTotal)} ریال</div>
                  )}
                </div>
              ) : (
                <>
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-white">
                  🧾 {isReceive ? 'چک‌های دریافتی از مشتری' : 'چک‌های صادره'} ({fmt(cheques.length)})
                </span>
                <button type="button"
                  onClick={() => setCheques(cs => [...cs, { serial_number: '', account_number: '', bank_branch: '', cheque_date: '', amount: '' }])}
                  className="text-xs px-3 py-1.5 rounded-lg bg-brand/15 text-brand hover:bg-brand/25 transition-all">
                  + افزودن چک
                </button>
              </div>
              {cheques.length === 0 && (
                <div className="text-[11px] text-gray-steel">مشتری ممکن است چند چک داده باشد — هر چک را یک ردیف اضافه کنید.</div>
              )}
              {cheques.map((ch, i) => (
                <div key={i} className="border border-white/10 rounded-lg p-3 space-y-2 relative">
                  <button type="button" onClick={() => setCheques(cs => cs.filter((_, j) => j !== i))}
                    className="absolute left-2 top-2 text-gray-steel hover:text-red-400 text-sm">×</button>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="label text-[10px] mb-0.5 block">شماره چک *</label>
                      <input value={ch.serial_number} dir="ltr"
                        onChange={e => setCheques(cs => cs.map((c, j) => j === i ? { ...c, serial_number: e.target.value } : c))}
                        className="input text-xs" />
                    </div>
                    <div>
                      <label className="label text-[10px] mb-0.5 block">مبلغ چک (ریال) *</label>
                      <AmountInput value={ch.amount}
                        onChange={e => setCheques(cs => cs.map((c, j) => j === i ? { ...c, amount: e.target.value } : c))}
                        className="input text-xs" placeholder="0" />
                    </div>
                    {/* شماره حساب و شعبه فقط برای چک دریافتی از مشتری — در صدور، از حساب جاری انتخاب‌شده خوانده می‌شود */}
                    {isReceive && (
                      <>
                    <div>
                      <label className="label text-[10px] mb-0.5 block">شماره حساب چک</label>
                      <input value={ch.account_number} dir="ltr"
                        onChange={e => setCheques(cs => cs.map((c, j) => j === i ? { ...c, account_number: e.target.value } : c))}
                        className="input text-xs" />
                    </div>
                    <div>
                      <label className="label text-[10px] mb-0.5 block">شعبه بانک</label>
                      <input value={ch.bank_branch}
                        onChange={e => setCheques(cs => cs.map((c, j) => j === i ? { ...c, bank_branch: e.target.value } : c))}
                        className="input text-xs" />
                    </div>
                      </>
                    )}
                    <div className="col-span-2">
                      <label className="label text-[10px] mb-0.5 block">تاریخ چک *</label>
                      <JalaliDateInput value={ch.cheque_date}
                        onChange={v => setCheques(cs => cs.map((c, j) => j === i ? { ...c, cheque_date: v } : c))}
                        className="input text-xs" />
                    </div>
                    {/* چک بابت فاکتور مشخص — هنگام وصول خودکار به همان فاکتور می‌رود؛ خالی = تخصیص خودکار FIFO */}
                    {isReceive && openInvoices.length > 0 && (
                      <div className="col-span-2">
                        <label className="label text-[10px] mb-0.5 block">بابت فاکتور (اختیاری)</label>
                        <select value={ch.sale_invoice_id || ''}
                          onChange={e => setCheques(cs => cs.map((c, j) => j === i ? { ...c, sale_invoice_id: e.target.value } : c))}
                          className="input text-xs">
                          <option value="">— تخصیص خودکار هنگام وصول (سررسید قدیمی‌تر اول) —</option>
                          {openInvoices.map(inv => (
                            <option key={inv.id} value={inv.id}>
                              فاکتور {inv.invoice_number} — مانده {fmt(inv.remaining_amount)} ریال
                            </option>
                          ))}
                        </select>
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {cheques.length > 0 && (
                <div className="text-xs text-white font-bold text-left">جمع: {fmt(chequeTotal)} ریال</div>
              )}
                </>
              )}
            </div>
          )}

          <div>
            <label className="label text-xs mb-1 block">شماره پیگیری / مرجع</label>
            <input value={form.reference} onChange={e => setForm(f => ({ ...f, reference: e.target.value }))} className="input text-sm" placeholder="اختیاری" />
          </div>
          <div>
            <label className="label text-xs mb-1 block">توضیحات</label>
            <input value={form.note} onChange={e => setForm(f => ({ ...f, note: e.target.value }))} className="input text-sm" placeholder="اختیاری" />
          </div>
        </div>

        {msg && (
          <div className={`mt-4 rounded-lg px-4 py-2 text-sm ${msg.type === 'success' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
            {msg.text}
          </div>
        )}
        {/* هشدار ثبت تکراری — بک‌اند ۴۰۹ داده؛ با تأیید کاربر همان پی‌لود با confirm_duplicate ارسال می‌شود */}
        {dupPayload && (
          <div className="mt-3 rounded-lg px-4 py-3 text-sm bg-yellow-500/10 border border-yellow-500/30 text-yellow-300 flex items-center justify-between gap-3">
            <span>⚠️ احتمال ثبت تکراری — مطمئنید این تراکنش جداست؟</span>
            <button onClick={() => mut.mutate({ ...dupPayload, confirm_duplicate: 1 })} disabled={mut.isPending}
              className="text-xs px-3 py-1.5 rounded-lg bg-yellow-500/20 border border-yellow-500/40 hover:bg-yellow-500/30 disabled:opacity-50 whitespace-nowrap">
              {mut.isPending ? '...' : 'ثبت قطعی'}
            </button>
          </div>
        )}

        <div className="flex gap-3 mt-5">
          <button onClick={handleSubmit} disabled={mut.isPending}
            className={`flex-1 py-2.5 rounded-xl font-semibold text-sm disabled:opacity-50 ${isReceive ? 'bg-green-600 hover:bg-green-500 text-white' : 'bg-red-600 hover:bg-red-500 text-white'}`}>
            {mut.isPending ? 'در حال ثبت...' : editing ? '✓ ذخیره تغییرات' : isReceive ? '✓ ثبت دریافت' : '✓ ثبت پرداخت'}
          </button>
          <button onClick={onClose} className="btn-secondary px-6 py-2.5">انصراف</button>
        </div>
      </div>
    </div>
  )
}

// ─── فرم سند حسابداری — انتقال بدهی/طلب بین دو طرف حساب ─────
function VoucherForm({ onClose }) {
  const qc = useQueryClient()
  const [form, setForm] = useState({
    from_contact_id: '', to_contact_id: '', currency: 'IRR', amount: '', rate_irr: '',
    date: new Date().toISOString().split('T')[0], reference: '', note: '',
  })
  const [msg, setMsg] = useState(null)

  const { data: contacts = [] } = useQuery({
    queryKey: ['contacts-plain'],
    queryFn: () => api.get('/accounting/contacts/').then(r => r.data),
  })

  const mut = useMutation({
    // یک فراخوانی اتمیک — هر دو طرف سند با هم ساخته و جفت می‌شوند (paired_with)
    mutationFn: (payload) => api.post('/accounting/payments/voucher/', payload).then(r => r.data),
    onSuccess: (r) => {
      qc.invalidateQueries(['payments-list'])
      qc.invalidateQueries(['accounts'])
      qc.invalidateQueries(['contacts-all'])
      qc.invalidateQueries(['contacts'])
      qc.invalidateQueries(['contact-detail'])
      setMsg({ type: 'success', text: r.message || 'سند انتقال ثبت شد' })
      setTimeout(onClose, 800)
    },
    onError: (e) => setMsg({ type: 'error', text: e.response?.data?.error || 'خطا' }),
  })

  const fromContact = contacts.find(c => String(c.id) === String(form.from_contact_id))
  const toContact = contacts.find(c => String(c.id) === String(form.to_contact_id))
  // عملیات ارزی — سند یوانی فقط وقتی مجاز است که هر دو طرف حساب کارکرد یوانی داشته باشند
  const voucherHasFx = [fromContact, toContact].every(c => !c || c.has_fx !== false)
  useEffect(() => {
    if (!voucherHasFx && form.currency === 'CNY') {
      setForm(f => ({ ...f, currency: 'IRR' }))
    }
  }, [voucherHasFx, form.currency])

  function handleSubmit() {
    if (!form.from_contact_id) return setMsg({ type: 'error', text: 'طرف حساب مبدا را انتخاب کنید' })
    if (!form.to_contact_id) return setMsg({ type: 'error', text: 'طرف حساب مقصد را انتخاب کنید' })
    if (form.from_contact_id === form.to_contact_id) return setMsg({ type: 'error', text: 'مبدا و مقصد نمی‌توانند یکی باشند' })
    if (!form.amount || Number(form.amount) <= 0) return setMsg({ type: 'error', text: 'مبلغ را وارد کنید' })
    setMsg(null)
    mut.mutate({
      from_contact_id: form.from_contact_id,
      to_contact_id: form.to_contact_id,
      currency: form.currency,
      amount: Number(form.amount),
      rate_irr: Number(form.rate_irr) || 0,
      date: form.date,
      reference: form.reference,
      note: form.note,
    })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="card p-6 w-full max-w-lg">
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-bold text-white text-lg">📒 سند حسابداری — انتقال بین طرف حساب‌ها</h2>
          <button onClick={onClose} className="text-gray-steel hover:text-white text-2xl">×</button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="label text-xs mb-1 block">از طرف حساب *</label>
            <SearchSelect
              value={form.from_contact_id}
              onChange={v => setForm(f => ({ ...f, from_contact_id: v }))}
              placeholder="جستجو و انتخاب طرف حساب مبدا..."
              options={contacts.map(c => ({ value: c.id, label: `${c.name} (${c.contact_type_display})`, sub: c.phone }))}
            />
            <div className="text-[10px] text-gray-steel mt-1">بدهی‌اش کم / بستانکاری‌اش زیاد می‌شود (مانده از حساب او برداشته می‌شود)</div>
          </div>
          <div>
            <label className="label text-xs mb-1 block">به طرف حساب *</label>
            <SearchSelect
              value={form.to_contact_id}
              onChange={v => setForm(f => ({ ...f, to_contact_id: v }))}
              placeholder="جستجو و انتخاب طرف حساب مقصد..."
              options={contacts.filter(c => String(c.id) !== String(form.from_contact_id)).map(c => ({ value: c.id, label: `${c.name} (${c.contact_type_display})`, sub: c.phone }))}
            />
            <div className="text-[10px] text-gray-steel mt-1">بدهی‌اش زیاد / بستانکاری‌اش کم می‌شود (مانده به حساب او منتقل می‌شود)</div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label text-xs mb-1 block">ارز</label>
              <select value={form.currency} onChange={e => setForm(f => ({ ...f, currency: e.target.value }))} className="input text-sm">
                <option value="IRR">ریال (IRR)</option>
                {voucherHasFx && <option value="CNY">یوان (CNY)</option>}
              </select>
            </div>
            <div>
              <label className="label text-xs mb-1 block">مبلغ *</label>
              <AmountInput value={form.amount}
                onChange={e => setForm(f => ({ ...f, amount: e.target.value }))}
                className="input text-sm" placeholder="0" />
            </div>
          </div>

          {voucherHasFx && form.currency === 'CNY' && (
            <div>
              <label className="label text-xs mb-1 block">نرخ تبدیل (ریال به ازای هر یوان)</label>
              <AmountInput value={form.rate_irr}
                onChange={e => setForm(f => ({ ...f, rate_irr: e.target.value }))}
                className="input text-sm" placeholder="مثلاً 270000" />
            </div>
          )}

          <div>
            <label className="label text-xs mb-1 block">تاریخ</label>
            <JalaliDateInput value={form.date} onChange={v => setForm(f => ({ ...f, date: v }))} className="input text-sm" />
          </div>
          <div>
            <label className="label text-xs mb-1 block">شماره پیگیری / مرجع</label>
            <input value={form.reference} onChange={e => setForm(f => ({ ...f, reference: e.target.value }))} className="input text-sm" placeholder="اختیاری" />
          </div>
          <div>
            <label className="label text-xs mb-1 block">شرح سند</label>
            <input value={form.note} onChange={e => setForm(f => ({ ...f, note: e.target.value }))} className="input text-sm" placeholder="اختیاری" />
          </div>
        </div>

        {msg && (
          <div className={`mt-4 rounded-lg px-4 py-2 text-sm ${msg.type === 'success' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
            {msg.text}
          </div>
        )}

        <div className="flex gap-3 mt-5">
          <button onClick={handleSubmit} disabled={mut.isPending}
            className="btn-primary flex-1 text-sm py-2.5 disabled:opacity-50">
            {mut.isPending ? 'در حال ثبت...' : '✓ ثبت سند انتقال'}
          </button>
          <button onClick={onClose} className="btn-secondary px-6 py-2.5">انصراف</button>
        </div>
      </div>
    </div>
  )
}

// ─── فرم جابجایی پول بین حساب‌های داخلی (هم‌ارز یا با نرخ تبدیل) ───
function TransferForm({ onClose }) {
  const qc = useQueryClient()
  const [form, setForm] = useState({
    from_account_id: '', to_account_id: '', amount: '', rate_irr: '',
    date: new Date().toISOString().split('T')[0], reference: '', note: '',
  })
  const [msg, setMsg] = useState(null)

  const { data: accounts = [] } = useQuery({
    queryKey: ['accounts'],
    queryFn: () => api.get('/accounting/accounts/').then(r => r.data),
  })
  // نرخ یوان مرجع روز — پیش‌پر کردن نرخ تبدیل بین‌ارزی
  const { data: rateData } = useQuery({
    queryKey: ['exchange-rate'],
    queryFn: () => api.get('/catalog/exchange-rate/').then(r => r.data),
    staleTime: 60000,
  })
  useEffect(() => {
    if (rateData?.rate_cny_to_irt) {
      setForm(f => f.rate_irr ? f : { ...f, rate_irr: String(rateData.rate_cny_to_irt) })
    }
  }, [rateData])

  const mut = useMutation({
    mutationFn: async (payloads) => {
      await api.post('/accounting/payments/', payloads[0])
      if (payloads[1]) return api.post('/accounting/payments/', payloads[1]).then(r => r.data)
    },
    onSuccess: () => {
      qc.invalidateQueries(['payments-list'])
      qc.invalidateQueries(['accounts'])
      setMsg({ type: 'success', text: 'جابجایی ثبت شد' })
      setTimeout(onClose, 800)
    },
    onError: (e) => setMsg({ type: 'error', text: e.response?.data?.error || 'خطا' }),
  })

  const fromAcc = accounts.find(a => String(a.id) === String(form.from_account_id))
  const toAcc = accounts.find(a => String(a.id) === String(form.to_account_id))
  const crossCurrency = fromAcc && toAcc && fromAcc.currency !== toAcc.currency
  const toAccounts = accounts.filter(a => String(a.id) !== String(form.from_account_id))

  // مبلغ واریز به مقصد بر اساس نرخ (ریال به ازای هر واحد ارز)
  const rate = Number(form.rate_irr) || 0
  const amountFrom = Number(form.amount) || 0
  let amountTo = amountFrom
  if (crossCurrency && rate > 0 && amountFrom > 0) {
    amountTo = fromAcc.currency === 'IRR' ? amountFrom / rate : amountFrom * rate
  }
  const CUR_LABEL = { IRR: 'ریال', CNY: 'یوان', USD: 'دلار' }

  function handleSubmit() {
    if (!form.from_account_id) return setMsg({ type: 'error', text: 'حساب مبدا را انتخاب کنید' })
    if (!form.to_account_id) return setMsg({ type: 'error', text: 'حساب مقصد را انتخاب کنید' })
    if (!form.amount || Number(form.amount) <= 0) return setMsg({ type: 'error', text: 'مبلغ را وارد کنید' })
    if (crossCurrency) {
      if (fromAcc.currency !== 'IRR' && toAcc.currency !== 'IRR') {
        return setMsg({ type: 'error', text: 'تبدیل مستقیم بین دو ارز غیرریالی پشتیبانی نمی‌شود — ابتدا به حساب ریالی منتقل کنید' })
      }
      if (!rate || rate <= 0) return setMsg({ type: 'error', text: 'نرخ تبدیل را وارد کنید' })
    }
    setMsg(null)
    const base = {
      payment_type: 'transfer',
      date: form.date,
      reference: form.reference,
      rate_irr: rate,
      note: form.note,
    }
    if (crossCurrency) {
      // دو رکورد: برداشت از مبدا + واریز به مقصد با ارز و مبلغ خودشان
      mut.mutate([
        { ...base, direction: 'out', from_account_id: form.from_account_id,
          currency: fromAcc.currency, amount: amountFrom,
          note: `جابجایی به ${toAcc.name}${form.note ? ' — ' + form.note : ''}` },
        { ...base, direction: 'in', to_account_id: form.to_account_id,
          currency: toAcc.currency, amount: Math.round(amountTo * 100) / 100,
          note: `جابجایی از ${fromAcc.name}${form.note ? ' — ' + form.note : ''}` },
      ])
    } else {
      mut.mutate([
        { ...base, direction: 'out', from_account_id: form.from_account_id,
          to_account_id: form.to_account_id, currency: fromAcc?.currency || 'IRR', amount: amountFrom },
      ])
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="card p-6 w-full max-w-lg">
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-bold text-white text-lg">🔁 جابجایی پول بین حساب‌ها</h2>
          <button onClick={onClose} className="text-gray-steel hover:text-white text-2xl">×</button>
        </div>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label text-xs mb-1 block">از حساب *</label>
              <select value={form.from_account_id}
                onChange={e => setForm(f => ({ ...f, from_account_id: e.target.value, to_account_id: '' }))}
                className="input text-sm">
                <option value="">انتخاب کنید...</option>
                {accounts.map(a => <option key={a.id} value={a.id}>{a.name} ({a.currency})</option>)}
              </select>
            </div>
            <div>
              <label className="label text-xs mb-1 block">به حساب *</label>
              <select value={form.to_account_id} onChange={e => setForm(f => ({ ...f, to_account_id: e.target.value }))}
                className="input text-sm" disabled={!form.from_account_id}>
                <option value="">انتخاب کنید...</option>
                {toAccounts.map(a => <option key={a.id} value={a.id}>{a.name} ({a.currency})</option>)}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label text-xs mb-1 block">مبلغ برداشت * {fromAcc && `(${CUR_LABEL[fromAcc.currency]})`}</label>
              <AmountInput value={form.amount}
                onChange={e => setForm(f => ({ ...f, amount: e.target.value }))}
                className="input text-sm" placeholder="0" />
            </div>
            {crossCurrency ? (
              <div>
                <label className="label text-xs mb-1 block">نرخ تبدیل (ریال به ازای هر {CUR_LABEL[toAcc.currency === 'IRR' ? fromAcc.currency : toAcc.currency]}) *</label>
                <AmountInput value={form.rate_irr}
                  onChange={e => setForm(f => ({ ...f, rate_irr: e.target.value }))}
                  className="input text-sm" placeholder="مثلاً 270000" />
              </div>
            ) : (
              <div>
                <label className="label text-xs mb-1 block">تاریخ</label>
                <JalaliDateInput value={form.date} onChange={v => setForm(f => ({ ...f, date: v }))} className="input text-sm" />
              </div>
            )}
          </div>

          {crossCurrency && (
            <>
              <div className="bg-brand/10 border border-brand/30 rounded-xl px-4 py-3 text-sm">
                <span className="text-gray-steel">مبلغ واریز به مقصد: </span>
                <span className="font-bold text-brand">
                  {rate > 0 && amountFrom > 0
                    ? `${Number(amountTo.toFixed(2)).toLocaleString('fa-IR')} ${CUR_LABEL[toAcc.currency]}`
                    : '—'}
                </span>
              </div>
              <div>
                <label className="label text-xs mb-1 block">تاریخ</label>
                <JalaliDateInput value={form.date} onChange={v => setForm(f => ({ ...f, date: v }))} className="input text-sm" />
              </div>
            </>
          )}

          <div>
            <label className="label text-xs mb-1 block">شماره پیگیری / مرجع</label>
            <input value={form.reference} onChange={e => setForm(f => ({ ...f, reference: e.target.value }))} className="input text-sm" placeholder="اختیاری" />
          </div>
          <div>
            <label className="label text-xs mb-1 block">توضیحات</label>
            <input value={form.note} onChange={e => setForm(f => ({ ...f, note: e.target.value }))} className="input text-sm" placeholder="اختیاری" />
          </div>
        </div>

        {msg && (
          <div className={`mt-4 rounded-lg px-4 py-2 text-sm ${msg.type === 'success' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
            {msg.text}
          </div>
        )}

        <div className="flex gap-3 mt-5">
          <button onClick={handleSubmit} disabled={mut.isPending}
            className="btn-primary flex-1 text-sm py-2.5 disabled:opacity-50">
            {mut.isPending ? 'در حال ثبت...' : '✓ ثبت جابجایی'}
          </button>
          <button onClick={onClose} className="btn-secondary px-6 py-2.5">انصراف</button>
        </div>
      </div>
    </div>
  )
}

// ─── باکس ویرایش اسناد مالی — جستجوی همه اسناد (بدون محدودیت روز) ─────
function DocsSearchPanel({ onClose }) {
  const qc = useQueryClient()
  const { can } = usePermissions()
  const [q, setQ] = useState('')
  // پیش‌فرض بازه = امروز — تا با باز شدن پنل، اسناد امروز دیده شوند
  const todayIso = new Date().toLocaleDateString('en-CA')
  const [dateFrom, setDateFrom] = useState(todayIso)
  const [dateTo, setDateTo] = useState(todayIso)
  const [editing, setEditing] = useState(null)

  const hasFilter = q.trim().length > 0 || dateFrom || dateTo
  const { data: results = [], isFetching } = useQuery({
    queryKey: ['payments-search', q, dateFrom, dateTo],
    queryFn: () => api.get('/accounting/payments/', {
      params: {
        ...(q.trim() && { q }),
        ...(dateFrom && { date_from: dateFrom }),
        ...(dateTo && { date_to: dateTo }),
      },
    }).then(r => r.data),
    enabled: !!hasFilter,
  })

  const revMut = useMutation({
    mutationFn: (id) => api.post(`/accounting/payments/${id}/reverse/`).then(r => r.data),
    onSuccess: (r) => {
      qc.invalidateQueries()
      toast.success(r.message || 'سند برگشت ثبت شد')
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا در ثبت برگشت'),
  })

  const tdS = { padding: '8px 10px' }
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="card p-6 w-full max-w-4xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-bold text-white text-lg">🗂 ویرایش اسناد مالی</h2>
          <button onClick={onClose} className="text-gray-steel hover:text-white text-2xl">×</button>
        </div>
        <input autoFocus value={q} onChange={e => setQ(e.target.value)}
          className="input text-sm w-full mb-3"
          placeholder="جستجو: شماره سند، نام طرف حساب، مبلغ، شماره فاکتور، مرجع یا شرح..." />
        {/* فیلتر بازه زمانی شمسی — هر دو یا فقط یک طرف بازه هم کار می‌کند */}
        <div className="grid grid-cols-2 gap-3 mb-4">
          <div>
            <label className="label text-xs mb-1 block">از تاریخ</label>
            <JalaliDateInput value={dateFrom} onChange={setDateFrom} className="input text-xs" />
          </div>
          <div>
            <label className="label text-xs mb-1 block">تا تاریخ</label>
            <JalaliDateInput value={dateTo} onChange={setDateTo} className="input text-xs" />
          </div>
        </div>

        {!hasFilter ? (
          <div className="text-center py-10 text-gray-steel text-sm">عبارت جستجو یا بازه زمانی را وارد کنید — همه اسناد (هر تاریخی) جستجو می‌شوند</div>
        ) : isFetching ? (
          <div className="text-center py-8 text-gray-steel text-sm">در حال جستجو...</div>
        ) : results.length === 0 ? (
          <div className="text-center py-8 text-gray-steel text-sm">سندی پیدا نشد</div>
        ) : (
          <div className="overflow-x-auto">
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.1)' }}>
                  {['سند', 'نوع', 'طرف حساب', 'مبلغ', 'تاریخ', 'مرجع / شرح', 'عملیات'].map(h => (
                    <th key={h} style={{ padding: '6px 10px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500, fontSize: 11 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {results.map((p, i) => (
                  <tr key={p.id} style={{ borderBottom: '0.5px solid rgba(255,255,255,0.05)', background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                    <td style={{ ...tdS, fontFamily: 'monospace', color: 'var(--color-text-muted)', whiteSpace: 'nowrap' }}>
                      #{p.id}
                      {p.paired_with && (
                        <div style={{ fontSize: 9, color: '#0066FF' }} title={`جفت‌شده با سند #${p.paired_with} (${p.paired_contact_name || ''})`}>🔗 #{p.paired_with}</div>
                      )}
                      {p.reversal_of && (
                        <div style={{ fontSize: 9, color: '#FBC02D' }}>↩ برگشت #{p.reversal_of}</div>
                      )}
                      {p.is_reversed && (
                        <div style={{ fontSize: 9, color: 'var(--color-text-muted)' }}>✗ برگشت‌خورده</div>
                      )}
                    </td>
                    <td style={tdS}>
                      <span style={{
                        color: p.direction === 'in' ? '#00C896' : '#FF3B3B',
                        background: p.direction === 'in' ? '#00C89620' : '#FF3B3B20',
                        padding: '2px 8px', borderRadius: 20, fontSize: 11, whiteSpace: 'nowrap',
                      }}>
                        {p.direction === 'in' ? '↓ دریافت' : '↑ پرداخت'}
                      </span>
                    </td>
                    <td style={tdS}>{p.contact_name || '—'}</td>
                    <td style={{ ...tdS, fontWeight: 600, whiteSpace: 'nowrap' }}>
                      {fmt(p.amount)} {p.currency === 'CNY' ? '¥' : 'ریال'}
                    </td>
                    <td style={{ ...tdS, color: 'var(--color-text-secondary)', fontSize: 11, whiteSpace: 'nowrap' }}>{formatDate(p.date)}</td>
                    <td style={{ ...tdS, color: 'var(--color-text-secondary)', fontSize: 11, maxWidth: 220 }}>
                      <div className="truncate" title={[p.reference, p.note].filter(Boolean).join(' — ')}>
                        {[p.reference, p.note].filter(Boolean).join(' — ') || '—'}
                      </div>
                    </td>
                    <td style={{ ...tdS, whiteSpace: 'nowrap' }}>
                      {can('payment_edit') && (
                        <>
                          <button onClick={() => setEditing(p)}
                            className="text-xs px-2 py-1 rounded-lg bg-brand/15 text-brand hover:bg-brand/25 transition-all ml-1">
                            ویرایش
                          </button>
                          {/* اصلاح اسناد فقط با «سند برگشت» — حذف عمداً نداریم تا سابقه حسابداری حفظ شود */}
                          {!p.is_reversed && !p.reversal_of && (
                            <button onClick={() => { if (window.confirm(`سند برگشت برای تراکنش #${p.id}${p.paired_with ? ` و طرف مقابلش #${p.paired_with}` : ''} ثبت شود؟`)) revMut.mutate(p.id) }}
                              disabled={revMut.isPending}
                              className="text-xs px-2 py-1 rounded-lg bg-yellow-500/15 text-yellow-400 hover:bg-yellow-500/25 transition-all ml-1 disabled:opacity-50">
                              برگشت
                            </button>
                          )}
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {editing && (
        <PaymentForm direction={editing.direction} editing={editing}
          onClose={() => setEditing(null)}
          onSuccess={() => { setEditing(null); qc.invalidateQueries() }} />
      )}
    </div>
  )
}

// ─── باکس امور چک — چرخه عمر چک: صندوق، خواباندن، واگذاری، برگشتی ─────
const CHEQUE_TABS = [
  ['in_hand', '📥 در صندوق'],
  ['deposited', '🏦 خوابانده به بانک'],
  ['endorsed', '📤 خرج‌شده به افراد'],
  ['issued', '📝 صادره از ما'],
  ['bounced', '⛔ برگشتی'],
  ['returned', '↩️ برگشت‌داده‌شده'],
]

function ChequesPanel({ onClose }) {
  const qc = useQueryClient()
  const { can } = usePermissions()
  const [tab, setTab] = useState('in_hand')
  const [q, setQ] = useState('')
  const [depositFor, setDepositFor] = useState(null)   // چکی که در حال خواباندنش هستیم
  const [depositAcc, setDepositAcc] = useState('')
  const [editCh, setEditCh] = useState(null)           // چک در حال اصلاح
  const [eForm, setEForm] = useState({})

  const { data: accounts = [] } = useQuery({
    queryKey: ['accounts'],
    queryFn: () => api.get('/accounting/accounts/').then(r => r.data),
  })
  const bankAccounts = accounts.filter(a => a.account_type === 'bank')

  // جستجو: نام / شماره چک / مبلغ — اگر ۸ رقم تاریخ شمسی بود، به ISO تبدیل می‌شود
  const qSend = (() => {
    const digits = q.trim().replace(/[^\d۰-۹٠-٩]/g, '')
      .replace(/[۰-۹]/g, d => '۰۱۲۳۴۵۶۷۸۹'.indexOf(d)).replace(/[٠-٩]/g, d => '٠١٢٣٤٥٦٧٨٩'.indexOf(d))
    if (digits.length === 8 && digits.startsWith('14')) {
      const [gy, gm, gd] = jalaliToGregorian(+digits.slice(0, 4), +digits.slice(4, 6), +digits.slice(6, 8))
      return `${gy}-${String(gm).padStart(2, '0')}-${String(gd).padStart(2, '0')}`
    }
    return q.trim()
  })()

  const { data: cheques = [], isFetching } = useQuery({
    queryKey: ['cheques-list', tab, qSend],
    queryFn: () => api.get('/accounting/cheques/', { params: { status: tab, ...(qSend && { q: qSend }) } }).then(r => r.data),
  })

  const actMut = useMutation({
    mutationFn: ({ id, action, account_id }) =>
      api.post(`/accounting/cheques/${id}/action/`, { action, ...(account_id && { account_id }) }).then(r => r.data),
    onSuccess: (r) => {
      qc.invalidateQueries(['cheques-list']); qc.invalidateQueries(['payments-list']); qc.invalidateQueries(['accounts'])
      toast.success(r.message || 'انجام شد')
      setDepositFor(null); setDepositAcc('')
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا'),
  })
  const editMut = useMutation({
    mutationFn: ({ id, ...d }) => api.patch(`/accounting/cheques/${id}/`, d).then(r => r.data),
    onSuccess: (r) => { qc.invalidateQueries(['cheques-list']); qc.invalidateQueries(['payments-list']); toast.success(r.message || 'چک اصلاح شد'); setEditCh(null) },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا در اصلاح'),
  })

  const doAct = (ch, action, confirmText) => {
    if (!window.confirm(confirmText)) return
    actMut.mutate({ id: ch.id, action })
  }

  const tdS = { padding: '8px 10px' }
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="card p-6 w-full max-w-5xl max-h-[92vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-bold text-white text-lg">🧾 امور چک</h2>
          <button onClick={onClose} className="text-gray-steel hover:text-white text-2xl">×</button>
        </div>

        <div className="flex gap-1 bg-white/5 rounded-lg p-1 mb-4 flex-wrap">
          {CHEQUE_TABS.map(([k, label]) => (
            <button key={k} onClick={() => setTab(k)}
              className={`text-xs px-3 py-1.5 rounded-md transition-all ${tab === k ? 'bg-brand/20 text-brand' : 'text-gray-steel hover:text-white'}`}>
              {label}
            </button>
          ))}
        </div>

        <input value={q} onChange={e => setQ(e.target.value)}
          className="input text-sm w-full mb-4"
          placeholder="جستجو: نام شخص، شماره چک، مبلغ یا تاریخ چک (مثلاً 14050610)..." />

        {isFetching ? (
          <div className="text-center py-8 text-gray-steel text-sm">در حال بارگذاری...</div>
        ) : cheques.length === 0 ? (
          <div className="text-center py-8 text-gray-steel text-sm">چکی در این وضعیت نیست</div>
        ) : (
          <div className="overflow-x-auto">
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.1)' }}>
                  {['شماره چک', 'شخص', 'مبلغ', 'تاریخ چک', 'بانک/شعبه', 'محل', 'عملیات'].map(h => (
                    <th key={h} style={{ padding: '6px 10px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500, fontSize: 11 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {cheques.map((ch, i) => (
                  <tr key={ch.id} style={{ borderBottom: '0.5px solid rgba(255,255,255,0.05)', background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                    <td style={{ ...tdS, fontFamily: 'monospace', whiteSpace: 'nowrap' }} dir="ltr">{ch.serial_number}</td>
                    <td style={tdS}>{ch.contact_name || ch.spent_contact_name || '—'}</td>
                    <td style={{ ...tdS, fontWeight: 700, whiteSpace: 'nowrap' }}>{fmt(ch.amount)} ریال</td>
                    <td style={{ ...tdS, fontSize: 11, color: 'var(--color-text-secondary)', whiteSpace: 'nowrap' }}>{formatDate(ch.cheque_date)}</td>
                    <td style={{ ...tdS, fontSize: 11, color: 'var(--color-text-secondary)' }}>{ch.bank_branch || '—'}</td>
                    <td style={{ ...tdS, fontSize: 11, color: 'var(--color-text-secondary)' }}>
                      {ch.status === 'deposited' ? ch.deposited_account_name
                        : ch.status === 'endorsed' ? `نزد ${ch.spent_contact_name}`
                        : ch.status === 'issued' ? ch.drawn_account_name
                        : ch.petty_account_name || '—'}
                    </td>
                    <td style={{ ...tdS, whiteSpace: 'nowrap' }}>
                      {can('payment_edit') && (
                        <>
                          {ch.status === 'in_hand' && (
                            <>
                              <button onClick={() => { setDepositFor(ch); setDepositAcc('') }}
                                className="text-xs px-2 py-1 rounded-lg bg-blue-500/15 text-blue-400 hover:bg-blue-500/25 transition-all ml-1">
                                🏦 خواباندن
                              </button>
                              <button onClick={() => doAct(ch, 'return', `چک ${ch.serial_number} به مشتری برگشت داده شود؟ (بدهی مشتری برمی‌گردد)`)}
                                className="text-xs px-2 py-1 rounded-lg bg-yellow-500/15 text-yellow-400 hover:bg-yellow-500/25 transition-all ml-1">
                                ↩️ برگشت به مشتری
                              </button>
                            </>
                          )}
                          {ch.status === 'deposited' && (
                            <button onClick={() => doAct(ch, 'bounce', `چک ${ch.serial_number} برگشت از بانک خورد؟ (به صندوق برمی‌گردد و در لیست برگشتی می‌ماند)`)}
                              className="text-xs px-2 py-1 rounded-lg bg-red-500/15 text-red-400 hover:bg-red-500/25 transition-all ml-1">
                              ⛔ برگشت از بانک
                            </button>
                          )}
                          {ch.status === 'endorsed' && (
                            <button onClick={() => doAct(ch, 'takeback', `چک ${ch.serial_number} از طرف حساب پس گرفته شد؟ (به صندوق برمی‌گردد و بدهی طرف برمی‌گردد)`)}
                              className="text-xs px-2 py-1 rounded-lg bg-yellow-500/15 text-yellow-400 hover:bg-yellow-500/25 transition-all ml-1">
                                📥 پس‌گیری
                            </button>
                          )}
                          {ch.status === 'bounced' && (
                            <button onClick={() => doAct(ch, 'return', `چک برگشتی ${ch.serial_number} به مشتری تحویل داده شود؟ (بدهی مشتری برمی‌گردد)`)}
                              className="text-xs px-2 py-1 rounded-lg bg-yellow-500/15 text-yellow-400 hover:bg-yellow-500/25 transition-all ml-1">
                              ↩️ تحویل به مشتری
                            </button>
                          )}
                          {['in_hand', 'issued', 'deposited'].includes(ch.status) && (
                            <button onClick={() => { setEditCh(ch); setEForm({ serial_number: ch.serial_number, account_number: ch.account_number, bank_branch: ch.bank_branch, cheque_date: ch.cheque_date, amount: ch.amount }) }}
                              className="text-xs px-2 py-1 rounded-lg bg-brand/15 text-brand hover:bg-brand/25 transition-all ml-1">
                              ✏️ اصلاح
                            </button>
                          )}
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* انتخاب حساب برای خواباندن */}
        {depositFor && (
          <div className="mt-4 border border-blue-500/30 bg-blue-500/10 rounded-xl p-4 flex items-center gap-3 flex-wrap">
            <span className="text-xs text-blue-300">خواباندن چک <b dir="ltr">{depositFor.serial_number}</b> به حساب:</span>
            <select value={depositAcc} onChange={e => setDepositAcc(e.target.value)} className="input text-xs max-w-[220px]">
              <option value="">انتخاب حساب بانکی...</option>
              {bankAccounts.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
            <button disabled={!depositAcc || actMut.isPending}
              onClick={() => actMut.mutate({ id: depositFor.id, action: 'deposit', account_id: depositAcc })}
              className="text-xs px-3 py-1.5 rounded-lg bg-blue-500/20 border border-blue-500/40 text-blue-300 disabled:opacity-50">
              {actMut.isPending ? '...' : 'تأیید خواباندن'}
            </button>
            <button onClick={() => setDepositFor(null)} className="text-xs text-gray-steel hover:text-white">انصراف</button>
          </div>
        )}

        {/* مودال اصلاح چک */}
        {editCh && (
          <div className="fixed inset-0 z-60 flex items-center justify-center bg-black/60 p-4" style={{ zIndex: 60 }}>
            <div className="card p-5 w-full max-w-md space-y-3">
              <h3 className="font-bold text-white text-sm">✏️ اصلاح چک {editCh.serial_number}</h3>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label text-[10px] mb-0.5 block">شماره چک</label>
                  <input value={eForm.serial_number} dir="ltr" onChange={e => setEForm(f => ({ ...f, serial_number: e.target.value }))} className="input text-xs" />
                </div>
                <div>
                  <label className="label text-[10px] mb-0.5 block">مبلغ چک (ریال)</label>
                  <AmountInput value={eForm.amount} onChange={e => setEForm(f => ({ ...f, amount: e.target.value }))} className="input text-xs" />
                </div>
                <div>
                  <label className="label text-[10px] mb-0.5 block">شماره حساب چک</label>
                  <input value={eForm.account_number} dir="ltr" onChange={e => setEForm(f => ({ ...f, account_number: e.target.value }))} className="input text-xs" />
                </div>
                <div>
                  <label className="label text-[10px] mb-0.5 block">شعبه بانک</label>
                  <input value={eForm.bank_branch} onChange={e => setEForm(f => ({ ...f, bank_branch: e.target.value }))} className="input text-xs" />
                </div>
                <div className="col-span-2">
                  <label className="label text-[10px] mb-0.5 block">تاریخ چک</label>
                  <JalaliDateInput value={eForm.cheque_date} onChange={v => setEForm(f => ({ ...f, cheque_date: v }))} className="input text-xs" />
                </div>
              </div>
              <div className="flex gap-2">
                <button disabled={editMut.isPending}
                  onClick={() => editMut.mutate({ id: editCh.id, serial_number: eForm.serial_number, account_number: eForm.account_number, bank_branch: eForm.bank_branch, cheque_date: eForm.cheque_date, amount: String(eForm.amount).replace(/[^\d]/g, '') })}
                  className="btn-primary flex-1 text-xs py-2 disabled:opacity-50">
                  {editMut.isPending ? '...' : 'ذخیره اصلاح'}
                </button>
                <button onClick={() => setEditCh(null)} className="btn-secondary px-4 text-xs">انصراف</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── صفحه اصلی: هاب دریافت و پرداخت ─────────────────────────
const ACTIONS = [
  { key: 'in',       icon: '💚', title: 'ثبت دریافت',       desc: 'دریافت وجه از طرف حساب به یکی از حساب‌ها', color: '#00C896' },
  { key: 'out',      icon: '🔴', title: 'ثبت پرداخت',       desc: 'پرداخت وجه به طرف حساب از یکی از حساب‌ها', color: '#FF3B3B' },
  { key: 'voucher',  icon: '📒', title: 'سند حسابداری',     desc: 'انتقال بدهی/طلب بین دو طرف حساب (بدون گردش بانکی)', color: '#FBC02D' },
  { key: 'transfer', icon: '🔁', title: 'جابجایی پول درون بانک', desc: 'انتقال بین حساب‌های داخلی — هم‌ارز یا با نرخ تبدیل', color: '#0066FF' },
  { key: 'cheques',  icon: '🧾', title: 'امور چک',           desc: 'چک‌های صندوق، خواباندن به بانک، واگذاشته‌ها، برگشتی‌ها و اصلاح چک', color: '#FF9500' },
  { key: 'docs',     icon: '🗂', title: 'ویرایش اسناد مالی', desc: 'جستجو و ویرایش/برگشت هر سند ثبت‌شده — با شماره سند، نام، مبلغ یا تاریخ', color: '#8B5CF6' },
]

export default function PaymentsPage() {
  const [active, setActive] = useState(null) // 'in' | 'out' | 'voucher' | 'transfer' | null
  const { can } = usePermissions()

  return (
    <div className="container-main py-8 max-w-3xl">
      <h1 className="font-display font-bold text-2xl text-white mb-6">دریافت و پرداخت</h1>

      {!can('purchase_create') ? (
        <div className="card p-12 text-center text-gray-steel text-sm">دسترسی ثبت تراکنش ندارید</div>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          {ACTIONS.map(a => (
            <button key={a.key} onClick={() => setActive(a.key)}
              className="card p-6 text-right hover:bg-white/5 transition-all cursor-pointer">
              <div className="text-3xl mb-3">{a.icon}</div>
              <div className="font-bold text-white mb-1" style={{ color: a.color }}>{a.title}</div>
              <div className="text-xs text-gray-steel">{a.desc}</div>
            </button>
          ))}
        </div>
      )}

      {(active === 'in' || active === 'out') && (
        <PaymentForm direction={active} onClose={() => setActive(null)} onSuccess={() => setActive(null)} />
      )}
      {active === 'voucher' && <VoucherForm onClose={() => setActive(null)} />}
      {active === 'transfer' && <TransferForm onClose={() => setActive(null)} />}
      {active === 'cheques' && <ChequesPanel onClose={() => setActive(null)} />}
      {active === 'docs' && <DocsSearchPanel onClose={() => setActive(null)} />}
    </div>
  )
}
