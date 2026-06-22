# Teen Safety & Digital Wellbeing

Instagram's safety + wellbeing surface: **Supervision / parental controls**,
**Family Center**, and **Screen Time / "Take a Break"**. This is defensive,
educational mapping of publicly observable, server-contract strings in a shipping
app — the dedicated `com.instagram.supervision` / `com.instagram.familybridges`
packages are thin stubs; the real surface lives under `com.instagram.wellbeing.*`,
`com.instagram.screentime.*`, and url-handlers. Logical→obfuscated names and
anchors are in the map + `signatures.yaml`.

## Supervision / parental controls

- **`SupervisionInfoGraphQLRepository`** (`com.instagram.wellbeing.familycenter.api`)
  loads a teen/parent's supervision-relationship state (`FetchSupervisionInfoWWW`,
  over `xdt_users__info`), merged into the `User` dict.
- **`GuardianPairingUrlHandlerActivity`** (`com.instagram.urlhandlers.guardianpairing`)
  is the parent↔teen linking entry, gated by `GetIsSupervisionEnabledQuery`.
- **`DailyLimitReminder`** (`com.instagram.wellbeing.timetools.reminder.dailylimit`)
  enforces the daily time limit; the **supervised** (parent-imposed) blocking
  variant is the condition `fail_supervised_blocking_daily_limit`.
- **`IGSleepModeReminder`** (`…reminder.sleepmode.sleepmodereminder`) enforces
  quiet-hours / sleep mode (condition `fail_no_sleep_mode_intervals`).
- The supervision relationship itself is the GraphQL `XDTSupervisionInfo` tree
  (`guardian_user`, `restricted_account`); teen-side mutations include
  `xfb_unsupervised_teen_cancel_setup_supervision_request`.

## Family Center

- **`FamilyCenterUrlHandlerActivity`** (`com.instagram.urlhandlers.familycenter`)
  is the Family Center dashboard entry (routes `supervision` / `dashboard` /
  `share_supervision`).
- **`IGFamilyAppLastUsedStatesLogWorker`** (`com.instagram.partneranalytics.igfamilyapplastusedstates`)
  is the cross-app (Meta Family) linkage telemetry worker (WorkManager tag
  `ig_family_app_last_used_states_logging_background_work`). The family
  relationship is server-resolved per supervision relationship — there is no rich
  local family-graph object.

## Screen Time / "Take a Break"

- **`InstagramTimeSpentManagerImpl`** (`com.instagram.wellbeing.timespent.listeners`)
  is the time-spent tracker / "Take a Break" orchestrator: it pulls settings from
  `mental_well_being/get_time_tools_settings/`, schedules `daily_limit_near_reminder`
  nudges, and launches the fully-blocking screen.
- **`TimeSpentReminderFullyBlockingFragment`** (`…timespent.fragment`) is the
  full-screen "Take a Break" / daily-limit-reached interstitial (entry tag
  `timespent_dashbaord_entrypoint` [sic]).
- **`IGScreenTimeApi`** (`com.instagram.screentime`) builds and uploads the
  time-in-app interval payload (`tia_clock_timestamp`, `tia_payload`), backed by a
  Room `screentime_sync` table.
- **`IGPresenterService`** (`com.instagram.wellbeing.timetools.presenter`) is the
  shared presenter that renders all time-tools reminder dialogs/notifications.
