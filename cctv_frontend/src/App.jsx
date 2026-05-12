import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import Layout from './components/layout/Layout'
import useAuthStore from './store/useAuthStore'
import DashboardPage from './pages/admin/DashboardPage'

// Pages
import HomePage from './pages/HomePage'
import ProductsPage from './pages/ProductsPage'
import ProductDetailPage from './pages/ProductDetailPage'
import CartPage from './pages/CartPage'
import OrdersPage from './pages/account/OrdersPage'
import InquiryCartPage from './pages/InquiryCartPage'
import AccountPage from './pages/AccountPage'
import PaymentResultPage from './pages/PaymentResultPage'
import { LoginPage } from './pages/auth/LoginPage'
import RegisterPage from './pages/auth/RegisterPage'

// ─── Guards ───────────────────────────────────────────────────────────────────
function RequireAuth({ children }) {
  const { isAuthenticated } = useAuthStore()
  const location = useLocation()
  if (!isAuthenticated()) return <Navigate to="/auth/login" state={{ from: location }} replace />
  return children
}

function RequirePartner({ children }) {
  const { isAuthenticated, isPartner } = useAuthStore()
  const location = useLocation()
  if (!isAuthenticated()) return <Navigate to="/auth/login" state={{ from: location }} replace />
  if (!isPartner()) return (
    <div className="container-main py-20 text-center">
      <div className="text-5xl mb-4">🔒</div>
      <h2 className="font-display font-bold text-xl text-white mb-3">دسترسی محدود</h2>
      <p className="text-gray-steel text-sm">این بخش فقط برای مشتریان همکار تأیید شده است.</p>
    </div>
  )
  return children
}

function GuestOnly({ children }) {
  const { isAuthenticated } = useAuthStore()
  if (isAuthenticated()) return <Navigate to="/" replace />
  return children
}

// ─── App ──────────────────────────────────────────────────────────────────────
export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        {/* عمومی */}
        <Route index element={<HomePage />} />
        <Route path="products" element={<ProductsPage />} />
        <Route path="products/:slug" element={<ProductDetailPage />} />

        {/* پرداخت */}
        <Route path="payment/success" element={<PaymentResultPage success={true} />} />
        <Route path="payment/failure" element={<PaymentResultPage success={false} />} />

        {/* فقط لاگین‌شده */}
        <Route path="cart" element={<RequireAuth><CartPage /></RequireAuth>} />
        <Route path="account/orders" element={<RequireAuth><OrdersPage /></RequireAuth>} />
        <Route path="admin/dashboard" element={<RequireAuth><DashboardPage /></RequireAuth>} />
        <Route path="account" element={<RequireAuth><AccountPage /></RequireAuth>} />
        <Route path="account/orders" element={<RequireAuth><AccountPage /></RequireAuth>} />

        {/* فقط همکار */}
        <Route path="inquiry-cart" element={<RequirePartner><InquiryCartPage /></RequirePartner>} />

        {/* فقط مهمان */}
        <Route path="auth/login" element={<GuestOnly><LoginPage /></GuestOnly>} />
        <Route path="auth/register" element={<GuestOnly><RegisterPage /></GuestOnly>} />

        {/* در انتظار تأیید */}
        <Route path="auth/pending" element={
          <div className="container-main py-20 text-center max-w-sm">
            <div className="text-5xl mb-4">⏳</div>
            <h2 className="font-display font-bold text-xl text-white mb-3">
              در انتظار تأیید ادمین
            </h2>
            <p className="text-gray-steel text-sm">
              درخواست همکاری شما ثبت شد. بعد از بررسی ادمین از طریق ایمیل اطلاع داده می‌شود.
            </p>
          </div>
        } />

        {/* ۴۰۴ */}
        <Route path="*" element={
          <div className="container-main py-20 text-center">
            <div className="text-6xl font-display font-black text-brand/20 mb-4">۴۰۴</div>
            <h2 className="font-display font-bold text-xl text-white mb-3">صفحه یافت نشد</h2>
            <a href="/" className="btn-primary">بازگشت به خانه</a>
          </div>
        } />
      </Route>
    </Routes>
  )
}
