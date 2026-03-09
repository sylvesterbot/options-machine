from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Options Machine Dashboard", layout="wide")
st.title("Options Machine Dashboard")

st.markdown("""
<style>
    /* Import Google Font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* KPI Cards */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #1A1F2E 0%, #252B3B 100%);
        border: 1px solid rgba(0, 212, 170, 0.2);
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    }
    [data-testid="stMetricLabel"] { font-size: 0.85rem; color: #8B95A5; }
    [data-testid="stMetricValue"] { font-size: 1.6rem; font-weight: 700; }

    /* Tab styling */
    .stTabs [data-baseweb="tab"] {
        font-weight: 600;
        font-size: 1rem;
        padding: 10px 24px;
    }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #00D4AA 0%, #00B894 100%);
        color: #0E1117;
        font-weight: 600;
        border-radius: 8px;
        border: none;
        padding: 8px 24px;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0, 212, 170, 0.4);
    }

    /* Download buttons */
    .stDownloadButton > button {
        background: transparent;
        border: 1px solid #00D4AA;
        color: #00D4AA;
        border-radius: 8px;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: #0A0D14;
        border-right: 1px solid rgba(0, 212, 170, 0.1);
    }

    /* Tier cards */
    .tier-1 { background: linear-gradient(135deg, rgba(255,75,75,0.15), rgba(255,75,75,0.05)); border-left: 4px solid #FF4B4B; }
    .tier-2 { background: linear-gradient(135deg, rgba(255,193,7,0.15), rgba(255,193,7,0.05)); border-left: 4px solid #FFC107; }
    .near-miss { background: linear-gradient(135deg, rgba(158,158,158,0.15), rgba(158,158,158,0.05)); border-left: 4px solid #9E9E9E; }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_csv(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p)


@st.cache_data
def load_json(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


backtest_path = st.sidebar.text_input("Backtest CSV", "outputs/walkforward_trades.csv")
scan_path = st.sidebar.text_input("Scan CSV", "outputs/openbb_earnings_iv_scan.csv")
mc_path = st.sidebar.text_input("Monte Carlo JSON", "outputs/monte_carlo.json")

backtest_df = load_csv(backtest_path)
scan_df = load_csv(scan_path)
mc = load_json(mc_path)

tab_overview, tab_backtest, tab_mc, tab_alerts, tab_config = st.tabs(
    ["📊 Overview", "⚡ Backtest", "🎲 Monte Carlo", "🔔 Alerts", "⚙️ Config"]
)

# ── Overview Tab ──────────────────────────────────────────────
with tab_overview:
    if not backtest_df.empty and "return_pct" in backtest_df.columns:
        r = pd.to_numeric(backtest_df["return_pct"], errors="coerce").fillna(0)
        eq = (1 + r).cumprod()
        total_return = float(eq.iloc[-1] - 1.0) if len(eq) > 0 else 0.0
        peak = eq.cummax()
        dd = (eq / peak) - 1.0
        max_dd = float(dd.min())
        wins = int((r > 0).sum())
        win_rate = wins / len(r) * 100 if len(r) > 0 else 0.0
        vol = float(r.std(ddof=1)) if len(r) > 1 else 0.0

        trades_per_year = float(len(r))
        if "entry_date" in backtest_df.columns:
            dates = pd.to_datetime(backtest_df["entry_date"], errors="coerce")
            years = (dates.max() - dates.min()).days / 365.25
            if years > 0:
                trades_per_year = len(r) / years
        sharpe = float((r.mean() / vol) * np.sqrt(trades_per_year)) if vol > 0 else 0.0

        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Trades", int(len(r)))
        c2.metric("Total Return", f"{total_return*100:.1f}%")
        c3.metric("Win Rate", f"{win_rate:.0f}%")
        c4.metric("Max Drawdown", f"{max_dd*100:.1f}%")
        c5.metric("Sharpe", f"{sharpe:.2f}")
        c6.metric("Trades/Year", f"{trades_per_year:.1f}")
    else:
        st.info("No backtest data available.")

    if not backtest_df.empty:
        st.dataframe(backtest_df.tail(50), use_container_width=True)
        st.download_button(
            "📥 Export Overview",
            backtest_df.to_csv(index=False),
            "overview.csv",
            "text/csv",
            key="dl_overview",
        )

# ── Backtest Tab ──────────────────────────────────────────────
with tab_backtest:
    st.subheader("Backtest")
    if backtest_df.empty:
        st.info("No backtest CSV found.")
    else:
        if "return_pct" in backtest_df.columns:
            bt = backtest_df.copy()
            bt["eq"] = (1 + pd.to_numeric(bt["return_pct"], errors="coerce").fillna(0)).cumprod()
            if "exit_date" in bt.columns:
                bt["x"] = pd.to_datetime(bt["exit_date"], errors="coerce")
            elif "entry_date" in bt.columns:
                bt["x"] = pd.to_datetime(bt["entry_date"], errors="coerce")
            else:
                bt["x"] = range(len(bt))
            fig = px.line(bt, x="x", y="eq", title="Equity Curve")
            st.plotly_chart(fig, use_container_width=True)

            bt["return_pct_num"] = pd.to_numeric(bt["return_pct"], errors="coerce")
            bt["color"] = bt["return_pct_num"].apply(lambda x: "green" if x > 0 else "red")
            bt["trade_num"] = range(len(bt))
            fig_bar = px.bar(
                bt, x="trade_num", y="return_pct_num",
                color="color", color_discrete_map={"green": "#00D4AA", "red": "#FF4B4B"},
                title="Per-Trade Returns",
                labels={"trade_num": "Trade #", "return_pct_num": "Return %"},
            )
            fig_bar.update_layout(showlegend=False)
            st.plotly_chart(fig_bar, use_container_width=True)

        st.dataframe(backtest_df, use_container_width=True)

# ── Monte Carlo Tab ───────────────────────────────────────────
with tab_mc:
    st.subheader("Monte Carlo")
    if not mc:
        st.info("No Monte Carlo JSON found.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Median Return", f"{mc.get('median_return', 0.0)*100:.2f}%")
        c2.metric("P5 Return", f"{mc.get('p5_return', 0.0)*100:.2f}%")
        c3.metric("P95 Return", f"{mc.get('p95_return', 0.0)*100:.2f}%")

        fan = mc.get("fan_chart", {})
        if fan:
            fig_fan = go.Figure()
            steps = list(range(len(fan.get("50", []))))

            fig_fan.add_trace(go.Scatter(
                x=steps, y=fan["95"], mode="lines", line=dict(width=0),
                showlegend=False, name="P95"))
            fig_fan.add_trace(go.Scatter(
                x=steps, y=fan["5"], mode="lines", line=dict(width=0),
                fill="tonexty", fillcolor="rgba(0, 212, 170, 0.1)",
                showlegend=True, name="5th-95th Percentile"))
            fig_fan.add_trace(go.Scatter(
                x=steps, y=fan["75"], mode="lines", line=dict(width=0),
                showlegend=False, name="P75"))
            fig_fan.add_trace(go.Scatter(
                x=steps, y=fan["25"], mode="lines", line=dict(width=0),
                fill="tonexty", fillcolor="rgba(0, 212, 170, 0.25)",
                showlegend=True, name="25th-75th Percentile"))
            fig_fan.add_trace(go.Scatter(
                x=steps, y=fan["50"], mode="lines",
                line=dict(color="#00D4AA", width=2), name="Median"))
            fig_fan.update_layout(
                title="Monte Carlo Fan Chart",
                xaxis_title="Trade #", yaxis_title="Equity ($)",
                template="plotly_dark")
            st.plotly_chart(fig_fan, use_container_width=True)

        st.dataframe(pd.DataFrame([mc]), use_container_width=True)
        mc_csv = pd.DataFrame([mc]).to_csv(index=False)
        st.download_button("📥 Export MC Results", mc_csv, "monte_carlo.csv", "text/csv", key="dl_mc")

# ── Alerts Tab ────────────────────────────────────────────────
with tab_alerts:
    st.subheader("Scanner Alerts")
    if scan_df.empty:
        st.info("No scan CSV found.")
    else:
        display_df = scan_df.copy()
        if "tier_label" in display_df.columns:
            tier_icons = {"TIER_1": "🔴", "TIER_2": "🟡", "NEAR_MISS": "⚪"}
            display_df["Signal"] = display_df["tier_label"].map(tier_icons).fillna("") + " " + display_df["tier_label"].fillna("")

        show_cols = [c for c in ["Signal", "symbol", "earnings_date", "strategies",
                                  "iv_rv_ratio", "ff_best", "tier_label", "filter_failures"]
                     if c in display_df.columns]
        st.dataframe(
            display_df[show_cols] if show_cols else display_df,
            use_container_width=True,
            column_config={
                "iv_rv_ratio": st.column_config.NumberColumn("IV/RV", format="%.2f"),
                "ff_best": st.column_config.NumberColumn("FF Best", format="%.2f"),
            },
        )
        csv_alerts = (display_df[show_cols] if show_cols else display_df).to_csv(index=False)
        st.download_button("📥 Export Alerts CSV", csv_alerts, "alerts.csv", "text/csv", key="dl_alerts")

# ── Config Tab ────────────────────────────────────────────────
with tab_config:
    st.subheader("⚙️ Scanner Configuration")

    config_path = Path("scanner_config.json")

    if config_path.exists():
        current_cfg = json.loads(config_path.read_text(encoding="utf-8"))
    else:
        from scanner.config import _DEFAULTS
        current_cfg = json.loads(json.dumps(_DEFAULTS))

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Strategy A (IV Crush)")
        sa_iv_rv = st.number_input(
            "IV/RV Minimum",
            value=float(current_cfg.get("strategy_a", {}).get("iv_rv_min", 1.25)),
            step=0.05,
            key="cfg_sa_iv_rv",
        )

        st.markdown("### Strategy B (Forward Factor)")
        sb_strong = st.number_input(
            "FF Strong Threshold",
            value=float(current_cfg.get("strategy_b", {}).get("ff_strong_threshold", 0.20)),
            step=0.05,
            key="cfg_sb_strong",
        )
        sb_moderate = st.number_input(
            "FF Moderate Threshold",
            value=float(current_cfg.get("strategy_b", {}).get("ff_moderate_threshold", 0.10)),
            step=0.05,
            key="cfg_sb_moderate",
        )

        st.markdown("### Strategy C (Skew)")
        sc_skew = st.number_input(
            "Put Skew Minimum",
            value=float(current_cfg.get("strategy_c", {}).get("put_skew_min", 1.3)),
            step=0.1,
            key="cfg_sc_skew",
        )

    with col2:
        st.markdown("### Hard Filters")
        hf_price = st.number_input(
            "Min Stock Price ($)",
            value=float(current_cfg.get("hard_filters", {}).get("min_price", 10.0)),
            step=1.0,
            key="cfg_hf_price",
        )
        hf_oi = st.number_input(
            "Min Open Interest",
            value=int(current_cfg.get("hard_filters", {}).get("min_open_interest", 2000)),
            step=100,
            key="cfg_hf_oi",
        )

        st.markdown("### Tiering")
        t_vol_pass = st.number_input(
            "Volume Pass Threshold",
            value=int(current_cfg.get("tiering", {}).get("volume_pass", 1500000)),
            step=100000,
            key="cfg_t_vol",
        )
        t_iv_rv = st.number_input(
            "IV/RV Pass",
            value=float(current_cfg.get("tiering", {}).get("iv_rv_pass", 1.25)),
            step=0.05,
            key="cfg_t_ivrv",
        )

    if st.button("💾 Save Configuration", key="save_cfg"):
        new_cfg = {
            "strategy_a": {"iv_rv_min": sa_iv_rv},
            "strategy_b": {
                "ff_strong_threshold": sb_strong,
                "ff_moderate_threshold": sb_moderate,
            },
            "strategy_c": {"put_skew_min": sc_skew},
            "hard_filters": {"min_price": hf_price, "min_open_interest": int(hf_oi)},
            "tiering": {"volume_pass": int(t_vol_pass), "iv_rv_pass": t_iv_rv},
        }
        config_path.write_text(json.dumps(new_cfg, indent=2), encoding="utf-8")
        st.success("✅ Configuration saved!")
        st.cache_data.clear()

    with st.expander("📝 View/Edit Raw JSON"):
        raw = st.text_area("scanner_config.json", json.dumps(current_cfg, indent=2), height=300, key="raw_cfg")
        if st.button("Save Raw JSON", key="save_raw"):
            try:
                parsed = json.loads(raw)
                config_path.write_text(json.dumps(parsed, indent=2), encoding="utf-8")
                st.success("✅ Raw JSON saved!")
            except json.JSONDecodeError as e:
                st.error(f"Invalid JSON: {e}")
