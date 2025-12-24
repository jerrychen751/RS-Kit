from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "src" / "rskit" / "core" / "registry.py"


def _load_ast(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"))


def _find_plugin_specs(tree: ast.AST) -> Dict[str, Tuple[str, str]]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Attribute) and target.attr == "_plugin_specs":
                    return ast.literal_eval(node.value)
        if isinstance(node, ast.AnnAssign):
            target = node.target
            if isinstance(target, ast.Attribute) and target.attr == "_plugin_specs":
                return ast.literal_eval(node.value)
    raise ValueError("Unable to find _plugin_specs in registry.")


def _module_to_path(module_path: str) -> Path:
    return ROOT / "src" / Path(*module_path.split("."))


def _load_schema_json(schema_path: Path) -> Dict[str, Any]:
    data = json.loads(schema_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Schema JSON must be an object: {schema_path}")
    return data


def _validate_list_of_strings(
    section: Dict[str, Any],
    key: str,
    errors: List[str],
    schema_path: Path,
) -> None:
    value = section.get(key)
    if value is None:
        return
    if not isinstance(value, list):
        errors.append(f"{schema_path}: '{key}' must be a list")
        return
    if not all(isinstance(item, str) for item in value):
        errors.append(f"{schema_path}: '{key}' must contain only strings")


def _validate_dict(
    section: Dict[str, Any],
    key: str,
    errors: List[str],
    schema_path: Path,
) -> None:
    value = section.get(key)
    if value is None:
        return
    if not isinstance(value, dict):
        errors.append(f"{schema_path}: '{key}' must be an object")


def _validate_required_any_of(
    section: Dict[str, Any],
    errors: List[str],
    schema_path: Path,
) -> None:
    value = section.get("required_any_of")
    if value is None:
        return
    if not isinstance(value, list):
        errors.append(f"{schema_path}: 'required_any_of' must be a list")
        return
    for group_index, group in enumerate(value):
        if not isinstance(group, list):
            errors.append(
                f"{schema_path}: 'required_any_of' group {group_index} must be a list"
            )
            continue
        for option_index, option in enumerate(group):
            if not isinstance(option, list):
                errors.append(
                    f"{schema_path}: 'required_any_of' group {group_index} option {option_index} must be a list"
                )
                continue
            if not all(isinstance(item, str) for item in option):
                errors.append(
                    f"{schema_path}: 'required_any_of' group {group_index} option {option_index} must contain only strings"
                )


def _validate_section(
    section: Dict[str, Any],
    schema_path: Path,
    errors: List[str],
) -> None:
    _validate_list_of_strings(section, "required_fields", errors, schema_path)
    _validate_list_of_strings(section, "optional_fields", errors, schema_path)
    _validate_list_of_strings(section, "notes", errors, schema_path)
    _validate_dict(section, "field_descriptions", errors, schema_path)
    _validate_required_any_of(section, errors, schema_path)


def _validate_schema(schema_path: Path, errors: List[str]) -> None:
    try:
        schema = _load_schema_json(schema_path)
    except (ValueError, json.JSONDecodeError) as exc:
        errors.append(f"{schema_path}: {exc}")
        return

    for key in ("credential_schema", "params_schema"):
        if key not in schema:
            errors.append(f"{schema_path}: missing '{key}' section")
            continue
        section = schema.get(key)
        if not isinstance(section, dict):
            errors.append(f"{schema_path}: '{key}' must be an object")
            continue
        _validate_section(section, schema_path, errors)


def _schema_path_for_plugin(module_path: str) -> Path:
    module_file = _module_to_path(module_path).with_suffix(".py")
    return module_file.with_name("schema.json")


def main() -> None:
    specs = _find_plugin_specs(_load_ast(REGISTRY_PATH))
    errors: List[str] = []

    for source, (module_path, _class_name) in specs.items():
        schema_path = _schema_path_for_plugin(module_path)
        if not schema_path.exists():
            errors.append(f"{schema_path}: missing for source '{source}'")
            continue
        _validate_schema(schema_path, errors)

    if errors:
        print("Schema validation failed:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print("Schema validation passed.")


if __name__ == "__main__":
    main()
