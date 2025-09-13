"""
LangGraph Person Qualification Agent with Tool Binding

This improved agent uses proper tool binding to let the LLM directly call
the search tools, providing more accurate and efficient qualification scoring.
"""

import os
from typing import TypedDict, Annotated, List, Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
import json
from datetime import datetime

# Import your custom tools
from web_search_weaviate_tool import search_web_with_deduplication
from weaviate_search_tool import search_weaviate
from langchain_brightdata import BrightDataUnlocker
from dotenv import load_dotenv


class QualificationState(TypedDict):
    """Enhanced state for the qualification agent"""
    messages: Annotated[List[BaseMessage], add_messages]
    person_name: str
    event_details: Dict[str, Any]
    collected_information: List[Dict[str, Any]]
    qualification_score: Optional[int]
    qualification_reasoning: Optional[str]
    final_report: Optional[Dict[str, Any]]


class ImprovedPersonQualificationAgent:
    """
    Enhanced LangGraph agent that properly uses tool binding for person qualification
    """
    
    def __init__(self, google_api_key: str = None):
        """Initialize with tool-bound LLM"""

        # Load environment variables
        load_dotenv()

        # Initialize BrightData unlocker
        self.unlocker_tool = BrightDataUnlocker(zone="unblocker")

        # Define the tools
        self.tools = [search_web_with_deduplication, search_weaviate]

        # Create LLM with tool binding
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0.1
        ).bind_tools(self.tools)

        # Create tool node for executing tool calls
        self.tool_node = ToolNode(self.tools)

        # Build the graph
        self.app = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build enhanced graph with tool binding"""
        
        builder = StateGraph(QualificationState)
        
        # Add nodes
        builder.add_node("gather_information", self._gather_information)
        builder.add_node("tools", self.tool_node)
        builder.add_node("analyze_and_score", self._analyze_and_score)
        builder.add_node("generate_report", self._generate_report)
        
        # Add conditional edge for tool calls
        def should_continue(state: QualificationState) -> str:
            """Check if we need to call tools or proceed to analysis"""
            messages = state["messages"]
            last_message = messages[-1]
            
            # If the LLM wants to use a tool, route to tools node
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                return "tools"
            
            # Check if we have enough information
            if len(state.get("collected_information", [])) >= 3:
                return "analyze"
            
            # Continue gathering if we have less than 3 searches
            return "continue"
        
        # Add edges
        builder.add_edge(START, "gather_information")
        builder.add_conditional_edges(
            "gather_information",
            should_continue,
            {
                "tools": "tools",
                "analyze": "analyze_and_score",
                "continue": "gather_information"
            }
        )
        builder.add_edge("tools", "gather_information")
        builder.add_edge("analyze_and_score", "generate_report")
        builder.add_edge("generate_report", END)
        
        return builder.compile()
    
    def _gather_information(self, state: QualificationState) -> QualificationState:
        """
        Enhanced information gathering using tool-bound LLM
        """
        person_name = state["person_name"]
        event_details = state["event_details"]
        messages = state["messages"]
        collected_info = state.get("collected_information", [])
        
        # Process any tool results from previous iteration
        if messages and isinstance(messages[-1], ToolMessage):
            try:
                tool_result = messages[-1].content
                if isinstance(tool_result, str):
                    result_data = json.loads(tool_result)
                    
                    # Extract relevant information based on source
                    info_entry = {
                        "source": result_data.get("source", "unknown"),
                        "query": result_data.get("query", ""),
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    if result_data.get("source") == "weaviate_existing":
                        # Process Weaviate results
                        results = result_data.get("results", [])
                        info_entry["data"] = results
                        info_entry["found_existing"] = True
                    elif result_data.get("web_search_performed"):
                        # Process web search results
                        web_search = result_data.get("web_search", {})
                        if web_search.get("success"):
                            results = web_search.get("results", [])
                            # Extract meaningful content
                            processed_results = []
                            for r in results[:5]:  # Top 5 results
                                if isinstance(r, dict):
                                    processed_results.append({
                                        "title": r.get("title", ""),
                                        "snippet": r.get("snippet", r.get("description", "")),
                                        "url": r.get("url", r.get("link", ""))
                                    })
                            info_entry["data"] = processed_results
                    elif result_data.get("results"):
                        # Direct search results from search_weaviate
                        info_entry["data"] = result_data.get("results", [])
                    
                    if info_entry.get("data"):
                        collected_info.append(info_entry)
                        
            except Exception as e:
                print(f"Error processing tool result: {e}")
        
        # Check if we have enough information
        if len(collected_info) >= 3:
            # We have enough searches, proceed to analysis
            return {
                **state,
                "collected_information": collected_info,
                "messages": messages + [AIMessage(content="Sufficient information gathered. Proceeding to analysis.")]
            }
        
        # Create prompt for the LLM to search for more information
        search_number = len(collected_info) + 1
        
        search_prompt = f"""
        You are helping to qualify {person_name} for an event. 
        
        Event Details: {json.dumps(event_details, indent=2)}
        
        Information gathered so far: {search_number - 1} searches completed.
        
        Search #{search_number}:
        Please search for specific information about {person_name} that would help determine their qualification for this event.
        
        Focus areas based on what we need:
        - Professional background and current role
        - Relevant expertise and skills
        - Notable achievements or publications
        - Speaking experience or similar events attended
        - Educational background
        
        Use the search_web_with_deduplication tool to find information. 
        Create a targeted search query that will help us assess their qualification.
        
        If searching for "{person_name}" directly, include their company or field if known.
        """
        
        # Invoke LLM with tool binding
        response = self.llm.invoke(messages + [HumanMessage(content=search_prompt)])
        
        return {
            **state,
            "messages": messages + [HumanMessage(content=search_prompt), response],
            "collected_information": collected_info
        }
    
    def _analyze_and_score(self, state: QualificationState) -> QualificationState:
        """
        Analyze collected information and generate qualification score
        """
        person_name = state["person_name"]
        event_details = state["event_details"]
        collected_info = state.get("collected_information", [])
        
        # Compile all collected data - FIX: Better data extraction
        all_data = []
        for info in collected_info:
            data_items = info.get("data", [])
            for item in data_items:
                if isinstance(item, dict):
                    # Handle different data formats
                    if "content" in item:
                        all_data.append(item.get("content", ""))
                    elif "snippet" in item:
                        all_data.append(f"{item.get('title', '')}: {item.get('snippet', '')}")
                    elif "title" in item and "description" in item:
                        all_data.append(f"{item.get('title', '')}: {item.get('description', '')}")
                    # Handle direct text content
                    elif "title" in item:
                        all_data.append(item.get("title", ""))
                elif isinstance(item, str):
                    all_data.append(item)
        
        compiled_data = "\n\n".join(filter(None, all_data))
        
        if not compiled_data.strip():
            compiled_data = f"Limited information found for {person_name}."
        
        # FIX: Clearer prompt that ensures JSON response
        scoring_prompt = f"""
        Analyze the following information and provide a qualification score.
        
        PERSON: {person_name}
        
        EVENT DETAILS:
        {json.dumps(event_details, indent=2)}
        
        INFORMATION FOUND:
        {compiled_data[:3000]}  # Limit to avoid token issues
        
        Provide a score from 1-10 where:
        - 1-3: Not qualified
        - 4-5: Minimally qualified
        - 6-7: Well qualified
        - 8-9: Highly qualified
        - 10: Exceptionally qualified
        
        YOU MUST RESPOND WITH ONLY A VALID JSON OBJECT, nothing else:
        {{"score": 5, "reasoning": "explanation here", "key_qualifications": ["qual1", "qual2"], "missing_information": ["info1", "info2"]}}
        """
        
        try:
            # FIX: Use a simpler model invocation
            response = self.llm.invoke([HumanMessage(content=scoring_prompt)])
            
            # Extract content from response
            if hasattr(response, 'content'):
                content = response.content
            else:
                content = str(response)
            
            # FIX: Better JSON extraction
            content = content.strip()
            
            # Remove any markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            # Try to parse JSON
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                # Try to extract JSON from the response
                import re
                json_match = re.search(r'\{[^{}]*\{[^{}]*\}[^{}]*\}|\{[^{}]*\}', content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    # Fallback: create a basic result
                    result = {
                        "score": 5,
                        "reasoning": f"Could not parse LLM response. Content found: {bool(compiled_data.strip())}",
                        "key_qualifications": [],
                        "missing_information": ["Unable to process response"]
                    }
            
            score = result.get("score", 5)
            reasoning = result.get("reasoning", "Unable to determine reasoning")
            key_quals = result.get("key_qualifications", [])
            missing_info = result.get("missing_information", [])
            
            # Validate score
            if not isinstance(score, int) or score < 1 or score > 10:
                score = 5
                reasoning = f"Score adjusted to valid range. {reasoning}"
            
        except Exception as e:
            print(f"Error in scoring: {e}")
            print(f"Compiled data length: {len(compiled_data)}")
            score = 5
            reasoning = f"Error in scoring process: {str(e)}. Data was collected but scoring failed."
            key_quals = []
            missing_info = ["Unable to process information"]
        
        return {
            **state,
            "qualification_score": score,
            "qualification_reasoning": reasoning,
            "messages": state["messages"] + [
                AIMessage(content=f"Analysis complete. Score: {score}/10")
            ]
        }
    
    def _generate_report(self, state: QualificationState) -> QualificationState:
        """
        Generate final qualification report
        """
        report = {
            "person_name": state["person_name"],
            "event_details": state["event_details"],
            "qualification_score": state.get("qualification_score", 0),
            "qualification_reasoning": state.get("qualification_reasoning", ""),
            "searches_performed": len(state.get("collected_information", [])),
            "information_sources": [
                {
                    "query": info.get("query", ""),
                    "source": info.get("source", ""),
                    "found_existing": info.get("found_existing", False)
                }
                for info in state.get("collected_information", [])
            ],
            "timestamp": datetime.now().isoformat()
        }
        
        return {
            **state,
            "final_report": report,
            "messages": state["messages"] + [
                AIMessage(content=f"Report generated successfully. Final score: {report['qualification_score']}/10")
            ]
        }

    def extract_event_details_from_url(self, event_url: str) -> Dict[str, Any]:
        """
        Extract event details from a URL using BrightData web scraping

        Args:
            event_url: URL of the event page to scrape

        Returns:
            Dictionary containing extracted event details
        """
        try:
            # Use BrightData unlocker to scrape the event page
            scraped_content = self.unlocker_tool.invoke(event_url)

            # Parse the scraped content using LLM to extract structured event details
            extraction_prompt = f"""
            Extract event details from the following scraped web content.
            Return ONLY a valid JSON object with the following structure:
            {{
                "name": "Event Name",
                "type": "Event Type (conference/workshop/meetup/etc.)",
                "date": "Event Date",
                "location": "Event Location",
                "description": "Brief description",
                "requirements": ["requirement1", "requirement2"],
                "audience": "Target audience",
                "format": "Event format (presentation/panel/workshop/etc.)",
                "topics": ["topic1", "topic2"],
                "url": "{event_url}"
            }}

            Scraped Content:
            {scraped_content[:4000]}  # Limit content to avoid token issues
            """

            # Use LLM to extract structured data
            response = self.llm.invoke([HumanMessage(content=extraction_prompt)])

            # Extract content from response
            if hasattr(response, 'content'):
                content = response.content
            else:
                content = str(response)

            content = content.strip()

            # Remove any markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            # Parse JSON
            try:
                event_details = json.loads(content)

                # Ensure required fields are present with defaults
                default_event = {
                    "name": "Unknown Event",
                    "type": "Event",
                    "date": "TBD",
                    "location": "TBD",
                    "description": "Event details extracted from URL",
                    "requirements": [],
                    "audience": "General audience",
                    "format": "Presentation",
                    "topics": [],
                    "url": event_url
                }

                # Merge extracted details with defaults
                for key, default_value in default_event.items():
                    if key not in event_details or not event_details[key]:
                        event_details[key] = default_value

                return event_details

            except json.JSONDecodeError:
                # Fallback: create basic event details if parsing fails
                return {
                    "name": "Event (parsing failed)",
                    "type": "Event",
                    "date": "TBD",
                    "location": "TBD",
                    "description": f"Event details could not be fully parsed from {event_url}",
                    "requirements": [],
                    "audience": "General audience",
                    "format": "Presentation",
                    "topics": [],
                    "url": event_url,
                    "raw_content": str(scraped_content)[:500]  # Include some raw content for manual review
                }

        except Exception as e:
            # Return error details for debugging
            return {
                "name": "Event (extraction failed)",
                "type": "Event",
                "date": "TBD",
                "location": "TBD",
                "description": f"Failed to extract event details from {event_url}",
                "requirements": [],
                "audience": "General audience",
                "format": "Presentation",
                "topics": [],
                "url": event_url,
                "extraction_error": str(e)
            }

    def qualify_person_from_url(self, person_name: str, event_url: str) -> Dict[str, Any]:
        """
        Qualify a person for an event by first extracting event details from URL

        Args:
            person_name: Name of the person to qualify
            event_url: URL of the event page to scrape for details

        Returns:
            Comprehensive qualification report including scraped event details
        """
        # First extract event details from URL
        event_details = self.extract_event_details_from_url(event_url)

        # Then qualify the person using extracted details
        result = self.qualify_person(person_name, event_details)

        # Add URL extraction info to the result
        result["event_url"] = event_url
        result["event_extracted_from_url"] = True

        return result

    def qualify_person(self, person_name: str, event_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main method to qualify a person for an event
        
        Args:
            person_name: Name of the person to qualify
            event_details: Dictionary with event information
            
        Returns:
            Comprehensive qualification report
        """
        # Initialize state
        initial_state = QualificationState(
            messages=[],
            person_name=person_name,
            event_details=event_details,
            collected_information=[],
            qualification_score=None,
            qualification_reasoning=None,
            final_report=None
        )
        
        # Run the graph
        try:
            result = self.app.invoke(initial_state)
            return result.get("final_report", {
                "error": "Failed to generate report",
                "person_name": person_name,
                "qualification_score": 0
            })
        except Exception as e:
            return {
                "error": f"Agent execution failed: {str(e)}",
                "person_name": person_name,
                "qualification_score": 0,
                "timestamp": datetime.now().isoformat()
            }


