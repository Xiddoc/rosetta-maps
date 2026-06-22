# Community Notes & Fundraisers / Donations

Crowd-sourced context **Community Notes** and charitable **Fundraisers**. Both
are largely Bloks/server-driven; the native surface is a launcher util, Pando
data models on media, and renamed `X/` fragments. Logical→obfuscated names are in
the map + `signatures.yaml`.

## Community Notes

- **`CommunityNotesUtil`** (`com.instagram.communitynotes`) holds all the Bloks
  launch ids: `com.bloks.www.community_notes.composer` (write a note),
  `…community_notes.rating` (rate a note helpful/not),
  `…community_notes.request_note`. Its `A05` orchestrates the NUX gate
  (`QPCommunityNotes`) → friction → composer.
- The media-attached model is **`CommunityNotesInfoImpl`** (Pando,
  `XDTCommunityNotesInfo`) with 4 Boolean eligibility/visibility flags
  (can-show / has-note / can-rate / can-request), read off a feed-media dict.
  **`CommunityNotesHubUrlHandlerActivity`** is the deep-link hub entry. The note
  text/rating UI is rendered entirely server-side via Bloks (no on-device note
  content class).

## Fundraisers / donations

(Charitable fundraisers — distinct from Live Stars/gifts, which are in `live.md`.)

- **`NewFundraiserInfo`** (`com.instagram.model.fundraiser`) is the in-app
  create/draft model (title/description/charity, goal). The resolved fundraiser
  model is `FundRaiser` (`XDTFundRaiser`), with donation-amount and consumption-
  sheet config models alongside.
- **`FundraiserStickerSearchController`** (renamed `X.SAk`) runs the searchable
  nonprofit/charity picker (`fundraiser/story_charities_search/`).
  **`ReelFundraiserDonorsListFragment`** (renamed `X.RZ2`) fetches the donor list
  (`media/story_fundraiser_donations/`). **`FundraiserNudgeQuery`** (renamed) is
  the GraphQL nudge (`IGFundraiserNudgeDecisionQuery`). User-level capability flags
  (`can_create_new_standalone_personal_fundraiser`, `charity_id`) live on
  `LiveTreeUserDict`; the REST request builders for enable/disable/untag are
  renamed `X/` classes anchored on their unique `fundraiser/*` paths.
