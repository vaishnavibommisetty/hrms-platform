from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from app.core.database import Base


class UserRole(str, enum.Enum):
    PLATFORM_ADMIN = "platform_admin"
    COMPANY_ADMIN = "company_admin"
    HR_MANAGER = "hr_manager"
    DEPARTMENT_MANAGER = "department_manager"
    FINANCE_MANAGER = "finance_manager"
    EMPLOYEE = "employee"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    # nullable for platform admins who don't belong to a specific company

    email = Column(String(200), unique=True, nullable=False, index=True)
    hashed_password = Column(String(500), nullable=False)
    full_name = Column(String(200), nullable=False)
    role = Column(SAEnum(UserRole), nullable=False, default=UserRole.EMPLOYEE)
    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    company = relationship("Company", back_populates="users")
    employee = relationship("Employee", back_populates="user", uselist=False)

    def __repr__(self):
        return f"<User id={self.id} email={self.email} role={self.role}>"
