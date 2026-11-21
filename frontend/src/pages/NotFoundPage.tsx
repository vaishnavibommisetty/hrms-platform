import { Link } from 'react-router-dom'
import { Home, AlertTriangle } from 'lucide-react'

export default function NotFoundPage() {
  return (
    <div className="p-8 flex flex-col items-center justify-center min-h-96 text-center">
      <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mb-4">
        <AlertTriangle className="w-8 h-8 text-slate-400" />
      </div>
      <h2 className="text-2xl font-bold text-slate-900 mb-2">Page not found</h2>
      <p className="text-slate-500 text-sm mb-6">This page is coming soon or doesn't exist yet.</p>
      <Link
        to="/dashboard"
        className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-xl hover:bg-indigo-700 transition-colors"
      >
        <Home className="w-4 h-4" />
        Go to Dashboard
      </Link>
    </div>
  )
}
