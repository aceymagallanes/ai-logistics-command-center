import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import pandas as pd
import plotly.express as px
import streamlit as st

from app.services.data_loader import DataLoader
from app.services.export_service import run_full_export
from app.services.inventory_service import build_inventory_risk_report


BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "app" / "outputs"


st.set_page_config(
    page_title="AI Logistics Command Center",
    page_icon="🚚",
    layout="wide",
)


def inject_custom_css():
    st.markdown(
        """
        <style>
        .main {
            background-color: #F8FAFC;
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }

        .hero-card {
            background: linear-gradient(135deg, #0F172A 0%, #064E3B 100%);
            padding: 28px;
            border-radius: 22px;
            color: white;
            margin-bottom: 22px;
            box-shadow: 0px 18px 40px rgba(15, 23, 42, 0.16);
        }

        .hero-title {
            font-size: 34px;
            font-weight: 800;
            margin-bottom: 6px;
        }

        .hero-subtitle {
            font-size: 16px;
            color: #D1FAE5;
            margin-bottom: 0px;
        }

        .status-badge {
            display: inline-block;
            padding: 8px 14px;
            border-radius: 999px;
            font-size: 13px;
            font-weight: 700;
            background-color: #FEF3C7;
            color: #92400E;
            margin-top: 14px;
        }

        .metric-card {
            background-color: #FFFFFF;
            padding: 22px;
            border-radius: 18px;
            box-shadow: 0px 12px 28px rgba(15, 23, 42, 0.08);
            border: 1px solid #E2E8F0;
            min-height: 130px;
        }

        .metric-label {
            font-size: 13px;
            font-weight: 700;
            color: #64748B;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .metric-value {
            font-size: 30px;
            font-weight: 800;
            color: #0F172A;
            margin-top: 8px;
        }

        .metric-caption {
            font-size: 13px;
            color: #64748B;
            margin-top: 6px;
        }

        .section-title {
            font-size: 22px;
            font-weight: 800;
            color: #0F172A;
            margin-top: 20px;
            margin-bottom: 12px;
        }

        .insight-card {
            background-color: #FFFFFF;
            padding: 22px;
            border-radius: 18px;
            box-shadow: 0px 12px 28px rgba(15, 23, 42, 0.08);
            border-left: 6px solid #047857;
            margin-bottom: 16px;
        }

        .warning-card {
            background-color: #FFFBEB;
            padding: 20px;
            border-radius: 18px;
            border-left: 6px solid #F59E0B;
            margin-bottom: 16px;
        }

        .critical-card {
            background-color: #FEF2F2;
            padding: 20px;
            border-radius: 18px;
            border-left: 6px solid #DC2626;
            margin-bottom: 16px;
        }

        div[data-testid="stDataFrame"] {
            border-radius: 16px;
            overflow: hidden;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def peso(value):
    try:
        return f"₱{float(value):,.0f}"
    except Exception:
        return "₱0"


def pct(value):
    try:
        return f"{float(value):.2f}%"
    except Exception:
        return "0.00%"


def ensure_outputs_exist():
    required_files = [
        "logistics_kpis.csv",
        "order_risk_report.csv",
        "exception_type_summary.csv",
        "owning_team_summary.csv",
        "warehouse_performance_summary.csv",
        "courier_performance_summary.csv",
        "region_summary.csv",
        "executive_summary_input.json",
    ]

    missing_files = [
        filename for filename in required_files
        if not (OUTPUT_DIR / filename).exists()
    ]

    if missing_files:
        loader = DataLoader()
        run_full_export(
            loader.load_orders(),
            loader.load_warehouses(),
            loader.load_inventory(),
            loader.load_couriers(),
        )


@st.cache_data
def load_dashboard_data():
    ensure_outputs_exist()

    data = {
        "kpis": pd.read_csv(OUTPUT_DIR / "logistics_kpis.csv"),
        "orders": pd.read_csv(OUTPUT_DIR / "order_risk_report.csv"),
        "exception_summary": pd.read_csv(OUTPUT_DIR / "exception_type_summary.csv"),
        "owning_team_summary": pd.read_csv(OUTPUT_DIR / "owning_team_summary.csv"),
        "warehouse_summary": pd.read_csv(OUTPUT_DIR / "warehouse_performance_summary.csv"),
        "courier_summary": pd.read_csv(OUTPUT_DIR / "courier_performance_summary.csv"),
        "region_summary": pd.read_csv(OUTPUT_DIR / "region_summary.csv"),
    }

    with open(OUTPUT_DIR / "executive_summary_input.json", "r", encoding="utf-8") as file:
        data["executive_json"] = json.load(file)

    loader = DataLoader()
    inventory = loader.load_inventory()
    data["inventory_risk"] = build_inventory_risk_report(inventory)

    return data


def metric_card(label, value, caption=""):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-caption">{caption}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def hero_section(kpis):
    overall_status = kpis.get("overall_status", "Unknown")
    total_orders = kpis.get("total_orders", 0)

    st.markdown(
        f"""
        <div class="hero-card">
            <div class="hero-title">AI Warehouse & Logistics Command Center</div>
            <div class="hero-subtitle">
                Executive logistics control tower for order risk, warehouse utilization,
                courier performance, inventory exposure, and revenue-at-risk monitoring.
            </div>
            <div class="status-badge">Overall Status: {overall_status} | Orders Analyzed: {total_orders}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def executive_overview(data):
    kpis = data["kpis"].iloc[0].to_dict()
    orders = data["orders"]
    exception_summary = data["exception_summary"]
    region_summary = data["region_summary"]

    hero_section(kpis)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        metric_card(
            "Total Orders",
            f"{int(kpis.get('total_orders', 0)):,}",
            "Orders analyzed in the current simulation",
        )

    with col2:
        metric_card(
            "Active Exceptions",
            f"{int(kpis.get('active_exceptions', 0)):,}",
            f"{pct(kpis.get('active_exception_rate', 0))} exception rate",
        )

    with col3:
        metric_card(
            "Revenue at Risk",
            peso(kpis.get("revenue_at_risk", 0)),
            "High and Critical delay-risk orders",
        )

    with col4:
        metric_card(
            "OTIF Estimate",
            pct(kpis.get("otif_estimate", 0)),
            "Estimated on-time-in-full performance",
        )

    st.markdown('<div class="section-title">Executive Risk View</div>', unsafe_allow_html=True)

    col5, col6, col7 = st.columns(3)

    with col5:
        fig = px.pie(
            orders,
            names="delay_risk_category",
            title="Orders by Delay Risk Category",
            hole=0.45,
        )
        fig.update_layout(height=380)
        st.plotly_chart(fig, use_container_width=True)

    with col6:
        fig = px.bar(
            exception_summary,
            x="exception_type",
            y="order_count",
            title="Exception Type Breakdown",
            text="order_count",
        )
        fig.update_layout(height=380, xaxis_title="", yaxis_title="Orders")
        st.plotly_chart(fig, use_container_width=True)

    with col7:
        fig = px.bar(
            region_summary,
            x="customer_region",
            y="active_exception_rate",
            title="Active Exception Rate by Region",
            text="active_exception_rate",
        )
        fig.update_layout(height=380, xaxis_title="", yaxis_title="Exception Rate %")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-title">Management Insight</div>', unsafe_allow_html=True)

    top_exception = exception_summary.sort_values("order_count", ascending=False).iloc[0]
    top_region = region_summary.sort_values("active_exception_rate", ascending=False).iloc[0]

    st.markdown(
        f"""
        <div class="insight-card">
            <b>Main operational signal:</b> The highest exception category is
            <b>{top_exception["exception_type"]}</b> with
            <b>{int(top_exception["order_count"])}</b> affected orders.
            The most exposed region is <b>{top_region["customer_region"]}</b>
            with an active exception rate of <b>{top_region["active_exception_rate"]:.2f}%</b>.
        </div>
        """,
        unsafe_allow_html=True,
    )


def order_risk_monitor(data):
    orders = data["orders"]

    st.markdown('<div class="section-title">Order Risk Monitor</div>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    risk_filter = col1.multiselect(
        "Delay Risk Category",
        sorted(orders["delay_risk_category"].dropna().unique()),
        default=sorted(orders["delay_risk_category"].dropna().unique()),
    )

    priority_filter = col2.multiselect(
        "Exception Priority",
        sorted(orders["exception_priority"].dropna().unique()),
        default=sorted(orders["exception_priority"].dropna().unique()),
    )

    region_filter = col3.multiselect(
        "Customer Region",
        sorted(orders["customer_region"].dropna().unique()),
        default=sorted(orders["customer_region"].dropna().unique()),
    )

    tier_filter = col4.multiselect(
        "Customer Tier",
        sorted(orders["customer_tier"].dropna().unique()),
        default=sorted(orders["customer_tier"].dropna().unique()),
    )

    filtered = orders[
        (orders["delay_risk_category"].isin(risk_filter)) &
        (orders["exception_priority"].isin(priority_filter)) &
        (orders["customer_region"].isin(region_filter)) &
        (orders["customer_tier"].isin(tier_filter))
    ].copy()

    st.markdown(
        f"""
        <div class="warning-card">
            Showing <b>{len(filtered):,}</b> orders after filters.
            Use this view to prioritize P1/P2 exceptions, high-value customers, and SLA-risk orders.
        </div>
        """,
        unsafe_allow_html=True,
    )

    display_columns = [
        "order_id",
        "customer_region",
        "customer_tier",
        "product_name",
        "quantity",
        "order_value",
        "delay_risk_score",
        "delay_risk_category",
        "exception_type",
        "exception_priority",
        "owning_team",
        "recommended_warehouse_name",
        "recommended_courier_name",
        "recommended_action",
    ]

    st.dataframe(
        filtered[display_columns].sort_values(
            by=["exception_priority", "delay_risk_score"],
            ascending=[True, False],
        ),
        use_container_width=True,
        height=560,
    )


def warehouse_performance(data):
    warehouse_summary = data["warehouse_summary"]

    st.markdown('<div class="section-title">Warehouse Performance</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(
            warehouse_summary,
            x="recommended_warehouse_name",
            y="orders_routed",
            title="Orders Routed by Warehouse",
            text="orders_routed",
        )
        fig.update_layout(height=430, xaxis_title="", yaxis_title="Orders")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.scatter(
            warehouse_summary,
            x="average_warehouse_utilization",
            y="high_risk_orders",
            size="revenue_total",
            color="recommended_warehouse_region",
            hover_name="recommended_warehouse_name",
            title="Warehouse Utilization vs High-Risk Orders",
        )
        fig.update_layout(height=430, xaxis_title="Avg Utilization %", yaxis_title="High-Risk Orders")
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(warehouse_summary, use_container_width=True)


def courier_performance(data):
    courier_summary = data["courier_summary"]

    st.markdown('<div class="section-title">Courier Performance</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(
            courier_summary,
            x="recommended_courier_name",
            y="high_risk_orders",
            title="High-Risk Orders by Courier",
            text="high_risk_orders",
        )
        fig.update_layout(height=430, xaxis_title="", yaxis_title="High-Risk Orders")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.scatter(
            courier_summary,
            x="average_delay_rate",
            y="average_delay_risk_score",
            size="orders_assigned",
            color="recommended_courier_region",
            hover_name="recommended_courier_name",
            title="Courier Delay Rate vs Risk Score",
        )
        fig.update_layout(height=430, xaxis_title="Average Delay Rate %", yaxis_title="Avg Risk Score")
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(courier_summary, use_container_width=True)


def inventory_risk(data):
    inventory = data["inventory_risk"]

    st.markdown('<div class="section-title">Inventory Risk</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    risk_counts = inventory["stockout_risk"].value_counts().reset_index()
    risk_counts.columns = ["stockout_risk", "count"]

    with col1:
        fig = px.bar(
            risk_counts,
            x="stockout_risk",
            y="count",
            title="Inventory Stockout Risk Count",
            text="count",
        )
        fig.update_layout(height=400, xaxis_title="", yaxis_title="SKU-Warehouse Records")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        status_counts = inventory["replenishment_status"].value_counts().reset_index()
        status_counts.columns = ["replenishment_status", "count"]

        fig = px.pie(
            status_counts,
            names="replenishment_status",
            values="count",
            title="Replenishment Status",
            hole=0.45,
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        inventory.sort_values(
            by=["stockout_risk", "available_quantity"],
            ascending=[True, True],
        ),
        use_container_width=True,
        height=520,
    )


def ai_executive_brief(data):
    executive_json = data["executive_json"]
    kpis = executive_json.get("executive_kpis", {})
    top_risks = executive_json.get("top_risks", [])
    recommended_actions = executive_json.get("recommended_actions", [])
    top_priority_orders = executive_json.get("top_priority_orders", [])

    st.markdown('<div class="section-title">AI Executive Brief Input</div>', unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="critical-card">
            <b>Overall Status:</b> {executive_json.get("overall_status", "Unknown")}<br>
            <b>Total Orders:</b> {kpis.get("total_orders", 0):,}<br>
            <b>Active Exceptions:</b> {kpis.get("active_exceptions", 0):,}<br>
            <b>Revenue at Risk:</b> {peso(kpis.get("revenue_at_risk", 0))}<br>
            <b>P1/P2 Priority Exceptions:</b> {kpis.get("p1_p2_priority_exceptions", 0):,}
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Top Risks")
        for risk in top_risks:
            st.markdown(
                f"""
                <div class="insight-card">
                    <b>{risk.get("risk_type")}</b><br>
                    Affected Orders: {risk.get("affected_orders")}<br>
                    Revenue Impact: {peso(risk.get("revenue_impact", 0))}<br>
                    Avg Risk Score: {risk.get("average_delay_risk_score")}
                </div>
                """,
                unsafe_allow_html=True,
            )

    with col2:
        st.subheader("Recommended Actions")
        for action in recommended_actions:
            st.markdown(f"- {action}")

    st.subheader("Top Priority Orders")
    st.dataframe(pd.DataFrame(top_priority_orders), use_container_width=True)

    with st.expander("View Raw Executive JSON for Claude / n8n"):
        st.json(executive_json)


def main():
    inject_custom_css()

    data = load_dashboard_data()

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        [
            "Executive Overview",
            "Order Risk Monitor",
            "Warehouse Performance",
            "Courier Performance",
            "Inventory Risk",
            "AI Executive Brief",
        ]
    )

    with tab1:
        executive_overview(data)

    with tab2:
        order_risk_monitor(data)

    with tab3:
        warehouse_performance(data)

    with tab4:
        courier_performance(data)

    with tab5:
        inventory_risk(data)

    with tab6:
        ai_executive_brief(data)


if __name__ == "__main__":
    main()
