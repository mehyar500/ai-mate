"""Reproducible adult PWA forecast. No inference, spend, or billing integration."""
import argparse
import copy
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load():
    return json.loads((ROOT/"config/economics.json").read_text(encoding="utf-8"))

def validate(c):
    a=c["assumptions"]
    for k,v in a.items():
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0:
            raise ValueError(f"{k} must be finite and nonnegative")
    if a["streams"]<1 or not 0<a["occupancy"]<=1:
        raise ValueError("Invalid capacity or occupancy")
    if a["processor_fraction"]+a["loss_fraction"]>=1 or a["reserve_fraction"]>1:
        raise ValueError("Invalid fee or reserve")
    for p in c["plans"]+c["packs"]:
        for k,v in p.items():
            if k!="name" and (isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0):
                raise ValueError("Invalid plan")
        if p["price"]<=0:
            raise ValueError("Price must be positive")
    if not c["plans"] or not math.isclose(sum(p["share"] for p in c["plans"]),1):
        raise ValueError("Plan shares must sum to one")
    fixed=c["monthly_fixed_breakdown"]
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 for v in fixed.values()):
        raise ValueError("Invalid fixed-cost breakdown")
    if not math.isclose(sum(fixed.values()),a["monthly_fixed"]):
        raise ValueError("Fixed-cost breakdown must match monthly_fixed")
    lag=c["launch"]["settlement_lag_months"]
    if isinstance(lag,bool) or not isinstance(lag,int) or lag<0:
        raise ValueError("Settlement lag must be whole nonnegative months")
    if len(c["launch"]["months"])!=3:
        raise ValueError("This report requires exactly three launch months")
    previous_paid=previous_free=0
    for m in c["launch"]["months"]:
        for k in ("payers","new_payers","free_users","new_free","aux_hours","renderer_open_hours"):
            v=m[k]
            if isinstance(v,bool) or not isinstance(v,int) or v<0:
                raise ValueError("Launch counts and scheduled hours must be nonnegative integers")
        if m["new_payers"]>m["payers"] or m["payers"]-m["new_payers"]>previous_paid:
            raise ValueError("Paid cohort cannot grow without new customers")
        if m["new_free"]>m["free_users"] or m["free_users"]-m["new_free"]>previous_free:
            raise ValueError("Free cohort cannot grow without new customers")
        previous_paid,previous_free=m["payers"],m["free_users"]

def price_floor(cost,fees,return_on_cost=3):
    denominator=1/(1+return_on_cost)-fees
    return cost/denominator if denominator>0 else None

def calculate(c):
    validate(c)
    a=c["assumptions"]
    fees=a["processor_fraction"]+a["loss_fraction"]
    renderer=a["gpu_hour"]/(60*a["streams"]*a["occupancy"])
    live=max(a["live_minute_floor"],(renderer+a["auxiliary_per_live_minute"]+a["transport_per_minute"])*(1+a["contingency"]))
    def product(p,base):
        delivery=base+p["live_minutes"]*live+p["phone_minutes"]*a["phone_minute"]+p["clips"]*a["clip_cost"]+p["photos"]*a["photo_cost"]+p["scenes"]*a["scene_cost"]
        cost=delivery+fees*p["price"]+a["payment_fixed"]
        return dict(p,delivery=delivery,cost=cost,profit=p["price"]-cost,margin=1-cost/p["price"],roi=p["price"]/cost-1,
                    floor300=price_floor(delivery+a["payment_fixed"],fees,3),
                    floor500=price_floor(delivery+a["payment_fixed"],fees,5))
    plans=[product(p,a["paid_messages"]+a["support"]) for p in c["plans"]]
    packs=[product(p,.10) for p in c["packs"]]
    arpu=sum(p["share"]*p["price"] for p in plans)
    unit=sum(p["share"]*p["cost"] for p in plans)
    minutes=sum(p["share"]*p["live_minutes"] for p in plans)
    n=a["payers"]
    # Count the scheduled renderer once: unit allocations plus any uncovered floor.
    renderer_allocated=n*minutes*renderer
    idle_topup=max(0,a["renderer_open_hours"]*a["gpu_hour"]-renderer_allocated)
    aux_fixed=a["aux_gpu_hour"]*a["aux_hours"]
    recurring=n*unit+a["monthly_fixed"]+aux_fixed+a["free_users"]*a["free_user"]+a["founder_labor"]+idle_topup
    startup=sum(a[k] for k in ("setup_technical","registration","legal_setup","security_setup","tooling_setup","domain_setup","entity_setup"))
    acquisition=n*a["cac"]
    verification=(n+a["free_users"])*a["verification_per_new_user"]
    first_cost=recurring+startup+acquisition+verification
    revenue=n*arpu
    verification_labor=(n+a["free_users"])*a["verification_minutes"]/60*a["review_hour_value"]
    # A conservative runway budget assumes no receipts finance first-month service.
    # Percentage fees are withheld from receipts, not prepaid operating purchases.
    prepaid_service=recurring-n*(fees*arpu+a["payment_fixed"])
    funding=startup+prepaid_service+acquisition+verification+a["working_buffer"]
    return dict(plans=plans,packs=packs,live_minute=live,renderer_minute=renderer,arpu=arpu,unit_cost=unit,
                idle_topup=idle_topup,recurring_cost=recurring,startup=startup,verification=verification,
                revenue=revenue,first_cost=first_cost,first_profit=revenue-first_cost,
                first_roi=revenue/first_cost-1 if first_cost else None,
                recurring_profit=revenue-recurring, cash_after_reserve=revenue-first_cost-revenue*a["reserve_fraction"],
                aux_fixed=aux_fixed,verification_labor=verification_labor,first_profit_after_review_labor=revenue-first_cost-verification_labor,
                funding_before_receipts=funding)

