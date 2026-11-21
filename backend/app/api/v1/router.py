from fastapi import APIRouter
from app.api.v1 import (audit, auth, companies, compensation, dashboard, departments, employees,
                        payroll, performance, qa, reports, salary, workflows)

api_router = APIRouter()

for module in (auth, companies, employees, departments, dashboard, salary, payroll, performance,
               compensation, workflows, qa, reports, audit):
    api_router.include_router(module.router)
