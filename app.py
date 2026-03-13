"""
AI Tax Evasion Detection Platform
A working Streamlit prototype demonstrating end-to-end detection workflow.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import networkx as nx
import random
from datetime import datetime, timedelta
import time

# ─────────────────────────── Page config ───────────────────────────
st.set_page_config(
    page_title="TaxGuard AI · Detection Platform",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────── Custom CSS ────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@400;500;600;700&display=swap');

:root {
    --risk-high:   #e53935;
    --risk-med:    #fb8c00;
    --risk-low:    #43a047;
    --accent:      #1565c0;
    --bg-card:     #f8f9fd;
    --border:      #e3e8f0;
}

.main { background: #f4f6fb; }

.metric-card {
    background: white;
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 18px 22px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.metric-card h2 { font-size: 2.2rem; font-weight: 700; margin: 0; }
.metric-card p  { font-size: 0.82rem; color: #6b7280; margin: 0; text-transform: uppercase; letter-spacing: .04em; }

.risk-badge-high { background:#fce4e4; color:#b71c1c; padding:4px 10px; border-radius:20px; font-size:.75rem; font-weight:600; }
.risk-badge-med  { background:#fff3e0; color:#e65100; padding:4px 10px; border-radius:20px; font-size:.75rem; font-weight:600; }
.risk-badge-low  { background:#e8f5e9; color:#1b5e20; padding:4px 10px; border-radius:20px; font-size:.75rem; font-weight:600; }

.alert-box {
    background: #fff8e1;
    border-left: 4px solid #ffd600;
    border-radius: 0 8px 8px 0;
    padding: 12px 16px;
    margin: 8px 0;
    font-size: .9rem;
}
.alert-box-high {
    background: #fce4e4;
    border-left: 4px solid #e53935;
    border-radius: 0 8px 8px 0;
    padding: 12px 16px;
    margin: 8px 0;
    font-size: .9rem;
}

.section-header {
    font-size: 1.05rem;
    font-weight: 600;
    color: #1a237e;
    border-bottom: 2px solid #e8eaf6;
    padding-bottom: 6px;
    margin-bottom: 14px;
}

.timeline-item {
    display: flex;
    gap: 12px;
    margin-bottom: 10px;
    align-items: flex-start;
    font-size: .85rem;
}

.feature-pill {
    display:inline-block;
    background:#e8eaf6;
    color:#283593;
    border-radius:12px;
    padding:3px 10px;
    font-size:.78rem;
    margin:2px;
}

stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
    font-size: 0.95rem;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────── Data Generation ───────────────────────

@st.cache_data
def generate_entities(n=120, seed=42):
    """Generate synthetic entity dataset with realistic tax evasion signals."""
    rng = np.random.default_rng(seed)

    first_names = ["Rajesh","Priya","Arjun","Sunita","Deepak","Kavita","Vikram","Anita",
                   "Suresh","Meena","Rohit","Pooja","Amit","Nisha","Kiran","Sanjay"]
    last_names  = ["Sharma","Patel","Singh","Verma","Gupta","Kumar","Joshi","Agarwal",
                   "Mehta","Shah","Tiwari","Yadav","Mishra","Pandey","Rao","Reddy"]
    cities      = ["Mumbai","Delhi","Bengaluru","Chennai","Hyderabad","Ahmedabad","Pune","Kolkata"]
    categories  = ["Retail","Restaurant","Consultancy","Construction","IT Services","Real Estate","Transport","Textile"]

    entities = []
    for i in range(n):
        etype = rng.choice(["Individual","Business"], p=[0.6, 0.4])
        city  = rng.choice(cities)
        cat   = rng.choice(categories) if etype == "Business" else None

        # Inject evasion signal ~30% of entities
        is_evader = rng.random() < 0.30

        declared = float(rng.integers(200_000, 5_000_000))

        if is_evader:
            # Evader: spend/assets >> declared income
            actual       = declared * rng.uniform(3.0, 8.0)
            spending     = actual   * rng.uniform(0.7, 1.1)
            properties   = int(rng.integers(3, 10))
            bank_txn_vol = actual   * rng.uniform(1.2, 2.5)
        else:
            actual       = declared * rng.uniform(0.9, 1.3)
            spending     = declared * rng.uniform(0.5, 0.9)
            properties   = int(rng.integers(0, 3))
            bank_txn_vol = declared * rng.uniform(0.6, 1.4)

        spend_income_ratio = spending / max(declared, 1)
        asset_score        = properties * rng.uniform(0.8, 1.2) + (bank_txn_vol / 2_000_000)

        # Anomaly score (Isolation Forest simulation)
        anomaly_signal = min(1.0, (spend_income_ratio - 1.0) * 0.4 + rng.uniform(-0.1, 0.1))
        anomaly_signal = max(0, anomaly_signal)

        # Network anomaly (some entities in suspicious rings)
        network_flag = is_evader and rng.random() < 0.4

        # Composite risk score (0-100)
        risk = float(np.clip(
            anomaly_signal * 40
            + min(properties / 8, 1) * 20
            + min((spend_income_ratio - 1) / 3, 1) * 30
            + (10 if network_flag else 0)
            + rng.uniform(-5, 5),
            0, 100
        ))

        name = f"{rng.choice(first_names)} {rng.choice(last_names)}"
        if etype == "Business":
            name = f"{name} & Co."

        entities.append({
            "id":             f"E{1000+i}",
            "name":           name,
            "type":           etype,
            "city":           city,
            "category":       cat if cat else "—",
            "declared_income":declared,
            "estimated_income":actual,
            "annual_spending":spending,
            "bank_txn_volume":bank_txn_vol,
            "properties_owned":properties,
            "spend_income_ratio":spend_income_ratio,
            "asset_score":    asset_score,
            "anomaly_score":  anomaly_signal,
            "network_flag":   network_flag,
            "risk_score":     risk,
            "risk_level":     "High" if risk >= 65 else ("Medium" if risk >= 35 else "Low"),
            "is_evader":      is_evader,
            "income_gap":     actual - declared,
            "last_filing":    (datetime.today() - timedelta(days=int(rng.integers(30,400)))).strftime("%Y-%m-%d"),
        })

    return pd.DataFrame(entities)


@st.cache_data
def generate_transactions(entity_ids, seed=42):
    """Generate monthly transaction volume series per entity."""
    rng = np.random.default_rng(seed)
    months = pd.date_range("2023-01", periods=12, freq="MS")
    rows = []
    for eid in entity_ids[:30]:
        base = rng.integers(50_000, 500_000)
        for m in months:
            rows.append({"entity_id": eid, "month": m,
                         "volume": float(base * rng.uniform(0.7, 1.4))})
    return pd.DataFrame(rows)


@st.cache_data
def build_network(df, seed=42):
    """Build suspicious transaction network graph."""
    rng = np.random.default_rng(seed)
    G = nx.DiGraph()

    flagged = df[df["network_flag"] == True]["id"].tolist()
    if len(flagged) < 4:
        flagged = df.nlargest(8, "risk_score")["id"].tolist()

    for eid in flagged:
        row = df[df["id"] == eid].iloc[0]
        G.add_node(eid, name=row["name"], risk=row["risk_score"], rtype=row["type"])

    # Add some shell intermediaries
    for i in range(3):
        shell_id = f"SHELL-{i+1}"
        G.add_node(shell_id, name=f"Shell Co. {i+1}", risk=80, rtype="Business")
        flagged.append(shell_id)

    # Connect into rings
    for eid in flagged[:6]:
        for _ in range(rng.integers(1, 3)):
            tgt = rng.choice(flagged)
            if tgt != eid:
                G.add_edge(eid, tgt, weight=float(rng.integers(100_000, 5_000_000)))

    return G


# ─────────────────────────── Helpers ───────────────────────────────

def risk_badge(level):
    cls = {"High":"risk-badge-high","Medium":"risk-badge-med","Low":"risk-badge-low"}[level]
    return f'<span class="{cls}">{level}</span>'


def score_gauge(score, size=120):
    color = "#e53935" if score >= 65 else ("#fb8c00" if score >= 35 else "#43a047")
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        gauge=dict(
            axis=dict(range=[0,100], tickfont=dict(size=9)),
            bar=dict(color=color, thickness=0.25),
            steps=[
                dict(range=[0, 35],  color="#e8f5e9"),
                dict(range=[35, 65], color="#fff3e0"),
                dict(range=[65, 100],color="#fce4e4"),
            ],
            threshold=dict(line=dict(color=color, width=3), thickness=0.75, value=score),
        ),
        number=dict(font=dict(size=28, color=color)),
    ))
    fig.update_layout(margin=dict(l=10,r=10,t=10,b=10), height=size+20, paper_bgcolor="rgba(0,0,0,0)")
    return fig


def shap_waterfall(entity_row):
    """Simulate SHAP-like feature contributions."""
    base = 10.0
    features = {
        "Spend/income ratio":   min((entity_row.spend_income_ratio - 1) * 18, 30),
        "Bank txn volume":      min(entity_row.bank_txn_volume / 10_000_000 * 12, 18),
        "Properties owned":     entity_row.properties_owned * 2.5,
        "Income gap":           min(entity_row.income_gap / 2_000_000 * 20, 20),
        "Anomaly model signal": entity_row.anomaly_score * 22,
        "Network flag":         10 if entity_row.network_flag else 0,
        "Filing recency":       float(np.random.uniform(-3, 3)),
    }
    items = [(k, round(v, 2)) for k, v in features.items()]
    items.sort(key=lambda x: abs(x[1]), reverse=True)

    labels = [i[0] for i in items]
    values = [i[1] for i in items]
    colors = ["#e53935" if v > 0 else "#43a047" for v in values]

    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h",
        marker_color=colors,
        text=[f"+{v:.1f}" if v > 0 else f"{v:.1f}" for v in values],
        textposition="outside",
    ))
    fig.add_vline(x=0, line_width=1, line_color="#90a4ae")
    fig.update_layout(
        title="Feature contributions to risk score (SHAP-style)",
        xaxis_title="Impact on score",
        height=320,
        margin=dict(l=0, r=60, t=40, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=11),
        yaxis=dict(autorange="reversed"),
    )
    return fig


def network_plot(G):
    pos = nx.spring_layout(G, seed=7, k=2.5)
    edge_x, edge_y = [], []
    for u, v in G.edges():
        x0,y0 = pos[u]; x1,y1 = pos[v]
        edge_x += [x0, x1, None]; edge_y += [y0, y1, None]

    edge_trace = go.Scatter(x=edge_x, y=edge_y, mode="lines",
                            line=dict(width=1.2, color="#90a4ae"),
                            hoverinfo="none")

    node_x = [pos[n][0] for n in G.nodes()]
    node_y = [pos[n][1] for n in G.nodes()]
    node_text = [G.nodes[n].get("name","?") for n in G.nodes()]
    node_risk  = [G.nodes[n].get("risk", 50) for n in G.nodes()]
    node_color = ["#e53935" if r>=65 else ("#fb8c00" if r>=35 else "#43a047") for r in node_risk]

    node_trace = go.Scatter(
        x=node_x, y=node_y, mode="markers+text",
        marker=dict(size=18, color=node_color,
                    line=dict(width=2, color="white")),
        text=[n.split()[0] for n in node_text],
        textposition="top center",
        hovertext=[f"{n}<br>Risk: {r:.0f}" for n, r in zip(node_text, node_risk)],
        hoverinfo="text",
    )

    fig = go.Figure([edge_trace, node_trace])
    fig.update_layout(
        showlegend=False,
        hovermode="closest",
        margin=dict(l=20,r=20,t=10,b=10),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        height=380,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# ─────────────────────────── Load data ─────────────────────────────

df = generate_entities(120)
txn_df = generate_transactions(df["id"].tolist())
G = build_network(df)


# ─────────────────────────── Sidebar ───────────────────────────────

with st.sidebar:
    st.markdown("## 🛡️ TaxGuard AI")
    st.markdown("*AI-powered tax compliance platform*")
    st.divider()

    page = st.radio("Navigation", [
        "📊 Executive Dashboard",
        "🔍 Entity Deep-Dive",
        "🤖 Run AI Analysis",
        "🕸️  Network Investigation",
        "📋 Alert Queue",
        "🔄 Model Feedback",
    ])

    st.divider()
    st.markdown("**Filters**")
    risk_filter = st.multiselect("Risk Level", ["High","Medium","Low"],
                                  default=["High","Medium","Low"])
    type_filter = st.multiselect("Entity Type", ["Individual","Business"],
                                  default=["Individual","Business"])
    city_filter = st.multiselect("City", sorted(df["city"].unique()),
                                  default=list(df["city"].unique()))

    score_range = st.slider("Risk Score Range", 0, 100, (0, 100))

    st.divider()
    st.markdown(f"**Database**: {len(df)} entities loaded")
    st.markdown(f"**High-Risk**: {len(df[df.risk_level=='High'])} flagged")
    st.caption("Demo v1.0 · Synthetic data only")


# ─────────────────────────── Filter data ───────────────────────────

mask = (
    df["risk_level"].isin(risk_filter) &
    df["type"].isin(type_filter) &
    df["city"].isin(city_filter) &
    df["risk_score"].between(score_range[0], score_range[1])
)
filtered = df[mask].copy()


# ══════════════════════════════════════════════════════════════════
#  PAGE 1: Executive Dashboard
# ══════════════════════════════════════════════════════════════════

if "Dashboard" in page:
    st.markdown("# 📊 Executive Compliance Dashboard")
    st.markdown(f"*{datetime.today().strftime('%d %B %Y')} · Real-time risk overview*")

    # KPI Row
    c1, c2, c3, c4, c5 = st.columns(5)
    high_risk   = len(df[df.risk_level=="High"])
    med_risk    = len(df[df.risk_level=="Medium"])
    avg_score   = df.risk_score.mean()
    potential_evaded = df[df.risk_level=="High"]["income_gap"].sum()
    network_cases    = int(df.network_flag.sum())

    with c1:
        st.markdown(f"""<div class="metric-card">
            <p>Total Entities</p>
            <h2>{len(filtered)}</h2>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="metric-card">
            <p>High Risk</p>
            <h2 style="color:#e53935">{high_risk}</h2>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="metric-card">
            <p>Medium Risk</p>
            <h2 style="color:#fb8c00">{med_risk}</h2>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class="metric-card">
            <p>Avg Risk Score</p>
            <h2 style="color:#1565c0">{avg_score:.1f}</h2>
        </div>""", unsafe_allow_html=True)
    with c5:
        st.markdown(f"""<div class="metric-card">
            <p>Network Suspects</p>
            <h2 style="color:#6a1b9a">{network_cases}</h2>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_l, col_r = st.columns([3, 2])

    with col_l:
        st.markdown('<div class="section-header">Risk Score Distribution</div>', unsafe_allow_html=True)
        fig_hist = px.histogram(
            filtered, x="risk_score", nbins=25, color="risk_level",
            color_discrete_map={"High":"#e53935","Medium":"#fb8c00","Low":"#43a047"},
            labels={"risk_score":"Risk Score","count":"Entities"},
            opacity=0.85,
        )
        fig_hist.update_layout(
            height=280, margin=dict(l=0,r=0,t=10,b=20),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(title="", orientation="h", y=1.02),
            bargap=0.05,
        )
        st.plotly_chart(fig_hist, use_container_width=True)

        st.markdown('<div class="section-header">Declared vs Estimated Income Gap (Top 20)</div>', unsafe_allow_html=True)
        top20 = filtered.nlargest(20, "income_gap")
        fig_bar = go.Figure()
        fig_bar.add_bar(name="Declared", x=top20["name"].str.split().str[0],
                        y=top20["declared_income"], marker_color="#42a5f5")
        fig_bar.add_bar(name="Estimated", x=top20["name"].str.split().str[0],
                        y=top20["estimated_income"], marker_color="#ef5350", opacity=0.7)
        fig_bar.update_layout(
            barmode="overlay", height=260,
            margin=dict(l=0,r=0,t=10,b=40),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", y=1.05),
            xaxis_tickangle=-30,
            yaxis=dict(title="₹ Amount"),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_r:
        st.markdown('<div class="section-header">Risk Level Breakdown</div>', unsafe_allow_html=True)
        pie_data = filtered["risk_level"].value_counts()
        fig_pie = px.pie(
            values=pie_data.values, names=pie_data.index,
            color=pie_data.index,
            color_discrete_map={"High":"#e53935","Medium":"#fb8c00","Low":"#43a047"},
            hole=0.55,
        )
        fig_pie.update_layout(height=220, margin=dict(l=0,r=0,t=10,b=0),
                               paper_bgcolor="rgba(0,0,0,0)",
                               legend=dict(orientation="h", y=-0.05))
        fig_pie.update_traces(textinfo="percent+label")
        st.plotly_chart(fig_pie, use_container_width=True)

        st.markdown('<div class="section-header">Risk by City</div>', unsafe_allow_html=True)
        city_risk = filtered.groupby(["city","risk_level"]).size().reset_index(name="count")
        fig_city = px.bar(city_risk, x="city", y="count", color="risk_level",
                          color_discrete_map={"High":"#e53935","Medium":"#fb8c00","Low":"#43a047"},
                          barmode="stack")
        fig_city.update_layout(height=220, margin=dict(l=0,r=0,t=10,b=40),
                                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                legend=dict(title="", orientation="h", y=1.05),
                                xaxis_tickangle=-30)
        st.plotly_chart(fig_city, use_container_width=True)

    # Risk leaderboard table
    st.markdown('<div class="section-header">🚨 High-Risk Entity Leaderboard</div>', unsafe_allow_html=True)
    table_df = filtered.nlargest(15, "risk_score")[
        ["id","name","type","city","declared_income","estimated_income",
         "risk_score","risk_level","spend_income_ratio","properties_owned","network_flag"]
    ].copy()
    table_df["declared_income"]  = table_df["declared_income"].apply(lambda x: f"₹{x:,.0f}")
    table_df["estimated_income"] = table_df["estimated_income"].apply(lambda x: f"₹{x:,.0f}")
    table_df["risk_score"]       = table_df["risk_score"].apply(lambda x: f"{x:.1f}")
    table_df["spend_income_ratio"]= table_df["spend_income_ratio"].apply(lambda x: f"{x:.2f}x")
    table_df["network_flag"]     = table_df["network_flag"].apply(lambda x: "⚠️ Yes" if x else "No")
    st.dataframe(table_df.rename(columns={
        "id":"ID","name":"Entity","type":"Type","city":"City",
        "declared_income":"Declared","estimated_income":"Estimated",
        "risk_score":"Score","risk_level":"Level",
        "spend_income_ratio":"Spend Ratio",
        "properties_owned":"Properties","network_flag":"Network Flag",
    }), use_container_width=True, hide_index=True, height=380)


# ══════════════════════════════════════════════════════════════════
#  PAGE 2: Entity Deep-Dive
# ══════════════════════════════════════════════════════════════════

elif "Deep-Dive" in page:
    st.markdown("# 🔍 Entity Deep-Dive Analysis")

    entity_list = filtered.sort_values("risk_score", ascending=False)["id"].tolist()
    entity_ids_labels = {
        r["id"]: f"{r['id']} · {r['name']} ({r['risk_level']} Risk)"
        for _, r in filtered.sort_values("risk_score", ascending=False).iterrows()
    }
    selected_id = st.selectbox("Select Entity", entity_list,
                                 format_func=lambda x: entity_ids_labels[x])

    entity = filtered[filtered["id"] == selected_id].iloc[0]

    # Header row
    h1, h2, h3 = st.columns([2, 1, 1])
    with h1:
        st.markdown(f"### {entity['name']}")
        st.markdown(f"**ID:** `{entity['id']}` · **Type:** {entity['type']} · **City:** {entity['city']} · **Category:** {entity['category']}")
        st.markdown(f"**Last Filing:** {entity['last_filing']}")
        st.markdown(risk_badge(entity['risk_level']), unsafe_allow_html=True)
    with h2:
        st.plotly_chart(score_gauge(entity["risk_score"]), use_container_width=True)
    with h3:
        st.metric("Declared Income", f"₹{entity['declared_income']:,.0f}")
        st.metric("Estimated Income", f"₹{entity['estimated_income']:,.0f}",
                  delta=f"+₹{entity['income_gap']:,.0f} gap" if entity['income_gap'] > 0 else None,
                  delta_color="inverse")
        st.metric("Properties Owned", entity["properties_owned"])

    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs(["📊 Financial Profile", "🧠 AI Explanation", "📈 Trends", "📝 Audit Notes"])

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div class="section-header">Key Financial Indicators</div>', unsafe_allow_html=True)
            indicators = {
                "Annual Spending":        f"₹{entity['annual_spending']:,.0f}",
                "Bank Transaction Volume":f"₹{entity['bank_txn_volume']:,.0f}",
                "Spend / Income Ratio":   f"{entity['spend_income_ratio']:.2f}x",
                "Asset Score":            f"{entity['asset_score']:.2f}",
                "Anomaly Score":          f"{entity['anomaly_score']:.3f}",
                "Network Involvement":    "⚠️ Flagged" if entity['network_flag'] else "✅ Clean",
            }
            for k, v in indicators.items():
                c_a, c_b = st.columns([2, 1])
                c_a.write(k)
                c_b.write(f"**{v}**")

        with col2:
            st.markdown('<div class="section-header">Risk Signal Radar</div>', unsafe_allow_html=True)
            categories_radar = ["Spend Mismatch","Asset Holdings","Transaction Volume",
                                 "Income Gap","Anomaly","Network Risk"]
            values_radar = [
                min(entity["spend_income_ratio"]/5*100, 100),
                min(entity["properties_owned"]/8*100, 100),
                min(entity["bank_txn_volume"]/5_000_000*100, 100),
                min(entity["income_gap"]/5_000_000*100, 100),
                entity["anomaly_score"]*100,
                100 if entity["network_flag"] else 20,
            ]
            fig_radar = go.Figure(go.Scatterpolar(
                r=values_radar + [values_radar[0]],
                theta=categories_radar + [categories_radar[0]],
                fill="toself",
                fillcolor="rgba(229,57,53,0.15)",
                line=dict(color="#e53935", width=2),
            ))
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0,100])),
                height=280, margin=dict(l=20,r=20,t=20,b=20),
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_radar, use_container_width=True)

    with tab2:
        st.markdown('<div class="section-header">AI Model Explanations (XAI)</div>', unsafe_allow_html=True)
        st.plotly_chart(shap_waterfall(entity), use_container_width=True)

        st.markdown("**Natural Language Explanation**")
        explanations = []
        if entity["spend_income_ratio"] > 2:
            explanations.append(f"🔴 Annual spending (₹{entity['annual_spending']:,.0f}) is **{entity['spend_income_ratio']:.1f}x** the declared income, indicating a significant lifestyle mismatch.")
        if entity["properties_owned"] >= 3:
            explanations.append(f"🔴 Entity owns **{entity['properties_owned']} properties** inconsistent with declared income level.")
        if entity["income_gap"] > 1_000_000:
            explanations.append(f"🟠 Estimated income exceeds declared income by **₹{entity['income_gap']:,.0f}** based on spending and asset patterns.")
        if entity["network_flag"]:
            explanations.append("🔴 Entity appears in a **suspicious transaction network** — possible shell company involvement or circular transactions.")
        if entity["anomaly_score"] > 0.5:
            explanations.append(f"🟠 Isolation Forest model flagged this entity with anomaly score **{entity['anomaly_score']:.3f}** (population average: 0.21).")
        if not explanations:
            explanations.append("✅ No significant risk signals detected. Entity appears consistent with declared profile.")

        for exp in explanations:
            st.markdown(exp)

        st.markdown("**Model Outputs Summary**")
        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.metric("Anomaly Model", f"{entity['anomaly_score']:.3f}", help="Isolation Forest score")
        mc2.metric("Income Pred.", f"₹{entity['estimated_income']:,.0f}", help="XGBoost regression")
        mc3.metric("Risk Score",   f"{entity['risk_score']:.1f}/100", help="Ensemble score")
        mc4.metric("Network Risk", "High" if entity["network_flag"] else "Low", help="GNN output")

    with tab3:
        st.markdown('<div class="section-header">Transaction Volume Trend</div>', unsafe_allow_html=True)
        ent_txn = txn_df[txn_df["entity_id"] == selected_id]
        if len(ent_txn) > 0:
            fig_line = px.line(ent_txn, x="month", y="volume",
                               labels={"volume":"₹ Volume","month":"Month"},
                               markers=True)
            fig_line.update_traces(line_color="#1565c0", marker_size=6)
            fig_line.update_layout(height=250, paper_bgcolor="rgba(0,0,0,0)",
                                    plot_bgcolor="rgba(0,0,0,0)",
                                    margin=dict(l=0,r=0,t=10,b=20))
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("Transaction data not available for this entity in current sample.")

        st.markdown('<div class="section-header">Income vs Spending Comparison</div>', unsafe_allow_html=True)
        comp_data = {
            "Metric": ["Declared Income","Estimated Income","Annual Spending","Bank Txn Vol."],
            "Amount": [entity["declared_income"], entity["estimated_income"],
                       entity["annual_spending"], entity["bank_txn_volume"]],
        }
        fig_comp = px.bar(comp_data, x="Metric", y="Amount",
                          color="Metric",
                          color_discrete_sequence=["#42a5f5","#ef5350","#ab47bc","#26a69a"])
        fig_comp.update_layout(height=240, showlegend=False,
                                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                margin=dict(l=0,r=0,t=10,b=20))
        st.plotly_chart(fig_comp, use_container_width=True)

    with tab4:
        st.markdown('<div class="section-header">Audit Trail &amp; Notes</div>', unsafe_allow_html=True)
        status = st.selectbox("Investigation Status",
                               ["Under Review","Open","Closed - Evasion Confirmed",
                                "Closed - No Violation","Escalated"])
        notes = st.text_area("Investigator Notes", placeholder="Add notes about this entity...")
        priority = st.select_slider("Priority", ["Low","Medium","High","Critical"])

        col_s, col_x = st.columns(2)
        with col_s:
            if st.button("💾 Save Investigation Notes", use_container_width=True):
                st.success("Notes saved and model feedback recorded.")
        with col_x:
            if st.button("📨 Escalate to Senior Auditor", use_container_width=True, type="primary"):
                st.success(f"Case {selected_id} escalated with priority: {priority}")


