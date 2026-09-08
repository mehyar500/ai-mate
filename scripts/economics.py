"""Offline asynchronous companion economics; no API calls or billing."""
import argparse
import copy
import json
import math
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def load():
    return json.loads((ROOT / "config/economics.json").read_text(encoding="utf-8"))


def validate(c):
    for group in (c["rates"], c["assumptions"]):
        for key, value in group.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise ValueError(f"{key} must be finite and nonnegative")
    a = c["assumptions"]
    if not 0 < a["video_accepted_fraction"] <= 1:
        raise ValueError("Acceptance must be in (0, 1]")
    if a["processor_fraction"] + a["refund_loss_fraction"] >= 1 or a["high_risk_fraction"] >= 1 or a["reserve_fraction"] > 1:
        raise ValueError("Invalid payment fraction")
    for p in c["plans"] + c["addons"]:
        for k, v in p.items():
            if k != "name" and (isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0):
                raise ValueError("Invalid plan")
        if p["price"] <= 0:
            raise ValueError("Price must be positive")
    if not c["plans"] or not math.isclose(sum(p["share"] for p in c["plans"]), 1):
        raise ValueError("Plan shares must sum to one")


def price_floor(nonpercentage_cost, fee_fraction, return_on_cost=3):
    # Revenue = (1+return)*all costs, including percentage-based fees.
    denominator = 1/(1+return_on_cost) - fee_fraction
    return nonpercentage_cost/denominator if denominator > 0 else None


def calculate(c):
    validate(c)
    a, r = c["assumptions"], c["rates"]
    video_model = (a["video_seconds"]*r["fal_video_per_output_second"] + a["video_other_per_attempt"]) / a["video_accepted_fraction"] * (1+a["buffer_fraction"])
    video_cost = max(video_model, a["video_delivered_budget"])
    custom = ((a["custom_video_billed_seconds"]+a["custom_keepwarm_seconds"])*a["gpu_rate_per_second"]+a["custom_other_per_attempt"])/a["video_accepted_fraction"]*(1+a["buffer_fraction"])
    fee = a["processor_fraction"]+a["refund_loss_fraction"]
    plans=[]
    for p in c["plans"]:
        delivery=a["paid_text_monthly"]+a["support_per_payer"]+p["call_minutes"]*a["phone_call_minute"]+p["videos"]*video_cost
        total=delivery+fee*p["price"]+a["payment_fixed"]
        high=delivery+a["high_risk_fraction"]*p["price"]+a["high_risk_fixed"]
        plans.append(dict(p,delivery=delivery,total=total,profit=p["price"]-total,margin=1-total/p["price"],return_on_cost=(p["price"]-total)/total,high_risk_total=high,price_floor=price_floor(delivery+a["payment_fixed"],fee,a["target_return_on_cost"])))
    arpu=sum(p["share"]*p["price"] for p in plans)
    unit=sum(p["share"]*p["total"] for p in plans)
    high_unit=sum(p["share"]*p["high_risk_total"] for p in plans)
    fixed=a["monthly_fixed"]+a["free_users_cap"]*a["free_user_monthly"]+a["founder_labor_monthly"]
    first_fixed=fixed+a["first_month_setup"]+a["free_users_cap"]*a["new_user_verification_cost"]
    variable=unit+a["customer_acquisition_cost"]+a["new_user_verification_cost"]
    n=a["cohort_payers"]
    revenue=n*arpu
    costs=n*variable+first_fixed
    headroom=arpu/(1+a["target_return_on_cost"])-variable
    contribution=arpu-variable
    addons=[]
    for p in c["addons"]:
        cost=p["call_minutes"]*a["phone_call_minute"]+p["videos"]*video_cost+p["support"]+fee*p["price"]+a["payment_fixed"]
        addons.append(dict(p,cost=cost,profit=p["price"]-cost,return_on_cost=(p["price"]-cost)/cost))
    return dict(plans=plans,addons=addons,video_formula_cost=video_model,video_budget=video_cost,custom_video_cost=custom,arpu=arpu,unit_cost=unit,high_risk_unit_cost=high_unit,first_fixed=first_fixed,recurring_fixed=fixed,revenue=revenue,first_cost=costs,first_profit=revenue-costs,first_return=(revenue-costs)/costs if costs else None,cash_after_reserve=revenue-costs-revenue*a["reserve_fraction"],break_even=math.ceil(first_fixed/contribution) if contribution>0 else None,target_payers=math.ceil(first_fixed/headroom) if headroom>0 else None)


