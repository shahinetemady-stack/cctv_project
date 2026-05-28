import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { orderService } from '../../services/orders'
import { PageLoader } from '../../components/ui'
import useAuthStore from '../../store/useAuthStore'

const STATUS = {
  pending:          { label: 'در انتظار تأیید',    color: '#FF9500', bg: 'rgba(255,149,0,0.1)' },
  confirmed:        { label: 'تأیید شده',           color: '#0066FF', bg: 'rgba(0,102,255,0.1)' },
  awaiting_payment: { label: 'در انتظار پرداخت',   color: '#8B5CF6', bg: 'rgba(139,92,246,0.1)' },
  paid:             { label: 'پرداخت شده',          color: '#00C896', bg: 'rgba(0,200,150,0.1)' },
  ready_to_ship:    { label: 'آماده ارسال',         color: '#00C896', bg: 'rgba(0,200,150,0.1)' },
  shipped:          { label: 'ارسال شده',           color: '#0066FF', bg: 'rgba(0,102,255,0.1)' },
  cancelled:        { label: 'لغو شده',             color: '#FF3B3B', bg: 'rgba(255,59,59,0.1)' },
}

const SHIPPING = { post: '📮 پست', courier: '🛵 پیک', freight: '🚛 باربری' }
const PAYMENT_METHOD = { cash: 'نقد', transfer: 'کارت به کارت', online: 'آنلاین', check: 'چک' }

