import requests
import os
import sys
from getpass import getpass

def login(base_url, username, password):
    """Login and get access token"""
    login_url = f"{base_url}/auth/login"
    response = requests.post(
        login_url,
        data={"username": username, "password": password}
    )
    
    if response.status_code != 200:
        print(f"Login failed with status code {response.status_code}")
        print(response.text)
        sys.exit(1)
    
    return response.json()["access_token"]

def upload_pdf(base_url, token, pdf_path):
    """Upload a PDF file to the server"""
    upload_url = f"{base_url}/upload/upload-pdf"
    
    # Check if file exists
    if not os.path.exists(pdf_path):
        print(f"Error: File {pdf_path} not found")
        sys.exit(1)
    
    # Check if file is a PDF (at least by extension)
    if not pdf_path.lower().endswith('.pdf'):
        print("Error: File must be a PDF")
        sys.exit(1)
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    with open(pdf_path, 'rb') as f:
        files = {"file": (os.path.basename(pdf_path), f, "application/pdf")}
        
        print(f"Uploading {pdf_path}...")
        response = requests.post(upload_url, headers=headers, files=files)
    
    if response.status_code == 201:
        result = response.json()
        print(f"✅ Upload successful!")
        print(f"   Document ID: {result['id']}")
        print(f"   Original filename: {result['original_filename']}")
        print(f"   Stored filename: {result['filename']}")
        print(f"   File size: {result['file_size']} bytes")
        print(f"   Vectorization status: {result['vectorization_status']}")
        print(f"   Chunks created: {result['chunks_count']}")
        print(f"   Upload time: {result['created_at']}")
        return result
    else:
        print(f"❌ Upload failed with status code {response.status_code}")
        print(f"Response: {response.text}")
        return None

def list_pdfs(base_url, token):
    """List all uploaded PDF files"""
    list_url = f"{base_url}/upload/pdf-list"
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    print("Fetching list of uploaded PDFs...")
    response = requests.get(list_url, headers=headers)
    
    if response.status_code == 200:
        documents = response.json()
        print(f"✅ Found {len(documents)} documents:")
        for doc in documents:
            status_emoji = "✅" if doc['vectorization_status'] == 'completed' else "⏳" if doc['vectorization_status'] == 'pending' else "❌"
            print(f"   {status_emoji} ID: {doc['id']}")
            print(f"      File: {doc['original_filename']}")
            print(f"      Size: {doc['file_size']} bytes")
            print(f"      Uploaded by: {doc['uploaded_by']}")
            print(f"      Status: {doc['vectorization_status']}")
            print(f"      Chunks: {doc['chunks_count']}")
            print(f"      Date: {doc['created_at']}")
            print()
        return documents
    else:
        print(f"❌ Failed to list documents with status code {response.status_code}")
        print(f"Response: {response.text}")
        return None

def print_document_info(doc):
    """Print formatted document information"""
    print(f"- ID: {doc['id']}")
    print(f"  Filename: {doc['filename']}")
    print(f"  Original: {doc['original_filename']}")
    print(f"  Size: {doc['file_size']} bytes")
    print(f"  Type: {doc['content_type']}")
    print(f"  Uploaded by: {doc['uploaded_by']}")
    print(f"  Created at: {doc['created_at']}")
    if 'message' in doc:
        print(f"  Message: {doc['message']}")
    print()

def search_documents(base_url, token, query, limit=5):
    """Search for documents using semantic search"""
    search_url = f"{base_url}/upload/search"
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    print(f"🔍 Searching for: '{query}'")
    print("-" * 70)
    
    response = requests.post(
        search_url, 
        headers=headers, 
        params={"query": query, "limit": limit}
    )
    
    if response.status_code == 200:
        results = response.json()
        print(f"✅ Found {results['results_count']} matching chunks (showing top 3):")
        print(f"📝 Query: '{results['query']}'")
        print()
        
        for i, result in enumerate(results['results'], 1):
            score = result['score']
            
            # Enhanced relevance indicators
            if score >= 0.8:
                relevance = "🎯 EXCELLENT MATCH"
                score_color = "🟢"
            elif score >= 0.6:
                relevance = "📈 GOOD MATCH"
                score_color = "🟡"
            elif score >= 0.4:
                relevance = "📊 FAIR MATCH"
                score_color = "🟠"
            else:
                relevance = "📉 WEAK MATCH"
                score_color = "🔴"
            
            print(f"{'━' * 70}")
            print(f"🏆 RESULT #{i}")
            print(f"{'━' * 70}")
            print(f"{score_color} Similarity Score: {score:.4f} - {relevance}")
            print(f"📄 Document: {result['document']['original_filename']}")
            print(f"🔢 Chunk: #{result['chunk_index']} | 📅 Uploaded: {result['document']['created_at'][:10]}")
            print()
            
            # Enhanced text display with better formatting
            text = result['text'].strip()
            
            # Clean up the text
            text = text.replace('\n', ' ').replace('\r', ' ')
            text = ' '.join(text.split())  # Remove extra spaces
            
            print(f"📖 CONTENT:")
            print(f"   {text}")
            print()
        
        # Summary statistics
        if results['results']:
            avg_score = sum(r['score'] for r in results['results']) / len(results['results'])
            best_score = max(r['score'] for r in results['results'])
            print(f"{'=' * 70}")
            print(f"📊 SEARCH SUMMARY:")
            print(f"   🎯 Best Match Score: {best_score:.4f}")
            print(f"   📈 Average Score: {avg_score:.4f}")
            print(f"   🔍 Search Quality: {'Excellent' if best_score >= 0.7 else 'Good' if best_score >= 0.5 else 'Fair' if best_score >= 0.3 else 'Poor'}")
            print(f"{'=' * 70}")
        
        return results
    else:
        print(f"❌ Search failed with status code {response.status_code}")
        print(f"Response: {response.text}")
        return None

if __name__ == "__main__":
    # Default to localhost if not specified
    base_url = "http://localhost:8000"
    
    # Get credentials
    print("Please enter your login credentials:")
    username = input("Username: ")
    password = getpass("Password: ")
    
    # Login and get token
    try:
        token = login(base_url, username, password)
        print(f"Login successful, token obtained")
        
        while True:
            print("\nOptions:")
            print("1. Upload a PDF file")
            print("2. List all PDF files")
            print("3. Search documents")
            print("4. Exit")
            
            choice = input("Enter your choice (1-4): ")
            
            if choice == "1":
                pdf_path = input("Enter the path to the PDF file: ")
                upload_pdf(base_url, token, pdf_path)
            elif choice == "2":
                list_pdfs(base_url, token)
            elif choice == "3":
                query = input("Enter your search query: ")
                search_documents(base_url, token, query, 3)
            elif choice == "4":
                print("Exiting...")
                break
            else:
                print("Invalid choice. Please try again.")
    except requests.exceptions.ConnectionError:
        print(f"Connection error: Could not connect to {base_url}")
        print("Make sure the server is running")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0) 