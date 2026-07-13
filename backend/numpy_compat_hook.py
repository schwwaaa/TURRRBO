# Runtime hook — patches numpy.core → numpy._core for bundled app
import sys
import types

try:
    import numpy._core as _core
    import numpy
    
    # Create numpy.core as an alias pointing to numpy._core
    core_mod = types.ModuleType("numpy.core")
    core_mod.__dict__.update(_core.__dict__)
    core_mod.multiarray = _core._multiarray_umath
    sys.modules["numpy.core"] = core_mod
    sys.modules["numpy.core.multiarray"] = _core._multiarray_umath
    sys.modules["numpy.core._multiarray_umath"] = _core._multiarray_umath
    numpy.core = core_mod
except Exception as e:
    print(f"[numpy_compat] warning: {e}")
