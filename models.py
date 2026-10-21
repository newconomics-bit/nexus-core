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

