import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "app" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

WAREHOUSES = [
    ["WH-001", "Metro Manila Fulfillment Center", "Taguig", "Metro Manila", 5000, 4200, 84],
    ["WH-002", "Luzon North Distribution Hub", "Clark", "Luzon", 3500, 3150, 90],
    ["WH-003", "Visayas Fulfillment Center", "Cebu", "Visayas", 3000, 2520, 84],
    ["WH-004", "Mindanao Distribution Hub", "Davao", "Mindanao", 2500, 2300, 92],
    ["WH-005", "Overflow Warehouse South", "Laguna", "Luzon", 2000, 900, 45],
    ["WH-006", "National Backup Fulfillment Center", "Batangas", "National", 1800, 1080, 60],
]

COURIERS = [
    ["CR-001", "ExpressGo", "Metro Manila", 1.2, 94, 6, 18],
    ["CR-002", "IslandShip", "Visayas", 2.4, 86, 14, 24],
    ["CR-003", "MindanaoMove", "Mindanao", 3.1, 78, 22, 28],
    ["CR-004", "LuzonRapid", "Luzon", 2.0, 88, 12, 22],
    ["CR-005", "BudgetHaul", "National", 4.2, 72, 28, 15],
    ["CR-006", "PremiumSameDay", "Metro Manila", 0.8, 96, 4, 35],
    ["CR-007", "ProvincialLink", "Luzon", 2.8, 81, 19, 20],
    ["CR-008", "InterIsland Priority", "National", 3.5, 80, 20, 30],
]

PRODUCTS = [
    ("SKU-LAPTOP-001", "Laptop Pro 14", 48000),
    ("SKU-PHONE-002", "Smartphone X", 28000),
    ("SKU-TABLET-003", "Tablet Air", 22000),
    ("SKU-HEADSET-004", "Wireless Headset", 4500),
    ("SKU-MONITOR-005", "27-inch Monitor", 14500),
    ("SKU-CAMERA-006", "Action Camera", 39000),
    ("SKU-KEYBOARD-007", "Mechanical Keyboard", 6200),
    ("SKU-MOUSE-008", "Gaming Mouse", 3500),
    ("SKU-PRINTER-009", "Office Printer", 17000),
    ("SKU-ROUTER-010", "WiFi Router", 8500),
    ("SKU-SPEAKER-011", "Bluetooth Speaker", 7200),
    ("SKU-SSD-012", "External SSD", 9800),
]

CUSTOMER_LOCATIONS = [
    ("Quezon City", "Metro Manila"),
    ("Makati City", "Metro Manila"),
    ("Pasig City", "Metro Manila"),
    ("Taguig City", "Metro Manila"),
    ("Manila", "Metro Manila"),
    ("Cebu City", "Visayas"),
    ("Iloilo City", "Visayas"),
    ("Bacolod City", "Visayas"),
    ("Tacloban City", "Visayas"),
    ("Davao City", "Mindanao"),
    ("Cagayan de Oro", "Mindanao"),
    ("General Santos", "Mindanao"),
    ("Zamboanga City", "Mindanao"),
    ("Baguio City", "Luzon"),
    ("Clark", "Luzon"),
    ("Batangas City", "Luzon"),
    ("Tagaytay", "Luzon"),
    ("San Fernando", "Luzon"),
]

CUSTOMER_TIERS = ["Bronze", "Silver", "Gold", "Platinum"]


def write_csv(filename, rows, headers):
    path = DATA_DIR / filename
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"Created {filename} with {len(rows)} records")


def generate_inventory():
    rows = []

    for warehouse in WAREHOUSES:
        warehouse_id = warehouse[0]

        for sku, product_name, base_price in PRODUCTS:
            safety_stock = random.choice([10, 15, 20, 25, 30, 40, 50, 80, 100])
            reorder_point = safety_stock + random.choice([10, 15, 20, 30, 50])

            scenario = random.choices(
                ["healthy", "near_reorder", "critical"],
                weights=[0.60, 0.25, 0.15],
                k=1
            )[0]

            if scenario == "healthy":
                available_quantity = random.randint(reorder_point + 10, reorder_point + 180)
            elif scenario == "near_reorder":
                available_quantity = random.randint(safety_stock + 1, reorder_point)
            else:
                available_quantity = random.randint(0, safety_stock)

            rows.append([
                warehouse_id,
                sku,
                product_name,
                available_quantity,
                safety_stock,
                reorder_point
            ])

    return rows


