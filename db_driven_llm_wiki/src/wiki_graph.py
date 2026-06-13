import os
import re
from typing import List, Dict, Any
from pathlib import Path
from typing_extensions import TypedDict
from dotenv import load_dotenv

from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from utils import build_yaml_frontmatter, resolve_wiki_path, REPO_ROOT

STAGING_DIR = REPO_ROOT / "knowledge_base" / "staging"
load_dotenv()

# 1. Define the Graph State structure
class WikiState(TypedDict):
    # Inputs from CLI
    source_files: List[str]
    category: str
    title: str
    page_type: str
    tags: str
    
    # Internal state tracking variables
    existing_content: str
    compiled_new_material: str
    final_markdown_body: str

# 2. Node A: Read existing documentation and text inputs
def read_sources_node(state: WikiState) -> Dict[str, Any]:
    print("🕸️ [LangGraph] Node: Reading sources and existing context...")
    target_file = resolve_wiki_path(state["category"], state["title"])
    
    # Read existing wiki data
    existing_text = ""
    if target_file.exists():
        full_text = target_file.read_text(encoding="utf-8")
        if full_text.startswith("---\n"):
            parts = full_text.split("---\n", 2)
            existing_text = parts[2] if len(parts) > 2 else full_text
            
    # Read staging text documents
    new_material = ""
    for filename in state["source_files"]:
        file_path = STAGING_DIR / filename.strip()
        if file_path.exists():
            new_material += f"\n--- Source Document: {filename} ---\n"
            new_material += file_path.read_text(encoding="utf-8") + "\n"
        else:
            print(f"⚠️ Warning: Staging file missing: {filename}")

    return {
        "existing_content": existing_text,
        "compiled_new_material": new_material
    }

# 3. Node B: Execute local LLM generation 
def synthesize_wiki_node(state: WikiState) -> Dict[str, Any]:
    print(f"🕸️ [LangGraph] Node: Querying local model '{os.getenv('LLM_MODEL_NAME', 'llama3.1')}'...")
    
    # Initialize LangChain model pointing directly to local Ollama API
    llm = ChatOpenAI(
        base_url=os.getenv("LLM_PROVIDER_URL", "http://localhost:11434/v1"),
        api_key="ollama-local",
        model=os.getenv("LLM_MODEL_NAME", "llama3.1"),
        temperature=0.2,
        timeout=600.0
    )
    
    system_prompt = (
        "You are an expert technical documentation synthesizer. Your goal is to take an "
        "existing wiki entry and update it by incorporating new information from multiple incoming documents.\n\n"
        "Strict Rules:\n"
        "1. Do NOT delete pre-existing accurate facts or headers from the current wiki.\n"
        "2. De-duplicate information cleanly.\n"
        "3. Maintain our markdown layout format precisely.\n"
        "4. Do NOT include greetings, conversational intro text, or markdown code blocks around your entire response.\n\n"
        f"Format Layout Requirement:\n"
        f"# {state['title']}\n\n"
        "## Summary\n"
        "[Updated summary blending old and new insights together]\n\n"
        "## Key Concepts\n"
        "- **[Concept Name]**: [Unified definition tracking facts across all sources]\n\n"
        "## References\n"
        f"- Material updated using sources: {', '.join(state['source_files'])}\n"
    )
    
    user_prompt = (
        f"CURRENT WIKI ENTRY CONTENTS:\n{state['existing_content'] if state['existing_content'] else '[Empty Baseline]'}\n\n"
        f"NEW INCOMING DOCUMENTS TO CONSOLIDATE:\n{state['compiled_new_material']}"
    )
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    response = llm.invoke(messages)
    
    return {"final_markdown_body": response.content}

# 4. Build and compile the state graph layout
workflow = StateGraph(WikiState)

# Add Nodes
workflow.add_node("read_sources", read_sources_node)
workflow.add_node("synthesize_wiki", synthesize_wiki_node)

# Map execution edges
workflow.add_edge(START, "read_sources")
workflow.add_edge("read_sources", "synthesize_wiki")
workflow.add_edge("synthesize_wiki", END)

# Compile graph topology
wiki_agent_graph = workflow.compile()

def run_langgraph_pipeline(source_files, category, title, page_type, tags=""):
    """Entry point function to invoke the compiled LangGraph workflow pipeline."""
    initial_state: WikiState = {
        "source_files": source_files,
        "category": category,
        "title": title,
        "page_type": page_type,
        "tags": tags,
        "existing_content": "",
        "compiled_new_material": "",
        "final_markdown_body": ""
    }
    
    # Run graph execution to completion
    final_output = wiki_agent_graph.invoke(initial_state)
    
    # Save the resulting outputs using our repository schemas
    target_file = resolve_wiki_path(category, title)
    frontmatter = build_yaml_frontmatter(title, page_type, tags, ", ".join(source_files))
    
    target_file.write_text(frontmatter + final_output["final_markdown_body"], encoding="utf-8")
    print(f"✨ [LangGraph] Successfully output file to repository: {target_file.relative_to(REPO_ROOT)}")