"""
Competitor Intelligence Digest & Reporting Engine.
Compiles periodic cross-catalog insights (price drops, stockouts, sentiment flaws, catalog diffs)
and generates executive HTML email templates and downloadable ReportLab PDF reports.
"""

import io
import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple, Union
from croniter import croniter

from sqlalchemy import select, func, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession

# ReportLab imports for PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether

from app.models.product import Product, PriceHistory, ProductInventoryForecast, ProductSentimentSummary
from app.models.report import ReportSchedule, GeneratedReport
from app.config import settings

logger = logging.getLogger(__name__)


def calculate_next_run(cron_expression: str, base_time: Optional[datetime] = None) -> datetime:
    """Calculate next execution datetime using cron expression."""
    if base_time is None:
        base_time = datetime.now(timezone.utc)
    elif base_time.tzinfo is None:
        base_time = base_time.replace(tzinfo=timezone.utc)

    iter_cron = croniter(cron_expression, base_time)
    next_ts = iter_cron.get_next(datetime)
    if next_ts.tzinfo is None:
        next_ts = next_ts.replace(tzinfo=timezone.utc)
    return next_ts


class ReportService:
    """Service for compiling competitor intelligence and producing PDF/HTML digests."""

    async def compile_intelligence_data(
        self,
        db: AsyncSession,
        domain: Optional[str] = None,
        days: int = 7
    ) -> Dict[str, Any]:
        """Aggregate catalog metrics, price drops, stockout opportunities, and sentiment insights."""
        now = datetime.now(timezone.utc)
        since_date = now - timedelta(days=days)

        # 1. Catalog Products Query
        prod_stmt = select(Product)
        if domain:
            prod_stmt = prod_stmt.where(Product.source_domain.contains(domain.lower()))
        res_prods = await db.execute(prod_stmt)
        products = res_prods.scalars().all()

        total_products = len(products)
        in_stock_count = sum(1 for p in products if p.in_stock)
        out_of_stock_count = total_products - in_stock_count

        prices = [float(p.price) for p in products if p.price and float(p.price) > 0]
        avg_price = round(sum(prices) / len(prices), 2) if prices else 0.0

        # Unique competitor domains
        domains = sorted(list(set(p.source_domain for p in products if p.source_domain)))

        # 2. Top Price Drops
        price_drops = []
        for p in products:
            if p.previous_price and p.price and float(p.price) < float(p.previous_price):
                prev = float(p.previous_price)
                curr = float(p.price)
                pct = round(((prev - curr) / prev) * 100, 1)
                price_drops.append({
                    "id": p.id,
                    "name": p.name,
                    "domain": p.source_domain or "Unknown",
                    "previous_price": prev,
                    "current_price": curr,
                    "drop_amount": round(prev - curr, 2),
                    "drop_percentage": pct,
                    "url": p.url,
                })
        price_drops.sort(key=lambda x: x["drop_percentage"], reverse=True)
        top_price_drops = price_drops[:10]

        # 3. Competitor Stockout & Depletion Opportunities
        opp_stmt = (
            select(ProductInventoryForecast, Product)
            .join(Product, ProductInventoryForecast.product_id == Product.id)
            .where(ProductInventoryForecast.stockout_risk_level.in_(["high", "medium", "out_of_stock"]))
        )
        if domain:
            opp_stmt = opp_stmt.where(Product.source_domain.contains(domain.lower()))
        opp_stmt = opp_stmt.order_by(
            desc(ProductInventoryForecast.estimated_daily_revenue),
            ProductInventoryForecast.days_until_stockout.asc()
        ).limit(10)

        res_opp = await db.execute(opp_stmt)
        stockout_opps = []
        for fc, prod in res_opp.all():
            stockout_opps.append({
                "product_id": prod.id,
                "name": prod.name,
                "domain": prod.source_domain,
                "current_stock": fc.current_stock,
                "sales_velocity_per_day": fc.sales_velocity_per_day,
                "days_until_stockout": fc.days_until_stockout,
                "estimated_daily_revenue": fc.estimated_daily_revenue,
                "risk_level": fc.stockout_risk_level,
                "verdict": fc.opportunity_verdict,
            })

        # 4. Competitor Vulnerabilities & Sentiment Flaws
        sent_stmt = (
            select(ProductSentimentSummary, Product)
            .join(Product, ProductSentimentSummary.product_id == Product.id)
            .where(func.json_array_length(ProductSentimentSummary.key_weaknesses) > 0)
        )
        if domain:
            sent_stmt = sent_stmt.where(Product.source_domain.contains(domain.lower()))
        sent_stmt = sent_stmt.order_by(ProductSentimentSummary.negative_percentage.desc()).limit(8)

        res_sent = await db.execute(sent_stmt)
        vulnerabilities = []
        for s_sum, prod in res_sent.all():
            vulnerabilities.append({
                "product_name": prod.name,
                "domain": prod.source_domain,
                "negative_percentage": s_sum.negative_percentage,
                "weaknesses": s_sum.key_weaknesses or [],
                "buyer_pain_points": s_sum.buyer_pain_points or [],
            })

        return {
            "generated_at": now.strftime("%Y-%m-%d %H:%M UTC"),
            "domain_scope": domain or "All Monitored Competitors",
            "period_days": days,
            "total_products": total_products,
            "in_stock_count": in_stock_count,
            "out_of_stock_count": out_of_stock_count,
            "avg_price": avg_price,
            "competitor_domains_count": len(domains),
            "domains_list": domains,
            "top_price_drops": top_price_drops,
            "total_price_drops_count": len(price_drops),
            "stockout_opportunities": stockout_opps,
            "vulnerabilities": vulnerabilities,
        }

    def generate_html_report(self, data: Dict[str, Any]) -> str:
        """Render responsive, inline-styled executive HTML email digest."""
        drops_rows = ""
        for d in data.get("top_price_drops", []):
            drops_rows += f"""
            <tr style="border-bottom: 1px solid #e5e7eb;">
                <td style="padding: 10px 12px; font-weight: 500; color: #111827; max-width: 250px;">{d['name'][:60]}...</td>
                <td style="padding: 10px 12px; color: #4b5563; text-transform: capitalize;">{d['domain']}</td>
                <td style="padding: 10px 12px; color: #9ca3af; text-decoration: line-through;">${d['previous_price']}</td>
                <td style="padding: 10px 12px; font-weight: 700; color: #111827;">${d['current_price']}</td>
                <td style="padding: 10px 12px; font-weight: 700; color: #dc2626;">-{d['drop_percentage']}%</td>
            </tr>
            """

        if not drops_rows:
            drops_rows = '<tr><td colspan="5" style="padding: 16px; text-align: center; color: #9ca3af;">No recent competitor price drops recorded.</td></tr>'

        stockout_rows = ""
        for s in data.get("stockout_opportunities", []):
            risk_color = "#dc2626" if s['risk_level'] == 'high' else "#d97706" if s['risk_level'] == 'medium' else "#991b1b"
            stockout_rows += f"""
            <tr style="border-bottom: 1px solid #e5e7eb;">
                <td style="padding: 10px 12px; font-weight: 500; color: #111827; max-width: 240px;">{s['name'][:60]}...</td>
                <td style="padding: 10px 12px; color: #4b5563; text-transform: capitalize;">{s['domain']}</td>
                <td style="padding: 10px 12px; font-weight: 600;">{s['current_stock'] if s['current_stock'] is not None else '0'} units</td>
                <td style="padding: 10px 12px; color: #2563eb; font-weight: 600;">{s['sales_velocity_per_day']}/day</td>
                <td style="padding: 10px 12px; font-weight: 700; color: {risk_color};">
                    {s['days_until_stockout']} days ({s['risk_level'].upper().replace('_', ' ')})
                </td>
            </tr>
            """

        if not stockout_rows:
            stockout_rows = '<tr><td colspan="5" style="padding: 16px; text-align: center; color: #9ca3af;">No imminent competitor stockouts detected.</td></tr>'

        vuln_cards = ""
        for v in data.get("vulnerabilities", []):
            flaws = "".join([f"<li style='margin-bottom: 3px;'>{f}</li>" for f in v['weaknesses'][:3]])
            vuln_cards += f"""
            <div style="background-color: #fef2f2; border: 1px solid #fee2e2; border-radius: 8px; padding: 12px; margin-bottom: 10px;">
                <div style="font-weight: 600; color: #991b1b; font-size: 13px; margin-bottom: 4px;">{v['product_name'][:65]}... ({v['domain']})</div>
                <div style="font-size: 11px; color: #dc2626; font-weight: 600; margin-bottom: 6px;">Negative Sentiment: {v['negative_percentage']}%</div>
                <ul style="font-size: 12px; color: #7f1d1d; margin: 0; padding-left: 18px;">
                    {flaws}
                </ul>
            </div>
            """

        if not vuln_cards:
            vuln_cards = '<div style="color: #9ca3af; font-size: 12px;">No major competitor product flaws flagged this period.</div>'

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Competitor Intelligence Digest</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f3f4f6; margin: 0; padding: 24px; color: #1f2937;">
    <div style="max-width: 680px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
        
        <!-- Header -->
        <div style="background-color: #4f46e5; padding: 28px 32px; color: #ffffff;">
            <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #c7d2fe; margin-bottom: 4px;">Executive Market Briefing</div>
            <h1 style="margin: 0; font-size: 24px; font-weight: 800; letter-spacing: -0.5px;">Competitor Intelligence Digest</h1>
            <div style="font-size: 12px; color: #e0e7ff; margin-top: 8px;">Scope: <strong>{data['domain_scope']}</strong> • Generated: <strong>{data['generated_at']}</strong></div>
        </div>

        <div style="padding: 28px 32px;">
            <!-- KPI Blocks -->
            <div style="display: flex; gap: 12px; margin-bottom: 28px;">
                <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 20px;">
                    <tr>
                        <td width="25%" style="background-color: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; text-align: center;">
                            <div style="font-size: 10px; font-weight: 600; color: #6b7280; text-transform: uppercase;">Tracked SKUs</div>
                            <div style="font-size: 20px; font-weight: 800; color: #111827; margin-top: 4px;">{data['total_products']}</div>
                        </td>
                        <td width="4%"></td>
                        <td width="25%" style="background-color: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; text-align: center;">
                            <div style="font-size: 10px; font-weight: 600; color: #6b7280; text-transform: uppercase;">Avg Price</div>
                            <div style="font-size: 20px; font-weight: 800; color: #111827; margin-top: 4px;">${data['avg_price']}</div>
                        </td>
                        <td width="4%"></td>
                        <td width="25%" style="background-color: #fef2f2; border: 1px solid #fee2e2; border-radius: 8px; padding: 12px; text-align: center;">
                            <div style="font-size: 10px; font-weight: 600; color: #dc2626; text-transform: uppercase;">Price Drops</div>
                            <div style="font-size: 20px; font-weight: 800; color: #dc2626; margin-top: 4px;">{data['total_price_drops_count']}</div>
                        </td>
                        <td width="4%"></td>
                        <td width="25%" style="background-color: #fef3c7; border: 1px solid #fde68a; border-radius: 8px; padding: 12px; text-align: center;">
                            <div style="font-size: 10px; font-weight: 600; color: #d97706; text-transform: uppercase;">Stockout Opps</div>
                            <div style="font-size: 20px; font-weight: 800; color: #d97706; margin-top: 4px;">{len(data.get('stockout_opportunities', []))}</div>
                        </td>
                    </tr>
                </table>
            </div>

            <!-- Top Price Drops Table -->
            <div style="margin-bottom: 28px;">
                <h3 style="font-size: 15px; font-weight: 700; color: #111827; margin: 0 0 12px 0;">🚨 Top Competitor Price Drops</h3>
                <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse: collapse; font-size: 12px; border: 1px solid #e5e7eb; border-radius: 8px;">
                    <thead>
                        <tr style="background-color: #f9fafb; border-bottom: 1px solid #e5e7eb; text-align: left; color: #6b7280; font-size: 11px; text-transform: uppercase;">
                            <th style="padding: 10px 12px;">Product</th>
                            <th style="padding: 10px 12px;">Store</th>
                            <th style="padding: 10px 12px;">Old</th>
                            <th style="padding: 10px 12px;">New</th>
                            <th style="padding: 10px 12px;">Drop</th>
                        </tr>
                    </thead>
                    <tbody>
                        {drops_rows}
                    </tbody>
                </table>
            </div>

            <!-- Competitor Stockout Opportunities -->
            <div style="margin-bottom: 28px;">
                <h3 style="font-size: 15px; font-weight: 700; color: #111827; margin: 0 0 12px 0;">📦 Stockout Depletion & Sales Velocity Opportunities</h3>
                <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse: collapse; font-size: 12px; border: 1px solid #e5e7eb; border-radius: 8px;">
                    <thead>
                        <tr style="background-color: #f9fafb; border-bottom: 1px solid #e5e7eb; text-align: left; color: #6b7280; font-size: 11px; text-transform: uppercase;">
                            <th style="padding: 10px 12px;">Competitor Item</th>
                            <th style="padding: 10px 12px;">Store</th>
                            <th style="padding: 10px 12px;">Stock</th>
                            <th style="padding: 10px 12px;">Velocity</th>
                            <th style="padding: 10px 12px;">Runout Time</th>
                        </tr>
                    </thead>
                    <tbody>
                        {stockout_rows}
                    </tbody>
                </table>
            </div>

            <!-- Competitor Weaknesses Section -->
            <div style="margin-bottom: 24px;">
                <h3 style="font-size: 15px; font-weight: 700; color: #111827; margin: 0 0 12px 0;">🔍 Exploitable Competitor Product Vulnerabilities</h3>
                {vuln_cards}
            </div>
        </div>

        <!-- Footer -->
        <div style="background-color: #f9fafb; border-top: 1px solid #e5e7eb; padding: 20px 32px; font-size: 11px; color: #9ca3af; text-align: center;">
            This automated competitor digest was generated by E-Commerce Scraper Platform.<br>
            Configure report intervals or recipient distribution in the Reports Dashboard.
        </div>
    </div>