def generate_orders(total_orders=500):
    rows = []
    base_date = datetime(2026, 6, 29)

    for i in range(1, total_orders + 1):
        location, region = random.choice(CUSTOMER_LOCATIONS)
        sku, product_name, base_price = random.choice(PRODUCTS)

        quantity = random.choices(
            [1, 2, 3, 4, 5],
            weights=[0.55, 0.25, 0.12, 0.05, 0.03],
            k=1
        )[0]

        customer_tier = random.choices(
            CUSTOMER_TIERS,
            weights=[0.25, 0.35, 0.25, 0.15],
            k=1
        )[0]

        order_date = base_date + timedelta(days=random.randint(0, 7))

        promised_days = random.choices(
            [1, 2, 3, 4, 5],
            weights=[0.20, 0.30, 0.25, 0.15, 0.10],
            k=1
        )[0]

        promised_delivery_date = order_date + timedelta(days=promised_days)
        order_value = int(base_price * quantity * random.uniform(0.95, 1.08))

        rows.append([
            f"ORD-{1000 + i}",
            f"CUST-{i:04d}",
            location,
            region,
            sku,
            product_name,
            quantity,
            order_value,
            customer_tier,
            order_date.strftime("%Y-%m-%d"),
            promised_delivery_date.strftime("%Y-%m-%d")
        ])

    return rows


def generate_delivery_history(orders):
    rows = []

    for i, order in enumerate(orders, start=1):
        order_id = order[0]
        customer_region = order[3]
        order_date = datetime.strptime(order[9], "%Y-%m-%d")
        promised_delivery_date = datetime.strptime(order[10], "%Y-%m-%d")

        possible_warehouses = [w for w in WAREHOUSES if w[3] == customer_region]
        if not possible_warehouses:
            possible_warehouses = [w for w in WAREHOUSES if w[3] in ["National", "Luzon"]]

        warehouse = random.choice(possible_warehouses)

        possible_couriers = [c for c in COURIERS if c[2] == customer_region or c[2] == "National"]
        courier = random.choice(possible_couriers)

        promised_days = max((promised_delivery_date - order_date).days, 1)

        delay_probability = courier[5] / 100

        if warehouse[6] >= 90:
            delay_probability += 0.15

        was_late = random.random() < delay_probability

        if was_late:
            actual_days = promised_days + random.randint(1, 3)
            status = "Late"
        else:
            actual_days = max(1, promised_days - random.choice([0, 0, 1]))
            status = "On Time"

        return_flag = "Yes" if random.random() < 0.08 else "No"
        damage_flag = "Yes" if random.random() < 0.04 else "No"

        rows.append([
            f"DEL-{i:04d}",
            order_id,
            warehouse[0],
            courier[0],
            actual_days,
            promised_days,
            status,
            return_flag,
            damage_flag
        ])

    return rows


def main():
    inventory = generate_inventory()
    orders = generate_orders(500)
    delivery_history = generate_delivery_history(orders)

    write_csv(
        "warehouses.csv",
        WAREHOUSES,
        [
            "warehouse_id",
            "warehouse_name",
            "city",
            "region",
            "max_daily_capacity",
            "current_daily_load",
            "utilization_rate"
        ]
    )

    write_csv(
        "couriers.csv",
        COURIERS,
        [
            "courier_id",
            "courier_name",
            "region",
            "average_delivery_days",
            "on_time_rate",
            "delay_rate",
            "cost_per_km"
        ]
    )

    write_csv(
        "inventory.csv",
        inventory,
        [
            "warehouse_id",
            "product_sku",
            "product_name",
            "available_quantity",
            "safety_stock_level",
            "reorder_point"
        ]
    )

    write_csv(
        "orders.csv",
        orders,
        [
            "order_id",
            "customer_id",
            "customer_location",
            "customer_region",
            "product_sku",
            "product_name",
            "quantity",
            "order_value",
            "customer_tier",
            "order_date",
            "promised_delivery_date"
        ]
    )

    write_csv(
        "delivery_history.csv",
        delivery_history,
        [
            "delivery_id",
            "order_id",
            "warehouse_id",
            "courier_id",
            "actual_delivery_days",
            "promised_delivery_days",
            "status",
            "return_flag",
            "damage_flag"
        ]
    )

    print("")
    print("Mock logistics data generation complete.")
    print("Main transactional dataset: 500 orders")


if __name__ == "__main__":
    main()
