from enum import Enum

from pydantic import BaseModel


class ProjectState(str, Enum):
    LEAD = "LEAD"
    DISCOVERY = "DISCOVERY"
    QUOTED = "QUOTED"
    SIGNED = "SIGNED"
    BUILDING = "BUILDING"
    AUDITING = "AUDITING"
    DEPLOYED = "DEPLOYED"
    SUBSCRIPTION = "SUBSCRIPTION"
    CHURNED = "CHURNED"


_LINEAR = (
    ProjectState.LEAD,
    ProjectState.DISCOVERY,
    ProjectState.QUOTED,
    ProjectState.SIGNED,
    ProjectState.BUILDING,
    ProjectState.AUDITING,
    ProjectState.DEPLOYED,
    ProjectState.SUBSCRIPTION,
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


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ApprovalPayload(BaseModel):
    discount_pct: int
    final_price_before: int
    final_price_after: int


class ApprovalRequest(BaseModel):
    approval_id: str
    project_id: str
    quote_id: str
    type: ApprovalType
    payload: ApprovalPayload
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

