import importlib
import pkgutil
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_ROOT = PROJECT_ROOT / "app"

if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))


def _alias_package_modules(source_package: str, target_package: str) -> None:
    source = importlib.import_module(source_package)

    if hasattr(source, "__path__"):
        for _, module_name, _ in pkgutil.walk_packages(
            source.__path__, prefix=f"{source_package}."
        ):
            importlib.import_module(module_name)

    for module_name, module in list(sys.modules.items()):
        if module_name == source_package or module_name.startswith(f"{source_package}."):
            aliased_name = f"{target_package}{module_name[len(source_package):]}"
            sys.modules[aliased_name] = module


_alias_package_modules("_alembic", "app._alembic")
