"""
Web Search Tool with Automatic Weaviate Ingestion

This tool wraps BrightData SERP to perform web searches and automatically
ingests the results into Weaviate for future retrieval.
"""

import os
import json
import hashlib
import time
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Union
from langchain_core.tools import tool
from langchain_brightdata import BrightDataSERP
from langchain_core.documents import Document
from langchain_weaviate import WeaviateVectorStore
from langchain_openai import OpenAIEmbeddings
import weaviate
from weaviate.classes.init import Auth
from dotenv import load_dotenv
from weaviate.classes.query import Filter, MetadataQuery


# Load environment variables
load_dotenv()


class WebSearchWeaviateManager:
    """Manager for web search and Weaviate ingestion operations"""
    
    def __init__(self, 
                 cluster_url: str = None,
                 api_key: str = None,
                 openai_api_key: str = None,
                 collection_name: str = "WebSearchResults"):
        """
        Initialize the manager
        
        Args:
            cluster_url: Weaviate Cloud cluster URL
            api_key: Weaviate API key  
            openai_api_key: OpenAI API key for embeddings
            collection_name: Weaviate collection name for web search results
        """
        self.cluster_url = cluster_url or os.getenv("WEAVIATE_URL")
        self.api_key = api_key or os.getenv("WEAVIATE_API_KEY")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.collection_name = "WebSearchResults"
        
        if not all([self.cluster_url, self.api_key]):
            raise ValueError("Weaviate cluster URL and API key are required")
        
        self._client = None
        self._vectorstore = None
        self._serp_tool = None
    
    @property
    def client(self):
        """Lazy initialization of Weaviate client"""
        if self._client is None:
            self._client = weaviate.connect_to_weaviate_cloud(
                cluster_url=self.cluster_url,
                auth_credentials=Auth.api_key(self.api_key)
            )
        return self._client
    
    @property
    def vectorstore(self):
        """Lazy initialization of WeaviateVectorStore"""
        if self._vectorstore is None:
            embeddings = OpenAIEmbeddings(openai_api_key=self.openai_api_key)
            self._vectorstore = WeaviateVectorStore(
                client=self.client,
                index_name=self.collection_name,
                text_key="text",
                embedding=embeddings
            )
        return self._vectorstore
    
    @property
    def serp_tool(self):
        """Lazy initialization of BrightData SERP tool"""
        if self._serp_tool is None:
            self._serp_tool = BrightDataSERP(parse_results=True)
        return self._serp_tool
    
    def search_web(self, query: str) -> Dict[str, Any]:
        """
        Perform web search using BrightData SERP
        
        Args:
            query: Search query string
            
        Returns:
            Dictionary containing search results
        """
        try:
            results = self.serp_tool.invoke(query)
            return {
                "success": True,
                "query": query,
                "results": results,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "query": query,
                "error": str(e),
                "results": [],
                "timestamp": datetime.now().isoformat()
            }
    
    def create_content_hash(self, content: str) -> str:
        """Create a hash for content to help with deduplication"""
        return hashlib.md5(content.encode()).hexdigest()
    
    def process_search_results(self, search_response: Dict[str, Any]) -> List[Document]:
        documents: List[Document] = []
        if not search_response.get("success"):
            return documents

        query = search_response["query"]
        timestamp = search_response["timestamp"]
        results = search_response.get("results")

        def _make_doc(title: str, url: str, snippet: str, idx: int) -> Optional[Document]:
            if not title or not url:
                return None
            # skip obvious junk/navigation
            if "google.com" in url or url.startswith("/search"):
                return None
            content = f"{title}\n\n{snippet}".strip()
            if not content:
                return None
            content_hash = self.create_content_hash(f"{url}|{content}")
            return Document(
                page_content=content,
                metadata={
                    "source": "web_search",
                    "search_query": query,
                    "url": url,
                    "title": title,
                    "snippet": snippet,
                    "search_timestamp": timestamp,
                    "result_index": idx,
                    "content_hash": content_hash,
                    "ingestion_date": datetime.now().strftime("%Y-%m-%d"),
                    "tool": "brightdata_serp",
                }
            )

        # BrightData can return dicts, lists, or strings.
        # If string, try to parse it as JSON first
        if isinstance(results, str):
            try:
                results = json.loads(results)
            except json.JSONDecodeError:
                # If we can't parse it as JSON, just return empty documents
                return documents
                
        # 1) If dict: look for "organic"/"results"
        if isinstance(results, dict):
            organic = results.get("organic") or results.get("results") or []
            for i, r in enumerate(organic[:10]):
                title = r.get("title") or ""
                url = r.get("link") or r.get("url") or r.get("href") or ""
                snippet = r.get("description") or r.get("snippet") or ""
                doc = _make_doc(title, url, snippet, i)
                if doc:
                    documents.append(doc)

        # 2) If list of dicts: same extraction
        elif isinstance(results, list):
            for i, r in enumerate(results[:10]):
                if not isinstance(r, dict):
                    continue
                title = r.get("title") or ""
                url = r.get("url") or r.get("link") or r.get("href") or ""
                snippet = r.get("snippet") or r.get("description") or ""
                doc = _make_doc(title, url, snippet, i)
                if doc:
                    documents.append(doc)

        # 3) If string: ignore the SERP blob to avoid junk ingestion
        # (If you really want to index it, parse & extract first.)
        else:
            return documents

        return documents

    
    def ingest_to_weaviate(self, documents: List[Document]) -> Dict[str, Any]:
        if not documents:
            return {"success": True, "message": "No documents to ingest", "ingested_count": 0}

        filtered: List[Document] = []
        coll = self.client.collections.get(self.collection_name)
        for d in documents:
            ch = d.metadata.get("content_hash")
            url = d.metadata.get("url")
            filt = None
            if ch:
                filt = Filter.by_property("content_hash").equal(ch)
            elif url:
                filt = Filter.by_property("url").equal(url)

            exists = False
            if filt:
                try:
                    resp = coll.query.fetch_objects(limit=1, filters=filt)
                    exists = bool(resp.objects)
                except Exception:
                    pass

            if not exists:
                filtered.append(d)

        if not filtered:
            return {"success": True, "message": "All documents already ingested", "ingested_count": 0}

        self.vectorstore.add_documents(filtered)
        return {
            "success": True,
            "message": f"Successfully ingested {len(filtered)} documents",
            "ingested_count": len(filtered),
            "documents_metadata": [doc.metadata for doc in filtered],
        }

    
    def close(self):
        """Close Weaviate client connection"""
        if self._client:
            self._client.close()
            self._client = None
            self._vectorstore = None


