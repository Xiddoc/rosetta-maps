# IG Live & Live Monetization

Live video broadcasting + the creator-monetization surfaces around it (Stars,
Badges, gift feed). The IG-Live code lives under `com.instagram.video.live.mvvm`
(an MVVM tree); the broadcaster controller and capture/viewer fragments are
renamed into `X/`. There is **no dedicated IG-Live foreground service** —
broadcasting rides the shared RTC/RSYS media stack (`OngoingCallServiceWithMic`,
see `rtc-calls.md`); `BroadcastType` enumerates `LIVESWAP_RTMP` /
`LIVESWAP_TRANSITION_{IG,RSYS}_INFRA`. Logical→obfuscated names are in the map +
`signatures.yaml`.

## Broadcasting

- **`IgLiveStreamingController`** (renamed `X.Q3l`) is the broadcaster controller:
  it POSTs `live/create/`, manages interrupt/resume and video toggle, and tears
  down on failure (`endBroadcastWithFailure(`). Prime hook for the broadcast
  session.
- **`IgLiveCaptureFragment`** (renamed `X.L7p`) is the go-live broadcaster capture
  surface; **`IgLiveExploreLiveViewerFragment`** (renamed `X.PbJ`) is the viewer
  consumption surface (`ARG_VIEWER_SESSION_ID`, `post_live`).
- **`IgLiveCommentsRepository`** (`…mvvm.model.repository`) sends/fetches live
  comments (`live/%s/comment/`, `live/%s/get_comment/`) and subscribes to the
  realtime comment/like streams.
- **`IgLiveCobroadcastRepository`** drives live-with / guest co-broadcast
  (`live/%s/broadcast_event/`); **`IgLiveLikesApi`** is the heart/react path
  (`live/%s/react/`). Viewer count comes from a heartbeat API
  (`live/%s/heartbeat_and_get_viewer_count/`).

## Monetization (Stars, Badges, gifts)

- **`AppreciationGiftingDataSource`** (`com.instagram.appreciation.gifting.repository`)
  is the **Stars** send/balance path (`xig_live_stars_send`).
- **`AppreciationGiftFeedDataSource`** (`…giftfeed.repository`) is the gifter feed
  (`creators/content_appreciation/async_get_paginated_gift_feed_transactions/`).
- **`UserBadgeInfoImpl`** (`com.instagram.badge.api.model`) is the badge-count data
  model (`XDTAccountBadgeCount`; fields `total_count`, `badge_count_map`).
- **`IgLiveBroadcastSettingsApi`** toggles live badges (`live/%s/badge_setting/`).
  The monetary badge-purchase pipeline itself is funnelled through the Stars flow;
  the per-badge purchase classes are obfuscated `X/` keyed on `ig_live_badges_ufi`.
