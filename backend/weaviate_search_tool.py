"""
FINAL FIXED Weaviate Search Tool - Compatible with Weaviate v4 Client
"""

import os
import weaviate
from typing import List, Dict, Any, Optional, Union
from langchain_core.tools import tool
from langchain_weaviate import WeaviateVectorStore
from langchain_openai import OpenAIEmbeddings
from weaviate.classes.init import Auth
from weaviate.classes.query import Filter, MetadataQuery

import json
import uuid


def json_serializer(obj):
    """Custom JSON serializer to handle UUID and other non-serializable objects"""
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if hasattr(obj, '__dict__'):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


class WeaviateSearchManager:
    """Manager class for Weaviate search operations with v4 client"""
    
    def __init__(self, 
                 cluster_url: str = None, 
                 api_key: str = None,
                 openai_api_key: str = None,
                 collection_name: str = "WebSearchResults"):
        """Initialize Weaviate Search Manager"""
        self.cluster_url = cluster_url or os.getenv("WEAVIATE_URL")
        self.api_key = api_key or os.getenv("WEAVIATE_API_KEY") 
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.collection_name = collection_name
        
        if not all([self.cluster_url, self.api_key]):
            raise ValueError("Weaviate cluster URL and API key are required")
            
        self._client = None
        self._vectorstore = None
        
    @property
    def client(self):
        """Lazy initialization of Weaviate client"""
        if self._client is None:
            try:
                self._client = weaviate.connect_to_weaviate_cloud(
                    cluster_url=self.cluster_url,
                    auth_credentials=Auth.api_key(self.api_key)
                )
            except Exception as e:
                raise Exception(f"Failed to connect to Weaviate: {str(e)}")
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
    
    def close(self):
        """Close Weaviate client connection"""
        if self._client:
            self._client.close()
            self._client = None
            self._vectorstore = None


# Global manager instance
_weaviate_manager = None

def get_weaviate_manager() -> WeaviateSearchManager:
    """Get or create global Weaviate manager instance"""
    global _weaviate_manager
    if _weaviate_manager is None:
        _weaviate_manager = WeaviateSearchManager()
    return _weaviate_manager


