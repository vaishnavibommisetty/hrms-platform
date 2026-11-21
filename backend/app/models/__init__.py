# Import all models here so SQLAlchemy registers them
from app.models.company import Company
from app.models.user import User, UserRole
from app.models.employee import Employee, Department, Designation, EmploymentStatus, EmploymentType, Gender
from app.models.salary import (SalaryComponent, SalaryStructure,
                                SalaryStructureComponent, EmployeeSalaryAssignment,
                                ComponentType, CalculationType)
from app.models.compensation import (CompensationCycle, CompensationPlan,
                                     CompensationRule, CycleStatus, PlanStatus)
from app.models.performance import (PerformanceCycle, KPI, PerformanceReview,
                                    KPIScore, ReviewStatus)
from app.models.payroll import PayrollRun, Payslip, PayslipItem, PayrollStatus
from app.models.workflow import (WorkflowDefinition, ApprovalRequest, ApprovalAction,
                                 WorkflowEntityType, RequestStatus, ActionType)
from app.models.qa import (TestPlan, TestCase, TestExecution, Defect,
                           TestType, ExecutionStatus, DefectSeverity, DefectPriority, DefectStatus)
from app.models.audit import AuditLog

__all__ = [
    "Company", "User", "UserRole",
    "Employee", "Department", "Designation", "EmploymentStatus", "EmploymentType", "Gender",
    "SalaryComponent", "SalaryStructure", "SalaryStructureComponent", "EmployeeSalaryAssignment",
    "ComponentType", "CalculationType",
    "CompensationCycle", "CompensationPlan", "CompensationRule", "CycleStatus", "PlanStatus",
    "PerformanceCycle", "KPI", "PerformanceReview", "KPIScore", "ReviewStatus",
    "PayrollRun", "Payslip", "PayslipItem", "PayrollStatus",
    "WorkflowDefinition", "ApprovalRequest", "ApprovalAction",
    "WorkflowEntityType", "RequestStatus", "ActionType",
    "TestPlan", "TestCase", "TestExecution", "Defect",
    "TestType", "ExecutionStatus", "DefectSeverity", "DefectPriority", "DefectStatus",
    "AuditLog",
]
