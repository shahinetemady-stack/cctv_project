import { useState, useRef } from 'react'
import api from '../services/api'
import * as XLSX from 'xlsx'

const TEMPLATE_HEADERS = [
  'name', 'category', 'brand', 'model_number', 'description',
  'sensor_name', 'voltage', 'lens_name', 'board_name',
  'sku', 'purchase_price_cny', 'profit_percent', 'stock_quantity'
]

function downloadTemplate() {
  const ws = XLSX.utils.aoa_to_sheet([
    TEMPLATE_HEADERS,
    ['نام محصول نمونه', 'لنز دوربین مداربسته', 'YTOT', 'YT-1000', 'توضیحات',
     'Sony IMX335', '12V', 'لنز 3.6mm', '', 'SKU001', '15.5', '30', '100']
  ])
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, 'محصولات')
  XLSX.writeFile(wb, 'products_template.xlsx')
}

export default function BulkUploadPage() {
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState([])
  const [status, setStatus] = useState(null)
  const [result, setResult] = useState(null)
  const fileRef = useRef()

  function handleFile(e) {
    const f = e.target.files[0]
    if (!f) return
    setFile(f)

    const reader = new FileReader()
    reader.onload = (ev) => {
      const wb = XLSX.read(ev.target.result, { type: 'binary' })
      const ws = wb.Sheets[wb.SheetNames[0]]
      const rows = XLSX.utils.sheet_to_json(ws, { header: 1 })
      setPreview(rows.slice(0, 6))
    }
    reader.readAsBinaryString(f)
  }

  async function handleUpload() {
    if (!file) return
    setStatus('loading')
    const formData = new FormData()
    formData.append('file', file)
    try {
      const res = await api.post('/catalog/products/bulk-upload/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      setResult(res.data)
      setStatus('success')
    } catch (e) {
      setStatus('error')
      setResult({ error: e.response?.data?.error || 'خطا در آپلود' })
    }
  }

  return (
    <div className="container-main py-12 max-w-3xl">
      <div className="flex items-center justify-between mb-8">
        <h1 className="font-display font-bold text-2xl text-white">📊 آپلود دسته‌جمعی محصولات</h1>
        <button onClick={downloadTemplate}
          className="btn-secondary text-sm px-4 py-2 flex items-center gap-2">
          ⬇️ دانلود Template
        </button>
      </div>

      {/* راهنما */}
      <div className="card p-5 mb-6">
        <h3 className="font-semibold text-white mb-3">مراحل آپلود:</h3>
        <ol className="space-y-2 text-sm text-gray-steel list-decimal list-inside">
          <li>فایل Template را دانلود کنید</li>
          <li>اطلاعات محصولات را در فایل Excel وارد کنید</li>
          <li>فایل تکمیل شده را آپلود کنید</li>
          <li>پیش‌نمایش را بررسی و تأیید کنید</li>
        </ol>
      </div>

      {/* آپلود */}
      <div className="card p-6 mb-6">
        <div
          onClick={() => fileRef.current.click()}
          className="border-2 border-dashed border-white/20 rounded-xl p-10 text-center cursor-pointer hover:border-brand/50 transition-all">
          <div className="text-4xl mb-3">📁</div>
          <div className="text-white font-semibold mb-1">
            {file ? file.name : 'کلیک کنید یا فایل را اینجا رها کنید'}
          </div>
          <div className="text-xs text-gray-steel">فرمت‌های مجاز: .xlsx, .xls</div>
        </div>
        <input ref={fileRef} type="file" accept=".xlsx,.xls" onChange={handleFile} className="hidden" />
      </div>

      {/* پیش‌نمایش */}
      {preview.length > 0 && (
        <div className="card p-5 mb-6 overflow-x-auto">
          <h3 className="font-semibold text-white mb-3">پیش‌نمایش فایل:</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            {preview.map((row, i) => (
              <tr key={i} style={{ background: i === 0 ? 'rgba(0,102,255,0.1)' : 'transparent' }}>
                {row.map((cell, j) => (
                  <td key={j} style={{ padding: '6px 10px', borderBottom: '1px solid rgba(255,255,255,0.05)',
                    color: i === 0 ? '#0066FF' : '#fff', fontWeight: i === 0 ? 600 : 400 }}>
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </table>
        </div>
      )}

      {/* نتیجه */}
      {result && (
        <div className={`card p-5 mb-6 ${status === 'success' ? 'border-green-500/30' : 'border-red-500/30'}`}>
          {status === 'success' ? (
            <div className="text-green-400">
              <div className="font-bold mb-2">✅ آپلود موفق</div>
              <div className="text-sm">ایجاد شده: {result.created} | آپدیت: {result.updated} | خطا: {result.errors}</div>
            </div>
          ) : (
            <div className="text-red-400">❌ {result.error}</div>
          )}
        </div>
      )}

      <button onClick={handleUpload} disabled={!file || status === 'loading'}
        className="btn-primary w-full py-3 text-sm font-semibold disabled:opacity-50">
        {status === 'loading' ? 'در حال آپلود...' : '📤 آپلود و وارد کردن محصولات'}
      </button>
    </div>
  )
}
