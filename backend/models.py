from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import datetime
from enum import Enum

# Optional user model for future authentication
class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(SQLEnum(UserRole), default=UserRole.USER)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    
    # Relationships
    documents = relationship("Document", back_populates="user")
    search_queries = relationship("SearchQuery", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"

# Main document model (currently used in the app)
class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Optional for now
    filename = Column(String, nullable=False)
    original_filename = Column(String)
    file_path = Column(String)
    file_size = Column(Integer)
    content_type = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    vectorization_status = Column(String, default="pending")  # pending, completed, failed
    vectorization_error = Column(Text, nullable=True)
    chunks_count = Column(Integer, default=0)
    
    # Relationships
    user = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Document(id={self.id}, filename='{self.filename}', status={self.vectorization_status})>"

# Track individual text chunks
class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    text_content = Column(Text, nullable=False)
    vector_id = Column(String, nullable=True)  # ID in Qdrant
    start_page = Column(Integer, nullable=True)
    end_page = Column(Integer, nullable=True)
    character_count = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    document = relationship("Document", back_populates="chunks")
    
    def __repr__(self):
        return f"<DocumentChunk(id={self.id}, document_id={self.document_id}, chunk_index={self.chunk_index})>"

# Track search queries for analytics
class SearchQuery(Base):
    __tablename__ = "search_queries"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Optional for anonymous searches
    query_text = Column(Text, nullable=False)
    results_count = Column(Integer, default=0)
    search_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    response_time_ms = Column(Integer, nullable=True)
    min_score = Column(Float, nullable=True)
    max_score = Column(Float, nullable=True)
    filters_applied = Column(Text, nullable=True)  # JSON string
    
    # Relationships
    user = relationship("User", back_populates="search_queries")
    
    def __repr__(self):
        return f"<SearchQuery(id={self.id}, query_text='{self.query_text[:50]}...', results_count={self.results_count})>"

# Manage vector collections
class VectorCollectionStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"

class VectorCollection(Base):
    __tablename__ = "vector_collections"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)
    embedding_model = Column(String, nullable=False)
    vector_dimension = Column(Integer, nullable=False)
    distance_metric = Column(String, default="cosine")
    status = Column(SQLEnum(VectorCollectionStatus), default=VectorCollectionStatus.ACTIVE)
    document_count = Column(Integer, default=0)
    chunk_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    creator = relationship("User")
    
    def __repr__(self):
        return f"<VectorCollection(id={self.id}, name='{self.name}', status={self.status})>"




















