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
    startup=sum(a[k] for k in ("setup_technical","registration","legal_setup","security_setup","tooling_setup","domain_setup"))
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

def report(c):
    a=c["assumptions"];d=calculate(c)
    rows=["# Adult-first PWA economics","",f"USD, checked {c['as_of']}. Generated from [config](../config/economics.json). {c['scope']}. No benchmark, binding provider quote or customer forecast. Full allowance redemption; before income tax. No paid tier launches until its included adult modalities pass the REPORT requirements.",
          "","## Unit delivery and payment assumptions","",
          f"Renderer node \u0024{a['gpu_hour']:.2f}/hour, {a['streams']} concurrent stream, {a['occupancy']:.0%} occupancy. Renderer allocation \u0024{d['renderer_minute']:.3f}/connected minute; transport, contingency and floor produce \u0024{d['live_minute']:.3f}/visual minute. A separate warm auxiliary GPU pool costs \u0024{d['aux_fixed']:.0f}/month and is counted below. One provider does not mean one GPU holds every model.",
          f"Voice-only \u0024{a['phone_minute']:.2f}/minute; accepted portrait video \u0024{a['clip_cost']:.2f}; photo \u0024{a['photo_cost']:.2f}; prepared scene \u0024{a['scene_cost']:.2f}. Paid text/recorded voice/check-ins/memory \u0024{a['paid_messages']:.2f}/month plus \u0024{a['support']:.2f} support allowance. These are budgets requiring measured acceptance/retry costs.",
          f"Processor {a['processor_fraction']:.0%} + refunds/losses {a['loss_fraction']:.0%} + \u0024{a['payment_fixed']:.2f}/transaction; hold {a['reserve_fraction']:.0%} of gross receipts. All are planning assumptions, not CCBill quotes.",
          "","## Monthly plans: full usage","",
          "| Plan | Price | Visual / voice min | Photos / videos / scenes | Direct cost | Contribution | Margin |",
          "|---|---:|---:|---:|---:|---:|---:|"]
    for p in d["plans"]:
        rows.append(f"| {p['name']} | \u0024{p['price']:.2f} | {p['live_minutes']} / {p['phone_minutes']} | {p['photos']} / {p['clips']} / {p['scenes']} | \u0024{p['cost']:.2f} | \u0024{p['profit']:.2f} | {p['margin']:.1%} |")
    rows+=["","Optional proactive photos/videos consume these included allowances only after opt-in; no extra surprise charge. Failed preparation restores the user's credit but may still cost us. Do not use unused credits as the profitability assumption.",
           "","| Optional pack | Price | Direct cost | Margin |","|---|---:|---:|---:|"]
    for p in d["packs"]:
        rows.append(f"| {p['name']} | \u0024{p['price']:.2f} | \u0024{p['cost']:.2f} | {p['margin']:.1%} |")
    rows+=["","## First-month funding at configured cohort","",
           "| Item | Budget | Basis |","|---|---:|---|",
           f"| Technical POC | \u0024{a['setup_technical']:.0f} | Fixed experiment cap |",
           f"| Card registration | \u0024{a['registration']:.0f} | CCBill US/Canada reference, subject to approval/quote |",
           f"| Legal/state/provider review | \u0024{a['legal_setup']:.0f} | Planning allowance, not a quote or completed national review |",
           f"| Independent security review | \u0024{a['security_setup']:.0f} | Narrow pilot scope allowance, not a full audit quote |",
           f"| Development tools/API allowance | \u0024{a['tooling_setup']:.0f} | Not a published GPT-6 price; excludes existing subscriptions |",
           f"| Domain | \u0024{a['domain_setup']:.0f} | Budget |",
           f"| Warm auxiliary inference | \u0024{d['aux_fixed']:.0f} | {a['aux_hours']} hours x \u0024{a['aux_gpu_hour']:.2f} |",
           f"| Platform, storage, monitoring, transactional delivery | \u0024{a['monthly_fixed']:.0f} | Monthly allowance |",
           f"| Free-account delivery | \u0024{a['free_users']*a['free_user']:.2f} | {a['free_users']} accounts |",
           f"| Paid delivery, excluding withheld payment fees | \u0024{a['payers']*sum(p['share']*p['delivery'] for p in d['plans']):.2f} | Full included usage, {a['payers']} payers |",
           f"| Uncovered renderer availability | \u0024{d['idle_topup']:.2f} | Minimum {a['renderer_open_hours']} hours; no double counting allocated GPU |",
           f"| Internal age-check processing | \u0024{d['verification']:.2f} | \u0024{a['verification_per_new_user']:.2f}/new free/paid user, no vendor fee |",
           f"| Working buffer | \u0024{a['working_buffer']:.0f} | Liquidity, not an expense |",
           f"| **Cash funding before receipts** | **\u0024{d['funding_before_receipts']:.2f}** | Assumes no customer receipts fund promised month-one delivery |"]
    rows += ["",f"Internal review is not free economically: {a['verification_minutes']} minutes/account at \u0024{a['review_hour_value']:.0f}/hour values age-review time at \u0024{d['verification_labor']:.2f} for this cohort. Founder cash pay defaults to \u0024{a['founder_labor']:.0f}; engineering labor remains excluded. Development or legal overruns require more capital, not relaxed release gates.",
             "","## Profit versus available cash","",
             "| Payers | Revenue | All first-month modeled expense | Profit/loss | Cash after assumed hold |",
             "|---|---:|---:|---:|---:|"]
    for n in (20,100,250,300,500):
        x=copy.deepcopy(c);x["assumptions"]["payers"]=n;z=calculate(x)
        rows.append(f"| {n} | \u0024{z['revenue']:.2f} | \u0024{z['first_cost']:.2f} | \u0024{z['first_profit']:.2f} | \u0024{z['cash_after_reserve']:.2f} |")
    thresholds={}
    for key in ("first_profit","cash_after_reserve"):
        thresholds[key]=None
        for n in range(1,10001):
            x=copy.deepcopy(c);x["assumptions"]["payers"]=n
            if calculate(x)[key]>=0:
                thresholds[key]=n;break
    rows += ["",f"At the assumed plan mix, first-month expense break-even is about {thresholds['first_profit']} payers; cash break-even after the modeled hold is about {thresholds['cash_after_reserve']}. Fractions in plan mix are expectations; actual sales mix changes these thresholds. A waitlist is not collected revenue. No sales, settlement date or profit is guaranteed.",
             "","## Stress cases at configured cohort","",
             "| Change | Funding before receipts | First-month profit |","|---|---:|---:|"]
    for label,updates in [("Adult photo/scene/clip costs double",dict(photo_cost=a['photo_cost']*2,scene_cost=a['scene_cost']*2,clip_cost=a['clip_cost']*2)),("Adult visual delivery budget doubles",dict(live_minute_floor=d['live_minute']*2)),("Quote-dependent $600 registration",dict(registration=600)),("No internal API fee but $1 vendor fallback",dict(verification_per_new_user=1)),("25% renderer occupancy",dict(occupancy=.25)),("CAC $5",dict(cac=5)),("Legal budget $3,000",dict(legal_setup=3000)),("Founder pay $3,000",dict(founder_labor=3000))]:
        x=copy.deepcopy(c);x["assumptions"].update(updates);z=calculate(x)
        rows.append(f"| {label} | \u0024{z['funding_before_receipts']:.2f} | \u0024{z['first_profit']:.2f} |")
    rows+=["","The $600 registration scenario is an illustrative USD allowance for a lower-fee approved quote, not a verified EUR conversion or proof that Verotel Basic supports this visual-call business. Its public chart lists EUR 500 annual registration but excludes webcam billing on Basic and has additional recurring fees; confirm full scope.",
           "","Recommended target: roughly 60% direct contribution margin, then positive cash after overhead. A 300-500% return is no longer a requirement. At scale, retention, service quality and acquisition costs determine profit. Keep at least one month of fulfillment/refund runway; do not take restricted reserves or unearned annual subscriptions as spendable profit.",
           "","Sources: [CCBill fees](https://ccbill.com/doc/visa-and-mastercard-payment-processing-faqs), [CCBill pricing](https://ccbill.com/pricing), [Verotel chart](https://www.verotel.com/en/pricechart.html), [TensorDock](https://www.tensordock.com/). Processor approval, appropriate internal age assurance and model/content suitability are not established.",""]
    return "\n".join(rows)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--write",action="store_true");p.add_argument("--json",action="store_true");p.add_argument("--payers",type=int)
    args=p.parse_args()
    if args.write and (args.json or args.payers is not None):
        p.error("--write cannot combine with output/assumption overrides")
    c=load()
    if args.payers is not None: c["assumptions"]["payers"]=args.payers
    try: output=json.dumps(calculate(c),indent=2) if args.json else report(c)
    except ValueError as e: p.error(str(e))
    if args.write:
        (ROOT/"docs/ECONOMICS.md").write_text(output,encoding="utf-8")
        print("Updated docs/ECONOMICS.md")
    else: print(output)

if __name__=="__main__": main()
