# Stories

Instagram **Stories** — the ephemeral 24-hour reel of photos/videos. Internally
Stories live under `com.instagram.reels` / `instagram.features.stories` (the
"reels" package is Stories; *Reels-the-video-format* is `clips`). Class names for
data models are kept; the viewer/tray UI is renamed into `X/` but each renamed
class preserves its real name in a `__redex_internal_original_name` field, which
the map captures (e.g. `StoriesTrayControllerImpl → X.2uX`,
`StoryRepliesListFragment → X.Rp8`). Logical→obfuscated names and anchors are in
the map + `signatures.yaml`.

## Tray & viewer

- **`StoriesTrayControllerImpl`** (renamed `X.2uX`) owns the main-feed Stories
  tray: it preloads reels and launches the viewer (trace
  `MainFeedReelTrayController.maybePreloadAndLaunchViewer`) and the story camera.
  Prime hook for "which story is opening".
- **`ReelViewerFragment`** (`instagram.features.stories.fragment`) is the
  on-screen story player; the modern coordinator initializes with the trace
  `StoriesMVVM.StoriesViewerComponentCoordinator.init`.
- **`ReelDashboardFragment`** (`instagram.features.stories.dashboard.fragment`)
  is your own-story dashboard, identified by the GraphQL op
  `XCXPIGStoryUnifiedFeedbackQuery`.
- **`ReelDashboardViewersAdapter`** (renamed `X.D3U`) binds the "seen-by" viewer
  list on your own story.

## Replies & reactions

- **`StoryRepliesListFragment`** (renamed `X.Rp8`) lists replies to a story.
- **`ReelQuickReactorsListFragment`** (renamed `X.VOx`) lists people who quick
  (emoji) reacted. Story emoji reactions also flow through QuickSnap's
  `IGQuickSnapSendEmojiReactionMutation` (see `quicksnap.md`).

## Data model, cache & seen-state

- **`Interactive`** (`com.instagram.reels.interactive`) is the story interactive
  **sticker model** — geometry + type of every tappable overlay (its `toString`
  emits `InteractiveType: ` and per-sticker dumps). Serialized by
  `InteractiveSerializer`.
- **`ReelResponseCache`** (`com.instagram.reels.store`) is the in-memory + on-disk
  cache of fetched reel responses (traces `ReelResponseCache.getCacheAndVend` /
  `.writeToDiskInternal`). Backed by a Room seen-state DB (`user_reel_medias`
  table). Hook here to observe/inject cached story sets.

## Creation, highlights & archive

- **`StoryDraftsStore`** (`com.instagram.creation.capture.quickcapture.storydrafts.model`)
  persists story drafts (error `Failed to de-serialise story drafts`). Story
  publish is the REST `media/configure_to_story/` call.
- **`ManageHighlightsFragment`** (renamed `X.E3z`) creates/edits Highlights
  (archived stories pinned to a profile).
- **`ArchiveReelPeopleFragment`** (`com.instagram.archive.fragment`) lists the
  people in your story archive (`archive/reel/friends_with_history/`).
