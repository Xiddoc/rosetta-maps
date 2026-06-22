# Instagram — on-device secure storage & keystore crypto

App: `com.instagram.android` v433.0.0.47.68 (`version_code` 383909338)

Instagram protects sensitive on-device data (notably the cross-app E2E
auth-token cache keyed `xapp.e2e.tokens`, see `alt-login-paths.md`) with an
Android-Keystore-backed crypto stack. This doc maps that stack. All classes
below were pinned on globally-unique string literals (`rg -l` count == 1).

## The stack

| logical name | obfuscated | role |
|--------------|-----------|------|
| `IgAndroidKeyStoreManager` (`X/4bn`) | `X/4bn` | Creates/loads the `AndroidKeyStore`, generates keys, and produces **hardware-attested** keys (it checks "is hardware backed" and can generate an attested key) |
| `IgKeystoreJweCipher` (`X/2h3`) | `X/2h3` | JWE (JSON Web Encryption) encrypt/decrypt: wraps a content key with `RSA/ECB/OAEPPadding` from a Keystore `PrivateKeyEntry`, then `AES/GCM/NoPadding` for the payload; parses/validates the JWE structure |
| `IgSymmetricKeystoreTransformer` (`X/2sq`) | `X/2sq` | Symmetric (AES) encrypt/decrypt helper over a Keystore secret key (`extends X/2v6`); the "SymmetricTransformer" tag is its log/identity marker |
| `IgKeystoreKeyLoader` (`X/7VH`) | `X/7VH` | Loads a specific Keystore key by id for encrypt/decrypt; raises "Keystore cannot load the key with ID: …" on miss; uses `NoPadding` AES-GCM with an AAD correctness self-check |

## How it fits together

1. **Key material** lives in the `AndroidKeyStore` (hardware-backed where the
   device supports it). `X/4bn` is the gatekeeper: it creates the store, and
   for high-value keys generates a **key-attested** keypair so the server can
   verify the key is hardware-bound.
2. **Asymmetric wrapping** (`X/2h3`) uses RSA-OAEP from a Keystore
   `PrivateKeyEntry` to wrap a per-message AES-GCM content key — the standard
   JWE `RSA-OAEP` + `A256GCM` shape. This is what protects blobs that must
   survive process restarts / be readable only on this device.
3. **Symmetric paths** (`X/2sq`, `X/7VH`) handle the common case of
   encrypting/decrypting with a named Keystore AES key directly (no per-message
   asymmetric wrap), e.g. for the E2E token cache.

## Hook points (adapters)

- `IgKeystoreJweCipher` (`X/2h3`) — intercept JWE encrypt/decrypt to read
  plaintext blobs (e.g. cached tokens) without touching the Keystore.
- `IgSymmetricKeystoreTransformer` (`X/2sq`) / `IgKeystoreKeyLoader` (`X/7VH`) —
  the symmetric encrypt/decrypt boundary for keystore-named secrets.
- `IgAndroidKeyStoreManager` (`X/4bn`) — observe key generation / attestation.

## Confidence

**High** for all four — each is pinned on a unique, descriptive error/identity
string reached by live crypto code, and the surrounding `const-string`s
(`RSA/ECB/OAEPPadding`, `AES/GCM/NoPadding`, `AndroidKeyStore`,
`PrivateKeyEntry`) confirm the role structurally rather than by guess.