function ProformaInvoice({ order, onClose }) {
  const { user } = useAuthStore()
  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}>
        <div className="p-8" dir="rtl" style={{fontFamily:'Arial,sans-serif',color:'#000'}}>
          {/* هدر */}
          <div style={{display:'flex',justifyContent:'space-between',marginBottom:24,borderBottom:'2px solid #0066FF',paddingBottom:16}}>
            <div>
              <div style={{fontSize:20,fontWeight:'bold',color:'#0066FF'}}>فروشگاه قطعات دوربین مداربسته</div>
              <div style={{fontSize:11,color:'#666',marginTop:4}}>cctvparts.ir</div>
            </div>
            <div style={{textAlign:'left'}}>
              <div style={{fontSize:15,fontWeight:'bold'}}>پیش‌فاکتور</div>
              <div style={{fontSize:11,color:'#666'}}>شماره: {order.order_number}</div>
              <div style={{fontSize:11,color:'#666'}}>تاریخ: {new Date(order.created_at).toLocaleDateString('fa-IR')}</div>
            </div>
          </div>

          {/* اطلاعات مشتری */}
          <div style={{background:'#f8f9fa',borderRadius:8,padding:16,marginBottom:20,fontSize:12}}>
            <div style={{fontWeight:'bold',marginBottom:8}}>اطلاعات خریدار</div>
            <div>نام: {user?.first_name} {user?.last_name}</div>
            <div>موبایل: {user?.phone}</div>
            {order.shipping_address && <div>آدرس: {order.shipping_address}</div>}
            {order.shipping_method && (
              <div>روش ارسال: {SHIPPING[order.shipping_method] || order.shipping_method}
                {order.freight_company && ` — ${order.freight_company}`}
              </div>
            )}
          </div>

          {/* جدول */}
          <table style={{width:'100%',borderCollapse:'collapse',marginBottom:20,fontSize:12}}>
            <thead>
              <tr style={{background:'#0066FF',color:'white'}}>
                <th style={{padding:'8px 12px',textAlign:'right'}}>ردیف</th>
                <th style={{padding:'8px 12px',textAlign:'right'}}>محصول</th>
                <th style={{padding:'8px 12px',textAlign:'center'}}>تعداد</th>
                <th style={{padding:'8px 12px',textAlign:'left'}}>قیمت واحد</th>
                <th style={{padding:'8px 12px',textAlign:'left'}}>جمع</th>
              </tr>
            </thead>
            <tbody>
              {order.items?.map((item, i) => (
                <tr key={item.id} style={{background: i%2===0?'#fff':'#f8f9fa'}}>
                  <td style={{padding:'8px 12px',borderBottom:'1px solid #eee'}}>{i+1}</td>
                  <td style={{padding:'8px 12px',borderBottom:'1px solid #eee'}}>{item.variant_name || item.variant_sku}</td>
                  <td style={{padding:'8px 12px',borderBottom:'1px solid #eee',textAlign:'center'}}>{item.quantity}</td>
                  <td style={{padding:'8px 12px',borderBottom:'1px solid #eee',textAlign:'left'}}>{Number(item.unit_price||0).toLocaleString('fa-IR')}</td>
                  <td style={{padding:'8px 12px',borderBottom:'1px solid #eee',textAlign:'left',fontWeight:'bold'}}>{Number((item.unit_price||0)*item.quantity).toLocaleString('fa-IR')}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* جمع کل */}
          <div style={{display:'flex',justifyContent:'flex-end',marginBottom:16}}>
            <div style={{background:'#0066FF',color:'white',borderRadius:8,padding:'12px 24px',textAlign:'left'}}>
              <div style={{fontSize:11,opacity:0.8}}>جمع کل</div>
              <div style={{fontSize:18,fontWeight:'bold'}}>{Number(order.total_amount||0).toLocaleString('fa-IR')} تومان</div>
            </div>
          </div>

          {/* اطلاعات پرداخت */}
          {(order.status === 'paid' || order.paid_amount) && (
            <div style={{background:'#e8f5e9',borderRadius:8,padding:12,marginBottom:12,fontSize:12}}>
              <div style={{fontWeight:'bold',marginBottom:6,color:'#2e7d32'}}>✅ اطلاعات پرداخت</div>
              {order.paid_amount && <div>مبلغ پرداخت شده: {Number(order.paid_amount).toLocaleString('fa-IR')} تومان</div>}
              {order.payment_method && <div>روش پرداخت: {PAYMENT_METHOD[order.payment_method] || order.payment_method}</div>}
              {order.paid_at && <div>تاریخ پرداخت: {new Date(order.paid_at).toLocaleDateString('fa-IR')}</div>}
            </div>
          )}

          {/* اطلاعات ارسال */}
          {order.tracking_code && (
            <div style={{background:'#e3f2fd',borderRadius:8,padding:12,marginBottom:12,fontSize:12}}>
              <div style={{fontWeight:'bold',marginBottom:6,color:'#1565c0'}}>📦 اطلاعات ارسال</div>
              <div>کد رهگیری: <span style={{fontFamily:'monospace',fontSize:14}}>{order.tracking_code}</span></div>
              {order.shipping_method && <div>روش ارسال: {SHIPPING[order.shipping_method]}</div>}
            </div>
          )}

          <div style={{marginTop:16,fontSize:10,color:'#999',textAlign:'center',borderTop:'1px solid #eee',paddingTop:12}}>
            این پیش‌فاکتور به صورت الکترونیکی صادر شده — cctvparts.ir
          </div>
        </div>

        <div className="flex gap-3 p-4 border-t">
          <button onClick={() => window.print()}
            className="flex-1 bg-blue-600 text-white rounded-xl py-2.5 text-sm font-medium hover:bg-blue-700">
            🖨️ چاپ / دانلود PDF
          </button>
          <button onClick={onClose} className="px-6 border border-gray-200 rounded-xl text-sm hover:bg-gray-50">
            بستن
          </button>
        </div>
      </div>
    </div>
  )
}

