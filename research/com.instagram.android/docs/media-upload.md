# Instagram — media upload & publish pipeline

App: `com.instagram.android` v433.0.0.47.68 (`version_code` 383909338)

How a photo/video/reel/story gets from the device to a published post: a
**resumable upload** (`rupload`) of the bytes, then a **configure** call that
turns the uploaded blob into a post of the right type. The pipeline logic is
obfuscated into `X/` (unlike DM/realtime), so most of it is mapped. All anchors
below are globally unique (`rg -l` count == 1).

## Stage 1 — resumable upload (`rupload`)

- **`IgUploadMediaTypeEnum` (`X/DBs`)** — enum of upload media types mapped to
  their endpoints: `rupload_igphoto`, `rupload_igvideo`. The authoritative
  type→endpoint table. Anchor: `rupload_igphoto`.
- **`IgRuploadRequestBuilder` (`X/DBu`)** — builds the initial resumable-upload
  request: sets `X-Instagram-Rupload-Params`, picks the
  `desired_upload_handler`, and the per-type compression strategy. Anchor:
  `desired_upload_handler`.
- **`IgRuploadHttpExecutor` (`X/DCI`)** — executes the chunk POSTs to
  `/rupload_igphoto/` or `/rupload_igvideo/`, attaching per-chunk entity headers
  (`Offset`, `X-Entity-Length`, `X-Entity-Name`, `X-Entity-Type`) and rupload
  debug headers. Anchor: the log line `Failed to parse debug_segment_id from
  rupload params`. (The entity/rupload header *names* recur across builder
  classes, so the unique log string is the anchor.)

The in-flight upload state object is `PendingMedia` (obfuscated `X/6tx`, a
200+-field model holding `BarcelonaParams`/`ClipsParams`/`StoryParams`/
`IngestionData`); it is described here but not signatured (its anchors are
structural field patterns, not a unique string).

## Stage 2 — configure / publish

- **`IgMediaConfigureEndpointEnum` (`X/IwY`)** — enum of `media/configure*`
  endpoints per target: feed (`media/configure/`), carousel
  (`media/configure_sidecar/`), clips/reels (`media/configure_to_clips/`),
  upload-finish (`media/upload_finish/`). Anchor: `media/configure/`.
- **`IgStoryConfigureEndpoint` (`X/Hcb`)** — the story-specific subclass
  (`media/configure_to_story/`). Anchor: `media/configure_to_story/`.
- **`IgMediaConfigureBodyBuilder` (`X/KgI`)** — builds the configure request
  JSON body from the `PendingMedia` model: `upload_id`, media type, carousel /
  `client_sidecar_id`, share targets, app attribution, etc. Anchor:
  `client_sidecar_id`.

The orchestration steps (`MediaUploader`, `ConfigureMediaStep`,
`VideoIngestionStep`, `IngestionData`) keep their **real names** under
`com.instagram.pendingmedia.*` / `com.facebook.videolite.instagram.*` and are
documented here, not signatured.

## End-to-end flow

```
PendingMedia (X/6tx) describes the media
   → IgRuploadRequestBuilder (X/DBu)  builds the rupload request
   → IgRuploadHttpExecutor   (X/DCI)  POSTs chunks to rupload_ig{photo,video}
   → ConfigureMediaStep              (when bytes are up)
   → IgMediaConfigureBodyBuilder (X/KgI)  builds the configure JSON
   → POST to endpoint from IgMediaConfigureEndpointEnum (X/IwY) /
     IgStoryConfigureEndpoint (X/Hcb)
   → (video) VideoIngestionStep transcodes / segments
```

## Confidence

All six mapped classes are **high**: each pinned on a unique endpoint / handler
/ log string reached by live code, corroborated by the surrounding rupload and
`media/configure*` constants. `X/DCI`'s identity rests on a unique log line
because the rupload header names are shared across builders.
