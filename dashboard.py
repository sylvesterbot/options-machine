from __future__ import annotations

from pathlib import Path
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Options Machine Dashboard", layout="wide")
st.title("Options Machine Dashboard")

DEFAULT_FILES = [
    "outputs/spy_baseline.csv",
    "outputs/spy_regime_filtered.csv",
    "outputs/spy_kelly.csv",
    "outputs/spy_full.csv",
]


def summarize(df: pd.DataFrame) -> dict:
    if df.empty or "return_pct" not in df.columns:
        return {"trades": 0, "total_return": 0.0, "avg_return": 0.0}
    r = pd.to_numeric(df["return_pct"], errors="coerce").dropna()
    if r.empty:
        return {"trades": 0, "total_return": 0.0, "avg_return": 0.0}
    eq = (1 + r).cumprod()
    return {"trades": len(r), "total_return": float(eq.iloc[-1] - 1), "avg_return": float(r.mean())}

rows = []
for fp in DEFAULT_FILES:
    p = Path(fp)
    if p.exists():
        d = pd.read_csv(p)
        s = summarize(d)
        rows.append({"file": fp, **s})

if not rows:
    st.warning("No output CSV files found yet.")
else:
    table = pd.DataFrame(rows)
    st.dataframe(table)

    for r in rows:
        fp = r["file"]
        st.subheader(fp)
        d = pd.read_csv(fp)
        if "return_pct" in d.columns and not d.empty:
            eq = (1 + pd.to_numeric(d["return_pct"], errors="coerce").fillna(0)).cumprod()
            st.line_chart(eq)
