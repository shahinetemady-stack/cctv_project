import { useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import api from '../../../services/api'

const SPRING_SNAPPY = { type: 'spring', stiffness: 500, damping: 35 }
const SPRING_SMOOTH = { type: 'spring', stiffness: 300, damping: 30 }

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
    <motion.div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/70 backdrop-blur-md"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.18 }}
      onClick={onClose}
    >
      <motion.div
        className="card max-w-md w-full p-6 relative"
        initial={{ opacity: 0, scale: 0.96, y: 8 }}
        animate={{ opacity: 1, scale: 1, y: 0, transition: SPRING_SNAPPY }}
        exit={{ opacity: 0, scale: 0.96, y: 8, transition: { duration: 0.15 } }}
        onClick={(e) => e.stopPropagation()}
        style={{ boxShadow: 'var(--shadow-modal)' }}
      >
        <h3 className="text-lg font-bold mb-4 tracking-tight">آپلود لوگو</h3>
        <input ref={fileRef} type="file" accept="image/*" onChange={handleFile} className="hidden" />
        <motion.div
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
          animate={{
            borderColor: dragging ? 'var(--color-brand)' : 'var(--color-border)',
            backgroundColor: dragging ? 'var(--color-brand-softer)' : 'transparent',
          }}
          transition={SPRING_SNAPPY}
        >
          {preview ? (
            <motion.img
              src={preview}
              alt="preview"
              className="max-h-32 mx-auto object-contain"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={SPRING_SMOOTH}
            />
          ) : (
            <div className="text-sm text-[var(--color-text-muted)]">
              <motion.div
                className="text-3xl mb-2"
                animate={{ y: [0, -4, 0] }}
                transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
              >
                📁
              </motion.div>
              برای انتخاب کلیک کنید یا فایل را رها کنید
            </div>
          )}
        </motion.div>
        <p className="text-[10px] text-[var(--color-text-muted)] mt-2">
          ابعاد پیشنهادی: ارتفاع حدود ۱۲۸ پیکسل، عرض آزاد — PNG با پس‌زمینه شفاف یا SVG — حداکثر ۲ مگابایت.
        </p>
        {error && (
          <motion.div
            className="text-alert-red text-sm mt-3"
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={SPRING_SNAPPY}
          >
            {error}
          </motion.div>
        )}
        <div className="flex gap-2 mt-4">
          <motion.button
            onClick={upload}
            disabled={uploading || !preview}
            whileHover={{ scale: 1.02, y: -1 }}
            whileTap={{ scale: 0.97, y: 0 }}
            transition={SPRING_SNAPPY}
            className="btn-gold flex-1 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {uploading ? 'در حال آپلود...' : 'آپلود'}
          </motion.button>
          <motion.button
            onClick={onClose}
            whileHover={{ scale: 1.02, y: -1 }}
            whileTap={{ scale: 0.97, y: 0 }}
            transition={SPRING_SNAPPY}
            className="btn-ghost flex-1"
          >
            انصراف
          </motion.button>
        </div>
      </motion.div>
    </motion.div>
  )
}
