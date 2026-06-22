# Instagram — feed, stories tray & reels HTTP surface

App: `com.instagram.android` v433.0.0.47.68 (`version_code` 383909338)

How the app fetches the main feed, the stories (reels) tray, and reels/clips,
and how it reports that stories were watched. The *content* packages
(`com.instagram.feed`, `com.instagram.reels`, `com.instagram.clips`) keep their
names; the obfuscated **request-building** classes with unique anchors are
mapped.

## Endpoint registry

- **`IgFeedEndpointRegistry` (`X/0ZN`)** — holds the static lists of feed/clips
  endpoint paths: `feed/timeline/`, `feed/timeline_stream/`,
  `feed/reels_tray/`, `feed/reels_media/`, `feed/reels_media_stream/`,
  `discover/topical_explore/`, plus the clips list `clips/discover/`,
  `clips/homecoming/`. The individual endpoint strings each recur across many
  builder classes (so they aren't unique anchors), but
  `feed/timeline_stream/` is unique to this registry. Anchored on it.

This matters because the timeline/reels endpoint *strings* are not per-class
unique — they're centralised here and routed into the shared request builder
(`X/2k4`) by strategy objects. So the registry is the reliable map anchor for
"which feed endpoints exist".

## Stories tray

- **`IgReelApiFactory` (`X/4a9`)** — the factory that builds the stories-tray
  streaming request to `feed/reels_tray/` (with a `_v1` variant), wiring up
  view-state tracking and a "reason" code for why the tray is being fetched.
  Anchored on the unique log substring `createReelsTrayStreamingRequestTask`
  (the `feed/reels_tray/` string itself is shared across classes).

- **`IgStorySeenStateReporter` (`X/0tF`)** — batches which stories/reels the
  user watched and POSTs them to `media/seen/` (URL
  `media/seen/?reel=%s&live_vod=0`), with a JSON body carrying `reels`,
  `reel_media_skipped`, `nuxes`, `nuxes_skipped`, `force_seen_story_ids`. This
  is the "mark stories as seen" call. Anchored on the unique substring
  `media/seen/?reel=` (regex-escaped in the signature).

## Reels / clips & main feed

The reels/clips feed requests (`clips/homecoming/`, `clips/discover/`) and the
main timeline (`feed/timeline/`) are built by per-surface factory classes that
call into the shared request builder, but they're anchored only on endpoint
strings that recur across multiple classes — so they are documented here and
captured via the endpoint **registry** (`X/0ZN`) rather than as their own
fragile single-string signatures.

## Confidence

`X/0ZN`, `X/4a9`, `X/0tF`: **high** — each pinned on a string verified globally
unique (`feed/timeline_stream/`, the `createReelsTrayStreamingRequestTask` log,
the `media/seen/?reel=` URL), with corroborating endpoint/JSON constants in the
same class. The shared-endpoint builder/feed classes are intentionally left to
prose to avoid one-version-fragile anchors.
