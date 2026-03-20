"""
Synthesis agent — uses the configured LLM provider (OpenAI, Anthropic, or NIM)
to synthesise retrieved documents into a coherent summary.
"""

import structlog
from typing import Dict, Any

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from .base import BaseAgent
from ..orchestration.state import WorkflowState
from ..llm.providers import get_llm

logger = structlog.get_logger()


class SynthesisAgent(BaseAgent):
    """Agent specialised in synthesising information from multiple sources"""

    def __init__(self):
        super().__init__(
            name="synthesis",
            description="Synthesises and combines information from multiple sources into coherent insights",
        )
        self._llm = None  # lazy-initialised so tests can run without API keys

    @property
    def llm(self):
        if self._llm is None:
            self._llm = get_llm(temperature=0.2)
        return self._llm

    async def execute(self, state: WorkflowState, **kwargs: Any) -> WorkflowState:
        """Execute synthesis tasks and update the workflow state"""
        self.logger.info("Starting synthesis phase")

        try:
            retrieved_documents = state.get("retrieved_documents", [])

            # Build conversation history prefix so the LLM has context from past sessions
            history_messages = []
            for turn in state.get("conversation_history", []):
                if turn.get("role") == "user":
                    history_messages.append(HumanMessage(content=turn["content"]))
                elif turn.get("role") == "assistant":
                    history_messages.append(AIMessage(content=turn["content"]))

            if not retrieved_documents:
                self.logger.info("No documents in knowledge base — answering from LLM knowledge")
                messages = [
                    SystemMessage(content=(
                        "You are a knowledgeable assistant. "
                        "Answer the user's question clearly and accurately using your own knowledge. "
                        "Be concise but thorough. Use bullet points for key facts."
                    )),
                    *history_messages,
                    HumanMessage(content=state["user_request"]),
                ]
                response = await self.llm.ainvoke(messages)
                summary = response.content
                synthesis_result = {
                    "summary": summary,
                    "sources_used": 0,
                    "confidence_score": 0.75,
                    "key_points": [
                        line.strip("- ").strip()
                        for line in summary.split("\n")
                        if line.strip().startswith("-")
                    ][:5] or ["See summary above"],
                    "note": "Answered from model knowledge — no documents in knowledge base",
                }
                state["intermediate_results"]["synthesis"] = synthesis_result
                self.logger.info("Synthesis completed from LLM knowledge")
            else:
                # Build context from top documents (cap at ~6000 chars to stay within context)
                context_parts = []
                char_budget = 6000
                for i, doc in enumerate(retrieved_documents):
                    snippet = doc["text"][:char_budget // len(retrieved_documents)]
                    source = doc.get("metadata", {}).get("source", f"source_{i+1}")
                    context_parts.append(f"[{source}]\n{snippet}")

                context = "\n\n".join(context_parts)
                user_request = state["user_request"]

                messages = [
                    SystemMessage(content=(
                        "You are an expert research synthesiser. "
                        "Given a user question and a set of retrieved source documents, "
                        "produce a clear, accurate, well-structured summary. "
                        "Cite which sources support each key point. "
                        "Be concise but comprehensive."
                    )),
                    *history_messages,
                    HumanMessage(content=(
                        f"User question: {user_request}\n\n"
                        f"Retrieved documents:\n{context}\n\n"
                        "Please synthesise the above into a clear summary with key points."
                    )),
                ]

                response = await self.llm.ainvoke(messages)
                summary = response.content

                synthesis_result = {
                    "summary": summary,
                    "sources_used": len(retrieved_documents),
                    "confidence_score": 0.85,
                    "key_points": [
                        line.strip("- ").strip()
                        for line in summary.split("\n")
                        if line.strip().startswith("-")
                    ][:5] or ["See summary above"],
                }

                state["intermediate_results"]["synthesis"] = synthesis_result
                self.logger.info("Synthesis completed", sources_used=len(retrieved_documents))

            state["completed_steps"].append("synthesis")
            state["current_step"] = "synthesis"
            state["history"].append(
                f"Synthesis agent processed {len(retrieved_documents)} documents"
            )

        except Exception as e:
            state["errors"].append({"agent": self.name, "error": str(e), "step": "synthesis"})
            state["status"] = "failed"
            self.logger.error("Synthesis agent failed", error=str(e), exc_info=True)

        return state
