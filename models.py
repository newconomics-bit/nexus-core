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

