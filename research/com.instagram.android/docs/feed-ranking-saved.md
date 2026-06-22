# Main Feed (cache/ranking) & Saved / Collections

The home-timeline cache/network layer and the Saved/Collections subsystem.
(Complements master's `feed-stories-reels.md`, which covers the feed *HTTP
endpoint registry*; this doc covers the *cache/store* classes and Saved.)
Class names under `com.instagram.mainfeed.*` / `com.instagram.feed.media.*` /
`com.instagram.save.*` are kept; the request builders are renamed `X/`.
Logical→obfuscated names are in the map + `signatures.yaml`.

## Main feed cache & model

- **`MainFeedCacheDataSource`** (`com.instagram.mainfeed.network`) orchestrates
  cold-start-vs-network feed loading (`MainFeedCacheDataSource.coldStartCacheLoad`,
  `feed_schedule_initial_cache_load`, `feed_cache_bg_prefetch`). Prime hook for
  feed-content interception.
- **`ColdStartFeedCache`** loads the persisted feed blob from disk on launch
  (`ColdStartFeedCache.loadFromFile`); **`FeedMediaCache`** post-processes/ages
  cached media (`FeedMediaCache.getAndProcess`, `top_pos_guardrail`). Backing
  store is a Room `OneCacheDatabase`.
- **`Media`** (`com.instagram.feed.media`) is the per-post feed model;
  **`MediaCache`** the id-keyed registry. **`SuggestedChannels`** is a netego
  (ad/suggestion) feed-item. The home-feed request (`feed/timeline/`, with
  `is_pull_to_refresh`) and the "You're all caught up" end-of-feed demarcator are
  driven by renamed `X/` classes (no kept name).

## Saved / Collections

- **`SavedCollection`** (`com.instagram.save.model`) is the collection model
  (cover image, representative media, collab metadata, owner, type enums).
- **`CollectionsApiClient`** (renamed `X.MZB`) is the collection CRUD client:
  `collections/create/`, `collections/%s/edit/`, `collections/%s/delete/`,
  `collections/bulk_remove/`, `collections/list/`.
- **`SavedFeedRequestBuilder`** (renamed `X.BSt`) builds the saved-feed
  (`feed/saved/`, `feed/saved/posts/`, `feed/saved/clips/`, `feed/saved/audio/`,
  `feed/saved/all/`) and packages a `SavedCollection` into
  **`SavedContextualFeedNetworkConfig`** (the collection-contents feed config).
  **`SavedMediaGridCollectionsViewModel`** backs the saved-grid screen. The
  per-post save toggle is a GraphQL mutation in this build (no `media/%s/save/`
  REST path); cross-app saves use `xfb_cross_app_saved_collections`.
