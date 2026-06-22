# Reels / Clips creation — drafts, teleprompter, music, publish

The Reels ("clips") creation pipeline: record in the clips camera → edit on the
"sundial" timeline → add a music sticker → optionally read a teleprompter script
while recording → save to drafts (exposed cross-app via a ContentProvider) →
publish. Class names are kept; members are `A0x`-rotated. Logical→obfuscated
names and anchor regexes are in the map + `signatures.yaml`.

## Clips drafts ContentProvider (cross-app surface)

- **`ClipsDraftProvider`** + nested **`$Impl`**
  (`com.instagram.creation.drafts.contentprovider`; outer in dex classes3, `$Impl`
  in classes12). Manifest-registered with `authorities` == the FQCN,
  `exported="true"`, `enabled="false"`; `$Impl` extends
  `com.facebook.secure.content.delegate.TrustedAppsContentProviderDelegate` (the
  cross-app trusted surface that exposes clips drafts to other Meta apps). Its
  query resolves the `UserSession` from a URI userId segment
  (`"[IG] No session found for userId: "`) and serializes draft previews to JSON
  with stable keys: `last_save_time`, `caption`, `media_id`, `cover_photo_asset`,
  `thumbnail_video`, `total_segment_duration_ms`, `remix_model`,
  `created_at_time`, `is_pinned`, `is_basel_template`, `share_only_to_profile`,
  `deleted_at_time`, `is_importing_from_server`, `draft_origin`. URI shapes:
  1 segment = list previews; 2 = single draft (`"[IG] No draft found for
  draftId: "`); 3 + `files` = open a draft asset file via `ParcelFileDescriptor`.
  Backed by `IgClipsDraftDataSource` + `ClipsDraftAssetRepository`. **Primary
  hook point** for reading/observing clips drafts.

## Camera entry & editor

- **`CameraConfiguration`** (`com.instagram.creation.cameraconfiguration`) is the
  Parcelable threaded through the camera entry (capture mode + a set of
  capture-format enums); the deep-link entry is `ClipsCameraUrlHandlerActivity`
  (`com.instagram.urlhandlers.clipscamera`, extends `UserSessionUrlHandlerActivity`).
  (No in-body string literal — named but not signature-anchored.)
- The editor/timeline is the **"sundial"** package
  (`…creation.capture.quickcapture.sundial.store.*`): `ClipsVideoStore`,
  `ClipsAudioStore`, `ClipsStitchedAudioStore`, `ClipsVirtualVideoStore`, with
  `ClipsTimelineBottomSheetViewController` / `ClipsAudioMixingDrawerController`
  driving timeline + audio-mix UI. Kept names, weak string anchors — documented,
  not signed.

## Teleprompter

- **`TeleprompterCardScriptKt`** (`com.instagram.teleprompter.ui.script`,
  dex classes14) renders the scrolling script over the recording preview. The
  teleprompter subsystem is entirely Jetpack-Compose UI; the Compose
  composition-trace strings are fully-qualified and rotation-stable (e.g.
  `com.instagram.teleprompter.ui.script.PlaceholderScript (TeleprompterCardScript.kt:165)`),
  with `ScriptTextUnderscrollSpacer`, `TransparentTopScrollBlocker`,
  `ScriptTextOverscrollSpacer`. No separate recording-side controller exists —
  the teleprompter is UI-only.

## Music sticker

- **`MusicBrowserHomeFragment`** (`com.instagram.music.search`, dex classes12) is
  the music search/browse home (analytics `import_audio_postcap`,
  `extract_audio_dialog_dismiss`, `music_browser_use_audio_error`,
  `spotlight_banner_selection`; opens the `audio_page` modal). It selects a track
  into a `MusicAssetModel`.
- **`MusicAssetModel`** (`com.instagram.music.common.model`, dex classes3,
  Parcelable) is the core audio model carried search → sticker → editor → publish,
  with factories from API track / original sound / `TrackData` / Pando / sticker.
- **`MusicOverlayStickerModel`** (same package, Pando `TreeWithGraphQL`) is the
  licensing/attribution-bearing sticker (carries `AudioMutingInfoIntf` and the
  licensing booleans); its interface `MusicOverlayStickerModelIntf` keeps logical
  getter names. **`AudioPageAssetModel`** (`com.instagram.clips.audio.model`)
  builds a stable `audio_page_<id>` cache key.

## Publish

- **`FollowersShareFragment`** (`instagram.features.creation.publishscreen.fragment.feed`
  — note the top-level `instagram.` package, not `com.instagram.`) is the
  feed/clips publish (share) screen: module `media_broadcast_share`, impression
  `external_share_view_impression`, config `hashtagCountSnackbarConfig`. Sibling
  `ClipsProfileVisibilityFragment` handles clips visibility at publish.

## Flow (summary)

`ClipsCameraUrlHandlerActivity` / `CameraConfiguration` (record) → sundial
stores (edit/timeline) → `MusicBrowserHomeFragment` → `MusicAssetModel` /
`MusicOverlayStickerModel` (add music) → `TeleprompterCardScriptKt` overlay →
`IgClipsDraftDataSource` persistence exposed via `ClipsDraftProvider` →
`FollowersShareFragment` (publish).
