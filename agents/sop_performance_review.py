from database import get_agent_performance_last_30_days, save_corporate_memory
from core.telegram_bot import send_message
from models import CorporateMemory, MemoryCategory, MemorySeverity


async def generate_performance_report() -> dict:
    performances = await get_agent_performance_last_30_days()

    if not performances:
        return {"agents": [], "summary": "No performance data available"}

    agents_report = []
    underperform_count = 0

    for perf in performances:
        avg_success = perf.success_rate
        avg_error = perf.error_rate
        total_tokens = perf.token_usage
        completed = perf.tasks_completed
        failed = perf.tasks_failed

        underperform = avg_success < 0.8 or avg_error > 0.2
        if underperform:
            underperform_count += 1

        agents_report.append({
            "name": perf.agent_name,
            "metrics": {
                "avg_success_rate": round(avg_success, 2),
                "avg_error_rate": round(avg_error, 2),
                "total_tokens_used": total_tokens,
                "tasks_completed": completed,
                "tasks_failed": failed,
            },
            "underperform": underperform,
        })

    return {
        "agents": agents_report,
        "summary": f"{underperform_count} agen underperform",
    }


async def schedule_monthly_review() -> dict:
    report = await generate_performance_report()

    # Send to Telegram (Founder + Pak Arif)
    message_lines = [
        "📊 *Monthly AI Agent Performance Review*",
        f"Summary: {report['summary']}",
        "",
    ]

    for agent in report["agents"]:
        m = agent["metrics"]
        flag = " ⚠️" if agent["underperform"] else " ✅"
        message_lines.append(
            f"{flag} {agent['name']}: Success={m['avg_success_rate']:.0%}, "
            f"Error={m['avg_error_rate']:.0%}, Tokens={m['total_tokens_used']}, "
            f"Completed={m['tasks_completed']}, Failed={m['tasks_failed']}"
        )

    message = "\n".join(message_lines)
    await send_message(message)

    # Log to corporate memory
    from database import save_corporate_memory
    from models import CorporateMemory, MemoryCategory, MemorySeverity
    import uuid
    from datetime import datetime, timezone

    memory = CorporateMemory(
        memory_id=str(uuid.uuid4()),
        project_id="",
        category=MemoryCategory.FINANCE_MARGIN_LEAK,
        lesson_text=f"Monthly performance review: {report['summary']}. {len(report['agents'])} agen reviewed.",
        severity=MemorySeverity.LOW,
        target_agent="MANAGER",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    from database import save_corporate_memory
    await save_corporate_memory(memory)

    return report