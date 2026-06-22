# Avatars & AR Effects

Meta **Avatars** (3D avatar creation, stickers, avatar-as-profile-pic) and the
camera **AR effects** platform (Spark/voltron engine, effect gallery, Nametag
scanner). Class names under `com.instagram.avatars.*` / `com.instagram.ar.*` are
kept; GraphQL op names are the gold anchors. Logical→obfuscated names are in the
map + `signatures.yaml`. (Native libs: `libarcore_sdk_*.so` are Google ARCore;
the IG/Spark effect engine is `com.facebook.cameracore.mediapipeline.arengineservices.*`.)

## Avatars

- **`AvatarStatusRepository`** (`com.instagram.avatars.status`) answers
  "does this user have an avatar" (`HasAvatarQuery`); its result is cached by
  `AvatarStore` (`com.instagram.avatars.store`).
- **`UserAvatarInfoGraphQLRepository`** (`…avatars.graphql`) fetches avatar
  info/image URLs (`IGAvatarInfoQuery`); **`AvatarStickerGraphQLRepository`**
  resolves avatar stickers for DMs/stories/comments
  (`IGAvatarStickersForKeysQuery`); **`AvatarMutationRepository`** deletes the
  avatar (`IGAvatarDeleteMutation`).
- **`AvatarPrivacySettingsRepository`** (`…avatars.privacysettings`) reads/writes
  the avatar usability/privacy setting
  (`xig_update_usability_avatar_privacy_setting`).
- **`AvatarProfileRepository`** (`com.instagram.profile.data`) drives
  avatar-as-profile-pic / CoinFlip (`xig_ig_avatar_profile_pic`,
  `creatives/save_avatar_profile_settings/`).
- **`AvatarQuestsRepository`** (`…avatars.unlockables.data`) backs avatar
  quests/unlockables (`IGAvatarUnlockableStickerQuestMutation`). The editor entry
  is the `AvatarEditorUrlHandlerActivity` deep link, which gates on `AvatarStore`.

## AR Effects

- **`EffectCollectionService`** (`com.instagram.ar.core.effectcollection`) is the
  effect download/fetch service (`IGAREffectsByIdQuery`; verifies effect ZIP
  assets via `crypto_hash`/`revision_id`), persisting into a Room cache
  (`MiniGalleryDatabase_Impl` holds the `mini_gallery_categories` table; the
  effect-collection DB holds `effect_collections_effects`).
- **`IgArVoltronModuleLoader`** (`com.instagram.ar.core.voltron`) is the Spark/AR
  **voltron dynamic-module loader** — lazily loads/prefetches native AR engine
  modules (including PyTorch ML modules), one loader per session. The native
  bridge to the engine is `IgEffectServiceHost`.
- **`NametagController`** (`com.instagram.arlink.fragment`) drives the Nametag /
  ArLink scan UI (deep-link template `https://www.instagram.com/%s/?r=nametag`),
  with a JNI YUV bridge converting camera frames for the native nametag detector.
- **`ArirangScavengerHuntPreferencesUtil`** (`com.instagram.arirang.scavengerhunt`)
  tracks the AR scavenger-hunt easter-egg count
  (`arirang_easter_egg_completed_count`). Effect save/unsave and gallery/preview
  GraphQL ops live in renamed `X/` classes.
