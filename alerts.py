"""Format Telegram/Discord alerts for daily scans and outcomes."""
import pandas as pd
import numpy as np
import requests


def format_daily_alert(df: pd.DataFrame) -> str:
    if df.empty:
        return "📊 Options Machine — No candidates found today."

    lines = [f"📊 Options Machine Scan — {pd.Timestamp.now().strftime('%b %d, %Y')}", ""]

    strong = df[df["strategies"].str.contains(",", na=False)]
    single = df[~df["strategies"].str.contains(",", na=False) & (df["strategies"] != "")]

    if not strong.empty:
        lines.append("🔴 STRONG (multi-strategy):")
        for _, r in strong.iterrows():
            d = r.to_dict()
            iv_rv = f"IV/RV: {d['iv_rv_ratio']:.2f}" if not np.isnan(d.get("iv_rv_ratio", float("nan"))) else ""
            ff_val = d.get("ff_best", d.get("forward_factor", float("nan")))
            ff = f"FF: {ff_val:.2f}" if not np.isnan(ff_val) else ""
            alloc = d.get("suggested_allocation_pct", float("nan"))
            alloc_txt = f"Alloc: {alloc*100:.1f}%" if not np.isnan(alloc) else ""
            parts = [p for p in [iv_rv, ff, alloc_txt] if p]
            lines.append(f"  • {d['symbol']} [{d['strategies']}] — {' | '.join(parts)} | Earnings {d['earnings_date']}")
        lines.append("")

    if not single.empty:
        lines.append("🟡 MODERATE (single strategy):")
        for _, r in single.iterrows():
            d = r.to_dict()
            iv_rv = f"IV/RV: {d['iv_rv_ratio']:.2f}" if not np.isnan(d.get("iv_rv_ratio", float("nan"))) else ""
            alloc = d.get("suggested_allocation_pct", float("nan"))
            alloc_txt = f" | Alloc: {alloc*100:.1f}%" if not np.isnan(alloc) else ""
            lines.append(f"  • {d['symbol']} [{d['strategies']}] — {iv_rv}{alloc_txt} | Earnings {d['earnings_date']}")
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


def format_trade_alert(row: dict, capital: float = 100000.0) -> str:
    symbol = row.get("symbol", "?")
    strategies = row.get("strategies", "-")
    earnings = row.get("earnings_date", "?")
    ivrv = row.get("iv_rv_ratio", float("nan"))
    ff = row.get("ff_best", row.get("forward_factor", float("nan")))
    alloc = row.get("suggested_allocation_pct", float("nan"))

    iv_txt = f"{ivrv:.2f}" if not pd.isna(ivrv) else "n/a"
    ff_txt = f"{ff:.2f}" if not pd.isna(ff) else "n/a"

    if pd.isna(alloc):
        alloc = 0.04
    alloc_usd = float(capital) * float(alloc)

    return (
        f"🚨 Trade Signal: {symbol}\n"
        f"Strategies: {strategies}\n"
        f"Earnings: {earnings}\n"
        f"IV/RV: {iv_txt} | FF: {ff_txt}\n"
        f"Suggested allocation: {float(alloc)*100:.1f}% (${alloc_usd:,.0f})"
    )


def send_discord_webhook(message: str, webhook_url: str) -> bool:
    if not webhook_url:
        return False
    resp = requests.post(webhook_url, json={"content": message})
    return 200 <= resp.status_code < 300
