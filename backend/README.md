# Document Upload & Vector Search API

A FastAPI application for uploading PDF documents, converting URLs to PDFs, and performing semantic vector search on document content. Features include LinkedIn profile processing with authentication and comprehensive document management.

## ✨ Features

- **🔓 No Authentication Required** - Simple to use without user management
- **📄 PDF Upload** - Upload PDF files with automatic text extraction and vectorization
- **🌐 URL to PDF** - Convert web pages to PDF documents with content extraction
- **🔍 Vector Search** - Semantic similarity search through document content using embeddings
- **📋 Document Management** - List and manage uploaded documents with status tracking
- **🔗 LinkedIn Integration** - Process LinkedIn profiles with cookie-based authentication
- **🎯 Smart Content Extraction** - Handles both regular web pages and LinkedIn profiles
- **📊 Status Tracking** - Monitor vectorization status and chunk counts

## 🛠 Prerequisites

Before starting, ensure you have:
- **Python 3.12.10** (specific version required for ML dependencies)
- **Docker** (for Qdrant vector database)
- **Git** (for cloning the repository)

## 🚀 Quick Start

### Option 1: Automated Setup (Recommended)

```bash
# Make setup script executable and run
chmod +x setup.sh
./setup.sh
```

This script will:
- ✅ Check for Docker installation
- ✅ Start Qdrant vector database
- ✅ Create Python virtual environment with correct Python version
- ✅ Install all dependencies including ML libraries
- ✅ Initialize the SQLite database
- ✅ Install Playwright browsers for web scraping

### Option 2: Manual Setup

#### 1. Start Qdrant Vector Database

```bash
# Pull and run Qdrant (required for vector search)
docker run -p 6333:6333 qdrant/qdrant:latest

# Alternative: Run with persistent storage
mkdir qdrant_data
docker run -p 6333:6333 -v $(pwd)/qdrant_data:/qdrant/storage qdrant/qdrant:latest
```

**Verify Qdrant is running:**
```bash
curl http://localhost:6333/collections
# Should return: {"result":{"collections":[]}}
```

#### 2. Setup Python Environment

```bash
# Create virtual environment with Python 3.12.10
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Verify Python version
python --version  # Should show Python 3.12.10
```

#### 3. Install Dependencies

```bash
# Install all Python dependencies
pip install -r requirements.txt

# Install Playwright browsers for web scraping
playwright install
```

#### 4. Initialize Database

```bash
# Create SQLite database and tables
python migrations/init_database.py
```

#### 5. Start the API Server

```bash
# Start on default port 8001
python main.py

# Or specify a different port
python main.py --port 8002
```

**🎉 API Available at:** `http://localhost:8001`

**📚 Interactive Documentation:** `http://localhost:8001/docs`

## 🔧 Environment Variables

Create a `.env` file to customize settings:

```env
# Qdrant Configuration
QDRANT_HOST=localhost
QDRANT_PORT=6333
COLLECTION_NAME=KBCollection_LinkedIn

# Embedding Model Configuration
EMBEDDING_MODEL=all-mpnet-base-v2

# Optional: Disable tokenizer warnings
TOKENIZERS_PARALLELISM=false
```

## 📡 API Endpoints

