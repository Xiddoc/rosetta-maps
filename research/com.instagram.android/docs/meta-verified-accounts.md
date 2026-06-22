# Meta Verified & Account Switching / Accounts Center

Profile verification (**Meta Verified** + the Authenticity identity-document
flow) and **multi-account** switching / Meta Accounts Center linking. Defensive,
class-identity-only mapping. The flow UIs are Bloks-server-driven; the native
surface is URL handlers, Pando status models, and renamed `X/` fragments.
Logical→obfuscated names are in the map + `signatures.yaml`.

## Meta Verified / profile verification

- **`MetaVerifiedUrlHandlerActivity`** (`com.instagram.urlhandlers.metaverified`)
  is the `instagram://meta_verified` entry — dispatches Bloks routing controllers
  (`mv_mobile_routing_screen_controller`; analytics `mv_deeplink_navigation`).
  **`MetaSubscriptionsUrlHandlerActivity`** is the Meta Verified subscription/
  upsell hub (`com.bloks.www.meta_subs.unified_entry_point_screen.controller`).
- The verified-status model is `UserMetaVerifiedBenefitsInfoDict`
  (GraphQL `XDTUserMetaVerifiedBenefitsInfoDict`), with eligibility flags on
  `LiveTreeUserDict` (`is_eligible_for_meta_verified_label`).
  **`MetaVerifiedEnhancedContentProtectionHelper`** is a concrete MV benefit gate
  (`IGNMEBenefitContentProtectionUsageCheckQuery`).
- Identity-document upload runs the IdVerification fragment sequence
  (**`IdVerificationPhotoCaptureFragment`** renamed, recovered by redex name) and
  uploads via **`AuthenticityGraphApiUploaderWithRetries`**
  (`submit_to_authenticity_platform`). **`MetaVerifiedLinkFragment`** is the
  profile-links benefit. (There is no client-side `apply_for_verification` op —
  the apply flow is fully Bloks-driven.)

## Account switching / Accounts Center

- **`IgLoggedInUsersContentProvider$Impl`** (`com.instagram.contentprovider.users.impl`)
  is the canonical multi-account registry exported to other Meta apps — a
  MatrixCursor with `user_id`, `authorization_token`, `profile_pic_url`,
  `is_active_user`. Hook its `query` to enumerate/alter the logged-in set.
- **`AccountSwitchFragment`** (renamed) renders the switcher;
  **`AddAccountBottomSheetFragment`** (renamed) starts add-account.
- **`FxSsoViewModel`** (`com.instagram.fx.access.sso`) mints/caches the cross-app
  SSO token (`cached_ig_access_token`) for family-of-apps single sign-on;
  **`FxCalIGAccountsCenterRedirectActivity`** is the Accounts Center entry
  (`com.bloks.www.fxcal.settings.async`). **`AccountFamily`**
  (`com.instagram.accountlinking.model`) is the linked-account graph model;
  **`AccountLinkingMainGroupManagementFragment`** (renamed) the group-management UI.
