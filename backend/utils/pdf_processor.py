import PyPDF2
from langchain_text_splitters import CharacterTextSplitter
from langchain_text_splitters import RecursiveCharacterTextSplitter
import logging
from typing import List, Dict, Any
import io
import re

logger = logging.getLogger(__name__)

class PDFProcessor:
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,  # Slightly smaller for better context
            chunk_overlap=150,  # More overlap for better continuity
            separators=["\n\n", "\n", ". ", "? ", "! ", " ", ""]
        )
    
    def extract_text_from_pdf(self, pdf_content: bytes) -> str:
        """Extract text from PDF content"""
        try:
            pdf_file = io.BytesIO(pdf_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text = ""
            for page_num, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text += f"\n--- Page {page_num + 1} ---\n"
                    text += page_text
            
            if not text.strip():
                raise Exception("No text could be extracted from the PDF")
            
            logger.info(f"Extracted {len(text)} characters from PDF")
            return text.strip()
            
        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {str(e)}")
            raise
    
    def chunk_text(self, text: str) -> List[str]:
        """Split text into chunks with better boundaries"""
        try:
            # Clean the text first
            text = self.clean_text(text)

            chunks = self.text_splitter.split_text(text)
            logger.info(f"Split text into {len(chunks)} chunks")
            return chunks
        except Exception as e:
            logger.error(f"Failed to chunk text: {str(e)}")
            raise

    def clean_text(self, text: str) -> str:
        """Clean extracted text for better processing"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Fix common PDF extraction issues
        text = text.replace('- ', '')  # Remove hyphen
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)  # Add space between words
        
        return text.strip()    
    
    def process_pdf_to_chunks(self, pdf_content: bytes) -> List[str]:
        """Process PDF content and return text chunks"""
        try:
            # Extract text
            text = self.extract_text_from_pdf(pdf_content)
            
            # Split into chunks
            chunks = self.chunk_text(text)
            
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to process PDF: {str(e)}")
            raise

# Global instance
pdf_processor = PDFProcessor() 