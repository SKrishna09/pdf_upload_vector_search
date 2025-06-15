#!/bin/bash

echo "🚀 Document Upload API Setup Script"
echo "=================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

echo "✅ Docker found"

# Check if Qdrant is already running
if curl -s http://localhost:6333/health &> /dev/null; then
    echo "✅ Qdrant is already running"
else
    echo "🔧 Starting Qdrant vector database..."
    
    # Check if qdrant_data directory exists, create if not
    if [ ! -d "qdrant_data" ]; then
        mkdir qdrant_data
        echo "📁 Created qdrant_data directory for persistence"
    fi
    
    # Start Qdrant with persistent storage
    docker run -d --name document-upload-qdrant -p 6333:6333 -v "$(pwd)/qdrant_data:/qdrant/storage" qdrant/qdrant:latest
    
    # Wait for Qdrant to start
    echo "⏳ Waiting for Qdrant to start..."
    for i in {1..30}; do
        if curl -s http://localhost:6333/health &> /dev/null; then
            echo "✅ Qdrant is running!"
            break
        fi
        sleep 2
        echo -n "."
    done
    
    if ! curl -s http://localhost:6333/health &> /dev/null; then
        echo "❌ Failed to start Qdrant. Please check Docker logs:"
        echo "docker logs document-upload-qdrant"
        exit 1
    fi
fi

# Setup Python virtual environment
if [ ! -d "venv" ]; then
    echo "🐍 Creating Python virtual environment..."
    python3 -m venv venv
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment and install dependencies
echo "📦 Installing Python dependencies..."
source venv/bin/activate
pip install -r requirements.txt

# Initialize database
echo "🗄️ Initializing database..."
python migrations/init_database.py

echo ""
echo "🎉 Setup complete!"
echo ""
echo "To start the API:"
echo "1. source venv/bin/activate"
echo "2. python main.py"
echo ""
echo "The API will be available at: http://localhost:8001"
echo "API Documentation: http://localhost:8001/docs"
echo ""
echo "To verify Qdrant collection:"
echo "curl http://localhost:6333/collections"
echo ""
echo "To stop Qdrant later:"
echo "docker stop document-upload-qdrant" 