import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from database import (
    get_project,
    get_quote,
    save_contract,
    get_expired_contracts,
    get_contracts_nearing_expiry,
    get_contract,
    insert_audit_log,
)
from models import Contract, ContractType, ContractStatus, ProjectSpec, Quote, AuditAction, AuditResult


TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"


def _load_template(template_name: str) -> str:
    template_path = TEMPLATES_DIR / f"{template_name}.md"
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")
    return template_path.read_text(encoding="utf-8")


def _render_template(template: str, context: dict) -> str:
    result = template
    for key, value in context.items():
        placeholder = f"{{{{{key}}}}}"
        result = result.replace(placeholder, str(value))
    return result


def _build_context(project: dict, quote: Quote | None, spec: ProjectSpec | None) -> dict:
    from datetime import date, timedelta

    today = date.today()
    expires = today + timedelta(days=7)
    timeline = 30  # default 30 hari kerja

    context = {
        "PROJECT_ID": "",  # will be filled by caller
        "QUOTE_ID": quote.quote_id if quote else "",
        "CLIENT_NAME": project.get("client_name", ""),
        "FEATURES": ", ".join(spec.features) if spec and spec.features else "",
        "FINAL_PRICE": f"{quote.final_price:,}".replace(",", ".") if quote else "0",
        "TIMELINE": str(timeline),
        "EFFECTIVE_DATE": date.today().isoformat(),
        "SIGNATURE_DATE_PROVIDER": date.today().isoformat(),
        "PROVIDER_NAME": "RakitDigital",
        "PROVIDER_TITLE": "CTO",
    }
    return context


async def generate_contract(
    project_id: str,
    contract_type: ContractType,
    client_email: Optional[str] = None,
) -> Contract:
    project = await get_project(project_id)
    if not project:
        raise ValueError(f"Project not found: {project_id}")

    if not project.get("spec_json"):
        raise ValueError("Project spec not found")

    from models import ProjectSpec
    spec = ProjectSpec.model_validate_json(project["spec_json"])

    quote = await get_quote(project_id)
    latest_quote = quote  # simplified: use latest

    template_map = {
        ContractType.MSA: "msa",
        ContractType.NDA: "nda",
        ContractType.TOS: "tos",
        ContractType.PRIVACY: "privacy",
    }

    template_name = template_map.get(contract_type)
    if not template_name:
        raise ValueError(f"Unknown contract type: {contract_type}")

    template = _load_template(template_name)
    context = _build_context(project, latest_quote, None)
    context["PROJECT_ID"] = project_id

    content = _render_template(template, context)

    contract_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()

    contract = Contract(
        contract_id=contract_id,
        project_id=project_id,
        contract_type=contract_type,
        template_name=f"{template_name}.md",
        content=content,
        status=ContractStatus.DRAFT,
        created_at=now.isoformat(),
        expires_at=(datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        client_email=client_email,
    )

    await save_contract(contract)
    return contract


async def send_contract(contract_id: str, client_email: str) -> Contract:
    contract = await get_contract(contract_id)
    if not contract:
        raise ValueError("Contract not found")

    if contract.status != ContractStatus.DRAFT:
        raise ValueError("Contract already sent")

    # Mock send email
    print(f"MOCK EMAIL SENT to {client_email}")
    print(f"Contract: {contract.contract_id} ({contract.contract_type.value})")
    print(f"Content preview: {contract.content[:200]}...")

    contract.status = ContractStatus.SENT
    contract.sent_at = datetime.now(timezone.utc).isoformat()
    contract.client_email = client_email
    contract.expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    await save_contract(contract)

    return contract


async def mark_contract_signed(contract_id: str, client_name: str = "", client_title: str = "") -> Contract:
    contract = await get_contract(contract_id)
    if not contract:
        raise ValueError("Contract not found")

    if contract.status == ContractStatus.SIGNED:
        return contract

    # Update contract content with signature details
    updated_content = contract.content
    if "{{CLIENT_SIGNATORY_NAME}}" in updated_content:
        updated_content = updated_content.replace("{{CLIENT_SIGNATORY_NAME}}", client_name)
    if "{{CLIENT_SIGNATORY_TITLE}}" in updated_content:
        updated_content = updated_content.replace("{{CLIENT_SIGNATORY_TITLE}}", client_title)
    if "{{SIGNATURE_DATE_CLIENT}}" in updated_content:
        updated_content = updated_content.replace("{{SIGNATURE_DATE_CLIENT}}", datetime.now(timezone.utc).date().isoformat())

    contract.content = updated_content
    contract.status = ContractStatus.SIGNED
    contract.signed_at = datetime.now(timezone.utc).isoformat()
    await save_contract(contract)

    # Audit log for contract signing
    await insert_audit_log(
        actor="system",
        action=AuditAction.CONTRACT_SIGNED.value,
        target_id=contract_id,
        result=AuditResult.SUCCESS.value,
        context={"contract_type": contract.contract_type.value, "client_name": client_name, "project_id": contract.project_id},
    )

    return contract


async def expire_contract(contract_id: str) -> Contract:
    contract = await get_contract(contract_id)
    if not contract:
        raise ValueError("Contract not found")

    if contract.status == ContractStatus.EXPIRED:
        return contract

    contract.status = ContractStatus.EXPIRED
    await save_contract(contract)
    return contract