# Mobile deployment contract

Personal AI OS is an installable PWA, but a separate phone must open it from one trusted
HTTPS origin. A plain LAN address such as `http://192.168.x.x:3000` is useful for limited
page testing only: browsers do not treat it as a secure context, so microphone access and
GPT Live are not a supported path.

## Required topology

Expose one HTTPS hostname to the phone and keep both application processes private behind
it:

```text
phone browser / installed PWA
        |
        | HTTPS
        v
trusted reverse proxy
        |-- /api/*  -> FastAPI :8000
        `-- /*      -> Next.js :3000
```

- Use a certificate trusted by the phone and matching the public hostname.
- Keep the API and web ports on loopback or a private container/network interface.
- Preserve the same public origin for pages and `/api/*`; provider credentials stay only
  in the API process environment.
- Preserve streaming responses for `/api/chat/stream`; disable proxy response buffering
  on that route if the proxy enables it by default.
- Persist `PERSONAL_AI_OS_DATA_DIR` on durable storage and back it up before moving hosts.
- Never place provider keys in `NEXT_PUBLIC_*`, client bundles, the manifest, or the service
  worker.
- Any Internet deployment must either enable the built-in access gate or sit behind an
  owner-only identity proxy. Set `PERSONAL_AI_OS_REQUIRE_AUTH=true`, an access password, and a
  password of at least 10 characters, and a random session secret of at least 32 characters in
  the host's secret store.

The current Next.js server can also proxy `/api/*` through `NEXT_PUBLIC_API_URL`. When a
front proxy routes `/api/*` directly to FastAPI, that build-time rewrite is bypassed.

### UI-only phone preview

An access-controlled design preview may be built with
`NEXT_PUBLIC_PERSONAL_AI_OS_MOBILE_PREVIEW=true`. The preview is visibly labelled,
does not pretend that API calls succeeded, and must not be used as the functional
deployment. Normal builds remain fail-closed when the API cannot be reached.

The owner-only Sites preview uses the `vinext` hosted build with Cloudflare's Vite
plugin because Sites requires a real Worker entrypoint at `dist/server/index.js`.
The regular `build:static` and Docker paths remain separate and do not enable
preview mode.

## Acceptance

After deployment, run the repository verifier from a trusted workstation:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check-mobile-readiness.ps1 -BaseUrl "https://ai.example.com"
```

For an access-protected deployment, set `PERSONAL_AI_OS_VERIFIER_ACCESS_PASSWORD` only in the
verifier process before running the command; the verifier uses it to obtain a temporary HTTP-only
session and never prints it.

Once a Realtime credential is configured, use the stricter gate:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check-mobile-readiness.ps1 -BaseUrl "https://ai.example.com" -RequireRealtimeConfigured
```

For a local production build only, HTTP localhost can be accepted explicitly:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check-mobile-readiness.ps1 -BaseUrl "http://127.0.0.1:3001" -AllowInsecureLocalhost
```

The verifier checks the Home and Live routes, standalone manifest, required app icons,
service-worker API exclusion, and the safe Realtime status contract. It does not claim
that microphone permission, audio playback, provider billing, or Home Screen installation
works on a physical device; those remain device-level acceptance steps.

## Physical-device checklist

1. Open the HTTPS address in Safari or Chrome on the phone.
2. Confirm Settings -> Mobile app reports `Secure HTTPS`, `Media capture Browser ready`,
   and `GPT Live Ready`.
3. Install from the in-app More menu or Safari's Add to Home Screen action.
4. Reopen from the Home Screen and confirm Settings reports `Installed`.
5. Start GPT Live, approve microphone access, hear one assistant response, interrupt it
   once, and end the call.
6. Reopen the conversation and confirm both completed transcript turns and its short title
   were persisted.
