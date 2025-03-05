from pathlib import Path
import shutil
from git import Repo
from rich.table import Table
from rich.console import Console
import json
from naptha_sdk.module_manager import plugin_manager

class PluginCLI:
    @staticmethod
    async def add_plugin(naptha, url: str):
        """Add a plugin from Git repository URL"""
        try:
            plugin_dir = Path("~/.naptha/plugins").expanduser()
            plugin_dir.mkdir(parents=True, exist_ok=True)
            
            repo_name = url.split("/")[-1].replace(".git", "")
            dest_path = plugin_dir / repo_name
            
            if dest_path.exists():
                print(f"Plugin {repo_name} already exists. Use 'update' to refresh.")
                return

            print(f"Cloning plugin from {url}...")
            Repo.clone_from(url, str(dest_path))
            print(f"Successfully added plugin: {repo_name}")
            
            # Reload plugins after addition
            plugin_manager.load_plugins()

        except Exception as e:
            print(f"Plugin addition failed: {str(e)}")

    @staticmethod
    async def remove_plugin(naptha, name: str):
        """Remove an installed plugin"""
        try:
            plugin_dir = Path("~/.naptha/plugins").expanduser() / name
            
            if not plugin_dir.exists():
                print(f"Plugin {name} not found")
                return

            shutil.rmtree(plugin_dir)
            print(f"Successfully removed plugin: {name}")
            
            # Reload plugins after removal
            plugin_manager.load_plugins()

        except Exception as e:
            print(f"Plugin removal failed: {str(e)}")

    @staticmethod
    async def update_plugin(naptha, name: str = None):
        """Update one or all plugins"""
        try:
            plugin_base = Path("~/.naptha/plugins").expanduser()
            
            if name:
                plugins = [plugin_base / name]
            else:
                plugins = [d for d in plugin_base.iterdir() if d.is_dir()]

            updated = []
            for plugin_dir in plugins:
                if not (plugin_dir / ".git").exists():
                    print(f"Skipping {plugin_dir.name} (not a Git repository)")
                    continue
                
                print(f"Updating {plugin_dir.name}...")
                repo = Repo(plugin_dir)
                repo.remotes.origin.pull()
                updated.append(plugin_dir.name)

            if updated:
                print(f"Successfully updated: {', '.join(updated)}")
                plugin_manager.load_plugins()
            else:
                print("No plugins updated")

        except Exception as e:
            print(f"Plugin update failed: {str(e)}")

    @staticmethod
    async def list_plugins(naptha):
        """List all installed plugins"""
        table = Table(title="Installed Plugins")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Version", style="green")
        table.add_column("Path", style="yellow")
        
        plugin_dir = Path("~/.naptha/plugins").expanduser()
        
        for plugin_path in plugin_dir.iterdir():
            if plugin_path.is_dir():
                metadata_path = plugin_path / "metadata.json"
                if metadata_path.exists():
                    with open(metadata_path) as f:
                        metadata = json.load(f)
                    table.add_row(
                        plugin_path.name,
                        metadata.get("plugin_type", "unknown"),
                        metadata.get("sdk_version", "unknown"),
                        str(plugin_path)
                    )
        
        Console().print(table)