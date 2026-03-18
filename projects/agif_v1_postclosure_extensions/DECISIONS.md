# Decisions

| ID | Date | Decision | Why it is locked now |
| --- | --- | --- | --- |
| V1X-D-001 | 2026-03-18 | Track B lives under `projects/agif_v1_postclosure_extensions/` as a separate initiative inside the AGIF v1 repo. | Keeps extension work organized without reopening the closed AGIF v1 phase history. |
| V1X-D-002 | 2026-03-18 | Extension progress uses fixed denominator `130` only inside this project folder. | Prevents extension work from altering the closed AGIF v1 `600/600` record. |
| V1X-D-003 | 2026-03-18 | Extension tokens are tracked only inside this project folder and not in the root AGIF v1 pass-token file. | Keeps the closed v1 proof and the extension evidence clearly separated. |
| V1X-D-004 | 2026-03-18 | The ordered dependency chain is setup -> organic load -> skill graph -> POS domain -> bundle close. | Prevents later proof claims from getting ahead of missing prerequisites. |
| V1X-D-005 | 2026-03-18 | Root AGIF v1 remains finance-only proof for the closed v1 claim even after extension work starts. | Protects the already-closed v1 research story from scope drift. |