def forecast(c):
    """Cash planning, not GAAP accounting. New cohorts exclude free-to-paid conversions.

    Fees/loss allowance and reserves are withheld; eligible proceeds settle after
    an explicit lag. Reserve release is outside this three-month horizon.
    """
    validate(c)
    a=c["assumptions"]; lag=c["launch"]["settlement_lag_months"]
    months=[]; cumulative_cash=0; peak_deficit=0
    for i,m in enumerate(c["launch"]["months"]):
        x=copy.deepcopy(c)
        x["assumptions"].update({k:m[k] for k in ("payers","free_users","aux_hours","renderer_open_hours")})
        d=calculate(x)
        startup=d["startup"] if i==0 else 0
        verified=m["new_payers"]+m["new_free"]
        verification=verified*a["verification_per_new_user"]
        acquisition=m["new_payers"]*a["cac"]
        withheld=m["payers"]*((a["processor_fraction"]+a["loss_fraction"])*d["arpu"]+a["payment_fixed"])
        reserve=d["revenue"]*a["reserve_fraction"]
        eligible=d["revenue"]-withheld-reserve
        expenses=d["recurring_cost"]+startup+verification+acquisition
        cash_out=expenses-withheld
        receipts=eligible if lag==0 else (months[i-lag]["eligible"] if i>=lag else 0)
        cash_change=receipts-cash_out
        cumulative_cash+=cash_change
        peak_deficit=max(peak_deficit,-cumulative_cash)
        months.append(dict(m,revenue=d["revenue"],startup=startup,expenses=expenses,
                           delivery=m["payers"]*sum(p["share"]*p["delivery"] for p in d["plans"]),
                           fixed=a["monthly_fixed"],aux=d["aux_fixed"],idle=d["idle_topup"],
                           free_delivery=m["free_users"]*a["free_user"],founder_pay=a["founder_labor"],
                           verified=verified,verification=verification,acquisition=acquisition,
                           withheld=withheld,reserve=reserve,eligible=eligible,
                           profit=d["revenue"]-expenses,cash_out=cash_out,receipts=receipts,
                           cash_change=cash_change,cumulative_cash=cumulative_cash,
                           review_labor=verified*a["verification_minutes"]/60*a["review_hour_value"]))
    totals={k:sum(m[k] for m in months) for k in (
        "revenue","expenses","profit","cash_out","receipts","reserve","eligible","verified","review_labor")}
    totals.update(unsettled=totals["eligible"]-totals["receipts"],cash_change=cumulative_cash,
                  minimum_funding=peak_deficit+a["working_buffer"],
                  funding_without_receipts=totals["cash_out"]+a["working_buffer"])
    return dict(months=months,totals=totals)


