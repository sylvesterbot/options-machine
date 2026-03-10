from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from alerts import format_trade_alert

st.set_page_config(page_title="Options Machine Dashboard", layout="wide")
st.title("Options Machine Dashboard")

try:
    from scanner.regime import classify_regime, get_vix_level

    _vix = get_vix_level()
    if not pd.isna(_vix):
        _regime = classify_regime(_vix)
        _color_map = {"CALM": "🟢", "NORMAL": "🔵", "ELEVATED": "🟡", "CRISIS": "🔴"}
        _icon = _color_map.get(_regime["regime"], "⚪")
        st.markdown(
            f'<div style="background:rgba(0,212,170,0.08);border-radius:8px;padding:8px 16px;'
            f'margin-bottom:16px;display:inline-block;">'
            f'{_icon} <strong>VIX: {_vix:.1f}</strong> — {_regime["regime"]} '
            f'<span style="opacity:0.7;">({_regime["note"]})</span></div>',
            unsafe_allow_html=True,
        )
except Exception:
    pass

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #1A1F2E 0%, #252B3B 100%);
        border: 1px solid rgba(0, 212, 170, 0.2);
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    }
    [data-testid="stMetricLabel"] { font-size: 0.85rem; color: #8B95A5; }
    [data-testid="stMetricValue"] { font-size: 1.6rem; font-weight: 700; }

    .stTabs [data-baseweb="tab"] {
        font-weight: 600;
        font-size: 1rem;
        padding: 10px 24px;
    }

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

    .stDownloadButton > button {
        background: transparent;
        border: 1px solid #00D4AA;
        color: #00D4AA;
        border-radius: 8px;
    }

    [data-testid="stSidebar"] {
        background: #0A0D14;
        border-right: 1px solid rgba(0, 212, 170, 0.1);
    }

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
            years = (dates.max() - dates.min()).days / 365.25 if dates.notna().any() else 0
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
        st.download_button("📥 Export Overview", backtest_df.to_csv(index=False), "overview.csv", "text/csv", key="dl_overview")

    if not scan_df.empty:
        st.subheader("Scanner Snapshot")
        display_cols = [
            "symbol",
            "earnings_date",
            "days_to_earnings",
            "strategies",
            "tier_label",
            "iv_rv_ratio",
            "ff_best",
            "put_skew",
            "event_vol",
            "event_premium_pct",
            "suggested_allocation_pct",
        ]
        display_cols = [c for c in display_cols if c in scan_df.columns]
        st.dataframe(scan_df[display_cols] if display_cols else scan_df, use_container_width=True)

# ── Backtest Tab ──────────────────────────────────────────────
with tab_backtest:
    st.subheader("⚡ Backtest Runner")

    col_left, col_right = st.columns([2, 1])

    with col_right:
        st.markdown("### Run New Backtest")
        strategy_choice = st.selectbox("Strategy", ["strategy_b", "strategy_c"], key="bt_strategy")
        bt_holding = st.slider("Holding Days", 1, 14, 5, key="bt_hold")
        bt_stop = st.slider("Stop-Loss %", 0, 50, 30, key="bt_stop")
        bt_kelly = st.checkbox("Use Kelly Sizing", value=True, key="bt_kelly")
        bt_min_trades = st.number_input("Kelly Min Trades", 5, 200, 30, key="bt_min_trades")

        if st.button("🚀 Run Backtest", key="run_bt"):
            cmd = [
                sys.executable,
                "backtests/run_walkforward.py",
                "--strategy", strategy_choice,
                "--holding-days", str(bt_holding),
                "--stop-loss-pct", str(bt_stop / 100),
            ]
            if bt_kelly:
                cmd.extend(["--use-kelly", "--kelly-min-trades", str(bt_min_trades)])
            with st.spinner("Running backtest..."):
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=".", timeout=240)
            if result.returncode == 0:
                st.success("✅ Backtest complete!")
                stdout_tail = result.stdout[-500:] if len(result.stdout) > 500 else result.stdout
                st.code(stdout_tail)
                st.cache_data.clear()
                st.rerun()
            else:
                stderr_tail = result.stderr[-500:] if len(result.stderr) > 500 else result.stderr
                st.error(f"❌ Error:\n{stderr_tail}")

    with col_left:
        if backtest_df.empty:
            st.info("No backtest CSV found. Run a backtest or load a CSV.")
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

                fig = px.line(bt, x="x", y="eq", title="Equity Curve", template="plotly_dark")
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)

                bt["return_pct_num"] = pd.to_numeric(bt["return_pct"], errors="coerce")
                bt["color"] = bt["return_pct_num"].apply(lambda x: "green" if x > 0 else "red")
                bt["trade_num"] = range(len(bt))
                fig_bar = px.bar(
                    bt,
                    x="trade_num",
                    y="return_pct_num",
                    color="color",
                    color_discrete_map={"green": "#00D4AA", "red": "#FF4B4B"},
                    title="Per-Trade Returns",
                    template="plotly_dark",
                )
                fig_bar.update_layout(showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_bar, use_container_width=True)

            st.download_button("📥 Export Backtest CSV", backtest_df.to_csv(index=False), "backtest_trades.csv", "text/csv")
            st.dataframe(backtest_df, use_container_width=True)
            if "exit_reason" in backtest_df.columns:
                exit_counts = backtest_df["exit_reason"].value_counts()
                st.subheader("Exit Reason Distribution")
                st.bar_chart(exit_counts)

