"""
Retrieval-Augmented Generation (RAG) system for knowledge retrieval.
"""

import structlog
from typing import List, Dict, Any, Optional
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType
from langchain_community.vectorstores import Milvus
from langchain_openai import OpenAIEmbeddings

from ..config import settings

logger = structlog.get_logger()

class RAGSystem:
    """Manages the RAG pipelines and knowledge base"""

    def __init__(self):
        self.milvus_host = settings.milvus_host
        self.milvus_port = settings.milvus_port
        self.collection_name = "artist_knowledge_base"
        self.collection = None
        self.embeddings = None

    async def initialize(self):
        """Initializes the RAG system and connects to the vector database"""
        logger.info("Initializing RAG system...")
        try:
            connections.connect(host=self.milvus_host, port=self.milvus_port)
            self.embeddings = OpenAIEmbeddings(openai_api_key=settings.openai_api_key)
            self.create_collection_if_not_exists()
            logger.info("RAG system initialized successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Milvus: {e}")

    async def shutdown(self):
        """Shuts down the RAG system and disconnects from the vector database"""
        logger.info("Shutting down RAG system...")
        connections.disconnect()

    def create_collection_if_not_exists(self):
        """Creates the Milvus collection if it doesn't already exist"""
        if self.collection_name not in connections.list_collections():
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1536),
                FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="metadata", dtype=DataType.JSON)
            ]
            schema = CollectionSchema(fields, "Knowledge base for ARTIST")
            self.collection = Collection(self.collection_name, schema)
            logger.info(f"Created Milvus collection: {self.collection_name}")
        else:
            self.collection = Collection(self.collection_name)
            logger.info(f"Using existing Milvus collection: {self.collection_name}")

    async def add_documents(self, documents: List[Dict[str, Any]]):
        """Adds documents to the knowledge base"""
        texts = [doc["text"] for doc in documents]
        metadatas = [doc["metadata"] for doc in documents]
        
        vector_store = Milvus(self.embeddings, connection_args={"host": self.milvus_host, "port": self.milvus_port}, collection_name=self.collection_name)
        await vector_store.aadd_texts(texts, metadatas)
        logger.info(f"Added {len(documents)} documents to the knowledge base")

    async def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Searches the knowledge base for relevant documents"""
        vector_store = Milvus(self.embeddings, connection_args={"host": self.milvus_host, "port": self.milvus_port}, collection_name=self.collection_name)
        results = await vector_store.asimilarity_search_with_score(query, k=k)
        
        return [
            {
                "text": doc.page_content,
                "metadata": doc.metadata,
                "score": score
            }
            for doc, score in results
        ]

    def health_check(self) -> bool:
        """Health check for the RAG system"""
        try:
            connections.get_connection_addr('default')
            return True
        except Exception:
            return False

