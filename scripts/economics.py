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


def report(c):
    a=c["assumptions"]; d=calculate(c); f=forecast(c); t=f["totals"]
    rows=["# Adult-first PWA economics","",
          f"USD; checked {c['as_of']}. Generated from [config](../config/economics.json). {c['scope']}. This is a cash-planning model with startup costs expensed at kickoff, not financial statements, a benchmark, a binding quote or a customer forecast. All included allowances are fully redeemed. Sales tax is assumed collected separately and remitted; income taxes and paid engineering are excluded.",
          "","## Decision","",
          f"Budget **${t['funding_without_receipts']:,.2f} before relying on any customer payout** for the illustrated three-month pilot, including a ${a['working_buffer']:,.0f} unspent liquidity buffer. Under the modeled settlement timing the month-end minimum is ${t['minimum_funding']:,.2f}; that smaller number depends on receipts arriving as assumed and does not model intramonth payment dates. Round the stronger budget up, obtain quotes, and do not spend if launch eligibility fails.",
          "","## Unit economics and monthly offer","",
          f"Fully configured GPU allowances: auxiliary ${a['aux_gpu_hour']:.2f}/hour, renderer ${a['gpu_hour']:.2f}/hour. These exceed advertised GPU-only starting rates and are not verified US offers. One stream and {a['occupancy']:.0%} occupied renderer capacity give ${d['renderer_minute']:.3f}/connected minute. Transport, contingency and a floor produce **${d['live_minute']:.3f}/visual minute**. Warm auxiliary capacity is a separate fixed cost; incremental media/message allowances cover burst capacity and processing. Do not charge the same GPU hours twice when replacing estimates with bills.",
          f"Voice-only ${a['phone_minute']:.2f}/minute; accepted portrait clip ${a['clip_cost']:.2f}; photo ${a['photo_cost']:.2f}; scene ${a['scene_cost']:.2f}. These are cost ceilings to validate including loading, retries, rejected outputs and checks. They do not price unrestricted general video. Each paid account includes ${a['paid_messages']:.2f} incremental text/voice-note processing and ${a['support']:.2f} support allowance; human support exceeding this raises cost.",
          f"Payments: {a['processor_fraction']:.0%} processing + {a['loss_fraction']:.0%} refunds/chargeback-loss allowance + ${a['payment_fixed']:.2f} per monthly payment, with a {a['reserve_fraction']:.0%} rolling reserve. These are assumptions, not a CCBill quote. Refunds/loss allowance is conservatively modeled as withheld cash. Actual fees, chargebacks, minimums and reserves may differ.",
          "","| Plan | Price | Visual / voice minutes | Photos / portrait clips / scenes | Direct cost | Contribution | Margin |",
          "|---|---:|---:|---:|---:|---:|---:|"]
    for p in d["plans"]:
        rows.append(f"| {p['name']} | ${p['price']:.2f} | {p['live_minutes']} / {p['phone_minutes']} | {p['photos']} / {p['clips']} / {p['scenes']} | ${p['cost']:.2f} | ${p['profit']:.2f} | {p['margin']:.1%} |")
    rows += ["","Direct contribution is before warm capacity, overhead, verification, acquisition and startup. It is not net profit. Feature entitlements cannot be sold before their adult-use license, capability and cost gates pass. Free access is capped at 25 verified pilot accounts; no unlimited free generation.",
             "","| Optional pack | Price | Direct cost | Margin |","|---|---:|---:|---:|"]
    for p in d["packs"]:
        rows.append(f"| {p['name']} | ${p['price']:.2f} | ${p['cost']:.2f} | {p['margin']:.1%} |")
    rows += ["","Separate general-video experiment: an 80GB node allowance of $2.50/hour costs $0.42 for two five-minute attempts. Adding $0.25 for other fulfillment yields $0.67; two 20-minute attempts instead yield $1.92. These times are illustrative, not Wan benchmarks, and producing a coherent 15-second result may require extensions. Proposed ceiling $1.25/accepted clip, proposed price $9.99, direct cost including assumed payment deductions $3.55, contribution $6.44 (64.5%). A 60% contribution target requires price at least (delivery + $0.50) / (1 - 0.18 - 0.60), or $7.95 at the ceiling. No general-video revenue, cost or entitlement is included in the forecast. Activate only after measured cost and delivery time support a separately priced offer.",
             "","## Startup purchases and review allowances","",
             "| Item | Budget | Basis |","|---|---:|---|"]
    for key,label,basis in [
        ("setup_technical","Technical POC","Capped GPU experiments; no purchase made"),
        ("registration","Card registration","CCBill US/Canada Visa $950 + Mastercard $1,000 annual reference; obtain initial merchant quote"),
        ("legal_setup","Legal, contracts and state review","Narrow launch allowance; not a 50-state clearance or quote"),
        ("security_setup","Independent security/privacy review","Narrow pilot review allowance, not a comprehensive audit"),
        ("entity_setup","Entity/administrative setup","Jurisdiction-dependent allowance; avoid duplicate cost if already formed"),
        ("domain_setup","Domain","Allowance")]:
        rows.append(f"| {label} | ${a[key]:,.2f} | {basis} |")
    if a["tooling_setup"]:
        rows.append(f"| Additional one-time tooling | ${a['tooling_setup']:,.2f} | Separate from monthly subscriptions |")
    rows.append(f"| **Startup total** | **${d['startup']:,.2f}** | Charged once in M1 for conservative budgeting |")
    rows += ["","Technical validation and host eligibility precede larger commitments. Registration is not paid merely to keep experimenting. Annual card fees recur outside this quarter; save $162.50/month thereafter if the $1,950 annual figure applies. Legal/security overruns are possible and not covered by an unlimited guarantee.",
             "","## Fixed monthly allowances","","| Item | Per month |","|---|---:|"]
    for label,value in c["monthly_fixed_breakdown"].items():
        rows.append(f"| {label} | ${value:,.2f} |")
    rows.append(f"| **Total excluding GPUs** | **${a['monthly_fixed']:,.2f}** |")
    rows += ["","The $100 age-service minimum and $1.25/new unique user are procurement allowances, not Yoti prices: $1/check plus 25% retry provision. An accepted internal method could reduce vendor spend, but has development, privacy and review costs. No provider quote or insurance coverage is bound. Cloudflare's $20 neutral inference allowance is not a quoted token tariff; adult conversations stay on the approved private route. Warm dialogue/audio GPU adds $432 per 30-day pilot month. GPU disk costs persist when compute is stopped; a running idle VM is billable.",
             "","## Three months from kickoff","",
             "Scenario: M1 builds with no paying customers and 120 auxiliary GPU hours; M2 has 50 payers; M3 has 150. M3 keeps 40 of M2's 50 and adds 110, illustrating 20% monthly churn. New paid users are separate from the initial 25 free users; no free-to-paid conversion or repeated renewal verification is assumed. Plan mix: 25% Together, 50% Closer, 25% Companion. Counts/mix are planning expectations, not demand evidence. M2/M3 only happen if development and all release gates pass; timing may slip.",
             f"Settlement assumption: eligible proceeds arrive {c['launch']['settlement_lag_months']} model month(s) later; reserve release is outside this quarter. Month 3 receivables and restricted reserves are not available cash.",
             "","| Item | M1 build | M2 pilot | M3 pilot | Three months |","|---|---:|---:|---:|---:|"]
    for label,key in [("Active payers","payers"),("New unique age checks","verified"),("Gross revenue","revenue"),
                      ("One-time startup","startup"),("Fixed non-GPU overhead","fixed"),("Auxiliary GPU","aux"),
                      ("Paid service delivery","delivery"),("Uncovered renderer availability","idle"),
                      ("Free service delivery","free_delivery"),("Age checks","verification"),
                      ("Customer acquisition","acquisition"),("Founder cash pay","founder_pay"),
                      ("Processing/refund/loss allowance","withheld"),("Total modeled expense","expenses"),
                      ("Profit / loss","profit"),("New restricted reserve","reserve"),
                      ("Cash payouts received","receipts"),("Cash paid out, excluding withheld fees","cash_out"),
                      ("Net cash change","cash_change")]:
        values=[m[key] for m in f["months"]]
        if key in ("payers","verified"):
            display=[str(v) for v in values]+["—" if key=="payers" else str(sum(values))]
        else:
            display=[f"${v:,.2f}" for v in values]+[f"${sum(values):,.2f}"]
        rows.append("| "+label+" | "+" | ".join(display)+" |")
    rows += ["",f"Quarter reconciliation: profit ${t['profit']:,.2f} minus restricted reserves ${t['reserve']:,.2f} minus unsettled eligible proceeds ${t['unsettled']:,.2f} = cash change ${t['cash_change']:,.2f}. The ${a['working_buffer']:,.0f} buffer is capital kept available, not an expense or reserve fee.",
             f"The quarter has {t['verified']} new age checks. Four minutes of founder review per account at $30/hour adds ${t['review_labor']:,.2f} of unpaid economic labor value, excluded from cash expenses. Baseline acquisition cost is zero only as an organic-founder-distribution assumption; it is not evidence users arrive free.",
             "","## Funding and downside cases","",
             "| Scenario | Three-month expense | Profit / loss | Funding with no payouts + buffer |","|---|---:|---:|---:|"]
    scenarios=[("Baseline",c),("No paying users; retain scheduled pilot capacity",no_sales(c))]
    for label,updates in [("CAC $20 per new payer",dict(cac=20)),
                          ("Visual delivery $0.08/min; photos/scenes/clips double",dict(live_minute_floor=.08,photo_cost=.10,scene_cost=.20,clip_cost=.30)),
                          ("Two auxiliary GPUs throughout",dict(aux_gpu_hour=1.20)),
                          ("Founder cash pay $3,000/month",dict(founder_labor=3000)),
                          ("Legal/security quotes total $9,000",dict(legal_setup=6000,security_setup=3000))]:
        x=copy.deepcopy(c);x["assumptions"].update(updates);scenarios.append((label,x))
    for label,x in scenarios:
        z=forecast(x)["totals"]
        rows.append(f"| {label} | ${z['expenses']:,.2f} | ${z['profit']:,.2f} | ${z['funding_without_receipts']:,.2f} |")
    rows += ["","Stress cases change one factor at a time and can combine. No-sales operation is a downside budget, not a reason to keep spending after failure. At 160 new paid users, $20 CAC adds $3,200. Founder pay and hired engineering are separate: illustrative 160–320 hours at $75/hour adds $12,000–$24,000 if outsourced. Neither the hourly rate nor effort is a quote. Unlimited investigations, legal defense, hardware purchase and a full national launch are outside this pilot budget.",
             "","## Operating break-even and release decision","",
             f"Weighted revenue is ${d['arpu']:.2f}/payer and direct contribution ${d['arpu']-d['unit_cost']:.2f} before fixed costs. At the configured {a['payers']} active-payer snapshot, ongoing expense is ${d['recurring_cost']:,.2f}, revenue ${d['revenue']:,.2f}, and operating contribution after modeled overhead ${d['recurring_profit']:,.2f}; this snapshot excludes new-user verification, acquisition and startup recovery.",
             "No guarantee of first-month profit is possible. With zero M1 revenue, its startup/build expense is a loss in this planning model. A profitable recurring month does not repay startup automatically and can still precede payment settlement. Target about 60% direct contribution, measure retention and CAC, then require cash runway for already-promised usage. Do not treat a reserve or prepaid annual liability as profit.",
             "","Sources: [TensorDock advertised rates](https://www.tensordock.com/), [CCBill registration reference](https://ccbill.com/doc/visa-and-mastercard-payment-processing-faqs), [CCBill pricing](https://ccbill.com/pricing), [Yoti age-service overview](https://www.yoti.com/business/age-verification/). Actual full-node offers, processor terms, vendor minimums, adult model performance and licensing acceptance remain unresolved. See [BUILD](BUILD.md) and [USA](USA.md).",""]
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
    try: output=json.dumps(dict(unit_economics=calculate(c),launch=forecast(c)),indent=2) if args.json else report(c)
    except ValueError as e: p.error(str(e))
    if args.write:
        (ROOT/"docs/ECONOMICS.md").write_text(output,encoding="utf-8")
        print("Updated docs/ECONOMICS.md")
    else: print(output)

if __name__=="__main__": main()
