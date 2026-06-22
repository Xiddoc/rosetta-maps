# Explore & Search

The discovery surfaces: the **Explore** grid and the **Search** (SERP) stack.
Most of the logic here is renamed into `X/` and recovered via
`__redex_internal_original_name` fields, kept inner-class FQCNs in DebugMetadata,
or unique REST/error strings; the Parcelable models and Room DBs keep their
names. These surfaces use REST (`discover/`, `fbsearch/`) more than GraphQL.
Logical→obfuscated names are in the map + `signatures.yaml`.

## Explore

- **`ExploreFragment`** (renamed `X.3IG`) is the Explore grid host — sets up the
  grid tiles (DYNAMIC_GRID / MEDIA_GRID / TWO_BY_TWO), autoplay, and the data
  store (trace `ExploreFragment.setupGrid`).
- **`ExploreTopicalFeedNetworkHelper`** (renamed `X.8Xv`) is the Explore feed
  data source — builds the `discover/topical_explore/` request and manages
  topic-cluster paging (`dest_topic_cluster_debug_info`,
  `is_nonpersonalized_explore`).
- **`ExploreFragmentConfig`** / **`ExploreTopicCluster`** (kept) are the
  Parcelable config + topic-cluster/section model. **`ExploreClipsRequest`**
  (renamed) builds `discover/explore_clips/` (clips-in-Explore). Explore ranking
  is server-driven (no client ranking class).

## Search

- **`SerpRepository`** (renamed; kept inner FQCN
  `com.instagram.search.surface.repository.SerpRepository`) is the search-results
  (SERP) data layer — `fetchFeedPage` fetches paged results (GraphQL
  `XDTTopSerpEntitiesUnit`). **`SerpChildViewModel`** drives a single results tab.
- **`CompositeSerpTabbedFragment`** (renamed) is the tabbed results container
  hosting the accounts/tags/places/audio tabs; **`BaseSerpGridFragment`** is the
  per-tab grid base (error `Expected parentFragment to be
  CompositeSerpTabbedFragment but was `).
- **`SingleSearchTypeaheadTabFragment`** (renamed) is the as-you-type typeahead
  tab (`fbsearch/ig_typeahead/`, `fbsearch/keyword_typeahead/`).
- **`SearchNullStateFetcher`** (renamed `X.9CC`) fetches the null-state
  (suggested entities / popular sections, `fbsearch/nullstate_dynamic_sections/`)
  and reads recent searches; the recent-searches store itself is a separate
  timestamped SharedPreferences class. **`SerpEntryPointConstants`** (kept) maps
  client entry-point strings to server enum constants; **`SuggestedUsersDatabase`**
  (kept Room DB) backs suggested-users.
