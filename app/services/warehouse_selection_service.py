import pandas as pd

from app.services.inventory_service import determine_stockout_risk


def get_selection_risk_level(selection_score: int) -> str:
    """
    Convert warehouse selection score into a business risk level.

    Higher score = better warehouse choice.
    Lower score = riskier warehouse choice.
    """

    if selection_score >= 80:
        return "Low"
    elif selection_score >= 60:
        return "Medium"
    elif selection_score >= 40:
        return "High"
    else:
        return "Critical"


def score_warehouse_candidate(order: dict, candidate: pd.Series) -> dict:
    """
    Score one warehouse candidate for one order.

    The scoring logic combines:
    - region match
    - inventory availability
    - safety stock protection
    - warehouse utilization
    - warehouse load
    - stockout risk
    """

    score = 0
    reasons = []

    customer_region = order["customer_region"]
    quantity = int(order["quantity"])

    warehouse_region = candidate["region"]
    utilization_rate = float(candidate["utilization_rate"])
    current_daily_load = float(candidate["current_daily_load"])
    max_daily_capacity = float(candidate["max_daily_capacity"])
    available_quantity = int(candidate["available_quantity"])
    safety_stock_level = int(candidate["safety_stock_level"])
    reorder_point = int(candidate["reorder_point"])

    remaining_stock = available_quantity - quantity

    # 1. Region match scoring
    if warehouse_region == customer_region:
        score += 40
        reasons.append("same customer region")
    elif warehouse_region == "National":
        score += 20
        reasons.append("national backup warehouse")
    else:
        score -= 10
        reasons.append("different region")

    # 2. Inventory and safety stock scoring
    if remaining_stock > safety_stock_level:
        score += 30
        reasons.append("stock remains above safety stock after fulfillment")
    elif remaining_stock == safety_stock_level:
        score += 10
        reasons.append("stock reaches safety stock after fulfillment")
    else:
        score -= 20
        reasons.append("fulfillment may breach safety stock")

    # 3. Warehouse utilization scoring
    if utilization_rate < 85:
        score += 20
        reasons.append("warehouse utilization below 85%")
    elif utilization_rate <= 90:
        score += 5
        reasons.append("warehouse utilization is elevated")
    else:
        score -= 30
        reasons.append("warehouse congestion risk above 90%")

    # 4. Current load scoring
    load_ratio = current_daily_load / max_daily_capacity

    if load_ratio < 0.80:
        score += 10
        reasons.append("daily load below 80% capacity")
    elif load_ratio <= 0.90:
        score += 0
        reasons.append("daily load is manageable")
    else:
        score -= 10
        reasons.append("daily load is close to capacity")

    # 5. Stockout risk adjustment
    stockout_risk = determine_stockout_risk(
        available_quantity,
        safety_stock_level,
        reorder_point
    )

    if stockout_risk == "Low":
        score += 10
        reasons.append("low stockout risk")
    elif stockout_risk == "Medium":
        score += 0
        reasons.append("medium stockout risk")
    elif stockout_risk == "High":
        score -= 10
        reasons.append("high stockout risk")
    else:
        score -= 20
        reasons.append("critical stockout risk")

    # Keep score between 0 and 100 for clean dashboard display
    score = max(0, min(100, score))

    return {
        "warehouse_id": candidate["warehouse_id"],
        "warehouse_name": candidate["warehouse_name"],
        "warehouse_region": warehouse_region,
        "city": candidate["city"],
        "selection_score": int(score),
        "selection_risk_level": get_selection_risk_level(score),
        "warehouse_utilization_rate": utilization_rate,
        "available_quantity": available_quantity,
        "remaining_stock_after_order": int(remaining_stock),
        "stockout_risk": stockout_risk,
        "selection_reason": "; ".join(reasons)
    }


def recommend_best_warehouse(
    order: dict,
    warehouses_df: pd.DataFrame,
    inventory_df: pd.DataFrame
) -> dict:
    """
    Recommend the best warehouse for one order.

    Args:
        order: Order dictionary.
        warehouses_df: Warehouse data.
        inventory_df: Inventory data.

    Returns:
        Dictionary containing recommended warehouse and reason.
    """

    product_sku = order["product_sku"]
    quantity = int(order["quantity"])

    sku_inventory = inventory_df[
        inventory_df["product_sku"] == product_sku
    ].copy()

    if sku_inventory.empty:
        return {
            "order_id": order["order_id"],
            "product_sku": product_sku,
            "recommended_warehouse_id": None,
            "recommended_warehouse_name": None,
            "selection_score": 0,
            "selection_risk_level": "Critical",
            "stockout_risk": "Critical",
            "selection_reason": "SKU not found in inventory.",
            "can_fulfill": False
        }

    candidate_df = sku_inventory.merge(
        warehouses_df,
        on="warehouse_id",
        how="left"
    )

    candidate_df = candidate_df[
        candidate_df["available_quantity"] >= quantity
    ].copy()

    if candidate_df.empty:
        return {
            "order_id": order["order_id"],
            "product_sku": product_sku,
            "recommended_warehouse_id": None,
            "recommended_warehouse_name": None,
            "selection_score": 0,
            "selection_risk_level": "Critical",
            "stockout_risk": "Critical",
            "selection_reason": "No warehouse has enough available stock.",
            "can_fulfill": False
        }

    scored_candidates = [
        score_warehouse_candidate(order, candidate)
        for _, candidate in candidate_df.iterrows()
    ]

    scored_candidates = sorted(
        scored_candidates,
        key=lambda item: item["selection_score"],
        reverse=True
    )

    best = scored_candidates[0]

    return {
        "order_id": order["order_id"],
        "product_sku": product_sku,
        "customer_region": order["customer_region"],
        "recommended_warehouse_id": best["warehouse_id"],
        "recommended_warehouse_name": best["warehouse_name"],
        "recommended_warehouse_region": best["warehouse_region"],
        "recommended_warehouse_city": best["city"],
        "selection_score": best["selection_score"],
        "selection_risk_level": best["selection_risk_level"],
        "warehouse_utilization_rate": best["warehouse_utilization_rate"],
        "available_quantity": best["available_quantity"],
        "remaining_stock_after_order": best["remaining_stock_after_order"],
        "stockout_risk": best["stockout_risk"],
        "selection_reason": best["selection_reason"],
        "can_fulfill": True
    }


def build_warehouse_recommendation_report(
    orders_df: pd.DataFrame,
    warehouses_df: pd.DataFrame,
    inventory_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Build warehouse recommendations for all orders.

    This report will later feed the API and Streamlit dashboard.
    """

    results = []

    for _, order_row in orders_df.iterrows():
        order = order_row.to_dict()
        recommendation = recommend_best_warehouse(
            order,
            warehouses_df,
            inventory_df
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
            **recommendation
        }

        results.append(combined_result)

    return pd.DataFrame(results)
