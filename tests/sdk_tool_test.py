from naptha_sdk.toolset import Toolset
import asyncio

async def main():
    # Initialize Toolset
    worker_node_url = "http://0.0.0.0:7001"  # Replace with your worker node URL
    agent_id = "test-agent-id"  # Replace with your agent ID
    
    toolset = Toolset(worker_node_url=worker_node_url, agent_id=agent_id)
    
    try:
        # Test loading a tool repository
        print("\n1. Testing load_or_add_tool_repo_to_toolset:")
        await toolset.load_or_add_tool_repo_to_toolset(
            toolset_name="test-toolset",
            repo_url="https://github.com/C0deMunk33/test_toolset"
        )
        
        # Test getting toolset list
        print("\n2. Testing get_toolset_list:")
        await toolset.get_toolset_list()
        
        # Test setting a toolset
        print("\n3. Testing set_toolset:")
        await toolset.set_toolset(toolset_name="test-toolset")
        
        # Test getting current toolset
        print("\n4. Testing get_current_toolset:")
        await toolset.get_current_toolset()
        
        # Test running a tool
        print("\n5. Testing run_tool:")
        test_params = {
            "a": "1",
            "b": "1"
        }
        result = await toolset.run_tool(
            toolset_name="test-toolset",
            tool_name="add",
            params=test_params
        )

        print(f"\nTool run result: {result}")
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        raise
    else:
        print("\nAll tests completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())