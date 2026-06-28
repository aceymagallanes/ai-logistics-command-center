from datetime import datetime
import pandas as pd

from app.services.warehouse_selection_service import recommend_best_warehouse
from app.services.courier_selection_service import recommend_best_courier


def calculate_promised_delivery_window(order: dict) -> int:
    """
    Calculate the number of days between order date and promised delivery date.

    Business meaning:
    A shorter delivery window means higher SLA pressure.
    """

    order_date = datetime.strptime(str(order["order_date"]), "%Y-%m-%d")
    promised_delivery_date = datetime.strptime(
        str(order["promised_delivery_date"]),
        "%Y-%m-%d"
    )

    return max((promised_delivery_date - order_date).days, 1)


def get_delay_risk_category(score: int) -> str:
    """
    Convert delay risk score into a dashboard-friendly risk category.
    """

    if score <= 30:
        return "Low"
    elif score <= 60:
        return "Medium"
    elif score <= 80:
        return "High"
    else:
        return "Critical"


def get_recommended_action(risk_category: str, customer_tier: str) -> str:
    """
    Return an operational recommendation based on the risk category and customer tier.
    """

    if risk_category == "Critical":
        if customer_tier in ["Platinum", "Gold"]:
            return "Immediate escalation required. Prioritize fulfillment, assign best courier, and notify operations lead."
        return "Immediate operations review required. Check warehouse capacity, courier availability, and SLA exposure."

    if risk_category == "High":
        if customer_tier in ["Platinum", "Gold"]:
            return "Prioritize order handling and monitor courier dispatch closely due to high-value customer impact."
        return "Monitor closely and prepare contingency routing if fulfillment risk increases."

    if risk_category == "Medium":
        return "Proceed with fulfillment but monitor warehouse and courier risk indicators."

    return "Proceed with standard fulfillment."


def predict_delay_risk(
    order: dict,
    warehouse_result: dict,
    courier_result: dict
) -> dict:
    """
    Predict late delivery risk for a single order using rules-based logic.

    This is Version 1 of the prediction engine.
    It is intentionally explainable, which makes it suitable for business users.
    """

    score = 0
    reasons = []

    customer_region = order["customer_region"]
    customer_tier = order["customer_tier"]
    promised_window = calculate_promised_delivery_window(order)

    warehouse_utilization = float(
        warehouse_result.get("warehouse_utilization_rate", 0) or 0
    )

    recommended_warehouse_region = warehouse_result.get(
        "recommended_warehouse_region",
        ""
    )

    stockout_risk = warehouse_result.get("stockout_risk", "Low")
    selection_risk_level = warehouse_result.get("selection_risk_level", "Low")

    courier_delay_rate = float(
        courier_result.get("delay_rate", 0) or 0
    )

    courier_risk_level = courier_result.get("courier_risk_level", "Low")
    average_delivery_days = float(
        courier_result.get("average_delivery_days", 0) or 0
    )

    # 1. Warehouse congestion risk
    if warehouse_utilization > 90:
        score += 25
        reasons.append("warehouse utilization is above 90%, indicating congestion risk")
    elif warehouse_utilization >= 85:
        score += 15
        reasons.append("warehouse utilization is between 85% and 90%, indicating elevated load")
    else:
        reasons.append("warehouse utilization is within manageable range")

    # 2. Courier delay risk
    if courier_delay_rate > 20:
        score += 25
        reasons.append("courier delay rate is above 20%")
    elif courier_delay_rate >= 15:
        score += 15
        reasons.append("courier delay rate is elevated")
    elif courier_delay_rate >= 10:
        score += 8
        reasons.append("courier delay rate requires monitoring")
    else:
        reasons.append("courier delay rate is low")

    # 3. Delivery promise pressure
    if promised_window <= 1:
        score += 20
        reasons.append("delivery promise window is extremely tight")
    elif promised_window <= 2:
        score += 10
        reasons.append("delivery promise window is tight")
    else:
        reasons.append("delivery promise window is reasonable")

    # 4. Average courier delivery speed versus promised window
    if average_delivery_days > promised_window:
        score += 15
        reasons.append("courier average delivery speed may miss promised SLA")
    else:
        reasons.append("courier average delivery speed fits promised SLA")

    # 5. Region mismatch or national backup routing
    if recommended_warehouse_region == "National":
        score += 8
        reasons.append("order is routed through national backup warehouse")
    elif recommended_warehouse_region != customer_region:
        score += 15
        reasons.append("recommended warehouse is outside customer region")
    else:
        reasons.append("recommended warehouse matches customer region")

    # 6. Inventory risk
    if stockout_risk == "Critical":
        score += 20
        reasons.append("inventory is at critical stockout risk")
    elif stockout_risk == "High":
        score += 15
        reasons.append("inventory has high stockout risk")
    elif stockout_risk == "Medium":
        score += 8
        reasons.append("inventory requires monitoring")
    else:
        reasons.append("inventory risk is low")

    # 7. Warehouse selection risk
    if selection_risk_level == "Critical":
        score += 15
        reasons.append("warehouse selection has critical fulfillment risk")
    elif selection_risk_level == "High":
        score += 10
        reasons.append("warehouse selection has high fulfillment risk")
    elif selection_risk_level == "Medium":
        score += 5
        reasons.append("warehouse selection has medium fulfillment risk")
    else:
        reasons.append("warehouse selection risk is low")

    # 8. Courier selection risk
    if courier_risk_level == "Critical":
        score += 15
        reasons.append("courier selection has critical delivery risk")
    elif courier_risk_level == "High":
        score += 10
        reasons.append("courier selection has high delivery risk")
    elif courier_risk_level == "Medium":
        score += 5
        reasons.append("courier selection has medium delivery risk")
    else:
        reasons.append("courier selection risk is low")

    # 9. Customer tier impact
    if customer_tier == "Platinum":
        score += 20
        reasons.append("Platinum customer order increases service impact")
    elif customer_tier == "Gold":
        score += 10
        reasons.append("Gold customer order increases service impact")
    else:
        reasons.append("customer tier has standard service impact")

    # Keep score clean for dashboard display
    score = max(0, min(100, int(score)))

    risk_category = get_delay_risk_category(score)

    return {
        "order_id": order["order_id"],
        "delay_risk_score": score,
        "delay_risk_category": risk_category,
        "promised_delivery_window_days": promised_window,
        "delay_risk_explanation": "; ".join(reasons),
        "recommended_action": get_recommended_action(
            risk_category,
            customer_tier
        )
    }


