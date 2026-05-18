#!/usr/bin/env python3
"""Generate DTCG 2025.10 token files from a Figma token report JSON."""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


FORMAT_EXTENSION = {
    "format": {
        "name": "Design Tokens Format Module",
        "version": "2025.10",
        "source": "https://www.designtokens.org/tr/2025.10/format/",
    }
}

FONT_WEIGHTS = {
    "thin": 100,
    "ultralight": 200,
    "ultra light": 200,
    "light": 300,
    "regular": 400,
    "normal": 400,
    "medium": 500,
    "semibold": 600,
    "semi bold": 600,
    "bold": 700,
    "heavy": 800,
    "black": 900,
}


@dataclass
class NormalizedName:
    original: str
    normalized: str
    collision: bool
    collision_of: str | None = None


class NameRegistry:
    def __init__(self, translations: dict[str, str] | None = None):
        self.translations = translations or {}
        self.used: dict[str, str] = {}

    def normalize(self, original: str) -> NormalizedName:
        translated = self.translations.get(original, original)
        had_non_english = bool(re.search(r"[^\x00-\x7F]", translated))
        value = translated.lower()
        value = re.sub(r"[^a-z0-9]+", "-", value)
        value = re.sub(r"-+", "-", value).strip("-")
        if not value:
            value = "token"
        if had_non_english and translated == original:
            value = "token"

        base = value
        index = 2
        collision_of = None
        while value in self.used and self.used[value] != original:
            collision_of = self.used[value]
            value = f"{base}-{index}"
            index += 1
        self.used[value] = original
        return NormalizedName(original, value, collision_of is not None, collision_of)


