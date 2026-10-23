from enum import Enum

from pydantic import BaseModel


class ProjectState(str, Enum):
    LEAD = "LEAD"
    DISCOVERY = "DISCOVERY"
    QUOTED = "QUOTED"
    SIGNED = "SIGNED"
    BUILDING = "BUILDING"
    AUDITING = "AUDITING"
    APPROVED = "APPROVED"
    DEPLOYED = "DEPLOYED"
    SUBSCRIPTION = "SUBSCRIPTION"
    SUSPENDED = "SUSPENDED"
    CHURNED = "CHURNED"


_LINEAR = (
    ProjectState.LEAD,
    ProjectState.DISCOVERY,
    ProjectState.QUOTED,
    ProjectState.SIGNED,
    ProjectState.BUILDING,
    ProjectState.AUDITING,
    ProjectState.APPROVED,
    ProjectState.DEPLOYED,
    ProjectState.SUBSCRIPTION,
    ProjectState.SUSPENDED,
    ProjectState.CHURNED,
)

ALLOWED_TRANSITIONS: dict[ProjectState, frozenset[ProjectState]] = {
    state: frozenset() for state in ProjectState
}
for _current, _nxt in zip(_LINEAR, _LINEAR[1:]):
    ALLOWED_TRANSITIONS[_current] = frozenset({_nxt})


class StartProjectRequest(BaseModel):
    client_name: str


class AdvanceStateRequest(BaseModel):
    new_state: ProjectState


class ChatRequest(BaseModel):
    message: str


class ProjectSpec(BaseModel):
    client_name: str
    features: list[str]
    budget: str


