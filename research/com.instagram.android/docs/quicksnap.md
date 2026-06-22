# QuickSnap / QuickSends — BeReal-style dual camera

QuickSnap is Instagram's BeReal-style daily dual-camera feature (front+back
capture, time-limited, friends-only). It ships entirely under
`com.instagram.quicksnap` and `com.instagram.quicksends` — there is **no
`candid` package** in this build (an earlier "Candid" codename is fully renamed
to QuickSnap here). Class names are kept; members are `A0x`-rotated.

## Cross-app seen-state ContentProvider (the headline class)

- **`QuickSnapSeenStateProvider`** (`…quicksnap.viewer.seenstate.provider`,
  dex classes3) is a thin provider whose `<clinit>` binds the pref key
  `"quick_snap_last_updated_app_id"`. Manifest:
  `authorities="com.instagram.quicksnap.seenstate"`, `exported="true"`,
  `enabled="false"`. Real logic is in the nested **`$Impl`**.
- **`QuickSnapSeenStateProvider$Impl`** (dex classes2) extends
  `com.facebook.secure.content.delegate.TrustedAppsContentProviderDelegate` —
  the **cross-app trusted-content delegate** that lets other Meta apps (Facebook,
  the Moonshot/QuickSnap widget host) read/write QuickSnap seen-state. Bracketed
  log strings (`"[QuickSnapSeenState] Unknown path: "`,
  `"[QuickSnapSeenState] No session for userId: "`,
  `"[QuickSnapSeenState] Invalid URI: "`) and columns `seen_media_ids`,
  `media_ids`, `media_id`, `last_updated_app_id`, `app_id` mark its
  query/insert/update/delete paths. **Hook point:** observe or forge seen-state
  across Meta apps here.

## Data / API layer

- **`QuickSnapApi`** (`…quicksnap.data.api`) is the GraphQL surface. Persisted
  operations map to `xdt_*` docs: `IGQuickSnapGetQuickSnapsQuery` →
  `xdt_get_quick_snaps`, `IGQuickSnapUpdateSeenStateMutation` →
  `xdt_mark_quick_snap_seen`, `IGQuickSnapSendEmojiReactionMutation` →
  `xdt_send_quick_snap_emoji_reaction`, plus history, mute, "moods" (prompt
  content), trending-moods, hidden, and item queries. Request params:
  `sample_types`, `cached_media_ids`, `should_fetch_all_valid_media_ids`.
- **`QuickSnapRepository`** (`…data.repository`) orchestrates fetch + QPL logging
  and drives the flyout/prompt cadence via pref keys
  `quicksnap_last_flyout_newest_snap_timestamp_seconds` and
  `quicksnap_last_archive_open_timestamp_seconds`. Capture-metadata QPL
  annotations include `media_type`, `has_caption`, `is_flash_on`.

## Capture → preview → post flow

- **`QuickSnapCameraViewModel`** (`…camera.domain`, dex classes14) is the capture
  brain: a photo path (Bitmap) and a video path (File) each build a resolved
  capture model and write through a `QuickSnapRepository` field. (Pure logic, no
  string literals — not in the signature set; located by name.)
- **`QuickSnapMediaSaver`** (`…quicksnap.util`) saves snaps to the gallery
  (event `quick_snap_archive_preview_save`; error `"Failed to save video: media
  url is null"`).
- The capture UI is Jetpack-Compose (`QuickSnapCameraScreen.kt`) with the
  creation entry tile `QuickSnapCreationEntrypointView` and reaction-emitter
  overlays.

## Send / share

- **`QuickSendsManager`** (`com.instagram.quicksends`) fetches contacts and sends
  the QuickSnap to recipients (folder `quicksends_photos`; error `"Failed to
  fetch contacts"`). Paired with a share-sheet integration and consent store.

## Entry points

- Deep links via `QuickSnapUrlHandlerActivity` route
  `quick_snap_creation_camera`, `quick_snap_details`, `quick_snaps_from_author`
  (params `media_id`, `media_author_id`).
- A home-screen widget (`QuickSnapMediaWidgetProvider` + update receiver) shows
  the latest snaps, with actions `…appwidget.CREATION_CARD_CLICK` /
  `MEDIA_CARD_CLICK` / `UPDATE_ALARM`. (The widget/deeplink classes share their
  route/action strings with sibling classes and aren't cleanly pinnable to one
  class, so they're documented here but not in the signature set.)
