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


class Subscription(BaseModel):
    subscription_id: str
    project_id: str
    monthly_fee: int
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    current_invoice_id: str | None = None

