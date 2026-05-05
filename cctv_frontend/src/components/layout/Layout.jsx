import { Outlet } from 'react-router-dom'
import { useEffect } from 'react'
import Header from './Header'
import Footer from './Footer'
import useThemeStore from '../../store/useThemeStore'

export default function Layout() {
  const { init } = useThemeStore()
  useEffect(() => init(), [])

  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <main className="flex-1">
        <Outlet />
      </main>
      <Footer />
    </div>
  )
}
