"""Folder-backed prompt queue for ComfyUI V3."""

from pathlib import Path

from comfy_api.latest import io
from ..categories import TEXT

from ...runtime_state import with_queue_state


def normalize_extensions(extensions: str) -> tuple[str, ...]:
    values = tuple(
        f".{item.strip().lstrip('.').lower()}"
        for item in str(extensions).split(",")
        if item.strip()
    )
    return values or (".txt",)


def get_files(folder_path: str, extensions: str) -> list[Path]:
    folder = Path(folder_path).expanduser()
    if not folder.is_dir():
        return []
    allowed = set(normalize_extensions(extensions))
    try:
        return sorted(
            (path for path in folder.iterdir() if path.is_file() and path.suffix.lower() in allowed),
            key=lambda path: path.name,
        )
    except OSError as exc:
        print(f"[PromptQueueFromFolder] Error listing files: {exc}")
        return []


def snapshot_files(paths: list[Path]) -> list[tuple[str, int, int]]:
    snapshot: list[tuple[str, int, int]] = []
    for path in paths:
        try:
            stat = path.stat()
        except OSError:
            continue
        snapshot.append((str(path), stat.st_mtime_ns, stat.st_size))
    return snapshot


def _new_state() -> dict:
    return {"index": 0, "files": [], "config": None, "reset_trigger": None}


class PromptQueueFromFolder(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="PromptQueueFromFolder",
            display_name="Prompt Queue (From Folder)",
            category=TEXT,
            inputs=[
                io.String.Input("folder_path", default="C:/Prompts", multiline=False),
                io.String.Input("extensions", default="txt, json", optional=True),
                io.Combo.Input("on_end", options=["empty", "loop", "hold_last"], default="empty", optional=True),
                io.Int.Input("reset_trigger", default=0, min=0, max=2**31 - 1, optional=True),
            ],
            outputs=[
                io.String.Output(display_name="prompt_text"),
                io.String.Output(display_name="filename"),
            ],
            hidden=[io.Hidden.unique_id],
            not_idempotent=True,
        )

    @classmethod
    def fingerprint_inputs(cls, **kwargs):
        return float("nan")

    @classmethod
    def execute(
        cls,
        folder_path,
        extensions="txt, json",
        on_end="empty",
        reset_trigger=0,
    ) -> io.NodeOutput:
        node_id = getattr(cls.hidden, "unique_id", "unknown")
        current_files = get_files(str(folder_path), str(extensions))
        snapshot = snapshot_files(current_files)

        def next_value(state: dict) -> tuple[str, str]:
            config = (str(Path(str(folder_path)).expanduser()), normalize_extensions(str(extensions)))
            reset_changed = state["reset_trigger"] != int(reset_trigger)
            files_changed = state["files"] != snapshot
            if state["config"] != config or reset_changed or files_changed:
                state["files"] = snapshot
                state["index"] = 0
                state["config"] = config
                state["reset_trigger"] = int(reset_trigger)
                print(f"[PromptQueueFromFolder] Folder scanned: {len(snapshot)} files found")

            if not state["files"]:
                return "", "no_files_found"

            count = len(state["files"])
            index = state["index"]
            if index >= count:
                if on_end == "loop":
                    index = 0
                    state["index"] = 0
                elif on_end == "hold_last":
                    index = count - 1
                else:
                    return "", "end_of_list"

            path = Path(state["files"][index][0])
            try:
                content = path.read_text(encoding="utf-8")
            except Exception as exc:
                content = f"Error reading file: {exc}"
                print(f"[PromptQueueFromFolder] Error reading {path.name}: {exc}")

            next_index = state["index"] + 1
            if next_index >= count:
                if on_end == "loop":
                    state["index"] = 0
                elif on_end == "hold_last":
                    state["index"] = count - 1
                else:
                    state["index"] = count
            else:
                state["index"] = next_index
            return content, path.name

        content, filename = with_queue_state("folder_prompt", node_id, _new_state, next_value)
        return io.NodeOutput(content, filename)


__all__ = ["PromptQueueFromFolder", "get_files", "normalize_extensions", "snapshot_files"]
