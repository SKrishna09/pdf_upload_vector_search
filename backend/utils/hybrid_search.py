"""
Hybrid Search Module

This module provides hybrid search functionality that combines semantic similarity
with keyword matching for improved search relevance.
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class HybridSearchEngine:
    """
    Hybrid search engine that combines semantic similarity with keyword matching.
    
    This class provides methods to enhance semantic search results by applying
    keyword-based scoring and proximity matching to improve search relevance.
    """
    
    def __init__(self, semantic_weight: float = 0.7, keyword_weight: float = 0.3):
        """
        Initialize the hybrid search engine.
        
        Args:
            semantic_weight: Weight for semantic similarity score (default: 0.7)
            keyword_weight: Weight for keyword matching score (default: 0.3)
        """
        self.semantic_weight = semantic_weight
        self.keyword_weight = keyword_weight
        self.proximity_distance = 50  # Characters within which words are considered close
    
    def calculate_keyword_score(self, query_text: str, document_text: str) -> float:
        """
        Calculate keyword matching score for a document.
        
        Args:
            query_text: The search query
            document_text: The document text to score
            
        Returns:
            Normalized keyword score between 0 and 1+
        """
        query_words = query_text.lower().split()
        query_lower = query_text.lower()
        text_lower = document_text.lower()
        
        if not query_words:
            return 0.0
        
        keyword_score = 0.0
        matched_words = 0
        
        # Check for individual word matches
        for word in query_words:
            if word in text_lower:
                matched_words += 1
                keyword_score += 1.0
        
        # Bonus for phrase matching (more flexible)
        if len(query_words) > 1:
            # Check for exact phrase match
            if query_lower in text_lower:
                keyword_score += 0.5
            # Check for partial phrase matches (words appearing close together)
            elif matched_words >= 2:
                proximity_bonus = self._calculate_proximity_bonus(query_words, text_lower)
                keyword_score += proximity_bonus
        
        # Normalize keyword score
        return keyword_score / len(query_words)
    
    def _calculate_proximity_bonus(self, query_words: List[str], text_lower: str) -> float:
        """
        Calculate proximity bonus for words appearing close together.
        
        Args:
            query_words: List of query words
            text_lower: Lowercase document text
            
        Returns:
            Proximity bonus score
        """
        # Find positions of each word in the text
        words_found = []
        for word in query_words:
            word_positions = []
            start = 0
            while True:
                pos = text_lower.find(word, start)
                if pos == -1:
                    break
                word_positions.append(pos)
                start = pos + 1
            if word_positions:
                words_found.append((word, word_positions))
        
        # Check if words appear within proximity distance of each other
        proximity_bonus = 0.0
        if len(words_found) >= 2:
            proximity_bonus_applied = False
            for i, (word1, positions1) in enumerate(words_found):
                for j, (word2, positions2) in enumerate(words_found):
                    if i != j and not proximity_bonus_applied:
                        for pos1 in positions1:
                            for pos2 in positions2:
                                if abs(pos1 - pos2) <= self.proximity_distance:
                                    proximity_bonus = 0.3  # Proximity bonus
                                    proximity_bonus_applied = True
                                    break
                            if proximity_bonus_applied:
                                break
                    if proximity_bonus_applied:
                        break
        
        return proximity_bonus
    
    def calculate_hybrid_score(self, semantic_score: float, keyword_score: float, 
                             matched_words: int, total_words: int) -> float:
        """
        Calculate the final hybrid score combining semantic and keyword scores.
        
        Args:
            semantic_score: Semantic similarity score
            keyword_score: Keyword matching score
            matched_words: Number of query words found in document
            total_words: Total number of words in query
            
        Returns:
            Combined hybrid score
        """
        # If all words are found, give more weight to keyword score
        if matched_words == total_words:
            # 60% semantic, 40% keyword for perfect keyword matches
            return (0.6 * semantic_score) + (0.4 * keyword_score)
        else:
            # Use default weighting for partial matches
            return (self.semantic_weight * semantic_score) + (self.keyword_weight * keyword_score)
    
    def rerank_results(self, query_text: str, semantic_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Rerank semantic search results using hybrid scoring.
        
        Args:
            query_text: The search query
            semantic_results: List of semantic search results
            
        Returns:
            Reranked results with hybrid scores
        """
        query_words = query_text.lower().split()
        total_words = len(query_words)
        
        if not query_words:
            return semantic_results
        
        hybrid_results = []
        
        for result in semantic_results:
            document_text = result.get('text', '')
            semantic_score = result.get('score', 0.0)
            
            # Calculate keyword score
            keyword_score = self.calculate_keyword_score(query_text, document_text)
            
            # Count matched words for weighting decision
            matched_words = sum(1 for word in query_words if word in document_text.lower())
            
            # Calculate hybrid score
            hybrid_score = self.calculate_hybrid_score(
                semantic_score, keyword_score, matched_words, total_words
            )
            
            # Create enhanced result
            hybrid_result = {
                **result,
                'score': hybrid_score,
                'semantic_score': semantic_score,
                'keyword_score': keyword_score
            }
            hybrid_results.append(hybrid_result)
        
        # Sort by hybrid score (descending)
        hybrid_results.sort(key=lambda x: x['score'], reverse=True)
        
        return hybrid_results
    
    def search(self, query_text: str, semantic_search_func, limit: int = 5, 
               filter_dict: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Perform hybrid search using a semantic search function.
        
        Args:
            query_text: The search query
            semantic_search_func: Function to perform semantic search
            limit: Maximum number of results to return
            filter_dict: Optional filter dictionary for semantic search
            
        Returns:
            Hybrid search results
        """
        try:
            # Get more semantic results for better reranking
            # Use limit*4 to ensure we capture relevant chunks that might rank lower semantically
            semantic_limit = max(limit * 4, 20)
            semantic_results = semantic_search_func(query_text, semantic_limit, filter_dict)
            
            if not semantic_results:
                return []
            
            # Rerank using hybrid scoring
            hybrid_results = self.rerank_results(query_text, semantic_results)
            
            # Return top results
            return hybrid_results[:limit]
            
        except Exception as e:
            logger.error(f"Failed to perform hybrid search: {str(e)}")
            # Fallback to semantic search with original limit
            return semantic_search_func(query_text, limit, filter_dict)


# Create a global instance with default settings
hybrid_search_engine = HybridSearchEngine() 