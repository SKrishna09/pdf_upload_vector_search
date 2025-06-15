from fastapi import APIRouter, HTTPException, UploadFile, File, status, Body, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
from datetime import datetime
import shutil
import traceback
from pydantic import BaseModel, HttpUrl
import logging
import requests
from bs4 import BeautifulSoup
import tempfile
from playwright.async_api import async_playwright
import urllib.parse

from database import get_db
from models import Document
from utils.pdf_processor import pdf_processor
from utils.qdrant_client import qdrant_client
from utils.linkedin_extractor import LinkedInExtractor
from utils.web_extractor import WebExtractor

# Configure logging
logger = logging.getLogger(__name__)

# Define Pydantic model for document response (without user info)
class DocumentResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_size: int
    content_type: str
    created_at: datetime
    vectorization_status: str
    chunks_count: int
    
    class Config:
        from_attributes = True

class UrlToPdfRequest(BaseModel):
    url: HttpUrl
    cookies: Optional[str] = None  # Optional cookies string for authentication

router = APIRouter(
    prefix="/upload",
    tags=["document upload"],
    responses={404: {"description": "Not found"}},
)

# Configure the upload directory
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "uploads", "pdfs")
os.makedirs(UPLOAD_DIR, exist_ok=True)

def initialize_qdrant():
    """Initialize Qdrant connection and collection"""
    try:
        if not qdrant_client.connect():
            return False
        if not qdrant_client.initialize_collection():
            return False
        if not qdrant_client.load_embedding_model():
            return False
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Qdrant: {str(e)}")
        return False

