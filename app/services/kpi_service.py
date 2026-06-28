import pandas as pd


def safe_percentage(numerator: float, denominator: float) -> float:
    """
    Calculate percentage safely.

    This prevents divide-by-zero errors.
    """

    if denominator == 0:
        return 0.0

    return round((numerator / denominator) * 100, 2)


def calculate_logistics_kpis(exception_report: pd.DataFrame) -> dict:
    """
    Calculate executive-level logistics KPIs.

    The input is the full exception report created by the exception classifier.
    """

    total_orders = len(exception_report)

    active_exceptions = int(exception_report["is_exception"].sum())
    no_exception_orders = total_orders - active_exceptions

    p1_exceptions = int((exception_report["exception_priority"] == "P1").sum())
    p2_exceptions = int((exception_report["exception_priority"] == "P2").sum())
    p3_exceptions = int((exception_report["exception_priority"] == "P3").sum())
    p4_exceptions = int((exception_report["exception_priority"] == "P4").sum())

    high_risk_orders = int((exception_report["delay_risk_category"] == "High").sum())
    critical_risk_orders = int((exception_report["delay_risk_category"] == "Critical").sum())

    high_and_critical = exception_report[
        exception_report["delay_risk_category"].isin(["High", "Critical"])
    ]

    p1_p2_orders = exception_report[
        exception_report["exception_priority"].isin(["P1", "P2"])
    ]

    revenue_at_risk = float(high_and_critical["order_value"].sum())
    p1_p2_revenue_at_risk = float(p1_p2_orders["order_value"].sum())

    average_delay_risk_score = round(
        float(exception_report["delay_risk_score"].mean()),
        2
    )

    predicted_delay_rate = safe_percentage(
        high_risk_orders + critical_risk_orders,
        total_orders
    )

    active_exception_rate = safe_percentage(
        active_exceptions,
        total_orders
    )

    perfect_order_rate_estimate = safe_percentage(
        no_exception_orders,
        total_orders
    )

    priority_exception_rate = safe_percentage(
        p1_exceptions + p2_exceptions,
        total_orders
    )

    escalation_required_count = int(exception_report["escalation_required"].sum())

    escalation_rate = safe_percentage(
        escalation_required_count,
        total_orders
    )

    platinum_orders_at_risk = int(
        (
            (exception_report["customer_tier"] == "Platinum") &
            (exception_report["delay_risk_category"].isin(["High", "Critical"]))
        ).sum()
    )

    gold_orders_at_risk = int(
        (
            (exception_report["customer_tier"] == "Gold") &
            (exception_report["delay_risk_category"].isin(["High", "Critical"]))
        ).sum()
    )

    stockout_risk_count = int(
        exception_report["exception_type"].isin(
            ["Stockout Risk", "Inventory Shortage"]
        ).sum()
    )

    warehouse_congestion_count = int(
        (exception_report["exception_type"] == "Warehouse Congestion").sum()
    )

    courier_delay_count = int(
        (exception_report["exception_type"] == "Courier Delay").sum()
    )

    manual_review_count = int(
        (exception_report["exception_type"] == "Manual Review Required").sum()
    )

    # Estimated fill rate:
    # If the can_fulfill field exists, use it.
    # If not, assume all analyzed orders were fulfillable.
    if "can_fulfill" in exception_report.columns:
        fill_rate_estimate = safe_percentage(
            int(exception_report["can_fulfill"].sum()),
            total_orders
        )
    else:
        fill_rate_estimate = 100.0

    # Estimated OTIF:
    # In this portfolio model, orders with Low or Medium risk are treated as likely on-time.
    likely_on_time_orders = int(
        exception_report["delay_risk_category"].isin(["Low", "Medium"]).sum()
    )

    otif_estimate = safe_percentage(
        likely_on_time_orders,
        total_orders
    )

    # Overall operating status
    if critical_risk_orders > 0 or p1_exceptions > 0:
        overall_status = "At Risk"
    elif high_risk_orders > 0 or p2_exceptions > 0:
        overall_status = "Watch"
    else:
        overall_status = "Healthy"

    return {
        "total_orders": total_orders,
        "overall_status": overall_status,

        "active_exceptions": active_exceptions,
        "active_exception_rate": active_exception_rate,

        "p1_exceptions": p1_exceptions,
        "p2_exceptions": p2_exceptions,
        "p3_exceptions": p3_exceptions,
        "p4_exceptions": p4_exceptions,
        "p1_p2_priority_exceptions": p1_exceptions + p2_exceptions,
        "priority_exception_rate": priority_exception_rate,

        "high_risk_orders": high_risk_orders,
        "critical_risk_orders": critical_risk_orders,
        "predicted_delay_rate": predicted_delay_rate,
        "average_delay_risk_score": average_delay_risk_score,

        "revenue_at_risk": round(revenue_at_risk, 2),
        "p1_p2_revenue_at_risk": round(p1_p2_revenue_at_risk, 2),

        "perfect_order_rate_estimate": perfect_order_rate_estimate,
        "fill_rate_estimate": fill_rate_estimate,
        "otif_estimate": otif_estimate,

        "escalation_required_count": escalation_required_count,
        "escalation_rate": escalation_rate,

        "platinum_orders_at_risk": platinum_orders_at_risk,
        "gold_orders_at_risk": gold_orders_at_risk,

        "stockout_risk_count": stockout_risk_count,
        "warehouse_congestion_count": warehouse_congestion_count,
        "courier_delay_count": courier_delay_count,
        "manual_review_count": manual_review_count,
    }


