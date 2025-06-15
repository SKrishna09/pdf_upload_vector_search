from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Float, MetaData, Table, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
import os
from dotenv import load_dotenv
import datetime

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = "sqlite:///./local_documents.db"

# Create engine
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create metadata instance
metadata = MetaData()

def run_migrations():
    """Initialize database with complete documents table"""
    try:
        # Define the complete documents table with all fields
        documents = Table(
            'documents',
            metadata,
            Column('id', Integer, primary_key=True, index=True),
            Column('user_id', Integer, nullable=True),  # Made nullable since no auth
            Column('filename', String, nullable=False),
            Column('original_filename', String),
            Column('file_path', String),
            Column('file_size', Integer),
            Column('content_type', String),
            Column('created_at', DateTime, server_default=func.now(), nullable=False),
            # Vectorization fields
            Column('vectorization_status', String, default="pending"),  # pending, completed, failed
            Column('vectorization_error', Text, nullable=True),  # Store error details if vectorization fails
            Column('chunks_count', Integer, default=0),  # Number of chunks created
        )
        
        # Create the table
        metadata.create_all(engine, tables=[documents], checkfirst=True)
        
        print("Documents table created successfully with all fields")
        return True
        
    except Exception as e:
        print(f"Migration failed: {str(e)}")
        raise

if __name__ == "__main__":
    run_migrations() 