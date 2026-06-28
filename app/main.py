from fastapi import FastAPI, HTTPException, Body
import pandas as pd

from app.services.data_loader import DataLoader
from app.services.warehouse_selection_service import recommend_best_warehouse
from app.services.courier_selection_service import recommend_best_courier
from app.services.delay_prediction_service import (
    predict_delay_risk,
    build_delay_risk_report,
)
from app.services.exception_classifier_service import (
    classify_exception,
    build_exception_report,
    get_active_exceptions,
    get_priority_exceptions,
)
from app.services.kpi_service import (
    calculate_logistics_kpis,
    build_exception_type_summary,
    build_owning_team_summary,
    build_warehouse_performance_summary,
    build_courier_performance_summary,
    build_region_summary,
)
from app.services.export_service import run_full_export


app = FastAPI(
    title="AI Warehouse & Logistics Command Center",
    description="An AI-powered logistics control tower for warehouse routing, courier selection, delivery risk prediction, exception classification, and executive KPI reporting.",
    version="1.0.0",
)


def df_to_records(df: pd.DataFrame) -> list:
    """
    Convert DataFrame to clean JSON records.
    """
    clean_df = df.where(pd.notnull(df), None)
    return clean_df.to_dict(orient="records")


def load_core_data():
    """
    Load all required logistics datasets.
    """
    loader = DataLoader()

    return {
        "orders": loader.load_orders(),
        "warehouses": loader.load_warehouses(),
        "inventory": loader.load_inventory(),
        "couriers": loader.load_couriers(),
        "delivery_history": loader.load_delivery_history(),
    }


@app.get("/")
def root():
    return {
        "project": "AI Warehouse & Logistics Command Center",
        "description": "A logistics intelligence API for e-commerce fulfillment risk analysis.",
        "status": "running",
        "available_endpoints": [
            "/health",
            "/orders",
            "/warehouses",
            "/inventory",
            "/couriers",
            "/delivery-history",
            "/analyze/orders",
            "/exceptions",
            "/exceptions/priority",
            "/kpis",
            "/summaries/exception-types",
            "/summaries/owning-teams",
            "/summaries/warehouses",
            "/summaries/couriers",
            "/summaries/regions",
            "/export",
            "/order/analyze",
        ],
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "message": "AI Warehouse & Logistics Command Center API is running.",
    }


@app.get("/orders")
def get_orders():
    data = load_core_data()
    return {
        "count": len(data["orders"]),
        "orders": df_to_records(data["orders"]),
    }


@app.get("/warehouses")
def get_warehouses():
    data = load_core_data()
    return {
        "count": len(data["warehouses"]),
        "warehouses": df_to_records(data["warehouses"]),
    }


@app.get("/inventory")
def get_inventory():
    data = load_core_data()
    return {
        "count": len(data["inventory"]),
        "inventory": df_to_records(data["inventory"]),
    }


@app.get("/couriers")
def get_couriers():
    data = load_core_data()
    return {
        "count": len(data["couriers"]),
        "couriers": df_to_records(data["couriers"]),
    }


@app.get("/delivery-history")
def get_delivery_history():
    data = load_core_data()
    return {
        "count": len(data["delivery_history"]),
        "delivery_history": df_to_records(data["delivery_history"]),
    }


@app.get("/analyze/orders")
def analyze_orders():
    data = load_core_data()

    report = build_exception_report(
        data["orders"],
        data["warehouses"],
        data["inventory"],
        data["couriers"],
    )

    return {
        "count": len(report),
        "analysis": df_to_records(report),
    }


@app.get("/exceptions")
def get_exceptions():
    data = load_core_data()

    report = build_exception_report(
        data["orders"],
        data["warehouses"],
        data["inventory"],
        data["couriers"],
    )

    active_exceptions = get_active_exceptions(report)

    return {
        "count": len(active_exceptions),
        "exceptions": df_to_records(active_exceptions),
    }


@app.get("/exceptions/priority")
def get_priority_exception_orders():
    data = load_core_data()

    report = build_exception_report(
        data["orders"],
        data["warehouses"],
        data["inventory"],
        data["couriers"],
    )

    priority_exceptions = get_priority_exceptions(report)

    return {
        "count": len(priority_exceptions),
        "priority_exceptions": df_to_records(priority_exceptions),
    }


@app.get("/kpis")
def get_kpis():
    data = load_core_data()

    report = build_exception_report(
        data["orders"],
        data["warehouses"],
        data["inventory"],
        data["couriers"],
    )

    kpis = calculate_logistics_kpis(report)

    return {
        "kpis": kpis,
    }


