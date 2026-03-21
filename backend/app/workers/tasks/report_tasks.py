"""Scheduled report delivery tasks."""

import html
import logging
from datetime import date, datetime

from app.utils.datetime_utils import utc_now

from sqlalchemy import select

from app.models.report_template import ReportTemplate
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="send_scheduled_reports",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
)
def send_scheduled_reports_task():
    """
    Send scheduled report emails.
    Runs daily at 8am UTC.
    """
    import asyncio

    asyncio.run(_send_scheduled_reports_async())


async def _send_scheduled_reports_async():
    """Async implementation of scheduled report delivery."""
    from app.services.email_service import email_service
    from app.services.report_service import ReportService
    from app.workers.utils import get_celery_session

    today = utc_now().date()

    async with get_celery_session() as db:
        try:
            # Load all templates that have scheduled delivery enabled
            result = await db.execute(
                select(ReportTemplate).where(
                    ReportTemplate.scheduled_delivery.isnot(None)
                )
            )
            templates = list(result.scalars().all())

            logger.info(
                "Checking %d report templates for scheduled delivery", len(templates)
            )

            sent_count = 0
            for template in templates:
                delivery = template.scheduled_delivery
                if not delivery or not delivery.get("enabled"):
                    continue

                delivery_emails = delivery.get("delivery_emails") or []
                if not delivery_emails:
                    logger.warning(
                        "Template %s has scheduled delivery enabled but no emails configured",
                        template.id,
                    )
                    continue

                frequency = delivery.get("frequency", "daily")

                # Check if delivery is due today
                if not _is_due_today(delivery, today):
                    continue

                # Check last_delivered_at to avoid double-sending within the same day
                last_delivered_raw = delivery.get("last_delivered_at")
                if last_delivered_raw:
                    try:
                        last_delivered = datetime.fromisoformat(last_delivered_raw).date()
                        if last_delivered >= today:
                            logger.info(
                                "Template %s already delivered today, skipping",
                                template.id,
                            )
                            continue
                    except ValueError:
                        pass  # Malformed date — proceed with delivery

                # Execute the report
                try:
                    report_result = await ReportService.execute_report(
                        db=db,
                        organization_id=template.organization_id,
                        config=template.config,
                    )
                except Exception as exc:
                    logger.error(
                        "Failed to execute report for template %s: %s",
                        template.id,
                        exc,
                        exc_info=True,
                    )
                    continue

                # Build email content from report result
                subject, html_body, text_body = _build_report_email(
                    template, report_result, today, frequency
                )

                # Send to each configured recipient
                any_sent = False
                for email_addr in delivery_emails:
                    ok = await email_service.send_email(
                        to_email=email_addr,
                        subject=subject,
                        html_body=html_body,
                        text_body=text_body,
                    )
                    if ok:
                        any_sent = True
                        logger.info(
                            "Sent scheduled report '%s' to %s",
                            template.name,
                            email_addr,
                        )

                # Update last_delivered_at on success
                if any_sent:
                    updated_delivery = dict(delivery)
                    updated_delivery["last_delivered_at"] = today.isoformat()
                    template.scheduled_delivery = updated_delivery
                    await db.commit()
                    sent_count += 1
                elif delivery_emails:
                    logger.warning(
                        "Scheduled report %s: all %d email sends failed",
                        template.id,
                        len(delivery_emails),
                    )

            logger.info("Scheduled report delivery complete. Reports sent: %d", sent_count)

        except Exception as exc:
            logger.error(
                "Error in scheduled report delivery: %s", exc, exc_info=True
            )
            raise


def _is_due_today(delivery: dict, today: date) -> bool:
    """Return True if a scheduled delivery should run on *today*."""
    frequency = delivery.get("frequency", "daily")

    if frequency == "daily":
        return True

    if frequency == "weekly":
        # day_of_week: 0=Monday … 6=Sunday (matches Python's weekday())
        target_dow = delivery.get("day_of_week", 0)
        return today.weekday() == target_dow

    if frequency == "monthly":
        target_dom = delivery.get("day_of_month", 1)
        return today.day == target_dom

    # Unknown frequency — skip
    logger.warning("Unknown scheduled_delivery frequency: %s", frequency)
    return False


