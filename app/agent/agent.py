from pathlib import Path
from agno.agent import Agent
from agno.models.azure import AzureOpenAI  # Adapter oficial de Agno
from app.core.settings import get_settings

PROMPT_PATH = Path(__file__).parent / "prompt.md"
def load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")

def build_agent() -> Agent:
    s = get_settings()
    model = AzureOpenAI(
        id=s.azure_openai_deployment,              # Nombre del deployment
        api_key=s.azure_openai_api_key,
        api_version=s.azure_openai_api_version,
        azure_endpoint=s.azure_openai_endpoint,
        azure_deployment=s.azure_openai_deployment,
        temperature=0.2,
        max_tokens=800,
    )
    return Agent(name="azure-agno-agent", model=model, instructions=load_prompt())

_agent = None
def get_agent() -> Agent:
    global _agent
    if _agent is None:
        _agent = build_agent()
    return _agent