# ── Monte Carlo Tab ───────────────────────────────────────────
with tab_mc:
    st.subheader("🎲 Monte Carlo Simulation")

    col_ctrl, col_chart = st.columns([1, 3])

    with col_ctrl:
        st.markdown("### Run Simulation")
        mc_strategy = st.selectbox("Strategy", ["strategy_b", "strategy_c"], key="mc_strat")
        mc_sims = st.slider("Simulations", 100, 10000, 1000, step=100, key="mc_sims")
        mc_capital = st.number_input("Starting Capital ($)", value=100000, step=10000, key="mc_cap")

        if st.button("🎲 Run Monte Carlo", key="run_mc"):
            cmd = [
                sys.executable,
                "-m",
                "backtests.monte_carlo",
                "--trades-csv",
                backtest_path,
                "--n-simulations",
                str(mc_sims),
                "--initial-capital",
                str(mc_capital),
                "--out",
                mc_path,
            ]
            with st.spinner(f"Running Monte Carlo simulation for {mc_strategy}..."):
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=".", timeout=240)
            if result.returncode == 0:
                st.success("✅ Simulation complete!")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(f"Error: {(result.stderr or result.stdout)[-300:]}")

        mc = load_json(mc_path)
        if mc:
            st.markdown("---")
            st.metric("Median Return", f"{mc.get('median_return', 0.0)*100:.1f}%")
            st.metric("P5 (Worst Case)", f"{mc.get('p5_return', 0.0)*100:.1f}%")
            st.metric("P95 (Best Case)", f"{mc.get('p95_return', 0.0)*100:.1f}%")
            prob_profit = mc.get("prob_profit", None)
            if prob_profit is not None:
                st.metric("Prob. of Profit", f"{prob_profit*100:.0f}%")

    with col_chart:
        if not mc:
            st.info("No Monte Carlo results. Run a simulation to see the fan chart.")
        else:
            fan = mc.get("fan_chart", {})
            if fan:
                fig_fan = go.Figure()
                steps = list(range(len(fan.get("50", []))))

                fig_fan.add_trace(go.Scatter(x=steps, y=fan.get("95", []), mode="lines", line=dict(width=0), showlegend=False, name="P95"))
                fig_fan.add_trace(go.Scatter(x=steps, y=fan.get("5", []), mode="lines", line=dict(width=0), fill="tonexty", fillcolor="rgba(0, 212, 170, 0.1)", showlegend=True, name="5th-95th Percentile"))
                fig_fan.add_trace(go.Scatter(x=steps, y=fan.get("75", []), mode="lines", line=dict(width=0), showlegend=False, name="P75"))
                fig_fan.add_trace(go.Scatter(x=steps, y=fan.get("25", []), mode="lines", line=dict(width=0), fill="tonexty", fillcolor="rgba(0, 212, 170, 0.25)", showlegend=True, name="25th-75th Percentile"))
                fig_fan.add_trace(go.Scatter(x=steps, y=fan.get("50", []), mode="lines", line=dict(color="#00D4AA", width=2), name="Median"))
                fig_fan.update_layout(
                    title="Monte Carlo Fan Chart",
                    xaxis_title="Trade #",
                    yaxis_title="Equity ($)",
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    height=500,
                )
                st.plotly_chart(fig_fan, use_container_width=True)

            st.download_button("📥 Export MC Results", pd.DataFrame([mc]).to_csv(index=False), "monte_carlo.csv", "text/csv", key="dl_mc")

