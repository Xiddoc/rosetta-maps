# Sticker Search / GIPHY & Music / Audio

The GIF/sticker search stack (incl. the GIPHY client) and the broader music/audio
subsystem (search, download, lyrics, waveforms, original audio). Class names for
models/UI are kept; the REST request builders and the GIPHY client are renamed
`X/`. Logical→obfuscated names are in the map + `signatures.yaml`.

## Sticker search / GIPHY

- **`GiphyApiClient`** (renamed `X.PCW`) is the GIPHY public-API client — it
  hard-codes the GIPHY host (`api.giphy.com`), api_key, and `rating=PG`, hitting
  `/v1/{gifs,stickers}/{trending,search}`. Cleanest hook to observe GIF search.
  **`GiphyAttributionFragment`** is the "Powered by GIPHY" attribution UI;
  **`IgWebPAnimDecoder`** (`com.instagram.giphy.webp`) decodes animated GIF/WebP
  stickers (native).
- Avatar stickers use IG's own backend: **`AvatarStickerGraphQLApi`**
  (`bloks_tappable_animated_avatar_sticker_id_`) and
  **`AvatarStickerSearchRepository`** (`creatives/search_avatar_sticker_pack/`).
  Saved/recently-used GIFs go through Facebook EIMU GraphQL ops
  (**`SavedRecentGifsApi`**, `xfb_recently_used_gifs_for_eimu`).

## Music / audio

- **`MusicBrowseSearchApi`** (renamed `X.Ady`) is the music search/browse REST
  surface (`music/search/`, `music/clips_audio_browser/`,
  `music/stories_audio_browser/`). **`MusicResultsListController`** +
  **`MusicSearchFilterRepository`** (GraphQL `IGAudioSearchFiltersQuery`) drive
  the picker UI/filters.
- **`MusicAssetModel`** (`com.instagram.music.common.model`) is the canonical
  track model (display artist, cover artwork, duration, audio_cluster_id; its
  null-validation logs self-identify it). **`TrackSnippet`** is the start+duration
  selection model.
- **`TrackDownloader`** downloads audio to `audio-{id}-audio.mp4`;
  **`MusicAmplitudesApiUtil`** fetches waveform amplitudes
  (`music/track/%s/oa_amplitudes/`); lyrics come from a sibling
  `music/track/%s/lyrics/` API. **`OriginalSoundAudioAssetsApi`** (renamed `X.MI4`)
  handles original-audio creation (`music/original_sound_audio_assets/`). The
  audio playback engine is an obfuscated `X/` class (not resolved to a name);
  `MusicPreviewButton` holds the player handle. Music licensing/region gating runs
  through obfuscated `X/` classes consuming `MusicConsumptionModelImpl`
  (`XDTMusicConsumptionInfoDict`).
