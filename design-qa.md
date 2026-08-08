# Design QA

## Comparison target

- Home source visual truth: `C:\Users\RighthereWaiting\.codex\generated_images\019fe1a2-7b5a-7293-8cae-436d304b629b\exec-90a679d9-3f8a-4ccc-937f-45d1ede5eee0.png`
- Text conversation source visual truth: `C:\Users\RighthereWaiting\.codex\generated_images\019fe1a2-7b5a-7293-8cae-436d304b629b\exec-5aa441f4-c349-4ae5-a07f-1d17192e9d52.png`
- Implementation URL: `http://127.0.0.1:3001`
- Implementation screenshot path: unavailable; browser capture is blocked in this Codex session.
- Intended viewport: 390 x 844 CSS px, deviceScaleFactor 1.
- Source dimensions: 853 x 1844 px for each reference (approximately 2.187x the intended CSS width).
- Implementation dimensions: unavailable because no browser-rendered capture could be produced.
- State: mobile Home; empty new Text conversation; GPT Live idle/unconfigured; conversation history after first completed transcript.

## Automated verification

- Backend: 26 passed, 2 skipped.
- Python compile check: passed.
- Frontend TypeScript check: passed.
- Next.js production build: passed.
- Service worker JavaScript syntax: passed.
- Isolated local checks: Home, chat route, generated artwork, app icons, manifest, service worker, and Realtime status are reachable.
- Realtime contract test: server-side key use, WebRTC session payload, project/conversation context, and input transcription configuration passed with a mocked OpenAI upstream.
- Live transcript contract test: completed user and assistant transcripts persist in the conversation and the first user transcript updates the short title.

## Full-view comparison evidence

The two source images were opened at original resolution and inspected. A matching browser-rendered implementation screenshot could not be captured. The required combined source-plus-implementation comparison input therefore does not exist, so no visual match claim is made.

## Focused region comparison evidence

Blocked for the same reason. The required focused comparisons for header controls, hero artwork crop, primary CTA/mode switch, list rows, bottom navigation, empty conversation artwork, starter rows, and composer could not be produced.

## Findings

- [P0] Required browser-rendered evidence is unavailable.
  - Location: mobile Home and conversation screens.
  - Evidence: both source visuals are available, but the in-app Browser and Chrome control interfaces are not exposed in this session.
  - Impact: spacing, overflow, keyboard behavior, safe-area behavior, font rendering, and interaction states cannot be accepted from code/build evidence alone.
  - Fix: capture Home and Text at 390 x 844, combine each capture with its matching source image, inspect, fix P0/P1/P2 differences, and repeat.
- [P1] Real GPT Live media is not end-to-end verified.
  - Location: GPT Live start/listen/interrupt/end flow.
  - Evidence: the current local runtime reports `configured: false`; WebRTC and transcript persistence are covered by isolated tests only.
  - Impact: actual microphone permission, SDP negotiation, streaming audio, transcript event ordering, and interruption behavior remain unproven.
  - Fix: configure the server-side OpenAI key in an approved runtime, then exercise one full user/assistant audio turn without exposing the key.

## Comparison history

- Iteration 1: source visuals opened; implementation capture unavailable; final visual comparison blocked.
- Iteration 2: retried the required in-app Browser, then the allowed Chrome fallback; neither control interface is exposed. Added completed-transcript persistence, Live short-title generation, PWA icons/installability, and stronger automated Realtime tests. These changes improve product completeness but do not substitute for browser visual evidence.
- Iteration 3: the required in-app Browser control interface is still unavailable. Added explicit per-message Save to Memory with an editable, categorized modal; Active/Archived Memory filtering; date-grouped Repository timeline rows; and tighter mobile density for Projects and Settings. Backend tests, TypeScript, production build, Python compile, service-worker syntax, and diff checks pass, but these checks still do not substitute for a browser-rendered comparison.
- Iteration 4: reopened both source visuals at original resolution and retried Browser discovery; the required control interface is still unavailable. Added an honest iPhone Add to Home Screen guide, Project last-activity labels sourced from Repository events, and expandable Repository event details with sensitive/internal fields filtered out. Automated checks pass, but iPhone installation, disclosure layout, and the Project cards remain visually unverified.

## Implementation checklist

- Capture Home and empty Text conversation at 390 x 844.
- Test Home to Text, Home to GPT Live, Text/Live switching, More sheet, Chromium install prompt, iPhone install guide, history sheet, first-title update, per-message Save to Memory, Memory filters, Repository tabs/disclosures, Project open/activity labels, and Settings anchors.
- Check console errors, focus order, horizontal overflow, safe areas, keyboard/composer behavior, and 44 px minimum touch targets.
- Run a real configured GPT Live audio turn.
- Perform combined-image comparisons and resolve every P0/P1/P2 finding.

## Follow-up polish

- Consider a dedicated iOS installation hint because Safari does not emit the Chromium install prompt.
- Revisit the source artwork crop after the first valid phone screenshot.

final result: blocked