def report(c):
    a,d=c["assumptions"],calculate(c)
    rows=["# Asynchronous MVP economics", "", f"USD; checked {c['as_of']}. Generated from [config](../config/economics.json). Proposed non-explicit launch, not measured results. A 300% return on total cost means a 75% margin. All outputs below are before income tax; founder labor and verification default to zero and must be priced before claiming economic profit.", "", "## Allowances and unit economics", "", f"Free: {a['free_exchanges']} exchanges/month, 5/day, one curated portrait; cap {a['free_users_cap']} free accounts. Paid: {a['paid_exchanges']} text exchanges/month. Text replies can also be played as free voice messages (up to 15 seconds each); free uploaded voice notes have a separate five-minute input cap. Paid voice allowance below means connected phone-call minutes, including listening; video allowance is delivered clips up to {a['video_seconds']} seconds.", "", "| Plan | Price/month | Phone-call min | Clips | Direct cost incl. payment | Contribution | Return on direct cost |", "|---|---:|---:|---:|---:|---:|---:|"]
    for p in d["plans"]:
        rows.append(f"| {p['name']} | ${p['price']:.2f} | {p['call_minutes']} | {p['videos']} | ${p['total']:.2f} | ${p['profit']:.2f} | {p['return_on_cost']:.1%} |")
    rows += ["",f"Budgets: ${a['phone_call_minute']:.2f}/connected phone-call minute, ${d['video_budget']:.2f}/delivered clip, ${a['paid_text_monthly']:.2f}/payer text, free voice playback and memory, ${a['support_per_payer']:.2f}/payer support. Ordinary-processing scenario: {a['processor_fraction']:.0%} processing/platform allowance + {a['refund_loss_fraction']:.0%} refund/loss + ${a['payment_fixed']:.2f}/transaction; no merchant approval assumed.", "", "| Optional prepaid pack | Price | Direct cost | Return on direct cost |", "|---|---:|---:|---:|"]
    for p in d["addons"]:
        rows.append(f"| {p['name']}: {p['videos']} clips / {p['call_minutes']} phone-call min | ${p['price']:.2f} | ${p['cost']:.2f} | {p['return_on_cost']:.1%} |")
    rows += ["", "These are contribution returns, not company profit. Budget full redemption; do not count unused credits as the business model. Reserve unfulfilled service costs and refunds. No annual prepaid plan or automatic overage in the pilot.", "", "## Generation cost and speed", "",f"fal FlashHead: {a['video_seconds']} output seconds x ${c['rates']['fal_video_per_output_second']:.3f} = ${a['video_seconds']*c['rates']['fal_video_per_output_second']:.3f} vendor price. Add ${a['video_other_per_attempt']:.2f}/attempt, divide by {a['video_accepted_fraction']:.0%} usable-output rate and add {a['buffer_fraction']:.0%}: ${d['video_formula_cost']:.3f}; reserve at least ${d['video_budget']:.2f}. Rejected successful generations cost us; vendor server errors have different billing treatment. Hosted text endpoint bundles its own speech; do not charge Aura again for the same video.", f"Custom Runware scenario: {a['custom_video_billed_seconds']} runtime + {a['custom_keepwarm_seconds']} warm seconds x ${a['gpu_rate_per_second']:.6f}/GPU-second, plus ${a['custom_other_per_attempt']:.2f}/attempt, same acceptance/buffer = ${d['custom_video_cost']:.3f}. This is an unbenchmarked alternative, not an available endpoint or an adult approval. Count model loading if the contract meters it. Zero workers means zero compute; held-warm and reserved workers cost money.", "[fal model](https://fal.ai/models/fal-ai/flashhead), [billing](https://fal.ai/docs/documentation/model-apis/pricing), [Runware compute](https://runware.ai/serverless/compute). Fifteen-second output duration is not turnaround time. Require measured p95 <=20 seconds from submit to playable result before advertising fast delivery.", "", "## First month: cash operating scenarios", "", f"Assume the configured plan mix, {a['free_users_cap']} free accounts, ${a['monthly_fixed']:.2f} recurring fixed cost, ${a['first_month_setup']:.2f} setup/benchmark cost, ${a['customer_acquisition_cost']:.2f} acquisition per payer, ${a['founder_labor_monthly']:.2f} founder labor and ${a['new_user_verification_cost']:.2f} per new free/paid user. Setup is a spending ceiling to test, not a quote for building a production app or US legal review.", "", "| Payers | Revenue | First-month modeled cost | Profit/loss | Return on cost |", "|---|---:|---:|---:|---:|"]
    for n in (20,100,600):
        v=copy.deepcopy(c);v["assumptions"]["cohort_payers"]=n;x=calculate(v)
        rows.append(f"| {n} | ${x['revenue']:.2f} | ${x['first_cost']:.2f} | ${x['first_profit']:.2f} | {x['first_return']:.1%} |")
    rows += ["", f"Break-even: {d['break_even']} mixed-plan payers; 300% first-month return: {d['target_payers']} payers under these assumptions. Revenue is earned only as promised service is delivered; cash collection alone is not profit. All scenarios budget full monthly allowance consumption.", "", "| Stress at configured payer count | Profit/loss | 300% target payer count |", "|---|---:|---:|"]
    for label,updates in (("Paid acquisition $5",dict(customer_acquisition_cost=5)),("Verification $1/new account",dict(new_user_verification_cost=1)),("Founder labor $3,000",dict(founder_labor_monthly=3000)),("No setup charge (later month, same new-payer assumption)",dict(first_month_setup=0)),("High-risk fees",dict(processor_fraction=a["high_risk_fraction"],refund_loss_fraction=0,payment_fixed=a["high_risk_fixed"]))):
        v=copy.deepcopy(c);v["assumptions"].update(updates);x=calculate(v)
        rows.append(f"| {label} | ${x['first_profit']:.2f} | {x['target_payers'] if x['target_payers'] is not None else 'Impossible at this mix and unit cost'} |")
    rows += ["",f"An assumed {a['reserve_fraction']:.0%} payment reserve reduces configured first-month available cash to ${d['cash_after_reserve']:.2f}; it is not an expense. Provider prepaid balances, settlement delays and refund liabilities require working capital even when profit is positive.", "", "Formula: price floor = (delivery + fixed payment fee + allocated overhead/acquisition) / (0.25 - percentage fees/losses). If the denominator is nonpositive, 300% return is impossible. No sales or price is guaranteed. Do not rely on unquoted ordinary fees for adult business.", "", "## Later FaceTime-style video calls", "", "Keep disabled in the first month. FlashHead Pro on a quoted TensorDock two-5090 group plus local Qwen3-8B/Whisper/Kokoro: prior modeled $5.69/30 minutes at 50% utilization. At high-risk 18% fees + $0.50, direct 300% floor is ($5.69 + $0.50)/0.07 = about $88.46, before support/startup/overhead. Model $59/30 minutes for an approved clean service with ordinary fees, or $129/30 minutes under the high-risk fee scenario. Both require their own warm-up, support and overhead budget; validate actual cost and demand first. Quark LiveAvatar + Wan2.2-S2V-14B with eight rented H100s costs about $24.69/30 minutes; same direct floor about $359.89. Reject this as the default product. Prices are scenarios, not live offers.", ""]
    return "\n".join(rows)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write",action="store_true")
    parser.add_argument("--json",action="store_true")
    parser.add_argument("--payers",type=int)
    args=parser.parse_args()
    if args.write and (args.json or args.payers is not None):
        parser.error("Persist config first; --write cannot combine with overrides or --json")
    c=load()
    if args.payers is not None:
        c["assumptions"]["cohort_payers"]=args.payers
    try:
        output=json.dumps(calculate(c),indent=2) if args.json else report(c)
    except ValueError as error:
        parser.error(str(error))
    if args.write:
        (ROOT/"docs/ECONOMICS.md").write_text(output,encoding="utf-8")
        print("Updated docs/ECONOMICS.md")
    else:
        print(output)


if __name__ == "__main__":
    main()