class Difficulty(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class QuoteStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ACCEPTED = "ACCEPTED"
    EXPIRED = "EXPIRED"


class EffortEstimate(BaseModel):
    labor_hours: float
    difficulty: Difficulty
    notes: str


class HppBreakdown(BaseModel):
    infra_cost: int
    labor_hours: float
    labor_rate: int
    qris_mdr: int
    total_hpp: int


class Quote(BaseModel):
    quote_id: str
    project_id: str
    version: int
    hpp_breakdown: HppBreakdown
    margin_pct: float = 75
    discount_pct: float = 0
    final_price: int
    status: QuoteStatus
    valid_until_days: int = 7
    created_at: str


class DiscountRequest(BaseModel):
    discount_pct: int
    founder_approved: bool


class SignRequest(BaseModel):
    quote_id: str


class ApprovalType(str, Enum):
    DISCOUNT_ESCALATION = "DISCOUNT_ESCALATION"
    DEPLOY = "DEPLOY"
    PAYMENT = "PAYMENT"
    QA_ESCALATION = "QA_ESCALATION"
    DEPLOY_PRODUCTION = "DEPLOY_PRODUCTION"


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    AUTO_REJECTED = "AUTO_REJECTED"


class ApprovalRequest(BaseModel):
    approval_id: str
    project_id: str
    quote_id: str
    type: ApprovalType
    payload: dict
    status: ApprovalStatus
    requested_at: str
    decided_at: str = ""
    decided_by: str = ""
    expires_at: str | None = None


class DecideRequest(BaseModel):
    decision: str
    decided_by: str


class TaskKind(str, Enum):
    FRONTEND = "FRONTEND"
    BACKEND = "BACKEND"
    DATABASE = "DATABASE"


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    DONE = "DONE"
    FAILED = "FAILED"


class BuildTask(BaseModel):
    task_id: str
    project_id: str
    kind: TaskKind
    title: str
    status: TaskStatus = TaskStatus.PENDING
    attempts: int = 0
    artifact_id: str | None = None


class BuildArtifact(BaseModel):
    artifact_id: str
    project_id: str
    task_id: str
    filename: str
    content: str
    created_at: str


class BuildSubmission(BaseModel):
    submission_id: str
    project_id: str
    artifact_ids: list[str]
    task_count: int
    created_at: str
    status: str = "READY_FOR_AUDIT"


class AuditCategory(str, Enum):
    OSINT = "OSINT"
    SAST = "SAST"
    DAST = "DAST"
    DB_AUDIT = "DB_AUDIT"


class FindingSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class AuditFinding(BaseModel):
    finding_id: str
    project_id: str
    submission_id: str
    category: AuditCategory
    severity: FindingSeverity
    location: str
    description: str
    recommendation: str


class AuditReportStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"


class AuditReport(BaseModel):
    report_id: str
    project_id: str
    submission_id: str
    cycle: int
    findings: list[AuditFinding]
    status: AuditReportStatus
    created_at: str


class DomainChoice(str, Enum):
    HOSTED = "HOSTED"
    CUSTOM = "CUSTOM"


class DeploymentStatus(str, Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    DEPLOYED = "DEPLOYED"
    REJECTED = "REJECTED"


class DeploymentRequest(BaseModel):
    deployment_id: str
    project_id: str
    domain_choice: DomainChoice
    custom_domain_url: str | None = None
    hosted_url: str | None = None
    status: DeploymentStatus = DeploymentStatus.PENDING_APPROVAL
    created_at: str


class InvoiceStatus(str, Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"
    PAYMENT_EXCEPTION = "PAYMENT_EXCEPTION"


class SubscriptionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    CHURNED = "CHURNED"


class Invoice(BaseModel):
    invoice_id: str
    project_id: str
    amount: int
    due_date: str
    status: InvoiceStatus = InvoiceStatus.PENDING
    paid_at: str | None = None
    created_at: str | None = None


class Subscription(BaseModel):
    subscription_id: str
    project_id: str
    monthly_fee: int
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    current_invoice_id: str | None = None


class QrisStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAID = "PAID"
    EXPIRED = "EXPIRED"


class QrisRequest(BaseModel):
    qris_id: str
    invoice_id: str
    amount: int
    qr_string: str
    status: QrisStatus = QrisStatus.ACTIVE
    created_at: str
    expires_at: str


class MockLedgerEntry(BaseModel):
    entry_id: str
    reference_code: str
    qris_id: str
    amount: int
    paid_at: str


class MemoryCategory(str, Enum):
    CODING_MISTAKE = "CODING_MISTAKE"
    CS_MISUNDERSTANDING = "CS_MISUNDERSTANDING"
    QA_BYPASS = "QA_BYPASS"
    FINANCE_MARGIN_LEAK = "FINANCE_MARGIN_LEAK"
    CLIENT_CHURN_REASON = "CLIENT_CHURN_REASON"


class MemorySeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class CorporateMemory(BaseModel):
    memory_id: str
    project_id: str
    category: MemoryCategory
    lesson_text: str
    severity: MemorySeverity
    target_agent: str
    created_at: str


class AlertType(str, Enum):
    PAYMENT_EXCEPTION = "PAYMENT_EXCEPTION"
    DISCOUNT_AUTO_REJECTED = "DISCOUNT_AUTO_REJECTED"
    PROJECT_BLOCKED = "PROJECT_BLOCKED"
    TOKEN_CAP_NEAR = "TOKEN_CAP_NEAR"
    MEMORY_CREATED = "MEMORY_CREATED"
    DEPLOY_READY = "DEPLOY_READY"


class AlertSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertSentVia(str, Enum):
    TELEGRAM = "TELEGRAM"
    LOG = "LOG"


class AlertEvent(BaseModel):
    alert_id: str
    project_id: str | None = None
    type: AlertType
    severity: AlertSeverity
    message: str
    sent_via: AlertSentVia = AlertSentVia.LOG
    created_at: str
    acknowledged: bool = False


class DailyReport(BaseModel):
    report_id: str
    report_date: str
    revenue_today: int
    pipeline: dict[str, int]
    exceptions: list[str]
    new_memories: int
    alerts_sent_today: int
    generated_at: str

