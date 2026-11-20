from datetime import datetime, timezone
from sqlalchemy import String, Float, Integer, DateTime, Boolean, ForeignKey, Text, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON
from app.database.connection import Base

def utcnow(): return datetime.now(timezone.utc).replace(tzinfo=None)

class Zone(Base):
    __tablename__ = 'zones'
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    district: Mapped[str] = mapped_column(String(120), default='Demo District')
    latitude: Mapped[float] = mapped_column(Float, default=22.47)
    longitude: Mapped[float] = mapped_column(Float, default=70.06)
    population_reference: Mapped[int] = mapped_column(Integer, default=0)

class EnvironmentObservation(Base):
    __tablename__ = 'environment_observations'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    zone_id: Mapped[str] = mapped_column(ForeignKey('zones.id'), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    apparent_temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    aqi: Mapped[float | None] = mapped_column(Float, nullable=True)
    pm25: Mapped[float | None] = mapped_column(Float, nullable=True)
    pm10: Mapped[float | None] = mapped_column(Float, nullable=True)
    no2: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(40), default='SYNTHETIC')
    source_detail: Mapped[str] = mapped_column(String(120), default='')
    quality_status: Mapped[str] = mapped_column(String(30), default='valid')

class HealthObservation(Base):
    __tablename__ = 'health_observations'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    zone_id: Mapped[str] = mapped_column(ForeignKey('zones.id'), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    clinic_visits: Mapped[int] = mapped_column(Integer, default=0)
    heat_complaints: Mapped[int] = mapped_column(Integer, default=0)
    respiratory_complaints: Mapped[int] = mapped_column(Integer, default=0)
    fatigue_reports: Mapped[int] = mapped_column(Integer, default=0)
    first_aid_cases: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(40), default='SYNTHETIC')
    source_detail: Mapped[str] = mapped_column(String(120), default='')
    quality_status: Mapped[str] = mapped_column(String(30), default='valid')

class WorkforceObservation(Base):
    __tablename__ = 'workforce_observations'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    zone_id: Mapped[str] = mapped_column(ForeignKey('zones.id'), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    shift: Mapped[str] = mapped_column(String(30), default='Day')
    exposed_workers: Mapped[int] = mapped_column(Integer, default=0)
    heat_complaints: Mapped[int] = mapped_column(Integer, default=0)
    respiratory_complaints: Mapped[int] = mapped_column(Integer, default=0)
    first_aid_cases: Mapped[int] = mapped_column(Integer, default=0)
    absence_count: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(40), default='SYNTHETIC')
    source_detail: Mapped[str] = mapped_column(String(120), default='')
    quality_status: Mapped[str] = mapped_column(String(30), default='valid')

class RiskAssessment(Base):
    __tablename__ = 'risk_assessments'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    zone_id: Mapped[str] = mapped_column(ForeignKey('zones.id'), index=True)
    risk_type: Mapped[str] = mapped_column(String(30), index=True)
    score: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    severity: Mapped[str] = mapped_column(String(30))
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    explanation: Mapped[str] = mapped_column(Text, default='')
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

class Alert(Base):
    __tablename__ = 'alerts'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    zone_id: Mapped[str] = mapped_column(ForeignKey('zones.id'), index=True)
    risk_type: Mapped[str] = mapped_column(String(30))
    severity: Mapped[str] = mapped_column(String(30))
    score: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    title: Mapped[str] = mapped_column(String(200))
    explanation: Mapped[str] = mapped_column(Text)
    recommendation: Mapped[str] = mapped_column(Text)
    responsible_role: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), default='open')
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class IngestionJob(Base):
    __tablename__ = 'ingestion_jobs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_type: Mapped[str] = mapped_column(String(30))
    category: Mapped[str] = mapped_column(String(30))
    filename: Mapped[str] = mapped_column(String(255), default='manual-entry')
    status: Mapped[str] = mapped_column(String(30), default='staged')
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, default=0)
    invalid_rows: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_rows: Mapped[int] = mapped_column(Integer, default=0)
    imported_rows: Mapped[int] = mapped_column(Integer, default=0)
    staged_data: Mapped[list] = mapped_column(JSON, default=list)
    errors: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    committed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[str] = mapped_column(String(80), default='system', index=True)

class InterventionAction(Base):
    __tablename__ = 'intervention_actions'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey('alerts.id'), index=True)
    responsible_role: Mapped[str] = mapped_column(String(100))
    notes: Mapped[str] = mapped_column(Text, default='')
    status: Mapped[str] = mapped_column(String(30), default='assigned')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor: Mapped[str] = mapped_column(String(100), default='demo-user')
    action: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[str] = mapped_column(String(100))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

class SimulationRun(Base):
    __tablename__ = 'simulation_runs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    zone_id: Mapped[str] = mapped_column(ForeignKey('zones.id'))
    scenario: Mapped[str] = mapped_column(String(80))
    inputs: Mapped[dict] = mapped_column(JSON, default=dict)
    results: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

class DataSourceStatus(Base):
    __tablename__ = 'data_source_status'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(50), unique=True)
    status: Mapped[str] = mapped_column(String(30), default='not_configured')
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    message: Mapped[str] = mapped_column(Text, default='')

Index('ix_env_zone_time', EnvironmentObservation.zone_id, EnvironmentObservation.observed_at)
Index('ix_health_zone_time', HealthObservation.zone_id, HealthObservation.observed_at)
Index('ix_workforce_zone_time', WorkforceObservation.zone_id, WorkforceObservation.observed_at)

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
