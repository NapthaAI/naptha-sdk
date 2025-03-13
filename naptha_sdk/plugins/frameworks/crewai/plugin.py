import json
from pathlib import Path
from importlib.metadata import version
from typing import List, Dict
from packaging.version import parse
from naptha_sdk.plugins.core import NapthaPlugin
from jinja2 import Template  # Added import for Jinja2

class CrewAIPlugin(NapthaPlugin):
    
    @property
    def framework(self) -> str:
        """Identifier for the framework"""
        return self.metadata["name"]
    
    def __init__(self):
        self.metadata = self._load_metadata()
        self.supported_versions = self.metadata["officially_supported_versions"]
        self.tested_combinations = self.metadata["tested_package_and_python_versions"]
        
    def _load_metadata(self):
        metadata_path = Path(__file__).parent / "metadata.json"
        with open(metadata_path) as f:
            return json.load(f)
    
    def _version_in_range(self, pkg: str, ver: str) -> bool:
        """Check if installed version matches supported ranges"""
        supported = self.supported_versions.get(pkg, "")
        if not supported:
            return False
            
        current = parse(ver)
        return any(
            current in self._parse_specifier(spec)
            for spec in supported.split("||")
        )
    
    def _parse_specifier(self, spec: str):
        """Parse version specifiers into Version objects"""
        from packaging.specifiers import SpecifierSet
        return SpecifierSet(spec)
    
    def detect_requirements(self, imports: List[str]) -> bool:
        """Check if any crewai packages are imported"""
        return any(imp.startswith(tuple(self.supported_versions.keys())) for imp in imports)
    
    def get_compatible_versions(self, dependencies: Dict[str, str]) -> Dict[str, str]:
        """Find matching version combination from metadata"""
        for combo in self.tested_combinations:
            for pkg_set in combo["packages"]:
                if all(
                    self._version_in_range(pkg, dependencies.get(pkg, "0.0.0"))
                    for pkg in pkg_set.keys()
                ):
                    return pkg_set
        return {}

    @property
    def package_versions(self) -> Dict[str, str]:
        """Dynamically get current versions"""
        return {
            pkg: f"^{version(pkg)}"
            for pkg in self.supported_versions.keys()
            if self._is_installed(pkg)
        }
    
    def _is_installed(self, pkg: str) -> bool:
        try:
            version(pkg)
            return True
        except:
            return False

    def render_agent_code_final_block(self, context: dict) -> str:
        """Generate framework-specific agent code"""
        template_path = Path(__file__).parent / self.metadata["tested_package_and_python_versions"][0]["template"]
        with open(template_path, 'r') as f:
            template_str = f.read()
        template = Template(template_str)
        return template.render(**context)