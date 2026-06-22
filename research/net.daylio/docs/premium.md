# Premium (billing, the is-premium gate, restore, offers)

Confirmed against **version_code 252**. Mapped classes: `PremiumStatusManager`,
`Prefs`, `BillingClientWrapper`, `PremiumRestoreModule`, `ProductSku`,
`SpecialOfferModule`. The premium/billing layer lives mostly under
`net.daylio.modules.purchases.*` (~240 classes); this maps the backbone.

## TL;DR — the hook point

**Premium status is one persisted boolean.** The app-wide gate is:

```
PremiumStatusManager.isPremium()  →  net.daylio.modules.purchases.d0.u6()Z
    return ((Boolean) ad.c.l(ad.c.D)).booleanValue();
```

`ad.c.D` is the typed preference whose underlying name is the string
**`IS_PRO_VERSION_PURCHASED`**. `u6()Z` is invoked from **62 call sites across 47
files** — it *is* the "is the user premium?" check. To observe premium, hook
`d0.u6()Z` and read the return value; to force it, override the return (or the
stored `ad.c.D`).

## How premium is determined & stored

- The central typed-preferences registry `Prefs` (`ad.c`) holds 255+ keys. The
  premium one is static field `ad.c.D` (name `IS_PRO_VERSION_PURCHASED`); a
  companion `ad.c.D0` ("premium status changed") is set alongside it.
- `PremiumStatusManager` (`d0`, impl of purchases interface `j`) owns the
  entitlement:
  - **reader:** `u6()Z` (above).
  - **writer:** private `p7(Z)` — **unconditionally** sets `ad.c.D := TRUE` (it
    *grants* premium). Its boolean argument is **not** the stored value; it is a
    type hint (false = lifetime, true = subscription) forwarded to `j.a`
    listeners only.
  - **grant entry points** (all funnel into `p7`): `onPremiumSubscribed(String)`
    = `I7`, `onPremiumLifetimeRestored(long)` = `T9`,
    `onPremiumSubscriptionRestored()` = `fb`.
  - **clear:** `onPremiumLost()` = `Y0` sets `ad.c.D := false`.

## Products / SKUs (`ProductSku`, enum `md.v`)

Maps Daylio products → Google-Play product ids:

| Enum constant | Play product id | Type |
| --- | --- | --- |
| `SUBSCRIPTION_MONTHLY` | `net.daylio.premium.monthly` (P1M, 1-wk trial) | subs |
| `SUBSCRIPTION_YEARLY_NORMAL` | `net.daylio.premium.yearly` (P1Y, 1-wk trial) | subs |
| `SUBSCRIPTION_YEARLY_CHEAPER` | `net.daylio.premium.yearly.offer` | subs |
| `SUBSCRIPTION_YEARLY_CHEAPEST` | `net.daylio.premium.yearly.expired_offer` | subs |
| `PREMIUM_LIFETIME` | `net.daylio.pro.lifetime` | inapp |
| `PREMIUM_LIFETIME_PLAY_PASS` | `net.daylio.pro` | inapp |

Plus `*_TO_MONTHLY` downgrade variants and `monthly.to_yearly`. Subscriptions use
Play type `"subs"`; lifetime/Play-Pass use `"inapp"`. (A sibling debug class is a
mock that returns hardcoded `SkuDetails` JSON — not mapped.)

## Billing flow

`BillingClientWrapper` (`b`, impl of `f` + `a3.i` = `PurchasesUpdatedListener`)
is the real Google Play facade. It builds the client via
`a.g(ctx).b().d(this).a()` (newBuilder → enablePendingPurchases →
setListener(this) → build), connects lazily (`getBillingClientAsync`), and checks
subscription support. It fans `onPurchasesUpdated` out to registered listeners.

`PremiumRestoreModule` (`e0`, impl of `k`) drives restore: queries owned
`"inapp"` then `"subs"` purchases, validates them, and on a valid purchase calls
`PremiumStatusManager`'s grant methods (`T9` / `fb`) — which flip `ad.c.D`.
`isRestoreInProgress()` = `hd()Z`.

## Special offers / trials

`SpecialOfferModule` (`pd`, impl of `ja`, where `ja extends j.a, ka`) schedules
special-offer start / last-chance / end alarms
(`SpecialOfferStart/LastChance/EndReceiver`), tracks the running offer, and gates
everything on premium (`ad.c.D`) so offers only show to non-premium users. As a
`j.a` listener it reacts to premium changes. The free-trial period (`P1W`) is part
of the SKU definitions, not a separate local timer.

## Notes / next threads

- `ad.c.D` is documented but not member-mapped: its initializer string sits in
  `<clinit>`, and its type (`ad.c$a`) has no unique string anchor. The
  class-level `Prefs` map + `d0.u6()` cover the hook surface; mapping `ad.c$a`
  structurally would enable a field-level map of `D`.
- The `net.daylio.data.purchases.*` model classes (subscription state, etc.) are
  obfuscated-name but stringless — they need member/structural anchors.
- Premium-status UI activities (`PremiumStatus*Activity`, `StartFreeTrialActivity`,
  …) keep their real names; no signatures needed.
