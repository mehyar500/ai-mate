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
    a, r, d = c["assumptions_not_vendor_quotes"], c["published_rates"], calculate(c)
    tokens = a["call_turns_per_minute"] * a["call_input_tokens_per_turn"]
    hourly = a["gpu_per_hour"] + a["vm_extras_per_hour"]
    rows = [
        "# Pricing and US comparison", "",
        f"USD, {c['as_of']}. Generated by scripts/economics.py from [config/economics.json](../../config/economics.json). Published rates are separated from assumptions. No measured profit is claimed.", "",
        "## Proposed offer", "",
        f"Free: one fictional adult companion, fixed portrait, {a['free_monthly_messages']:,.0f} text exchanges/month (daily ceiling {math.ceil(a['free_monthly_messages']/30)}), available all month. One prerecorded voice preview; no free GPU calls. Clean only.",
        f"Paid: {a['paid_monthly_messages']:,.0f} text exchanges/month, editable memory and live allowance. Adult text/calls only in approved US states and advertised beta hours; clean text remains available outside those hours with separate history. Verify eligibility before access.", "",
        "| Plan | Monthly price | Live minutes | Full-use contribution | Margin before fixed costs |",
        "|---|---:|---:|---:|---:|"
    ]
    for p in d["plans"]:
        rows.append(f"| {p['name']} | ${p['monthly_price']:.2f} | {p['live_minutes']} | ${p['contribution']:.2f} | {p['contribution_margin']:.1%} |")
    rows += ["", f"Top-up: ${a['topup_price']:.2f}/{a['topup_minutes']} minutes; contribution ${d['topup_contribution']:.2f}. Clip pack: ${a['clip_pack_price']:.2f}/{a['clips_per_pack']} delivered videos. Start with 5–10 second talking messages; add 5-second cinematic clips after validation.",
        "A minute is connected session time, including listening; voice/avatar share allowance. No rollover or automatic overage. Disclose expiry, restore failed clip entitlements, pause pilot metering during degradation. Unused allowances increase effective cost per used minute.", "",
        "## Call arithmetic", "",
        f"{a['call_turns_per_minute']:g} turns/minute × {a['call_input_tokens_per_turn']:,} input tokens/turn = **{tokens:,.0f} input tokens/minute**. Output: {a['call_output_tokens_per_minute']:g} tokens/minute; TTS: {a['tts_characters_per_minute']:g} characters/minute. Thirty minutes: {tokens*30:,.0f} input + {a['call_output_tokens_per_minute']*30:,.0f} output tokens. Sixty: {tokens*60:,.0f} + {a['call_output_tokens_per_minute']*60:,.0f}. Full history is billed again each turn.",
        f"Clean baseline: Qwen3-30B-A3B-FP8 ${r['llm_input_per_million']:.3f}/M input, ${r['llm_output_per_million']:.3f}/M output; Flux ASR ${r['streaming_asr_per_minute']:.4f}/minute; Aura-2 ${r['tts_per_thousand_characters']:.3f}/1,000 characters. Managed-call moderation adds explicit Llama Guard input/output checks. [Workers AI pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/).",
        f"SFU ${r['sfu_per_gb']:.2f}/GB × {a['aggregate_sfu_egress_mbps']:g} Mbps aggregate egress gives ${d['media_per_minute']:.6f}/minute, including both audio directions and video. Shared free allowances are excluded from pricing. [SFU rates](https://developers.cloudflare.com/realtime/sfu/pricing/).", "",
        "| Architecture | $/min | 30 min | 60 min |", "|---|---:|---:|---:|"]
    for name,key in (("Local GPU bundle: unbenchmarked primary","local_per_minute"),("Cloudflare voice + portrait","managed_voice_per_minute"),("Cloudflare voice + GPU avatar: fallback","managed_avatar_per_minute")):
        v=d[key]
        rows.append(f"| {name} | ${v:.4f} | ${v*30:.2f} | ${v*60:.2f} |")
    rows += ["", f"GPU formula: (${a['gpu_per_hour']:.2f} GPU + ${a['vm_extras_per_hour']:.2f} VM extras)/hour ÷ 60 ÷ {a['billable_utilization']:.0%} utilization ÷ {a['concurrent_calls_per_gpu']:g} concurrent calls = ${d['gpu_per_minute']:.4f}/minute including idle time. Add media, ${a['call_misc_per_minute']:.3f}/minute other cost and {a['variable_cost_buffer']:.0%} contingency.",
        "GPU rates, capacity and safety overhead are assumptions. Local policy inference must fit measured compute; local tokens have no extra per-token invoice. Do not add hosted LLM/TTS fees to the local row. Hosted speech still needs a GPU for an avatar.", "",
        "## Utilization and text cost", "",
        "| Utilization | Local $/min | 30 min | 60 min | " + " | ".join(p["name"]+" contribution" for p in d["plans"]) + " |",
        "|---|---:|---:|---:|" + "---:|"*len(d["plans"])]
    for utilization in (.1,.2,.5,.75):
        variant=copy.deepcopy(c)
        variant["assumptions_not_vendor_quotes"]["billable_utilization"]=utilization
        v=calculate(variant)
        rows.append(f"| {utilization:.0%} | ${v['local_per_minute']:.4f} | ${v['local_per_minute']*30:.2f} | ${v['local_per_minute']*60:.2f} | " + " | ".join(f"${p['contribution']:.2f}" for p in v["plans"]) + " |")
    rows += ["", f"One continuously warm worker at ${hourly:.2f}/hour costs ${hourly*720:,.2f}/30 days. At 1,000 delivered minutes: ${hourly*720/1000:.3f}/minute GPU allocation; at 10,000: ${hourly*720/10000:.4f}. Do not double-count this bill alongside utilization allocation. Start scheduled hours; averages do not solve concurrent demand.",
        f"Free text at full use: ${d['free_user_monthly']:.2f}/user/month. Each exchange budgets {a['chat_input_tokens']:,} chat input + {a['chat_output_tokens']:,} output tokens, combined {a['guard_input_tokens_per_exchange']:,} guard input + {a['guard_output_tokens_per_exchange']:,} output tokens. Assets/storage: ${a['profile_storage_asset_monthly']:.2f}/month.",
        f"Paid text: ${d['paid_text_monthly']:.2f}/month, using the higher of clean cost and ${a['local_adult_text_per_message_including_safety']:.4f}/local exchange. The local assumption includes separate text-worker loading, idle time and policy checks: only {a['local_adult_text_per_message_including_safety']/hourly*3600 if hourly else 0:.2f} allocated GPU seconds/exchange at this VM rate.",
        "Adult text is scheduled beta service. Queue/batch within a bounded window; outside hours show unavailable, without forwarding adult context. Meter text-worker time separately from calls and replace the flat assumption with measured delivered cost before sale.", "",
        "## Fees and cash", "",
        f"Processor assumption: {a['processor_fraction']:.0%} + ${a['processor_fixed_per_payment']:.2f}/payment; gross loss allowance {a['refund_chargeback_loss_fraction']:.0%} for refunds/chargebacks; separate {a['reserve_fraction']:.0%} reserve. Reserve withholds cash, not additional expense. Support: ${a['support_per_payer_monthly']:.2f}/payer/month. Actual fees, penalties and release terms need a quote.",
        f"Fixed non-GPU budget ${a['monthly_fixed_excluding_gpu']:.2f}/month covers paid Workers, registration amortization, email and other operations. Workers base is $5. [CCBill](https://ccbill.com/pricing) publishes applicable Visa $950 and Mastercard $500/$1,000 annual registration: $1,450–$1,950 upfront, up to $162.50/month amortized. Its percentage fee is quote-based. Prices exclude sales tax/VAT; collected tax is not revenue.",
        f"Age-check assumption ${a['age_check_per_user']:.2f}/new account, free or paid; Yoti quote required. Config has {a['cohort_new_free_users']:g} new free and {a['cohort_new_payers']:g} new paying users. Expiry/retries may add checks.",
        f"Cohort: {a['cohort_payers']:g} payers (" + ", ".join(f"{p['share']:.0%} {p['name']}" for p in d["plans"]) + f"), {a['cohort_free_users']:g} full-use free users. Gross ${d['cohort_gross']:.2f}; modeled surplus ${d['cohort_surplus']:.2f}; cash after reserve ${d['cohort_cash_before_age_and_tax']:.2f}; age checks ${d['cohort_first_month_age_cost']:.2f}; cash after checks ${d['cohort_cash_before_age_and_tax']-d['cohort_first_month_age_cost']:.2f}.",
        f"Break-even for the existing free cohort: {d['break_even_payers'] if d['break_even_payers'] is not None else 'unreachable at this mix'} payers before new verification, acquisition, salary, legal and tax. Annual-fee upfront timing needs additional cash. This is contribution, not net profit.", "",
        "## Clip sensitivity", "",
        f"Assume ${hourly:.2f}/GPU-hour, {a['clip_success_fraction']:.0%} successful attempts, ${a['clip_other_per_delivered']:.2f}/delivered clip for review/storage/other work, {a['variable_cost_buffer']:.0%} contingency. Allocated seconds include load/idle/retries; no permanently warm clip pool.",
        "| GPU seconds/attempt | Cost/delivered | Pack contribution |", "|---|---:|---:|"]
    for seconds in (120,600,1800):
        variant=copy.deepcopy(c)
        variant["assumptions_not_vendor_quotes"]["clip_gpu_seconds_per_attempt"]=seconds
        v=calculate(variant)
        rows.append(f"| {seconds} | ${v['clip_cost']:.2f} | ${v['clip_pack_contribution']:.2f} |")
    rows += ["", "Release gate: measured live cost ≤$0.055/minute and ≥50% recurring contribution at full use after actual fees. Charge one-time verification to acquisition economics. Change prices/allowances if this fails; the managed-avatar fallback may be too costly.",
        "Market quick talking clips only after p95 ≤15 seconds; cinematic clips after p95 ≤120 seconds and delivered cost ≤$0.50. Targets are unproven. Failed jobs consume our compute but restore customer entitlements within bounded retry budgets.", "",
        "## Chaturbate in dollars", ""]
    b=c["competitor_reference"]
    rows += [f"Official broadcaster payout ${b['performer_usd_per_token']:.2f}/token; official wire purchase ${b['customer_wire_usd_per_token']:.2f}/token, minimum funding ${b['wire_minimum_purchase_usd']:,.0f}. Current card-pack prices were not verified. These are wire-value comparisons, not universal retail quotes. [Buy tokens]({b['buyer_source']}), [convert earnings]({b['performer_source']}).",
        f"Broadcasters choose private rate/minimum duration. Official navigation lists categories from 6 to 90+ tokens/minute. Rows are scenarios, not averages or guaranteed availability. [Show types]({b['private_source']}), [official categories](https://chaturbate.com/support/).", "",
        "| Tokens/min | Buyer $/min | Performer $/min | Buyer 30 / 60 min | Performer 30 / 60 min |", "|---|---:|---:|---:|---:|"]
    for rate in b["private_tokens_per_minute"]:
        buyer=rate*b["customer_wire_usd_per_token"]
        performer=rate*b["performer_usd_per_token"]
        rows.append(f"| {rate} | ${buyer:.2f} | ${performer:.2f} | ${buyer*30:.2f} / ${buyer*60:.2f} | ${performer*30:.2f} / ${performer*60:.2f} |")
    rows += ["", f"The ${b['wire_minimum_purchase_usd']:,.0f} wire minimum still applies: a new buyer cannot fund only a short show's calculated value by wire. Taxes, tips, duration restrictions and unused balance alter spending.",
        f"A 100-token public tip is ${100*b['customer_wire_usd_per_token']:.2f} buyer value and ${100*b['performer_usd_per_token']:.2f} performer payout. The difference is gross spread, not platform profit. Tips do not automatically buy private time. Public streams can be watched free and funded by many tippers; an AI call uses per-customer compute.", "",
        "| Amorien, all included minutes used | Effective buyer $/min | Allocated 30 / 60 min value |", "|---|---:|---:|"]
    for p in d["plans"]:
        rate=p["monthly_price"]/p["live_minutes"]
        rows.append(f"| {p['name']} | ${rate:.3f} | ${rate*30:.2f} / ${rate*60:.2f} |")
    topup=a["topup_price"]/a["topup_minutes"]
    rows += [f"| Top-up | ${topup:.3f} | ${topup*30:.2f} / ${topup*60:.2f} |", "",
        "Allocated subscription values are not standalone purchase prices. Low use can make a monthly plan more expensive than a cheap human private; public viewing may be free. Compete on predictable one-to-one price, memory and consistent access. Equal realism, the appeal of a real person and willingness to pay are unproven; test against the cheapest band as well as expensive privates.", ""]
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
        (ROOT / "docs/product/ECONOMICS.md").write_text(output, encoding="utf-8")
        print("Updated docs/product/ECONOMICS.md")
    else:
        print(output)


if __name__ == "__main__":
    main()
