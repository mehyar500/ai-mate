"""Offline planning scenarios. No API calls, billing or credentials."""
import argparse
import copy
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load():
    return json.loads((ROOT / "config/economics.json").read_text(encoding="utf-8"))


def validate(c):
    a, rates, plans = c["assumptions_not_vendor_quotes"], c["published_rates"], c["plans"]
    for group in (a, rates):
        for key, value in group.items():
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value < 0:
                raise ValueError(f"{key} must be a finite nonnegative number")
    for key in ("billable_utilization", "clip_success_fraction"):
        if not 0 < a[key] <= 1:
            raise ValueError(f"{key} must be in (0, 1]")
    for key in ("processor_fraction", "refund_chargeback_loss_fraction", "reserve_fraction"):
        if a[key] > 1:
            raise ValueError(f"{key} cannot exceed 1")
    if a["concurrent_calls_per_gpu"] < 1 or a["clips_per_pack"] < 1 or a["topup_minutes"] <= 0:
        raise ValueError("Capacity and pack sizes must be positive")
    if not plans or not math.isclose(sum(p["share"] for p in plans), 1):
        raise ValueError("Plan shares must sum to 1")
    for p in plans:
        if not all(not isinstance(p[k], bool) and isinstance(p[k], (int, float)) and math.isfinite(p[k]) and p[k] >= 0 for k in ("monthly_price", "live_minutes", "share")) or p["monthly_price"] == 0 or p["live_minutes"] == 0:
            raise ValueError("Invalid paid plan")
    if a["cohort_new_free_users"] > a["cohort_free_users"] or a["cohort_new_payers"] > a["cohort_payers"]:
        raise ValueError("New users cannot exceed cohort totals")
    b = c["competitor_reference"]
    values = [b[k] for k in ("customer_wire_usd_per_token", "wire_minimum_purchase_usd", "performer_usd_per_token")] + b["private_tokens_per_minute"]
    if not all(not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v) and v > 0 for v in values):
        raise ValueError("Competitor rates must be finite positive numbers")


def calculate(c):
    validate(c)
    a, r = c["assumptions_not_vendor_quotes"], c["published_rates"]
    llm_min = (a["call_turns_per_minute"] * a["call_input_tokens_per_turn"] * r["llm_input_per_million"] + a["call_output_tokens_per_minute"] * r["llm_output_per_million"]) / 1e6
    media_min = a["aggregate_sfu_egress_mbps"] * 60 / 8000 * r["sfu_per_gb"]
    gpu_min = (a["gpu_per_hour"] + a["vm_extras_per_hour"]) / (60 * a["billable_utilization"] * a["concurrent_calls_per_gpu"])
    local_min = (gpu_min + media_min + a["call_misc_per_minute"]) * (1 + a["variable_cost_buffer"])
    # Managed speech + LLM replaces local speech/LLM. Its avatar still needs GPU.
    managed_voice = (llm_min + r["streaming_asr_per_minute"] + a["tts_characters_per_minute"] / 1000 * r["tts_per_thousand_characters"] + media_min + a["call_misc_per_minute"]) * (1 + a["variable_cost_buffer"])
    guard_per_exchange = (a["guard_input_tokens_per_exchange"] * r["guard_input_per_million"] + a["guard_output_tokens_per_exchange"] * r["guard_output_per_million"]) / 1e6
    managed_voice += guard_per_exchange * a["call_turns_per_minute"] * (1 + a["variable_cost_buffer"])
    managed_avatar = managed_voice + gpu_min * (1 + a["variable_cost_buffer"])
    chat = (a["chat_input_tokens"] * r["llm_input_per_million"] + a["chat_output_tokens"] * r["llm_output_per_million"] + a["guard_input_tokens_per_exchange"] * r["guard_input_per_million"] + a["guard_output_tokens_per_exchange"] * r["guard_output_per_million"]) / 1e6
    free = chat * a["free_monthly_messages"] + a["profile_storage_asset_monthly"]
    paid_text = max(chat, a["local_adult_text_per_message_including_safety"]) * a["paid_monthly_messages"] + a["profile_storage_asset_monthly"]

    def net(price):
        return price * (1 - a["processor_fraction"] - a["refund_chargeback_loss_fraction"]) - a["processor_fixed_per_payment"]

    plans = []
    for p in c["plans"]:
        cost = paid_text + p["live_minutes"] * local_min + a["support_per_payer_monthly"]
        contribution = net(p["monthly_price"]) - cost
        plans.append(dict(p, variable_cost=cost, contribution=contribution, contribution_margin=contribution / p["monthly_price"], cash_before_fixed=contribution - p["monthly_price"] * a["reserve_fraction"]))
    avg = sum(p["share"] * p["contribution"] for p in plans)
    gross = a["cohort_payers"] * sum(p["share"] * p["monthly_price"] for p in plans)
    surplus = a["cohort_payers"] * avg - a["cohort_free_users"] * free - a["monthly_fixed_excluding_gpu"]
    clip = ((a["gpu_per_hour"] + a["vm_extras_per_hour"]) * a["clip_gpu_seconds_per_attempt"] / 3600 / a["clip_success_fraction"] + a["clip_other_per_delivered"]) * (1 + a["variable_cost_buffer"])
    return dict(local_per_minute=local_min, gpu_per_minute=gpu_min, media_per_minute=media_min, managed_llm_per_minute=llm_min, managed_voice_per_minute=managed_voice, managed_avatar_per_minute=managed_avatar, free_user_monthly=free, paid_text_monthly=paid_text, plans=plans, weighted_contribution=avg, cohort_gross=gross, cohort_surplus=surplus, cohort_cash_before_age_and_tax=surplus - gross * a["reserve_fraction"], cohort_first_month_age_cost=(a["cohort_new_payers"] + a["cohort_new_free_users"]) * a["age_check_per_user"], break_even_payers=math.ceil((a["monthly_fixed_excluding_gpu"] + a["cohort_free_users"] * free) / avg) if avg > 0 else None, clip_cost=clip, clip_pack_contribution=net(a["clip_pack_price"]) - a["clips_per_pack"] * clip, topup_contribution=net(a["topup_price"]) - a["topup_minutes"] * local_min)


