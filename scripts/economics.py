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


def gpu_session_cost(hourly_rate, call_minutes, startup_seconds=60, idle_seconds=90):
    """Single admitted call per GPU; overhead is charged once per cold session."""
    values = [hourly_rate, call_minutes, startup_seconds, idle_seconds]
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in values):
        raise ValueError('GPU session assumptions must be finite nonnegative numbers.')
    if hourly_rate == 0 or call_minutes == 0:
        raise ValueError('GPU rate and call duration must be positive.')
    return hourly_rate * (call_minutes*60 + startup_seconds + idle_seconds)/3600


def pilot_estimate(c):
    """Optional rental comparison; never a purchase or a paid-launch budget."""
    p = c['gpu_pilot']
    for key, value in p.items():
        if key not in {'quoted_at_utc', 'quote_url', 'offers'} and (
                isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0):
            raise ValueError('Pilot assumptions must be finite and nonnegative.')
    fees = p['processor_fraction_assumed'] + p['refund_fraction_assumed']
    if fees >= 1 or p['retry_fraction'] > 1:
        raise ValueError('Invalid pilot fee or retry fraction.')
    months = []
    for index, month in enumerate(demo_forecast(c)['months']):
        amount = month['electricity'] + p['gpu_5090_hour']*p['monthly_test_hours'] + p['stopped_storage_allowance_monthly']
        if index == 0:
            amount += p['existing_gateway_funding_with_fee']
        months.append(amount)
    calls = []
    for minutes in [30, 60]:
        inputs = minutes*p['replies_per_minute']*p['input_tokens_per_reply']
        outputs = minutes*p['replies_per_minute']*p['output_tokens_per_reply']
        dialogue = (inputs*p['input_dollars_per_million']+outputs*p['output_dollars_per_million'])/1e6
        transport = minutes*60*p['downstream_mbps']/8000*p['sfu_egress_per_gb']
        gpu = gpu_session_cost(p['gpu_5090_hour'],minutes,p['startup_seconds'],p['idle_seconds'])
        half_used = gpu_session_cost(p['gpu_5090_hour'],minutes/.5,p['startup_seconds'],p['idle_seconds'])
        calls.append(dict(minutes=minutes,input_tokens=inputs,output_tokens=outputs,dialogue=dialogue,transport=transport,
                          gpu=gpu,technical=(gpu+dialogue+transport)*(1+p['retry_fraction']),
                          technical_half_used=(half_used+dialogue+transport)*(1+p['retry_fraction'])))
    offers = []
    for offer in p['offers']:
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 for v in offer.values()) or offer['price']<=0:
            raise ValueError('Invalid pilot offer.')
        cost = offer['fulfillment_ceiling']+p['fixed_transaction_assumed']+offer['price']*fees
        contribution = offer['price']-cost
        offers.append(dict(offer,cost=cost,contribution=contribution,margin=contribution/offer['price'],
                           return_on_cost=contribution/cost))
    return dict(months=months,total=sum(months),cap=c['poc']['quarter_cap'],
                remaining=c['poc']['quarter_cap']-sum(months),calls=calls,offers=offers,fees=fees)


