"""Module metadata protocol."""
from dataclasses import dataclass, field
from fastapi import APIRouter


@dataclass
class ModuleMeta:
    id: str
    tab_key: str
    router: APIRouter
    js_files: list = field(default_factory=list)
    css_files: list = field(default_factory=list)
    enabled_default: bool = True
    order: int = 99
    module_dir: str = ""

    def __post_init__(self):
        if not self.module_dir:
            self.module_dir = self.id.replace("-", "_")

    def install(self):
        """Install module dependencies (pip, dll, dirs)."""

    def uninstall(self):
        """Remove own artifacts (not shared data)."""
