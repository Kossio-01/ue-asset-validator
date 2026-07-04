"""Core reusable validation logic for the Gatekeeper tool.

This module is intentionally free of Unreal-only side effects so the UI can
render results without relying on the editor console.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

try:
    import unreal  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - only happens outside Unreal
    unreal = None


@dataclass(frozen=True)
class ValidationItem:
    actor_label: str
    actor_class: str
    status: str
    message: str


@dataclass(frozen=True)
class ValidationSummary:
    total_selected: int
    checked_static_meshes: int
    passed: int
    flagged: int
    skipped: int
    items: tuple[ValidationItem, ...] = field(default_factory=tuple)


def _safe_actor_label(actor: Any) -> str:
    try:
        return actor.get_actor_label()
    except Exception:
        return getattr(actor, "name", "Unknown Actor")


def _safe_actor_class_name(actor: Any) -> str:
    try:
        return actor.get_class().get_name()
    except Exception:
        return actor.__class__.__name__


def validate_naming_rules(selected_actors: Iterable[object]) -> ValidationSummary:
    """Validate selected actors and return structured results for the UI."""

    items = []
    passed = flagged = skipped = checked_static_meshes = 0
    actors = list(selected_actors or [])

    for actor in actors:
        label = _safe_actor_label(actor)
        class_name = _safe_actor_class_name(actor)

        if "StaticMesh" in class_name:
            checked_static_meshes += 1
            if label.startswith("SM_"):
                passed += 1
                items.append(
                    ValidationItem(
                        actor_label=label,
                        actor_class=class_name,
                        status="pass",
                        message="Matches the SM_ naming convention",
                    )
                )
            else:
                flagged += 1
                items.append(
                    ValidationItem(
                        actor_label=label,
                        actor_class=class_name,
                        status="flag",
                        message="Should start with SM_",
                    )
                )
        else:
            skipped += 1
            items.append(
                ValidationItem(
                    actor_label=label,
                    actor_class=class_name,
                    status="skip",
                    message="Not a StaticMesh actor; skipped",
                )
            )

    return ValidationSummary(
        total_selected=len(actors),
        checked_static_meshes=checked_static_meshes,
        passed=passed,
        flagged=flagged,
        skipped=skipped,
        items=tuple(items),
    )


def get_selected_level_actors():
    """Return the currently selected actors when running inside Unreal."""

    if unreal is None:
        return []
    editor_level_library = getattr(unreal, "EditorLevelLibrary", None)
    if editor_level_library is None:
        return []
    return editor_level_library.get_selected_level_actors()


def run_naming_validation(selected_actors: Sequence[object] | None = None) -> ValidationSummary:
    """Convenience wrapper used by the Unreal UI and scripts."""

    actors = selected_actors if selected_actors is not None else get_selected_level_actors()
    return validate_naming_rules(actors)