def no_sales(c):
    x=copy.deepcopy(c)
    for m in x["launch"]["months"]:
        m.update(payers=0,new_payers=0)
    return x



def demo_forecast(c):
    """Incremental founder-demo spending. No customer revenue or paid payroll."""
    p=c["poc"]
    for key,value in p.items():
        if key!="months" and (isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0):
            raise ValueError("POC assumptions must be finite and nonnegative")
    if len(p["months"])!=3:
        raise ValueError("POC requires three months")
    months=[]
    for m in p["months"]:
        for key in ("local_hours","fallback_hours","large_hours"):
            value=m[key]
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0:
                raise ValueError("Invalid POC hours")
        electricity=m["local_hours"]*p["local_kw"]*p["electricity_per_kwh"]
        fallback=m["fallback_hours"]*p["fallback_gpu_hour"]
        large=m["large_hours"]*p["large_gpu_hour"]
        expense=electricity+fallback+large+p["storage_monthly"]+p["incremental_tools_monthly"]+p["web_monthly"]
        months.append(dict(m,electricity=electricity,fallback=fallback,large=large,expense=expense))
    expense=sum(m["expense"] for m in months)
    funding=expense+p["contingency"]
    return dict(months=months,expense=expense,funding=funding,
                first_demo_funding=months[0]["expense"]+p["contingency"],
                cap=p["quarter_cap"],headroom=p["quarter_cap"]-funding,
                within_cap=funding<=p["quarter_cap"])


def remote_clip_comparison():
    rows = [
        '### Cloudflare-routed clip candidates — September 8', '',
        'Provider list-price arithmetic below is a planning comparison; Cloudflare model pages direct pricing to the account dashboard. Confirm the account quote before inference. The founder loaded $10 Gateway credits. Live account pricing confirms P-Video 720p draft/standard at $0.005/$0.020 per second and LTX-2.5 Fast 720p at $0.090; LTX 1080p is $0.150. Two five-second LTX tests recorded $0.45 each in Gateway cost metadata, reconciled to $9.10 remaining credits. Each took about 31s. Pruna input mapping failed; its low price is not a working result. One Cloudflare credential is preferred. [Unified Billing](https://developers.cloudflare.com/ai-gateway/features/unified-billing/) adds 5% to credit purchases.', '',
        '| Model / 720p configuration | Provider $/output second | 15-second clip | Clip with 5% funding fee | 30 minutes of generated footage, with fee |',
        '|---|---:|---:|---:|---:|',
    ]
    for name, rate in [('Pruna P-Video draft', .005), ('Pruna P-Video standard', .020),
                       ('Pruna P-Video-Avatar', .025), ('LTX-2.5 Fast', .090)]:
        rows.append(f'| {name} | ${rate:.3f} | ${rate*15:.3f} | ${rate*15*1.05:.4f} | ${rate*1800*1.05:.2f} |')
    rows += ['',
        'Sources: [P-Video rates](https://docs.api.pruna.ai/guides/models/p-video), [avatar rates](https://docs.api.pruna.ai/guides/models/p-video-avatar), [LTX rates](https://docs.ltx.io/pricing). Draft means lower quality. The 30-minute column aggregates many clips, not a supported continuous request or a measured live call. It excludes retries, discarded output, transport, other inference, taxes, payment fees and support. No volume discount or reusable-video saving is assumed.', '',
        'At a hypothetical $1.99 price for one 15-second standard P-Video clip, 30% Apple commission and the above $0.315 generation estimate leave $1.078 (54.2% of customer price) before every other cost. Avatar leaves $0.9993 (50.2%). Those are contribution ceilings, not net margins or validated willingness to pay. Ten standard clips consume $3.15 before other service costs, exceeding the $3.00 service ceiling for a $29.99 plan targeting 60% contribution at 30% Apple fees. Keep clips metered.', '',
        'Runpod [InfiniteTalk](https://docs.runpod.io/public-endpoints/models/infinitetalk) lists $0.25/480p or $0.50/720p per video, but that page does not establish an accepted audio-duration limit. Do not turn its flat price into an unlimited-call estimate. Managed clip endpoints need no reserved GPU, but have unmeasured queue/render latency. For continuous calls, compare a persistent streaming worker against local FlashHead; cold-start and occupancy costs remain. Runpod is excluded for explicit content under its [terms](https://www.runpod.io/legal/terms-of-service).',
    ]
    return '\n'.join(rows)


