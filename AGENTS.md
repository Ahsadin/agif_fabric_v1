# AGIF v1 Local Rules

## Project Identity
- This folder is the standalone root for AGIF v1.
- The authoritative execution plan for this repo is the external `PLAN.md` provided for this workspace.
- Do not treat this work as a sub-initiative inside `agif-tasklet-cell`.
- The old repo `agif-tasklet-cell` is reference-only.
- Never create a runtime dependency on the old repo. If anything is reused later, copy or adapt it into this workspace with provenance.

## Locked Mission
- Preserve the full AGIF architecture in concept:
  - cells
  - tissues
  - skill descriptors
  - shared workspace
  - local and fabric memory
  - bounded adaptation
  - utility and motivation
  - governance
  - replay, rollback, trust, and quarantine
  - growth over time
  - elastic split/merge/hibernate/reactivate lifecycle
- Keep the long-horizon AGIF path visible:
  - large-scale emergence
  - self-organizing intelligence
  - massive autonomous fabric behavior
  - real-world embodied intelligence
  - AGI-like generality
- AGIF v1 does not claim those long-horizon properties are proven yet.
- The locked proof domain is document/workflow intelligence.
- The first real tissue system is the finance document workflow.
- The locked finish line is:
  - runnable local AGIF v1
  - research paper
  - benchmark evidence
  - reproducibility package

## Resource Guardrails
- Primary target machine: Apple M4 MacBook Air, 16 GB RAM, about 65 GiB free disk.
- Target runtime working set must stay at or below 12 GB.
- Total project and evidence footprint must stay at or below 35 GB.
- Raw logs are not long-term memory.
- Need generates pressure; governance validates the response.
- Always distinguish fabric population from active runtime population.

## Working Rules
- Phase 0 is bootstrap only. Do not implement AGIF runtime code during Phase 0.
- Keep changes small, organized, and easy to review.
- Do not restructure folders unless explicitly asked.
- Maintain these source-of-truth files when the project changes:
  - `PROJECT_README.md`
  - `DECISIONS.md`
  - `CHANGELOG.md`
- Record planned carry-forward work in `00_admin/REFERENCE_IMPORT_MATRIX.md` before importing code from the old repo.
- Track workstreams in `00_admin/CODEX_THREAD_MAP.md`.
- Use plain language where possible and define constraints clearly.
- For every verification claim in project work, say whether it was locally verified or only assumed.
