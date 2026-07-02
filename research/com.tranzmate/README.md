# com.tranzmate (Moovit) — research notes

Human-readable *what-the-code-does* notes behind the machine artifacts for **Moovit** (`com.tranzmate`):

- **Authoritative name mapping** → [`maps/com.tranzmate/1785.json`](../../maps/com.tranzmate/)
- **Source-of-truth signatures** → [`signatures/com.tranzmate/signatures.yaml`](../../signatures/com.tranzmate/signatures.yaml)
- **These notes** → behaviour, flows, file formats, hook points.

Confirmed against **version_code 1785** (versionName 5.194.0.1785). Moovit is R8 *partially* obfuscated: package paths and many class names are kept, but internal classes rotate to short tokens and method/field names are renamed even inside kept classes — which is what the map recovers. Anchors are rotation-stable string literals, each verified globally-unique to one class.

## Index

| Doc | Subsystem | Classes |
| --- | --- | --- |
| [`docs/user-account.md`](docs/user-account.md) | User account & profile | 10 |
| [`docs/trip-planner.md`](docs/trip-planner.md) | Trip planning | 15 |
| [`docs/itinerary.md`](docs/itinerary.md) | Itinerary model & legs | 13 |
| [`docs/premium-subscription.md`](docs/premium-subscription.md) | Premium / Moovit+ / subscriptions | 12 |
| [`docs/payments-wallet.md`](docs/payments-wallet.md) | Payments & wallet | 10 |
| [`docs/ticketing-core.md`](docs/ticketing-core.md) | Ticketing core (storage & purchase) | 12 |
| [`docs/mot-ticketing.md`](docs/mot-ticketing.md) | MOT mobile ticketing | 20 |
| [`docs/fairtiq-ticketing.md`](docs/fairtiq-ticketing.md) | Fairtiq check-in/out ticketing | 11 |
| [`docs/tod-ridehailing.md`](docs/tod-ridehailing.md) | Transit-on-demand / ride hailing | 15 |
| [`docs/micromobility.md`](docs/micromobility.md) | Micromobility (bike/scooter) | 11 |
| [`docs/network-protocol.md`](docs/network-protocol.md) | Network & server protocol | 7 |
| [`docs/home-dashboard.md`](docs/home-dashboard.md) | Home & dashboard suggestions | 17 |
| [`docs/navigation-livetrip.md`](docs/navigation-livetrip.md) | Live navigation & trip tracking | 13 |
| [`docs/transit-realtime.md`](docs/transit-realtime.md) | Transit entities & real-time arrivals | 16 |
| [`docs/push-notifications.md`](docs/push-notifications.md) | Push, GCM & Braze | 11 |

**193 class findings across 15 subsystems.**

## Provenance

Produced by the `apk-research` skill: apktool + jadx decompile, a parallel 15-agent research workflow (one agent per subsystem), sigmatcher-verified signatures (every class anchor resolves to exactly one class), adversarially reviewed. Obfuscated names rotate between releases; the behaviour and the string anchors are the stable part.