@tool
def search_weaviate(
    query: str,
    search_type: str = "similarity",
    limit: int = 5,
    alpha: float = 0.75,
    filters: Optional[Dict[str, Any]] = None,
    include_scores: bool = True,
    collection_name: Optional[str] = None
) -> str:
    """
    Search the Weaviate vector database with various search types and filtering options.

    Args:
        query: The search query text
        search_type: "similarity" (vector), "hybrid" (vector+BM25), or "keyword" (BM25 only)
        limit: Max results
        alpha: Hybrid alpha (vector weight)
        filters: dict with { property, operator, value }
        include_scores: include distance/similarity (and score if available)
        collection_name: override default collection

    Returns:
        JSON string with results
    """
    try:
        manager = get_weaviate_manager()

        # Optional collection override
        if collection_name:
            manager.collection_name = collection_name
            manager._vectorstore = None  # reset cached vectorstore

        vectorstore = manager.vectorstore  # ensures client is connected too

        # ----- Build Weaviate filter (used by both vectorstore + v4 client) -----
        weaviate_filter = None
        if filters:
            try:
                prop = filters.get("property")
                operator = (filters.get("operator") or "Equal").lower()
                value = filters.get("value")
                if prop and value is not None:
                    f = Filter.by_property(prop)
                    if operator == "equal":
                        weaviate_filter = f.equal(value)
                    elif operator == "notequalto":
                        weaviate_filter = f.not_equal(value)
                    elif operator == "greaterthan":
                        weaviate_filter = f.greater_than(value)
                    elif operator == "lessthan":
                        weaviate_filter = f.less_than(value)
                    elif operator == "containsany" and isinstance(value, list):
                        weaviate_filter = f.contains_any(value)
                    else:
                        weaviate_filter = f.equal(value)
            except Exception as e:
                return json.dumps({
                    "error": f"Invalid filter format: {str(e)}",
                    "results": []
                }, default=json_serializer)

        search_type_l = (search_type or "similarity").lower()

        # ===== NEW: hybrid/keyword (BM25) branch via v4 collections API =====
        if search_type_l in ("hybrid", "keyword"):
            coll = manager.client.collections.get(manager.collection_name)

            # Ask for metadata.distance (and score if supported by your client)
            try:
                return_meta = MetadataQuery(distance=True, score=True)
            except TypeError:
                # Older clients may not accept score=...
                return_meta = MetadataQuery(distance=True)

            try:
                if search_type_l == "hybrid":
                    resp = coll.query.hybrid(
                        query=query,
                        alpha=alpha,
                        limit=limit,
                        filters=weaviate_filter,
                        return_metadata=return_meta,
                    )
                else:  # "keyword" -> BM25
                    resp = coll.query.bm25(
                        query=query,
                        limit=limit,
                        filters=weaviate_filter,
                        return_metadata=return_meta,
                    )

                results = []
                for o in (resp.objects or []):
                    props = o.properties or {}
                    # Try common fields for content text
                    text = props.get("text") or props.get("content") or props.get("body") or ""
                    # Keep other props as metadata, but drop the main text field
                    meta = {k: v for k, v in props.items() if k not in ("text", "content", "body")}

                    # Extract distance/score from metadata if present
                    md = getattr(o, "metadata", None) or {}
                    # some clients expose attributes; normalize to dict lookups
                    distance = getattr(md, "distance", None) if not isinstance(md, dict) else md.get("distance")
                    score = getattr(md, "score", None) if not isinstance(md, dict) else md.get("score")

                    # Convert distance -> similarity in [0,1] (cosine distance common cases)
                    similarity = None
                    if isinstance(distance, (int, float)):
                        if 0 <= distance <= 1:
                            similarity = 1 - distance
                        elif 0 < distance <= 2:
                            similarity = max(0.0, 1 - (distance / 2.0))

                    item = {
                        "content": text,
                        "metadata": meta,
                    }
                    if include_scores:
                        item.update({
                            "distance": float(distance) if isinstance(distance, (int, float)) else distance,
                            "similarity": similarity,
                        })
                        if score is not None:
                            # BM25/Hybrid relevance score (if your client returns it)
                            try:
                                item["score"] = float(score)
                            except Exception:
                                item["score"] = score

                    results.append(item)

                return json.dumps({
                    "query": query,
                    "search_type": search_type_l,
                    "collection_name": manager.collection_name,
                    "num_results": len(results),
                    "results": results
                }, default=json_serializer, indent=2)

            except Exception as e:
                return json.dumps({
                    "error": f"{search_type_l} search failed: {str(e)}",
                    "query": query,
                    "collection_name": manager.collection_name,
                    "results": []
                }, default=json_serializer)

        # ===== Existing: pure vector similarity via LangChain VectorStore =====
        # NOTE: alpha is ignored here; it's only relevant for hybrid.
        search_kwargs = {"k": limit}
        if weaviate_filter is not None:
            search_kwargs["filters"] = weaviate_filter

        results = []
        try:
            if include_scores:
                docs_with_scores = vectorstore.similarity_search_with_score(query, **search_kwargs)
                for doc, distance in docs_with_scores:
                    # normalize to similarity
                    similarity = None
                    if isinstance(distance, (int, float)):
                        if 0 <= distance <= 1:
                            similarity = 1 - distance
                        elif 0 < distance <= 2:
                            similarity = max(0.0, 1 - (distance / 2.0))

                    # Clean metadata for JSON
                    clean_metadata = {}
                    for k, v in (doc.metadata or {}).items():
                        try:
                            json.dumps(v, default=json_serializer)
                            clean_metadata[k] = v
                        except Exception:
                            clean_metadata[k] = str(v)

                    results.append({
                        "content": doc.page_content,
                        "metadata": clean_metadata,
                        "distance": float(distance) if isinstance(distance, (int, float)) else str(distance),
                        "similarity": similarity
                    })
            else:
                docs = vectorstore.similarity_search(query, **search_kwargs)
                for doc in docs:
                    clean_metadata = {}
                    for k, v in (doc.metadata or {}).items():
                        try:
                            json.dumps(v, default=json_serializer)
                            clean_metadata[k] = v
                        except Exception:
                            clean_metadata[k] = str(v)

                    results.append({
                        "content": doc.page_content,
                        "metadata": clean_metadata
                    })
        except Exception as search_error:
            return json.dumps({
                "error": f"Search execution failed: {str(search_error)}",
                "query": query,
                "collection_name": manager.collection_name,
                "results": []
            }, default=json_serializer)

        return json.dumps({
            "query": query,
            "search_type": "similarity",
            "collection_name": manager.collection_name,
            "num_results": len(results),
            "results": results
        }, default=json_serializer, indent=2)

    except Exception as e:
        return json.dumps({
            "error": f"Search failed: {str(e)}",
            "query": query,
            "collection_name": collection_name or "unknown",
            "results": []
        }, default=json_serializer)