# Global manager instance
_web_search_manager = None

def get_web_search_manager() -> WebSearchWeaviateManager:
    """Get or create global web search manager instance"""
    global _web_search_manager
    if _web_search_manager is None:
        _web_search_manager = WebSearchWeaviateManager()
    return _web_search_manager


@tool
def search_web(
    query: str,
    ingest_to_weaviate: bool = True,
    collection_name: Optional[str] = None
) -> str:
    """
    Perform web search using BrightData SERP and optionally ingest results to Weaviate.
    
    This tool searches the web for the given query and automatically saves the results
    to your Weaviate knowledge base so they can be found in future searches without
    needing to search the web again.
    
    Args:
        query: The search query to look for on the web
        ingest_to_weaviate: Whether to automatically save results to Weaviate (default: True)
        collection_name: Override default collection name if needed
        
    Returns:
        JSON string containing the web search results and ingestion status
        
    Example:
        search_web.invoke({"query": "latest AI research papers"})
        search_web.invoke({"query": "Python machine learning", "ingest_to_weaviate": False})
    """
    try:
        manager = get_web_search_manager()
        
        # Override collection name if provided
        if collection_name:
            manager.collection_name = collection_name
            manager._vectorstore = None  # Reset to use new collection
        
        # Perform web search
        search_results = manager.search_web(query)
        
        # Prepare response
        response = {
            "query": query,
            "web_search": search_results,
            "weaviate_ingestion": {"skipped": True}
        }
        
        # Ingest to Weaviate if requested and search was successful
        if ingest_to_weaviate and search_results.get("success"):
            # Process search results into documents
            documents = manager.process_search_results(search_results)
            
            # Ingest documents
            ingestion_result = manager.ingest_to_weaviate(documents)
            response["weaviate_ingestion"] = ingestion_result
        
        return json.dumps(response, indent=2)
        
    except Exception as e:
        error_response = {
            "query": query,
            "error": f"Web search failed: {str(e)}",
            "web_search": {"success": False, "error": str(e)},
            "weaviate_ingestion": {"skipped": True}
        }
        return json.dumps(error_response, indent=2)