def build_kpi_dataframe(kpis: dict) -> pd.DataFrame:
    """
    Convert KPI dictionary into a one-row DataFrame for export and dashboard use.
    """

    return pd.DataFrame([kpis])


def build_exception_type_summary(exception_report: pd.DataFrame) -> pd.DataFrame:
    """
    Summarize exception counts and revenue at risk by exception type.
    """

    summary = (
        exception_report
        .groupby("exception_type")
        .agg(
            order_count=("order_id", "count"),
            revenue_total=("order_value", "sum"),
            average_delay_risk_score=("delay_risk_score", "mean")
        )
        .reset_index()
    )

    summary["average_delay_risk_score"] = summary["average_delay_risk_score"].round(2)

    return summary.sort_values(
        by="order_count",
        ascending=False
    )


def build_owning_team_summary(exception_report: pd.DataFrame) -> pd.DataFrame:
    """
    Summarize exception workload by owning team.
    """

    summary = (
        exception_report
        .groupby("owning_team")
        .agg(
            order_count=("order_id", "count"),
            escalations=("escalation_required", "sum"),
            revenue_total=("order_value", "sum"),
            average_delay_risk_score=("delay_risk_score", "mean")
        )
        .reset_index()
    )

    summary["average_delay_risk_score"] = summary["average_delay_risk_score"].round(2)

    return summary.sort_values(
        by="order_count",
        ascending=False
    )


def build_warehouse_performance_summary(exception_report: pd.DataFrame) -> pd.DataFrame:
    """
    Summarize risk by recommended warehouse.
    """

    summary = (
        exception_report
        .groupby(
            [
                "recommended_warehouse_id",
                "recommended_warehouse_name",
                "recommended_warehouse_region"
            ],
            dropna=False
        )
        .agg(
            orders_routed=("order_id", "count"),
            average_warehouse_utilization=("warehouse_utilization_rate", "mean"),
            average_delay_risk_score=("delay_risk_score", "mean"),
            high_risk_orders=("delay_risk_category", lambda x: x.isin(["High", "Critical"]).sum()),
            revenue_total=("order_value", "sum")
        )
        .reset_index()
    )

    summary["average_warehouse_utilization"] = summary["average_warehouse_utilization"].round(2)
    summary["average_delay_risk_score"] = summary["average_delay_risk_score"].round(2)

    return summary.sort_values(
        by="high_risk_orders",
        ascending=False
    )


def build_courier_performance_summary(exception_report: pd.DataFrame) -> pd.DataFrame:
    """
    Summarize risk by recommended courier.
    """

    summary = (
        exception_report
        .groupby(
            [
                "recommended_courier_id",
                "recommended_courier_name",
                "recommended_courier_region"
            ],
            dropna=False
        )
        .agg(
            orders_assigned=("order_id", "count"),
            average_on_time_rate=("courier_on_time_rate", "mean"),
            average_delay_rate=("courier_delay_rate", "mean"),
            average_delay_risk_score=("delay_risk_score", "mean"),
            high_risk_orders=("delay_risk_category", lambda x: x.isin(["High", "Critical"]).sum()),
            revenue_total=("order_value", "sum")
        )
        .reset_index()
    )

    summary["average_on_time_rate"] = summary["average_on_time_rate"].round(2)
    summary["average_delay_rate"] = summary["average_delay_rate"].round(2)
    summary["average_delay_risk_score"] = summary["average_delay_risk_score"].round(2)

    return summary.sort_values(
        by="high_risk_orders",
        ascending=False
    )


def build_region_summary(exception_report: pd.DataFrame) -> pd.DataFrame:
    """
    Summarize order risk by customer region.
    """

    summary = (
        exception_report
        .groupby("customer_region")
        .agg(
            total_orders=("order_id", "count"),
            active_exceptions=("is_exception", "sum"),
            escalations=("escalation_required", "sum"),
            average_delay_risk_score=("delay_risk_score", "mean"),
            revenue_total=("order_value", "sum")
        )
        .reset_index()
    )

    summary["active_exception_rate"] = summary.apply(
        lambda row: safe_percentage(row["active_exceptions"], row["total_orders"]),
        axis=1
    )

    summary["average_delay_risk_score"] = summary["average_delay_risk_score"].round(2)

    return summary.sort_values(
        by="active_exceptions",
        ascending=False
    )
