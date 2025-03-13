from pathlib import Path
import os
import importlib.metadata
import inspect
import importlib.util
from typing import Dict, Any, List
from pathlib import Path
import json
from naptha_sdk.utils import get_logger
from importlib.metadata import entry_points
from naptha_sdk.plugins.core import NapthaPlugin

logger = get_logger(__name__)

class PluginManager:
    def __init__(self):
        self.plugins = []  # Initialize plugins list
        self.plugin_dirs = [
            # Built-in plugins
            Path(__file__).parent / "frameworks",
            # User-installed plugins
            Path("~/.naptha/plugins").expanduser(),
        ]
        # Only add custom plugin path if specified in environment variable
        custom_plugin_path = os.environ.get("NAPTHA_PLUGIN_PATH")
        if custom_plugin_path:
            self.plugin_dirs.append(Path(custom_plugin_path).expanduser())
        logger.info(f"Plugin directories: {self.plugin_dirs}")
        
        # Create directories if they don't exist, before loading plugins
        for dir_path in self.plugin_dirs:
            try:
                if dir_path == Path("~/.naptha/plugins").expanduser():
                    # Create parent .naptha directory if needed
                    dir_path.parent.mkdir(parents=True, exist_ok=True)
                dir_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error(f"Failed to create plugin directory {dir_path}: {str(e)}")
        
        # Load plugins after directories are created
        self.load_plugins()

    def load_plugins(self):
        """Load plugins from both entry points and plugin directories."""
        logger.info("Starting to load plugins")
        # Load from entry points
        try:
            for entry_point in entry_points(group="naptha_sdk.plugins"):
                plugin_class = entry_point.load()
                if inspect.isabstract(plugin_class):
                    logger.warning(f"Skipping abstract plugin class: {plugin_class}")
                    continue
                self.plugins.append(plugin_class())
                logger.info(f"Loaded plugin {plugin_class.__name__} from entry points")
        except Exception as e:
            logger.error(f"Error loading plugins from entry points: {str(e)}")

        # Load from directories
        for dir_path in self.plugin_dirs:
            self._load_from_directory(dir_path)

    def _load_from_directory(self, dir_path: Path):
        """Load plugins from a specified directory."""
        if not dir_path.exists():
            logger.info(f"Plugin directory {dir_path} does not exist, skipping.")
            return
        logger.info(f"Loading plugins from directory: {dir_path}")
        for plugin_dir in dir_path.iterdir():
            if plugin_dir.is_dir() and (plugin_dir / "metadata.json").exists():
                plugin_file = plugin_dir / "plugin.py"
                if plugin_file.exists():
                    try:
                        # Dynamically import the plugin module
                        spec = importlib.util.spec_from_file_location(plugin_dir.name, plugin_file)
                        if spec is None:
                            logger.error(f"Could not create module spec for {plugin_file}")
                            continue
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        # Find the plugin class
                        for name, obj in inspect.getmembers(module):
                            if (inspect.isclass(obj) and 
                                issubclass(obj, NapthaPlugin) and 
                                obj != NapthaPlugin):
                                self.plugins.append(obj())
                                logger.info(f"Loaded plugin {name} from {plugin_dir}")
                                break
                        else:
                            logger.warning(f"No NapthaPlugin subclass found in {plugin_file}")
                    except Exception as e:
                        logger.error(f"Error loading plugin from {plugin_dir}: {str(e)}")
                else:
                    logger.warning(f"No plugin.py found in {plugin_dir}")

    def detect_framework(self, imports: List[str]) -> NapthaPlugin:
        """Detect the appropriate framework plugin based on imports."""
        for plugin in self.plugins:
            if plugin.detect_requirements(imports):
                logger.info(f"Detected framework: {plugin.framework}")
                return plugin
        logger.warning("No supported framework detected")
        return None

    def _load_versions(self, plugin_dir: Path) -> Dict[str, str]:
        """Load template versions from versions directory (for reference, not currently used)."""
        versions_dir = plugin_dir / "versions"
        versions = {}
        if versions_dir.exists():
            for version_dir in versions_dir.iterdir():
                if version_dir.is_dir():
                    version = version_dir.name
                    template_file = version_dir / "template.jinja"
                    if template_file.exists():
                        with open(template_file) as f:
                            versions[version] = f.read()
        return versions

    def select_template(self, package_dependencies: dict) -> str:
        """Select the best template version based on project dependencies (for reference)."""
        plugin = self.detect_framework(list(package_dependencies.keys()))
        if not plugin:
            return None

        best_match = None
        max_matched = 0
        
        for version_spec in plugin.metadata["tested_package_and_python_versions"]:
            for pkg_set in version_spec["packages"]:
                matched = 0
                for pkg, constraint in pkg_set.items():
                    if pkg in package_dependencies:
                        if self._version_match(package_dependencies[pkg], constraint):
                            matched += 1
                if matched > max_matched:
                    best_match = version_spec
                    max_matched = matched
                
        return best_match["template"] if best_match else None

    def _version_match(self, actual_version: str, constraint: str) -> bool:
        """Semantic version matching helper (for reference)."""
        from semantic_version import Version, Spec
        return Version(actual_version) in Spec(constraint)