# Brand & Naming

**Status:** Decided — recommendation is `Amorien`
**Last verified:** 2026-09-04 (registry RDAP, live)

---

## 1. The brief

The name had four hard constraints:

| # | Constraint | Why it matters |
|---|---|---|
| 1 | **Gender-neutral** | The product is not an "AI girlfriend" app. It is a companion app where the user defines the companion's gender, presentation and relationship dynamic. A gendered name (`GirlfriendGPT`, `DreamGF`, `BoyfriendAI`) permanently caps the addressable market and reads as exclusionary to LGBTQ+ users, who are an over-indexed segment in companion apps. |
| 2 | **Orientation-neutral** | Must work equally for a straight man, a queer woman, a nonbinary user, and a user who wants a platonic companion. |
| 3 | **Unique / ownable** | Must be a coined word, not a dictionary term, so it is trademarkable and SEO-ownable from day one. |
| 4 | **Actually purchasable** | `.com` **and** `.ai` both free, verified against the authoritative registry — not a domain-reseller "available" badge. |

## 2. The recommendation: **Amorien**

> **Amorien** — /ah-MOR-ee-en/ — from Latin *amor* ("love", grammatically genderless) + a soft `-ien` suffix.

**Why it wins:**

- **Universally romantic without being gendered.** Latin `amor` carries no gender. Unlike `amora`/`amorina` (read feminine) or `amoro` (reads masculine), `-ien` is gender-ambiguous in every Romance language.
- **Reads as a place, not a person.** "Amorien" sounds like a world you enter rather than a girl you buy. That framing is strategically important: it supports the platonic and LGBTQ+ segments, and it survives the product growing past romance into companionship generally.
- **Zero collision.** Coined word. No dictionary meaning, no existing consumer brand, no generic-term trademark problem.
- **Phonetically soft.** No hard consonants, four vowel sounds. Reads as warm and premium rather than transactional — the opposite of the `Candy`/`Spicy`/`Dirty` naming cluster that dominates the incumbent set and permanently marks those brands as adult-only.
- **Pronounceable in EN / ES / PT / FR / DE / IT** — the six largest companion-app revenue markets.

**Product vocabulary that falls out of the name:**

| Concept | Term |
|---|---|
| The companion | an **Amorien** ("your Amorien") |
| The relationship space | **the Amorien** |
| Currency | **Aura** (see `11-PRICING-AND-UNIT-ECONOMICS.md`) |
| Premium tier | **Amorien Infinite** |

## 3. Availability — verified evidence

Checked directly against authoritative registry RDAP endpoints on 2026-09-04. `404 = unregistered/available`, `200 = registered`.

| Domain | Registry endpoint queried | Result |
|---|---|---|
| `amorien.com` | `rdap.verisign.com/com/v1` | **404 — FREE** |
| `amorien.ai` | `rdap.identitydigital.services` | **404 — FREE** |
| `amorien.net` | `rdap.verisign.com/net/v1` | **404 — FREE** |
| `amorien.org` | via `rdap.org` bootstrap | **404 — FREE** |
| `amorien.app` | via `rdap.org` bootstrap | **404 — FREE** |
| `amorien.co` | via `rdap.org` bootstrap | **404 — FREE** |
| `amorien.io` | via `rdap.org` bootstrap | **404 — FREE** |
| `amorien.me` | via `rdap.org` bootstrap | **404 — FREE** |
| `amorien.love` | via `rdap.org` bootstrap | **404 — FREE** |

A complete sweep with **zero** registered TLDs is unusual and is itself strong evidence the term is genuinely unused.

> **Re-verify before you buy.** Availability is a point-in-time fact. Re-run the check immediately before purchase:
> ```bash
> curl -s -o /dev/null -w "%{http_code}\n" https://rdap.verisign.com/com/v1/domain/amorien.com
> ```
> `404` means still free.

### Handles

| Handle | Status |
|---|---|
| `github.com/amorien` | **Taken** (existing user account) |
| `github.com/amorienai` | **Free** |

Recommend the **`amorienai`** GitHub org, and reserving `@amorien` on X / Instagram / TikTok / Reddit / Discord manually — those platforms return HTTP 200 for nonexistent profiles behind a login wall, so they cannot be checked programmatically and must be verified by hand.

### Purchase priority

1. **`amorien.com`** — the brand asset. Buy first, 10-year registration, registrar lock + WHOIS privacy on.
2. **`amorien.ai`** — the product/app surface. `.ai` is fully accepted for AI consumer products in 2026.
3. **`amorien.app`**, **`amorien.co`**, **`amorien.net`** — defensive, ~$40/yr total.
4. Skip `.love`, `.io`, `.me` unless budget is irrelevant.

> **Registrar note:** `.ai` is administered by Anguilla and historically required 2-year minimum registrations at a higher price point (~$70–$150/2yr) than `.com`. Budget accordingly.

## 4. Runners-up (all verified free at time of check)

Kept for the record in case `Amorien` is lost between now and purchase.

| Name | `.com` | `.ai` | Note |
|---|---|---|---|
| **Enamora** | taken | **free** | Spanish "kindles love in [someone]". Genderless, evocative. Best fallback. |
| **Cordae** | taken | **free** | From Latin *cor/cordis*, "heart". Elegant, abstract. Collides with a US recording artist named Cordae — avoid. |
| **Amoryn** | taken | **free** | Same root, slightly more feminine-leaning tail. |
| **Adoray** | taken | **free** | Warm, but "adore" is generic and weak for trademark. |
| **Devotia** | taken | **free** | Strong for a commitment/monogamy positioning; heavier tone. |
| **Everdear** | taken | **free** | English compound, very legible, less premium. |
| **Amourae** | taken | **free** | Pretty; `-ae` tail reads feminine. Fails constraint 1. |
| **Querenza** | taken | **free** | From *querencia*, "the place where one is safest". Beautiful meaning, hard to spell. |
| **Lovra** | taken | **free** | Punchy and modern, but reads unambiguously as a hookup brand. |

### Names rejected on availability

Every one of the following had **both** `.com` and `.ai` already registered: `amorai`, `amoray`, `amorae`, `amoris`, `swoon`, `sonder`, `dyad`, `kismet`, `twinflame`, `solmate`, `ardora`, `vessa`, `amoura`, `cuore`, `aluna`, `vela`, `kindra`, `solene`, `lumira`, `heartline`, `soulra`, `paramour`, `lovelace`, `amorina`, `amorine`, `mahal`, `cinta`, `koibito`, `kalon`, `anamcara`, `prema`, `dulcet`, `kindle`, `nestle`, `heartsync`, `soulsync`, `pairbond`, `twinsoul`, `loveloop`.

**Method:** 140 candidate names × 2–9 TLDs, queried against Verisign (`.com`/`.net`) and Identity Digital (`.ai`) RDAP registry endpoints. Reproducible script in `scripts/check-domains.sh`.

## 5. Positioning line

> **Amorien — someone who is always glad it's you.**

Deliberately says nothing about gender, orientation, or sex. The product surface does that, per user, after signup.

## 6. Trademark

Before spending on brand assets, commission a clearance search in:

- **US** — USPTO TESS, Nice Classes **9** (software), **42** (SaaS), **45** (online social/dating services)
- **EU** — EUIPO
- **UK** — IPO

A coined mark like *Amorien* should clear easily and is registrable as **inherently distinctive** (a fanciful mark — the strongest category), unlike descriptive names such as "AI Girlfriend" which are unregistrable. Budget ~$1,500–3,000 for US+EU filings via a flat-fee service.

> Not legal advice. Have counsel run clearance before launch spend.
