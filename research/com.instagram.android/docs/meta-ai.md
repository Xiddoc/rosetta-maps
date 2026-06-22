# Meta AI / AI Studio / Generative AI

Instagram's on-app generative-AI surface: Meta AI chat threads, **AI Studio**
(create/manage your own AI persona/character accounts), **Imagine** image
generation/editing, and **GenAI voices**. The richest, most stable classes are
the GraphQL repository/service classes — each carries both a literal operation
name (e.g. `"IGAiStudioYourAisQuery"`) and the persisted-query doc/API name
(e.g. `"xfb_fetch_viewer_created_genai_personas"`), which are server-contract
strings immune to member rotation. Logical→obfuscated names and the exact anchor
regexes are in the map + `signatures.yaml`; this is the behaviour narrative.

## Meta AI chat threads

- **`AiAgentThreadLauncher`** (`com.instagram.direct.aiagent.navigation`, dex
  classes10) is the central launcher/creator for Meta AI direct threads and
  "side chats". It builds local sidechat threads and hits two REST endpoints:
  `direct_v2/ig_meta_ai_side_chat_new_session/` and
  `direct_v2/create_ig_meta_ai_side_chat/`. Thread-type constants
  `"META_AI_CANONICAL"` / `"META_AI_SIDECHAT"` distinguish the main Meta AI chat
  from per-context side chats; intent-extra keys include `main_chat_thread_id`,
  `sidechat_thread_id`, `persona_id`, `context_media_id`, `send_welcome_message`.
  The local-thread creation is tagged `"DirectThreadStoreImpl.createLocalSidechatThread"`.
  **Hook point:** the two `…side_chat…` endpoint sites gate every entry into a
  Meta AI thread.
- **`DirectMetaAiThreadUrlHandlerActivity`** (`com.instagram.urlhandlers.directmetaaithread`)
  is the deeplink → Meta-AI-thread bridge (manifest-declared, `exported=false`).
  It reads `original_url` / `entry_point` / `prompt` extras and self-identifies
  with the module tag `"direct_meta_ai_thread_url_handler"`.
- **`AiBotVoiceFragment`** (`…direct.fragment.thread.aichats.immersive`) is the
  voice-mode immersive surface (tag `"ai_bot_voice_fragment"`, requires
  `RECORD_AUDIO`).

## AI Studio — persona/character creation & management

- **`YourAisRepository`** (`com.instagram.aistudio.yourais`) fetches the personas
  the viewer created: op `"IGAiStudioYourAisQuery"` / doc
  `"xfb_fetch_viewer_created_genai_personas"`, persona typename
  `"XIGGenAIIGCreatorPersona"`, audience constants `ANYONE_WITH_LINK`,
  `CLOSE_FRIENDS`, `PUBLIC_FOR_IG_PRIVATE_ACCOUNTS`.
- **`AiProfileCreationRepository`** (`…aistudio.creation.ugc.repository`) drives
  persona creation — multiple GraphQL ops including
  `"AICharacterProfileCreationAiInfoQuery"` (doc `xfb_fetch_genai_persona`),
  eligibility/content queries, and `"IGAIProfilesSuggestedUsernameQuery"` (doc
  `"xdt_suggest_genai_persona_profile_usernames"`).
- **`CreateAiAccountService`** (`…aistudio.creation.ugc.util`) is the
  account-creation flow, identifiable by full-sentence status strings:
  `"Your AI has not been approved yet"`, `" reached the maximum number of AI
  profiles"`, `"Created user is null"`.

## GenAI Imagine — image generation & editing

- **`GenAIImagineService`** (`com.instagram.genai.imageservice.service`) drives
  Imagine generation/editing. Success branch typename
  `"XFBGenAIIGImagineResultSuccess"`; edit-mode enums `CONTEXTUAL_BACKGROUND`,
  `AI_TAP_TO_EDIT`, `AI_FILTERS`, `AI_FONTS_I2I`, `AI_FONTS`, `STICKER_PACK`;
  params `prev_image_id`, `preset_id`, `concept_scores`.
- **`GenAIImagineQueryGraphQLApi`** (`…imageservice.api`) builds the GraphQL
  variables — wire keys `num_images`, `source_handle`, `mask_handle`,
  `return_unwatermarked`, `meta_ai_access_point`, `swap_params`, `edit_tool_name`,
  `camera_session_id`. (`return_unwatermarked` is a notable flag.)
- **`GenAIImageQueryGraphQLApi`** (`…imageservice.api`) is the image
  query/inpaint path: op `"IGSharingGenAIImageQuery"` / doc
  `"xig_ig_genai_image_query"`, with mask/segmentation vars
  `src_opaque_token_handle`, `mask_opaque_token_handle`, `points`.
- **`AiLocationSummaryRepository`** (`com.instagram.metaai.location.viewmodel`)
  is the Meta-AI "what's around here" location summary: op
  `"IGAiLocationSummaryQuery"` / doc `"xig_genai_location_summary"`.

## GenAI voices

- **`AIVoicesRepository`** (`com.instagram.genai.voices.datasource`): voice
  transform mutation `"IGDirectAIVoiceTransformMutation"` (doc
  `ig_voice_effects_apply`) and style list `"IGAIVoiceList"` (doc
  `"xig_ai_voice_styles"`); effect constants `CUSTOM_S2S`, `CUSTOM_TTS`,
  `harp_overlay`, `cupid`, `client_dsp`; param `audio_file_handle`.
- **`CustomVoiceEffectRepository`** (same package): list/create custom voice
  effects — `"IGListCustomAIVoiceEffectsQuery"` (doc
  `"ig_list_custom_ai_voice_effects"`) and
  `"IGCreateCustomAIVoiceEffectMutation"` (doc `ig_create_custom_ai_voice_effect`).

## Notes / gaps

- Persona/agent **data-model** holders (`…api.schemas.*MetaAiBotInfo`,
  `aistudio.intf.AiCharacterProfileUser`) are generated Pando/Parcelable trees
  with `A0x` getters and few literals — identify them via the repositories above,
  not directly.
- There is also a Meta-side RTC voice-call surface in `com.facebook.rtc.*`
  (e.g. `MetaAICallDismissalService`, action
  `com.facebook.rtc.notification.metaai.END_SESSION_ACTION`) — outside the
  `com.instagram.*` tree, noted for voice-call instrumentation.