def report(c):
    from decimal import Decimal
    d=pilot_estimate(c);p=c['gpu_pilot']
    rows=[
        '# PWA pilot costs and pricing',
        '',
        'Checked September 8, 2026 US Eastern (September 9 UTC). Generated by scripts/economics.py from config/economics.json. The founder is the only engineer. Existing PC, coding subscriptions and living costs are excluded from incremental cash needs. No GPU has been rented and no paid public service is enabled.',
        '',
        '## What to rent',
        '',
        'Keep the 16GB rig for development. For the next hosted comparison, choose **one RTX 5090 32GB, 8 vCPU, 64GB RAM and 150GB NVMe**, in a US region, for a capped ten-hour experiment. Use on-demand scheduled sessions. The current TensorDock Orlando offer is below; the 4090 is the fallback if 5090 availability or runtime compatibility fails.',
        '',
        '| Listed configuration | Per running hour | Ten hours | 720 running hours |',
        '|---|---:|---:|---:|']
    for name,rate in [('RTX 4090 24GB',p['gpu_4090_hour']),('RTX 5090 32GB',p['gpu_5090_hour'])]:
        rows.append(f'| {name}; 8 vCPU / 64GB RAM / 150GB disk | ${rate:.4f} | ${Decimal(str(rate))*10:.2f} | ${Decimal(str(rate))*720:.2f} |')
    rows += [
        '',
        '[Public deployment listing](https://console.tensordock.com/deploy), captured 2026-09-09 01:31 UTC. These are configured offers, not the misleading 4GB-system-RAM defaults or a checkout invoice. Availability, taxes, stopped-disk billing, bandwidth and minimum funding require checkout confirmation. The listed 5090 host shows 99.15% uptime and a Low Uptime warning, versus 99.85% for the 4090: acceptable to evaluate, insufficient evidence for production reliability.',
        '',
        'The 5090 adds 8GB VRAM for about 16% more hourly cost. It needs a compatible Blackwell/CUDA runtime. Neither faster calls nor model fit has been demonstrated on this rental. TensorDock is a content-policy candidate, not an approved host for this project; obtain acceptance for the complete service. GPU ownership does not override model licenses. [Host policy](https://docs.tensordock.com/legal-information/acceptable-use-policy-aup).',
        '',
        '## First three months: optional technical pilot',
        '',
        'Assume ten rented test hours per month, a $5/month stopped-storage allowance, local power at 300W and $0.20/kWh for 100/30/30 hours, and the already funded $10 Gateway purchase budgeted at $10.50 with its published funding fee. Storage is an allowance pending a host quote; power is not measured.',
        '',
        '| Item | Month 1 | Month 2 | Month 3 |',
        '|---|---:|---:|---:|',
        '| Local electricity | $6.00 | $1.80 | $1.80 |',
        f"| GPU experiment | ${p['gpu_5090_hour']*10:.2f} | ${p['gpu_5090_hour']*10:.2f} | ${p['gpu_5090_hour']*10:.2f} |",
        '| Stopped-storage allowance | $5.00 | $5.00 | $5.00 |',
        '| Existing Gateway credit purchase, fee estimate included | $10.50 | $0.00 | $0.00 |',
        '| New paid engineering / local preview hosting | $0.00 | $0.00 | $0.00 |',
        f"| Planned total | ${d['months'][0]:.2f} | ${d['months'][1]:.2f} | ${d['months'][2]:.2f} |",
        '',
        f"Quarter planning total: **${d['total']:.2f}**, including the existing credit purchase, leaving **${d['remaining']:.2f}** under the ${d['cap']:.0f} planning cap. Do not add the old contingency pool a second time. Credit consumption spends prepaid funds, not another cash purchase. The cap is not an implemented provider control or authorization to rent. This budget covers technical demonstrations, not a public adult launch, legal clearance, domain purchases or merchant onboarding.",
        '',
        '## Full call cost flow',
        '',
        '| Stage | Selected prototype component | Cost treatment |',
        '|---|---|---|',
        '| Capture / endpoint detection | Browser AudioWorklet and VAD | Client device; current endpoint wait approximately 0.65s |',
        '| Recognition | faster-whisper Base English int8 | CPU on the same worker; capacity must be tested |',
        '| Context and planning | Cloudflare @cf/qwen/qwen3-30b-a3b-fp8 | $0.051/M input tokens, $0.34/M output tokens |',
        '| Voice | Kokoro-82M ONNX, af_sarah | Same-worker CPU; no external per-character tariff |',
        '| Speech video | MuseTalk 1.5 + SD VAE + Whisper-tiny, prepared body media | Occupied GPU session, not per-frame API pricing |',
        '| New scenes / body footage | FLUX.2 Klein 4B / LTX benchmark pipeline | Separate preparation work; never assumed free or instantaneous |',
        '| Public media transport, proposed | Cloudflare Realtime SFU / WebRTC | $0.05/GB egress at marginal list price |',
        '| App, memory and billing | Cloudflare application/data services + accepted hosted checkout | Separate from model and GPU costs; not deployed |',
        '',
        '[Qwen rates](https://developers.cloudflare.com/workers-ai/models/qwen3-30b-a3b-fp8/), [SFU rates](https://developers.cloudflare.com/realtime/sfu/pricing/). The current demo uses loopback HTTP media, not WebRTC. Hosted dialogue and the LTX preparation pipeline are neutral-demo selections, not an approved adult-content route. In particular, LTX terms exclude the intended explicit scope; a lawful commercial pipeline needs separately qualified assets/models. See USA.md.',
        '',
        'Sizing scenario: two replies/minute, 2,000 input tokens and 60 output tokens per reply. Bound context; do not resend an unlimited transcript. One 2Mbps downstream is 0.45GB per 30 minutes before protocol overhead. Calculations ignore free tiers and add a 20% inference/transport contingency. Same-worker CPU speech is included in the configured rental, but co-resident throughput is untested.',
        '',
        '| Call | Input / output tokens | Dialogue | GPU, including 60s startup + 90s idle | SFU | Technical total +20% | At 50% call occupancy +20% |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for r in d['calls']:
        rows.append(f"| {r['minutes']} min | {r['input_tokens']:,.0f} / {r['output_tokens']:,.0f} | ${r['dialogue']:.4f} | ${r['gpu']:.4f} | ${r['transport']:.4f} | ${r['technical']:.2f} | ${r['technical_half_used']:.2f} |")
    rows += [
        '',
        'At 50% occupancy, allocated running time doubles; startup/idle overhead is added once per call. These totals exclude GPU-provider egress, storage, application usage, verification, moderation services, support, payment fees, acquisition and taxes. The 20% allowance is not a measurement of retries or sufficient funding for every failed render. Full-body arbitrary generation may cost substantially more than the prepared-motion demo.',
        '',
        '## Pricing experiments after approval',
        '',
        'Keep video metered. Test the following hypotheses with prospective users before charging. Fulfillment ceilings reserve more than the 50%-occupancy technical estimates for application, disk and routine handling; replace them with actual bills and accepted verification/moderation quotes. Price calculations assume 16% processing, 2% refund/loss provision and $0.50 fixed per purchase. **These are assumptions, not a processor offer.**',
        '',
        '| Video pack | Test price | Fulfillment ceiling | Fees + fulfillment | Contribution | Contribution margin |',
        '|---|---:|---:|---:|---:|---:|']
    for r in d['offers']:
        rows.append(f"| {r['minutes']} minutes | ${r['price']:.2f} | ${r['fulfillment_ceiling']:.2f} | ${r['cost']:.2f} | ${r['contribution']:.2f} | {r['margin']:.1%} |")
    rows += [
        '',
        'These are approximately 52–53% contributions, before fixed overhead, annual registration, acquisition, onboarding checks and founder labor. They are not net profit or measured willingness to pay. At 18% variable fees, a 500% return on all costs is mathematically unavailable even before service costs. A 300% return requires a price above $42.85 for a 60-minute pack with $3 of non-percentage costs; that conflicts with the affordable offer. Prefer sustainable unit contribution and measured retention over an arbitrary markup target.',
        '',
        'For early product research: limited free text and short voice notes; paid phone calls and video minutes. A $4.99 voice-hour concept with a $0.50 fulfillment ceiling yields about 62% contribution under the same assumed fees. No unlimited inference, proactive paid media or unmetered video. Free access needs a per-user and account-wide spend cap; it is not costless. General 15-second video pricing remains unvalidated until a permitted model passes latency, identity and delivery-cost tests.',
        '',
        'The earlier $19.99/$29.99/$49.99 bundles and two always-on GPU pools are deferred calculator scenarios retained in JSON output for sensitivity analysis. They are not the selected pilot or advertised plans.',
        '',
        '## Payments and first-month risk',
        '',
        '**CCBill is the first processor to request a quote from**, because it serves adult businesses. Its published US/Canada annual card registration is Visa $950 + Mastercard $1,000 = **$1,950/year**. Processing percentage, reserve, payout delay, chargeback charges and acceptance of interactive AI calls require underwriting. No monthly PSP fee does not mean no upfront card cost. [Pricing](https://ccbill.com/pricing), [US/Canada registration](https://ccbill.com/doc/risk-difference-between-low-risk-and-high-risk-accounts).',
        '',
        'Segpay is an alternative with published AI-site requirements, including restrictions on uploads and generation/review arrangements. Do not assume internal-only monitoring will satisfy its acquiring bank. [AI approval guidance](https://segpay.com/blog/your-roadmap-for-adult-ai-site-approval/). No processor has approved AI Mate, and no application has been sent.',
        '',
        f"The registration alone averages ${p['registration_yearly']/12:.2f}/month but may need cash upfront. At the proposed 60-minute pack contribution, about {math.ceil(p['registration_yearly']/d['offers'][1]['contribution'])} sales cover that annual registration alone. Legal/access-control work and every other fixed expense remain additional. Reserves delay cash even when a sale has positive contribution. There is no evidence for guaranteed first-month profit or a zero-upfront paid adult launch. Validate the call with the small technical budget before committing merchant-launch money.",
        '',
        '## Scaling without idle burn',
        '',
        'Reserve one tested GPU slot for a complete call. Keep the worker and temporal state warm between sentences. For the pilot use scheduled sessions, maximum one worker and a bounded rental window. Release it after calls finish; verify whether stopping actually releases GPU charges and what disk charges continue. Avoid interruptible spot instances for live calls.',
        '',
        'Scale asynchronous scene/clip workers to zero if an accepted provider supports it. Serverless is useful for uneven demand, but cold starts, active seconds, idle timeout and persistent storage still count. TensorDock managed serverless behavior has not been qualified here. Runpod is excluded for the intended explicit service under its terms; its neutral benchmark rates are not our launch architecture.',
        '',
        'For later public calls: reserve worst-case spend before admission, cap concurrent workers and session length, keep a short disconnect grace, stop admitting before the spending ceiling and drain existing sessions. Measure slots per worker and peak demand before growing capacity. An always-on 5090 at this rate consumes $534.60 per 30 days before extras. These lifecycle and billing controls are proposed, not deployed.',
        '',
        'Reproduce on this configured PC: ./.venv/Scripts/python.exe scripts/economics.py --write. Machine output labels the older commercial forecast as deferred. Figures are rounded independently; totals use unrounded rates. Technical evidence: LOCAL_POC.md; architecture: BUILD.md; release eligibility: USA.md.',
        ''
    ]
    return '\n'.join(rows)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--write",action="store_true");p.add_argument("--json",action="store_true")
    p.add_argument("--payers",type=int,help="Override the steady-cohort snapshot only; launch cohorts remain in config")
    args=p.parse_args()
    if args.write and (args.json or args.payers is not None):
        p.error("--write cannot combine with output/assumption overrides")
    c=load()
    if args.payers is not None: c["assumptions"]["payers"]=args.payers
    try: output=json.dumps(dict(active_stage=c['active_stage'],demo=demo_forecast(c),optional_gpu_pilot=pilot_estimate(c),deferred_unit_economics=calculate(c),deferred_launch=forecast(c)),indent=2) if args.json else report(c)
    except ValueError as e: p.error(str(e))
    if args.write:
        (ROOT/"docs/ECONOMICS.md").write_text(output,encoding="utf-8")
        print("Updated docs/ECONOMICS.md")
    else: print(output)

if __name__=="__main__": main()