</body>
</html>"""
        return html

    def generate_pdf_report(self, data: Dict[str, Any]) -> bytes:
        """Generate a multi-page, formatted PDF report using ReportLab."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()

        # Custom typography styles
        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=22,
            leading=26,
            textColor=colors.HexColor('#1e1b4b'),
            spaceAfter=4,
        )

        subtitle_style = ParagraphStyle(
            'DocSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#6b7280'),
            spaceAfter=14,
        )

        h2_style = ParagraphStyle(
            'Heading2Custom',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=13,
            leading=16,
            textColor=colors.HexColor('#1f2937'),
            spaceBefore=14,
            spaceAfter=6,
        )

        cell_style = ParagraphStyle(
            'CellText',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#374151'),
        )

        cell_bold = ParagraphStyle(
            'CellBold',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#111827'),
        )

        elements = []

        # 1. Header Banner
        elements.append(Paragraph("E-Commerce Competitor Intelligence Report", title_style))
        elements.append(Paragraph(
            f"Scope: <b>{data['domain_scope']}</b> | Generated: <b>{data['generated_at']}</b> | Period: Last <b>{data['period_days']} days</b>",
            subtitle_style
        ))
        elements.append(Spacer(1, 8))

        # 2. Executive KPI Summary Table
        kpi_data = [
            [
                Paragraph("<b>Tracked SKUs</b>", cell_bold),
                Paragraph("<b>Average Price</b>", cell_bold),
                Paragraph("<b>Price Drops</b>", cell_bold),
                Paragraph("<b>Stockout Opportunities</b>", cell_bold),
            ],
            [
                Paragraph(f"<font size=12><b>{data['total_products']}</b></font>", cell_style),
                Paragraph(f"<font size=12><b>${data['avg_price']}</b></font>", cell_style),
                Paragraph(f"<font size=12 color='#dc2626'><b>{data['total_price_drops_count']}</b></font>", cell_style),
                Paragraph(f"<font size=12 color='#d97706'><b>{len(data.get('stockout_opportunities', []))}</b></font>", cell_style),
            ]
        ]
        kpi_table = Table(kpi_data, colWidths=[135, 135, 135, 135])
        kpi_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f9fafb')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(kpi_table)
        elements.append(Spacer(1, 12))

        # 3. Top Price Drops Table
        elements.append(Paragraph("🚨 Top Competitor Price Reductions", h2_style))
        drops_data = [
            [
                Paragraph("<b>Product</b>", cell_bold),
                Paragraph("<b>Domain</b>", cell_bold),
                Paragraph("<b>Old Price</b>", cell_bold),
                Paragraph("<b>New Price</b>", cell_bold),
                Paragraph("<b>Drop %</b>", cell_bold),
            ]
        ]
        for d in data.get("top_price_drops", [])[:8]:
            drops_data.append([
                Paragraph(d['name'][:45] + "...", cell_style),
                Paragraph(d['domain'], cell_style),
                Paragraph(f"${d['previous_price']}", cell_style),
                Paragraph(f"<b>${d['current_price']}</b>", cell_bold),
                Paragraph(f"<font color='#dc2626'><b>-{d['drop_percentage']}%</b></font>", cell_bold),
            ])

        if len(drops_data) == 1:
            drops_data.append([Paragraph("No recent price drops recorded.", cell_style), "", "", "", ""])

        drops_table = Table(drops_data, colWidths=[200, 95, 80, 80, 85])
        drops_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
        ]))
        elements.append(drops_table)
        elements.append(Spacer(1, 14))

        # 4. Stockout Opportunities Table
        elements.append(Paragraph("📦 Competitor Depletion & Stockout Opportunities", h2_style))
        stock_data = [
            [
                Paragraph("<b>Competitor Product</b>", cell_bold),
                Paragraph("<b>Store</b>", cell_bold),
                Paragraph("<b>Stock</b>", cell_bold),
                Paragraph("<b>Velocity</b>", cell_bold),
                Paragraph("<b>Est. Runout</b>", cell_bold),
            ]
        ]
        for s in data.get("stockout_opportunities", [])[:8]:
            stock_data.append([
                Paragraph(s['name'][:45] + "...", cell_style),
                Paragraph(s['domain'], cell_style),
                Paragraph(f"{s['current_stock']} units", cell_style),
                Paragraph(f"{s['sales_velocity_per_day']}/day", cell_style),
                Paragraph(f"<b>{s['days_until_stockout']} days</b>", cell_bold),
            ])

        if len(stock_data) == 1:
            stock_data.append([Paragraph("No imminent stockouts detected.", cell_style), "", "", "", ""])

        stock_table = Table(stock_data, colWidths=[200, 95, 80, 80, 85])
        stock_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
        ]))
        elements.append(stock_table)

        doc.build(elements)
        return buffer.getvalue()

    async def send_email_report(
        self,
        to_emails: List[str],
        subject: str,
        html_content: str,
        pdf_bytes: Optional[bytes] = None,
        pdf_filename: str = "competitor-intelligence-report.pdf"
    ) -> Tuple[bool, str]:
        """Dispatch email with HTML content and optional PDF attachment via SMTP."""
        if not to_emails:
            return False, "No recipient emails provided"

        smtp_host = getattr(settings, "SMTP_HOST", None) or os.environ.get("SMTP_HOST")
        smtp_port = int(getattr(settings, "SMTP_PORT", 587) or os.environ.get("SMTP_PORT", 587))
        smtp_user = getattr(settings, "SMTP_USER", None) or os.environ.get("SMTP_USER")
        smtp_password = getattr(settings, "SMTP_PASSWORD", None) or os.environ.get("SMTP_PASSWORD")
        from_email = getattr(settings, "SMTP_FROM_EMAIL", "reports@ecommerce-scrapper.io")

        msg = MIMEMultipart("mixed")
        msg["Subject"] = subject
        msg["From"] = from_email
        msg["To"] = ", ".join(to_emails)

        msg.attach(MIMEText(html_content, "html"))

        if pdf_bytes:
            pdf_part = MIMEApplication(pdf_bytes, _subtype="pdf")
            pdf_part.add_header("Content-Disposition", "attachment", filename=pdf_filename)
            msg.attach(pdf_part)

        if not smtp_host:
            logger.info(
                f"[Report Simulated Delivery] SMTP not configured. Report simulated for {to_emails} "
                f"(PDF attached: {bool(pdf_bytes)})."
            )
            return True, f"Simulated delivery to {', '.join(to_emails)} (SMTP not configured)"

        try:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
                if getattr(settings, "SMTP_USE_TLS", True):
                    server.starttls()
                if smtp_user and smtp_password:
                    server.login(smtp_user, smtp_password)
                server.sendmail(from_email, to_emails, msg.as_string())
            return True, f"Report sent successfully to {len(to_emails)} recipients"
        except Exception as e:
            logger.error(f"Failed to send report email: {e}")
            return False, str(e)

    async def trigger_schedule_report(
        self,
        db: AsyncSession,
        schedule_id: int
    ) -> Dict[str, Any]:
        """Execute a report schedule, compile data, save report, and send email."""
        schedule = await db.get(ReportSchedule, schedule_id)
        if not schedule:
            raise ValueError(f"Report schedule {schedule_id} not found")

        now = datetime.now(timezone.utc)
        data = await self.compile_intelligence_data(db, domain=schedule.domain_filter)

        html_report = self.generate_html_report(data)
        pdf_bytes = self.generate_pdf_report(data) if schedule.format in ("both", "pdf") else None

        # Send email if configured
        recipients = schedule.recipient_emails or []
        email_sent = False
        error_msg = None

        if recipients and schedule.format in ("both", "email_html"):
            subject = f"📊 Competitor Intelligence Digest: {schedule.name} ({now.strftime('%b %d, %Y')})"
            success, msg = await self.send_email_report(
                to_emails=recipients,
                subject=subject,
                html_content=html_report,
                pdf_bytes=pdf_bytes,
                pdf_filename=f"{schedule.name.lower().replace(' ', '_')}_{now.strftime('%Y%m%d')}.pdf"
            )
            email_sent = success
            if not success:
                error_msg = msg

        # Save generated report
        report_record = GeneratedReport(
            schedule_id=schedule.id,
            title=f"{schedule.name} - {now.strftime('%b %d, %Y')}",
            domain=schedule.domain_filter,
            metrics_summary={
                "total_products": data["total_products"],
                "avg_price": data["avg_price"],
                "price_drops_count": data["total_price_drops_count"],
                "stockout_opportunities_count": len(data.get("stockout_opportunities", [])),
            },
            html_content=html_report,
            pdf_filename=f"report_{schedule.id}_{int(now.timestamp())}.pdf" if pdf_bytes else None,
            status="sent" if email_sent or not recipients else "ready",
            error_message=error_msg,
        )
        db.add(report_record)

        # Update schedule next run
        schedule.last_sent_at = now
        schedule.total_sent = (schedule.total_sent or 0) + 1
        schedule.last_status = "success" if not error_msg else "failed"
        schedule.last_error = error_msg
        if schedule.cron_expression:
            schedule.next_run_at = calculate_next_run(schedule.cron_expression, now)

        await db.commit()
        await db.refresh(report_record)

        return {
            "success": True,
            "report_id": report_record.id,
            "title": report_record.title,
            "recipients": recipients,
            "email_dispatched": email_sent,
            "next_run_at": schedule.next_run_at.isoformat() if schedule.next_run_at else None,
        }

    async def get_all_schedules(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """List all configured report schedules."""
        stmt = select(ReportSchedule).order_by(ReportSchedule.id.desc())
        res = await db.execute(stmt)
        records = res.scalars().all()
        return [r.to_dict() for r in records]

    async def create_schedule(
        self,
        db: AsyncSession,
        name: str,
        recipient_emails: List[str],
        frequency: str = "weekly",
        cron_expression: str = "0 9 * * 1",
        frequency_label: str = "Weekly",
        format: str = "both",
        domain_filter: Optional[str] = None,
        include_price_drops: bool = True,
        include_catalog_diffs: bool = True,
        include_stockouts: bool = True,
        include_sentiment: bool = True,
    ) -> Dict[str, Any]:
        """Create new scheduled report configuration."""
        now = datetime.now(timezone.utc)
        next_run = calculate_next_run(cron_expression, now) if cron_expression else None

        sched = ReportSchedule(
            name=name,
            recipient_emails=recipient_emails,
            frequency=frequency,
            cron_expression=cron_expression,
            frequency_label=frequency_label,
            format=format,
            domain_filter=domain_filter,
            include_price_drops=include_price_drops,
            include_catalog_diffs=include_catalog_diffs,
            include_stockouts=include_stockouts,
            include_sentiment=include_sentiment,
            is_active=True,
            next_run_at=next_run,
        )
        db.add(sched)
        await db.commit()
        await db.refresh(sched)
        return sched.to_dict()

    async def delete_schedule(self, db: AsyncSession, schedule_id: int) -> bool:
        """Delete report schedule by ID."""
        sched = await db.get(ReportSchedule, schedule_id)
        if not sched:
            return False
        await db.delete(sched)
        await db.commit()
        return True


report_service = ReportService()