@router.post("/upload-pdf", status_code=status.HTTP_201_CREATED, response_model=DocumentResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a PDF document, extract text, create embeddings, and store in vector DB
    No authentication required
    """
    # Check if file is a PDF
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )
    
    try:
        # Read file content
        file_content = await file.read()
        
        # Generate a unique filename to avoid collisions
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex
        original_filename = file.filename
        
        # Sanitize the original filename by removing special characters
        clean_filename = ''.join(c for c in original_filename if c.isalnum() or c in ['.', '_', '-'])
        
        # Create the new filename format: timestamp_uuid_originalname.pdf
        new_filename = f"{timestamp}_{unique_id}_{clean_filename}"
        file_path = os.path.join(UPLOAD_DIR, new_filename)
        
        # Save the file
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
        
        # Get file size
        file_size = len(file_content)
        
        # Create document record in the database (initially with pending status)
        # No user_id needed since no authentication
        try:
            db_document = Document(
                filename=new_filename,
                original_filename=original_filename,
                file_path=file_path,
                file_size=file_size,
                content_type=file.content_type,
                user_id=None,  # No user authentication
                vectorization_status="pending"
            )
            
            logger.info(f"Created document object: {db_document.filename}")
            
            db.add(db_document)
            db.commit()
            db.refresh(db_document)
            logger.info(f"Document saved with ID: {db_document.id}")
            
            # Now process the PDF for vectorization
            try:
                # Initialize Qdrant if not already done
                if not initialize_qdrant():
                    raise Exception("Failed to initialize Qdrant")
                
                # Process PDF to extract text and create chunks
                logger.info("Starting PDF text extraction and chunking")
                chunks = pdf_processor.process_pdf_to_chunks(file_content)
                
                # Prepare documents for Qdrant insertion
                documents_for_qdrant = []
                for i, chunk in enumerate(chunks):
                    documents_for_qdrant.append({
                        "text": chunk,
                        "document_id": db_document.id,
                        "user_id": None,  # No user authentication
                        "filename": original_filename,
                        "chunk_index": i,
                        "created_at": str(db_document.created_at)
                    })
                
                # Insert into Qdrant
                logger.info(f"Inserting {len(chunks)} chunks into Qdrant")
                if qdrant_client.insert_documents(documents_for_qdrant):
                    # Update document status to completed
                    db_document.vectorization_status = "completed"
                    db_document.chunks_count = len(chunks)
                    logger.info("Vectorization completed successfully")
                else:
                    raise Exception("Failed to insert documents into Qdrant")
                
            except Exception as vectorization_error:
                # Update document status to failed
                db_document.vectorization_status = "failed"
                db_document.vectorization_error = str(vectorization_error)
                logger.error(f"Vectorization failed: {str(vectorization_error)}")
                logger.error(traceback.format_exc())
                
                # Since the requirement is to fail the entire upload if vectorization fails
                # We'll delete the uploaded file and database record
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    db.delete(db_document)
                    db.commit()
                except Exception as cleanup_error:
                    logger.error(f"Cleanup failed: {str(cleanup_error)}")
                
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"PDF processing failed: {str(vectorization_error)}"
                )
            
            # Final commit for successful vectorization
            db.commit()
            db.refresh(db_document)
            
            # Return the document response (without user information)
            return {
                "id": db_document.id,
                "filename": db_document.filename,
                "original_filename": db_document.original_filename,
                "file_size": db_document.file_size,
                "content_type": db_document.content_type or "application/pdf",
                "created_at": db_document.created_at,
                "vectorization_status": db_document.vectorization_status,
                "chunks_count": db_document.chunks_count or 0
            }
            
        except Exception as db_error:
            logger.error(f"Database error: {str(db_error)}")
            logger.error(traceback.format_exc())
            
            # Clean up the uploaded file on database error
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as cleanup_error:
                logger.error(f"File cleanup failed: {str(cleanup_error)}")
                
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(db_error)}"
            )
        
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )

@router.get("/pdf-list", response_model=List[DocumentResponse])
async def list_pdfs(db: Session = Depends(get_db)):
    """
    Get a list of all uploaded PDF documents
    No authentication required
    """
    try:
        documents = db.query(Document).all()
        
        document_responses = []
        for doc in documents:
            document_responses.append({
                "id": doc.id,
                "filename": doc.filename,
                "original_filename": doc.original_filename,
                "file_size": doc.file_size,
                "content_type": doc.content_type or "application/pdf",
                "created_at": doc.created_at,
                "vectorization_status": doc.vectorization_status or "unknown",
                "chunks_count": doc.chunks_count or 0
            })
        
        return document_responses
        
    except Exception as e:
        logger.error(f"Error fetching documents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching documents: {str(e)}"
        )

@router.get("/search")
async def search_documents(
    query: str,
    limit: int = 5,
    min_confidence: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """
    Search through uploaded documents using vector similarity
    No authentication required
    """
    try:
        # Initialize Qdrant if not already done
        if not initialize_qdrant():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Vector search service unavailable"
            )
        
        # Perform the search using the correct method
        search_results = qdrant_client.search(
            query_text=query,
            limit=limit
        )
        
        if not search_results:
            return {
                "query": query,
                "results": [],
                "total_results": 0,
                "message": "No results found"
            }
        
        # Format results
        formatted_results = []
        for result in search_results:
            try:
                # Apply confidence filter if specified
                if min_confidence and result.get('score', 0) < min_confidence:
                    continue
                
                # Get document info from database
                doc_id = result.get('metadata', {}).get('document_id')
                if doc_id:
                    document = db.query(Document).filter(Document.id == doc_id).first()
                    if document:
                        formatted_results.append({
                            "document_id": doc_id,
                            "filename": document.original_filename,
                            "chunk_index": result.get('metadata', {}).get('chunk_index', 0),
                            "text": result.get('text', ''),
                            "confidence": result.get('score', 0.0),
                            "created_at": str(document.created_at)
                        })
            except Exception as result_error:
                logger.error(f"Error processing search result: {str(result_error)}")
                continue
        
        return {
            "query": query,
            "results": formatted_results,
            "total_results": len(formatted_results),
            "search_params": {
                "limit": limit,
                "min_confidence": min_confidence
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )

@router.post("/url-to-pdf", status_code=status.HTTP_201_CREATED, response_model=DocumentResponse)
async def url_to_pdf(
    url_request: UrlToPdfRequest,
    db: Session = Depends(get_db)
):
    """
    Fetch a URL, extract main content, convert to PDF, and upload as document
    """
    try:
        # Generate a filename from the URL
        parsed_url = urllib.parse.urlparse(str(url_request.url))
        base_name = parsed_url.netloc.replace('.', '_')
        path_part = parsed_url.path.strip('/').split('/')[-1] or 'webpage'
        if not path_part.lower().endswith('.pdf'):
            path_part += '.pdf'
        generated_filename = f"{base_name}_{path_part}"

        # Use Playwright to navigate to URL and render the full page
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page()
                
                # Use appropriate extractor based on URL type
                if LinkedInExtractor.is_linkedin_url(str(url_request.url)):
                    success, extracted_text = await LinkedInExtractor.process_linkedin_url(
                        page, str(url_request.url), url_request.cookies
                    )
                else:
                    success, extracted_text = await WebExtractor.process_web_url(page, str(url_request.url))
                
                if not success:
                    logger.warning(f"Failed to extract content from {str(url_request.url)}")
                    extracted_text = ""
                
                # Generate PDF of the fully rendered page
                await page.pdf(path=tmp_pdf.name, format='A4', print_background=True)
                await browser.close()
            
            tmp_pdf.seek(0)
            
            # If we have extracted text and it's substantial, use it for vectorization
            if extracted_text and len(extracted_text) > 100:
                # Create document record directly with extracted text
                try:
                    # Read PDF content for file storage
                    with open(tmp_pdf.name, "rb") as pdf_file:
                        pdf_content = pdf_file.read()
                    
                    # Generate unique filename
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    unique_id = uuid.uuid4().hex
                    clean_filename = ''.join(c for c in generated_filename if c.isalnum() or c in ['.', '_', '-'])
                    new_filename = f"{timestamp}_{unique_id}_{clean_filename}"
                    file_path = os.path.join(UPLOAD_DIR, new_filename)
                    
                    # Save PDF file
                    with open(file_path, "wb") as buffer:
                        buffer.write(pdf_content)
                    
                    # Create document record
                    db_document = Document(
                        filename=new_filename,
                        original_filename=generated_filename,
                        file_path=file_path,
                        file_size=len(pdf_content),
                        content_type="application/pdf",
                        user_id=None,  # No user authentication
                        vectorization_status="pending"
                    )
                    
                    db.add(db_document)
                    db.commit()
                    db.refresh(db_document)
                    
                    # Process extracted text for vectorization
                    try:
                        # Initialize Qdrant if not already done
                        if not initialize_qdrant():
                            raise Exception("Failed to initialize Qdrant")
                        
                        # Create chunks from extracted text
                        from langchain_text_splitters import RecursiveCharacterTextSplitter
                        text_splitter = RecursiveCharacterTextSplitter(
                            chunk_size=1000,
                            chunk_overlap=200,
                            length_function=len,
                        )
                        chunks = text_splitter.split_text(extracted_text)
                        
                        # Prepare documents for Qdrant insertion
                        documents_for_qdrant = []
                        for i, chunk in enumerate(chunks):
                            documents_for_qdrant.append({
                                "text": chunk,
                                "document_id": db_document.id,
                                "user_id": None,  # No user authentication
                                "filename": generated_filename,
                                "chunk_index": i,
                                "created_at": str(db_document.created_at)
                            })
                        
                        # Insert into Qdrant
                        if qdrant_client.insert_documents(documents_for_qdrant):
                            db_document.vectorization_status = "completed"
                            db_document.chunks_count = len(chunks)
                        else:
                            raise Exception("Failed to insert documents into Qdrant")
                        
                    except Exception as vectorization_error:
                        db_document.vectorization_status = "failed"
                        db_document.vectorization_error = str(vectorization_error)
                        logger.error(f"Vectorization failed: {str(vectorization_error)}")
                    
                    # Final commit
                    db.commit()
                    db.refresh(db_document)
                    
                    # Return response
                    result = {
                        "id": db_document.id,
                        "filename": db_document.filename,
                        "original_filename": db_document.original_filename,
                        "file_size": db_document.file_size,
                        "content_type": db_document.content_type or "application/pdf",
                        "created_at": db_document.created_at,
                        "vectorization_status": db_document.vectorization_status,
                        "chunks_count": db_document.chunks_count
                    }
                    
                except Exception as e:
                    logger.error(f"Error processing extracted text: {str(e)}")
                    # Fallback to creating document without vectorization
                    return await create_pdf_document_without_vectorization(tmp_pdf.name, generated_filename, db, "Content extraction succeeded but vectorization failed")
            else:
                # No substantial text extracted - create document but mark vectorization as failed
                return await create_pdf_document_without_vectorization(tmp_pdf.name, generated_filename, db, "No substantial text content could be extracted from the webpage")

        os.remove(tmp_pdf.name)
        return result
    except Exception as e:
        logger.error(f"URL to PDF error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to process URL: {str(e)}")

async def create_pdf_document_without_vectorization(pdf_path: str, original_filename: str, db: Session, error_reason: str):
    """Helper function to create a document record when vectorization fails"""
    try:
        # Read PDF content
        with open(pdf_path, "rb") as pdf_file:
            pdf_content = pdf_file.read()
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex
        clean_filename = ''.join(c for c in original_filename if c.isalnum() or c in ['.', '_', '-'])
        new_filename = f"{timestamp}_{unique_id}_{clean_filename}"
        file_path = os.path.join(UPLOAD_DIR, new_filename)
        
        # Save PDF file
        with open(file_path, "wb") as buffer:
            buffer.write(pdf_content)
        
        # Create document record with failed vectorization status
        db_document = Document(
            filename=new_filename,
            original_filename=original_filename,
            file_path=file_path,
            file_size=len(pdf_content),
            content_type="application/pdf",
            user_id=None,
            vectorization_status="failed",
            vectorization_error=error_reason,
            chunks_count=0
        )
        
        db.add(db_document)
        db.commit()
        db.refresh(db_document)
        
        return {
            "id": db_document.id,
            "filename": db_document.filename,
            "original_filename": db_document.original_filename,
            "file_size": db_document.file_size,
            "content_type": db_document.content_type or "application/pdf",
            "created_at": db_document.created_at,
            "vectorization_status": db_document.vectorization_status,
            "chunks_count": db_document.chunks_count
        }
        
    except Exception as e:
        logger.error(f"Failed to create document without vectorization: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save PDF document: {str(e)}"
        ) 