@tool
def search_web_with_deduplication(
    query: str,
    check_existing: bool = True,
    similarity_threshold: float = 0.6,  # Raised threshold for better precision
    collection_name: Optional[str] = None,
    keyword_boost: bool = True  # Enable keyword boosting for better relevance
) -> str:
    """
    Perform web search with smart deduplication - checks Weaviate first.
    
    This tool first checks if similar content already exists in Weaviate before
    performing a web search. If similar content is found, it returns that instead
    of searching the web, saving time and API calls.
    
    Args:
        query: The search query
        check_existing: Whether to check Weaviate for existing content first (default: True)
        similarity_threshold: Minimum similarity score to consider content as existing (0.0-1.0)
        collection_name: Override default collection name if needed
        keyword_boost: Whether to use hybrid search (vector + keyword) for better relevance
        
    Returns:
        JSON string containing results from either Weaviate or web search
    """
    try:
        from weaviate_search_tool import search_weaviate
        
        # Initialize response object
        response = {
            "query": query,
            "source": "unknown",
            "existing_content_found": False,
            "web_search_performed": False
        }
        
        # Initialize variables that will be used across scopes
        best = None
        best_sim = 0.0
        existing_data = {"results": []}
        
        # Check existing content in Weaviate first
        if check_existing:
            try:
                # Search existing content with more results to increase chance of finding matches
                existing_search_params = {
                    "query": query,
                    "search_type": "similarity",  # Using similarity search which works reliably
                    "limit": 10,  # Increased to get more potential matches
                    "include_scores": True
                }
                
                if collection_name:
                    existing_search_params["collection_name"] = collection_name
                
                # Debug info
                print(f"Searching Weaviate for: {query}")
                
                existing_results = search_weaviate.invoke(existing_search_params)
                
                # Handle different response formats - THIS IS THE KEY FIX
                try:
                    if isinstance(existing_results, str):
                        parsed_data = json.loads(existing_results)
                        # Extract the results array from the parsed JSON
                        existing_data = parsed_data.get("results", [])
                    else:
                        existing_data = existing_results.get("results", []) if isinstance(existing_results, dict) else []
                        
                    # Debug info
                    print(f"Found {len(existing_data)} results in Weaviate")
                except Exception as e:
                    print(f"Error parsing Weaviate results: {str(e)}")
                    existing_data = []
                
                # Check all results and find the best match above threshold
                for r in existing_data:
                    if not isinstance(r, dict):
                        print(f"Skipping non-dict result: {type(r)}")
                        continue
                    
                    # Get similarity score from result
                    sim = r.get("similarity")
                    # Debug info
                    print(f"Result similarity: {sim}")
                    
                    # Check if content is actually relevant to the query
                    content_relevant = False
                    content = str(r.get('content', '')).lower()
                    metadata = r.get('metadata', {})
                    title = str(metadata.get('title', '')).lower()
                    snippet = str(metadata.get('snippet', '')).lower()
                    full_content = f"{content} {title} {snippet}"
                    query_terms = query.lower().split()
                    
                    # First check for exact matches of important terms (names, organizations, etc.)
                    # Filter out common words and require longer terms
                    common_words = {'from', 'with', 'about', 'startup', 'company', 'person', 'the', 'and', 'or', 'at', 'in', 'to', 'for', 'of', 'on', 'by', 'founder', 'co-founder', 'ceo', 'cto', 'data', 'tech', 'ai', 'lead', 'head', 'director', 'manager'}
                    important_terms = [term.lower() for term in query.split() if len(term) > 4 and term.lower() not in common_words]
                    exact_matches = sum(1 for term in important_terms if term in full_content)
                    
                    # Then check for partial matches
                    matching_terms = sum(1 for term in query_terms if term in full_content)
                    relevance_score = matching_terms / len(query_terms) if query_terms else 0
                    
                    # Be more strict about what's considered relevant
                    # Require higher relevance score AND meaningful exact matches
                    content_relevant = (relevance_score >= 0.6) or (exact_matches >= 2 and relevance_score >= 0.4)
                    print(f"Content relevance: {relevance_score:.2f} (threshold: 0.6), Exact matches: {exact_matches}")

                    if isinstance(sim, (int, float)):
                        # Prioritize content relevance over similarity for existing content
                        # Be more conservative - require both good relevance AND exact matches for low threshold
                        effective_threshold = similarity_threshold

                        if content_relevant and exact_matches >= 2:
                            # High relevance + multiple exact matches = very likely existing content
                            effective_threshold = 0.02  # Very low threshold
                        elif content_relevant and exact_matches >= 1:
                            # Good relevance + some exact matches = lower threshold
                            effective_threshold = max(0.1, similarity_threshold - 0.4)
                        elif exact_matches >= 3:
                            # Many exact matches but lower relevance = medium threshold
                            effective_threshold = max(0.2, similarity_threshold - 0.3)

                        # Accept if similarity meets threshold and content is relevant
                        if sim >= effective_threshold and content_relevant and sim > best_sim:
                            best = r
                            best_sim = sim

                if best:
                    # Format the result to match web search format
                    metadata = best.get("metadata", {})
                    formatted_result = {
                        "title": metadata.get("title", ""),
                        "url": metadata.get("url", ""),
                        "snippet": metadata.get("snippet", best.get("content", "")[:200]),
                        "similarity": best_sim
                    }
                    
                    response.update({
                        "source": "weaviate_existing",
                        "existing_content_found": True,
                        "results": [formatted_result],
                        "message": f"Found existing relevant content (similarity: {best_sim:.3f})"
                    })
                    return json.dumps(response, indent=2)
                else:
                    # Debug info if no matches found
                    print(f"No results above similarity threshold {similarity_threshold}")
            
            except Exception as e:
                # If checking existing content fails, continue with web search
                print(f"Error checking existing content: {str(e)}")
                response["existing_check_error"] = str(e)
        
        # No relevant existing content found, perform web search
        print(f"Performing web search for: {query}")
        web_search_result = search_web.invoke({
            "query": query,
            "ingest_to_weaviate": True,
            "collection_name": collection_name
        })
        
        web_data = json.loads(web_search_result)
        response.update({
            "source": "web_search",
            "web_search_performed": True,
            "web_search": web_data.get("web_search"),
            "weaviate_ingestion": web_data.get("weaviate_ingestion")
        })
        
        return json.dumps(response, indent=2)
        
    except Exception as e:
        error_response = {
            "query": query,
            "error": f"Search with deduplication failed: {str(e)}",
            "source": "error"
        }
        return json.dumps(error_response, indent=2)