def build_delay_risk_report(
    orders_df: pd.DataFrame,
    warehouses_df: pd.DataFrame,
    inventory_df: pd.DataFrame,
    couriers_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Build delay risk prediction report for all orders.

    This combines:
    - order details
    - recommended warehouse
    - recommended courier
    - delay risk score
    - delay risk category
    - recommended action
    """

    results = []

    for _, order_row in orders_df.iterrows():
        order = order_row.to_dict()

        warehouse_result = recommend_best_warehouse(
            order,
            warehouses_df,
            inventory_df
        )

        courier_result = recommend_best_courier(
            order,
            couriers_df
        )

        delay_result = predict_delay_risk(
            order,
            warehouse_result,
            courier_result
        )

        combined_result = {
            "order_id": order["order_id"],
            "customer_id": order["customer_id"],
            "customer_location": order["customer_location"],
            "customer_region": order["customer_region"],
            "customer_tier": order["customer_tier"],
            "product_sku": order["product_sku"],
            "product_name": order.get("product_name", ""),
            "quantity": int(order["quantity"]),
            "order_value": float(order["order_value"]),
            "order_date": order["order_date"],
            "promised_delivery_date": order["promised_delivery_date"],

            "recommended_warehouse_id": warehouse_result.get("recommended_warehouse_id"),
            "recommended_warehouse_name": warehouse_result.get("recommended_warehouse_name"),
            "recommended_warehouse_region": warehouse_result.get("recommended_warehouse_region"),
            "warehouse_utilization_rate": warehouse_result.get("warehouse_utilization_rate"),
            "selection_score": warehouse_result.get("selection_score"),
            "selection_risk_level": warehouse_result.get("selection_risk_level"),
            "stockout_risk": warehouse_result.get("stockout_risk"),
            "remaining_stock_after_order": warehouse_result.get("remaining_stock_after_order"),
            "warehouse_selection_reason": warehouse_result.get("selection_reason"),

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

        results.append(combined_result)

    return pd.DataFrame(results)