### Core Endpoints
- **GET /** - Welcome message and API info
- **GET /health** - Health check endpoint
- **GET /docs** - Interactive API documentation (Swagger UI)

### Document Operations
- **POST /api/documents/upload/upload-pdf** - Upload PDF files
- **POST /api/documents/upload/url-to-pdf** - Convert URLs to PDF
- **GET /api/documents/upload/pdf-list** - List all uploaded documents
- **GET /api/documents/upload/search** - Search through documents (⚠️ **Updated to GET**)

## 💡 Usage Examples

### 📄 Upload a PDF File

```bash
curl -X POST "http://localhost:8001/api/documents/upload/upload-pdf" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your-document.pdf"
```

**Response:**
```json
{
  "id": 1,
  "filename": "20250615_123456_abc123_your-document.pdf",
  "original_filename": "your-document.pdf",
  "file_size": 1234567,
  "content_type": "application/pdf",
  "created_at": "2025-06-15T12:34:56",
  "vectorization_status": "completed",
  "chunks_count": 42
}
```

### 🌐 Convert URL to PDF

```bash
# Regular website
curl -X POST "http://localhost:8001/api/documents/upload/url-to-pdf" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'

# LinkedIn profile with authentication
curl -X POST "http://localhost:8001/api/documents/upload/url-to-pdf" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.linkedin.com/in/username/",
    "cookies": "li_at=YOUR_LINKEDIN_COOKIE; JSESSIONID=YOUR_SESSION_ID"
  }'
```

### 🔍 Search Documents (Updated!)

```bash
# Basic search
curl -X GET "http://localhost:8001/api/documents/upload/search?query=machine%20learning&limit=5"

# Search with confidence filtering
curl -X GET "http://localhost:8001/api/documents/upload/search?query=artificial%20intelligence&limit=3&min_confidence=0.6"
```

**Search Response:**
```json
{
  "query": "machine learning",
  "results": [
    {
      "document_id": 1,
      "filename": "ml-paper.pdf",
      "chunk_index": 5,
      "text": "Machine learning is a subset of artificial intelligence...",
      "confidence": 0.85,
      "created_at": "2025-06-15T12:34:56"
    }
  ],
  "total_results": 1,
  "search_params": {
    "limit": 5,
    "min_confidence": null
  }
}
```

### 📋 List All Documents

```bash
curl -X GET "http://localhost:8001/api/documents/upload/pdf-list"
```

## 🔗 LinkedIn Integration

### Getting LinkedIn Cookies

1. **Login to LinkedIn** in your browser
2. **Open Developer Tools** (F12)
3. **Go to Application/Storage tab**
4. **Find Cookies** for linkedin.com
5. **Copy the values** for:
   - `li_at` (authentication token)
   - `JSESSIONID` (session ID)

### Using LinkedIn Cookies

```bash
curl -X POST "http://localhost:8001/api/documents/upload/url-to-pdf" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.linkedin.com/in/profile-name/",
    "cookies": "li_at=AQEDAQNs6csCIHu4AAABl3BHfUoAAAGXlFQBSlYAsXe7W6sVh0Ij6zLVRAYFbkqhkTHFDGegAMI2ftNPa1Tjy1CaCAKC6zzq_9v1wajKQgiAXWey0_DPrVE_7J_kzsqMBlib23lhEEjr0LNGcjWh2nu2; JSESSIONID=ajax:8559594181470113726"
  }'
```

## 🔧 Troubleshooting

### Qdrant Issues

```bash
# Check if Qdrant is running
curl http://localhost:6333/health
# Expected: {"title":"qdrant - vector search engine","version":"1.x.x"}

# Check Docker container
docker ps | grep qdrant

# View Qdrant logs
docker logs $(docker ps -q --filter ancestor=qdrant/qdrant)

# Restart Qdrant if needed
docker restart $(docker ps -q --filter ancestor=qdrant/qdrant)
```

### Python Environment Issues

```bash
# Check Python version (must be 3.12.10)
python --version

# Check if virtual environment is activated
which python  # Should point to ./venv/bin/python

# Reinstall dependencies if needed
pip install --upgrade -r requirements.txt

# Install missing Playwright browsers
playwright install
```

### Database Issues

```bash
# Reinitialize database if corrupted
rm local_documents.db
python migrations/init_database.py
```

### Search Not Working

```bash
# Check if documents have successful vectorization
curl http://localhost:8001/api/documents/upload/pdf-list

# Verify Qdrant collection exists
curl http://localhost:6333/collections/KBCollection_LinkedIn

# Check collection point count
curl http://localhost:6333/collections/KBCollection_LinkedIn/points/count
```

### Common Error Solutions

| Error | Solution |
|-------|----------|
| `Address already in use` | Use different port: `python main.py --port 8002` |
| `No text could be extracted` | PDF might be image-based or corrupted |
| `net::ERR_TOO_MANY_REDIRECTS` | LinkedIn cookies expired, get fresh ones |
| `Collection not found` | Upload a document first to create collection |
| `numpy version conflict` | Downgrade numpy: `pip install "numpy<2.0"` |

## 📁 Project Structure

```
├── main.py                     # FastAPI application entry point
├── database.py                 # SQLAlchemy database configuration
├── models.py                   # Database models (Document)
├── requirements.txt            # Python dependencies
├── setup.sh                    # Automated setup script
├── .env                        # Environment variables (create this)
├── migrations/
│   └── init_database.py       # Database initialization script
├── routers/
│   └── document.py            # Document upload/search API routes
├── utils/                      # Utility modules
│   ├── qdrant_client.py       # Qdrant vector database client
│   ├── pdf_processor.py       # PDF text extraction and chunking
│   ├── linkedin_extractor.py  # LinkedIn-specific content extraction
│   ├── web_extractor.py       # General web content extraction
│   └── hybrid_search.py       # Hybrid search functionality
├── uploads/
│   └── pdfs/                  # Uploaded PDF file storage
└── local_documents.db          # SQLite database file
```

## 🧪 Testing the System

### 1. Test PDF Upload
```bash
# Upload a test PDF
curl -X POST "http://localhost:8001/api/documents/upload/upload-pdf" \
  -F "file=@test.pdf"
```

### 2. Test URL to PDF
```bash
# Test with Wikipedia (no auth needed)
curl -X POST "http://localhost:8001/api/documents/upload/url-to-pdf" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://en.wikipedia.org/wiki/Machine_learning"}'
```

### 3. Test Search
```bash
# Search for content
curl -X GET "http://localhost:8001/api/documents/upload/search?query=test&limit=3"
```

### 4. Verify Data
```bash
# Check document list
curl -X GET "http://localhost:8001/api/documents/upload/pdf-list"

# Check Qdrant collection
curl http://localhost:6333/collections/KBCollection_LinkedIn/points/count
```

## 🔄 System Status Indicators

### Vectorization Status
- **`pending`** - Document uploaded, vectorization in progress
- **`completed`** - Successfully vectorized and searchable
- **`failed`** - Vectorization failed (PDF saved but not searchable)

### Document Processing Flow
1. **Upload/URL Processing** → PDF saved to filesystem
2. **Text Extraction** → Extract text from PDF
3. **Chunking** → Split text into searchable chunks
4. **Vectorization** → Generate embeddings using sentence-transformers
5. **Storage** → Store vectors in Qdrant for search

## 🚀 Production Considerations

- **Qdrant Persistence**: Use volume mapping for data persistence
- **File Storage**: Consider cloud storage for uploaded files
- **Environment Variables**: Use proper secrets management
- **Monitoring**: Add logging and health checks
- **Rate Limiting**: Implement API rate limiting
- **Authentication**: Add proper user authentication if needed

## 📚 Dependencies

### Core Framework
- **FastAPI** - Modern web framework for APIs
- **SQLAlchemy** - Database ORM
- **Pydantic** - Data validation

### Vector Search & ML
- **Qdrant** - Vector database for semantic search
- **sentence-transformers** - Text embedding models
- **torch** - PyTorch for ML models

### Document Processing
- **PyPDF2** - PDF text extraction
- **langchain-text-splitters** - Text chunking
- **Playwright** - Web scraping and PDF generation
- **BeautifulSoup4** - HTML parsing

### Utilities
- **python-multipart** - File upload handling
- **httpx** - HTTP client for API calls

---

## 🎯 Quick Verification Checklist

After setup, verify everything works:

- [ ] ✅ Qdrant running on port 6333
- [ ] ✅ API server running on port 8001
- [ ] ✅ Can access `/docs` endpoint
- [ ] ✅ PDF upload works and shows `completed` status
- [ ] ✅ Search returns relevant results
- [ ] ✅ URL-to-PDF works for regular websites
- [ ] ✅ LinkedIn processing works with cookies

**🎉 You're ready to start using the Document Upload & Vector Search API!** 