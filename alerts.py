"""Format Telegram alerts for daily scans and outcomes."""
import pandas as pd
import numpy as np


def format_daily_alert(df: pd.DataFrame) -> str:
    if df.empty:
        return "📊 Options Machine — No candidates found today."

    lines = [f"📊 Options Machine Scan — {pd.Timestamp.now().strftime('%b %d, %Y')}", ""]

    # Group by signal strength
    strong = df[df["strategies"].str.contains(",", na=False)]  # multi-strategy
    single = df[~df["strategies"].str.contains(",", na=False) & (df["strategies"] != "")]
    no_sig = df[df["strategies"] == ""]

    if not strong.empty:
        lines.append("🔴 STRONG (multi-strategy):")
        for _, r in strong.iterrows():
            d = r.to_dict()
            iv_rv = f"IV/RV: {d['iv_rv_ratio']:.2f}" if not np.isnan(d.get("iv_rv_ratio", float("nan"))) else ""
            ff = f"FF: {d.get('ff_best', d.get('forward_factor', float("nan"))):.2f}" if not np.isnan(d.get("ff_best", d.get("forward_factor", float("nan")))) else ""
            alloc = d.get("suggested_allocation_pct", float("nan"))
            alloc_txt = f"Alloc: {alloc*100:.1f}%" if not np.isnan(alloc) else ""
            parts = [p for p in [iv_rv, ff, alloc_txt] if p]
            advice = d.get("advice", "")
            lines.append(f"  • {d['symbol']} [{d['strategies']}] — {' | '.join(parts)} | Earnings {d['earnings_date']}")
            if advice:
                lines.append(f"    ↳ {advice}")
        lines.append("")

    if not single.empty:
        lines.append("🟡 MODERATE (single strategy):")
        for _, r in single.iterrows():
            d = r.to_dict()
            iv_rv = f"IV/RV: {d['iv_rv_ratio']:.2f}" if not np.isnan(d.get("iv_rv_ratio", float("nan"))) else ""
            advice = d.get("advice", "")
            alloc = d.get("suggested_allocation_pct", float("nan"))
            alloc_txt = f" | Alloc: {alloc*100:.1f}%" if not np.isnan(alloc) else ""
            lines.append(f"  • {d['symbol']} [{d['strategies']}] — {iv_rv}{alloc_txt} | Earnings {d['earnings_date']}")
            if advice:
                lines.append(f"    ↳ {advice}")
        lines.append("")

    lines.append("Strategy key: A=IV Crush, B=Calendar, C=Skew Vertical")
    lines.append("Safety note: Strategy A should use hold-through long calendars or defined-risk structures only (iron condor/iron fly).")
    return "\n".join(lines)


def format_outcome_alert(alerts: list[dict]) -> str:
    if not alerts:
        return ""
    lines = ["📈 Post-Earnings Outcomes:", ""]
    for a in alerts:
        emoji = "✅" if a["outcome"] == "win" else "❌"
        exp = f"{a['expected_move']:.1%}" if a.get("expected_move") else "?"
        act = f"{a['actual_move']:.1%}"
        lines.append(f"{emoji} {a['symbol']} — predicted {exp}, actual {act}")
    return "\n".join(lines)
