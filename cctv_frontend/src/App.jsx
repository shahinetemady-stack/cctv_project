import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import Layout from './components/layout/Layout'
import useAuthStore from './store/useAuthStore'
import AdminOrdersPage from './pages/admin/AdminOrdersPage'
import DashboardPage from './pages/admin/DashboardPage'
import ContactsPage from './pages/admin/ContactsPage'
import PurchaseInvoicePage from './pages/admin/PurchaseInvoicePage'
import BalancePage from './pages/admin/BalancePage'
import ThemeSettingsPage from './pages/admin/ThemeSettingsPage'
import InvoicePrintPage from './pages/admin/InvoicePrintPage'
import SaleInvoicePage from './pages/admin/SaleInvoicePage'
import PaymentsPage from './pages/admin/PaymentsPage'
import FinancialReportsPage from './pages/admin/FinancialReportsPage'
import RolesPage from './pages/admin/RolesPage'
import ReportsPage from './pages/admin/ReportsPage'
import KardexPage from './pages/admin/KardexPage'

import HomePage from './pages/HomePage'
import BlogPage from './pages/BlogPage'
import ArticleDetailPage from './pages/ArticleDetailPage'
import VideosPage from './pages/VideosPage'
import VideoDetailPage from './pages/VideoDetailPage'
import PartSelectionGuidePage from './pages/PartSelectionGuidePage'
import DownloadsPage from './pages/DownloadsPage'
import TermsPage from './pages/TermsPage'
import PrivacyPage from './pages/PrivacyPage'
import BulkUploadPage from './pages/BulkUploadPage'
import TrackingPage from './pages/TrackingPage'
import ChinaOrderPage from './pages/ChinaOrderPage'
import PackagesPage from './pages/PackagesPage'
import PackageDetailPage from './pages/PackageDetailPage'
import ProductsPage from './pages/ProductsPage'
import ProductDetailPage from './pages/ProductDetailPage'
import CartPage from './pages/CartPage'
import OrdersPage from './pages/account/OrdersPage'
import InquiryCartPage from './pages/InquiryCartPage'
import AccountPage from './pages/AccountPage'
import PaymentResultPage from './pages/PaymentResultPage'
import { LoginPage } from './pages/auth/LoginPage'
import RegisterPage from './pages/auth/RegisterPage'

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

export default function App() {
  return (
    <Routes>
      <Route path="invoice-print" element={<InvoicePrintPage />} />
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="blog" element={<BlogPage />} />
        <Route path="blog/category/:categorySlug" element={<BlogPage />} />
        <Route path="blog/:slug" element={<ArticleDetailPage />} />
        <Route path="videos" element={<VideosPage />} />
        <Route path="videos/:slug" element={<VideoDetailPage />} />
        <Route path="guides/part-selection" element={<PartSelectionGuidePage />} />
        
        <Route path="downloads" element={<DownloadsPage />} />
        <Route path="terms" element={<TermsPage />} />
        <Route path="privacy" element={<PrivacyPage />} />
        <Route path="admin/bulk-upload" element={<RequireAuth><BulkUploadPage /></RequireAuth>} />
        <Route path="track" element={<TrackingPage />} />
        <Route path="track/:orderNumber" element={<TrackingPage />} />
        <Route path="china-order"  element={<ChinaOrderPage />} />
        <Route path="packages" element={<PackagesPage />} />
        <Route path="packages/:slug" element={<PackageDetailPage />} />
        <Route path="products" element={<ProductsPage />} />
        <Route path="products/:slug" element={<ProductDetailPage />} />

        <Route path="payment/success" element={<PaymentResultPage success={true} />} />
        <Route path="payment/failure" element={<PaymentResultPage success={false} />} />

        <Route path="cart" element={<RequireAuth><CartPage /></RequireAuth>} />
        <Route path="account/orders" element={<RequireAuth><OrdersPage /></RequireAuth>} />
        <Route path="account" element={<RequireAuth><AccountPage /></RequireAuth>} />
        <Route path="admin/orders-management" element={<RequireAuth><AdminOrdersPage /></RequireAuth>} />
        <Route path="admin/dashboard" element={<RequireAuth><DashboardPage /></RequireAuth>} />
                <Route path="admin/contacts" element={<RequireAuth><ContactsPage /></RequireAuth>} />
        <Route path="admin/purchases" element={<RequireAuth><PurchaseInvoicePage /></RequireAuth>} />
        <Route path="admin/balance" element={<RequireAuth><BalancePage /></RequireAuth>} />
        <Route path="admin/sales" element={<RequireAuth><SaleInvoicePage /></RequireAuth>} />
        <Route path="admin/payments" element={<RequireAuth><PaymentsPage /></RequireAuth>} />
        <Route path="admin/financial" element={<RequireAuth><FinancialReportsPage /></RequireAuth>} />
        <Route path="admin/roles" element={<RequireAuth><RolesPage /></RequireAuth>} />
        <Route path="admin/reports" element={<RequireAuth><ReportsPage /></RequireAuth>} />
        <Route path="admin/theme" element={<RequireAuth><ThemeSettingsPage /></RequireAuth>} />
        <Route path="admin/kardex" element={<RequireAuth><KardexPage /></RequireAuth>} />

        <Route path="inquiry-cart" element={<RequirePartner><InquiryCartPage /></RequirePartner>} />

        <Route path="auth/login" element={<GuestOnly><LoginPage /></GuestOnly>} />
        <Route path="auth/register" element={<GuestOnly><RegisterPage /></GuestOnly>} />

        <Route path="auth/pending" element={
          <div className="container-main py-20 text-center max-w-sm">
            <div className="text-5xl mb-4">⏳</div>
            <h2 className="font-display font-bold text-xl text-white mb-3">در انتظار تأیید ادمین</h2>
            <p className="text-gray-steel text-sm">درخواست همکاری شما ثبت شد.</p>
          </div>
        } />

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