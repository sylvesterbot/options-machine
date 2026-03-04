from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Options Machine Dashboard", layout="wide")
st.title("Options Machine Dashboard")


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

tab_overview, tab_backtest, tab_mc, tab_alerts = st.tabs(["Overview", "Backtest", "Monte Carlo", "Alerts"])

with tab_overview:
    c1, c2, c3 = st.columns(3)
    trades = int(len(backtest_df)) if not backtest_df.empty else 0
    total_return = 0.0
    if not backtest_df.empty and "return_pct" in backtest_df.columns:
        eq = (1 + pd.to_numeric(backtest_df["return_pct"], errors="coerce").fillna(0)).cumprod()
        if len(eq) > 0:
            total_return = float(eq.iloc[-1] - 1.0)

    c1.metric("Trades", trades)
    c2.metric("Backtest Total Return", f"{total_return*100:.2f}%")
    c3.metric("Scanner Signals", int(len(scan_df)) if not scan_df.empty else 0)

    if not backtest_df.empty:
        st.dataframe(backtest_df.tail(50), use_container_width=True)

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
        st.dataframe(backtest_df, use_container_width=True)

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
            fan_df = pd.DataFrame({
                "step": list(range(len(fan.get("50", [])))),
                "p5": fan.get("5", []),
                "p25": fan.get("25", []),
                "p50": fan.get("50", []),
                "p75": fan.get("75", []),
                "p95": fan.get("95", []),
            })
            long = fan_df.melt(id_vars=["step"], var_name="percentile", value_name="equity")
            fig = px.line(long, x="step", y="equity", color="percentile", title="Monte Carlo Fan Chart")
            st.plotly_chart(fig, use_container_width=True)
        st.dataframe(pd.DataFrame([mc]), use_container_width=True)

with tab_alerts:
    st.subheader("Alerts")
    if scan_df.empty:
        st.info("No scan CSV found.")
    else:
        show_cols = [c for c in ["symbol", "earnings_date", "strategies", "iv_rv_ratio", "forward_factor", "ff_best"] if c in scan_df.columns]
        alerts_df = scan_df[show_cols].copy() if show_cols else scan_df.copy()
        st.dataframe(alerts_df, use_container_width=True)
