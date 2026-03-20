"""
LLM provider factory.

Supports providers selected via DEFAULT_LLM_PROVIDER env var:
  - "groq"      → Groq (Llama, Mixtral — very fast, free tier)
  - "nim"       → NVIDIA NIM cloud API (OpenAI-compatible)
  - "openai"    → OpenAI API
  - "anthropic" → Anthropic API

Embeddings provider is selected separately via EMBEDDING_PROVIDER:
  - "nim"       → nvidia/nv-embedqa-e5-v5
  - "openai"    → text-embedding-ada-002
"""

import structlog
from functools import lru_cache
from typing import Union

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings

from ..config import settings

logger = structlog.get_logger()


def get_llm(
    temperature: float = 0.1,
    max_tokens: int = 4096,
) -> BaseChatModel:
    """
    Return a LangChain chat model for the configured provider.

    Provider is controlled by DEFAULT_LLM_PROVIDER env var.
    Falls back to OpenAI if the preferred provider has no API key set.
    """
    provider = settings.default_llm_provider.lower()

    if provider == "groq":
        if not settings.groq_api_key:
            raise ValueError(
                "DEFAULT_LLM_PROVIDER=groq but GROQ_API_KEY is not set. "
                "Add GROQ_API_KEY to your .env file."
            )
        logger.info("Using Groq provider", model=settings.default_model)
        return ChatOpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=settings.groq_api_key,
            model=settings.default_model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    if provider == "nim":
        if not settings.nvidia_api_key:
            raise ValueError(
                "DEFAULT_LLM_PROVIDER=nim but NVIDIA_API_KEY is not set. "
                "Add NVIDIA_API_KEY to your .env file."
            )
        logger.info("Using NVIDIA NIM provider", model=settings.nim_chat_model)
        return ChatOpenAI(
            base_url=settings.nim_base_url,
            api_key=settings.nvidia_api_key,
            model=settings.nim_chat_model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    if provider == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError(
                "DEFAULT_LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set. "
                "Add ANTHROPIC_API_KEY to your .env file."
            )
        logger.info("Using Anthropic provider", model=settings.default_model)
        return ChatAnthropic(
            api_key=settings.anthropic_api_key,
            model=settings.default_model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    # OpenAI
    if not settings.openai_api_key:
        raise ValueError(
            "DEFAULT_LLM_PROVIDER=openai but OPENAI_API_KEY is not set. "
            "Add OPENAI_API_KEY to your .env file, or switch to nim/anthropic."
        )
    logger.info("Using OpenAI provider", model=settings.default_model)
    return ChatOpenAI(
        api_key=settings.openai_api_key,
        model=settings.default_model,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def get_embeddings() -> Embeddings:
    """
    Return a LangChain embeddings model for the configured provider.

    Provider is controlled by EMBEDDING_PROVIDER env var.
    """
    provider = settings.embedding_provider.lower()

    if provider == "nim":
        if not settings.nvidia_api_key:
            raise ValueError(
                "EMBEDDING_PROVIDER=nim but NVIDIA_API_KEY is not set. "
                "Add NVIDIA_API_KEY to your .env file."
            )
        logger.info("Using NVIDIA NIM embeddings", model=settings.nim_embedding_model)
        return OpenAIEmbeddings(
            base_url=settings.nim_base_url,
            api_key=settings.nvidia_api_key,
            model=settings.nim_embedding_model,
        )

    # OpenAI
    if not settings.openai_api_key:
        raise ValueError(
            "EMBEDDING_PROVIDER=openai but OPENAI_API_KEY is not set. "
            "Add OPENAI_API_KEY to your .env file, or switch to EMBEDDING_PROVIDER=nim."
        )
    logger.info("Using OpenAI embeddings", model="text-embedding-ada-002")
    return OpenAIEmbeddings(
        api_key=settings.openai_api_key,
        model="text-embedding-ada-002",
    )
