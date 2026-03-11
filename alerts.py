"""Format Telegram/Discord alerts for daily scans and outcomes."""
import pandas as pd
import numpy as np
import requests

from scanner.regime import classify_regime, get_vix_level


def _strategy_a_action(d: dict, capital: float = 100000.0) -> str:
    """Generate Strategy A (IV Crush) action text with iron fly details."""
    iv_rv = d.get("iv_rv_ratio", float("nan"))
    em = d.get("expected_move_pct", float("nan"))
    avg_hist = d.get("avg_hist_move", float("nan"))
    iv_pct = d.get("iv_percentile_52w", float("nan"))
    event_premium = d.get("event_premium_pct", float("nan"))

    why_parts = []
    if not pd.isna(iv_rv):
        pct_above = (iv_rv - 1.0) * 100
        why_parts.append(f"IV is {pct_above:.0f}% above realized vol (IV/RV: {iv_rv:.2f})")
    if not pd.isna(iv_pct):
        why_parts.append(f"IV Percentile: {iv_pct*100:.0f}th")
    if not pd.isna(em) and not pd.isna(avg_hist) and avg_hist > 0:
        overpriced = ((em / avg_hist) - 1) * 100
        why_parts.append(
            f"Expected Move: {em*100:.1f}% vs Avg Historical: {avg_hist*100:.1f}% (overpriced by {overpriced:.0f}%)"
        )
    if not pd.isna(event_premium):
        why_parts.append(f"Event Premium: {event_premium*100:.0f}% above ambient vol")
    why = "\n   • ".join(why_parts) if why_parts else "IV/RV ratio elevated"

    if not pd.isna(iv_rv) and iv_rv >= 1.6:
        structure = "IRON FLY"
        note = "(wider wings for high-IV event risk)"
    else:
        structure = "IRON CONDOR"
        note = "(moderate IV premium)"

    action_parts = [f"Sell {structure} {note}"]

    alloc = d.get("suggested_allocation_pct", 0.04)
    if pd.isna(alloc):
        alloc = 0.04
    alloc_usd = capital * alloc

    return (
        f"📊 WHY: {why}\n"
        f"🎯 ACTION: {', '.join(action_parts)} (defined-risk only)\n"
        f"   • Expiry: 21-45 DTE (closest to 30 DTE)\n"
        f"   • Exit: Hold through earnings → IV crush → close for profit\n"
        f"💰 SIZING / Allocation: {alloc*100:.1f}% (${alloc_usd:,.0f} on ${capital:,.0f}) | Alloc: {alloc*100:.1f}%"
    )


def _strategy_b_action(d: dict, capital: float = 100000.0) -> str:
    """Generate Strategy B (Forward Factor Calendar) action text."""
    ff = d.get("ff_best", float("nan"))
    ff_pair = d.get("ff_best_pair", "?")
    ff_signal = d.get("ff_signal", "NONE")
    ff_z = d.get("ff_zscore", float("nan"))
    front_iv = d.get("front_iv", float("nan"))
    back_iv = d.get("back_iv", float("nan"))
    distorted = d.get("earnings_distortion_flag", False)

    why_parts = []
    if not pd.isna(front_iv) and not pd.isna(back_iv) and back_iv > 0:
        pct_above = ((front_iv / back_iv) - 1) * 100
        why_parts.append(
            f"Front IV ({front_iv*100:.1f}%) is {pct_above:.0f}% above back IV ({back_iv*100:.1f}%)"
        )
    if not pd.isna(ff):
        why_parts.append(f"FF Best: {ff:.2f} ({ff_signal})")
    if not pd.isna(ff_z):
        why_parts.append(f"Z-Score: {ff_z:.1f}σ")
    if distorted:
        why_parts.append("⚠️ Earnings distortion present")
    else:
        why_parts.append("No earnings distortion")
    why = "\n   • ".join(why_parts) if why_parts else "Forward factor elevated"

    alloc = d.get("suggested_allocation_pct", 0.04)
    if pd.isna(alloc):
        alloc = 0.04
    alloc_usd = capital * alloc

    return (
        f"📊 WHY: {why}\n"
        f"🎯 ACTION: Buy CALENDAR SPREAD (ATM)\n"
        f"   • Tenor pair: {ff_pair} — sell front-month ATM call, buy back-month ATM call\n"
        f"   • Exit: When FF < 5% (mean revert) OR stop-loss -20% OR after 10 days\n"
        f"💰 SIZING / Allocation: {alloc*100:.1f}% (${alloc_usd:,.0f}) | Alloc: {alloc*100:.1f}% {'⚠️ Reduced for earnings distortion' if distorted else ''}"
    )


