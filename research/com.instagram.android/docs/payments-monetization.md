# Payments & Creator Monetization

The payment client surface (**FBPay**, W3C Payment Request, ShopPay, creator
payout) and **creator subscriptions** (Fan Club). This maps public class identity
only — no secrets. Class names are kept; REST endpoint paths and GraphQL
typenames are the anchors. Logical→obfuscated names are in the map +
`signatures.yaml`.

## Payments / FBPay

- **`IGPaymentMethodsAPI`** (`com.instagram.fbpay.paymentmethods.data`) is the
  payment-methods data layer (list/add stored methods over GraphQL via the FBPay
  executor).
- **`IsReadyToPayServiceImpl`** (`com.instagram.fbpay.w3c.ipc`) is the exported
  W3C Payment Request "isReadyToPay" binder (manifest action
  `org.chromium.intent.action.IS_READY_TO_PAY`) — queried by a Chrome/Custom-Tabs
  payment flow; its sibling `FBPaymentServiceImpl` is the W3C payment-app service.
  The FBPay web/UI surfaces are `FBPayIgWebView` (a `SecureWebView`) and the W3C
  `PaymentMethodsActivity` / `PaymentActivity` / `DemaskCardActivity`.
- **`UserPayApi`** (`com.instagram.userpay.api`) is the creator "user pay" /
  earnings-insights REST surface (`api/v1/creators/user_pay/insights/`).
- **`PayoutApi`** (`com.instagram.payout.api`) is creator payout / financial-entity
  setup (`api/v1/creators/incentive_platform/set_financial_entity_information/`).

## Creator subscriptions / monetization

- **`FanClubApi`** (`com.instagram.fanclub.api`) is the creator-subscription
  (Fan Club) REST surface — `api/v1/fan_club/creators_subscribed_to/`,
  `…/blocked_members/`, `…/welcome_video/`, `…/promotional_video/`.
- **`FanClubInfoDictImpl`** (`com.instagram.api.schemas`) is the subscription
  data model attached to a user (GraphQL typename `XDTFanClubInfoDict`; obfuscated
  accessors carry subscriber/eligibility flags + counts).
- **`MonetizationApi`** (`com.instagram.monetization.api`) is the monetization
  onboarding/gating REST surface
  (`api/v1/creators/onboarding/get_monetization_products_onboarding_data/`,
  `…/partner_program/get_monetization_products_gating/`). Subscriber-only content,
  the consideration/setup funnel, and member-list management live in the
  `com.instagram.fanclub.*` sub-packages.
