"""Test helper: write the two model files from one combined text."""

from __future__ import annotations

import os


def write_model_files(folder, combined: str) -> tuple[str, str]:
    """Write a catalog given in one YAML text of models with their keys as
    the two real files, models_list.yaml and models.yaml, the way a user
    would split it: every model goes into models.yaml with its api_key,
    base_url and activated; the rest stays in the list. Returns (list
    path, models path). A text with `task_profiles:` or `escalation:`
    needs `write_split_model_files` or `model_file_config`: those
    sections have their own files."""
    import yaml

    data = yaml.safe_load(combined)
    moved = [key for key in ("task_profiles", "escalation") if key in data]
    if moved:
        raise ValueError(f"{', '.join(moved)}: use write_split_model_files or model_file_config")
    listed, personal = [], []
    for model in data.get("models") or []:
        model = dict(model)
        entry = {"name": model.get("name")}
        for key in ("api_key", "base_url", "activated"):
            if key in model:
                entry[key] = model.pop(key)
        listed.append(model)
        personal.append(entry)
    data["models"] = listed
    list_path = os.path.join(str(folder), "models_list.yaml")
    models_path = os.path.join(str(folder), "models.yaml")
    with open(list_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)
    with open(models_path, "w", encoding="utf-8") as f:
        yaml.safe_dump({"models": personal}, f, sort_keys=False)
    return list_path, models_path


def write_split_model_files(folder, combined: str) -> dict[str, str | None]:
    """The layout since 0.1.20: like `write_model_files`, but the
    `task_profiles:` and `escalation:` sections go into task_profiles.yaml
    and escalation.yaml. Returns the four paths as `load_model_catalog`
    keywords (None for a section the text doesn't have)."""
    import yaml

    data = yaml.safe_load(combined)
    paths: dict[str, str | None] = {"profiles_path": None, "escalation_path": None}
    for key, file_name, arg in (
        ("task_profiles", "task_profiles.yaml", "profiles_path"),
        ("escalation", "escalation.yaml", "escalation_path"),
    ):
        if key in data:
            path = os.path.join(str(folder), file_name)
            with open(path, "w", encoding="utf-8") as f:
                yaml.safe_dump({key: data.pop(key)}, f, sort_keys=False)
            paths[arg] = path
    list_path, models_path = write_model_files(folder, yaml.safe_dump(data, sort_keys=False))
    return {"list_path": list_path, "models_path": models_path, **paths}


def model_file_config(folder, combined: str) -> dict[str, str]:
    """`write_split_model_files`, as the Config fields (and benchmark file
    keys) that name the files: "" for a section the text doesn't have."""
    paths = write_split_model_files(folder, combined)
    return {
        "models_list_file": paths["list_path"],
        "models_file": paths["models_path"],
        "task_profiles_file": paths["profiles_path"] or "",
        "escalation_file": paths["escalation_path"] or "",
    }
