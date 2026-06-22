# Comments

The comments subsystem (`com.instagram.comments.*`) — reading a comment thread,
composing/posting, likes, and moderation (pin/hide/filter). Class names are mostly
kept; the moderation network helpers are kept `*NetworkRequestsKt` facades with
unique REST paths, and the comments UI fragment is renamed into `X/`.
Logical→obfuscated names and anchors are in the map + `signatures.yaml`.

- **`CommentsFetcher`** (`com.instagram.comments.request`) fetches the comment
  thread (params `sort_order`, `comment_filter_param`, `can_support_threading`;
  prefetch marker `ongoing_fetch_clash`). The data layer above it is
  `MediaCommentListRepository` (`…comments.mvvm.data`), which owns post / edit /
  bulk-hide / like / repost / uncover.
- **`CommentOffensiveCheckService`** (`…comments.mvvm.data.network`) is the
  pre-post moderation check (`media/comment/check_offensive_comment/`).
- Moderation network helpers (kept `…mvvm.data.network`):
  **`MediaCommentPinUnpinNetworkRequestsKt`** (`media/%s/pin_comment/%s/`),
  **`HideActionNetworkRequestsKt`** (`hidden_comments/%s/hide_comment/%s/`), plus
  uncover / bulk-delete / restricted / filter-setting siblings.
- **`CommentListBottomsheetFragment`** (renamed `X.KQP`) is the main comments
  thread/list UI (instantiates the comment composer binder); its view-model is the
  renamed `X.BLM`.

The comment composer/post path builds `media/%s/comment/` (with `comment_text`,
`replied_to_comment_id`, `comment_creation_key`) and can crosspost to Threads via
`PostCommentUtil`. The core comment dictionary model is not named `Comment*` in
`api.schemas` (it is embedded in the feed-media schema); confirmed comment-adjacent
schema types are `CommentGiphyMediaInfo`, `CommentStickerData`,
`CommentStoryTraySignalMetadata`.