# ── Alerts Tab ────────────────────────────────────────────────
with tab_alerts:
    st.subheader("🔔 Scanner Alerts")
    if scan_df.empty:
        st.info("No scan CSV found. Run a scan first.")
    else:
        filter_col1, filter_col2, filter_col3 = st.columns(3)
        tier_filter = []
        strat_filter = []
        with filter_col1:
            if "tier_label" in scan_df.columns:
                tier_filter = st.multiselect(
                    "Filter by Tier",
                    options=["TIER_1", "TIER_2", "NEAR_MISS", ""],
                    default=["TIER_1", "TIER_2"],
                    key="alert_tier_filter",
                )
        with filter_col2:
            if "strategies" in scan_df.columns:
                strat_filter = st.multiselect(
                    "Filter by Strategy",
                    options=["A", "B", "C"],
                    default=["A", "B", "C"],
                    key="alert_strat_filter",
                )
        with filter_col3:
            sort_by = st.selectbox("Sort By", ["iv_rv_ratio", "ff_best", "symbol", "earnings_date"], key="alert_sort")

        filtered = scan_df.copy()
        if "tier_label" in filtered.columns and tier_filter:
            filtered = filtered[filtered["tier_label"].isin(tier_filter)]
        if "strategies" in filtered.columns and strat_filter:
            mask = filtered["strategies"].apply(lambda s: any(x in str(s) for x in strat_filter) if pd.notna(s) else False)
            filtered = filtered[mask]
        if sort_by in filtered.columns:
            filtered = filtered.sort_values(sort_by, ascending=False)

        st.caption(f"Showing {len(filtered)} alerts")
        for _, row in filtered.iterrows():
            row_dict = row.to_dict()
            alert_text = format_trade_alert(row_dict, capital=100000.0)
            tier = row_dict.get("tier_label", "")
            css_class = {"TIER_1": "tier-1", "TIER_2": "tier-2", "NEAR_MISS": "near-miss"}.get(tier, "")
            safe_text = alert_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            st.markdown(
                f'<div class="alert-card {css_class}" style="padding:16px;margin:8px 0;'
                f'border-radius:8px;white-space:pre-wrap;font-family:monospace;font-size:13px;">'
                f'{safe_text}</div>',
                unsafe_allow_html=True,
            )

        st.download_button("📥 Export Filtered Alerts", filtered.to_csv(index=False), "filtered_alerts.csv", "text/csv", key="dl_alerts")

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
        sa_iv_rv = st.number_input("IV/RV Minimum", value=float(current_cfg.get("strategy_a", {}).get("iv_rv_min", 1.25)), step=0.05, key="cfg_sa_iv_rv")

        st.markdown("### Strategy B (Forward Factor)")
        sb_strong = st.number_input("FF Strong Threshold", value=float(current_cfg.get("strategy_b", {}).get("ff_strong_threshold", 0.20)), step=0.05, key="cfg_sb_strong")
        sb_moderate = st.number_input("FF Moderate Threshold", value=float(current_cfg.get("strategy_b", {}).get("ff_moderate_threshold", 0.10)), step=0.05, key="cfg_sb_moderate")

        st.markdown("### Strategy C (Skew)")
        sc_skew = st.number_input("Put Skew Minimum", value=float(current_cfg.get("strategy_c", {}).get("put_skew_min", 1.3)), step=0.1, key="cfg_sc_skew")

    with col2:
        st.markdown("### Hard Filters")
        hf_price = st.number_input("Min Stock Price ($)", value=float(current_cfg.get("hard_filters", {}).get("min_price", 10.0)), step=1.0, key="cfg_hf_price")
        hf_oi = st.number_input("Min Open Interest", value=int(current_cfg.get("hard_filters", {}).get("min_open_interest", 2000)), step=100, key="cfg_hf_oi")

        st.markdown("### Tiering")
        t_vol_pass = st.number_input("Volume Pass Threshold", value=int(current_cfg.get("tiering", {}).get("volume_pass", 1500000)), step=100000, key="cfg_t_vol")
        t_iv_rv = st.number_input("IV/RV Pass", value=float(current_cfg.get("tiering", {}).get("iv_rv_pass", 1.25)), step=0.05, key="cfg_t_ivrv")

    if st.button("💾 Save Configuration", key="save_cfg"):
        new_cfg = {
            "strategy_a": {"iv_rv_min": sa_iv_rv},
            "strategy_b": {"ff_strong_threshold": sb_strong, "ff_moderate_threshold": sb_moderate},
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
