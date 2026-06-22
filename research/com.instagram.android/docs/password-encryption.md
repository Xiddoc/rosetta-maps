# Instagram — client-side password encryption (`enc_password`)

App: `com.instagram.android` v433.0.0.47.68 (`version_code` 383909338)

Instagram never sends a plaintext password to `accounts/login/`. The password
field is `enc_password`, a tagged, versioned, hybrid-encrypted blob produced
entirely on-device before the request leaves. This doc documents that scheme.

## The wire format

`enc_password` is a colon-joined string built with `String.format("%s:%s:%s:%s", …)`:

```
<tag>:<version>:<key_id>:<base64(ciphertext)>
```

- **`tag`** — application/flow marker. Selected by `LX/fmF;->A00(Integer)`
  (`smali_classes18/X/fmF.smali`): `#PWD_INSTAGRAM`, `#PWD_FB4A`,
  `#PWD_MSGR`, `#PWD_WORKPLACE`, `#PWD_TALK`, `#PWD_ENC`. For a normal IG
  login this is `#PWD_INSTAGRAM`. A transient/bootstrap path uses
  `#PWD_TRANSIENT`.
- **`version`** — encryption scheme version (an `int`, e.g. `4`), tracked on the
  key material (`LX/97E;->A01`). `LX/ijJ;->A03` is initialised to `4`.
- **`key_id`** — integer id of the public key used. For the **bootstrap key**
  this is `0x29` (41).
- **`base64(ciphertext)`** — `Base64.encodeToString(…, NO_WRAP)` of the bytes
  returned by the native crypto.

## The encrypter — `X/ioi` (logical: `IgPasswordEncrypter`)

`smali_classes18/X/ioi.smali`, method `A00(String password) -> String`
(`enc_password`). Flow (`smali_classes18/X/ioi.smali:91-385`):

1. Reject empty input (`"Empty password passed in"`, line 193).
2. Compute a server-corrected timestamp: `Calendar.getTimeInMillis()` passed
   through `LX/135;->A0C(J)` (server time-offset correction), formatted `"%d"`
   — this becomes a bound parameter of the ciphertext (replay binding).
3. Fetch the current public key from `LX/96x;->A01()` → `LX/97E;`
   (`A02` = PEM/string key, `A00` = key_id, `A01` = type). The single live
   `LX/96x` instance (`A00()`) holds the key the server most recently pushed.
4. Encrypt via **Facebook CryptoPub native**:
   `com.facebook.cryptopub.CryptoPubNative.encrypt(int keyId, String publicKey,
   String password, String time) -> byte[]` (line 167). This is a hybrid
   public-key scheme (ephemeral symmetric key sealed to the server public key),
   not raw RSA. Result is base64'd (line 173).
5. Assemble `tag:version:key_id:cipher` (lines 219/237/358) and return it.
6. Emit analytics `instagram_client_password_encryption_encrypt_attempt` with
   `version`, `key`, `key_id`, `tag` fields (lines 250-301).

`LX/ijJ` (logical: `IgPasswordEncrypterImpl`) is the low-level holder: static
field `A04` of type `com.facebook.cryptopub.CryptoPubNative`, scheme version
`A03 = 4`, plus the fallback path `A00(String,String,LX/ijJ;)`.

## The bootstrap public key (offline fallback)

When no server key is available (`LX/96x;->A01()` returns null), `X/ioi` falls
back to a **hard-coded RSA-2048 public key with `key_id` 41**
(`smali_classes18/X/ioi.smali:308`):

```
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAvcu1KMDR1vzuBr9iYKW8
KWmhT8CVUBRkchiO8861H7zIOYRwkQrkeHA+0mkBo3Ly1PiLXDkbKQZyeqZbspke
4e7WgFNwT23jHfRMV/cNPxjPEy4kxNEbzLET6GlWepGdXFhzHfnS1PinGQzj0ZOU
ZM3pQjgGRL9fAf8brt1ewhQ5XtpvKFdPyQq5BkeFEDKoInDsC/yKDWRAx2twgPFr
CYUzAB8/yXuL30ErTHT79bt3yTnv1fRtE19tROIlBuqruwSBk9gGq/LuvSECgsl5
z4VcpHXhgZt6MhrAj6y9vAAxO2RVrt0Mq4OY4HgyYz9Wlr1vAxXXGAAYIvrhAYLP
7QIDAQAB
-----END PUBLIC KEY-----
```

This literal is an extremely stable, globally-unique anchor for the encrypter
class — it changes only when IG rotates the bundled bootstrap key (rare).

## Key distribution / refresh

The live key in `LX/96x`/`LX/97E` is updated from server responses (the
standard IG `password-encryption-pub-key` / `password-encryption-key-id`
response headers). `LX/97E;->A01` carries a type enum (`LX/008;->A00`/`A01`)
distinguishing a server-pushed key from the transient bootstrap key, which is
what selects `#PWD_TRANSIENT` vs `#PWD_INSTAGRAM`.

## Hook points (for the Frida/Xposed adapters)

- **`LX/ioi;->A00(String)String`** — intercept to read the plaintext password
  *before* encryption, or to read the final `enc_password`.
- **`com.facebook.cryptopub.CryptoPubNative.encrypt(...)`** — native boundary;
  plaintext is arg 3.
- **`LX/21G;->A0h(LX/2s4;String)String`** — the call site bridge from the login
  API into the encrypter.

## Confidence

**High.** Identity is confirmed structurally: `X/ioi` is the only class holding
the `instagram_client_password_encryption_encrypt_attempt` analytics literal AND
the `#PWD_TRANSIENT` + bootstrap-key literals, and its body shows the full
format/encrypt/log sequence. `com.facebook.cryptopub.CryptoPubNative` is an
un-obfuscated FB class name (kept by JNI).
