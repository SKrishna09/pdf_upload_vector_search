#!/usr/bin/env python3
"""
Test script to verify search functionality
"""
import sys
import os
sys.path.append('.')

from utils.qdrant_client import qdrant_client
from database import get_db
from models import Document

def test_search():
    print("=== TESTING SEARCH FUNCTIONALITY ===")
    
    # Initialize Qdrant
    print("1. Initializing Qdrant...")
    if not qdrant_client.connect():
        print("❌ Failed to connect to Qdrant")
        return
    if not qdrant_client.initialize_collection():
        print("❌ Failed to initialize collection")
        return
    if not qdrant_client.load_embedding_model():
        print("❌ Failed to load embedding model")
        return
    print("✅ Qdrant initialized successfully")
    
    # Test query
    query = "Knowledge Capture"
    print(f"\n2. Testing search for: '{query}'")
    
    # Get hybrid search results
    search_results = qdrant_client.hybrid_search(
        query_text=query,
        limit=5
    )
    
    print(f"✅ Found {len(search_results)} results")
    
    # Apply confidence threshold (same as API)
    default_min_confidence = float(os.getenv('MIN_SEARCH_CONFIDENCE', '0.5'))
    print(f"3. Applying confidence threshold: {default_min_confidence}")
    
    filtered_results = [result for result in search_results if result['score'] >= default_min_confidence]
    print(f"✅ {len(filtered_results)} results after confidence filtering")
    
    # Get database session
    db = next(get_db())
    
    # Process results (same as API)
    print("\n4. Processing results...")
    enriched_results = []
    for result in filtered_results:
        document_id = result['metadata']['document_id']
        filename = result['metadata'].get('filename', 'Unknown')
        created_at = result['metadata'].get('created_at') if 'created_at' in result['metadata'] else None
        
        if document_id is not None:
            try:
                document_id = int(document_id)
            except Exception:
                document_id = None
        
        document = db.query(Document).filter(Document.id == document_id).first() if document_id is not None else None

        enriched_result = {
            "score": result['score'],
            "text": result['text'],
            "chunk_index": result['metadata']['chunk_index'],
            "query_keywords": query.lower().split(),
            "semantic_score": result.get('semantic_score', result['score']),
            "keyword_score": result.get('keyword_score', 0),
            "document": {
                "id": document.id if document else None,
                "original_filename": document.original_filename if document else filename,
                "created_at": document.created_at if document else created_at
            } if document or filename != 'Unknown' else None
        }
        enriched_results.append(enriched_result)
    
    # Display results
    print(f"\n5. Final results (top 3):")
    for i, result in enumerate(enriched_results[:3], 1):
        print(f"\n--- Result #{i} ---")
        print(f"Score: {result['score']:.3f}")
        print(f"Semantic: {result['semantic_score']:.3f}")
        print(f"Keyword: {result['keyword_score']:.3f}")
        print(f"Document: {result['document']['original_filename'] if result['document'] else 'Unknown'}")
        print(f"Text: {result['text'][:150]}...")
    
    db.close()
    
    # Summary
    print(f"\n=== SUMMARY ===")
    print(f"Query: '{query}'")
    print(f"Total results: {len(search_results)}")
    print(f"After confidence filter: {len(filtered_results)}")
    print(f"Top result: {enriched_results[0]['document']['original_filename'] if enriched_results and enriched_results[0]['document'] else 'None'}")
    
    return enriched_results

if __name__ == "__main__":
    test_search() 