# Enhanced example usage
def test_agent():
    """Test the improved agent with various scenarios"""

    # Initialize agent
    agent = ImprovedPersonQualificationAgent()

    # Test Case 1: URL-based Event Qualification
    print("=" * 60)
    print("TEST 1: URL-based Event Qualification")
    print("=" * 60)

    # Test with URL scraping (using example.com as demonstration)
    result1 = agent.qualify_person_from_url(
        person_name="Meir Kadosh from Bright Data",
        event_url="https://luma.com/f13dwefh"
    )

    print(f"Person: {result1.get('person_name')}")
    print(f"Event URL: {result1.get('event_url')}")
    print(f"Event Name: {result1.get('event_details', {}).get('name', 'N/A')}")
    print(f"Score: {result1.get('qualification_score')}/10")
    print(f"Searches: {result1.get('searches_performed', 0)}")
    print(f"\nReasoning: {result1.get('qualification_reasoning')}")
    print(f"\nInformation Sources:")
    for source in result1.get('information_sources', []):
        print(f"  - {source.get('query')} ({source.get('source')})")

    # Test Case 2: Traditional Manual Event Details (fallback)
    print("\n" + "=" * 60)
    print("TEST 2: Traditional Manual Event Details")
    print("=" * 60)

    event2 = {
        "name": "AI/ML Innovation Summit 2024",
        "type": "Technical Conference",
        "requirements": [
            "Deep expertise in machine learning or AI",
            "Experience with production ML systems",
            "Strong communication skills",
            "Previous speaking experience preferred"
        ],
        "audience": "ML engineers, data scientists, researchers",
        "format": "45-minute technical presentation with Q&A"
    }

    result2 = agent.qualify_person(
        person_name="Meir Kadosh from Bright Data",
        event_details=event2
    )

    print(f"Person: {result2.get('person_name')}")
    print(f"Score: {result2.get('qualification_score')}/10")
    print(f"Searches: {result2.get('searches_performed', 0)}")
    print(f"\nReasoning: {result2.get('qualification_reasoning')}")

    return result1


if __name__ == "__main__":
    print("Improved Person Qualification Agent")
    print("=" * 40)
    print("This version properly uses tool binding for better results\n")
    
    try:
        result = test_agent()
        print("\n✅ Agent completed successfully!")
        
        # Save result to file for review
        with open("qualification_result.json", "w") as f:
            json.dump(result, f, indent=2)
            print("\nFull report saved to qualification_result.json")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nEnsure these environment variables are set:")
        print("- GOOGLE_API_KEY")
        print("- WEAVIATE_URL")
        print("- WEAVIATE_API_KEY")
        print("- BRIGHTDATA_API_TOKEN")