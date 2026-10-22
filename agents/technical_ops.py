import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

from database import (
    get_deployment,
    get_project,
    save_approval,
    save_deployment,
    update_project_state,
)
from models import (
    ApprovalRequest,
    ApprovalStatus,
    ApprovalType,
    DeploymentRequest,
    DeploymentStatus,
    DomainChoice,
)


def _sanitize_client_name(name: str) -> str:
    return "".join(c.lower() if c.isalnum() else "-" for c in name).strip("-")


async def request_deployment(
    project_id: str, domain_choice: DomainChoice, custom_domain_url: str | None = None
) -> tuple[str, str]:
    project = await get_project(project_id)
    if project is None:
        raise ValueError("Project not found")
    if project["state"] != "APPROVED":
        raise ValueError("Project must be in APPROVED state")

    deployment_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    hosted_url = None
    if domain_choice == DomainChoice.HOSTED:
        sanitized = _sanitize_client_name(project["client_name"])
        hosted_url = f"https://{sanitized}.rakitdigital.app"
    elif domain_choice == DomainChoice.CUSTOM:
        if not custom_domain_url:
            raise ValueError("Custom domain URL is required for CUSTOM domain choice")
        parsed = urlparse(custom_domain_url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("Invalid custom domain URL format")

    deployment = DeploymentRequest(
        deployment_id=deployment_id,
        project_id=project_id,
        domain_choice=domain_choice,
        custom_domain_url=custom_domain_url,
        hosted_url=hosted_url,
        status=DeploymentStatus.PENDING_APPROVAL,
        created_at=created_at,
    )
    await save_deployment(deployment)

    approval = ApprovalRequest(
        approval_id=str(uuid.uuid4()),
        project_id=project_id,
        quote_id="",
        type=ApprovalType.DEPLOY_PRODUCTION,
        payload={
            "deployment_id": deployment_id,
            "domain_choice": domain_choice.value,
            "custom_domain_url": custom_domain_url,
            "hosted_url": hosted_url,
            "client_name": project["client_name"],
        },
        status=ApprovalStatus.PENDING,
        requested_at=created_at,
    )
    await save_approval(approval)

    return deployment_id, approval.approval_id


async def execute_deployment(approval_id: str) -> dict:
    approval = await get_approval(approval_id)
    if approval is None:
        raise ValueError("Approval not found")
    if approval.type != ApprovalType.DEPLOY_PRODUCTION:
        raise ValueError("Approval is not a DEPLOY_PRODUCTION type")
    if approval.status != ApprovalStatus.APPROVED:
        raise ValueError("Approval is not approved")

    deployment_id = approval.payload.get("deployment_id")
    if not deployment_id:
        raise ValueError("Deployment ID not found in approval payload")

    deployment = await get_deployment(deployment_id)
    if deployment is None:
        raise ValueError("Deployment not found")

    deployment.status = DeploymentStatus.DEPLOYED
    await save_deployment(deployment)

    await update_project_state(deployment.project_id, "DEPLOYED")

    live_url = deployment.hosted_url or deployment.custom_domain_url
    return {
        "deployment_id": deployment_id,
        "status": "DEPLOYED",
        "live_url": live_url,
        "message": f"Successfully deployed to {live_url}",
    }


async def get_approval(approval_id: str):
    from database import get_approval as db_get_approval
    return await db_get_approval(approval_id)