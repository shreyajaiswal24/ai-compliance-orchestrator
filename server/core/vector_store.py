import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Tuple
import json
import os

class VectorStore:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        self.index = faiss.IndexFlatIP(self.dimension)  # Inner product (cosine similarity)
        self.documents: List[Dict] = []
        self.is_trained = False
        
    def add_documents(self, docs: List[Dict[str, Any]]):
        """Add documents to the vector store"""
        texts = [doc.get("content", "") for doc in docs]
        embeddings = self.model.encode(texts, convert_to_tensor=False)
        
        # Normalize for cosine similarity
        faiss.normalize_L2(embeddings)
        
        self.index.add(embeddings.astype('float32'))
        self.documents.extend(docs)
        self.is_trained = True
        
    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        if not self.is_trained:
            return []
            
        query_embedding = self.model.encode([query], convert_to_tensor=False)
        faiss.normalize_L2(query_embedding)
        
        scores, indices = self.index.search(query_embedding.astype('float32'), k)
        
        results = []
        for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
            if idx < len(self.documents):
                doc = self.documents[idx].copy()
                doc['similarity_score'] = float(score)
                doc['rank'] = i + 1
                results.append(doc)
                
        return results
    
    def save(self, filepath: str):
        """Save index and documents"""
        faiss.write_index(self.index, f"{filepath}.index")
        with open(f"{filepath}.docs", 'w') as f:
            json.dump(self.documents, f)
            
    def load(self, filepath: str):
        """Load index and documents"""
        if os.path.exists(f"{filepath}.index"):
            self.index = faiss.read_index(f"{filepath}.index")
            with open(f"{filepath}.docs", 'r') as f:
                self.documents = json.load(f)
            self.is_trained = True

class RAGSystem:
    def __init__(self):
        self.policy_store = VectorStore()
        self.evidence_store = VectorStore()
        self.vision_ocr_store = VectorStore()
        self._initialize_with_mock_data()
        
    def _initialize_with_mock_data(self):
        """Initialize with mock policy and evidence documents"""
        mock_policies = [
            {
                "doc_id": "POLICY-001",
                "chunk_id": "MFA-SEC-001",
                "content": "Multi-factor authentication is required for all user logins accessing sensitive data. MFA must include at least two factors: something you know (password) and something you have (token/phone).",
                "document_title": "Information Security Policy",
                "section": "Authentication Requirements"
            },
            {
                "doc_id": "POLICY-001", 
                "chunk_id": "MFA-SEC-002",
                "content": "Backup authentication methods must be provided in case primary MFA method is unavailable. This includes backup codes or alternative verification methods.",
                "document_title": "Information Security Policy",
                "section": "Authentication Requirements"
            },
            {
                "doc_id": "POLICY-002",
                "chunk_id": "AUTH-REQ-003", 
                "content": "Login systems must implement session timeout after 30 minutes of inactivity and force re-authentication for administrative functions.",
                "document_title": "Access Control Policy",
                "section": "Session Management"
            }
        ]
        
        mock_evidence = [
            {
                "doc_id": "SPEC-001",
                "chunk_id": "LOGIN-FLOW-001",
                "content": "User enters credentials -> SMS OTP sent to registered phone -> User enters OTP -> Access granted. System supports backup codes for emergency access.",
                "document_title": "Product Specification - Authentication Flow",
                "section": "Login Process"
            },
            {
                "doc_id": "API-DOC-001",
                "chunk_id": "AUTH-ENDPOINT-001", 
                "content": "POST /auth/login - Requires username, password, and otp_token parameters. Returns JWT token valid for 30 minutes.",
                "document_title": "API Documentation",
                "section": "Authentication Endpoints"
            }
        ]
        
        mock_vision_ocr = [
            {
                "doc_id": "SCREEN-001",
                "chunk_id": "LOGIN-UI-001",
                "content": "Screenshot shows login form with username field, password field, and 'Send SMS Code' button. Below that is OTP input field with 6 digits. Footer shows 'Use backup code' link.",
                "document_title": "Mobile App Login Screen",
                "section": "Authentication UI",
                "image_source": "mobile_login_screenshot.png",
                "ocr_confidence": 0.95
            },
            {
                "doc_id": "SCREEN-001",
                "chunk_id": "LOGIN-UI-002", 
                "content": "Dashboard header displays user avatar, notification bell icon, and settings gear. Main area shows 'Authentication Settings' panel with toggle switches for 'Require MFA', 'Session Timeout: 30 minutes', 'Force Re-auth for Admin'.",
                "document_title": "Admin Dashboard - Auth Settings",
                "section": "Configuration UI",
                "image_source": "admin_auth_settings.png",
                "ocr_confidence": 0.92
            },
            {
                "doc_id": "DIAGRAM-001",
                "chunk_id": "FLOW-CHART-001",
                "content": "Flow diagram shows: User Login -> Password Check -> SMS OTP -> Token Validation -> Access Granted. Side branch from SMS OTP shows 'Backup Code' option leading to same Token Validation step.",
                "document_title": "Authentication Flow Diagram",
                "section": "System Architecture",
                "image_source": "auth_flow_diagram.png", 
                "ocr_confidence": 0.88
            }
        ]
        
        self.policy_store.add_documents(mock_policies)
        self.evidence_store.add_documents(mock_evidence)
        self.vision_ocr_store.add_documents(mock_vision_ocr)
    
    async def retrieve_policies(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant policies for a query"""
        return self.policy_store.search(query, k)
        
    async def retrieve_evidence(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant evidence for a query"""  
        return self.evidence_store.search(query, k)
    
    async def retrieve_vision_ocr(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant vision/OCR content for a query"""
        return self.vision_ocr_store.search(query, k)
    
    async def add_ocr_document(self, doc: Dict[str, Any]):
        """Add a new OCR-processed document to the vision store"""
        self.vision_ocr_store.add_documents([doc])