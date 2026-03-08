"""Format Telegram/Discord alerts for daily scans and outcomes."""
import pandas as pd
import numpy as np
import requests


def format_daily_alert(df: pd.DataFrame) -> str:
    if df.empty:
        return "📊 Options Machine — No candidates found today."

    lines = [f"📊 Options Machine Scan — {pd.Timestamp.now().strftime('%b %d, %Y')}", ""]

    def _fmt_row(lines_list, d):
        iv_rv = f"IV/RV: {d['iv_rv_ratio']:.2f}" if not np.isnan(d.get("iv_rv_ratio", float("nan"))) else ""
        ff_val = d.get("ff_best", d.get("forward_factor", float("nan")))
        ff = f"FF: {ff_val:.2f}" if not np.isnan(ff_val) else ""
        alloc = d.get("suggested_allocation_pct", float("nan"))
        alloc_txt = f"Alloc: {alloc*100:.1f}%" if not np.isnan(alloc) else ""
        parts = [p for p in [iv_rv, ff, alloc_txt] if p]
        lines_list.append(f"  • {d['symbol']} [{d.get('strategies', '-')}] — {' | '.join(parts)} | Earnings {d['earnings_date']}")

    if "tier" in df.columns:
        tier1 = df[df["tier"] == 1]
        tier2 = df[df["tier"] == 2]
        near_miss = df[df["tier"] == 3]
    else:
        tier1 = df[df["strategies"].str.contains(",", na=False)]
        tier2 = df[~df["strategies"].str.contains(",", na=False) & (df["strategies"] != "")]
        near_miss = pd.DataFrame()

    if not tier1.empty:
        lines.append("🔴 TIER_1 — RECOMMENDED TRADES:")
        for _, r in tier1.iterrows():
            _fmt_row(lines, r.to_dict())
        lines.append("")

    if not tier2.empty:
        lines.append("🟡 TIER 2 — ONE NEAR-MISS FILTER:")
        for _, r in tier2.iterrows():
            _fmt_row(lines, r.to_dict())
        lines.append("")

    if not near_miss.empty:
        lines.append("⚪ NEAR MISSES — WATCH LIST:")
        for _, r in near_miss.iterrows():
            d = r.to_dict()
            reason = d.get("filter_failures", "")
            lines.append(f"  • {d['symbol']} [{d.get('strategies', '-')}] — {reason}")
        lines.append("")

    lines.append("Strategy key: A=IV Crush, B=Calendar, C=Skew Vertical")
    lines.append("Safety note: Strategy A should use defined-risk structures only (iron condor/iron fly).")
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


def format_trade_alert(row: dict, capital: float = 100000.0, iron_fly: dict | None = None) -> str:
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

    msg = (
        f"🚨 Trade Signal: {symbol}\n"
        f"Strategies: {strategies}\n"
        f"Earnings: {earnings}\n"
        f"IV/RV: {iv_txt} | FF: {ff_txt}\n"
        f"Suggested allocation: {float(alloc)*100:.1f}% (${alloc_usd:,.0f})"
    )

    if iron_fly and not iron_fly.get("error"):
        msg += (
            f"\n\n📐 Iron Fly:\n"
            f"  SHORT: ${iron_fly['short_put_strike']}P / ${iron_fly['short_call_strike']}C\n"
            f"  Credit: ${iron_fly['net_credit']} | Max loss: ${iron_fly['max_loss']}\n"
            f"  Break-evens: {iron_fly['lower_breakeven']} - {iron_fly['upper_breakeven']}\n"
            f"  Risk:Reward = 1:{iron_fly['risk_reward_ratio']}"
        )

    return msg


def send_discord_webhook(message: str, webhook_url: str) -> bool:
    if not webhook_url:
        return False
    resp = requests.post(webhook_url, json={"content": message})
    return 200 <= resp.status_code < 300