def _build_report_email(
    template: "ReportTemplate",
    report_result: dict,
    today: date,
    frequency: str,
) -> tuple[str, str, str]:
    """Build subject, HTML body, and plain-text body for a scheduled report email."""
    safe_name = html.escape(template.name)
    date_str = today.strftime("%B %d, %Y")
    frequency_label = {"daily": "Daily", "weekly": "Weekly", "monthly": "Monthly"}.get(
        frequency, frequency.capitalize()
    )

    subject = f"Nest Egg {frequency_label} Report: {template.name} — {date_str}"

    data = report_result.get("data", [])
    metrics = report_result.get("metrics", {})
    date_range = report_result.get("dateRange", {})
    period_str = ""
    if date_range.get("startDate") and date_range.get("endDate"):
        period_str = f"{date_range['startDate']} to {date_range['endDate']}"

    # Build a simple HTML table from the report data
    rows_html = ""
    rows_text = ""
    if data:
        headers = list(data[0].keys())
        header_cells = "".join(
            f'<th style="padding:6px 12px;text-align:left;border-bottom:1px solid #E2E8F0;">'
            f'{html.escape(str(h))}</th>'
            for h in headers
        )
        rows_html += f"<thead><tr>{header_cells}</tr></thead><tbody>"
        rows_text += "\t".join(str(h) for h in headers) + "\n"

        for row in data[:50]:  # Cap at 50 rows in email
            cells = "".join(
                f'<td style="padding:6px 12px;border-bottom:1px solid #F7FAFC;">'
                f'{html.escape(str(row.get(h, "")))}</td>'
                for h in headers
            )
            rows_html += f"<tr>{cells}</tr>"
            rows_text += "\t".join(str(row.get(h, "")) for h in headers) + "\n"

        rows_html += "</tbody>"

    metrics_html = ""
    metrics_text = ""
    if metrics:
        for k, v in metrics.items():
            label = k.replace("_", " ").title()
            val = f"${v:,.2f}" if isinstance(v, (int, float)) else str(v)
            metrics_html += (
                f'<p style="margin:4px 0;"><strong>{html.escape(label)}:</strong> '
                f'{html.escape(val)}</p>'
            )
            metrics_text += f"{label}: {val}\n"

    html_body = f"""<!DOCTYPE html>
<html>
<body style="font-family:Arial,sans-serif;max-width:700px;margin:0 auto;padding:20px;">
  <h2 style="color:#2D3748;">{safe_name}</h2>
  <p style="color:#718096;">{frequency_label} report &mdash; {html.escape(date_str)}</p>
  {f'<p style="color:#718096;font-size:13px;">Period: {html.escape(period_str)}</p>' if period_str else ''}
  {f'<div style="margin:16px 0;">{metrics_html}</div>' if metrics_html else ''}
  <table style="width:100%;border-collapse:collapse;font-size:14px;">
    {rows_html}
  </table>
  {f'<p style="color:#A0AEC0;font-size:12px;">Showing up to 50 rows.</p>' if len(data) > 50 else ''}
  <hr style="border:none;border-top:1px solid #E2E8F0;margin:24px 0;"/>
  <p style="color:#A0AEC0;font-size:12px;">
    You are receiving this because scheduled delivery is enabled for this report template in Nest Egg.
  </p>
</body>
</html>"""

    text_body = (
        f"{template.name}\n"
        f"{frequency_label} report — {date_str}\n"
        + (f"Period: {period_str}\n" if period_str else "")
        + "\n"
        + metrics_text
        + "\n"
        + rows_text
        + "\n---\n"
        "You are receiving this because scheduled delivery is enabled for this report template in Nest Egg.\n"
    )

    return subject, html_body, text_body