export default function OrdersPage() {
  const [params] = useSearchParams()
  const newOrder = params.get('new')
  const [selectedOrder, setSelectedOrder] = useState(null)

  const { data, isLoading } = useQuery({
    queryKey: ['orders'],
    queryFn: orderService.getOrders,
  })

  if (isLoading) return <PageLoader />
  const orders = data?.results || data || []

  return (
    <div className="container-main py-8 max-w-3xl">
      {selectedOrder && <ProformaInvoice order={selectedOrder} onClose={() => setSelectedOrder(null)} />}

      <h1 className="font-display font-bold text-2xl text-white mb-6">سفارش‌های من</h1>

      {newOrder && (
        <div className="card p-4 bg-green-500/10 border border-green-500/20 mb-6">
          <div className="flex items-center gap-3">
            <span className="text-2xl">✅</span>
            <div>
              <div className="font-bold text-green-400">سفارش ثبت شد!</div>
              <div className="text-sm text-gray-steel mt-1">شماره: <span className="font-mono text-white">{newOrder}</span></div>
              <div className="text-sm text-gray-steel">با شما تماس می‌گیریم و پرداخت را هماهنگ می‌کنیم.</div>
            </div>
          </div>
        </div>
      )}

      {orders.length === 0 ? (
        <div className="card p-12 text-center">
          <div className="text-5xl mb-4">📦</div>
          <div className="text-gray-steel">هنوز سفارشی ثبت نکرده‌اید</div>
          <Link to="/products" className="btn-primary mt-4 inline-block">مشاهده محصولات</Link>
        </div>
      ) : (
        <div className="space-y-4">
          {orders.map(order => {
            const st = STATUS[order.status] || {label: order.status, color:'#888', bg:'#f0f0f0'}
            return (
              <div key={order.id} className="card p-5">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <div className="font-mono text-sm text-white">{order.order_number}</div>
                    <div className="text-xs text-gray-steel mt-0.5">{new Date(order.created_at).toLocaleDateString('fa-IR')}</div>
                  </div>
                  <span className="text-xs px-3 py-1 rounded-full font-medium"
                    style={{color:st.color, background:st.bg}}>{st.label}</span>
                </div>

                {/* آیتم‌ها */}
                <div className="divide-y divide-white/5 mb-3">
                  {order.items?.slice(0,3).map(item => (
                    <div key={item.id} className="py-2 flex items-center justify-between text-sm">
                      <span className="text-gray-300 truncate">{item.variant_name || item.variant_sku}</span>
                      <span className="text-gray-steel flex-shrink-0 mr-2">×{item.quantity}</span>
                    </div>
                  ))}
                  {order.items?.length > 3 && (
                    <div className="py-2 text-xs text-gray-steel">+{order.items.length-3} محصول دیگر</div>
                  )}
                </div>

                {/* اطلاعات پرداخت */}
                {(order.status === 'paid' || order.paid_amount) && (
                  <div className="bg-green-500/10 rounded-lg px-3 py-2 mb-2">
                    <div className="text-xs text-green-400 font-medium mb-1">✅ پرداخت شده</div>
                    {order.paid_amount && (
                      <div className="text-xs text-gray-steel">
                        مبلغ: {Number(order.paid_amount).toLocaleString('fa-IR')} تومان
                        {order.payment_method && ` — ${PAYMENT_METHOD[order.payment_method]}`}
                      </div>
                    )}
                  </div>
                )}

                {/* اطلاعات ارسال */}
                {order.shipping_method && (
                  <div className="bg-blue-500/10 rounded-lg px-3 py-2 mb-2">
                    <div className="text-xs text-blue-400 font-medium mb-1">
                      {SHIPPING[order.shipping_method] || order.shipping_method}
                      {order.freight_company && ` — ${order.freight_company}`}
                    </div>
                    {order.tracking_code && (
                      <div className="text-xs text-gray-steel">
                        کد رهگیری: <span className="font-mono text-green-400">{order.tracking_code}</span>
                      </div>
                    )}
                  </div>
                )}

                <div className="flex items-center justify-between pt-3 border-t border-white/5">
                  <span className="font-bold text-brand dark:text-cyan text-sm">
                    {Number(order.total_amount||0).toLocaleString('fa-IR')} تومان
                  </span>
                  <div className="flex gap-2">
                    {order.tracking_code && (
                      <Link to={`/track/${order.order_number}`}
                        className="text-xs px-4 py-2 rounded-xl border border-green-500/30 text-green-400 hover:bg-green-500/10 transition-colors">
                        🚚 رهگیری
                      </Link>
                    )}
                    <button onClick={() => setSelectedOrder(order)}
                      className="text-xs px-4 py-2 rounded-xl border border-brand/30 text-brand dark:text-cyan hover:bg-brand/10 transition-colors">
                      📄 پیش‌فاکتور
                    </button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
