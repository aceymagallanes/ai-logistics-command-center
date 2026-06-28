import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from app.services.exception_classifier_service import build_exception_report
from app.services.kpi_service import (
    calculate_logistics_kpis,
    build_kpi_dataframe,
    build_exception_type_summary,
    build_owning_team_summary,
    build_warehouse_performance_summary,
    build_courier_performance_summary,
    build_region_summary,
)


BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def export_dataframe(df: pd.DataFrame, filename: str) -> str:
    """
    Export a DataFrame to the app/outputs folder.

    Returns the exported file path as a string.
    """

    output_path = OUTPUT_DIR / filename
    df.to_csv(output_path, index=False)
    return str(output_path)


def build_top_risks(exception_report: pd.DataFrame) -> list:
    """
    Build a small list of top risks for executive summary input.
    """

    top_risks = []

    exception_counts = exception_report["exception_type"].value_counts()

    for exception_type, count in exception_counts.items():
        if exception_type == "No Immediate Exception":
            continue

        related_orders = exception_report[
            exception_report["exception_type"] == exception_type
        ]

        revenue_impact = float(related_orders["order_value"].sum())
        average_risk_score = round(float(related_orders["delay_risk_score"].mean()), 2)

        top_risks.append(
            {
                "risk_type": exception_type,
                "affected_orders": int(count),
                "revenue_impact": round(revenue_impact, 2),
                "average_delay_risk_score": average_risk_score,
            }
        )

    top_risks = sorted(
        top_risks,
        key=lambda item: item["affected_orders"],
        reverse=True
    )

    return top_risks[:5]


def build_recommended_actions(exception_report: pd.DataFrame) -> list:
    """
    Build executive recommended actions based on the highest-risk patterns.
    """

    actions = []

    courier_delay_count = int(
        (exception_report["exception_type"] == "Courier Delay").sum()
    )

    stockout_risk_count = int(
        (exception_report["exception_type"] == "Stockout Risk").sum()
    )

    warehouse_congestion_count = int(
        (exception_report["exception_type"] == "Warehouse Congestion").sum()
    )

    p1_count = int(
        (exception_report["exception_priority"] == "P1").sum()
    )

    if courier_delay_count > 0:
        actions.append(
            "Review courier performance for high-risk lanes and prioritize alternate courier routing for P1/P2 orders."
        )

    if stockout_risk_count > 0:
        actions.append(
            "Trigger replenishment review for SKUs with Critical or High stockout risk."
        )

    if warehouse_congestion_count > 0:
        actions.append(
            "Assess warehouse load balancing and route orders to overflow or national backup fulfillment centers where appropriate."
        )

    if p1_count > 0:
        actions.append(
            "Escalate all P1 exceptions to the operations control tower for same-day resolution."
        )

    actions.append(
        "Prioritize Platinum and Gold customer orders with High or Critical delay risk."
    )

    return actions


def build_executive_summary_input(
    kpis: dict,
    exception_report: pd.DataFrame,
    exception_type_summary: pd.DataFrame,
    owning_team_summary: pd.DataFrame,
    warehouse_summary: pd.DataFrame,
    courier_summary: pd.DataFrame,
    region_summary: pd.DataFrame,
) -> dict:
    """
    Build a JSON-ready executive summary input for Claude or n8n.

    This is not the final AI-written executive brief.
    This is the structured business data that Claude will summarize.
    """

    top_priority_orders = exception_report[
        exception_report["exception_priority"].isin(["P1", "P2"])
    ].sort_values(
        by=["exception_priority", "delay_risk_score"],
        ascending=[True, False]
    ).head(10)

    return {
        "report_generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "report_name": "AI Warehouse & Logistics Command Center Executive Summary Input",
        "overall_status": kpis.get("overall_status"),
        "executive_kpis": kpis,
        "top_risks": build_top_risks(exception_report),
        "recommended_actions": build_recommended_actions(exception_report),
        "exception_type_summary": exception_type_summary.to_dict(orient="records"),
        "owning_team_summary": owning_team_summary.to_dict(orient="records"),
        "warehouse_performance_summary": warehouse_summary.to_dict(orient="records"),
        "courier_performance_summary": courier_summary.to_dict(orient="records"),
        "region_summary": region_summary.to_dict(orient="records"),
        "top_priority_orders": top_priority_orders[
            [
                "order_id",
                "customer_region",
                "customer_tier",
                "order_value",
                "delay_risk_score",
                "delay_risk_category",
                "exception_type",
                "exception_priority",
                "owning_team",
                "recommended_action",
            ]
        ].to_dict(orient="records"),
    }


def export_executive_summary_input(executive_summary_input: dict) -> str:
    """
    Export executive summary input as JSON.
    """

    output_path = OUTPUT_DIR / "executive_summary_input.json"

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(executive_summary_input, file, indent=2)

    return str(output_path)


def run_full_export(
    orders_df: pd.DataFrame,
    warehouses_df: pd.DataFrame,
    inventory_df: pd.DataFrame,
    couriers_df: pd.DataFrame,
) -> dict:
    """
    Run the full analysis pipeline and export all dashboard-ready files.

    Pipeline:
    1. Build exception report.
    2. Calculate KPIs.
    3. Build summary tables.
    4. Export CSV and JSON files.
    5. Return a list of generated output files.
    """

    exception_report = build_exception_report(
        orders_df,
        warehouses_df,
        inventory_df,
        couriers_df,
    )

    kpis = calculate_logistics_kpis(exception_report)
    kpi_df = build_kpi_dataframe(kpis)

    exception_type_summary = build_exception_type_summary(exception_report)
    owning_team_summary = build_owning_team_summary(exception_report)
    warehouse_summary = build_warehouse_performance_summary(exception_report)
    courier_summary = build_courier_performance_summary(exception_report)
    region_summary = build_region_summary(exception_report)

    executive_summary_input = build_executive_summary_input(
        kpis=kpis,
        exception_report=exception_report,
        exception_type_summary=exception_type_summary,
        owning_team_summary=owning_team_summary,
        warehouse_summary=warehouse_summary,
        courier_summary=courier_summary,
        region_summary=region_summary,
    )

    exported_files = {
        "logistics_kpis": export_dataframe(kpi_df, "logistics_kpis.csv"),
        "order_risk_report": export_dataframe(exception_report, "order_risk_report.csv"),
        "exception_type_summary": export_dataframe(exception_type_summary, "exception_type_summary.csv"),
        "owning_team_summary": export_dataframe(owning_team_summary, "owning_team_summary.csv"),
        "warehouse_performance_summary": export_dataframe(warehouse_summary, "warehouse_performance_summary.csv"),
        "courier_performance_summary": export_dataframe(courier_summary, "courier_performance_summary.csv"),
        "region_summary": export_dataframe(region_summary, "region_summary.csv"),
        "executive_summary_input": export_executive_summary_input(executive_summary_input),
    }

    return {
        "status": "success",
        "message": "Dashboard-ready logistics output files generated successfully.",
        "generated_files": exported_files,
        "kpis": kpis,
    }