@tool  
def get_weaviate_collections() -> str:
    """
    Get list of available collections in the Weaviate instance.
    
    Returns:
        JSON string containing list of collection names and their basic info
    """
    try:
        manager = get_weaviate_manager()
        client = manager.client
        
        # Get all collections using the v4 client API
        collections = []
        try:
            # For v4 client, collections.list_all() returns collection names as strings
            collection_names = client.collections.list_all()
            
            for name in collection_names:
                # Get collection object to access properties
                try:
                    collection = client.collections.get(name)
                    collection_info = {
                        "name": name,
                        "description": "Collection exists and accessible"
                    }
                    # Try to get more details if available
                    try:
                        config = collection.config.get()
                        collection_info["description"] = getattr(config, 'description', 'No description available')
                    except:
                        pass  # Use default description
                        
                    collections.append(collection_info)
                except Exception as e:
                    # Even if we can't get details, include the collection name
                    collections.append({
                        "name": name,
                        "description": f"Collection exists but details unavailable: {str(e)}"
                    })
                    
        except Exception as e:
            return json.dumps({
                "error": f"Failed to list collections: {str(e)}",
                "collections": []
            }, default=json_serializer)
        
        return json.dumps({
            "collections": collections,
            "total_count": len(collections)
        }, default=json_serializer, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": f"Failed to get collections: {str(e)}",
            "collections": []
        }, default=json_serializer)


@tool
def close_weaviate_connection() -> str:
    """
    Close the Weaviate connection to free up resources.
    """
    try:
        global _weaviate_manager
        if _weaviate_manager:
            _weaviate_manager.close()
            _weaviate_manager = None
        return "Weaviate connection closed successfully"
    except Exception as e:
        return f"Error closing connection: {str(e)}"


def debug_weaviate_connection():
    """Debug function to test Weaviate connection and collections"""
    try:
        print("Testing Weaviate connection...")
        manager = get_weaviate_manager()
        client = manager.client
        
        print("✓ Connected to Weaviate")
        
        # Test getting collections with v4 API
        print("Getting collections...")
        try:
            collection_names = client.collections.list_all()
            print(f"Found {len(collection_names)} collections:")
            for name in collection_names:
                print(f"  - {name}")
                
            # Test accessing a collection if any exist
            if collection_names:
                first_collection_name = collection_names[0]
                print(f"Testing access to collection: {first_collection_name}")
                
                collection = client.collections.get(first_collection_name)
                
                # Try to get some objects
                response = collection.query.fetch_objects(limit=3)
                print(f"Found {len(response.objects)} objects in collection")
                
                for i, obj in enumerate(response.objects[:2]):
                    print(f"  Object {i+1}: {str(obj.properties)[:100]}...")
            else:
                print("No collections found")
                
        except Exception as e:
            print(f"Error getting collections: {e}")
            
    except Exception as e:
        print(f"Connection test failed: {e}")
    
    finally:
        # Clean up properly using invoke
        try:
            close_weaviate_connection.invoke({})
        except Exception as e:
            print(f"Error during cleanup: {e}")


if __name__ == "__main__":
    debug_weaviate_connection()