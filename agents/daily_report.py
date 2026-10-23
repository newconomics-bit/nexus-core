import uuid
from datetime import datetime, timezone, date
from typing import Optional

from database import (
    count_alerts_for_date,
    count_memories_created_on,
    get_invoices_with_exception_on_date,
    get_last_report_date,
    get_pipeline_counts,
    get_revenue_for_date,
    save_daily_report,
)
from agents.text_quality_gate import score_text
from core.telegram_bot import send_message
from models import DailyReport


REPORT_TIME = "06:00"


async def generate_daily_report(report_date: Optional[date] = None) -> DailyReport:
    if report_date is None:
        report_date = date.today()

    date_str = report_date.isoformat()

    revenue_today = await get_revenue_for_date(date_str)
    pipeline = await get_pipeline_counts()

    exceptions = await get_invoices_with_exception_on_date(date_str)

    new_memories = await count_memories_created_on(date_str)
    alerts_sent_today = await count_alerts_for_date(date_str)

    report = DailyReport(
        report_id=str(uuid.uuid4()),
        report_date=date_str,
        revenue_today=revenue_today,
        pipeline=pipeline,
        exceptions=exceptions,
        new_memories=new_memories,
        alerts_sent_today=alerts_sent_today,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )

    await save_daily_report(report)
    return report


def format_report_text(report: DailyReport) -> str:
    """Format daily report as a clean, no-slop Telegram message."""
    revenue_str = f"Rp {report.revenue_today:,}".replace(",", ".")

    pipeline_lines = []
    for state, count in sorted(report.pipeline.items()):
        if count > 0:
            pipeline_lines.append(f"  {state}: {count}")

    pipeline_str = "\n".join(pipeline_lines) if pipeline_lines else "  (kosong)"

    exceptions_str = ""
    if report.exceptions:
        exc_lines = "\n".join(f"  - {e}" for e in report.exceptions)
        exceptions_str = f"\nPerlu perhatian:\n{exc_lines}"
    else:
        exceptions_str = "\nPerlu perhatian: Tidak ada"

    text = (
        f"Selamat pagi Bro Mufti. Laporan RakitDigital {report.report_date}.\n\n"
        f"Cuan masuk: {revenue_str}\n\n"
        f"Pipeline:\n{pipeline_str}{exceptions_str}\n\n"
        f"Memory baru: {report.new_memories} pelajaran\n"
        f"Alert terkirim: {report.alerts_sent_today}\n\n"
        f"— Budi"
    )

    # Validate with text quality gate
    score_result = score_text(text)
    if score_result["passed"]:
        return text

    # Fallback template if slop detected
    fallback = (
        f"Selamat pagi. Laporan {report.report_date}.\n"
        f"Revenue: {revenue_str}\n"
        f"Pipeline: {dict(report.pipeline)}\n"
        f"Exceptions: {len(report.exceptions)}\n"
        f"Memory: {report.new_memories}\n"
        f"Alerts: {report.alerts_sent_today}\n"
        f"— Budi"
    )
    return fallback


async def send_daily_report(report_date: Optional[date] = None) -> dict:
    if report_date is None:
        report_date = date.today()

    last_report = await get_last_report_date()
    if last_report == report_date.isoformat():
        return {"status": "skipped", "reason": "already_sent", "date": report_date.isoformat()}

    report = await generate_daily_report(report_date)
    text = format_report_text(report)

    result = await send_message(text)

    return {
        "status": "sent",
        "report_id": report.report_id,
        "date": report_date.isoformat(),
        "telegram_result": result,
    }