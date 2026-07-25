"""
Central place that decides which LLM/embedding provider to use.

Every agent should import get_llm() / get_embeddings() from here instead of
instantiating ChatOpenAI / ChatGroq / OpenAIEmbeddings / HuggingFaceEmbeddings
directly. That way switching providers is a single env var change
(LLM_PROVIDER=openai or LLM_PROVIDER=groq) instead of a code edit in five files.
"""

import logging
import os

from config.settings import settings

logger = logging.getLogger(__name__)

# transformers auto-imports TensorFlow if it's installed, even though
# sentence-transformers only needs the PyTorch backend here. Force it off so
# a broken/unrelated TF install can't break local embeddings.
os.environ.setdefault("USE_TF", "0")


def get_llm(temperature: float = 0):
    """Returns a chat model instance for whichever provider is configured."""
    if settings.llm_provider == "openai":
        from langchain_openai import ChatOpenAI

        logger.info(f"Using OpenAI chat model: {settings.openai_chat_model}")
        return ChatOpenAI(model=settings.openai_chat_model, temperature=temperature)

    if settings.llm_provider == "groq":
        from langchain_groq import ChatGroq

        logger.info(f"Using Groq chat model: {settings.groq_chat_model}")
        return ChatGroq(
            model=settings.groq_chat_model,
            temperature=temperature,
            api_key=settings.groq_api_key,
        )

    raise ValueError(
        f"Unknown LLM_PROVIDER '{settings.llm_provider}'. Use 'openai' or 'groq'."
    )


def get_embeddings():
    """Returns an embeddings instance for whichever provider is configured."""
    if settings.llm_provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        logger.info(f"Using OpenAI embeddings: {settings.openai_embedding_model}")
        return OpenAIEmbeddings(model=settings.openai_embedding_model)

    if settings.llm_provider == "groq":
        # Groq doesn't serve embedding models, so this branch always uses a
        # local HuggingFace model — free, no rate limit, runs on CPU.
        from langchain_huggingface import HuggingFaceEmbeddings

        logger.info(f"Using local embeddings: {settings.local_embedding_model}")
        return HuggingFaceEmbeddings(model_name=settings.local_embedding_model)

    raise ValueError(
        f"Unknown LLM_PROVIDER '{settings.llm_provider}'. Use 'openai' or 'groq'."
    )
