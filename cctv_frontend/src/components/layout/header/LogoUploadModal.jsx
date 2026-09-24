import { useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import api from '../../../services/api'

// ─── مودال آپلود لوگو (فقط برای کاربران staff) ────────────────
export default function LogoUploadModal({ onClose, onUploaded }) {
  const fileRef = useRef(null)
  const queryClient = useQueryClient()
  const [uploading, setUploading] = useState(false)
  const [preview, setPreview] = useState(null)
  const [error, setError] = useState('')
  const [dragging, setDragging] = useState(false)

  function handleFile(e) {
    const f = e.target.files?.[0]
    if (!f) return
    if (!f.type.startsWith('image/')) { setError('فقط فایل تصویری'); return }
    if (f.size > 2 * 1024 * 1024) { setError('حداکثر ۲ مگابایت'); return }
    setError('')
    setPreview(URL.createObjectURL(f))
  }

  async function upload() {
    if (!preview) return
    setUploading(true)
    try {
      const fd = new FormData()
      fd.append('logo', fileRef.current.files[0])
      await api.post('/core/upload-logo/', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
      await queryClient.invalidateQueries({ queryKey: ['site-settings'] })
      onUploaded?.()
      onClose()
    } catch (e) {
      setError('خطا در آپلود')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/70 backdrop-blur-md animate-fade-in-fast"
      onClick={onClose}
    >
      <div
        className="card max-w-md w-full p-6 relative animate-modal-in"
        onClick={(e) => e.stopPropagation()}
        style={{ boxShadow: 'var(--shadow-modal)' }}
      >
        <h3 className="text-lg font-bold mb-4 tracking-tight">آپلود لوگو</h3>
        <input ref={fileRef} type="file" accept="image/*" onChange={handleFile} className="hidden" />
        <div
          onClick={() => fileRef.current?.click()}
          onDragEnter={(e) => { e.preventDefault(); setDragging(true) }}
          onDragLeave={(e) => { e.preventDefault(); setDragging(false) }}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault(); setDragging(false)
            const f = e.dataTransfer.files?.[0]
            if (f) { fileRef.current.files = e.dataTransfer.files; handleFile({ target: { files: [f] } }) }
          }}
          className="border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-colors"
          style={{
            borderColor: dragging ? 'var(--color-brand)' : 'var(--color-border)',
            backgroundColor: dragging ? 'var(--color-brand-softer)' : 'transparent',
          }}
        >
          {preview ? (
            <img
              src={preview}
              alt="preview"
              className="max-h-32 mx-auto object-contain animate-scale-in"
            />
          ) : (
            <div className="text-sm text-[var(--color-text-muted)]">
              <div className="text-3xl mb-2 animate-bounce-soft">
                📁
              </div>
              برای انتخاب کلیک کنید یا فایل را رها کنید
            </div>
          )}
        </div>
        <p className="text-[10px] text-[var(--color-text-muted)] mt-2">
          ابعاد پیشنهادی: ارتفاع حدود ۱۲۸ پیکسل، عرض آزاد — PNG با پس‌زمینه شفاف یا SVG — حداکثر ۲ مگابایت.
        </p>
        {error && (
          <div className="text-alert-red text-sm mt-3 animate-error-in">
            {error}
          </div>
        )}
        <div className="flex gap-2 mt-4">
          <button
            onClick={upload}
            disabled={uploading || !preview}
            className="btn-gold flex-1 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {uploading ? 'در حال آپلود...' : 'آپلود'}
          </button>
          <button
            onClick={onClose}
            className="btn-ghost flex-1"
          >
            انصراف
          </button>
        </div>
      </div>
    </div>
  )
}
