import argparse

from langchain_core.language_models import BaseChatModel, BaseLLM
from langchain_core.language_models.base import BaseLanguageModel

# important note: if you import these after patching, the patch won't apply!
# mitigation will be added to patch_abc in a future change
from langchain_huggingface import HuggingFaceEndpoint
from langchain_ollama import OllamaLLM
from langchain_openai import ChatOpenAI

from opentelemetry.util._patch import patch_leaf_subclasses


def parse_args():
    parser = argparse.ArgumentParser(description="LangChain model comparison")
    parser.add_argument(
        "--provider",
        choices=["ollama", "openai", "huggingface"],
        default="ollama",
        help="Choose model provider (default: ollama)",
    )
    parser.add_argument("--model", type=str, help="Specify model name")
    parser.add_argument(
        "--prompt",
        type=str,
        default="What is the capital of France?",
        help="Input prompt",
    )

    return parser.parse_args()


def chat_with_model(model: BaseLanguageModel, prompt: str) -> str:
    try:
        response = model.invoke(prompt)
        if hasattr(response, "content"):
            return response.content
        else:
            return str(response)
    except Exception as e:
        return f"Error: {str(e)}"


def create_huggingface_model(model: str = "google/flan-t5-small"):
    return HuggingFaceEndpoint(repo_id=model, temperature=0.7)


def create_openai_model(model: str = "gpt-3.5-turbo"):
    return ChatOpenAI(model=model, temperature=0.7)


def create_ollama_model(model: str = "llama2"):
    return OllamaLLM(model=model, temperature=0.7)


def patch_llm():
    def my_wrapper(orig_fcn):
        def wrapped_fcn(self, *args, **kwargs):
            print("wrapper starting")
            print(f"Arguments: {args}")
            print(f"Keyword arguments: {kwargs}")
            return orig_fcn(self, *args, **kwargs)

        return wrapped_fcn

    # Patch traditional LLM models (Ollama, HuggingFace, etc.)
    patch_leaf_subclasses(BaseLLM, "_generate", my_wrapper)

    # Patch chat models (OpenAI, Anthropic, Google, etc.)
    patch_leaf_subclasses(BaseChatModel, "_generate", my_wrapper)


def main():
    args = parse_args()

    patch_llm()

    if args.provider == "ollama":
        model = create_ollama_model(args.model or "llama2")
    elif args.provider == "openai":
        model = create_openai_model(args.model or "gpt-3.5-turbo")
    elif args.provider == "huggingface":
        model = create_huggingface_model(args.model or "google/flan-t5-small")
    else:
        raise ValueError(f"Unsupported provider: {args.provider}")

    response = chat_with_model(model, args.prompt)
    print(f"{args.provider.title()} Response: {response}")


if __name__ == "__main__":
    main()
