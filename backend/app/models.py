from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

class DefectRecord(Base):
    __tablename__ = "defect_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    coach_id: Mapped[str] = mapped_column(String(24), index=True)
    service: Mapped[str] = mapped_column(String(64), default="Rajdhani Express")
    category: Mapped[str] = mapped_column(String(64), index=True)
    location: Mapped[str] = mapped_column(String(100), default="General")
    description: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(16), default="Medium")
    source: Mapped[str] = mapped_column(String(32), default="Inspection")
    reported_at: Mapped[object] = mapped_column(DateTime, index=True)
    status: Mapped[str] = mapped_column(String(24), default="Open")
    work_order_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    repairs: Mapped[list["RepairRecord"]] = relationship(back_populates="defect", cascade="all, delete-orphan")
    tasks: Mapped[list["MaintenanceTask"]] = relationship(back_populates="defect", cascade="all, delete-orphan")

class RepairRecord(Base):
    __tablename__ = "repair_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    defect_id: Mapped[int] = mapped_column(ForeignKey("defect_records.id"), index=True)
    work_order_id: Mapped[str] = mapped_column(String(32), index=True)
    repaired_at: Mapped[object] = mapped_column(DateTime, index=True)
    repair_summary: Mapped[str] = mapped_column(Text)
    technician: Mapped[str] = mapped_column(String(80))
    verification_status: Mapped[str] = mapped_column(String(24), default="Awaiting verification")
    verified_at: Mapped[object | None] = mapped_column(DateTime, nullable=True)
    verification_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    defect: Mapped[DefectRecord] = relationship(back_populates="repairs")

class MaintenanceTask(Base):
    __tablename__ = "maintenance_tasks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    defect_id: Mapped[int] = mapped_column(ForeignKey("defect_records.id"), index=True)
    task_code: Mapped[str] = mapped_column(String(32), unique=True)
    priority: Mapped[str] = mapped_column(String(16), index=True)
    status: Mapped[str] = mapped_column(String(24), default="Queued")
    assigned_team: Mapped[str] = mapped_column(String(80), default="Unassigned")
    resource_status: Mapped[str] = mapped_column(String(32), default="Available")
    due_date: Mapped[object] = mapped_column(DateTime)
    recommended_action: Mapped[str] = mapped_column(Text)
    recurrence_count: Mapped[int] = mapped_column(Integer, default=0)
    defect: Mapped[DefectRecord] = relationship(back_populates="tasks")

class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    detail: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(20), default="warning")
    created_at: Mapped[object] = mapped_column(DateTime)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
