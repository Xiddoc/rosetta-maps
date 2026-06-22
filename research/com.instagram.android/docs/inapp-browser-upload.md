# In-App Browser (IAB) & Media Upload Pipeline

The in-app web browser (Meta's BrowserLite engine embedded in IG) and the
post/story/reel upload engine. (Complements master's `media-upload.md`, which
covers the `rupload`/`media/configure*` HTTP surface; this doc covers the
PendingMedia store/uploader classes and the IAB.) Most class names are kept
(both `com.instagram.*` and `com.facebook.browser.lite.*`); the central
PendingMedia model is renamed. Logical→obfuscated names are in the map +
`signatures.yaml`.

## In-app browser (IAB)

- **`BrowserLiteFragment`** (`com.facebook.browser.lite`) is the WebView host —
  creates the WebView (`BLF.createWebView_start`) and loads external URLs
  (`BLF.loadExternalUrl_start`). **`BrowserLiteWrapperView`** is the WebView
  container; **`BrowserLiteJSBridgeProxy`** the JS-bridge base.
- **`BrowserLiteInMainProcessIGActivity`** (`com.instagram.inappbrowser.fragments`)
  hosts the fragment in IG's process. **`BrowserLinkshimUrlCache`**
  (`com.instagram.inappbrowser.helper`) de-shims ad/affiliate links before
  navigating out (`linkshim/fetch_lynx_url/`) — the leave-app link interception
  point. **`IGWatchAndBrowseLiteChrome`** is the split-screen watch-and-browse
  chrome. **`IABLaunchEvent`** is one of ~40 `IAB*Event` navigation-telemetry
  models. Autofill/leadgen-in-IAB runs through `AutofillSharedJSBridgeProxy`.

## Media upload pipeline

- The central model is **PendingMedia** (renamed `X.6tx`, a 447-field state bag
  for one post/story/reel; anchored on `num_reupload` + `ClipInfo` field type).
- **`PendingMediaStore`** is the runtime registry (`pending_media_*`);
  **`PendingMediaStoreSerializer`** flushes it to disk so uploads survive process
  death.
- **`PendingMediaWorker`** / `UploadQueueManager` drive ordered steps →
  **`MediaUploader`** (`ig_media_ingest_start`) → **`FbUploaderUtil`**
  (`fbuploader error (%s)`, the FB byte transport) → finalize via
  `ConfigureMediaStep` (the `configure/` call) → parse with
  **`ConfigureResponseHelper`** (`ConfigureResponseHelper Config returns invalid
  media`). Retries run through `NetworkRetryWorker`. Hook `MediaUploader` /
  `PendingMediaStore` for full upload visibility.
