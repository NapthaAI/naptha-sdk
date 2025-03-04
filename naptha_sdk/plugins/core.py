import json
from pathlib import Path
import pluggy
from abc import ABC, abstractmethod
from typing import Dict, List

hookspec = pluggy.HookspecMarker("naptha")
hookimpl = pluggy.HookimplMarker("naptha")

class MetadataLoader:
    def __init__(self, framework_dir):
        self.framework_dir = Path(framework_dir)
        self._metadata = None
    
    @property
    def metadata(self):
        if not self._metadata:
            with open(self.framework_dir / "metadata.json") as f:
                self._metadata = json.load(f)
        return self._metadata
    
    def get(self, key, default=None):
        return self.metadata.get(key, default)

class FrameworkSpecs:
    """Hook specifications for agent framework plugins"""
    
    @hookspec
    def get_decorators(self):
        """Return list of decorator names handled by this framework"""
        
    @hookspec
    def render_agent_code_final_block(self, context):
        """Render framework-specific agent code"""
        
    @hookspec
    def add_dependencies(self):
        """Add framework-specific dependencies to pyproject.toml"""
        
class NapthaPlugin(ABC):
    """Base class for all Naptha plugins"""
    
    @property
    @abstractmethod
    def framework(self) -> str:
        """Identifier for the framework/language"""
        pass
    
    @property
    @abstractmethod
    def package_versions(self) -> Dict[str, str]:
        """Dictionary of required packages with version constraints"""
        pass
    
    @abstractmethod
    def detect_requirements(self, imports: List[str]) -> bool:
        """Determine if this plugin should activate based on imports"""
        pass
        
    @abstractmethod
    def render_agent_code_final_block(self, context: dict) -> str:
        """Generate framework-specific agent code"""
        pass