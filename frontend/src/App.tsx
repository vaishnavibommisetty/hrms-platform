import { Suspense, lazy } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import LoginPage from './pages/LoginPage'
import MainLayout from './components/layout/MainLayout'
import DashboardPage from './pages/dashboard/DashboardPage'
import EmployeesPage from './pages/employees/EmployeesPage'
import EmployeeDetailPage from './pages/employees/EmployeeDetailPage'
import NotFoundPage from './pages/NotFoundPage'
import { Loading } from './components/ui/kit'

const SalaryPage = lazy(() => import('./pages/salary/SalaryPage'))
const PayrollPage = lazy(() => import('./pages/payroll/PayrollPage'))
const PayrollRunPage = lazy(() => import('./pages/payroll/PayrollRunPage'))
const PerformancePage = lazy(() => import('./pages/performance/PerformancePage'))
const PerformanceCyclePage = lazy(() => import('./pages/performance/PerformanceCyclePage'))
const CompensationPage = lazy(() => import('./pages/compensation/CompensationPage'))
const CompensationCyclePage = lazy(() => import('./pages/compensation/CompensationCyclePage'))
const ApprovalsPage = lazy(() => import('./pages/approvals/ApprovalsPage'))
const QAPage = lazy(() => import('./pages/qa/QAPage'))
const TestPlanPage = lazy(() => import('./pages/qa/TestPlanPage'))
const ReportsPage = lazy(() => import('./pages/reports/ReportsPage'))
const AuditPage = lazy(() => import('./pages/audit/AuditPage'))

const page = (el: React.ReactNode) => <Suspense fallback={<Loading />}>{el}</Suspense>

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth()
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-slate-500 text-sm">Loading...</p>
        </div>
      </div>
    )
  }
  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
}

function AppRoutes() {
  const { user } = useAuth()

  return (
    <Routes>
      <Route
        path="/login"
        element={user ? <Navigate to="/dashboard" replace /> : <LoginPage />}
      />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <MainLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="employees" element={<EmployeesPage />} />
        <Route path="employees/:id" element={<EmployeeDetailPage />} />
        <Route path="salary" element={page(<SalaryPage />)} />
        <Route path="payroll" element={page(<PayrollPage />)} />
        <Route path="payroll/:id" element={page(<PayrollRunPage />)} />
        <Route path="performance" element={page(<PerformancePage />)} />
        <Route path="performance/:id" element={page(<PerformanceCyclePage />)} />
        <Route path="compensation" element={page(<CompensationPage />)} />
        <Route path="compensation/:id" element={page(<CompensationCyclePage />)} />
        <Route path="approvals" element={page(<ApprovalsPage />)} />
        <Route path="qa" element={page(<QAPage />)} />
        <Route path="qa/plans/:id" element={page(<TestPlanPage />)} />
        <Route path="reports" element={page(<ReportsPage />)} />
        <Route path="audit" element={page(<AuditPage />)} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}
