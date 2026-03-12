# AGIF v1 Runner

This runner is the Phase 3 local fabric foundation.

Frozen commands:
- `./runner/cell fabric init <config_path>`
- `./runner/cell fabric run`
- `./runner/cell fabric status`
- `./runner/cell fabric replay <replay_manifest_path>`
- `./runner/cell fabric evidence <output_path>`

Behavior:
- stdout is bounded JSON only
- success uses `{"ok":true,...}`
- failure uses `{"ok":false,"error":{...}}`
- local runtime state is stored under `runtime_state/` by default
- tests may override the local state root with `AGIF_FABRIC_STATE_ROOT`

