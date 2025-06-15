from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from qdrant_client.models import Filter, FieldCondition, MatchValue
import os
import logging
from typing import List, Dict, Any, Optional
import uuid

from .hybrid_search import hybrid_search_engine

logger = logging.getLogger(__name__)

class QdrantVectorClient:
    def __init__(self):
        self.client = None
        self.collection_name = None
        self.embedding_model = None
        
    def connect(self) -> bool:
        """Initialize connection to Qdrant database"""
        try:
            # Check if we should connect to remote Qdrant or use local
            qdrant_host = os.getenv('QDRANT_HOST', 'localhost')
            qdrant_port = int(os.getenv('QDRANT_PORT', 6333))
            
            # Always connect to server instead of local storage
            self.client = QdrantClient(host=qdrant_host, port=qdrant_port)
            logger.info(f"Successfully connected to Qdrant server at {qdrant_host}:{qdrant_port}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {str(e)}")
            return False
    
    def load_embedding_model(self) -> bool:
        """Load the embedding model"""
        try:
            from sentence_transformers import SentenceTransformer
            model_name = os.getenv('EMBEDDING_MODEL', 'all-mpnet-base-v2')
            self.embedding_model = SentenceTransformer(model_name)
            logger.info(f"Successfully loaded embedding model: {model_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to load embedding model: {str(e)}")
            return False
    
    def initialize_collection(self) -> bool:
        """Initialize or get the collection"""
        try:
            self.collection_name = os.getenv('COLLECTION_NAME', 'KBCollection_LinkedIn')
            
            # Check if collection exists
            collections = self.client.get_collections().collections
            collection_exists = any(collection.name == self.collection_name for collection in collections)
            
            if not collection_exists:
                # Create collection with 768-dimensional vectors (for all-mpnet-base-v2)
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=768, distance=Distance.COSINE),
                )
                logger.info(f"Created new collection: {self.collection_name}")
            else:
                logger.info(f"Using existing collection: {self.collection_name}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to initialize collection: {str(e)}")
            return False
    
    def insert_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """Insert documents into the collection"""
        try:
            if not self.client or not self.embedding_model:
                raise Exception("Client or embedding model not initialized")
            
            # Prepare points for insertion
            points = []
            
            for i, doc in enumerate(documents):
                text = doc.get('text', '')
                
                # Generate embedding
                embedding = self.embedding_model.encode(text).tolist()
                
                # Create point with metadata
                point = PointStruct(
                    id=str(uuid.uuid4()),  # Generate unique ID
                    vector=embedding,
                    payload={
                        'text': text,
                        'document_id': doc.get('document_id'),
                        'user_id': doc.get('user_id'),
                        'filename': doc.get('filename'),
                        'chunk_index': doc.get('chunk_index', i)
                    }
                )
                points.append(point)
            
            # Insert points into collection
            logger.info(f"Inserting {len(points)} points into Qdrant")
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            logger.info(f"Successfully inserted {len(documents)} documents")
            return True
            
        except Exception as e:
            logger.error(f"Failed to insert documents: {str(e)}")
            return False
    
    def search(self, query_text: str, limit: int = 5, filter_dict: Optional[Dict] = None) -> List[Dict]:
        """Search for similar documents"""
        try:
            if not self.client or not self.embedding_model:
                raise Exception("Client or embedding model not initialized")
            
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query_text).tolist()
            
            # Prepare filter if provided
            query_filter = None
            if filter_dict:
                conditions = []
                for key, value in filter_dict.items():
                    conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
                if conditions:
                    query_filter = Filter(must=conditions)
            
            # Perform search
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=query_filter,
                limit=limit,
                with_payload=True
            )
            
            # Format results
            results = []
            for scored_point in search_result:
                results.append({
                    'id': str(scored_point.id),
                    'score': scored_point.score,
                    'text': scored_point.payload.get('text', ''),
                    'metadata': {
                        'document_id': scored_point.payload.get('document_id'),
                        'user_id': scored_point.payload.get('user_id'),
                        'filename': scored_point.payload.get('filename'),
                        'chunk_index': scored_point.payload.get('chunk_index')
                    }
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to search: {str(e)}")
            return []
    
    def hybrid_search(self, query_text: str, limit: int = 5, filter_dict: Optional[Dict] = None) -> List[Dict]:
        """Hybrid search combining semantic similarity with keyword matching"""
        return hybrid_search_engine.search(
            query_text=query_text,
            semantic_search_func=self.search,
            limit=limit,
            filter_dict=filter_dict
        )
    
    def get_collection_info(self) -> Dict:
        """Get collection information"""
        try:
            if not self.client or not self.collection_name:
                return {}
            
            collection_info = self.client.get_collection(self.collection_name)
            return {
                'name': collection_info.config.params.vectors.size,
                'vectors_count': collection_info.vectors_count,
                'points_count': collection_info.points_count,
                'status': collection_info.status
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {str(e)}")
            return {}

# Create a global instance
qdrant_client = QdrantVectorClient() 