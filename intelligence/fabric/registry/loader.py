"""Frozen config and blueprint registry loading for Phase 3."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from intelligence.fabric.common import (
    FabricError,
    REPO_ROOT,
    ensure_exact_keys,
    ensure_list_of_strings,
    ensure_non_empty_string,
    ensure_numeric,
    ensure_object,
    ensure_positive_int,
    load_json_file,
)


FABRIC_CONFIG_FIELDS = (
    "fabric_id",
    "proof_domain",
    "machine_profile",
    "active_population_cap",
    "logical_population_cap",
    "memory_caps",
    "storage_caps",
    "workspace_policy",
    "governance_policy",
    "need_signal_policy",
    "blueprint_registry_path",
    "benchmark_profile",
)

CELL_BLUEPRINT_FIELDS = (
    "cell_id",
    "bundle_ref",
    "role_family",
    "role_name",
    "descriptor_kinds",
    "split_policy",
    "merge_policy",
    "trust_profile",
    "policy_envelope",
    "activation_cost_ms",
    "working_memory_bytes",
    "idle_memory_bytes",
    "descriptor_cache_bytes",
    "memory_tier",
    "utility_profile_ref",
    "allowed_tissues",
)

UTILITY_PROFILE_FIELDS = (
    "reward_weight",
    "novelty_weight",
    "resource_cost_weight",
    "trust_penalty_weight",
    "policy_penalty_weight",
    "split_threshold",
    "merge_threshold",
    "hibernate_threshold",
    "reactivate_threshold",
)

ALLOWED_MEMORY_TIERS = {"hot", "warm", "cold"}


def _resolve_reference_path(reference: str, *, base_dir: Path) -> Path:
    path = Path(reference)
    if path.is_absolute():
        return path.resolve()
    candidate = (base_dir / path).resolve()
    if candidate.exists():
        return candidate
    return (REPO_ROOT / path).resolve()


def load_fabric_bootstrap(config_path: Path) -> tuple[dict[str, Any], Path, dict[str, Any], Path]:
    raw_config = load_json_file(
        config_path.resolve(),
        not_found_code="CONFIG_NOT_FOUND",
        invalid_code="CONFIG_INVALID",
        label="Fabric config",
    )
    if not isinstance(raw_config, dict):
        raise FabricError("CONFIG_INVALID", "Fabric config must be an object.")

    config = validate_fabric_config(raw_config)
    registry_path = _resolve_reference_path(config["blueprint_registry_path"], base_dir=config_path.resolve().parent)
    registry = load_blueprint_registry(registry_path)
    if registry["proof_domain"] != config["proof_domain"]:
        raise FabricError("REGISTRY_INVALID", "Blueprint registry proof_domain does not match FabricConfig proof_domain.")
    return config, config_path.resolve(), registry, registry_path


def validate_fabric_config(raw_config: dict[str, Any]) -> dict[str, Any]:
    ensure_exact_keys(raw_config, FABRIC_CONFIG_FIELDS, "FabricConfig", code="CONFIG_INVALID")
    return {
        "fabric_id": ensure_non_empty_string(raw_config["fabric_id"], "FabricConfig.fabric_id"),
        "proof_domain": ensure_non_empty_string(raw_config["proof_domain"], "FabricConfig.proof_domain"),
        "machine_profile": ensure_object(
            raw_config["machine_profile"], "FabricConfig.machine_profile", code="CONFIG_INVALID"
        ),
        "active_population_cap": ensure_positive_int(
            raw_config["active_population_cap"], "FabricConfig.active_population_cap"
        ),
        "logical_population_cap": ensure_positive_int(
            raw_config["logical_population_cap"], "FabricConfig.logical_population_cap"
        ),
        "memory_caps": ensure_object(raw_config["memory_caps"], "FabricConfig.memory_caps", code="CONFIG_INVALID"),
        "storage_caps": ensure_object(raw_config["storage_caps"], "FabricConfig.storage_caps", code="CONFIG_INVALID"),
        "workspace_policy": ensure_object(
            raw_config["workspace_policy"], "FabricConfig.workspace_policy", code="CONFIG_INVALID"
        ),
        "governance_policy": ensure_object(
            raw_config["governance_policy"], "FabricConfig.governance_policy", code="CONFIG_INVALID"
        ),
        "need_signal_policy": ensure_object(
            raw_config["need_signal_policy"], "FabricConfig.need_signal_policy", code="CONFIG_INVALID"
        ),
        "blueprint_registry_path": ensure_non_empty_string(
            raw_config["blueprint_registry_path"], "FabricConfig.blueprint_registry_path"
        ),
        "benchmark_profile": ensure_object(
            raw_config["benchmark_profile"], "FabricConfig.benchmark_profile", code="CONFIG_INVALID"
        ),
    }


def load_blueprint_registry(registry_path: Path) -> dict[str, Any]:
    raw_registry = load_json_file(
        registry_path.resolve(),
        not_found_code="REGISTRY_NOT_FOUND",
        invalid_code="REGISTRY_INVALID",
        label="Blueprint registry",
    )
    if not isinstance(raw_registry, dict):
        raise FabricError("REGISTRY_INVALID", "Blueprint registry must be an object.")

    expected_registry_keys = {"registry_version", "proof_domain", "utility_profiles", "blueprints"}
    ensure_exact_keys(raw_registry, expected_registry_keys, "BlueprintRegistry", code="REGISTRY_INVALID")

    registry_version = ensure_non_empty_string(raw_registry["registry_version"], "BlueprintRegistry.registry_version")
    if registry_version != "agif.fabric.blueprints.v1":
        raise FabricError("REGISTRY_INVALID", "BlueprintRegistry.registry_version must be agif.fabric.blueprints.v1.")

    proof_domain = ensure_non_empty_string(raw_registry["proof_domain"], "BlueprintRegistry.proof_domain")
    utility_profiles_raw = ensure_object(
        raw_registry["utility_profiles"], "BlueprintRegistry.utility_profiles", code="REGISTRY_INVALID"
    )
    blueprints_raw = raw_registry["blueprints"]
    if not isinstance(blueprints_raw, list) or len(blueprints_raw) == 0:
        raise FabricError("REGISTRY_INVALID", "BlueprintRegistry.blueprints must be a non-empty array.")

    utility_profiles: dict[str, dict[str, Any]] = {}
    for profile_name, profile_raw in sorted(utility_profiles_raw.items()):
        profile_key = ensure_non_empty_string(profile_name, "BlueprintRegistry.utility_profiles key", code="REGISTRY_INVALID")
        if not isinstance(profile_raw, dict):
            raise FabricError("REGISTRY_INVALID", f"Utility profile {profile_key} must be an object.")
        utility_profiles[profile_key] = _validate_utility_profile(profile_raw, profile_key)

    blueprints: list[dict[str, Any]] = []
    seen_cell_ids: set[str] = set()
    for index, blueprint_raw in enumerate(blueprints_raw):
        if not isinstance(blueprint_raw, dict):
            raise FabricError("REGISTRY_INVALID", f"BlueprintRegistry.blueprints[{index}] must be an object.")
        blueprint = _validate_cell_blueprint(
            blueprint_raw,
            blueprint_index=index,
            utility_profiles=utility_profiles,
            registry_path=registry_path,
        )
        if blueprint["cell_id"] in seen_cell_ids:
            raise FabricError("REGISTRY_INVALID", f"Duplicate blueprint cell_id: {blueprint['cell_id']}.")
        seen_cell_ids.add(blueprint["cell_id"])
        blueprints.append(blueprint)

    return {
        "registry_version": registry_version,
        "proof_domain": proof_domain,
        "utility_profiles": utility_profiles,
        "blueprints": sorted(blueprints, key=lambda item: item["cell_id"]),
    }


def _validate_utility_profile(raw_profile: dict[str, Any], profile_name: str) -> dict[str, Any]:
    ensure_exact_keys(raw_profile, UTILITY_PROFILE_FIELDS, f"CellUtilityProfile:{profile_name}", code="REGISTRY_INVALID")
    normalized: dict[str, Any] = {}
    for field_name in UTILITY_PROFILE_FIELDS:
        normalized[field_name] = ensure_numeric(
            raw_profile[field_name],
            f"CellUtilityProfile:{profile_name}.{field_name}",
            code="REGISTRY_INVALID",
        )
    return normalized


def _validate_cell_blueprint(
    raw_blueprint: dict[str, Any],
    *,
    blueprint_index: int,
    utility_profiles: dict[str, dict[str, Any]],
    registry_path: Path,
) -> dict[str, Any]:
    label = f"CellBlueprint[{blueprint_index}]"
    ensure_exact_keys(raw_blueprint, CELL_BLUEPRINT_FIELDS, label, code="REGISTRY_INVALID")

    utility_profile_ref = ensure_non_empty_string(
        raw_blueprint["utility_profile_ref"],
        f"{label}.utility_profile_ref",
        code="REGISTRY_INVALID",
    )
    if utility_profile_ref not in utility_profiles:
        raise FabricError("REGISTRY_INVALID", f"{label}.utility_profile_ref does not exist in utility_profiles.")

    bundle_ref = ensure_non_empty_string(raw_blueprint["bundle_ref"], f"{label}.bundle_ref", code="REGISTRY_INVALID")
    bundle_path = _resolve_reference_path(bundle_ref, base_dir=registry_path.parent)
    if not bundle_path.exists() or not bundle_path.is_file():
        raise FabricError("REGISTRY_INVALID", f"{label}.bundle_ref does not point to a readable file.")

    memory_tier = ensure_non_empty_string(raw_blueprint["memory_tier"], f"{label}.memory_tier", code="REGISTRY_INVALID")
    if memory_tier not in ALLOWED_MEMORY_TIERS:
        raise FabricError("REGISTRY_INVALID", f"{label}.memory_tier must be one of: hot,warm,cold.")

    return {
        "cell_id": ensure_non_empty_string(raw_blueprint["cell_id"], f"{label}.cell_id", code="REGISTRY_INVALID"),
        "bundle_ref": bundle_ref,
        "role_family": ensure_non_empty_string(raw_blueprint["role_family"], f"{label}.role_family", code="REGISTRY_INVALID"),
        "role_name": ensure_non_empty_string(raw_blueprint["role_name"], f"{label}.role_name", code="REGISTRY_INVALID"),
        "descriptor_kinds": ensure_list_of_strings(
            raw_blueprint["descriptor_kinds"], f"{label}.descriptor_kinds", code="REGISTRY_INVALID"
        ),
        "split_policy": ensure_object(
            raw_blueprint["split_policy"], f"{label}.split_policy", code="REGISTRY_INVALID"
        ),
        "merge_policy": ensure_object(
            raw_blueprint["merge_policy"], f"{label}.merge_policy", code="REGISTRY_INVALID"
        ),
        "trust_profile": ensure_object(
            raw_blueprint["trust_profile"], f"{label}.trust_profile", code="REGISTRY_INVALID"
        ),
        "policy_envelope": ensure_object(
            raw_blueprint["policy_envelope"], f"{label}.policy_envelope", code="REGISTRY_INVALID"
        ),
        "activation_cost_ms": ensure_positive_int(
            raw_blueprint["activation_cost_ms"], f"{label}.activation_cost_ms", code="REGISTRY_INVALID"
        ),
        "working_memory_bytes": ensure_positive_int(
            raw_blueprint["working_memory_bytes"], f"{label}.working_memory_bytes", code="REGISTRY_INVALID"
        ),
        "idle_memory_bytes": ensure_positive_int(
            raw_blueprint["idle_memory_bytes"], f"{label}.idle_memory_bytes", code="REGISTRY_INVALID"
        ),
        "descriptor_cache_bytes": ensure_positive_int(
            raw_blueprint["descriptor_cache_bytes"], f"{label}.descriptor_cache_bytes", code="REGISTRY_INVALID"
        ),
        "memory_tier": memory_tier,
        "utility_profile_ref": utility_profile_ref,
        "allowed_tissues": ensure_list_of_strings(
            raw_blueprint["allowed_tissues"], f"{label}.allowed_tissues", code="REGISTRY_INVALID"
        ),
    }