# ══════════════════════════════════════════════════════════════════
#  PAGE 3: Run AI Analysis
# ══════════════════════════════════════════════════════════════════

elif "AI Analysis" in page:
    st.markdown("# 🤖 Run AI Analysis Pipeline")
    st.markdown("Simulate the full end-to-end AI detection workflow on selected entities.")

    st.markdown('<div class="section-header">Pipeline Configuration</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        run_anomaly   = st.checkbox("Anomaly Detection (Isolation Forest)", value=True)
        run_income    = st.checkbox("Income Prediction (XGBoost)", value=True)
    with c2:
        run_revenue   = st.checkbox("Revenue Prediction (LightGBM)", value=True)
        run_network   = st.checkbox("Network Analysis (GNN)", value=True)
    with c3:
        run_xai       = st.checkbox("Explainability (SHAP)", value=True)
        threshold     = st.slider("Alert Threshold", 50, 90, 65)

    sample_size = st.slider("Sample Size (entities to analyse)", 10, len(filtered), min(50, len(filtered)))

    if st.button("▶ Run Full AI Pipeline", type="primary", use_container_width=True):
        sample = filtered.sample(n=sample_size, random_state=42)
        progress = st.progress(0)
        status_box = st.empty()

        steps = []
        if run_anomaly: steps.append(("🔍 Anomaly Detection", 0.2))
        if run_income:  steps.append(("📊 Income Prediction", 0.4))
        if run_revenue: steps.append(("💼 Revenue Prediction", 0.6))
        if run_network: steps.append(("🕸️  Network Analysis", 0.78))
        if run_xai:     steps.append(("🧠 Computing SHAP", 0.92))
        steps.append(("✅ Generating Risk Scores", 1.0))

        for label, frac in steps:
            status_box.markdown(f"**Running:** {label}...")
            time.sleep(0.6)
            progress.progress(frac)

        status_box.markdown("**✅ Pipeline complete!**")
        st.success(f"Analysed {sample_size} entities. Found **{len(sample[sample.risk_score >= threshold])} alerts** above threshold {threshold}.")

        # Results
        st.markdown('<div class="section-header">Pipeline Results</div>', unsafe_allow_html=True)
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Entities Scanned", sample_size)
        r2.metric("Anomalies Detected", int(sample["anomaly_score"].gt(0.4).sum()))
        r3.metric("Alerts Generated",   int(sample["risk_score"].ge(threshold).sum()))
        r4.metric("Network Suspects",   int(sample["network_flag"].sum()))

        # Score scatter
        st.markdown('<div class="section-header">Declared Income vs Risk Score</div>', unsafe_allow_html=True)
        fig_scatter = px.scatter(
            sample, x="declared_income", y="risk_score",
            color="risk_level", size="income_gap",
            color_discrete_map={"High":"#e53935","Medium":"#fb8c00","Low":"#43a047"},
            hover_data=["name","type","city"],
            labels={"declared_income":"Declared Income (₹)","risk_score":"Risk Score"},
            opacity=0.75,
        )
        fig_scatter.add_hline(y=threshold, line_dash="dash", line_color="#e53935",
                               annotation_text=f"Alert threshold: {threshold}")
        fig_scatter.update_layout(
            height=320, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0,r=0,t=20,b=20),
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

        # Feature importance (simulated)
        st.markdown('<div class="section-header">Global Feature Importance</div>', unsafe_allow_html=True)
        fi_data = {
            "Feature": ["Spend/income ratio","Bank txn volume","Income gap",
                         "Properties owned","Anomaly score","Network flag",
                         "Asset score","Filing age"],
            "Importance": [0.31, 0.22, 0.18, 0.12, 0.09, 0.05, 0.02, 0.01],
        }
        fi_df = pd.DataFrame(fi_data).sort_values("Importance")
        fig_fi = px.bar(fi_df, x="Importance", y="Feature", orientation="h",
                         color="Importance", color_continuous_scale="Reds")
        fig_fi.update_layout(height=280, margin=dict(l=0,r=0,t=10,b=10),
                               paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                               coloraxis_showscale=False)
        st.plotly_chart(fig_fi, use_container_width=True)

    else:
        st.info("Configure the pipeline above and click **Run Full AI Pipeline** to begin analysis.")

        st.markdown('<div class="section-header">Model Architecture Overview</div>', unsafe_allow_html=True)
        models_info = {
            "Anomaly Detection": ("Isolation Forest", "sklearn", "Detects unusual spending vs income patterns"),
            "Income Prediction": ("XGBoost Regressor", "xgboost", "Estimates true income from asset & spending features"),
            "Revenue Prediction":("LightGBM Regressor","lightgbm","Predicts business revenue from location + traffic"),
            "Network Analysis":  ("Graph Neural Network","PyG / NetworkX","Detects shell cos & circular transaction rings"),
            "Explainability":    ("SHAP + LIME", "shap / lime","Waterfall & force plots per entity"),
        }
        for name, (algo, lib, desc) in models_info.items():
            with st.expander(f"**{name}** — {algo}"):
                st.markdown(f"**Library:** `{lib}`")
                st.markdown(f"**Purpose:** {desc}")


# ══════════════════════════════════════════════════════════════════
#  PAGE 4: Network Investigation
# ══════════════════════════════════════════════════════════════════

elif "Network" in page:
    st.markdown("# 🕸️ Network Investigation")
    st.markdown("Visualise suspicious transaction networks, shell company chains, and circular invoice patterns.")

    col_graph, col_info = st.columns([3, 1])

    with col_graph:
        st.markdown('<div class="section-header">Suspicious Transaction Network</div>', unsafe_allow_html=True)
        st.plotly_chart(network_plot(G), use_container_width=True)
        st.caption("Node size = entity importance · Color = risk level (red=high, orange=medium, green=low) · Arrows = money flow direction")

    with col_info:
        st.markdown('<div class="section-header">Network Stats</div>', unsafe_allow_html=True)
        st.metric("Nodes in Network", G.number_of_nodes())
        st.metric("Transaction Links", G.number_of_edges())
        st.metric("Shell Companies", sum(1 for n in G.nodes() if "SHELL" in n))

        st.markdown("**Risk Indicators**")
        flags = [
            "⚠️ Circular transaction loops detected",
            "⚠️ Shell intermediaries identified",
            "⚠️ Rapid fund movement pattern",
        ]
        for f in flags:
            st.markdown(f"<div class='alert-box'>{f}</div>", unsafe_allow_html=True)

    st.divider()
    st.markdown('<div class="section-header">Network Entity List</div>', unsafe_allow_html=True)
    net_ids = [n for n in G.nodes() if not n.startswith("SHELL")]
    net_entities = df[df["id"].isin(net_ids)][["id","name","type","declared_income","risk_score","risk_level"]]
    if len(net_entities) > 0:
        st.dataframe(net_entities.assign(
            declared_income=lambda d: d["declared_income"].apply(lambda x: f"₹{x:,.0f}"),
            risk_score=lambda d: d["risk_score"].apply(lambda x: f"{x:.1f}"),
        ).rename(columns={"id":"ID","name":"Entity","type":"Type",
                           "declared_income":"Declared","risk_score":"Score","risk_level":"Level"}),
                     use_container_width=True, hide_index=True)

    st.markdown('<div class="section-header">Network Analysis Explanation</div>', unsafe_allow_html=True)
    st.markdown("""
    The GNN model analysed relationships between all flagged entities and identified the following patterns:
    - **Circular invoicing:** Entity E1005 → SHELL-1 → E1012 → E1005 suggests a fake invoice loop
    - **Layering:** Funds move through 2–3 shell companies before reaching a declared account
    - **Velocity anomaly:** High-volume transactions occurring within hours between related entities
    """)


# ══════════════════════════════════════════════════════════════════
#  PAGE 5: Alert Queue
# ══════════════════════════════════════════════════════════════════

elif "Alert" in page:
    st.markdown("# 📋 Alert Queue")

    threshold_alert = st.slider("Alert threshold", 50, 95, 65, key="alert_thresh")
    alerts = filtered[filtered["risk_score"] >= threshold_alert].sort_values("risk_score", ascending=False)

    st.markdown(f"**{len(alerts)} active alerts** above score {threshold_alert}")

    priority_filter = st.radio("Filter by priority", ["All","Critical (≥85)","High (65–84)"], horizontal=True)
    if "Critical" in priority_filter:
        alerts = alerts[alerts["risk_score"] >= 85]
    elif "High" in priority_filter:
        alerts = alerts[(alerts["risk_score"] >= 65) & (alerts["risk_score"] < 85)]

    for _, row in alerts.head(20).iterrows():
        box_class = "alert-box-high" if row["risk_score"] >= 80 else "alert-box"
        icon = "🔴" if row["risk_score"] >= 80 else "🟠"
        reasons = []
        if row["spend_income_ratio"] > 2:
            reasons.append(f"Spend ratio {row['spend_income_ratio']:.1f}x")
        if row["properties_owned"] >= 3:
            reasons.append(f"{row['properties_owned']} properties")
        if row["network_flag"]:
            reasons.append("Network suspect")
        reason_str = " · ".join(reasons) if reasons else "Multiple signals"

        st.markdown(f"""<div class="{box_class}">
            {icon} <strong>{row['name']}</strong> ({row['id']}) · {row['type']} · {row['city']}<br>
            <span>Risk Score: <strong>{row['risk_score']:.1f}</strong> &nbsp;|&nbsp; {reason_str}</span>
        </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
#  PAGE 6: Model Feedback
# ══════════════════════════════════════════════════════════════════

elif "Feedback" in page:
    st.markdown("# 🔄 Model Feedback & Continuous Learning")
    st.markdown("Submit investigation outcomes to improve model accuracy over time.")

    col_fb, col_metrics = st.columns([2, 1])

    with col_fb:
        st.markdown('<div class="section-header">Record Investigation Outcome</div>', unsafe_allow_html=True)
        fb_entity = st.selectbox("Entity", filtered["id"].tolist(),
                                   format_func=lambda x: entity_ids_labels.get(x, x))
        fb_outcome = st.selectbox("Outcome", [
            "Confirmed Tax Evasion",
            "Partial Evasion Found",
            "No Violation — False Positive",
            "Insufficient Evidence — Pending",
        ])
        fb_amount   = st.number_input("Confirmed Evaded Amount (₹)", min_value=0, step=10_000)
        fb_category = st.multiselect("Evasion Type", [
            "Income underreporting", "Shell companies",
            "Fake invoices", "Undisclosed assets", "Cash transactions"
        ])
        fb_notes = st.text_area("Feedback Notes")

        if st.button("📤 Submit Feedback to Model", type="primary"):
            st.success("✅ Feedback recorded. Model retraining queued for next cycle.")
            st.balloons()

    with col_metrics:
        st.markdown('<div class="section-header">Model Performance</div>', unsafe_allow_html=True)
        perf = {
            "Metric": ["Precision","Recall","F1 Score","AUC-ROC","False Positive Rate"],
            "Value":  [0.847, 0.793, 0.819, 0.911, 0.153],
        }
        for m, v in zip(perf["Metric"], perf["Value"]):
            st.metric(m, f"{v:.3f}")

        st.markdown('<div class="section-header">Feedback Summary</div>', unsafe_allow_html=True)
        st.metric("Cases Reviewed", "247")
        st.metric("Confirmed Evasion", "73 (29.6%)")
        st.metric("Model Accuracy Δ", "+4.2% after last retrain", delta="+4.2%")

    st.divider()
    st.markdown('<div class="section-header">Retraining History</div>', unsafe_allow_html=True)
    retrain_data = {
        "Date": ["2024-01","2024-03","2024-06","2024-09","2024-12","2025-03"],
        "AUC":  [0.841, 0.856, 0.871, 0.888, 0.899, 0.911],
        "Precision": [0.791, 0.803, 0.818, 0.831, 0.840, 0.847],
    }
    fig_retrain = go.Figure()
    fig_retrain.add_scatter(x=retrain_data["Date"], y=retrain_data["AUC"],
                             mode="lines+markers", name="AUC-ROC", line=dict(color="#1565c0"))
    fig_retrain.add_scatter(x=retrain_data["Date"], y=retrain_data["Precision"],
                             mode="lines+markers", name="Precision", line=dict(color="#43a047"))
    fig_retrain.update_layout(
        height=240, margin=dict(l=0,r=0,t=10,b=20),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=1.05),
        yaxis=dict(range=[0.7, 1.0]),
    )
    st.plotly_chart(fig_retrain, use_container_width=True)
