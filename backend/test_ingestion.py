from weaviate_search_tool import search_weaviate
from web_search_weaviate_tool import search_web_with_deduplication
from dotenv import load_dotenv
import json

load_dotenv()

print("Testing Meir Kadosh (should find existing content):")
results1 = search_web_with_deduplication.invoke({
    "query":"Meir Kadosh from Bright Data"
})
result1_parsed = json.loads(results1)
print(f"Source: {result1_parsed.get('source')}")
print(f"Web search performed: {result1_parsed.get('web_search_performed')}")
print()

print("Testing Gennady Shenker (should perform web search):")
results2 = search_web_with_deduplication.invoke({
    "query":"Tianyi Luo AI Engineer"
})
result2_parsed = json.loads(results2)
print(f"Source: {result2_parsed.get('source')}")
print(f"Web search performed: {result2_parsed.get('web_search_performed')}")