@app.get("/summaries/exception-types")
def get_exception_type_summary():
    data = load_core_data()

    report = build_exception_report(
        data["orders"],
        data["warehouses"],
        data["inventory"],
        data["couriers"],
    )

    summary = build_exception_type_summary(report)

    return {
        "count": len(summary),
        "summary": df_to_records(summary),
    }


@app.get("/summaries/owning-teams")
def get_owning_team_summary():
    data = load_core_data()

    report = build_exception_report(
        data["orders"],
        data["warehouses"],
        data["inventory"],
        data["couriers"],
    )

    summary = build_owning_team_summary(report)

    return {
        "count": len(summary),
        "summary": df_to_records(summary),
    }


@app.get("/summaries/warehouses")
def get_warehouse_summary():
    data = load_core_data()

    report = build_exception_report(
        data["orders"],
        data["warehouses"],
        data["inventory"],
        data["couriers"],
    )

    summary = build_warehouse_performance_summary(report)

    return {
        "count": len(summary),
        "summary": df_to_records(summary),
    }


@app.get("/summaries/couriers")
def get_courier_summary():
    data = load_core_data()

    report = build_exception_report(
        data["orders"],
        data["warehouses"],
        data["inventory"],
        data["couriers"],
    )

    summary = build_courier_performance_summary(report)

    return {
        "count": len(summary),
        "summary": df_to_records(summary),
    }


@app.get("/summaries/regions")
def get_region_summary():
    data = load_core_data()

    report = build_exception_report(
        data["orders"],
        data["warehouses"],
        data["inventory"],
        data["couriers"],
    )

    summary = build_region_summary(report)

    return {
        "count": len(summary),
        "summary": df_to_records(summary),
    }


@app.get("/export")
def export_dashboard_files():
    data = load_core_data()

    result = run_full_export(
        data["orders"],
        data["warehouses"],
        data["inventory"],
        data["couriers"],
    )

    return result


@app.post("/order/analyze")
def analyze_single_order(order: dict = Body(...)):
    """
    Analyze one order sent through the API.

    This endpoint is useful for n8n, demos, and future live order simulation.
    """

    required_fields = [
        "order_id",
        "customer_id",
        "customer_location",
        "customer_region",
        "product_sku",
        "quantity",
        "order_value",
        "customer_tier",
        "order_date",
        "promised_delivery_date",
    ]

    missing_fields = [
        field for field in required_fields
        if field not in order
    ]

    if missing_fields:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Missing required order fields.",
                "missing_fields": missing_fields,
            },
        )

    data = load_core_data()

    warehouse_result = recommend_best_warehouse(
        order,
        data["warehouses"],
        data["inventory"],
    )

    courier_result = recommend_best_courier(
        order,
        data["couriers"],
    )

    delay_result = predict_delay_risk(
        order,
        warehouse_result,
        courier_result,
    )

    combined_analysis = {
        **order,

        "recommended_warehouse_id": warehouse_result.get("recommended_warehouse_id"),
        "recommended_warehouse_name": warehouse_result.get("recommended_warehouse_name"),
        "recommended_warehouse_region": warehouse_result.get("recommended_warehouse_region"),
        "warehouse_utilization_rate": warehouse_result.get("warehouse_utilization_rate"),
        "selection_score": warehouse_result.get("selection_score"),
        "selection_risk_level": warehouse_result.get("selection_risk_level"),
        "stockout_risk": warehouse_result.get("stockout_risk"),
        "remaining_stock_after_order": warehouse_result.get("remaining_stock_after_order"),
        "warehouse_selection_reason": warehouse_result.get("selection_reason"),
        "can_fulfill": warehouse_result.get("can_fulfill"),

        "recommended_courier_id": courier_result.get("recommended_courier_id"),
        "recommended_courier_name": courier_result.get("recommended_courier_name"),
        "recommended_courier_region": courier_result.get("recommended_courier_region"),
        "courier_score": courier_result.get("courier_score"),
        "courier_risk_level": courier_result.get("courier_risk_level"),
        "courier_on_time_rate": courier_result.get("on_time_rate"),
        "courier_delay_rate": courier_result.get("delay_rate"),
        "average_delivery_days": courier_result.get("average_delivery_days"),
        "courier_selection_reason": courier_result.get("courier_selection_reason"),

        "delay_risk_score": delay_result.get("delay_risk_score"),
        "delay_risk_category": delay_result.get("delay_risk_category"),
        "promised_delivery_window_days": delay_result.get("promised_delivery_window_days"),
        "delay_risk_explanation": delay_result.get("delay_risk_explanation"),
        "recommended_action": delay_result.get("recommended_action"),
    }

    exception_result = classify_exception(combined_analysis)

    return {
        "order_id": order["order_id"],
        "analysis": {
            **combined_analysis,
            **exception_result,
        },
    }