def _strategy_c_action(d: dict, capital: float = 100000.0) -> str:
    """Generate Strategy C (Skew Vertical) action text."""
    put_skew = d.get("put_skew", float("nan"))
    rv_edge = d.get("rv_edge_put", float("nan"))
    mom_dir = d.get("momentum_dir", "NEUTRAL")
    mom_pct = d.get("momentum_pct", float("nan"))
    otm_put_strike = d.get("otm_put_strike", float("nan"))

    why_parts = []
    if not pd.isna(put_skew):
        pct_above = (put_skew - 1.0) * 100
        why_parts.append(f"25Δ put IV is {pct_above:.0f}% above ATM IV (skew: {put_skew:.2f})")
    if not pd.isna(rv_edge):
        why_parts.append(f"RV Edge: +{rv_edge*100:.1f}%")
    if not pd.isna(mom_pct):
        why_parts.append(f"Momentum: {mom_dir} ({mom_pct*100:+.1f}% in 20 days)")
    why = "\n   • ".join(why_parts) if why_parts else "Rich put skew detected"

    alloc = d.get("suggested_allocation_pct", 0.04)
    if pd.isna(alloc):
        alloc = 0.04
    alloc_usd = capital * alloc

    stop_mult = d.get("stop_loss_multiplier", 1.0)
    if pd.isna(stop_mult):
        stop_mult = 1.0
    adjusted_stop = -50 * float(stop_mult)

    strike_info = ""
    if not pd.isna(otm_put_strike):
        strike_info = f"   • SELL: ${otm_put_strike:.0f}P (25Δ) — buy next strike down for protection\n"

    return (
        f"📊 WHY: {why}\n"
        f"🎯 ACTION: Sell PUT CREDIT SPREAD (~30 DTE)\n"
        f"{strike_info}"
        f"   • Exit: Stop-loss at {adjusted_stop:.0f}% max loss OR after 10 days\n"
        f"💰 SIZING / Allocation: {alloc*100:.1f}% (${alloc_usd:,.0f}) | Alloc: {alloc*100:.1f}%"
    )


def format_trade_alert(row: dict, capital: float = 100000.0, iron_fly: dict | None = None) -> str:
    symbol = row.get("symbol", "?")
    strategies = row.get("strategies", "-")
    earnings = row.get("earnings_date", "?")
    days_to = row.get("days_to_earnings", "?")
    tier = row.get("tier_label", "")
    tier_icon = {"TIER_1": "🔴", "TIER_2": "🟡", "NEAR_MISS": "⚪"}.get(tier, "📊")
    strat_set = {x.strip() for x in (strategies or "").split(",") if x.strip()}

    strat_names = []
    if "A" in strat_set:
        strat_names.append("IV CRUSH")
    if "B" in strat_set:
        strat_names.append("FORWARD FACTOR")
    if "C" in strat_set:
        strat_names.append("RICH SKEW")
    header_name = " + ".join(strat_names) if strat_names else "WATCH"

    lines = [
        f"{tier_icon} {symbol} — {header_name}",
        "━" * 40,
        f"📅 Earnings: {earnings} ({days_to} days)",
        "",
    ]

    if "A" in strat_set:
        lines.append(_strategy_a_action(row, capital))
        if iron_fly and not iron_fly.get("error"):
            lines.append("\n📐 Iron Fly Detail:")
            lines.append(f"   SHORT: ${iron_fly['short_put_strike']}P / ${iron_fly['short_call_strike']}C")
            lines.append(f"   LONG:  ${iron_fly['long_put_strike']}P / ${iron_fly['long_call_strike']}C")
            lines.append(f"   Credit: ${iron_fly['net_credit']} | Max loss: ${iron_fly['max_loss']}")
            lines.append(f"   Break-evens: {iron_fly['lower_breakeven']} — {iron_fly['upper_breakeven']}")
        lines.append("")

    if "B" in strat_set:
        lines.append(_strategy_b_action(row, capital))
        lines.append("")

    if "C" in strat_set:
        lines.append(_strategy_c_action(row, capital))
        lines.append("")

    return "\n".join(lines)


def format_daily_alert(df: pd.DataFrame, capital: float = 100000.0) -> str:
    if df.empty:
        return "📊 Options Machine — No candidates found today."

    lines = [f"📊 Options Machine Scan — {pd.Timestamp.now().strftime('%b %d, %Y')}", ""]

    vix = get_vix_level()
    if not pd.isna(vix):
        regime = classify_regime(vix)
        lines.append(f"📈 VIX: {vix:.1f} — {regime['regime']} ({regime['note']})")
        lines.append("")

    if "tier" in df.columns:
        tier1 = df[df["tier"] == 1]
        tier2 = df[df["tier"] == 2]
        near_miss = df[df["tier"] == 3]
    else:
        tier1 = df[df["strategies"].str.contains(",", na=False)]
        tier2 = df[~df["strategies"].str.contains(",", na=False) & (df["strategies"] != "")]
        near_miss = pd.DataFrame()

    if not tier1.empty:
        lines.append("═══ TIER 1 — HIGH CONVICTION ═══")
        lines.append("")
        for _, r in tier1.iterrows():
            lines.append(format_trade_alert(r.to_dict(), capital))
            lines.append("")

    if not tier2.empty:
        lines.append("═══ TIER 2 — ONE FILTER NEAR-MISS ═══")
        lines.append("")
        for _, r in tier2.iterrows():
            lines.append(format_trade_alert(r.to_dict(), capital))
            lines.append("")

    if not near_miss.empty:
        lines.append("═══ WATCH LIST ═══")
        for _, r in near_miss.iterrows():
            d = r.to_dict()
            reason = d.get("filter_failures", "")
            lines.append(f"  ⚪ {d.get('symbol', '?')} — {reason}")
        lines.append("")

    lines.append("A=IV Crush (iron condor/fly) | B=Calendar (forward factor) | C=Put credit spread (skew)")
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


def send_discord_webhook(message: str, webhook_url: str) -> bool:
    if not webhook_url:
        return False
    resp = requests.post(webhook_url, json={"content": message})
    return 200 <= resp.status_code < 300