@tool
def close_web_search_connection() -> str:
    """
    Close the web search manager connection to free up resources.
    Call this when done with web search operations.
    
    Returns:
        Status message
    """
    try:
        global _web_search_manager
        if _web_search_manager:
            _web_search_manager.close()
            _web_search_manager = None
        return "Web search manager connection closed successfully"
    except Exception as e:
        return f"Error closing web search connection: {str(e)}"


# Example usage and testing functions
def test_web_search_tool():
    """Test function for the web search tool"""
    
    print("Testing Web Search Tool with Weaviate Ingestion")
    print("=" * 50)
    
    # Test basic web search
    print("\n1. Basic web search:")
    result1 = search_web.invoke({
        "query": "latest AI research papers",
        "ingest_to_weaviate": True
    })
    print(json.loads(result1))
    
    # Test search without ingestion
    print("\n2. Web search without Weaviate ingestion:")
    result2 = search_web.invoke({
        "query": "Python machine learning tutorials",
        "ingest_to_weaviate": False
    })
    print(json.loads(result2))
    
    # Test search with deduplication
    print("\n3. Search with deduplication (should find existing content):")
    result3 = search_web_with_deduplication.invoke({
        "query": "latest AI research papers",  # Same as first query
        "check_existing": True
    })
    print(json.loads(result3))


if __name__ == "__main__":
    print("Web Search Tool with Weaviate Ingestion")
    print("======================================")
    
    print("\nConfiguration required:")
    print("- WEAVIATE_URL: Your Weaviate Cloud cluster URL")
    print("- WEAVIATE_API_KEY: Your Weaviate API key") 
    print("- OPENAI_API_KEY: Your OpenAI API key")
    print("- BRIGHTDATA_API_TOKEN: Your BrightData API token")
    
    print("\nExample usage:")
    print('search_web.invoke({"query": "latest AI research"})')
    print('search_web_with_deduplication.invoke({"query": "machine learning"})')
    
    # Uncomment to run tests (ensure environment is configured)
    test_web_search_tool()