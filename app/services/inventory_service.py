import pandas as pd


def determine_stockout_risk(
    available_quantity: int,
    safety_stock_level: int,
    reorder_point: int
) -> str:
    """
    Determine inventory risk level based on available stock.

    Business meaning:
    - Critical: Stock is already at or below safety stock.
    - High: Stock is below reorder point.
    - Medium: Stock is getting close to reorder point.
    - Low: Stock is healthy.
    """

    if available_quantity <= safety_stock_level:
        return "Critical"
    elif available_quantity <= reorder_point:
        return "High"
    elif available_quantity <= reorder_point * 1.25:
        return "Medium"
    else:
        return "Low"


def get_available_warehouses_for_sku(
    product_sku: str,
    quantity: int,
    inventory_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Return warehouses that have enough stock for the requested SKU and quantity.
    """

    sku_inventory = inventory_df[
        inventory_df["product_sku"] == product_sku
    ].copy()

    available_warehouses = sku_inventory[
        sku_inventory["available_quantity"] >= quantity
    ].copy()

    return available_warehouses


def check_inventory_for_order(
    order: dict,
    inventory_df: pd.DataFrame
) -> dict:
    """
    Check inventory availability for a single order.

    Args:
        order: A dictionary containing order details.
        inventory_df: Inventory DataFrame.

    Returns:
        Dictionary with inventory status and risk information.
    """

    product_sku = order["product_sku"]
    quantity = int(order["quantity"])

    sku_inventory = inventory_df[
        inventory_df["product_sku"] == product_sku
    ].copy()

    if sku_inventory.empty:
        return {
            "product_sku": product_sku,
            "requested_quantity": quantity,
            "inventory_available": False,
            "available_warehouse_count": 0,
            "lowest_stockout_risk": "Critical",
            "message": "SKU not found in inventory."
        }

    available_warehouses = sku_inventory[
        sku_inventory["available_quantity"] >= quantity
    ].copy()

    if available_warehouses.empty:
        return {
            "product_sku": product_sku,
            "requested_quantity": quantity,
            "inventory_available": False,
            "available_warehouse_count": 0,
            "lowest_stockout_risk": "Critical",
            "message": "No warehouse has enough available stock."
        }

    available_warehouses["stockout_risk"] = available_warehouses.apply(
        lambda row: determine_stockout_risk(
            int(row["available_quantity"]),
            int(row["safety_stock_level"]),
            int(row["reorder_point"])
        ),
        axis=1
    )

    risk_priority = {
        "Low": 1,
        "Medium": 2,
        "High": 3,
        "Critical": 4
    }

    lowest_risk_row = available_warehouses.sort_values(
        by="stockout_risk",
        key=lambda col: col.map(risk_priority)
    ).iloc[0]

    return {
        "product_sku": product_sku,
        "requested_quantity": quantity,
        "inventory_available": True,
        "available_warehouse_count": int(len(available_warehouses)),
        "best_inventory_warehouse_id": lowest_risk_row["warehouse_id"],
        "best_inventory_available_quantity": int(lowest_risk_row["available_quantity"]),
        "lowest_stockout_risk": lowest_risk_row["stockout_risk"],
        "message": "Inventory available for fulfillment."
    }


def build_inventory_risk_report(inventory_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a full inventory risk report for dashboard use.
    """

    report = inventory_df.copy()

    report["stockout_risk"] = report.apply(
        lambda row: determine_stockout_risk(
            int(row["available_quantity"]),
            int(row["safety_stock_level"]),
            int(row["reorder_point"])
        ),
        axis=1
    )

    report["replenishment_status"] = report["stockout_risk"].map(
        {
            "Critical": "Critical Replenishment Needed",
            "High": "Reorder Needed",
            "Medium": "Monitor Closely",
            "Low": "Healthy"
        }
    )

    return report