def report(c):
    a,d=c["assumptions_not_vendor_quotes"],calculate(c)
    b=c["competitor_reference"]
    tokens=a["call_turns_per_minute"]*a["call_input_tokens_per_turn"]
    rows=["# Prices, costs and savings", "", f"USD, {c['as_of']}. Generated from [config](../config/economics.json); assumptions, not measured earnings.", "",
        f"Free: portrait, {a['free_monthly_messages']:g} clean exchanges/month, daily ceiling {math.ceil(a['free_monthly_messages']/30)}, prerecorded voice sample. Paid: {a['paid_monthly_messages']:g} exchanges/month plus calls below. Adult service only in approved states and advertised hours.", "",
        "| Plan | Monthly price | Minutes | Full-use contribution | Margin before fixed costs |", "|---|---:|---:|---:|---:|"]
    for p in d["plans"]:
        rows.append(f"| {p['name']} | ${p['monthly_price']:.2f} | {p['live_minutes']} | ${p['contribution']:.2f} | {p['contribution_margin']:.1%} |")
    rows += ["",f"Top-up ${a['topup_price']:.2f}/{a['topup_minutes']} minutes. Clip pack ${a['clip_pack_price']:.2f}/{a['clips_per_pack']} delivered videos. Minutes include listening. No rollover/automatic overage; disclose expiry, pause pilot deductions on degradation, restore failed clips.", "",
        "## Our call cost", "", "| Route | Cost/min | 30 min | 60 min |", "|---|---:|---:|---:|"]
    for name,key in (("Local GPU","local_per_minute"),("Cloudflare voice/portrait","managed_voice_per_minute"),("Cloudflare voice/GPU face","managed_avatar_per_minute")):
        v=d[key]
        rows.append(f"| {name} | ${v:.4f} | ${v*30:.2f} | ${v*60:.2f} |")
    rows += ["",f"Assumed (${a['gpu_per_hour']:.2f} GPU + ${a['vm_extras_per_hour']:.2f} VM extras)/hour; {a['billable_utilization']:.0%} utilization; {a['concurrent_calls_per_gpu']:g} call/GPU. Add ${d['media_per_minute']:.6f}/minute media, ${a['call_misc_per_minute']:.3f} other cost, {a['variable_cost_buffer']:.0%} contingency. Local tokens have no separate API bill.",
        f"Hosted context: {tokens:,.0f} input tokens/minute; thirty minutes {tokens*30:,.0f} input + {a['call_output_tokens_per_minute']*30:,.0f} output; sixty {tokens*60:,.0f} + {a['call_output_tokens_per_minute']*60:,.0f}. Repeated history counts. Speech: {a['tts_characters_per_minute']:g} characters/minute. [AI prices](https://developers.cloudflare.com/workers-ai/platform/pricing/), [SFU prices](https://developers.cloudflare.com/realtime/sfu/pricing/).", "",
        "| Utilization | Local cost/min | 60 min |", "|---|---:|---:|"]
    for u in (.1,.2,.5):
        v=copy.deepcopy(c); v["assumptions_not_vendor_quotes"]["billable_utilization"]=u
        cost=calculate(v)["local_per_minute"]
        rows.append(f"| {u:.0%} | ${cost:.4f} | ${cost*60:.2f} |")
    rows += ["",f"Always-warm VM at assumed rates: ${(a['gpu_per_hour']+a['vm_extras_per_hour'])*720:.2f}/30 days; do not count again alongside idle allocation. Free text ${d['free_user_monthly']:.2f}/user/month; paid text ${d['paid_text_monthly']:.2f}. Separate adult-text worker must cover loading/idle/safety within ${a['local_adult_text_per_message_including_safety']:.4f}/exchange. Scheduled service, not unbudgeted 24/7 capacity.", "",
        "## Earnings are conditional", "",
        f"Fee assumptions: {a['processor_fraction']:.0%} + ${a['processor_fixed_per_payment']:.2f}/payment, {a['refund_chargeback_loss_fraction']:.0%} refund/dispute loss, {a['reserve_fraction']:.0%} withheld reserve; support ${a['support_per_payer_monthly']:.2f}/payer; fixed ${a['monthly_fixed_excluding_gpu']:.2f}/month; verification ${a['age_check_per_user']:.2f}/new free or paid account. Reserve affects cash, not profit.",
        f"Configured {a['cohort_payers']:g}-payer/{a['cohort_free_users']:g}-free cohort: revenue ${d['cohort_gross']:.2f}; surplus ${d['cohort_surplus']:.2f}; cash after reserve and ${d['cohort_first_month_age_cost']:.2f} age checks: ${d['cohort_cash_before_age_and_tax']-d['cohort_first_month_age_cost']:.2f}. Excludes salary, acquisition, legal and tax.",
        "[CCBill](https://ccbill.com/pricing) fees need a quote; applicable $1,450–$1,950 annual card registration is amortized in fixed costs but payable upfront. Actual verification pricing also needs a quote.",
        f"Clip assumption: {a['clip_gpu_seconds_per_attempt']:g} allocated GPU seconds/attempt, {a['clip_success_fraction']:.0%} success, ${a['clip_other_per_delivered']:.2f} other cost plus contingency: ${d['clip_cost']:.2f}/delivered clip. Include load/idle/retries. Speed and realism are unproved.", "",
        "## Chaturbate in dollars", "",
        f"Wire buyer ${b['customer_wire_usd_per_token']:.2f}/token with **${b['wire_minimum_purchase_usd']:g} funding minimum**; performer ${b['performer_usd_per_token']:.2f}/token. Card prices not verified. [Buyer]({b['buyer_source']}), [performer]({b['performer_source']}).", "",
        "| Tokens/min | Buyer $/min | Performer $/min | Buyer 30 / 60 min | Performer 30 / 60 min |", "|---|---:|---:|---:|---:|"]
    for rate in b["private_tokens_per_minute"]:
        buy=rate*b["customer_wire_usd_per_token"]; pay=rate*b["performer_usd_per_token"]
        rows.append(f"| {rate} | ${buy:.2f} | ${pay:.2f} | ${buy*30:.2f} / ${buy*60:.2f} | ${pay*30:.2f} / ${pay*60:.2f} |")
    rows += ["", "Rate examples, not averages; the wire minimum still applies. Tips/taxes/minimum durations change spending. Gross spread is not platform profit. [Show rules]("+b["private_source"]+"), [listed categories](https://chaturbate.com/support/).", "",
        "| Our full-use offer | Buyer $/min | Cheaper than 6 tokens/min | Cheaper than 30 tokens/min |", "|---|---:|---:|---:|"]
    for name,rate in [(p["name"],p["monthly_price"]/p["live_minutes"]) for p in d["plans"]]+[("Top-up",a["topup_price"]/a["topup_minutes"])]:
        rows.append(f"| {name} | ${rate:.3f} | {(1-rate/(6*b['customer_wire_usd_per_token']))*100:.1f}% | {(1-rate/(30*b['customer_wire_usd_per_token']))*100:.1f}% |")
    rows += ["", "Savings assume all minutes used and the wire valuation. Low use can make subscriptions more expensive; public streams may be free. ChatGPT prices and product differences: [REPORT](REPORT.md).",
        "Launch price gate: measured live cost ≤$0.055/minute and ≥50% recurring contribution after actual fees. Quick talking clips need measured p95≤15s; cinematic clips p95≤120s and cost≤$0.50. No guarantee of arbitrary live actions or unrestricted content.", ""]
    return "\n".join(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Regenerate the pricing document")
    parser.add_argument("--json", action="store_true", help="Print numeric baseline results")
    parser.add_argument("--utilization", type=float, help="Override baseline for a sensitivity check")
    args = parser.parse_args()
    if args.write and args.json:
        parser.error("--write creates Markdown; use --json separately")
    c = load()
    if args.utilization is not None:
        c["assumptions_not_vendor_quotes"]["billable_utilization"] = args.utilization
    if args.write and args.utilization is not None:
        parser.error("Persist assumption changes in config before regenerating docs")
    try:
        output = json.dumps(calculate(c), indent=2) if args.json else report(c)
    except ValueError as error:
        parser.error(str(error))
    if args.write:
        (ROOT / "docs/ECONOMICS.md").write_text(output, encoding="utf-8")
        print("Updated docs/ECONOMICS.md")
    else:
        print(output)


if __name__ == "__main__":
    main()
