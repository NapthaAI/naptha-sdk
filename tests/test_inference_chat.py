import asyncio

from pyexpat.errors import messages
from naptha_sdk.schemas import ChatCompletionRequest, ChatMessage
from pydantic import BaseModel
from naptha_sdk.client.naptha import Naptha

async def test_inference_chat_endpoint(naptha: Naptha):
    chat_request = ChatCompletionRequest(
        model="NousResearch/Hermes-3-Llama-3.1-8B",
        messages=[
            ChatMessage(role="user", content="Hello, how are you today?"),
            ChatMessage(role="assistant", content="I am doing well, thank you! How can I help?"),
            ChatMessage(role="user", content="What is the capital of France?")
        ],
        temperature=0.8
    )

    output = await naptha.inference_client.run_inference(chat_request)
    print(output.choices[0].message.content)


async def test_inference_chat_structured_output(naptha: Naptha):
    class User(BaseModel):
        id: str
        name: str
        email: str
        role: str

    def get_openai_structured_schema():
        return {
            "type": "json_schema",
            "json_schema": {
                "name": "User",
                "schema": User.model_json_schema()
            }
        }

    schema = get_openai_structured_schema()

    prompt = """Sam is an intern at NapthaAI. His role is to help with the development of the NapthaAI platform. 
    You can find more information about him on his LinkedIn profile. You can also reach out to him on his email. sam@naptha.ai"""
    chat_request = ChatCompletionRequest(
        model="NousResearch/Hermes-3-Llama-3.1-8B",
        messages=[
            ChatMessage(role="user", content=prompt)
        ],
        temperature=0.8,
        response_format=schema
    )

    output = await naptha.inference_client.run_inference(chat_request)
    output = output.choices[0].message.content
    print(output)


async def main():
    naptha = Naptha()
    await test_inference_chat_structured_output(naptha)


if __name__ == "__main__":
    asyncio.run(main())