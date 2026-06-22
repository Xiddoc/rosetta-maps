# Notes & Broadcast Channels

Two DM-adjacent features: **Notes** (short text/music notes on the inbox) and
**Broadcast Channels** (creator one-to-many DM). Both live under
`com.instagram.direct.*` (Notes is NOT `com.instagram.notes`). Logical→obfuscated
names and anchors are in the map + `signatures.yaml`.

## Notes

Backend term for notes is **"ambient data"**.

- **`NotesRepository`** (`com.instagram.direct.inbox.notes.data.repository`)
  creates/updates a note (`xdt_create_or_update_ambient_data`; error
  `Failed to create or update ambient note`), with optimistic posting. Hook
  `postNote` to intercept note creation.
- **`NotesTrayApiFetcher`** (same package) fetches the inbox-top notes tray
  (`xdt_get_inbox_tray_items`, param `should_fetch_school_note_dict`), cached in a
  Room `tray_items` table.
- **`NotesCtaRepository`** (`…notes.data.cta`) backs note call-to-action surfaces
  (`xdt_fetch_user_ctas_notes`).
- The note **audience** selector is the `NoteAudience` enum
  (`MUTUAL_FOLLOWERS`, `CLOSE_FRIENDS`, `SCHOOL`, `PUBLIC`, …); note-content
  variants (music, poll, GIF, location, hyperlink) are a family of
  `*NoteResponseInfo` schemas. Replies go through `NoteReplyComposerBarController`.

## Broadcast Channels

- **`XFBIGDChannelCreatorBroadcastThreadData`** (`com.instagram.direct.model.protobufmodel`)
  is the broadcast-channel thread data model — kept protobuf field names
  `creatorUsername_`, `joinLink_`, `numberOfMembers_`, `audienceType_`,
  `isCreatorVerified_`. It attaches to a generic DM thread via
  `ThreadMetadata.creatorBroadcastThreadData_` (field #3). Best hook for reading
  channel state per thread.
- **`ChannelJoinRepository`** (`com.instagram.direct.fragment.channels.directoryv2.model`)
  adds a discovered channel to the inbox (`ChannelCategoryAddToInbox`);
  **`ChannelDirectoryDataSource`** powers channel discovery
  (`xfb_igd_global_directory`).
- **`ChannelsEducationRepository`** (`com.instagram.direct.channels.education.repository`)
  handles creator education + the channel-thread fetch
  (`xfb_igd_channels_update_creator_education_goal_metric`,
  `xfb_igd_broadcast_channel_thread`).
- Channel-only realtime event types (collaborator/invite/participant/input-mode
  updates) are delivered via `RealtimeProtocol` topic constants (see
  `realtime-mqtt.md`).