class TokenGenerator:
    def __init__(self, report: dict[str, Any], output_dir: Path, style_types: list[str]):
        self.report = report
        self.output_dir = output_dir
        self.style_types = style_types
        self.translations = report.get("translations", {})
        self.normalization_rows: list[dict[str, Any]] = []
        self.warnings: list[str] = list(report.get("validationWarnings", []))
        self.fallbacks: list[str] = list(report.get("fallbacksUsed", []))
        self.skipped: list[dict[str, str]] = list(report.get("skippedItems", []))
        self.generated_files: list[str] = []

    def add_fallback(self, message: str) -> None:
        if message not in self.fallbacks:
            self.fallbacks.append(message)

    def add_row(
        self,
        *,
        kind: str,
        source: str,
        original: str,
        normalized: NormalizedName,
    ) -> None:
        row = {
            "kind": kind,
            "source": source,
            "originalName": original,
            "normalizedName": normalized.normalized,
            "collision": normalized.collision,
            "collisionOf": normalized.collision_of,
        }
        self.normalization_rows.append(row)
        if normalized.collision:
            self.warnings.append(
                f"Normalized name collision for {kind} '{original}', emitted as '{normalized.normalized}'."
            )

    def generate(self) -> None:
        self.generate_variable_files()
        self.generate_style_files()
        self.update_report()

    def generate_variable_files(self) -> None:
        collections = self.report.get("variableCollections") or self.report.get("variables") or []
        variables_dir = self.output_dir / "tokens" / "variables"
        variables_dir.mkdir(parents=True, exist_ok=True)
        file_registry = NameRegistry(self.translations)

        for collection in collections:
            original_collection = get_name(collection)
            collection_name = file_registry.normalize(original_collection)
            self.add_row(
                kind="collection",
                source="Variable Collections",
                original=original_collection,
                normalized=collection_name,
            )
            self.add_row(
                kind="file",
                source=original_collection,
                original=f"{original_collection}.tokens.json",
                normalized=collection_name,
            )

            document: dict[str, Any] = {
                "$extensions": {
                    **copy.deepcopy(FORMAT_EXTENSION),
                    "figma": {
                        "source": "figma-token-report.json",
                        "collection": original_collection,
                    },
                }
            }
            modes = collection.get("modes", [])
            mode_registry = NameRegistry(self.translations)
            variable_registry = NameRegistry(self.translations)
            variable_names: dict[str, str] = {}

            for variable in collection.get("variables", collection.get("tokens", [])):
                original_variable = get_name(variable)
                variable_name = variable_registry.normalize(original_variable)
                variable_names[original_variable] = variable_name.normalized
                self.add_row(
                    kind="variable",
                    source=original_collection,
                    original=original_variable,
                    normalized=variable_name,
                )

            for mode in modes:
                original_mode = get_name(mode)
                mode_name = mode_registry.normalize(original_mode)
                self.add_row(
                    kind="mode",
                    source=original_collection,
                    original=original_mode,
                    normalized=mode_name,
                )
                mode_group: dict[str, Any] = {}
                for variable in collection.get("variables", collection.get("tokens", [])):
                    original_variable = get_name(variable)
                    token_name = variable_names[original_variable]
                    raw_value = values_by_mode(variable).get(original_mode)
                    mode_group[token_name] = self.variable_token(
                        variable,
                        raw_value,
                        mode_name.normalized,
                        original_mode,
                        variable_names,
                    )
                document[mode_name.normalized] = mode_group

            path = variables_dir / f"{collection_name.normalized}.tokens.json"
            write_json(path, document)
            self.generated_files.append(str(path.relative_to(self.output_dir)))

    def variable_token(
        self,
        variable: dict[str, Any],
        raw_value: Any,
        normalized_mode: str,
        original_mode: str,
        variable_names: dict[str, str],
    ) -> dict[str, Any]:
        original_name = get_name(variable)
        resolved_type = variable.get("type") or variable.get("resolvedType")
        token_type = map_variable_type(resolved_type)
        value, alias = self.convert_value(raw_value, token_type, normalized_mode, variable_names)
        token = {
            "$type": token_type,
            "$value": value,
            "$extensions": {
                "figma": {
                    "originalName": original_name,
                    "resolvedType": resolved_type,
                    "mode": original_mode,
                }
            },
        }
        if alias:
            token["$extensions"]["figma"]["alias"] = alias
        return token

    def convert_value(
        self,
        raw_value: Any,
        token_type: str,
        normalized_mode: str,
        variable_names: dict[str, str],
    ) -> tuple[Any, str | None]:
        if isinstance(raw_value, dict) and "alias" in raw_value:
            alias = raw_value["alias"]
            if alias in variable_names:
                return f"{{{normalized_mode}.{variable_names[alias]}}}", alias
            self.add_fallback(
                f"Resolved cross-file or unknown alias '{alias}' to metadata because no same-file token target was available."
            )
            return raw_value.get("value", f"UNRESOLVED_ALIAS:{alias}"), alias
        if token_type == "color":
            return color_value(raw_value), None
        return raw_value, None

    def generate_style_files(self) -> None:
        styles = self.report.get("styles", {})
        styles_dir = self.output_dir / "tokens" / "styles"
        styles_dir.mkdir(parents=True, exist_ok=True)

        if "color" in self.style_types:
            self.generate_color_styles(styles, styles_dir)
        if "text" in self.style_types:
            self.generate_text_styles(styles, styles_dir)

        for style_type in sorted(set(self.style_types) - {"color", "text"}):
            self.skipped.append(
                {
                    "kind": "style",
                    "name": style_type,
                    "reason": "Requested style type is not implemented by the default DTCG generator.",
                }
            )
            self.add_fallback(
                f"Skipped requested style type '{style_type}' because the default generator only implements color and text styles."
            )

    def generate_color_styles(self, styles: dict[str, Any], styles_dir: Path) -> None:
        color_styles = styles.get("color") or styles.get("paint") or styles.get("paintStyles") or []
        registry = NameRegistry(self.translations)
        document = {
            "$extensions": {
                **copy.deepcopy(FORMAT_EXTENSION),
                "figma": {"source": "figma-token-report.json", "styleType": "color"},
            }
        }
        for style in color_styles:
            original = get_name(style)
            normalized = registry.normalize(original)
            self.add_row(kind="style", source="Color Styles", original=original, normalized=normalized)
            paint = first_solid_paint(style)
            if paint is None:
                self.skipped.append(
                    {
                        "kind": "style",
                        "name": original,
                        "reason": "Color style is not a single solid paint.",
                    }
                )
                continue
            document[normalized.normalized] = {
                "$type": "color",
                "$value": color_value(paint),
                "$extensions": {"figma": {"originalName": original, "styleType": "paint"}},
            }
        path = styles_dir / "color.tokens.json"
        write_json(path, document)
        self.generated_files.append(str(path.relative_to(self.output_dir)))

    def generate_text_styles(self, styles: dict[str, Any], styles_dir: Path) -> None:
        text_styles = styles.get("text") or styles.get("textStyles") or []
        registry = NameRegistry(self.translations)
        document = {
            "$extensions": {
                **copy.deepcopy(FORMAT_EXTENSION),
                "figma": {"source": "figma-token-report.json", "styleType": "text"},
            }
        }
        for style in text_styles:
            original = get_name(style)
            normalized = registry.normalize(original)
            self.add_row(kind="style", source="Text Styles", original=original, normalized=normalized)
            document[normalized.normalized] = {
                "$type": "typography",
                "$value": typography_value(style),
                "$extensions": {
                    "figma": {
                        "originalName": original,
                        "fontStyle": style.get("fontStyle")
                        or style.get("fontName", {}).get("style"),
                    }
                },
            }
        path = styles_dir / "text.tokens.json"
        write_json(path, document)
        self.generated_files.append(str(path.relative_to(self.output_dir)))

    def update_report(self) -> None:
        self.report["generatedAt"] = datetime.now(timezone.utc).isoformat()
        self.report["generatedFiles"] = self.generated_files
        self.report["normalization"] = self.normalization_rows
        self.report["skippedItems"] = self.skipped
        self.report["validationWarnings"] = sorted(set(self.warnings))
        self.report.pop("fallbacksUsed", None)
        write_json(self.output_dir / "figma-token-report.json", self.report)
        write_report_md(self.output_dir / "figma-token-report.md", self.report)


def get_name(item: Any) -> str:
    if isinstance(item, str):
        return item
    return item.get("originalName") or item.get("name") or item.get("label") or "Token"


