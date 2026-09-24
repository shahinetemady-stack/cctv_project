import { lazy, Suspense, useEffect } from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import Layout from './components/layout/Layout'
import useAuthStore from './store/useAuthStore'
import { authService } from './services/auth'
import { PageLoader } from './components/ui'
import ErrorBoundary from './components/ui/ErrorBoundary'

// ─── صفحات ادمین — lazy load برای کاهش باندل اولیه ──────────
const AdminOrdersPage = lazy(() => import('./pages/admin/AdminOrdersPage'))
const AdminProductsPage = lazy(() => import('./pages/admin/AdminProductsPage'))
const AdminPackagesPage = lazy(() => import('./pages/admin/AdminPackagesPage'))
const PricingPage = lazy(() => import('./pages/admin/PricingPage'))
const ContentPage = lazy(() => import('./pages/admin/ContentPage'))
const AdminLogsPage = lazy(() => import('./pages/admin/AdminLogsPage'))
const AdminCategoriesPage = lazy(() => import('./pages/admin/AdminCategoriesPage'))
const AdminCategoryFieldsPage = lazy(() => import('./pages/admin/AdminCategoryFieldsPage'))
const DashboardPage = lazy(() => import('./pages/admin/DashboardPage'))
const ContactsPage = lazy(() => import('./pages/admin/ContactsPage'))
const PurchaseInvoicePage = lazy(() => import('./pages/admin/PurchaseInvoicePage'))
const BalancePage = lazy(() => import('./pages/admin/BalancePage'))
const InvoicePrintPage = lazy(() => import('./pages/admin/InvoicePrintPage'))
const SaleInvoicePage = lazy(() => import('./pages/admin/SaleInvoicePage'))
const PayrollPage = lazy(() => import('./pages/admin/PayrollPage'))
const ExpensesPage = lazy(() => import('./pages/admin/ExpensesPage'))
const PaymentsPage = lazy(() => import('./pages/admin/PaymentsPage'))
const AdminBanksPage = lazy(() => import('./pages/admin/AdminBanksPage'))
const FinancialReportsPage = lazy(() => import('./pages/admin/FinancialReportsPage'))
const RolesPage = lazy(() => import('./pages/admin/RolesPage'))
const KardexPage = lazy(() => import('./pages/admin/KardexPage'))
const WarehousesPage = lazy(() => import('./pages/admin/WarehousesPage'))
const BackupPage = lazy(() => import('./pages/admin/BackupPage'))
const ReceiptsPage = lazy(() => import('./pages/admin/ReceiptsPage'))
const AgingReportPage = lazy(() => import('./pages/admin/AgingReportPage'))
const ShortageReportPage = lazy(() => import('./pages/admin/ShortageReportPage'))
const RejectReportPage = lazy(() => import('./pages/admin/RejectReportPage'))
const ReturnsPage = lazy(() => import('./pages/admin/ReturnsPage'))
const SmsSettingsPage = lazy(() => import('./pages/admin/SmsSettingsPage'))
const ClubSettingsPage = lazy(() => import('./pages/admin/ClubSettingsPage'))
const SmsCampaignPage = lazy(() => import('./pages/admin/SmsCampaignPage'))
const AssistantSettingsPage = lazy(() => import('./pages/admin/AssistantSettingsPage'))
const LeadsPage = lazy(() => import('./pages/admin/LeadsPage'))
// AccountPage سنگین است (recharts) — lazy تا وارد باندل اصلی نشود
const AccountPage = lazy(() => import('./pages/AccountPage'))

