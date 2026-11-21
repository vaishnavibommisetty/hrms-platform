from fastapi import APIRouter
from app.api.v1 import auth, companies, employees, departments, dashboard

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(companies.router)
api_router.include_router(employees.router)
api_router.include_router(departments.router)
api_router.include_router(dashboard.router)

# Placeholder routers — implemented in Phase 3+
# from app.api.v1 import salary, compensation, performance, payroll, workflows, qa, reports, audit
# api_router.include_router(salary.router)
# api_router.include_router(compensation.router)
# api_router.include_router(performance.router)
# api_router.include_router(payroll.router)
# api_router.include_router(workflows.router)
# api_router.include_router(qa.router)
# api_router.include_router(reports.router)
# api_router.include_router(audit.router)
