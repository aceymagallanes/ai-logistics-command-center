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



PLOTLY_CONFIG = {
    "displaylogo": False,
    "displayModeBar": False,
    "responsive": True,
}

REGION_COLORS = {
    "National": "#0F766E",
    "Luzon": "#2563EB",
    "Visayas": "#F59E0B",
    "Metro Manila": "#EC4899",
    "Mindanao": "#8B5CF6",
}

RISK_COLORS = {
    "Low": "#10B981",
    "Medium": "#F59E0B",
    "High": "#F97316",
    "Critical": "#DC2626",
}



EXCEPTION_COLORS = {
    "No Immediate Exception": "#0F766E",
    "Courier Delay": "#F97316",
    "Stockout Risk": "#F59E0B",
    "Manual Review Required": "#2563EB",
    "Warehouse Congestion": "#8B5CF6",
    "Inventory Shortage": "#DC2626",
    "SLA Breach Risk": "#EF4444",
    "High Value Customer Risk": "#EC4899",
}

def apply_chart_style(fig, height=420):
    """
    Apply a consistent executive dashboard style to Plotly charts.
    """

    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=20, r=20, t=75, b=95),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(
            family="Arial, sans-serif",
            size=13,
            color="#0F172A",
        ),
        title=dict(
            font=dict(size=20, color="#0F172A"),
            x=0.01,
            xanchor="left",
        ),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.22,
            xanchor="left",
            x=0,
            title_text="",
            font=dict(size=12),
        ),
    )

    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        showline=True,
        linecolor="#CBD5E1",
        tickfont=dict(size=12, color="#64748B"),
        title_font=dict(size=14, color="#64748B"),
    )

    fig.update_yaxes(
        showgrid=False,
        zeroline=False,
        showline=False,
        tickfont=dict(size=12, color="#64748B"),
        title_font=dict(size=14, color="#64748B"),
    )

    return fig


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
    orders = data["orders"].copy()
    exception_summary = data["exception_summary"].copy()
    region_summary = data["region_summary"].copy()

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
        risk_order = ["Low", "Medium", "High", "Critical"]

        risk_counts = (
            orders["delay_risk_category"]
            .value_counts()
            .reindex(risk_order, fill_value=0)
            .reset_index()
        )

        risk_counts.columns = ["delay_risk_category", "count"]

        fig = px.pie(
            risk_counts,
            names="delay_risk_category",
            values="count",
            title="Orders by Delay Risk Category",
            hole=0.58,
            color="delay_risk_category",
            color_discrete_map=RISK_COLORS,
        )

        fig.update_traces(
            textposition="inside",
            textinfo="percent",
            marker=dict(line=dict(color="white", width=2)),
        )

        fig = apply_chart_style(fig, height=390)

        fig.update_layout(
            showlegend=False,
            margin=dict(l=20, r=20, t=70, b=30),
        )

        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

    with col6:
        exception_summary = exception_summary.sort_values(
            "order_count",
            ascending=True
        )

        exception_names = exception_summary["exception_type"].tolist()
        bold_exception_names = [f"<b>{name}</b>" for name in exception_names]

        fig = px.bar(
            exception_summary,
            x="order_count",
            y="exception_type",
            orientation="h",
            title="Exception Type Breakdown",
            text="order_count",
            color="exception_type",
            color_discrete_map=EXCEPTION_COLORS,
            hover_data={
                "revenue_total": ":,.0f",
                "average_delay_risk_score": True,
            },
        )

        fig.update_traces(
            textposition="outside",
            cliponaxis=False,
            textfont=dict(
                color="#0F172A",
                size=13,
                family="Arial, sans-serif",
            ),
            marker_line_color="white",
            marker_line_width=1.2,
        )

        fig = apply_chart_style(fig, height=390)

        fig.update_layout(
            showlegend=False,
            bargap=0.30,
            xaxis_title="Orders",
            yaxis_title="",
            margin=dict(l=20, r=60, t=70, b=40),
        )

        fig.update_xaxes(
            showgrid=False,
            zeroline=False,
        )

        fig.update_yaxes(
            showgrid=False,
            zeroline=False,
            tickmode="array",
            tickvals=exception_names,
            ticktext=bold_exception_names,
            automargin=True,
        )

        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

    with col7:
        region_summary = region_summary.sort_values(
            "active_exception_rate",
            ascending=False
        )

        region_names = region_summary["customer_region"].tolist()
        bold_region_names = [f"<b>{name}</b>" for name in region_names]

        fig = px.bar(
            region_summary,
            x="customer_region",
            y="active_exception_rate",
            title="Active Exception Rate by Region",
            text="active_exception_rate",
            color="customer_region",
            color_discrete_map=REGION_COLORS,
            hover_data={
                "total_orders": True,
                "active_exceptions": True,
                "escalations": True,
                "revenue_total": ":,.0f",
            },
        )

        fig.update_traces(
            texttemplate="%{text:.1f}%",
            textposition="inside",
            textfont=dict(
                color="white",
                size=13,
                family="Arial, sans-serif",
            ),
            marker_line_color="white",
            marker_line_width=1.2,
        )

        fig = apply_chart_style(fig, height=390)

        fig.update_layout(
            showlegend=False,
            bargap=0.32,
            xaxis_title="",
            yaxis_title="Exception Rate %",
            margin=dict(l=20, r=20, t=70, b=70),
        )

        fig.update_xaxes(
            showgrid=False,
            zeroline=False,
            tickmode="array",
            tickvals=region_names,
            ticktext=bold_region_names,
        )

        fig.update_yaxes(
            showgrid=False,
            zeroline=False,
        )

        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

    st.markdown('<div class="section-title">Management Insight</div>', unsafe_allow_html=True)

    actionable_exceptions = exception_summary[
        exception_summary["exception_type"] != "No Immediate Exception"
    ].copy()

    if not actionable_exceptions.empty:
        top_actionable_exception = actionable_exceptions.sort_values(
            "order_count",
            ascending=False
        ).iloc[0]

        top_region_by_exceptions = region_summary.sort_values(
            "active_exceptions",
            ascending=False
        ).iloc[0]

        top_region_by_rate = region_summary.sort_values(
            "active_exception_rate",
            ascending=False
        ).iloc[0]

        revenue_at_risk = kpis.get("revenue_at_risk", 0)
        p1_p2_count = kpis.get("p1_p2_priority_exceptions", 0)
        overall_status = kpis.get("overall_status", "Unknown")

        st.markdown(
            f"""
            <div class="insight-card">
                <b>Executive Summary:</b> Overall logistics status is
                <b>{overall_status}</b>. The leading actionable issue is
                <b>{top_actionable_exception["exception_type"]}</b>, affecting
                <b>{int(top_actionable_exception["order_count"])}</b> orders with
                approximately <b>{peso(top_actionable_exception["revenue_total"])}</b>
                in associated order value.
                <br><br>
                <b>Business Impact:</b> High and Critical delay-risk orders represent
                <b>{peso(revenue_at_risk)}</b> in revenue at risk. There are
                <b>{int(p1_p2_count)}</b> P1/P2 priority exceptions requiring management attention.
                <br><br>
                <b>Operational Hotspot:</b> <b>{top_region_by_rate["customer_region"]}</b>
                has the highest active exception rate at
                <b>{top_region_by_rate["active_exception_rate"]:.2f}%</b>, while
                <b>{top_region_by_exceptions["customer_region"]}</b> has the highest exception volume
                with <b>{int(top_region_by_exceptions["active_exceptions"])}</b> active exceptions.
                <br><br>
                <b>Recommended Management Action:</b> Prioritize P1/P2 orders, review the root cause
                behind <b>{top_actionable_exception["exception_type"]}</b>, protect Platinum and Gold
                customer orders, and assign immediate ownership to the responsible operations team.
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="insight-card">
                <b>Executive Summary:</b> No major actionable logistics exceptions were detected.
                Operations can proceed under standard fulfillment monitoring.
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
    warehouse_summary = data["warehouse_summary"].copy()

    warehouse_summary = warehouse_summary.sort_values(
        by="orders_routed",
        ascending=False
    )

    st.markdown('<div class="section-title">Warehouse Performance</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        max_orders = warehouse_summary["orders_routed"].max()
        x_axis_max = max_orders * 1.18

        warehouse_names = warehouse_summary["recommended_warehouse_name"].tolist()
        bold_warehouse_names = [f"<b>{name}</b>" for name in warehouse_names]

        fig = px.bar(
            warehouse_summary,
            x="orders_routed",
            y="recommended_warehouse_name",
            orientation="h",
            color="recommended_warehouse_region",
            color_discrete_map=REGION_COLORS,
            text="orders_routed",
            title="Orders Routed by Warehouse",
            hover_data={
                "recommended_warehouse_region": True,
                "average_warehouse_utilization": True,
                "high_risk_orders": True,
                "revenue_total": ":,.0f",
                "orders_routed": True,
            },
        )

        fig.update_traces(
            textposition="outside",
            cliponaxis=False,
            textfont=dict(
                size=14,
                color="#0F172A",
                family="Arial, sans-serif",
            ),
            marker_line_color="rgba(255,255,255,0.9)",
            marker_line_width=1.2,
        )

        fig = apply_chart_style(fig, height=470)

        fig.update_layout(
            showlegend=False,
            bargap=0.28,
            xaxis_title="Orders Routed",
            yaxis_title="",
            margin=dict(l=20, r=95, t=70, b=60),
        )

        fig.update_xaxes(
            showgrid=False,
            zeroline=False,
            range=[0, x_axis_max],
        )

        fig.update_yaxes(
            showgrid=False,
            zeroline=False,
            tickmode="array",
            tickvals=warehouse_names,
            ticktext=bold_warehouse_names,
            automargin=True,
        )

        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

    with col2:
        fig = px.scatter(
            warehouse_summary,
            x="average_warehouse_utilization",
            y="high_risk_orders",
            size="revenue_total",
            color="recommended_warehouse_region",
            color_discrete_map=REGION_COLORS,
            hover_name="recommended_warehouse_name",
            size_max=46,
            title="Warehouse Utilization vs High-Risk Orders",
            hover_data={
                "orders_routed": True,
                "average_delay_risk_score": True,
                "revenue_total": ":,.0f",
                "recommended_warehouse_region": True,
            },
        )

        fig.update_traces(
            marker=dict(
                line=dict(width=1.8, color="white"),
                opacity=0.88,
            )
        )

        fig.add_vline(
            x=85,
            line_dash="dash",
            line_color="#F59E0B",
            line_width=2,
            annotation_text="85% threshold",
            annotation_position="top right"
        )

        fig = apply_chart_style(fig, height=470)

        fig.update_layout(
            showlegend=False,
            xaxis_title="Average Utilization %",
            yaxis_title="High-Risk Orders",
            margin=dict(l=20, r=40, t=70, b=70),
        )

        fig.update_xaxes(
            showgrid=False,
            zeroline=False,
        )

        fig.update_yaxes(
            showgrid=False,
            zeroline=False,
        )

        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

    top_volume_warehouse = warehouse_summary.sort_values(
        "orders_routed",
        ascending=False
    ).iloc[0]

    top_risk_warehouse = warehouse_summary.sort_values(
        "high_risk_orders",
        ascending=False
    ).iloc[0]

    highest_utilization_warehouse = warehouse_summary.sort_values(
        "average_warehouse_utilization",
        ascending=False
    ).iloc[0]

    total_orders_routed = int(warehouse_summary["orders_routed"].sum())
    total_high_risk_orders = int(warehouse_summary["high_risk_orders"].sum())

    top_volume_share = (top_volume_warehouse["orders_routed"] / total_orders_routed) * 100
    top_risk_share = (top_risk_warehouse["high_risk_orders"] / total_high_risk_orders) * 100 if total_high_risk_orders > 0 else 0

    st.markdown(
        f"""
        <div class="insight-card">
            <b>Director-Level Interpretation:</b> Warehouse routing is currently concentrated in
            <b>{top_volume_warehouse["recommended_warehouse_name"]}</b>, which is handling
            <b>{int(top_volume_warehouse["orders_routed"])}</b> orders, representing
            <b>{top_volume_share:.1f}%</b> of total routed volume.
            <br><br>
            <b>Operational Risk Signal:</b> The highest high-risk order exposure is coming from
            <b>{top_risk_warehouse["recommended_warehouse_name"]}</b>, with
            <b>{int(top_risk_warehouse["high_risk_orders"])}</b> high-risk orders and an average
            delay risk score of <b>{top_risk_warehouse["average_delay_risk_score"]:.2f}</b>.
            This warehouse accounts for approximately <b>{top_risk_share:.1f}%</b> of all warehouse-linked
            high-risk orders.
            <br><br>
            <b>Capacity Watch:</b> The warehouse with the highest utilization is
            <b>{highest_utilization_warehouse["recommended_warehouse_name"]}</b> at
            <b>{highest_utilization_warehouse["average_warehouse_utilization"]:.1f}%</b> utilization.
            Any site operating near or above the 85% threshold should be reviewed for capacity pressure,
            routing imbalance, and overflow planning.
            <br><br>
            <b>Recommended Management Action:</b> Review routing concentration, rebalance volume away from
            high-risk fulfillment nodes, validate whether overflow capacity is being used effectively,
            and prioritize high-value or SLA-sensitive orders through lower-risk warehouses.
        </div>
        """,
        unsafe_allow_html=True,
    )

    display_df = warehouse_summary.copy()
    display_df["revenue_total"] = display_df["revenue_total"].map(lambda x: f"₱{x:,.0f}")

    st.dataframe(display_df, use_container_width=True, height=320)


def courier_performance(data):
    courier_summary = data["courier_summary"].copy()

    courier_summary = courier_summary.sort_values(
        by="high_risk_orders",
        ascending=False
    )

    st.markdown('<div class="section-title">Courier Performance</div>', unsafe_allow_html=True)

    total_orders_assigned = int(courier_summary["orders_assigned"].sum())
    total_high_risk_orders = int(courier_summary["high_risk_orders"].sum())
    avg_delay_rate = float(courier_summary["average_delay_rate"].mean())
    avg_risk_score = float(courier_summary["average_delay_risk_score"].mean())

    top_high_risk_courier = courier_summary.sort_values(
        "high_risk_orders",
        ascending=False
    ).iloc[0]

    highest_delay_courier = courier_summary.sort_values(
        "average_delay_rate",
        ascending=False
    ).iloc[0]

    highest_risk_score_courier = courier_summary.sort_values(
        "average_delay_risk_score",
        ascending=False
    ).iloc[0]

    colm1, colm2, colm3, colm4 = st.columns(4)

    with colm1:
        metric_card(
            "Orders Assigned",
            f"{total_orders_assigned:,}",
            "Total orders assigned to courier partners",
        )

    with colm2:
        metric_card(
            "High-Risk Orders",
            f"{total_high_risk_orders:,}",
            "Orders exposed to elevated delivery risk",
        )

    with colm3:
        metric_card(
            "Avg Delay Rate",
            f"{avg_delay_rate:.1f}%",
            "Average courier delay rate across partners",
        )

    with colm4:
        metric_card(
            "Avg Risk Score",
            f"{avg_risk_score:.1f}",
            "Average delivery risk score across couriers",
        )

    st.markdown('<div style="height: 12px;"></div>', unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1], gap="small")

    with col1:
        courier_summary_bar = courier_summary.sort_values(
            by="high_risk_orders",
            ascending=True
        )

        courier_names = courier_summary_bar["recommended_courier_name"].tolist()
        bold_courier_names = [f"<b>{name}</b>" for name in courier_names]

        max_high_risk = courier_summary_bar["high_risk_orders"].max()
        x_axis_max = max_high_risk * 1.25 if max_high_risk > 0 else 10

        fig = px.bar(
            courier_summary_bar,
            x="high_risk_orders",
            y="recommended_courier_name",
            orientation="h",
            color="recommended_courier_region",
            color_discrete_map=REGION_COLORS,
            text="high_risk_orders",
            title="High-Risk Orders by Courier",
            hover_data={
                "orders_assigned": True,
                "average_delay_rate": True,
                "average_on_time_rate": True,
                "average_delay_risk_score": True,
                "revenue_total": ":,.0f",
            },
        )

        fig.update_traces(
            textposition="outside",
            cliponaxis=False,
            textfont=dict(
                color="#0F172A",
                size=14,
                family="Arial, sans-serif",
            ),
            marker_line_color="white",
            marker_line_width=1.2,
        )

        fig = apply_chart_style(fig, height=430)

        fig.update_layout(
            showlegend=False,
            bargap=0.32,
            xaxis_title="High-Risk Orders",
            yaxis_title="",
            margin=dict(l=20, r=90, t=70, b=60),
        )

        fig.update_xaxes(
            showgrid=False,
            zeroline=False,
            range=[0, x_axis_max],
        )

        fig.update_yaxes(
            showgrid=False,
            zeroline=False,
            tickmode="array",
            tickvals=courier_names,
            ticktext=bold_courier_names,
            automargin=True,
        )

        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

    with col2:
        fig = px.scatter(
            courier_summary,
            x="average_delay_rate",
            y="average_delay_risk_score",
            size="orders_assigned",
            color="recommended_courier_region",
            color_discrete_map=REGION_COLORS,
            hover_name="recommended_courier_name",
            size_max=44,
            title="Courier Delay Rate vs Risk Score",
            hover_data={
                "orders_assigned": True,
                "average_on_time_rate": True,
                "high_risk_orders": True,
                "revenue_total": ":,.0f",
            },
        )

        fig.update_traces(
            marker=dict(
                line=dict(width=1.8, color="white"),
                opacity=0.88,
            )
        )

        fig.add_vline(
            x=15,
            line_dash="dash",
            line_color="#F59E0B",
            line_width=2,
            annotation_text="15% delay threshold",
            annotation_position="top right",
        )

        fig = apply_chart_style(fig, height=430)

        fig.update_layout(
            showlegend=False,
            xaxis_title="Average Delay Rate %",
            yaxis_title="Average Risk Score",
            margin=dict(l=20, r=45, t=70, b=65),
        )

        fig.update_xaxes(
            showgrid=False,
            zeroline=False,
        )

        fig.update_yaxes(
            showgrid=False,
            zeroline=False,
        )

        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

    high_risk_share = (
        top_high_risk_courier["high_risk_orders"] / total_high_risk_orders
    ) * 100 if total_high_risk_orders > 0 else 0

    delay_gap = highest_delay_courier["average_delay_rate"] - avg_delay_rate

    st.markdown(
        f"""
        <div class="insight-card">
            <b>Director-Level Interpretation:</b> Courier performance is a material contributor
            to logistics risk. <b>{top_high_risk_courier["recommended_courier_name"]}</b>
            carries the highest high-risk order exposure with
            <b>{int(top_high_risk_courier["high_risk_orders"])}</b> high-risk orders,
            representing <b>{high_risk_share:.1f}%</b> of all courier-linked high-risk orders.
            <br><br>
            <b>Operational Risk Signal:</b> <b>{highest_delay_courier["recommended_courier_name"]}</b>
            has the highest average delay rate at
            <b>{highest_delay_courier["average_delay_rate"]:.1f}%</b>, which is
            <b>{delay_gap:.1f} percentage points</b> above the courier network average.
            The highest average risk score is observed in
            <b>{highest_risk_score_courier["recommended_courier_name"]}</b> at
            <b>{highest_risk_score_courier["average_delay_risk_score"]:.2f}</b>.
            <br><br>
            <b>Business Impact:</b> Courier-related risk should be reviewed against P1/P2 orders,
            customer tier, and revenue exposure. High-risk courier assignments can directly affect
            SLA performance, customer experience, compensation cost, and repeat purchase behavior.
            <br><br>
            <b>Recommended Management Action:</b> Review courier allocation for high-risk lanes,
            shift urgent Platinum and Gold customer orders to lower-risk courier partners, validate
            backup carrier capacity, and create an escalation rule for couriers exceeding the
            15% delay threshold.
        </div>
        """,
        unsafe_allow_html=True,
    )

    display_df = courier_summary.copy()
    display_df["revenue_total"] = display_df["revenue_total"].map(lambda x: f"₱{x:,.0f}")

    st.dataframe(display_df, use_container_width=True, height=320)


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