import HomePage from './pages/HomePage'
// همه صفحات غیرخانگی lazy — کاهش JS اولیه در لود موبایل
const BlogPage = lazy(() => import('./pages/BlogPage'))
const ArticleDetailPage = lazy(() => import('./pages/ArticleDetailPage'))
const VideosPage = lazy(() => import('./pages/VideosPage'))
const VideoDetailPage = lazy(() => import('./pages/VideoDetailPage'))
const DownloadsPage = lazy(() => import('./pages/DownloadsPage'))
const TermsPage = lazy(() => import('./pages/TermsPage'))
const PrivacyPage = lazy(() => import('./pages/PrivacyPage'))
const AboutPage = lazy(() => import('./pages/AboutPage'))
const ClubPage = lazy(() => import('./pages/ClubPage'))
const ContactPage = lazy(() => import('./pages/ContactPage'))
const TrackingPage = lazy(() => import('./pages/TrackingPage'))
const ChinaOrderPage = lazy(() => import('./pages/ChinaOrderPage'))
const FAQPage = lazy(() => import('./pages/FAQPage'))
const PackagesPage = lazy(() => import('./pages/PackagesPage'))
const PackageDetailPage = lazy(() => import('./pages/PackageDetailPage'))
const ProductsPage = lazy(() => import('./pages/ProductsPage'))
const CategoryPage = lazy(() => import('./pages/CategoryPage'))
const ProductDetailPage = lazy(() => import('./pages/ProductDetailPage'))
const ComparePage = lazy(() => import('./pages/ComparePage'))
const CartPage = lazy(() => import('./pages/CartPage'))
const OrdersPage = lazy(() => import('./pages/account/OrdersPage'))
const InquiryCartPage = lazy(() => import('./pages/InquiryCartPage'))
const PaymentResultPage = lazy(() => import('./pages/PaymentResultPage'))
const LoginPage = lazy(() => import('./pages/auth/LoginPage').then(m => ({ default: m.LoginPage })))
const RegisterPage = lazy(() => import('./pages/auth/RegisterPage'))

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
  // تازه‌سازی اطلاعات کاربر در هر لود اپ — تا تغییر نقش/سطح همکار توسط ادمین
  // بدون نیاز به خروج و ورود مجدد در منو و قیمت‌ها اعمال شود
  const accessToken = useAuthStore((s) => s.accessToken)
  const updateUser = useAuthStore((s) => s.updateUser)
  useEffect(() => {
    if (!accessToken) return
    authService.getMe().then(updateUser).catch(() => {})
    // فقط یک بار در mount — accessToken در dependency نیاید تا بعد از login دوباره نزند
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <ErrorBoundary>
      <Suspense fallback={<PageLoader />}>
        <Routes>
      <Route path="invoice-print" element={<InvoicePrintPage />} />
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="blog" element={<BlogPage />} />
        <Route path="blog/category/:categorySlug" element={<BlogPage />} />
        <Route path="blog/:slug" element={<ArticleDetailPage />} />
        <Route path="videos" element={<VideosPage />} />
        <Route path="videos/:slug" element={<VideoDetailPage />} />

        <Route path="downloads" element={<DownloadsPage />} />
        <Route path="terms" element={<TermsPage />} />
        <Route path="privacy" element={<PrivacyPage />} />
        <Route path="about" element={<AboutPage />} />
        <Route path="club" element={<ClubPage />} />
        <Route path="contact" element={<ContactPage />} />
        <Route path="track" element={<TrackingPage />} />
        <Route path="track/:orderNumber" element={<TrackingPage />} />
        <Route path="china-order"  element={<ChinaOrderPage />} />
        <Route path="china-order/faq" element={<FAQPage />} />
        <Route path="packages" element={<PackagesPage />} />
        <Route path="packages/:slug" element={<PackageDetailPage />} />
        <Route path="products" element={<ProductsPage />} />
        <Route path="products/:slug" element={<ProductDetailPage />} />
        <Route path="compare" element={<ComparePage />} />
        <Route path="categories/:slug" element={<CategoryPage />} />

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
        <Route path="admin/payroll" element={<RequireAuth><PayrollPage /></RequireAuth>} />
        <Route path="admin/expenses" element={<RequireAuth><ExpensesPage /></RequireAuth>} />
        <Route path="admin/returns" element={<RequireAuth><ReturnsPage /></RequireAuth>} />
        <Route path="admin/banks" element={<RequireAuth><AdminBanksPage /></RequireAuth>} />
        <Route path="admin/financial" element={<RequireAuth><FinancialReportsPage /></RequireAuth>} />
        <Route path="admin/roles" element={<RequireAuth><RolesPage /></RequireAuth>} />
        <Route path="admin/reports" element={<Navigate to="/admin/contacts" replace />} />
        <Route path="admin/kardex" element={<RequireAuth><KardexPage /></RequireAuth>} />
        <Route path="admin/warehouses" element={<RequireAuth><WarehousesPage /></RequireAuth>} />
        <Route path="admin/products" element={<RequireAuth><AdminProductsPage /></RequireAuth>} />
        <Route path="admin/packages" element={<RequireAuth><AdminPackagesPage /></RequireAuth>} />
        <Route path="admin/pricing" element={<RequireAuth><PricingPage /></RequireAuth>} />
        <Route path="admin/content" element={<RequireAuth><ContentPage /></RequireAuth>} />
        <Route path="admin/logs" element={<RequireAuth><AdminLogsPage /></RequireAuth>} />
        <Route path="admin/categories" element={<RequireAuth><AdminCategoriesPage /></RequireAuth>} />
        <Route path="admin/category-fields" element={<RequireAuth><AdminCategoryFieldsPage /></RequireAuth>} />
        <Route path="admin/backup" element={<RequireAuth><BackupPage /></RequireAuth>} />
        <Route path="admin/sms-settings" element={<RequireAuth><SmsSettingsPage /></RequireAuth>} />
        <Route path="admin/assistant-settings" element={<RequireAuth><AssistantSettingsPage /></RequireAuth>} />
        <Route path="admin/club-settings" element={<RequireAuth><ClubSettingsPage /></RequireAuth>} />
        <Route path="admin/sms-campaign" element={<RequireAuth><SmsCampaignPage /></RequireAuth>} />
        <Route path="admin/leads" element={<RequireAuth><LeadsPage /></RequireAuth>} />
        <Route path="admin/receipts" element={<RequireAuth><ReceiptsPage /></RequireAuth>} />
        <Route path="admin/aging" element={<RequireAuth><AgingReportPage /></RequireAuth>} />
        <Route path="admin/shortage" element={<RequireAuth><ShortageReportPage /></RequireAuth>} />
        <Route path="admin/reject-report" element={<RequireAuth><RejectReportPage /></RequireAuth>} />

        <Route path="inquiry-cart" element={<RequirePartner><InquiryCartPage /></RequirePartner>} />

        <Route path="auth/login" element={<GuestOnly><LoginPage /></GuestOnly>} />
        <Route path="auth/register" element={<GuestOnly><RegisterPage /></GuestOnly>} />

        <Route path="auth/pending" element={
          <div className="container-main py-20 text-center max-w-sm">
            <div className="text-5xl mb-4">⏳</div>
            <h2 className="font-display font-bold text-xl text-white mb-3">در انتظار تأیید ادمین</h2>
            <p className="text-gray-steel text-sm leading-7">
              درخواست همکاری شما ثبت شد و پس از بررسی مدارک/کانال کاری، سطح سیلور شما فعال خواهد شد.
              نتیجه را با پیامک اطلاع می‌دهیم.
            </p>
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
      </Suspense>
    </ErrorBoundary>
  )
}
