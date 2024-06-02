from importlib import import_module, reload
from pathlib import Path

from .cache import *
from .context import *
from .network import *
from .ratelimit import *
from .regex import *

for patch in Path("tools/managers/patch").glob("**/*.py"):
    reload(import_module(f"tools.managers.patch.{patch.stem}"))