def values_by_mode(variable: dict[str, Any]) -> dict[str, Any]:
    return variable.get("valuesByMode") or variable.get("values") or {}


def map_variable_type(resolved_type: str | None) -> str:
    return {
        "COLOR": "color",
        "FLOAT": "number",
        "STRING": "string",
        "BOOLEAN": "boolean",
    }.get(str(resolved_type or "").upper(), "string")


def first_solid_paint(style: dict[str, Any]) -> Any | None:
    paints = style.get("paints")
    if paints is None and "value" in style:
        paints = [{"type": "SOLID", "value": style["value"]}]
    if not paints or len(paints) != 1:
        return None
    paint = paints[0]
    if isinstance(paint, str):
        return paint
    if paint.get("type") != "SOLID":
        return None
    return paint.get("value") or paint.get("color") or paint


def color_value(raw: Any) -> dict[str, Any]:
    if isinstance(raw, str):
        match = re.fullmatch(r"#?([0-9a-fA-F]{6})(?:\s*@\s*([\d.]+))?", raw.strip())
        if not match:
            raise ValueError(f"Unsupported color string: {raw}")
        hex_value = f"#{match.group(1).upper()}"
        alpha = float(match.group(2)) if match.group(2) else None
    elif isinstance(raw, dict):
        hex_value = raw.get("hex")
        alpha = raw.get("alpha")
        if not hex_value and {"r", "g", "b"}.issubset(raw):
            rgb = [raw["r"], raw["g"], raw["b"]]
            if all(isinstance(v, (int, float)) and 0 <= v <= 1 for v in rgb):
                rgb = [round(v * 255) for v in rgb]
            hex_value = "#" + "".join(f"{int(v):02X}" for v in rgb)
            alpha = raw.get("a", alpha)
        if not hex_value:
            raise ValueError(f"Unsupported color object: {raw}")
        hex_value = hex_value.upper()
    else:
        raise ValueError(f"Unsupported color value: {raw}")

    r = int(hex_value[1:3], 16) / 255
    g = int(hex_value[3:5], 16) / 255
    b = int(hex_value[5:7], 16) / 255
    value: dict[str, Any] = {
        "colorSpace": "srgb",
        "components": [round(r, 6), round(g, 6), round(b, 6)],
        "hex": hex_value,
    }
    if alpha is not None and float(alpha) != 1:
        value["alpha"] = float(alpha)
    return value


def typography_value(style: dict[str, Any]) -> dict[str, Any]:
    font_family = style.get("fontFamily") or style.get("fontName", {}).get("family")
    font_style = style.get("fontStyle") or style.get("fontName", {}).get("style") or "Regular"
    font_size = float(style.get("fontSize"))
    line_height = style.get("lineHeight")
    letter_spacing = style.get("letterSpacing", 0)

    if isinstance(line_height, dict):
        line_height_value = line_height.get("value")
        if line_height.get("unit") == "PIXELS":
            line_height = float(line_height_value) / font_size
        elif line_height.get("unit") == "PERCENT":
            line_height = float(line_height_value) / 100
        else:
            line_height = line_height_value
    elif isinstance(line_height, (int, float)):
        line_height = float(line_height) / font_size if float(line_height) > 4 else float(line_height)

    if isinstance(letter_spacing, dict):
        letter_spacing = letter_spacing.get("value", 0)

    return {
        "fontFamily": font_family,
        "fontWeight": font_weight(font_style),
        "fontSize": {"value": font_size, "unit": "px"},
        "lineHeight": round(float(line_height), 10),
        "letterSpacing": {"value": float(letter_spacing), "unit": "px"},
    }


def font_weight(font_style: str) -> int:
    style = font_style.lower().replace("italic", "").strip()
    return FONT_WEIGHTS.get(style, 400)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_report_md(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# Figma Token Report",
        "",
        "## Generated Files",
        "",
        *[f"- `{file}`" for file in report.get("generatedFiles", [])],
        "",
        "## Normalization",
        "",
        "| Kind | Source | Original Name | Normalized Name | Collision |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in report.get("normalization", []):
        lines.append(
            f"| {row['kind']} | {row['source']} | {row['originalName']} | {row['normalizedName']} | {row['collision']} |"
        )
    lines.extend(["", "## Skipped Items", ""])
    skipped = report.get("skippedItems", [])
    lines.extend([f"- {item['kind']}: {item['name']} - {item['reason']}" for item in skipped] or ["- None"])
    lines.extend(["", "## Validation Warnings", ""])
    warnings = report.get("validationWarnings", [])
    lines.extend([f"- {warning}" for warning in warnings] or ["- None"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report_json", type=Path, help="Path to figma-token-report.json")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for report updates and token output. Defaults to report directory.",
    )
    parser.add_argument(
        "--style-types",
        default="color,text",
        help="Comma-separated style types to generate. Defaults to color,text.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir or args.report_json.parent
    report = json.loads(args.report_json.read_text(encoding="utf-8"))
    style_types = [part.strip().lower() for part in args.style_types.split(",") if part.strip()]
    generator = TokenGenerator(report, output_dir, style_types)
    generator.generate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
