from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Use local SQLite database for development
DATABASE_URL = "sqlite:///./local_documents.db"

# Create engine with local database
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for declarative models
Base = declarative_base()

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Initialize database
def init_db():
    """Initialize the database by creating all tables"""
    Base.metadata.create_all(bind=engine)
    print("Database initialized with local SQLite database")

# Simple pool status function (no complex pooling for SQLite)
def get_connection_pool_status():
    return {"status": "SQLite - no pooling", "database_url": DATABASE_URL}

# Simple cleanup function
def cleanup_connection_pool():
    return {"message": "SQLite - no pool cleanup needed"}

# Simple monitor class
class PoolMonitor:
    def get_history(self):
        return {"message": "SQLite - no pool monitoring"}
    
    def start_monitoring(self, interval=60):
        return "SQLite - monitoring not needed"
    
    def stop_monitoring(self):
        return "SQLite - monitoring not active"

pool_monitor = PoolMonitor() 