def report(c):
    p=c["poc"];d=demo_forecast(c);future=calculate(c)
    rows=["# Local proof-of-concept economics","",
          f"Checked {c['as_of']}. Generated from [config](../config/economics.json). Active stage: founder-operated proof of concept and fundraising demos. No customer sales, paid engineering, production uptime or public adult service is budgeted. Existing computer and existing coding subscriptions are already owned/paid; founder living costs are outside this incremental project budget.",
          "","## Spending decision","",
          f"First-demo allowance including the reserve: **${d['first_demo_funding']:.2f}**. Three-month planned expense: **${d['expense']:.2f}**, plus one **${p['contingency']:.2f}** contingency pool = **${d['funding']:.2f}**. Set a **${p['quarter_cap']:.0f} quarter cap**. The reserve is counted once, not every month. No cloud GPU, new paid tool or paid engineer is in this active budget. Planned funding is {'within' if d['within_cap'] else 'OVER'} the cap; stop/re-scope if actual commitments exceed it. The electricity-only baseline below predates the founder-funded $10 Gateway top-up; its allocation from contingency is recorded under stop rules. The agent made no payment-method or automatic top-up changes.",
          "","## Why this is cheaper","",
          "Read-only local inventory found an NVIDIA RTX 4060 Ti with 16,380 MiB reported VRAM and about 47.7 GiB system RAM. Cloudflare currently handles dialogue; CPU speech and local graphics share the existing rig. Scene preparation is a separate phase. No rented GPU is used in this stage. Downloads need internet access; active call graphics and speech stay local, with separately funded cloud video benchmarks; hosted dialogue may incur usage charges. See LOCAL_POC for measured results and limitations.",
          "Founder screenshares a private app using synthetic demo profiles. Public material is a non-explicit product preview with no adult service access, uploads, checkout or exposed inference endpoint. Private does not waive model/host terms or applicable law; unresolved intended-content eligibility is reported as unresolved, not hidden in a demo.",
          "","## Three-month incremental costs","",
          "| Item | M1 build/demo | M2 demos | M3 demos | Total |","|---|---:|---:|---:|---:|"]
    entries=[("Local electricity",[m['electricity'] for m in d['months']]),
             ("24GB cloud fallback",[m['fallback'] for m in d['months']]),
             ("Large-GPU video experiments",[m['large'] for m in d['months']]),
             ("Storage allowance",[p['storage_monthly']]*3),
             ("Incremental tools/API allowance",[p['incremental_tools_monthly']]*3),
             ("Local/free-tier web preview",[p['web_monthly']]*3),
             ("Total planned expense",[m['expense'] for m in d['months']])]
    for label,values in entries:
        rows.append("| "+label+" | "+" | ".join(f"${v:.2f}" for v in [*values,sum(values)])+" |")
    rows += ["",f"Local power assumes {p['local_kw']*1000:.0f}W incremental average draw and ${p['electricity_per_kwh']:.2f}/kWh, for 100/30/30 hours. This is an estimate, not measured power or the user's tariff. Local disk capacity and existing subscriptions are already available. Cloud fallback and large-GPU hours are zero; legacy rates remain in config only for an explicitly approved future comparison. No guaranteed video throughput or model fit is implied by the budget.",
             "","Use localhost; no domain or remote deployment is needed. The active Cloudflare dialogue adapter uses existing credentials and may incur usage charges, which are not measured in this electricity-only baseline. Ollama is an optional local alternative; CPU speech uses downloaded weights. A future eligible web preview could use Cloudflare Free, but it is not needed or deployed now. [Cloudflare pricing](https://developers.cloudflare.com/workers/platform/pricing/).",
             "","## Sensitivity and stop rules","",f"| Scenario | Quarter expense | With one contingency pool | Within ${p['quarter_cap']:.0f} cap? |","|---|---:|---:|---|"]
    variants=[("Baseline",c)]
    for label,changes in [("Local power draw doubles",dict(local_kw=p['local_kw']*2)),
                          ("New optional tools at $10/month",dict(incremental_tools_monthly=10)),
                          ("Electricity only, no contingency",dict(contingency=0))]:
        x=copy.deepcopy(c);x['poc'].update(changes);variants.append((label,x))
    for label,x in variants:
        z=demo_forecast(x)
        rows.append(f"| {label} | ${z['expense']:.2f} | ${z['funding']:.2f} | {'Yes' if z['within_cap'] else 'No — reduce hours/scope'} |")
    rows += ["",f"The ${p['quarter_cap']:.0f} cap is a planning limit, not an implemented account control or permission to purchase. The founder now permits considering inexpensive cloud/larger-GPU approaches if local latency remains unacceptable. Compare measured benefit before purchasing; no rental is currently provisioned. The founder-funded $10 credit top-up now exists. Budget $10.50 before tax with the published 5% funding fee, drawn from the existing $75 contingency; that leaves $64.50 reserve and keeps the original $84.60 envelope. The $0.90 test usage spends those prepaid credits, so do not count it again as a second cash purchase. Exact tax/receipt fees and other hosted dialogue charges still need reconciliation. No further top-up or future funding is assumed.",
             "","## Costs postponed by the stage change","",
             "Customer billing and card registration: $0 now because there is no checkout or payment acceptance. Public age-service minimums: $0 now because there is no public adult access. Paid launch legal/security packages, company-formation purchases, insurance and production support are not automatically incurred for this private prototype. They have not been declared unnecessary for a real launch. Any required advice or third-party access clearance must fit new approved funding or stop that activity. Never take payments through an incompatible processor or call a public adult beta a private demo.",
             "","## Future price hypotheses only","",
             "### Apple billing sensitivity — September 8\n\nUse **30%** as the conservative commission assumption. Apple's subscription guidance describes 70% proceeds in a subscriber's first year and 85% after one paid year, before applicable taxes. Approved eligible Small Business Program participants can receive the 15% commission rate earlier; do not assume enrollment. [Subscriptions](https://developer.apple.com/app-store/subscriptions/), [Small Business Program](https://developer.apple.com/app-store/small-business-program/).\n\n| Customer price | After 30% Apple fee | After 15% fee | Service-cost ceiling for 60% contribution on customer price, at 30% fee |\n|---|---:|---:|---:|\n| $19.99 | $13.99 | $16.99 | $2.00 |\n| $29.99 | $20.99 | $25.49 | $3.00 |\n| $49.99 | $34.99 | $42.49 | $5.00 |\n\nFormula: contribution = price × (1 − commission) − all variable service costs. These ceilings exclude fixed overhead, tax/refunds and acquisition, so they are not net-profit promises. Earlier roughly 63% web contribution estimates cannot be carried into Apple billing unchanged. Use quotas and prepaid top-ups only after measuring service cost; never promise unlimited generated video against these ceilings.\n\n### Optional GPU benchmark budget, not provisioned\n\nCurrent [Runpod pricing](https://www.runpod.io/pricing) lists a 24GB RTX 4090 Pod at $0.74/hour, 32GB RTX 5090 at $0.99/hour, and 48GB L40S at $1.09/hour. Ten test hours are **$7.40/$9.90/$10.90 GPU compute**, plus storage and applicable charges. Its Serverless 4090 tier lists $1.10/hour: **$0.55 for a continuously occupied 30-minute call**, before other costs and startup. Rates/availability are quotes to recheck at provisioning; the marketing blog and live price table differ, so use the table rather than combining them.\n\nFlex can scale to zero, but startup, execution and the idle timeout are billed; persistent storage still costs money. An 80GB standard network volume at $0.07/GB/month adds **$5.60/month**. Zero idle GPU time does not mean a zero-dollar account. [Billing rules](https://docs.runpod.io/serverless/pricing). A capped 10-hour, 80GB experiment would therefore start around $13–$17 using those Pod quotes, before incidental charges. No machine has been rented and no model has demonstrated the target call speed there.\n\n[Modal](https://modal.com/pricing) lists L4 at $0.000222/s, A10 at $0.000306/s and L40S at $0.000542/s: **$0.7992/$1.1016/$1.9512 per GPU-hour**. CPU, RAM and storage are additional; explicit region selection lists a 1.15–1.75 multiplier. Free credits are not assumed. These are alternative benchmark costs, not confirmation of content-policy or US deployment eligibility.\n\nMore system RAM helps keep weights available for offloading; it does not turn the 4060 Ti into a faster GPU. Benchmark a rental before buying a card. For scale, an always-running $0.74/hour worker costs about **$533 per 30 days**, so low utilization can erase subscription margin. Public prices need measured GPU occupancy per delivered call, startup behavior, rejected generations, support/refunds and demand data.","",
             "September 8's additional synthetic Cloudflare comparisons total **$0.01443 at published variable list prices for responses with known usage**, including the capability-prompt retest. One timed-out GLM request has unknown billed usage; this is not an invoice. The earlier Aura-2 experiment added $0.01806 nominally. These small tests use existing credentials, do not purchase a plan, and do not establish future production costs. Qwen and local Kokoro remain selected. [Measured comparison](LOCAL_POC.md#cloudflare-comparison--september-8-follow-up).",
             "",
             remote_clip_comparison(), "",
             "A warm RTX 4090 Pod at $0.74/hour costs $0.37 of GPU time per 30-minute call at full occupancy with one simultaneous call. At 25% occupied time it becomes $1.48 per served call; 24/7 operation costs $532.80 per 30 days. A 32GB RTX 5090 at $0.99/hour gives $0.495/$1.98/$712.80 under the same assumptions. These exclude storage, transport, other services and unused startup time. They are rental arithmetic, not measured concurrency or public-service quotes. Ten 4090 test hours cost $7.40 compute; no rental has been made, and Gateway credits cannot pay that separate provider.",
             "",
             "Cloudflare [Realtime SFU pricing](https://developers.cloudflare.com/realtime/sfu/pricing/) is $0.05/GB egress after its shared SFU/TURN allowance. A single 2Mbps downstream for 30 minutes is 0.45GB, or $0.0225 at that rate before protocol overhead and other billable traffic. GPU-provider egress is separate. This is transport only; WebRTC does not perform model inference.",
             "",
             "The existing commercial calculator remains available for later planning; its funded-pilot scenario is deferred, not an immediate requirement or committed fundraising target. Its assumptions are not mixed into the local budget. Full-inclusion feature quality and costs remain unvalidated.",
             "","| Future monthly offer | Price to test | Earlier direct contribution hypothesis |","|---|---:|---:|"]
    for plan in future['plans']:
        rows.append(f"| {plan['name']} | ${plan['price']:.2f} | {plan['margin']:.1%} |")
    rows += ["","Show prospective users clearly labeled price concepts; record qualified interest and objections without charging. Interview responses and investor meetings are not revenue. This stage deliberately has zero revenue, so its expense is a small planned loss. Its return is evidence: local inference measurements, a future demo, license findings and demand signals. Public launch/fundraising legal work and guarantees of investment are outside this budget. See [LOCAL_POC](LOCAL_POC.md), [REPORT](REPORT.md), [BUILD](BUILD.md) and [USA](USA.md).",""]
    return "\n".join(rows)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--write",action="store_true");p.add_argument("--json",action="store_true")
    p.add_argument("--payers",type=int,help="Override the steady-cohort snapshot only; launch cohorts remain in config")
    args=p.parse_args()
    if args.write and (args.json or args.payers is not None):
        p.error("--write cannot combine with output/assumption overrides")
    c=load()
    if args.payers is not None: c["assumptions"]["payers"]=args.payers
    try: output=json.dumps(dict(active_stage=c['active_stage'],demo=demo_forecast(c),deferred_unit_economics=calculate(c),deferred_launch=forecast(c)),indent=2) if args.json else report(c)
    except ValueError as e: p.error(str(e))
    if args.write:
        (ROOT/"docs/ECONOMICS.md").write_text(output,encoding="utf-8")
        print("Updated docs/ECONOMICS.md")
    else: print(output)

if __name__=="__main__": main()
