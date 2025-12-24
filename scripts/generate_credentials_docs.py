from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "src" / "rskit" / "core" / "registry.py"
OUTPUT_PATH = ROOT / "docs" / "credentials.md"


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


def _find_class_schema(tree: ast.AST, class_name: str) -> Dict[str, Any]:
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue
        for stmt in node.body:
            if not isinstance(stmt, ast.Assign):
                continue
            if any(isinstance(t, ast.Name) and t.id == "CREDENTIAL_SCHEMA" for t in stmt.targets):
                return ast.literal_eval(stmt.value)
    raise ValueError(f"Unable to find CREDENTIAL_SCHEMA on class {class_name}.")


def _format_fields(fields: Iterable[str], descriptions: Dict[str, Any]) -> List[str]:
    lines: List[str] = []
    for field in fields:
        description = str(descriptions.get(field, "")).strip()
        if description:
            lines.append(f"- `{field}`: {description}")
        else:
            lines.append(f"- `{field}`")
    return lines


def _render_docs(specs: Dict[str, Tuple[str, str]]) -> str:
    lines: List[str] = [
        "# Data Plugin Credentials",
        "",
        "This page is generated from plugin `CREDENTIAL_SCHEMA` definitions.",
        "Run `python scripts/generate_credentials_docs.py` to update.",
        "",
    ]

    for source, (module_path, class_name) in specs.items():
        module_file = _module_to_path(module_path).with_suffix(".py")
        schema = _find_class_schema(_load_ast(module_file), class_name)
        required = list(schema.get("required_fields", []))
        descriptions = dict(schema.get("field_descriptions", {}))
        optional = [field for field in descriptions.keys() if field not in required]

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

        if optional:
            lines.append("Optional fields:")
            lines.extend(_format_fields(optional, descriptions))
            lines.append("")

        if not required and not optional:
            lines.append("No credentials required.")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    specs = _find_plugin_specs(_load_ast(REGISTRY_PATH))
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(_render_docs(specs), encoding="utf-8")


if __name__ == "__main__":
    main()
