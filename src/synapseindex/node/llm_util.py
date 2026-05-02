import os
import asyncio

from litellm import acompletion
import logging

MODEL = None
LOGGER = logging.getLogger(__name__)

class Model:
    def __init__(self, name=None, api_key=None):
        self.model = name
        self.api_key = api_key
    @staticmethod
    def build_from_env() -> 'Model':
        model = os.getenv("SY_MODEL_NAME")
        if model:
            model = model.removeprefix("litellm/")
        return Model(model, os.getenv("SY_MODEL_API_KEY"))

    def get_model_params(self) -> dict:
        return {"model": self.model, "api_key": self.api_key}

if MODEL is None:
    MODEL = Model.build_from_env()

async def llm_completion(prompt):
    max_retries = 10
    messages = [{"role": "user", "content": prompt}]
    for i in range(max_retries):
        try:
            response = await acompletion(
                messages=messages,
                temperature=0,
                **MODEL.get_model_params()
            )
            return response.choices[0].message.content
        except Exception as e:
            print(e)
            if i < max_retries - 1:
                await asyncio.sleep(1)
            else:
                logging.error('Max retries reached for prompt: ' + prompt)
                return ""

async def generate_node_summary(node):
    LOGGER.info("Generating summary for node: " + node.node_id)
    prompt = f"""You are given a part of a document, your task is to generate a description of the partial document about what are main points covered in the partial document.

    Partial Document Text: {node.text}

    Directly return the description, do not include any other text.
    """
    response = await llm_completion(prompt)
    return response

async def check_similarity(node_1, node_2):
    pass
