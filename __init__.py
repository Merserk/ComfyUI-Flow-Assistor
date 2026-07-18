"""ComfyUI Flow Assistor — V3-only custom node extension."""

# ComfyUI imports this directory as a package. Some test collectors import the
# file directly because the repository name contains hyphens; avoid executing
# package-relative imports in that unsupported direct-module context.
if __package__:
    from .extension import comfy_entrypoint
else:  # pragma: no cover - exercised only by direct file import/collection.
    comfy_entrypoint = None


WEB_DIRECTORY = "./web"


__all__ = ["WEB_DIRECTORY", "comfy_entrypoint"]
