from dotenv import load_dotenv
import os
import pytest
import subprocess
import time
from typing import Optional

load_dotenv(override=True)

def run_command(command: str, expected_success: bool = True, delay: int = 2) -> Optional[str]:
    print(f"\n=== Running: {command} ===")

    # Check whether to use local or hosted node 
    node_url = os.getenv('NODE_URL')
    print(f"Node URL: {node_url}")
    node_url = node_url.split('://')[1].split(':')[0]
    command = command.replace('localhost', node_url)

    try:
        result = subprocess.run(command, shell=True, check=expected_success, 
                              capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(f"STDERR: {result.stderr}")
        time.sleep(delay)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Command failed with error: {e}")
        print(f"STDERR: {e.stderr}")
        if expected_success:
            raise
        return None

class TestNapthaCLI:
    @pytest.mark.parametrize("command", [
        pytest.param("naptha agents", id="list_agents"),
        pytest.param("naptha tools", id="list_tools"),
        pytest.param("naptha orchestrators", id="list_orchestrators"),
        pytest.param("naptha kbs", id="list_kbs"),
        pytest.param("naptha memories", id="list_memories"),
        pytest.param("naptha environments", id="list_environments"),
        pytest.param("naptha personas", id="list_personas"),
        pytest.param("naptha nodes", id="list_nodes"),
        pytest.param('naptha agents agent_name -c "description=\'Agent description\' parameters=\'{tool_name: str, tool_input_data: str}\' module_url=\'ipfs://QmNer9SRKmJPv4Ae3vdVYo6eFjPcyJ8uZ2rRSYd3koT6jg\'"', id="create_agent"),
        pytest.param("naptha agents agent_name -u \"module_version='v0.2'\"", id="update_agent"),
        pytest.param("naptha agents -d agent_name", id="delete_agent"),
        pytest.param("naptha tools tool_name -c \"description='Tool description' parameters='{tool_input_1: str, tool_input_2: str}' module_url='ipfs://QmNer9SRKmJPv4Ae3vdVYo6eFjPcyJ8uZ2rRSYd3koT6jg'\"", id="create_tool"),
        pytest.param("naptha tools tool_name -u \"module_version='v0.2'\"", id="update_tool"),
        pytest.param("naptha tools -d tool_name", id="delete_tool"),
        pytest.param("naptha orchestrators orchestrator_name -c \"description='Orchestrator description' parameters='{input_parameter_1: str, input_parameter_2: int}' module_url='ipfs://QmNer9SRKmJPv4Ae3vdVYo6eFjPcyJ8uZ2rRSYd3koT6jg'\"", id="create_orchestrator"),
        pytest.param("naptha orchestrators orchestrator_name -u \"module_version='v0.2'\"", id="update_orchestrator"),
        pytest.param("naptha orchestrators -d orchestrator_name", id="delete_orchestrator"),
        pytest.param("naptha kbs kb_name -c \"description='Knowledge Base description' parameters='{input_parameter_1: str, input_parameter_2: int}' module_url='ipfs://QmNer9SRKmJPv4Ae3vdVYo6eFjPcyJ8uZ2rRSYd3koT6jg'\"", id="create_kb"),
        pytest.param("naptha kbs kb_name -u \"module_version='v0.2'\"", id="update_kb"),
        pytest.param("naptha kbs -d kb_name", id="delete_kb"),
        pytest.param("naptha memories memory_name -c \"description='Memory description' parameters='{input_parameter_1: str, input_parameter_2: int}' module_url='ipfs://QmNer9SRKmJPv4Ae3vdVYo6eFjPcyJ8uZ2rRSYd3koT6jg'\"", id="create_memory"),
        pytest.param("naptha memories memory_name -u \"module_version='v0.2'\"", id="update_memory"),
        pytest.param("naptha memories -d memory_name", id="delete_memory"),
        pytest.param("naptha environments environment_name -c \"description='Environment description' parameters='{input_parameter_1: str, input_parameter_2: int}' module_url='ipfs://QmNer9SRKmJPv4Ae3vdVYo6eFjPcyJ8uZ2rRSYd3koT6jg'\"", id="create_environment"),
        pytest.param("naptha environments environment_name -u \"module_version='v0.2'\"", id="update_environment"),
        pytest.param("naptha environments -d environment_name", id="delete_environment"),
        pytest.param("naptha personas persona_name -c \"description='Persona description' parameters='{input_parameter_1: str, input_parameter_2: int}' module_url='ipfs://QmNer9SRKmJPv4Ae3vdVYo6eFjPcyJ8uZ2rRSYd3koT6jg'\"", id="create_persona"),
        pytest.param("naptha personas persona_name -u \"module_version='v0.2'\"", id="update_persona"),
        pytest.param("naptha personas -d persona_name", id="delete_persona"),
    ])
    def test_hub_command(self, command):
        assert run_command(command) is not None, f"Command failed: {command}"

    @pytest.mark.parametrize("command", [
        pytest.param("naptha create agent:hello_world_agent", id="create_hello_world_agent"),
        pytest.param("naptha create tool:generate_image_tool", id="create_generate_image_tool"),
        pytest.param("naptha create orchestrator:multiagent_chat --agent_modules \"agent:simple_chat_agent,agent:simple_chat_agent\" --agent_nodes \"localhost,localhost\" --kb_modules \"kb:groupchat_kb\" --kb_nodes \"localhost\"", id="create_multiagent_chat"),
        pytest.param("naptha create kb:wikipedia_kb", id="create_wikipedia_kb"),
        pytest.param("naptha create environment:groupchat_environment", id="create_groupchat_environment"),
        pytest.param("naptha create memory:cognitive_memory", id="create_cognitive_memory"),
    ])
    def test_create_module_command(self, command):
        if not os.path.exists(".env"):
            run_command("cp .env.example .env")
            pytest.skip("Please fill in your .env file with appropriate credentials before continuing")
        assert run_command(command) is not None, f"Command failed: {command}"

    @pytest.mark.parametrize("command", [
        pytest.param("naptha run agent:hello_world_agent -p \"firstname=sam surname=altman\"", id="run_hello_world"),
        pytest.param("naptha run agent:simple_chat_agent -p \"tool_name='chat' tool_input_data='what is an ai agent?'\"", id="run_chat_agent"),
        pytest.param("naptha run tool:generate_image_tool -p \"tool_name='generate_image_tool' prompt='A beautiful image of a cat'\"", id="run_generate_image_tool"),
        pytest.param("naptha run agent:generate_image_agent -p \"tool_name='generate_image_tool' prompt='A beautiful image of a cat'\" --tool_nodes \"localhost\"", id="run_generate_image_agent"),
        pytest.param("naptha run orchestrator:multiagent_chat -p \"prompt='i would like to count up to ten, one number at a time. ill start. one.'\" --agent_nodes \"localhost,localhost\" --kb_nodes \"localhost\"", id="run_multiagent_chat"),
        pytest.param("naptha run kb:wikipedia_kb -p \"func_name='init'\"", id="init_wikipedia_kb"),
        pytest.param("""naptha run kb:wikipedia_kb -p '{
            "func_name": "list_rows",
            "func_input_data": {
                "limit": "10"
            }
        }'""", id="list_wikipedia_data"),
        pytest.param("""naptha run kb:wikipedia_kb -p '{
            "func_name": "add_data",
            "func_input_data": {
                "url": "https://en.wikipedia.org/wiki/Socrates",
                "title": "Socrates",
                "text": "Socrates was a Greek philosopher from Athens."
            }
        }'""", id="add_wikipedia_data"),
        pytest.param("""naptha run kb:wikipedia_kb -p '{
            "func_name": "run_query",
            "func_input_data": {
                "query": "Socrates"
            }
        }'""", id="query_wikipedia_data"),
        pytest.param("""naptha run kb:wikipedia_kb -p '{
            "func_name": "delete_row",
            "func_input_data": {
                "condition": {
                    "title": "Socrates"
                }
            }
        }'""", id="delete_wikipedia_data"),
        pytest.param("naptha run agent:wikipedia_agent -p \"func_name='run_query' query='Elon Musk' question='Who is Elon Musk?'\" --kb_nodes \"localhost\"", id="run_wiki_agent"),
        pytest.param("""naptha run kb:wikipedia_kb -p '{
            "func_name": "delete_table",
            "func_input_data": {
                "table_name": "wikipedia_kb"
            }
        }'""", id="delete_wikipedia_table"),
        pytest.param("naptha run memory:cognitive_memory -p \"func_name='init'\"", id="init_cognitive_memory"),
        pytest.param("""naptha run memory:cognitive_memory -p '{
            "func_name": "store_cognitive_item", 
            "func_input_data": {
                "cognitive_step": "reflection",
                "content": "I am reflecting."
            }
        }'""", id="store_cognitive_memory"),
        pytest.param("""naptha run memory:cognitive_memory -p '{
            "func_name": "get_cognitive_items",
            "func_input_data": {
                "cognitive_step": "reflection" 
            }
        }'""", id="get_cognitive_memory"),
        pytest.param("""naptha run memory:cognitive_memory -p '{
            "func_name": "delete_cognitive_items",
            "func_input_data": {
                "condition": {"cognitive_step": "reflection"}
            }
        }'""", id="delete_cognitive_memory"),
    ])
    def test_run_module_command(self, command):
        if not os.path.exists(".env"):
            run_command("cp .env.example .env")
            pytest.skip("Please fill in your .env file with appropriate credentials before continuing")
        assert run_command(command) is not None, f"Command failed: {command}"

    @pytest.mark.parametrize("command", [
        pytest.param("naptha storage fs create test_upload -f README.md", id="create_fs_storage"),
        pytest.param("naptha storage fs list test_upload", id="list_fs_storage"),
        pytest.param("naptha storage fs read test_upload", id="read_fs_storage"),
        pytest.param("""naptha storage db create test_table -d '{
            "schema": {
                "id": {"type": "TEXT", "primary_key": true},
                "name": {"type": "TEXT", "required": true},
                "age": {"type": "INTEGER"}
            }
        }'""", id="create_db_table"),
        pytest.param("""naptha storage db create test_table -d '{
            "schema": {
                "id": {"type": "TEXT", "primary_key": true},
                "text": {"type": "TEXT", "required": true},
                "embedding": {"type": "vector", "dimension": 3}
            }
        }'""", id="write_db_data"),
        pytest.param("naptha storage db read test_table", id="read_db_data"),
        pytest.param("""naptha inference completions "What is artificial intelligence?" -m "hermes3:8b\"""", id="run_inference_ai"),
    ])
    def test_storage_and_inference_command(self, command):
        assert run_command(command) is not None, f"Command failed: {command}"