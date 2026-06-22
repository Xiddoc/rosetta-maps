# Shopping / Commerce & Branded Content

Instagram's commerce surface — product browsing, the shopping bag, checkout,
product tagging — plus the **Branded Content / Paid Partnerships** creator tools.
Class names are kept; REST endpoint paths and GraphQL op names are the anchors.
Logical→obfuscated names are in the map + `signatures.yaml`.

## Shopping / Commerce

- **`ShoppingCartFragment`** (`com.instagram.shopping.fragment.cart`) is the
  global shopping bag index (analytics `instagram_shopping_bag_index_load_success`;
  drives the checkout-awareness interstitial across PDP/drops/shop-home/bag).
- **`MerchantShoppingCartFragment`** (same package) is the per-merchant bag and
  **checkout launch** (`instagram_shopping_merchant_bag_load_success`; builds
  checkout with `checkoutSessionId`/`merchantId`; payment rail `IG_NMOR_SHOPPING`).
- **`UnifiedProductApi`** (`com.instagram.commercepage.api`) is the unified
  product-info data source (request key `unified_product_info_<n>_page`).
- **`ShoppingTaggingFeedRepository`** (`com.instagram.shopping.repository.taggingfeed`)
  backs tagging products onto a post (GraphQL `ig_affiliate_deeplink_validation`).
- The product detail page is driven by `ProductDetailsPageArguments` +
  `commercepage`; the product/merchant data model is `com.instagram.user.model.Product`
  and product tags are `com.instagram.model.shopping.ProductTag`. A newer agentic
  shopping surface lives under `com.instagram.shoplab`.

## Branded Content / Paid Partnerships

- **`BrandedContentApi`** (`com.instagram.brandedcontent.repository`) is the full
  creator↔brand REST surface — 11 `business/branded_content/…` endpoints covering
  brand-approval requests (`create_brand_approval_request/`), partner whitelist
  (`get_whitelist_sponsors/`), and the branded-content-ads opt-in
  (`update_branded_content_opt_in_status/`).
- **`AdsEligibilityController`** (`com.instagram.brandedcontent.adseligibility.controller`)
  decides paid-partnership-ads eligibility for a piece of media, reading
  `media_branded_content_sponsor_igid` (the sponsor field) and
  `has_partnership_ads_enabled` (the ads toggle).
- **`BrandedContentSettingsRepository`** drives creator-marketplace + dynamic-ads
  settings (`xfb_is_user_eligible_for_creator_dynamic_ads`,
  `onboard_creator_to_creator_marketplace/`).
- **`BrandedContentDisclosureBaseViewModel`** (`com.instagram.brandedcontent.disclosure`)
  is the "Add paid partnership label" disclosure flow; audience gating lives in
  the `BrandedContentGatingInfo` schema (country/min-age).
