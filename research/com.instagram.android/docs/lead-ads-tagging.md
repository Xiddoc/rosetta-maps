# Lead Ads / Lead Gen & Tagging

Advertiser **lead generation** forms and post **tagging** (people / product /
collab). Class names under `com.instagram.leadads.*` / `com.instagram.tagging.*`
are kept; the IAB-prefill helpers are renamed `X/`. Logical→obfuscated names are
in the map + `signatures.yaml`.

## Lead Ads / Lead Gen

- **`LeadFormRepository`** (`com.instagram.leadads.repository`) fetches the form
  (`LeadGenDeepLinkQuery`) and submits it via mutation
  `xfb_lead_gen_deep_link_user_info_create` (payload `ad_id`, `lead_gen_data_id`,
  `fields_data`, `disclaimer_responses`, `submission_session_id`,
  `submitted_to_ig_user_id` = the advertiser). There is a parallel
  `PAID_IN_THREAD_FORMS` path for DM lead forms.
- **`LeadFormQuestionsRepository`** drives conditional/branching questions
  (`xfb_lead_gen_conditions_user_interaction`). **`LeadAdsActivity`** orchestrates
  fetch/open/submit. **`LeadGenFormBaseQuestion`** is the per-question model; the
  leadgen-core `LeadForm` (`XDTLeadForm`) is the resolved form payload. Prefill/
  disclaimer in the in-app browser runs through obfuscated `X/` helpers
  (`lead_gen_iab_prefill_disclaimer_bottom_sheet`) — behavioral hook points, not
  mappable kept classes.

## Tagging

- **`TaggingActivity`** (`com.instagram.tagging.activity`) is the photo/video
  tagging host (`instagram_shopping_product_tagging_tab_impression`).
  **`PeopleTagListFragment`** lists people tags + collab (`pending_collab_people`).
- **`TaggingSuggestionsRepository`** is the people-tag search/picker backend
  (`TaggingSuggestionsBffsQuery`, followers query `xdt_api__v1__friendships__followers`);
  **`TaggingSuggestionsViewModel`** performs add-tag (`Failed to add tag`).
- The tag model is **`Tag`** (abstract base; holds the normalized `PointF`
  position) with **`PeopleTag`** (`com.instagram.model.people`, adds `user_id`/
  `categories`) as the concrete person tag. Product tags reuse the `Tag`
  hierarchy. A serializer emits the tag diff (`added`/`removed`/`untagged`) as
  part of media upload. Face-detection confidence (`low_confidence`) arrives with
  suggestions; there is no dedicated on-device face-detect class in
  `com.instagram.tagging`.
