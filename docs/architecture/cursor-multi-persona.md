## Cursor-native multi-persona workflow (no CrewAI)

This repo uses Cursor chats with five personas: Coordinator ("Kenny"), Architect, Implementer, Tester, and Voice of Customer (VoC). See the shared rules in `.cursorrules`.

### Setup
- Create five saved chat tabs and name them: `Coordinator (Kenny)`, `Architect`, `Implementer`, `Tester`, `Voice of Customer`.
- For each chat, add a one-line role rule via the gear icon:
  - Coordinator: "You are the Coordinator (Kenny). Plan and orchestrate plan → design → implement → test; enforce ADR/NFR alignment."
  - Architect: "You are the Architect. Propose/update notes and ADRs under `docs/architecture`; keep design minimal."
  - Implementer: "You are the Implementer. Apply minimal, safe edits and draft an atomic commit message."
  - Tester: "You are the Tester. Verify acceptance criteria; produce a short pass/fail report."
  - VoC: "You are the Voice of Customer. Optimize for user value: be a better friend/partner and save time managing messages/time."

### Typical cycle
1) Coordinator: State objective + acceptance criteria; request a numbered plan and expected handoffs.
2) VoC: Review objective for user value; flag risks and propose success metrics; go/no-go.
3) Architect: Draft/update design or ADRs; output filenames/sections to change.
4) Implementer (Agent mode): Apply only the specified edits; show diffs and proposed commit message.
5) Tester: Validate against criteria; summarize pass/fail and follow-ups.
6) Coordinator: Summarize outcome; decide next step.

### Notes
- Follow ADRs in `docs/architecture/decision-records` and security posture; prefer local-first. External egress must be on the allowlist.
- Calendar actions require explicit human approval; defaults to WhatsApp for approvals when available.
- Keep edits minimal and reviewable. Defer non-essential scope.
