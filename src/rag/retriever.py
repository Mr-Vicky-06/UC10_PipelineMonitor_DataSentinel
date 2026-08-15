import os
import glob
from typing import List, Dict, Any

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


class DocumentRetriever:
    def __init__(self, docs_dir: str = "docs"):
        self.docs_dir = docs_dir
        self.documents = []
        self.vectorizer = None
        self.tfidf_matrix = None
        self.doc_mapping = {}
        
        self._load_documents()

    def _load_documents(self):
        """Loads markdown documents from the docs directory."""
        # Load runbooks specifically
        runbook_pattern = os.path.join(self.docs_dir, "runbooks", "*.md")
        for filepath in glob.glob(runbook_pattern):
            self._add_document(filepath, "RUNBOOK")
            
        # Optionally load other docs if needed for TF-IDF fallback
        general_pattern = os.path.join(self.docs_dir, "*.md")
        for filepath in glob.glob(general_pattern):
            self._add_document(filepath, "GENERAL_DOC")

        if SKLEARN_AVAILABLE and self.documents:
            self.vectorizer = TfidfVectorizer(stop_words='english')
            texts = [doc['content'] for doc in self.documents]
            self.tfidf_matrix = self.vectorizer.fit_transform(texts)

    def _add_document(self, filepath: str, doc_type: str):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        filename = os.path.basename(filepath)
        doc = {
            "source_document": filename,
            "source_type": doc_type,
            "content": content
        }
        self.documents.append(doc)
        self.doc_mapping[filename] = doc

    def _deterministic_routing(self, anomaly_type: str) -> Dict[str, Any]:
        """Routes specific anomalies to exact runbooks."""
        route_map = {
            "DATA_QUALITY": "DATA_QUALITY_RUNBOOK.md",
            "VOLUME_ANOMALY": "VOLUME_ANOMALY_RUNBOOK.md",
            "MULTIVARIATE_ANOMALY": "MULTIVARIATE_ANOMALY_RUNBOOK.md"
        }
        
        target_filename = route_map.get(anomaly_type)
        if target_filename and target_filename in self.doc_mapping:
            return self.doc_mapping[target_filename]
        return None

    def _tfidf_fallback(self, query: str) -> Dict[str, Any]:
        """Uses TF-IDF to find the most relevant document based on a query."""
        if not SKLEARN_AVAILABLE or not self.documents:
            return None
            
        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        
        best_idx = similarities.argmax()
        if similarities[best_idx] > 0.05: # threshold
            return self.documents[best_idx]
        return None

    def retrieve(self, anomaly_type: str = None, user_query: str = None) -> List[Dict[str, Any]]:
        """Retrieves documents based on deterministic routing or fallback query."""
        retrieved = []
        
        if anomaly_type:
            doc = self._deterministic_routing(anomaly_type)
            if doc:
                doc['retrieval_method'] = 'DETERMINISTIC'
                retrieved.append(doc)
                
        # If deterministic failed or there's an explicit query, try fallback
        if not retrieved and user_query:
            doc = self._tfidf_fallback(user_query)
            if doc:
                doc['retrieval_method'] = 'TF-IDF'
                retrieved.append(doc)
                
        return retrieved
