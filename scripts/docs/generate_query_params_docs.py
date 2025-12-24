from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "src" / "rskit" / "core" / "registry.py"
OUTPUT_PATH = ROOT / "docs" / "query_params.md"


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


def _get_params_schema(module_file: Path, class_name: str) -> Dict[str, Any]:
    schema_path = module_file.with_name("schema.json")
    if not schema_path.exists():
        raise ValueError(f"Missing schema.json for {class_name}: {schema_path}")
    data = _load_schema_json(schema_path)
    schema = data.get("params_schema", {})
    if schema is None:
        return {}
    if not isinstance(schema, dict):
        raise ValueError(
            f"params_schema must be an object: {schema_path}"
        )
    return schema


def _format_fields(fields: Iterable[str], descriptions: Dict[str, Any]) -> List[str]:
    lines: List[str] = []
    for field in fields:
        description = str(descriptions.get(field, "")).strip()
        if description:
            lines.append(f"- `{field}`: {description}")
        else:
            lines.append(f"- `{field}`")
    return lines


def _format_required_any_of(groups: Iterable[Iterable[Iterable[str]]]) -> List[str]:
    lines: List[str] = []
    for group in groups:
        choices = []
        for option in group:
            if len(option) == 1:
                choices.append(f"`{option[0]}`")
            else:
                joined = ", ".join(f"`{item}`" for item in option)
                choices.append(joined)
        if choices:
            lines.append(f"- {', or '.join(choices)}")
    return lines


def _format_notes(notes: Iterable[str]) -> List[str]:
    return [f"- {note}" for note in notes]


def _render_docs(specs: Dict[str, Tuple[str, str]]) -> str:
    lines: List[str] = [
        "# Data Plugin Query Parameters",
        "",
        "This page is generated from plugin `schema.json` definitions.",
        "Run `python scripts/docs/generate_query_params_docs.py` to update.",
        "",
    ]

    for source, (module_path, class_name) in specs.items():
        module_file = _module_to_path(module_path).with_suffix(".py")
        schema = _get_params_schema(module_file, class_name)
        required = list(schema.get("required_fields", []))
        required_any_of = list(schema.get("required_any_of", []))
        optional = list(schema.get("optional_fields", []))
        descriptions = dict(schema.get("field_descriptions", {}))
        notes = list(schema.get("notes", []))

        lines.extend(
            [
                f"## {source}",
                "",
                f"Plugin class: `{class_name}`",
                "",
            ]
        )

        if required:
            lines.append("Required fields:")
            lines.extend(_format_fields(required, descriptions))
            lines.append("")

        if required_any_of:
            lines.append("Required (one of):")
            lines.extend(_format_required_any_of(required_any_of))
            lines.append("")

        if optional:
            lines.append("Optional fields:")
            lines.extend(_format_fields(optional, descriptions))
            lines.append("")

        if notes:
            lines.append("Notes:")
            lines.extend(_format_notes(notes))
            lines.append("")

        if not required and not required_any_of and not optional and not notes:
            lines.append("No plugin-specific query parameters.")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    specs = _find_plugin_specs(_load_ast(REGISTRY_PATH))
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(_render_docs(specs), encoding="utf-8")


if __name__ == "__main__":
    main()
