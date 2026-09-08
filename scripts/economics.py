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
        delivery=base+p["live_minutes"]*live+p["phone_minutes"]*a["phone_minute"]+p["clips"]*a["clip_cost"]
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
    recurring=n*unit+a["monthly_fixed"]+a["free_users"]*a["free_user"]+a["founder_labor"]+idle_topup
    startup=a["setup_technical"]+a["registration"]+a["legal_setup"]
    acquisition=n*a["cac"]
    verification=(n+a["free_users"])*a["verification_per_new_user"]
    first_cost=recurring+startup+acquisition+verification
    revenue=n*arpu
    return dict(plans=plans,packs=packs,live_minute=live,renderer_minute=renderer,arpu=arpu,unit_cost=unit,
                idle_topup=idle_topup,recurring_cost=recurring,startup=startup,verification=verification,
                revenue=revenue,first_cost=first_cost,first_profit=revenue-first_cost,
                first_roi=revenue/first_cost-1 if first_cost else None,
                recurring_profit=revenue-recurring, cash_after_reserve=revenue-first_cost-revenue*a["reserve_fraction"])

def report(c):
    a=c["assumptions"];d=calculate(c)
    rows=["# Adult PWA economics","",f"USD, {c['as_of']}. Generated from [config](../config/economics.json). Every cost is an assumption unless a source is expressly identified. Full allowance redemption. No adult-host approval or inference benchmark completed.",
          "","## Unit budget","",
          f"Renderer: \u0024{a['gpu_hour']:.2f}/hour / ({a['streams']} streams x {a['occupancy']:.0%} occupied capacity x 60) = \u0024{d['renderer_minute']:.4f}/connected minute. Add \u0024{a['auxiliary_per_live_minute']:.3f} auxiliary and \u0024{a['transport_per_minute']:.4f} transport, apply {a['contingency']:.0%} contingency and floor at \u0024{a['live_minute_floor']:.3f}: \u0024{d['live_minute']:.4f}/live minute.",
          f"Phone \u0024{a['phone_minute']:.3f}/minute; accepted 15-second portrait clip \u0024{a['clip_cost']:.2f}; paid text/recorded voice/memory \u0024{a['paid_messages']:.2f}/month; support \u0024{a['support']:.2f}. Free accounts \u0024{a['free_user']:.2f}/month, capped at {a['free_users']}. These self-hosted budgets do not use fal adult generation or hosted Cloudflare adult inference.",
          f"Payment scenario: {a['processor_fraction']:.0%} processing + {a['loss_fraction']:.0%} refunds/losses + \u0024{a['payment_fixed']:.2f}/transaction. Obtain quotes. 300% return on cost = 75% margin; 500% = 83.33%.",
          "","## Monthly plans","",
          "| Plan | Price | Visual min | Phone min | Clips | Total direct cost | Contribution | Return on cost |",
          "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for p in d["plans"]:
        rows.append(f"| {p['name']} | \u0024{p['price']:.2f} | {p['live_minutes']} | {p['phone_minutes']} | {p['clips']} | \u0024{p['cost']:.2f} | \u0024{p['profit']:.2f} | {p['roi']:.1%} |")
    rows+=["","| Prepaid pack | Price | Direct cost | Return on cost |","|---|---:|---:|---:|"]
    for p in d["packs"]:
        rows.append(f"| {p['name']} | \u0024{p['price']:.2f} | \u0024{p['cost']:.2f} | {p['roi']:.1%} |")
    rows+=["","These are contribution returns before company overhead and first-user verification. Packs include $0.10 handling; do not sell them to unverified accounts. Service credits are not cash wallets. No automatic overages or reliance on unused credits.",
           "","## Company cash scenarios","",
           f"Recurring fixed \u0024{a['monthly_fixed']:.0f}; renderer availability floor {a['renderer_open_hours']} hours x \u0024{a['gpu_hour']:.2f}, adding only the portion not already allocated to calls. Startup: \u0024{a['setup_technical']:.0f} technical budget + \u0024{a['registration']:.0f} card registration + \u0024{a['legal_setup']:.0f} unquoted legal expense. Legal zero means excluded/unquoted, NOT unnecessary. Founder labor \u0024{a['founder_labor']:.0f}, CAC \u0024{a['cac']:.0f}, verification \u0024{a['verification_per_new_user']:.2f}/new free and paid account.",
           "","| Payers | Revenue | First-month cost | First-month profit | Return | Later-month profit* |","|---|---:|---:|---:|---:|---:|"]
    for n in (20,100,500,1000):
        x=copy.deepcopy(c);x["assumptions"]["payers"]=n;z=calculate(x)
        rows.append(f"| {n} | \u0024{z['revenue']:.2f} | \u0024{z['first_cost']:.2f} | \u0024{z['first_profit']:.2f} | {z['first_roi']:.1%} | \u0024{z['recurring_profit']:.2f} |")
    rows+=["","*Later month assumes the same retained users, no new acquisition/verification/setup, and excludes an annual registration accrual. Capacity is expandable: higher cohorts require more renderer hours/groups; the model allocates them through each live minute. It does not claim one GPU serves the whole cohort.",
           "","## Stress at configured payer count","",
           "| Change | Live cost/min | First-month profit | Middle-plan direct return |","|---|---:|---:|---:|"]
    for label,update in [("18% combined fees",dict(processor_fraction=.16,loss_fraction=.02)),("One stream, 25% occupancy",dict(streams=1,occupancy=.25)),("One stream, 10% occupancy",dict(streams=1,occupancy=.10)),("CAC $5",dict(cac=5)),("Legal $3,000",dict(legal_setup=3000)),("Founder labor $3,000",dict(founder_labor=3000))]:
        x=copy.deepcopy(c);x["assumptions"].update(update);z=calculate(x)
        rows.append(f"| {label} | \u0024{z['live_minute']:.4f} | \u0024{z['first_profit']:.2f} | {z['plans'][1]['roi']:.1%} |")
    rows+=["",f"Configured first-month cash after a {a['reserve_fraction']:.0%} payment hold: \u0024{d['cash_after_reserve']:.2f}. Holds are cash restrictions, not expenses. Provider balances and unsettled receipts need working capital.",
           "","Price floor = (delivery + fixed transaction fee + allocated overhead) / (1/(1+target return) - percentage fees/losses). At 18%, a 500% total-cost return is impossible even with free inference. At 14%, it leaves just 2.67% of sales for all other costs; none of these offers achieves 500%. Do not relabel markup on GPU cost as company profit.",
           "","If combined fees/losses are 18%, price the same visual packs at $19.99/30 minutes and $34.99/60 minutes to retain over 300% direct return at the base delivery budget. Equivalent subscription prices are $29.99/$44.99/$64.99. These still exclude verification/acquisition and company overhead; remeasure before offering.",
           "","At the default mix, a $1 verification charge for every new payer makes 300% first-month company return unattainable even as cohort size grows under these prices. Existing-account recurring economics can improve, but must include annual registration accrual and actual retention. This forecast does not claim 300% company profit.",
           "","Technical POC budget $100-$250 can test rendering privately before merchant activation; it cannot fund a legal adult launch. CCBill currently lists Visa $950 plus Mastercard $1,000 annually for US/Canada high-risk accounts. Verify applicability and quote.",
           "","Sources: [TensorDock starting prices](https://www.tensordock.com/), [FlashHead benchmark](https://github.com/Soul-AILab/SoulX-FlashHead), [Cloudflare transport](https://developers.cloudflare.com/realtime/sfu/pricing/), [CCBill registration](https://ccbill.com/doc/visa-and-mastercard-payment-processing-faqs). $0.90 complete renderer node/hour is a budget, not TensorDock's advertised GPU-only floor or a reserved US quote.",""]
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
