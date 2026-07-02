import os
import json
from typing import List, Dict, Optional
from pathlib import Path
import PyPDF2
import pdfplumber
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from openai import OpenAI
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

embedding_model = None


def load_embedding_model():
    global embedding_model

    if embedding_model is not None:
        return embedding_model

    try:
        embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    except Exception as e:
        print(f"Error loading embedding model: {e}")
        print("Trying alternative model...")
        try:
            embedding_model = SentenceTransformer('all-mpnet-base-v2')
        except Exception as e2:
            print(f"Error loading alternative model: {e2}")
            embedding_model = None

    return embedding_model

openai_api_key = os.getenv('OPENAI_API_KEY')
openai_client = OpenAI(api_key=openai_api_key) if openai_api_key else None

if openai_client:
    print('OpenAI client initialized successfully.')
else:
    print('Warning: no OpenAI API key found. Set OPENAI_API_KEY in .env.')

# Storage
PDF_STORAGE_DIR = 'pdfs'
INDEX_DIR = 'indices'
METADATA_FILE = 'metadata.json'

Path(PDF_STORAGE_DIR).mkdir(exist_ok=True)
Path(INDEX_DIR).mkdir(exist_ok=True)

class PDFResearchAssistant:
    def __init__(self):
        self.documents = {}
        self.faiss_index = None
        self.embeddings = []
        self.load_metadata()
    
    def load_metadata(self):
        if os.path.exists(METADATA_FILE):
            with open(METADATA_FILE, 'r') as f:
                data = json.load(f)
                self.documents = data.get('documents', {})
                if data.get('embeddings'):
                    self.embeddings = np.array(data['embeddings'])
                    dimension = self.embeddings.shape[1]
                    self.faiss_index = faiss.IndexFlatL2(dimension)
                    self.faiss_index.add(self.embeddings)
    
    def save_metadata(self):
        with open(METADATA_FILE, 'w') as f:
            json.dump({
                'documents': self.documents,
                'embeddings': self.embeddings.tolist() if len(self.embeddings) > 0 else []
            }, f)
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
        except Exception as e:
            print(f"Error extracting text: {e}")
            # Fallback to PyPDF2
            try:
                with open(pdf_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page in pdf_reader.pages:
                        text += page.extract_text() + "\n"
            except Exception as e2:
                print(f"PyPDF2 also failed: {e2}")
        return text
    
    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        chunks = []
        words = text.split()
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            chunks.append(chunk)
        return chunks
    
    def add_pdf(self, pdf_name: str, pdf_path: str) -> Dict:
        model = load_embedding_model()

        if model is None:
            return {
                'success': False,
                'error': 'Embedding model not loaded. Please check your internet connection and restart the server.'
            }
        
        text = self.extract_text_from_pdf(pdf_path)
        chunks = self.chunk_text(text)
        
        doc_id = pdf_name
        self.documents[doc_id] = {
            'name': pdf_name,
            'path': pdf_path,
            'chunks': chunks,
            'chunk_count': len(chunks)
        }
        
        # Generate embeddings for new chunks
        new_embeddings = model.encode(chunks)
        
        # Update FAISS index
        if self.faiss_index is None:
            dimension = new_embeddings.shape[1]
            self.faiss_index = faiss.IndexFlatL2(dimension)
        
        self.faiss_index.add(new_embeddings.astype('float32'))
        
        # Update embeddings array
        if len(self.embeddings) == 0:
            self.embeddings = new_embeddings
        else:
            self.embeddings = np.vstack([self.embeddings, new_embeddings])
        
        self.save_metadata()
        
        return {
            'success': True,
            'document_id': doc_id,
            'chunk_count': len(chunks)
        }
    
    def search(self, query: str, top_k: int = 5, document_ids: Optional[List[str]] = None) -> List[Dict]:
        model = load_embedding_model()

        if model is None:
            return []
        
        if self.faiss_index is None or len(self.embeddings) == 0:
            return []
        
        query_embedding = model.encode([query])
        query_embedding = query_embedding.astype('float32')
        
        search_top_k = len(self.embeddings) if document_ids else top_k
        distances, indices = self.faiss_index.search(query_embedding, search_top_k)

        selected_ids = set(document_ids or [])
        
        results = []
        chunk_index = 0
        for doc_id, doc_data in self.documents.items():
            if selected_ids and doc_id not in selected_ids:
                chunk_index += len(doc_data['chunks'])
                continue

            for chunk in doc_data['chunks']:
                if chunk_index in indices[0]:
                    idx_in_results = np.where(indices[0] == chunk_index)[0][0]
                    results.append({
                        'document': doc_id,
                        'chunk': chunk,
                        'score': float(distances[0][idx_in_results])
                    })
                chunk_index += 1
        
        results.sort(key=lambda x: x['score'])
        return results[:top_k]
    
    def generate_answer(self, query: str, context_chunks: List[str]) -> str:
        if openai_client is None:
            return 'OpenAI API key is missing. Set OPENAI_API_KEY in .env to enable answer generation.'

        context = "\n\n".join(context_chunks)
        
        try:
            response = openai_client.chat.completions.create(
                model='gpt-4o-mini',
                temperature=0.3,
                max_tokens=500,
                messages=[
                    {
                        'role': 'system',
                        'content': (
                            'You are a helpful PDF research assistant. Answer naturally and conversationally using the provided PDF context. '
                            'If the context does not explicitly state the answer, give the closest supported answer or a brief inference based on the document, '
                            'and clearly say it is an inference or likely interpretation. Do not give a bare refusal unless the context is completely unusable. '
                            'When the answer includes structured records (like employee details, IDs, roles, skills, locations, dates, or metrics), format the output as a Markdown table.'
                        )
                    },
                    {
                        'role': 'user',
                        'content': (
                            f'Context:\n{context}\n\n'
                            f'Question: {query}\n\n'
                            'Write a concise, helpful answer with a friendly tone. '
                            'If needed, mention uncertainty instead of saying you could not find anything.'
                        )
                    }
                ]
            )
            return response.choices[0].message.content or ''
        except Exception as e:
            error_text = str(e)
            if 'api_key' in error_text.lower() or 'authentication' in error_text.lower():
                return 'The configured OpenAI API key is invalid. Replace OPENAI_API_KEY in .env with a valid OpenAI key, then restart the server.'
            return f"Error generating answer: {error_text}"
    
    def ask(self, query: str, document_ids: Optional[List[str]] = None) -> Dict:
        search_results = self.search(query, top_k=3, document_ids=document_ids)
        
        if not search_results:
            return {
                'answer': 'No documents have been indexed yet. Please upload PDFs first.',
                'sources': []
            }
        
        context_chunks = [result['chunk'] for result in search_results]
        answer = self.generate_answer(query, context_chunks)
        
        sources = list(set([result['document'] for result in search_results]))
        
        return {
            'answer': answer,
            'sources': sources,
            'context_used': len(context_chunks)
        }

assistant = PDFResearchAssistant()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_pdf():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.endswith('.pdf'):
        return jsonify({'error': 'Only PDF files are allowed'}), 400
    
    pdf_path = os.path.join(PDF_STORAGE_DIR, file.filename)
    file.save(pdf_path)
    
    result = assistant.add_pdf(file.filename, pdf_path)
    return jsonify(result)

@app.route('/ask', methods=['POST'])
def ask_question():
    data = request.json
    query = data.get('query', '')
    document_ids = data.get('document_ids') or []
    
    if not query:
        return jsonify({'error': 'No query provided'}), 400
    
    result = assistant.ask(query, document_ids=document_ids)
    return jsonify(result)

@app.route('/documents', methods=['GET'])
def list_documents():
    docs = []
    for doc_id, doc_data in assistant.documents.items():
        docs.append({
            'id': doc_id,
            'name': doc_data['name'],
            'chunk_count': doc_data['chunk_count']
        })
    return jsonify(docs)

@app.route('/clear', methods=['POST'])
def clear_documents():
    assistant.documents = {}
    assistant.embeddings = np.array([])
    assistant.faiss_index = None
    assistant.save_metadata()
    
    # Clear PDF storage
    for file in os.listdir(PDF_STORAGE_DIR):
        os.remove(os.path.join(PDF_STORAGE_DIR, file))
    
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
