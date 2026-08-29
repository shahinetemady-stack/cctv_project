import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { Search, Plus, UserPlus, X, Users, Shield, Check } from 'lucide-react'
import api from '../../services/api'

const PERM_GROUPS = [
  { label: 'فروش', perms: ['sale_view', 'sale_create', 'sale_edit', 'sale_payment'] },
  { label: 'برگشت از فروش و خرید', perms: ['return_view', 'return_create', 'return_edit'] },
  { label: 'انبار و کاردکس', perms: ['kardex_view', 'kardex_edit'] },
  { label: 'خرید', perms: ['purchase_view', 'purchase_create', 'purchase_edit', 'payment_edit'] },
  { label: 'طرف حساب‌ها', perms: ['contacts_view', 'contacts_create', 'contacts_edit', 'partner_approve'] },
  { label: 'گزارشات مالی', perms: ['reports_view', 'balance_view', 'accounts_edit'] },
  { label: 'مدیریت کاربران', perms: ['users_view', 'users_edit'] },
  { label: 'محصولات', perms: ['products_view', 'products_edit'] },
  { label: 'فرمول قیمت', perms: ['pricing_rate_view', 'pricing_costs_view'] },
  { label: 'داشبورد', perms: ['dashboard_view'] },
]

function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }

// ─── ویرایش نقش ──────────────────────────────────────────────
function RoleEditor({ role, allPerms, contactTypes = [], onSave, onClose }) {
  const [name, setName] = useState(role?.name || '')
  const [desc, setDesc] = useState(role?.description || '')
  const [perms, setPerms] = useState(new Set(role?.permissions || []))
  const [allowedTypes, setAllowedTypes] = useState(new Set(role?.allowed_contact_types || []))
  const qc = useQueryClient()

  const saveMut = useMutation({
    mutationFn: (d) => role?.id
      ? api.patch(`/accounting/roles/${role.id}/`, d).then(r => r.data)
      : api.post('/accounting/roles/', d).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['roles'])
      toast.success('نقش ذخیره شد')
      onSave?.()
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا در ذخیره نقش'),
  })

  const togglePerm = (code) => {
    setPerms(p => {
      const n = new Set(p)
      if (n.has(code)) n.delete(code); else n.add(code)
      return n
    })
  }

  const toggleGroup = (groupPerms) => {
    const allIn = groupPerms.every(p => perms.has(p))
    setPerms(p => {
      const n = new Set(p)
      groupPerms.forEach(gp => allIn ? n.delete(gp) : n.add(gp))
      return n
    })
  }

  const selectAll = () => setPerms(new Set(allPerms.map(p => p.code)))
  const clearAll = () => setPerms(new Set())

  const toggleType = (code) => {
    setAllowedTypes(t => {
      const n = new Set(t)
      if (n.has(code)) n.delete(code); else n.add(code)
      return n
    })
  }

  const permMap = Object.fromEntries(allPerms.map(p => [p.code, p.label]))

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="card p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-bold text-white text-lg">{role ? 'ویرایش نقش' : 'نقش جدید'}</h2>
          <button onClick={onClose} className="text-gray-steel hover:text-white"><X size={20} /></button>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-5">
          <div>
            <label className="label text-xs mb-1 block">نام نقش *</label>
            <input value={name} onChange={e => setName(e.target.value)} className="input text-sm" placeholder="مثلاً: فروشنده" />
          </div>
          <div>
            <label className="label text-xs mb-1 block">توضیح</label>
            <input value={desc} onChange={e => setDesc(e.target.value)} className="input text-sm" placeholder="اختیاری" />
          </div>
        </div>

        <div className="mb-4">
          <div className="flex items-center justify-between mb-3">
            <label className="label text-sm">دسترسی‌ها ({perms.size} از {allPerms.length})</label>
            <div className="flex gap-2">
              <button onClick={selectAll} className="text-xs text-brand hover:text-brand/80">انتخاب همه</button>
              <button onClick={clearAll} className="text-xs text-red-400 hover:text-red-300">حذف همه</button>
            </div>
          </div>

          <div className="space-y-3">
            {PERM_GROUPS.map(group => {
              const groupPerms = group.perms.filter(p => permMap[p])
              if (groupPerms.length === 0) return null
              const allIn = groupPerms.every(p => perms.has(p))
              const someIn = groupPerms.some(p => perms.has(p))
              return (
                <div key={group.label} className="bg-white/5 rounded-xl p-4">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-sm font-semibold text-white">{group.label}</span>
                    <button onClick={() => toggleGroup(groupPerms)}
                      className={`text-xs px-3 py-1 rounded-full border transition-all ${
                        allIn ? 'bg-brand/20 border-brand text-brand' :
                        someIn ? 'bg-white/10 border-white/20 text-gray-steel' :
                        'border-white/10 text-gray-steel hover:border-white/30'
                      }`}>
                      {allIn ? '✓ همه انتخاب' : someIn ? '— بعضی' : 'انتخاب همه'}
                    </button>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    {groupPerms.map(code => (
                      <label key={code} className="flex items-center gap-2 cursor-pointer group">
                        <div onClick={() => togglePerm(code)}
                          className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-all ${
                            perms.has(code) ? 'bg-brand border-brand' : 'border-white/20 group-hover:border-white/40'
                          }`}>
                          {perms.has(code) && <Check size={12} strokeWidth={3} className="text-white" />}
                        </div>
                        <span className="text-xs text-gray-steel group-hover:text-white transition-colors">
                          {permMap[code]}
                        </span>
                      </label>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* نوع‌های طرف حساب قابل دسترس برای این نقش */}
        <div className="mb-4 bg-white/5 rounded-xl p-4">
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm font-semibold text-white">نوع‌های طرف حساب قابل مشاهده</span>
            {allowedTypes.size > 0 && (
              <button onClick={() => setAllowedTypes(new Set())} className="text-xs text-brand hover:text-brand/80">
                همه نوع‌ها
              </button>
            )}
          </div>
          <div className="text-[10px] text-gray-steel mb-3">
            اگر هیچکدام انتخاب نشود، این نقش همه نوع‌ها را می‌بیند. با انتخاب، فقط نوع‌های انتخاب‌شده در لیست/کاردکس/جزئیات طرف حساب‌ها قابل دسترس است.
          </div>
          <div className="flex flex-wrap gap-2">
            {contactTypes.map(t => (
              <button key={t.code} onClick={() => toggleType(t.code)}
                className={`text-xs px-3 py-1.5 rounded-full border transition-all ${
                  allowedTypes.has(t.code) ? 'bg-brand/20 border-brand text-brand' : 'border-white/10 text-gray-steel hover:border-white/30'
                }`}>
                {t.label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex gap-3">
          <button onClick={() => saveMut.mutate({ name, description: desc, permissions: [...perms], allowed_contact_types: [...allowedTypes] })}
            disabled={!name || saveMut.isPending}
            className="btn-primary flex-1 py-2.5 disabled:opacity-50">
            {saveMut.isPending ? 'در حال ذخیره...' : 'ذخیره نقش'}
          </button>
          <button onClick={onClose} className="btn-secondary px-6 py-2.5">انصراف</button>
        </div>
      </div>
    </div>
  )
}

// ─── ویرایش پرسنل ────────────────────────────────────────────
const staffSchema = z.object({
  first_name: z.string().max(50, 'حداکثر ۵۰ کاراکتر').optional(),
  last_name: z.string().max(50, 'حداکثر ۵۰ کاراکتر').optional(),
  phone: z.string().regex(/^09\d{9}$/, 'شماره موبایل معتبر نیست — مثال: 09123456789'),
  role_id: z.string().optional(),
  employee_id: z.string().max(20, 'حداکثر ۲۰ کاراکتر').optional(),
  department: z.string().max(50, 'حداکثر ۵۰ کاراکتر').optional(),
  is_active: z.string(),
  password: z.string().min(6, 'رمز عبور حداقل ۶ کاراکتر').or(z.literal('')),
})

function StaffEditor({ staff, roles, onClose }) {
  const qc = useQueryClient()
  const { register, handleSubmit, formState: { errors } } = useForm({
    resolver: zodResolver(staffSchema),
    defaultValues: {
      first_name: staff.first_name || '',
      last_name: staff.last_name || '',
      phone: staff.phone || '',
      role_id: staff.role_id ? String(staff.role_id) : '',
      employee_id: staff.employee_id || '',
      department: staff.department || '',
      is_active: staff.is_active ? '1' : '0',
      password: '',
    },
  })

  const saveMut = useMutation({
    mutationFn: (d) => api.patch(`/accounting/staff/${staff.id}/`, d).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['staff'])
      toast.success('اطلاعات پرسنل ذخیره شد')
      onClose()
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا در ذخیره'),
  })

  const onSubmit = (d) => {
    const payload = { ...d, is_active: d.is_active === '1' }
    if (!payload.password) delete payload.password
    saveMut.mutate(payload)
  }

  const err = (name) => errors[name] && (
    <div className="text-[11px] text-red-400 mt-1">{errors[name].message}</div>
  )

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="card p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-bold text-white text-lg">ویرایش پرسنل</h2>
          <button onClick={onClose} className="text-gray-steel hover:text-white"><X size={20} /></button>
        </div>

        <form onSubmit={handleSubmit(onSubmit)}>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="label text-xs mb-1 block">نام</label>
              <input {...register('first_name')} className="input text-sm" />
              {err('first_name')}
            </div>
            <div>
              <label className="label text-xs mb-1 block">نام خانوادگی</label>
              <input {...register('last_name')} className="input text-sm" />
              {err('last_name')}
            </div>
            <div>
              <label className="label text-xs mb-1 block">موبایل *</label>
              <input {...register('phone')} dir="ltr" className="input text-sm font-mono text-left" placeholder="09..." />
              {err('phone')}
            </div>
            <div>
              <label className="label text-xs mb-1 block">نقش</label>
              <select {...register('role_id')} className="input text-sm">
                <option value="">بدون نقش</option>
                {roles.map(r => <option key={r.id} value={String(r.id)}>{r.name}</option>)}
              </select>
            </div>
            <div>
              <label className="label text-xs mb-1 block">کد پرسنلی</label>
              <input {...register('employee_id')} className="input text-sm" />
              {err('employee_id')}
            </div>
            <div>
              <label className="label text-xs mb-1 block">بخش</label>
              <input {...register('department')} className="input text-sm" />
              {err('department')}
            </div>
            <div>
              <label className="label text-xs mb-1 block">وضعیت</label>
              <select {...register('is_active')} className="input text-sm">
                <option value="1">فعال</option>
                <option value="0">غیرفعال</option>
              </select>
            </div>
            <div>
              <label className="label text-xs mb-1 block">رمز جدید</label>
              <input type="password" {...register('password')} dir="ltr" className="input text-sm font-mono text-left"
                placeholder="خالی بماند، تغییر نمی‌کند" />
              {err('password')}
            </div>
          </div>

          <div className="flex gap-2">
            <button type="submit" disabled={saveMut.isPending} className="btn-primary px-6 py-2.5 disabled:opacity-50">
              {saveMut.isPending ? 'در حال ذخیره...' : 'ذخیره'}
            </button>
            <button type="button" onClick={onClose} className="btn-secondary px-6 py-2.5">انصراف</button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ─── مدیریت پرسنل ────────────────────────────────────────────
function StaffManager({ roles }) {
  const qc = useQueryClient()
  const [showAdd, setShowAdd] = useState(false)
  const [addMode, setAddMode] = useState('search') // search | new
  const [form, setForm] = useState({ user_id: '', role_id: '', employee_id: '', department: '' })
  const [newUser, setNewUser] = useState({ phone: '', first_name: '', last_name: '', password: '' })
  const [userSearch, setUserSearch] = useState('')
  const [selectedUser, setSelectedUser] = useState(null)
  const [showUserDrop, setShowUserDrop] = useState(false)
  const [editing, setEditing] = useState(null) // پرسنل در حال ویرایش

  const { data: staff = [] } = useQuery({
    queryKey: ['staff'],
    queryFn: () => api.get('/accounting/staff/').then(r => r.data),
  })

  const { data: users = [] } = useQuery({
    queryKey: ['customer-search-staff', userSearch],
    queryFn: () => api.get('/accounting/customers/search/', { params: { q: userSearch } }).then(r => r.data),
    enabled: userSearch.length >= 2,
  })

  const createUserMut = useMutation({
    mutationFn: (d) => api.post('/accounting/staff/create-user/', d).then(r => r.data),
    onSuccess: (data) => {
      setSelectedUser({ id: data.user_id, name: data.name, phone: data.phone })
      setForm(f => ({ ...f, user_id: data.user_id }))
      setAddMode('search')
      toast.success(`کاربر ${data.name} ساخته شد`)
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا در ساخت کاربر'),
  })

  const addMut = useMutation({
    mutationFn: (d) => api.post('/accounting/staff/', d).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['staff'])
      setShowAdd(false)
      setForm({ user_id: '', role_id: '', employee_id: '', department: '' })
      setSelectedUser(null)
      setUserSearch('')
      toast.success('پرسنل ثبت شد')
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا در ثبت پرسنل'),
  })

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-white">لیست پرسنل</h3>
        <button onClick={() => setShowAdd(true)} className="btn-primary text-xs px-4 py-2 flex items-center gap-1.5">
          <Plus size={14} /> افزودن پرسنل
        </button>
      </div>

      {showAdd && (
        <div className="bg-white/5 rounded-xl p-4 mb-4 space-y-3">
          {/* انتخاب حالت */}
          <div className="flex gap-2 mb-2">
            <button onClick={() => setAddMode('search')}
              className={`text-xs px-3 py-1.5 rounded-lg border transition-all flex items-center gap-1.5 ${addMode==='search' ? 'bg-brand/20 border-brand text-white' : 'border-white/10 text-gray-steel'}`}>
              <Search size={13} /> جستجوی کاربر موجود
            </button>
            <button onClick={() => setAddMode('new')}
              className={`text-xs px-3 py-1.5 rounded-lg border transition-all flex items-center gap-1.5 ${addMode==='new' ? 'bg-brand/20 border-brand text-white' : 'border-white/10 text-gray-steel'}`}>
              <UserPlus size={13} /> ساخت کاربر جدید
            </button>
          </div>

          {addMode === 'new' ? (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label text-xs mb-1 block">شماره موبایل *</label>
                  <input value={newUser.phone} onChange={e => setNewUser(u => ({...u, phone: e.target.value}))}
                    className="input text-xs" placeholder="09..." />
                </div>
                <div>
                  <label className="label text-xs mb-1 block">رمز عبور *</label>
                  <input type="password" value={newUser.password} onChange={e => setNewUser(u => ({...u, password: e.target.value}))}
                    className="input text-xs" placeholder="حداقل ۶ کاراکتر" />
                </div>
                <div>
                  <label className="label text-xs mb-1 block">نام</label>
                  <input value={newUser.first_name} onChange={e => setNewUser(u => ({...u, first_name: e.target.value}))}
                    className="input text-xs" placeholder="اختیاری" />
                </div>
                <div>
                  <label className="label text-xs mb-1 block">نام خانوادگی</label>
                  <input value={newUser.last_name} onChange={e => setNewUser(u => ({...u, last_name: e.target.value}))}
                    className="input text-xs" placeholder="اختیاری" />
                </div>
              </div>
              <button onClick={() => createUserMut.mutate(newUser)} disabled={!newUser.phone || !newUser.password || createUserMut.isPending}
                className="btn-primary text-xs px-4 py-2 disabled:opacity-50">
                {createUserMut.isPending ? 'در حال ساخت...' : 'ساخت کاربر'}
              </button>
              {selectedUser && <div className="text-xs text-green-400">✓ کاربر ساخته شد: {selectedUser.name || selectedUser.phone}</div>}
            </div>
          ) : (
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label text-xs mb-1 block">جستجوی کاربر *</label>
              <div className="relative">
                <input value={userSearch} onChange={e => { setUserSearch(e.target.value); setShowUserDrop(true) }}
                  onFocus={() => setShowUserDrop(true)}
                  placeholder="نام یا موبایل..." className="input text-xs" />
                {showUserDrop && users.length > 0 && (
                  <div className="absolute z-50 top-full right-0 left-0 mt-1 bg-navy border border-white/10 rounded-xl overflow-hidden max-h-40 overflow-y-auto">
                    {users.map(u => (
                      <button key={u.id} className="w-full text-right px-3 py-2 hover:bg-white/5 border-b border-white/5 last:border-0"
                        onClick={() => { setSelectedUser(u); setForm(f => ({ ...f, user_id: u.id })); setUserSearch(u.display || u.name); setShowUserDrop(false) }}>
                        <div className="text-xs text-white">{u.name}</div>
                        <div className="text-[10px] text-gray-steel">{u.phone}</div>
                      </button>
                    ))}
                  </div>
                )}
                {showUserDrop && <div className="fixed inset-0 z-40" onClick={() => setShowUserDrop(false)} />}
                {selectedUser && <div className="text-xs text-green-400 mt-1">✓ {selectedUser.name || selectedUser.phone}</div>}
              </div>
            </div>
            <div>
              <label className="label text-xs mb-1 block">نقش *</label>
              <select value={form.role_id} onChange={e => setForm(f => ({ ...f, role_id: e.target.value }))} className="input text-xs">
                <option value="">انتخاب نقش...</option>
                {roles.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
              </select>
            </div>
            <div>
              <label className="label text-xs mb-1 block">کد پرسنلی</label>
              <input value={form.employee_id} onChange={e => setForm(f => ({ ...f, employee_id: e.target.value }))} className="input text-xs" placeholder="اختیاری" />
            </div>
            <div>
              <label className="label text-xs mb-1 block">بخش</label>
              <input value={form.department} onChange={e => setForm(f => ({ ...f, department: e.target.value }))} className="input text-xs" placeholder="مثلاً: فروش" />
            </div>
          </div>
          )}
          <div className="flex gap-2">
            <button onClick={() => addMut.mutate(form)} disabled={!form.user_id || !form.role_id || addMut.isPending}
              className="btn-primary text-xs px-4 py-2 disabled:opacity-50">ذخیره</button>
            <button onClick={() => setShowAdd(false)} className="btn-secondary text-xs px-4 py-2">انصراف</button>
          </div>
        </div>
      )}

      {staff.length === 0 ? (
        <div className="text-center py-8 text-gray-steel text-sm">هنوز پرسنلی تعریف نشده</div>
      ) : (
        <div className="overflow-x-auto">
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.1)' }}>
                {['نام', 'موبایل', 'نقش', 'کد پرسنلی', 'بخش', 'وضعیت'].map(h => (
                  <th key={h} style={{ padding: '8px 12px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {staff.map((s, i) => (
                <tr key={s.id} style={{ borderBottom: '0.5px solid rgba(255,255,255,0.05)', background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                  <td style={{ padding: '10px 12px', fontWeight: 500 }}>
                    <button onClick={() => setEditing(s)} className="hover:text-brand transition-colors" title="ویرایش">{s.name}</button>
                  </td>
                  <td style={{ padding: '10px 12px', color: 'var(--color-text-secondary)', fontSize: 11 }}>{s.phone}</td>
                  <td style={{ padding: '10px 12px' }}>
                    <span style={{ color: '#0066FF', background: '#0066FF20', padding: '2px 8px', borderRadius: 20, fontSize: 11 }}>
                      {s.role_name || '—'}
                    </span>
                  </td>
                  <td style={{ padding: '10px 12px', color: 'var(--color-text-secondary)', fontSize: 11 }}>{s.employee_id || '—'}</td>
                  <td style={{ padding: '10px 12px', color: 'var(--color-text-secondary)', fontSize: 11 }}>{s.department || '—'}</td>
                  <td style={{ padding: '10px 12px' }}>
                    <span style={{ color: s.is_active ? '#00C896' : '#FF3B3B', background: (s.is_active ? '#00C896' : '#FF3B3B') + '20', padding: '2px 8px', borderRadius: 20, fontSize: 11 }}>
                      {s.is_active ? 'فعال' : 'غیرفعال'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {editing && <StaffEditor staff={editing} roles={roles} onClose={() => setEditing(null)} />}
    </div>
  )
}

// ─── صفحه اصلی ───────────────────────────────────────────────
export default function RolesPage() {
  const qc = useQueryClient()
  const [editRole, setEditRole] = useState(null)
  const [showNew, setShowNew] = useState(false)
  const [tab, setTab] = useState('roles')

  const { data, isLoading } = useQuery({
    queryKey: ['roles'],
    queryFn: () => api.get('/accounting/roles/').then(r => r.data),
  })

  const deleteMut = useMutation({
    mutationFn: (id) => api.delete(`/accounting/roles/${id}/`).then(r => r.data),
    onSuccess: () => qc.invalidateQueries(['roles']),
  })

  const roles = data?.roles || []
  const allPerms = data?.all_permissions || []
  const contactTypes = data?.contact_types || []

  return (
    <div className="container-main py-8 max-w-5xl">
      <h1 className="font-display font-bold text-2xl text-white mb-6">مدیریت نقش‌ها و پرسنل</h1>

      <div className="flex gap-2 mb-6 border-b border-white/10">
        {[['roles', 'نقش‌ها', Shield], ['staff', 'پرسنل', Users]].map(([k, v, Icon]) => (
          <button key={k} onClick={() => setTab(k)}
            className={`text-sm px-5 py-2.5 rounded-t-lg border-b-2 transition-all flex items-center gap-2 ${tab === k ? 'border-brand text-white bg-brand/10' : 'border-transparent text-gray-steel hover:text-white'}`}>
            <Icon size={15} /> {v}
          </button>
        ))}
      </div>

      {tab === 'roles' && (
        <>
          <div className="flex justify-between items-center mb-4">
            <div className="text-xs text-gray-steel">{roles.length} نقش تعریف شده</div>
            <button onClick={() => setShowNew(true)} className="btn-primary text-sm px-4 py-2 flex items-center gap-1.5">
              <Plus size={15} /> نقش جدید
            </button>
          </div>

          {isLoading ? <div className="text-center py-8 text-gray-steel">در حال بارگذاری...</div> : (
            <div className="grid grid-cols-2 gap-4">
              {roles.map(role => (
                <div key={role.id} className="card p-5">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h3 className="font-bold text-white">{role.name}</h3>
                      <div className="text-xs text-gray-steel mt-0.5">{role.description}</div>
                    </div>
                    <div className="flex gap-2">
                      <button onClick={() => setEditRole(role)} className="text-xs text-brand hover:text-brand/80">ویرایش</button>
                      {role.staff_count === 0 && (
                        <button onClick={() => { if(window.confirm('حذف شود؟')) deleteMut.mutate(role.id) }}
                          className="text-xs text-red-400 hover:text-red-300">حذف</button>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-3 mb-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${role.is_active ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                      {role.is_active ? 'فعال' : 'غیرفعال'}
                    </span>
                    <span className="text-xs text-gray-steel">{role.perm_count} دسترسی</span>
                    <span className="text-xs text-gray-steel">{role.staff_count} نفر</span>
                  </div>

                  <div className="flex flex-wrap gap-1">
                    {PERM_GROUPS.map(group => {
                      const count = group.perms.filter(p => role.permissions?.includes(p)).length
                      if (count === 0) return null
                      return (
                        <span key={group.label} style={{ fontSize: 10, padding: '1px 6px', borderRadius: 10, background: 'rgba(0,102,255,0.15)', color: '#0066FF' }}>
                          {group.label} ({count})
                        </span>
                      )
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {tab === 'staff' && <StaffManager roles={roles} />}

      {(showNew || editRole) && (
        <RoleEditor
          role={editRole}
          allPerms={allPerms}
          contactTypes={contactTypes}
          onSave={() => { setShowNew(false); setEditRole(null) }}
          onClose={() => { setShowNew(false); setEditRole(null) }}
        />
      )}
    </div>
  )
}
