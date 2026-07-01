from ._core import router  # noqa: F401

# Importing sub-modules triggers their @router.get() registrations
from . import home       # noqa: F401
from . import security   # noqa: F401
from . import graph      # noqa: F401
from . import runtime    # noqa: F401
from . import data       # noqa: F401
from . import integration  # noqa: F401
from . import objects    # noqa: F401
from . import portal     # noqa: F401
from . import platform   # noqa: F401
from . import perf       # noqa: F401
from . import tools      # noqa: F401

__all__ = ["router"]
