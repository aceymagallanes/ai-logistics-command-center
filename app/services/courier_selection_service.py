import pandas as pd
from datetime import datetime


def get_courier_risk_level(score: int) -> str:
    """
    Convert courier score into a business risk level.

    Higher score = better courier choice.
    Lower score = higher delivery risk.
    """

    if score >= 80:
        return "Low"
    elif score >= 60:
        return "Medium"
    elif score >= 40:
        return "High"
    else:
        return "Critical"


def calculate_promised_delivery_window(order: dict) -> int:
    """
    Calculate number of days between order date and promised delivery date.
    """

    order_date = datetime.strptime(str(order["order_date"]), "%Y-%m-%d")
    promised_delivery_date = datetime.strptime(
        str(order["promised_delivery_date"]),
        "%Y-%m-%d"
    )

    return max((promised_delivery_date - order_date).days, 1)


def score_courier_candidate(order: dict, courier: pd.Series) -> dict:
    """
    Score one courier candidate for one customer order.

    Scoring considers:
    - region match
    - on-time performance
    - delay rate
    - average delivery speed
    - cost per kilometer
    - promised delivery window
    """

    score = 0
    reasons = []

    customer_region = order["customer_region"]
    promised_window = calculate_promised_delivery_window(order)

    courier_region = courier["region"]
    on_time_rate = float(courier["on_time_rate"])
    delay_rate = float(courier["delay_rate"])
    average_delivery_days = float(courier["average_delivery_days"])
    cost_per_km = float(courier["cost_per_km"])

    # 1. Regional coverage scoring
    if courier_region == customer_region:
        score += 40
        reasons.append("courier serves the customer region directly")
    elif courier_region == "National":
        score += 25
        reasons.append("national courier can cover the customer region")
    else:
        score -= 20
        reasons.append("courier is outside the customer region")

    # 2. On-time performance scoring
    if on_time_rate >= 95:
        score += 25
        reasons.append("excellent on-time performance")
    elif on_time_rate >= 90:
        score += 20
        reasons.append("strong on-time performance")
    elif on_time_rate >= 85:
        score += 10
        reasons.append("acceptable on-time performance")
    elif on_time_rate >= 80:
        score += 5
        reasons.append("moderate on-time performance")
    else:
        score -= 15
        reasons.append("weak on-time performance")

    # 3. Delay rate scoring
    if delay_rate <= 8:
        score += 20
        reasons.append("very low delay rate")
    elif delay_rate <= 15:
        score += 10
        reasons.append("manageable delay rate")
    elif delay_rate <= 20:
        score += 0
        reasons.append("elevated delay rate")
    else:
        score -= 20
        reasons.append("high courier delay rate")

    # 4. Delivery speed scoring
    if average_delivery_days <= promised_window:
        score += 15
        reasons.append("average delivery speed fits SLA window")
    else:
        score -= 15
        reasons.append("average delivery speed may miss SLA window")

    # 5. Cost scoring
    # This does not dominate the decision. We prioritize service reliability.
    if cost_per_km <= 18:
        score += 8
        reasons.append("low delivery cost")
    elif cost_per_km <= 25:
        score += 4
        reasons.append("moderate delivery cost")
    else:
        score -= 3
        reasons.append("premium delivery cost")

    # 6. Tight SLA adjustment
    if promised_window <= 1 and average_delivery_days <= 1:
        score += 10
        reasons.append("suitable for same-day or next-day delivery")
    elif promised_window <= 1 and average_delivery_days > 1:
        score -= 20
        reasons.append("not ideal for tight delivery promise")

    # Keep score between 0 and 100 for dashboard use
    score = max(0, min(100, score))

    return {
        "courier_id": courier["courier_id"],
        "courier_name": courier["courier_name"],
        "courier_region": courier_region,
        "courier_score": int(score),
        "courier_risk_level": get_courier_risk_level(score),
        "average_delivery_days": average_delivery_days,
        "on_time_rate": on_time_rate,
        "delay_rate": delay_rate,
        "cost_per_km": cost_per_km,
        "promised_delivery_window_days": promised_window,
        "courier_selection_reason": "; ".join(reasons)
    }


def recommend_best_courier(order: dict, couriers_df: pd.DataFrame) -> dict:
    """
    Recommend the best courier for a single order.

    The system first considers couriers that serve the customer region
    or national couriers. If none are found, it scores all couriers.
    """

    customer_region = order["customer_region"]

    candidate_df = couriers_df[
        (couriers_df["region"] == customer_region) |
        (couriers_df["region"] == "National")
    ].copy()

    if candidate_df.empty:
        candidate_df = couriers_df.copy()

    scored_candidates = [
        score_courier_candidate(order, courier)
        for _, courier in candidate_df.iterrows()
    ]

    scored_candidates = sorted(
        scored_candidates,
        key=lambda item: item["courier_score"],
        reverse=True
    )

    best = scored_candidates[0]

    return {
        "order_id": order["order_id"],
        "customer_region": customer_region,
        "recommended_courier_id": best["courier_id"],
        "recommended_courier_name": best["courier_name"],
        "recommended_courier_region": best["courier_region"],
        "courier_score": best["courier_score"],
        "courier_risk_level": best["courier_risk_level"],
        "average_delivery_days": best["average_delivery_days"],
        "on_time_rate": best["on_time_rate"],
        "delay_rate": best["delay_rate"],
        "cost_per_km": best["cost_per_km"],
        "promised_delivery_window_days": best["promised_delivery_window_days"],
        "courier_selection_reason": best["courier_selection_reason"]
    }


def build_courier_recommendation_report(
    orders_df: pd.DataFrame,
    couriers_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Build courier recommendations for all orders.

    This report will later feed:
    - FastAPI
    - Streamlit dashboard
    - delay prediction engine
    - executive logistics brief
    """

    results = []

    for _, order_row in orders_df.iterrows():
        order = order_row.to_dict()
        recommendation = recommend_best_courier(order, couriers_df)

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
            **recommendation
        }

        results.append(combined_result)

    return pd.DataFrame(results)
