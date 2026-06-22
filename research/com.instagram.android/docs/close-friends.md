# Close Friends

The **Close Friends** ("green ring") audience — a curated list you can share
Stories and posts with. Server-side it is modelled as **"private_stories" friend
lists** (the REST endpoint paths are the strongest anchors). The core API is a
kept class; the picker/home UI is renamed into `X/`. Logical→obfuscated names and
anchors are in the map + `signatures.yaml`.

## List management API

- **`AudienceListsApiUtil`** (`com.instagram.closefriends.audiencelists.api`,
  kept name) is the multi-list close-friends REST surface:
  `api/v1/stories/private_stories/bulk_update_members/` (add/remove members,
  with `added_user_ids`/`removed_user_ids`), `.../friend_lists/create/`,
  `.../friend_lists/edit/`, `.../friend_lists/delete/`, and `.../%s/members/`.
  **Best add/remove hook point.**
- **`SetBestiesApi`** (renamed `X.Qe9`, `@Deprecated`) is the legacy single-user
  toggle (`friendships/set_besties/` with `add`/`remove` arrays) — the classic
  profile "Add to Close Friends".
- **`CloseFriendsLeaveListController`** (renamed `X.2gT`) holds the only GraphQL
  close-friends mutation, `LeaveCloseFriendsListMutation` /
  `xig_ig_leave_close_friends_list` (there is no symmetric *add* mutation — adds
  go through REST).

## Audience UI & gate

- **`AudienceListsAudiencePickerFragment`** (renamed `X.JJJ`) is the list editor
  screen; saving fires `request_key_audience_lists_settings_session_finished`.
- **`FeedFavoritesHomeFragment`** (renamed `X.TDe`) is the close-friends
  ("Favorites") feed/management home (events `instagram_feed_favorites_exit` /
  `_impression`).
- **`CloseFriendsBadgePrefs`** (renamed `X.QkX`) gates the green-ring/badge
  impression + animation via the pref key `close_friends_badge_last_timestamp`.
- The story audience gate itself is `CloseFriendsUserStoryTarget`
  (`com.instagram.pendingmedia.model`), whose default target is
  `CLOSE_FRIENDS_WITH_BLACKLIST` and which carries the allow/block member list —
  the object attached to a pending story to mark it close-friends-only.
