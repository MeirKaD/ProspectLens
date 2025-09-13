#!/usr/bin/env python

def test_imports():
    print("Testing imports...")
    try:
        from langchain_brightdata import (
            BrightDataSERP,
            BrightDataUnlocker, 
            BrightDataWebScraperAPI,
            BrightDataAPIWrapper,
            BrightDataSERPAPIWrapper,
            BrightDataUnlockerAPIWrapper, 
            BrightDataWebScraperAPIWrapper
        )
        print("✅ Successfully imported all modules!")
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

if __name__ == "__main__":
    test_imports()