import pandas as pd

from app.services.delay_prediction_service import build_delay_risk_report


def get_exception_priority(exception_type: str, delay_risk_category: str) -> str:
    """
    Convert exception type and delay risk into operational priority.

    Priority meaning:
    - P1: Immediate action required
    - P2: Same-day action required
    - P3: Monitor and resolve within normal workflow
    - P4: No immediate action
    """

    if delay_risk_category == "Critical":
        return "P1"

    if exception_type in [
        "Inventory Shortage",
        "SLA Breach Risk",
        "High Value Customer Risk"
    ]:
        return "P1" if delay_risk_category in ["High", "Critical"] else "P2"

    if exception_type in [
        "Warehouse Congestion",
        "Courier Delay",
        "Stockout Risk"
    ]:
        return "P2" if delay_risk_category in ["High", "Critical"] else "P3"

    if exception_type == "Manual Review Required":
        return "P3"

    return "P4"


def classify_exception(order_analysis: dict) -> dict:
    """
    Classify the main logistics exception for an analyzed order.

    The goal is to identify the most important business issue behind the risk.
    """

    delay_risk_category = order_analysis.get("delay_risk_category", "Low")
    delay_risk_score = int(order_analysis.get("delay_risk_score", 0) or 0)

    stockout_risk = order_analysis.get("stockout_risk", "Low")
    selection_risk_level = order_analysis.get("selection_risk_level", "Low")
    courier_risk_level = order_analysis.get("courier_risk_level", "Low")

    customer_tier = order_analysis.get("customer_tier", "Bronze")
    order_value = float(order_analysis.get("order_value", 0) or 0)

    warehouse_utilization_rate = float(
        order_analysis.get("warehouse_utilization_rate", 0) or 0
    )

    courier_delay_rate = float(
        order_analysis.get("courier_delay_rate", 0) or 0
    )

    promised_delivery_window_days = int(
        order_analysis.get("promised_delivery_window_days", 0) or 0
    )

    can_fulfill = order_analysis.get("can_fulfill", True)

    exception_type = "No Immediate Exception"
    exception_reason = "Order can proceed through standard fulfillment."
    owning_team = "Standard Operations"
    escalation_required = False

    # 1. Inventory and fulfillment availability issues
    if can_fulfill is False:
        exception_type = "Inventory Shortage"
        exception_reason = "No warehouse has enough available stock to fulfill the order."
        owning_team = "Inventory Planning"
        escalation_required = True

    elif stockout_risk == "Critical":
        exception_type = "Stockout Risk"
        exception_reason = "Inventory is at or below safety stock level."
        owning_team = "Inventory Planning"
        escalation_required = True

    elif stockout_risk == "High":
        exception_type = "Stockout Risk"
        exception_reason = "Inventory is below reorder point and may affect future fulfillment."
        owning_team = "Inventory Planning"
        escalation_required = delay_risk_category in ["High", "Critical"]

    # 2. Warehouse congestion issues
    elif warehouse_utilization_rate >= 90 or selection_risk_level == "Critical":
        exception_type = "Warehouse Congestion"
        exception_reason = "Recommended warehouse is operating at high utilization or has critical selection risk."
        owning_team = "Warehouse Operations"
        escalation_required = delay_risk_category in ["High", "Critical"]

    elif warehouse_utilization_rate >= 85 or selection_risk_level == "High":
        exception_type = "Warehouse Congestion"
        exception_reason = "Warehouse utilization is elevated and may impact fulfillment speed."
        owning_team = "Warehouse Operations"
        escalation_required = delay_risk_category == "Critical"

    # 3. Courier performance issues
    elif courier_delay_rate >= 20 or courier_risk_level == "Critical":
        exception_type = "Courier Delay"
        exception_reason = "Recommended courier has elevated delay risk."
        owning_team = "Transport Management"
        escalation_required = delay_risk_category in ["High", "Critical"]

    elif courier_delay_rate >= 15 or courier_risk_level == "High":
        exception_type = "Courier Delay"
        exception_reason = "Courier performance requires monitoring due to delay exposure."
        owning_team = "Transport Management"
        escalation_required = delay_risk_category == "Critical"

    # 4. SLA breach risk
    elif promised_delivery_window_days <= 1 and delay_risk_category in ["High", "Critical"]:
        exception_type = "SLA Breach Risk"
        exception_reason = "Order has a tight promised delivery window and high predicted delay risk."
        owning_team = "SLA Control Tower"
        escalation_required = True

    elif delay_risk_score >= 75:
        exception_type = "SLA Breach Risk"
        exception_reason = "Delay risk score is high enough to threaten promised delivery performance."
        owning_team = "SLA Control Tower"
        escalation_required = True

    # 5. High-value customer risk
    elif customer_tier in ["Platinum", "Gold"] and delay_risk_category in ["High", "Critical"]:
        exception_type = "High Value Customer Risk"
        exception_reason = "High-value customer order has elevated fulfillment or delivery risk."
        owning_team = "Customer Experience"
        escalation_required = True

    elif order_value >= 50000 and delay_risk_category in ["High", "Critical"]:
        exception_type = "High Value Customer Risk"
        exception_reason = "High-value order has elevated fulfillment or delivery risk."
        owning_team = "Customer Experience"
        escalation_required = True

    # 6. Manual review
    elif delay_risk_category == "Medium":
        exception_type = "Manual Review Required"
        exception_reason = "Order has moderate risk indicators and should be monitored."
        owning_team = "Operations Analyst"
        escalation_required = False

    priority = get_exception_priority(
        exception_type,
        delay_risk_category
    )

    return {
        "exception_type": exception_type,
        "exception_reason": exception_reason,
        "exception_priority": priority,
        "owning_team": owning_team,
        "escalation_required": escalation_required,
        "is_exception": exception_type != "No Immediate Exception"
    }


def build_exception_report(
    orders_df: pd.DataFrame,
    warehouses_df: pd.DataFrame,
    inventory_df: pd.DataFrame,
    couriers_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Build a full exception report for all orders.

    This report combines delay risk analysis with business exception classification.
    """

    delay_report = build_delay_risk_report(
        orders_df,
        warehouses_df,
        inventory_df,
        couriers_df
    )

    exception_results = []

    for _, row in delay_report.iterrows():
        row_dict = row.to_dict()
        exception = classify_exception(row_dict)

        combined = {
            **row_dict,
            **exception
        }

        exception_results.append(combined)

    return pd.DataFrame(exception_results)


def get_active_exceptions(exception_report: pd.DataFrame) -> pd.DataFrame:
    """
    Return only orders that have active exceptions.
    """

    return exception_report[
        exception_report["is_exception"] == True
    ].copy()


def get_priority_exceptions(exception_report: pd.DataFrame) -> pd.DataFrame:
    """
    Return only high-priority exceptions: P1 and P2.
    """

    return exception_report[
        exception_report["exception_priority"].isin(["P1", "P2"])
    ].copy()
