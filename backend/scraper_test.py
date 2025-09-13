from langchain_brightdata import BrightDataUnlocker
from dotenv import load_dotenv
load_dotenv()
unlocker_tool = BrightDataUnlocker(zone="unblocker")

results=unlocker_tool.invoke("https://www.example.com")
print(results)