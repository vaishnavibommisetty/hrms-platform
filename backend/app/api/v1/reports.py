"""
SQL Reports.

Every report is a hand-written SQL query that runs against the live database.
Each query is parameterised with :company_id so one company can never see another's data.
Where PostgreSQL and SQLite differ (date maths), a dialect-specific variant is provided;
the PostgreSQL version is the one shown to users, since production runs on PostgreSQL.
"""
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.v1._common import company_id_of, jsonable
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/reports", tags=["SQL Reports"])

REPORTS = [
    {
        "id": "headcount_by_department",
        "title": "Headcount by department",
        "category": "Workforce",
        "description": "Active headcount, leavers and average CTC per department.",
        "chart": {"type": "bar", "x": "department", "y": ["active", "on_leave"]},
        "sql": """
SELECT d.name                                                  AS department,
       COUNT(e.id)                                             AS headcount,
       SUM(CASE WHEN e.status = 'ACTIVE'   THEN 1 ELSE 0 END)  AS active,
       SUM(CASE WHEN e.status = 'ON_LEAVE' THEN 1 ELSE 0 END)  AS on_leave,
       ROUND(AVG(e.gross_ctc), 0)                              AS avg_ctc
FROM departments d
LEFT JOIN employees e
       ON e.department_id = d.id
      AND e.is_active = TRUE
WHERE d.company_id = :company_id
  AND d.is_active = TRUE
GROUP BY d.name
ORDER BY headcount DESC, department""",
    },
    {
        "id": "payroll_cost_by_department",
        "title": "Payroll cost by department (latest run)",
        "category": "Payroll",
        "description": "Gross, deductions and net pay per department for the most recent processed "
                       "payroll, with each department's share of the total.",
        "chart": {"type": "bar", "x": "department", "y": ["net_pay"]},
        "sql": """
WITH latest_run AS (
    SELECT id
    FROM payroll_runs
    WHERE company_id = :company_id
      AND status IN ('PENDING_APPROVAL', 'APPROVED', 'PAID')
    ORDER BY year DESC, month DESC
    LIMIT 1
)
SELECT d.name                                                         AS department,
       COUNT(p.id)                                                    AS employees,
       SUM(p.total_earnings)                                          AS gross_pay,
       SUM(p.total_deductions)                                        AS deductions,
       SUM(p.net_salary)                                              AS net_pay,
       ROUND(100.0 * SUM(p.net_salary) / SUM(SUM(p.net_salary)) OVER (), 1) AS share_pct
FROM payslips p
JOIN latest_run lr ON lr.id = p.payroll_run_id
JOIN employees e   ON e.id = p.employee_id
JOIN departments d ON d.id = e.department_id
GROUP BY d.name
ORDER BY net_pay DESC""",
    },
    {
        "id": "payroll_trend",
        "title": "Monthly payroll trend",
        "category": "Payroll",
        "description": "Total net payroll per month with the change from the previous month "
                       "(LAG window function).",
        "chart": {"type": "line", "x": "period", "y": ["total_net"]},
        "sql": """
SELECT year || '-' || CASE WHEN month < 10 THEN '0' ELSE '' END || month  AS period,
       status,
       total_employees,
       total_gross,
       total_deductions,
       total_net,
       total_net - LAG(total_net) OVER (ORDER BY year, month)              AS change_vs_prev_month
FROM payroll_runs
WHERE company_id = :company_id
  AND status <> 'CANCELLED'
  AND total_net IS NOT NULL
ORDER BY year, month""",
    },
    {
        "id": "payroll_variance",
        "title": "Payroll variance: this month vs last month",
        "category": "Payroll",
        "description": "Reconciliation check: employees whose net pay changed between the last "
                       "two payroll runs, plus joiners and leavers.",
        "chart": None,
        "sql": """
WITH runs AS (
    SELECT id, ROW_NUMBER() OVER (ORDER BY year DESC, month DESC) AS rn
    FROM payroll_runs
    WHERE company_id = :company_id
      AND status <> 'CANCELLED'
),
cur  AS (SELECT p.employee_id, p.net_salary FROM payslips p JOIN runs r ON r.id = p.payroll_run_id AND r.rn = 1),
prev AS (SELECT p.employee_id, p.net_salary FROM payslips p JOIN runs r ON r.id = p.payroll_run_id AND r.rn = 2),
ids  AS (SELECT employee_id FROM cur UNION SELECT employee_id FROM prev)
SELECT e.employee_code,
       e.first_name || ' ' || e.last_name                           AS employee,
       prev.net_salary                                              AS previous_net,
       cur.net_salary                                               AS current_net,
       COALESCE(cur.net_salary, 0) - COALESCE(prev.net_salary, 0)   AS difference,
       CASE WHEN prev.net_salary IS NULL THEN 'New in payroll'
            WHEN cur.net_salary  IS NULL THEN 'Dropped from payroll'
            WHEN cur.net_salary > prev.net_salary THEN 'Increase'
            ELSE 'Decrease' END                                     AS remark
FROM ids
JOIN employees e ON e.id = ids.employee_id
LEFT JOIN cur  ON cur.employee_id  = ids.employee_id
LEFT JOIN prev ON prev.employee_id = ids.employee_id
WHERE COALESCE(cur.net_salary, -1) <> COALESCE(prev.net_salary, -1)
ORDER BY ABS(COALESCE(cur.net_salary, 0) - COALESCE(prev.net_salary, 0)) DESC""",
    },
    {
        "id": "salary_bands",
        "title": "Salary band distribution",
        "category": "Compensation",
        "description": "How many employees fall into each annual CTC band.",
        "chart": {"type": "bar", "x": "band", "y": ["employees"]},
        "sql": """
SELECT CASE WHEN gross_ctc <  500000 THEN '1. Under 5 L'
            WHEN gross_ctc < 1000000 THEN '2. 5 to 10 L'
            WHEN gross_ctc < 1500000 THEN '3. 10 to 15 L'
            WHEN gross_ctc < 2500000 THEN '4. 15 to 25 L'
            ELSE '5. 25 L and above' END  AS band,
       COUNT(*)                          AS employees,
       MIN(gross_ctc)                    AS min_ctc,
       MAX(gross_ctc)                    AS max_ctc,
       ROUND(AVG(gross_ctc), 0)          AS avg_ctc
FROM employees
WHERE company_id = :company_id
  AND is_active = TRUE
  AND gross_ctc IS NOT NULL
GROUP BY band
ORDER BY band""",
    },
    {
        "id": "pay_vs_performance",
        "title": "Pay vs performance (compa-ratio)",
        "category": "Compensation",
        "description": "Each employee's latest review score next to their pay relative to the "
                       "department average. A compa-ratio below 1 for a top performer is a "
                       "retention risk.",
        "chart": None,
        "sql": """
WITH dept_avg AS (
    SELECT department_id, AVG(gross_ctc) AS avg_ctc
    FROM employees
    WHERE company_id = :company_id AND is_active = TRUE AND gross_ctc IS NOT NULL
    GROUP BY department_id
),
latest_review AS (
    SELECT r.employee_id, r.final_score,
           ROW_NUMBER() OVER (PARTITION BY r.employee_id ORDER BY r.completed_at DESC) AS rn
    FROM performance_reviews r
    WHERE r.status = 'COMPLETED'
)
SELECT RANK() OVER (ORDER BY lr.final_score DESC)        AS rank,
       e.employee_code,
       e.first_name || ' ' || e.last_name                AS employee,
       d.name                                            AS department,
       lr.final_score                                    AS review_score,
       e.gross_ctc,
       ROUND(e.gross_ctc / da.avg_ctc, 2)                AS compa_ratio,
       CASE WHEN lr.final_score >= 75 AND e.gross_ctc < da.avg_ctc
            THEN 'Underpaid high performer' ELSE '' END  AS flag
FROM employees e
JOIN latest_review lr ON lr.employee_id = e.id AND lr.rn = 1
JOIN dept_avg da      ON da.department_id = e.department_id
JOIN departments d    ON d.id = e.department_id
WHERE e.company_id = :company_id AND e.is_active = TRUE
ORDER BY rank
LIMIT 25""",
    },
    {
        "id": "compensation_by_department",
        "title": "Increment budget by department",
        "category": "Compensation",
        "description": "For the latest compensation cycle: average increment and the annual cost "
                       "of increments per department.",
        "chart": {"type": "bar", "x": "department", "y": ["increment_cost"]},
        "sql": """
WITH latest_cycle AS (
    SELECT id FROM compensation_cycles
    WHERE company_id = :company_id AND status <> 'CANCELLED'
    ORDER BY year DESC, id DESC
    LIMIT 1
)
SELECT d.name                                                         AS department,
       COUNT(p.id)                                                    AS employees,
       SUM(p.current_salary)                                          AS current_payroll,
       ROUND(AVG(COALESCE(p.final_increment_pct, p.manager_recommended_pct,
                          p.system_recommended_pct)), 2)              AS avg_increment_pct,
       ROUND(SUM(p.current_salary * COALESCE(p.final_increment_pct, p.manager_recommended_pct,
                          p.system_recommended_pct) / 100), 0)        AS increment_cost,
       SUM(CASE WHEN p.status = 'APPROVED' THEN 1 ELSE 0 END)         AS approved_plans
FROM compensation_plans p
JOIN latest_cycle lc ON lc.id = p.cycle_id
JOIN employees e     ON e.id = p.employee_id
JOIN departments d   ON d.id = e.department_id
WHERE p.status <> 'REJECTED'
GROUP BY d.name
ORDER BY increment_cost DESC""",
    },
    {
        "id": "rating_distribution",
        "title": "Performance rating distribution",
        "category": "Performance",
        "description": "Spread of final review scores in the most recent closed review cycle "
                       "(a quick bell-curve check).",
        "chart": {"type": "bar", "x": "rating", "y": ["employees"]},
        "sql": """
WITH latest_cycle AS (
    SELECT pc.id
    FROM performance_cycles pc
    WHERE pc.company_id = :company_id
      AND EXISTS (SELECT 1 FROM performance_reviews r
                  WHERE r.cycle_id = pc.id AND r.status = 'COMPLETED')
    ORDER BY CASE WHEN pc.status = 'COMPLETED' THEN 0 ELSE 1 END, pc.start_date DESC
    LIMIT 1
)
SELECT CASE WHEN r.final_score >= 90 THEN '1. Outstanding (90+)'
            WHEN r.final_score >= 75 THEN '2. Exceeds (75-89)'
            WHEN r.final_score >= 60 THEN '3. Meets (60-74)'
            WHEN r.final_score >= 40 THEN '4. Needs improvement (40-59)'
            ELSE '5. Unsatisfactory (<40)' END                AS rating,
       COUNT(*)                                               AS employees,
       ROUND(AVG(r.final_score), 1)                           AS avg_score,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)     AS pct_of_total
FROM performance_reviews r
JOIN latest_cycle lc ON lc.id = r.cycle_id
WHERE r.status = 'COMPLETED'
GROUP BY rating
ORDER BY rating""",
    },
    {
        "id": "gender_diversity",
        "title": "Gender diversity by department",
        "category": "Workforce",
        "description": "Gender split of active employees per department.",
        "chart": {"type": "bar", "x": "department", "y": ["male", "female", "other"]},
        "sql": """
SELECT d.name                                                        AS department,
       SUM(CASE WHEN e.gender = 'MALE'   THEN 1 ELSE 0 END)          AS male,
       SUM(CASE WHEN e.gender = 'FEMALE' THEN 1 ELSE 0 END)          AS female,
       SUM(CASE WHEN e.gender NOT IN ('MALE', 'FEMALE')
                  OR e.gender IS NULL THEN 1 ELSE 0 END)             AS other,
       COUNT(e.id)                                                   AS total,
       ROUND(100.0 * SUM(CASE WHEN e.gender = 'FEMALE' THEN 1 ELSE 0 END)
             / NULLIF(COUNT(e.id), 0), 1)                            AS female_pct
FROM departments d
JOIN employees e ON e.department_id = d.id AND e.is_active = TRUE
WHERE d.company_id = :company_id
GROUP BY d.name
ORDER BY total DESC""",
    },
    {
        "id": "tenure_attrition",
        "title": "Tenure and attrition",
        "category": "Workforce",
        "description": "Employees by years of service, with how many in each band have left.",
        "chart": {"type": "bar", "x": "tenure_band", "y": ["current", "exited"]},
        "sql": """
WITH t AS (
    SELECT status, (CURRENT_DATE - joining_date) / 365.25 AS years
    FROM employees
    WHERE company_id = :company_id
)
SELECT CASE WHEN years < 1 THEN '1. Under 1 year'
            WHEN years < 3 THEN '2. 1 to 3 years'
            WHEN years < 5 THEN '3. 3 to 5 years'
            ELSE '4. 5+ years' END                                          AS tenure_band,
       SUM(CASE WHEN status IN ('ACTIVE', 'ON_LEAVE') THEN 1 ELSE 0 END)    AS current,
       SUM(CASE WHEN status IN ('RESIGNED', 'TERMINATED') THEN 1 ELSE 0 END) AS exited,
       ROUND(100.0 * SUM(CASE WHEN status IN ('RESIGNED', 'TERMINATED') THEN 1 ELSE 0 END)
             / COUNT(*), 1)                                                 AS attrition_pct
FROM t
GROUP BY tenure_band
ORDER BY tenure_band""",
        "sqlite": """
WITH t AS (
    SELECT status, (julianday('now') - julianday(joining_date)) / 365.25 AS years
    FROM employees
    WHERE company_id = :company_id
)
SELECT CASE WHEN years < 1 THEN '1. Under 1 year'
            WHEN years < 3 THEN '2. 1 to 3 years'
            WHEN years < 5 THEN '3. 3 to 5 years'
            ELSE '4. 5+ years' END                                          AS tenure_band,
       SUM(CASE WHEN status IN ('ACTIVE', 'ON_LEAVE') THEN 1 ELSE 0 END)    AS current,
       SUM(CASE WHEN status IN ('RESIGNED', 'TERMINATED') THEN 1 ELSE 0 END) AS exited,
       ROUND(100.0 * SUM(CASE WHEN status IN ('RESIGNED', 'TERMINATED') THEN 1 ELSE 0 END)
             / COUNT(*), 1)                                                 AS attrition_pct
FROM t
GROUP BY tenure_band
ORDER BY tenure_band""",
    },
    {
        "id": "hires_by_month",
        "title": "New hires by month",
        "category": "Workforce",
        "description": "Joiners per month over the last 24 months.",
        "chart": {"type": "line", "x": "month", "y": ["hires"]},
        "sql": """
SELECT TO_CHAR(joining_date, 'YYYY-MM')  AS month,
       COUNT(*)                          AS hires
FROM employees
WHERE company_id = :company_id
  AND joining_date >= CURRENT_DATE - INTERVAL '24 months'
GROUP BY TO_CHAR(joining_date, 'YYYY-MM')
ORDER BY month""",
        "sqlite": """
SELECT strftime('%Y-%m', joining_date)  AS month,
       COUNT(*)                         AS hires
FROM employees
WHERE company_id = :company_id
  AND joining_date >= date('now', '-24 months')
GROUP BY strftime('%Y-%m', joining_date)
ORDER BY month""",
    },
    {
        "id": "data_quality",
        "title": "Data quality check",
        "category": "Implementation",
        "description": "Records that would cause problems in payroll or reporting: missing salary "
                       "structure, missing designation, future joining dates, duplicate emails.",
        "chart": None,
        "sql": """
SELECT 'No salary structure assigned' AS issue, e.employee_code,
       e.first_name || ' ' || e.last_name AS employee
FROM employees e
WHERE e.company_id = :company_id AND e.is_active = TRUE
  AND NOT EXISTS (SELECT 1 FROM employee_salary_assignments a
                  WHERE a.employee_id = e.id AND a.end_date IS NULL)
UNION ALL
SELECT 'No designation', e.employee_code, e.first_name || ' ' || e.last_name
FROM employees e
WHERE e.company_id = :company_id AND e.is_active = TRUE AND e.designation_id IS NULL
UNION ALL
SELECT 'Joining date in the future', e.employee_code, e.first_name || ' ' || e.last_name
FROM employees e
WHERE e.company_id = :company_id AND e.joining_date > CURRENT_DATE
UNION ALL
SELECT 'Duplicate email: ' || e.email, e.employee_code, e.first_name || ' ' || e.last_name
FROM employees e
WHERE e.company_id = :company_id
  AND e.email IN (SELECT email FROM employees WHERE company_id = :company_id
                  GROUP BY email HAVING COUNT(*) > 1)
ORDER BY issue, employee_code""",
    },
    {
        "id": "test_execution_status",
        "title": "Test execution status by plan",
        "category": "QA",
        "description": "Latest result of every test case, rolled up per test plan, with pass rate.",
        "chart": {"type": "bar", "x": "test_plan", "y": ["passed", "failed", "blocked", "not_run"]},
        "sql": """
WITH latest AS (
    SELECT te.test_case_id, te.status,
           ROW_NUMBER() OVER (PARTITION BY te.test_case_id
                              ORDER BY te.executed_at DESC, te.id DESC) AS rn
    FROM test_executions te
)
SELECT tp.name                                                    AS test_plan,
       COUNT(tc.id)                                               AS cases,
       SUM(CASE WHEN l.status = 'PASSED'  THEN 1 ELSE 0 END)      AS passed,
       SUM(CASE WHEN l.status = 'FAILED'  THEN 1 ELSE 0 END)      AS failed,
       SUM(CASE WHEN l.status = 'BLOCKED' THEN 1 ELSE 0 END)      AS blocked,
       SUM(CASE WHEN l.status IS NULL     THEN 1 ELSE 0 END)      AS not_run,
       ROUND(100.0 * SUM(CASE WHEN l.status = 'PASSED' THEN 1 ELSE 0 END)
             / NULLIF(SUM(CASE WHEN l.status IS NOT NULL THEN 1 ELSE 0 END), 0), 1) AS pass_rate
FROM test_plans tp
JOIN test_cases tc   ON tc.plan_id = tp.id
LEFT JOIN latest l   ON l.test_case_id = tc.id AND l.rn = 1
WHERE tp.company_id = :company_id
GROUP BY tp.name
ORDER BY tp.name""",
    },
    {
        "id": "defects_by_module",
        "title": "Open defects by module and severity",
        "category": "QA",
        "description": "Where the open bugs are, weighted by severity.",
        "chart": {"type": "bar", "x": "module", "y": ["critical", "high", "medium", "low"]},
        "sql": """
SELECT COALESCE(module, 'Unassigned')                          AS module,
       SUM(CASE WHEN severity = 'CRITICAL' THEN 1 ELSE 0 END)  AS critical,
       SUM(CASE WHEN severity = 'HIGH'     THEN 1 ELSE 0 END)  AS high,
       SUM(CASE WHEN severity = 'MEDIUM'   THEN 1 ELSE 0 END)  AS medium,
       SUM(CASE WHEN severity = 'LOW'      THEN 1 ELSE 0 END)  AS low,
       COUNT(*)                                                AS total_open
FROM defects
WHERE company_id = :company_id
  AND status IN ('OPEN', 'IN_PROGRESS', 'REOPENED')
GROUP BY COALESCE(module, 'Unassigned')
ORDER BY critical DESC, high DESC, total_open DESC""",
    },
]

BY_ID = {r["id"]: r for r in REPORTS}


def _meta(r: dict) -> dict:
    return {k: r[k] for k in ("id", "title", "category", "description", "chart")}


@router.get("")
def list_reports(user: User = Depends(get_current_user)):
    return [_meta(r) for r in REPORTS]


@router.get("/{report_id}")
def run_report(report_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cid = company_id_of(user)
    report = BY_ID.get(report_id)
    if not report:
        raise HTTPException(404, "Report not found")
    dialect = db.bind.dialect.name
    sql = report.get(dialect, report["sql"]).strip()
    started = time.perf_counter()
    try:
        result = db.execute(text(sql), {"company_id": cid})
        columns = list(result.keys())
        rows = [[jsonable(v) for v in r] for r in result.fetchall()]
    except Exception as exc:  # surface SQL errors clearly instead of a bare 500
        db.rollback()
        raise HTTPException(500, f"Report query failed: {exc.__class__.__name__}")
    return {
        **_meta(report),
        "sql": report["sql"].strip(),
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "execution_ms": round((time.perf_counter() - started) * 1000, 1),
    }
