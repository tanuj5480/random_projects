import os
import re
import json
from datetime import datetime
from typing import List, Dict, Any, Annotated
from pathlib import Path
from typing_extensions import TypedDict
from dotenv import load_dotenv

from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from utils import build_yaml_frontmatter, resolve_wiki_path, REPO_ROOT, WIKI_DIR

STAGING_DIR = REPO_ROOT / "knowledge_base" / "staging"
load_dotenv()

# Initialize our universal local LLM instance
llm = ChatOpenAI(
    base_url=os.getenv("LLM_PROVIDER_URL", "http://localhost:11434/v1"),
    api_key="ollama-local",
    model=os.getenv("LLM_MODEL_NAME", "llama3.1"),
    temperature=0.1,  # Lower temperature prevents factual hallucination
    timeout=600.0
)

# 1. Define the Global Graph State
class WikiState(TypedDict):
    source_files: List[str]
    category: str
    target_topic: str
    tags: str
    
    # Text buffers
    raw_source_content: str
    
    # Structured Data extracted during pipeline
    extracted_entities: List[Dict[str, str]]    # [{'name': '...', 'description': '...'}]
    extracted_concepts: List[Dict[str, str]]    # [{'name': '...', 'description': '...'}]
    claims_and_key_info: List[str]
    contradictions: List[str]
    
    # Control Logs
    execution_log_entries: List[str]

STAGING_DIR = REPO_ROOT / "knowledge_base" / "staging"
load_dotenv()


## 2. Implement the Modular Concern Nodes

# Node 1: Read raw files from staging
def read_source_node(state: WikiState) -> Dict[str, Any]:
    print("🕸️ [Node 1/9] Reading raw source documents...")
    combined_text = ""
    for filename in state["source_files"]:
        file_path = STAGING_DIR / filename.strip()
        if file_path.exists():
            combined_text += f"\n--- Source: {filename} ---\n" + file_path.read_text(encoding="utf-8") + "\n"
    return {"raw_source_content": combined_text}

# Node 2: Factual claims and key data extraction
def extract_claims_node(state: WikiState) -> Dict[str, Any]:
    print("🕸️ [Node 2/9] Identifying core claims and structural information...")
    prompt = "Extract a clean bulleted list of core factual claims, data points, or truths from this material. Output only bullets."
    res = llm.invoke([SystemMessage(content=prompt), HumanMessage(content=state["raw_source_content"])])
    claims = [line.strip("- ").strip() for line in res.content.splitlines() if line.strip()]
    return {"claims_and_key_info": claims}

# Node 3: Identify core Entities & Concepts (JSON Extraction)
def extract_taxonomy_node(state: WikiState) -> Dict[str, Any]:
    print("🕸️ [Node 3/9] Extracting concrete Entities and abstract Concepts (Strict Document Bound)...")
    
    # We force the LLM to output a 'source_quote' property to prove it didn't hallucinate
    system_prompt = (
        "You are a strict data-extraction engine. Your job is to extract key Entities and Concepts "
        "from the user-provided text. You must operate under a strict 'CLOSED-WORLD ASSUMPTION'.\n\n"
        "CRITICAL RULES:\n"
        "1. Do NOT use your internal general knowledge to invent or introduce outside topics, tools, names, or ideas.\n"
        "2. Every extracted item MUST have an exact 'source_quote' taken word-for-word from the text to prove it exists.\n"
        "3. If the text does not mention an item, do NOT extract it.\n\n"
        "Output ONLY raw, valid JSON matching this exact structural schema (no code fences, no filler conversation):\n"
        "{\n"
        '  "entities": [{"name": "Item Name", "description": "Context from text", "source_quote": "Exact word-for-word quote"}],\n'
        '  "concepts": [{"name": "Concept Name", "description": "Context from text", "source_quote": "Exact word-for-word quote"}]\n'
        "}"
    )
    
    res = llm.invoke([
        SystemMessage(content=system_prompt), 
        HumanMessage(content=f"Strict Source Document Material:\n{state['raw_source_content']}")
    ])
    
    try:
        clean_json = re.sub(r"```json\s*|\s*```", "", res.content.strip())
        data = json.loads(clean_json)
        
        # --- VALIDATION LOOP ---
        valid_entities = []
        valid_concepts = []
        source_text_lower = state["raw_source_content"].lower()
        
        # Verify Entities
        for ent in data.get("entities", []):
            quote = ent.get("source_quote", "").strip().lower()
            # If the quote is missing or doesn't actually exist inside the source text, drop it!
            if quote and quote in source_text_lower:
                valid_entities.append(ent)
            else:
                print(f"🛑 Hallucination Filtered: Dropped entity '{ent.get('name')}' (Quote mismatch/missing)")
                
        # Verify Concepts
        for con in data.get("concepts", []):
            quote = con.get("source_quote", "").strip().lower()
            if quote and quote in source_text_lower:
                valid_concepts.append(con)
            else:
                print(f"🛑 Hallucination Filtered: Dropped concept '{con.get('name')}' (Quote mismatch/missing)")

        return {
            "extracted_entities": valid_entities, 
            "extracted_concepts": valid_concepts
        }
        
    except Exception as e:
        print(f"⚠️ Warning: JSON extraction or validation failed: {e}. Proceeding with empty lists.")
        return {"extracted_entities": [], "extracted_concepts": []}


# Node 4: Flag contradictions against current repository state
def identify_contradictions_node(state: WikiState) -> Dict[str, Any]:
    print("🕸️ [Node 4/9] Auditing material against current repository database for contradictions...")
    # Gather titles of pages that already exist to check against
    existing_pages = [p.stem.replace("_", " ") for p in WIKI_DIR.rglob("*.md")]
    
    prompt = (
        f"Existing topics in our knowledge base: {', '.join(existing_pages)}.\n"
        f"New Claims: {', '.join(state['claims_and_key_info'][:10])}.\n"
        "Identify if any new claims logically contradict known baseline properties. "
        "Output a bulleted list of contradictions, or write 'None' if completely safe."
    )
    res = llm.invoke([SystemMessage(content=prompt)])
    contradictions = [res.content.strip()] if "None" not in res.content else []
    return {"contradictions": contradictions}

# Node 5: Write Summary File into specific directory
def write_summary_page_node(state: WikiState) -> Dict[str, Any]:
    print("🕸️ [Node 5/9] Compiling core topic markdown body and writing pages...")
    
    # 1. Ask the local LLM to generate the technical body content
    prompt = (
        f"You are an expert technical wiki writer. Generate a comprehensive master page body for the topic: '{state['target_topic']}'.\n"
        "Strict Grounding Rule: Rely ONLY on the clear factual claims provided below. Do NOT use outside knowledge.\n\n"
        "Follow this layout structure layout exactly:\n"
        f"# {state['target_topic']}\n\n"
        "## Summary\n"
        "[A clear 3-sentence high level summary blending the core context]\n\n"
        "## Key Concepts\n"
        "Provide bulleted breakdowns based on these claims:\n"
    )
    
    claims_text = "\n".join(f"- {c}" for c in state["claims_and_key_info"])
    res = llm.invoke([SystemMessage(content=prompt), HumanMessage(content=claims_text)])
    generated_body = res.content.strip()

    # 2. WRITE SUMMARY ASSET
    summary_file = resolve_wiki_path("Summaries", state["target_topic"])
    summary_frontmatter = build_yaml_frontmatter(state["target_topic"], "summary", state["tags"], ", ".join(state["source_files"]))
    summary_file.write_text(summary_frontmatter + generated_body, encoding="utf-8")
    
    # 3. WRITE MAIN CATEGORY ASSET 
    main_category_file = resolve_wiki_path(state["category"], state["target_topic"])
    
    # Preserve original creation date if this is an update pass
    preserved_date = None
    if main_category_file.exists():
        try:
            old_text = main_category_file.read_text(encoding="utf-8")
            match = re.search(r"^created:\s*(\d{4}-\d{2}-\d{2})", old_text, re.MULTILINE)
            if match:
                preserved_date = match.group(1)
        except Exception:
            pass

    main_frontmatter = build_yaml_frontmatter(
        title=state["target_topic"],
        page_type="concept",
        tags=state["tags"],
        sources=", ".join(state["source_files"])
    )
    
    if preserved_date:
        main_frontmatter = re.sub(r"^(created:\s*)\d{4}-\d{2}-\d{2}", f"created: {preserved_date}", main_frontmatter, flags=re.MULTILINE)

    main_category_file.write_text(main_frontmatter + generated_body, encoding="utf-8")
    print(f"💾 [Node 5] Hard-wrote main wiki file directly to: {main_category_file.relative_to(REPO_ROOT)}")

    import gc
    gc.collect()

    return {
        "final_markdown_body": generated_body,
        "execution_log_entries": [
            f"Generated core markdown body for: {state['target_topic']}",
            f"Saved primary asset file to /{state['category']}/{state['target_topic']}.md",
            f"Saved snapshot brief to /Summaries/{state['target_topic']}.md"
        ]
    }

# Node 6: Batch spawn/update isolated Entity records
def update_entity_pages_node(state: WikiState) -> Dict[str, Any]:
    print(f"🕸️ [Node 6/9] Processing {len(state['extracted_entities'])} Entity database files...")
    logs = []
    for ent in state["extracted_entities"]:
        name = ent["name"]
        target_file = resolve_wiki_path("Entities", name)
        
        # Merge if existing, write clean if new
        existing_text = target_file.read_text(encoding="utf-8") if target_file.exists() else ""
        frontmatter = build_yaml_frontmatter(name, "entity", "entity-auto", ", ".join(state["source_files"]))
        
        prompt = f"Integrate this information into an active technical wiki profile: {ent['description']}\nExisting Context:\n{existing_text}"
        res = llm.invoke([SystemMessage(content="Format as clean markdown body."), HumanMessage(content=prompt)])
        
        target_file.write_text(frontmatter + res.content, encoding="utf-8")
        logs.append(f"Updated entity profile page: {name}")
    return {"execution_log_entries": logs}

# Node 7: Batch spawn/update isolated Concept records
def update_concept_pages_node(state: WikiState) -> Dict[str, Any]:
    print(f"🕸️ [Node 7/9] Processing {len(state['extracted_concepts'])} Concept framework profiles...")
    logs = []
    for con in state["extracted_concepts"]:
        name = con["name"]
        target_file = resolve_wiki_path("Concepts", name)
        
        existing_text = target_file.read_text(encoding="utf-8") if target_file.exists() else ""
        frontmatter = build_yaml_frontmatter(name, "concept", "concept-auto", ", ".join(state["source_files"]))
        
        prompt = f"Develop this concept framework detailing definitions: {con['description']}\nExisting Baseline:\n{existing_text}"
        res = llm.invoke([SystemMessage(content="Format cleanly."), HumanMessage(content=prompt)])
        
        target_file.write_text(frontmatter + res.content, encoding="utf-8")
        logs.append(f"Updated concept blueprint page: {name}")
    return {"execution_log_entries": logs}

# Node 8: Adjust top-level Overview dashboard map
def revise_topic_overview_node(state: WikiState) -> Dict[str, Any]:
    print(f"🕸️ [Node 8/9] Regenerating global Overview dashboard mapping for category '{state['category']}'...")
    target_file = resolve_wiki_path(state["category"], f"{state['category']}_Overview")
    frontmatter = build_yaml_frontmatter(f"{state['category']} Knowledge Map", "overview", "index-map", "system")
    
    # Programmatically find all files inside this specific domain category directory
    category_dir = WIKI_DIR / state["category"].strip().title()
    discovered_links = [f"-[[{p.stem}]]" for p in category_dir.glob("*.md") if p.is_file()]
    
    body = (
        f"# {state['category']} Master Directory Landscape Overview\n\n"
        "## Sub-Topic Node Connections\n"
        "This tracking dashboard list is generated dynamically across localized repository assets:\n\n"
        + "\n".join(discovered_links)
    )
    target_file.write_text(frontmatter + body, encoding="utf-8")
    return {"execution_log_entries": [f"Refreshed top-level directory listing map for: {state['category']}"]}

# Node 9: Append changes block directly to global chronological Log index file
def append_log_and_index_node(state: WikiState) -> Dict[str, Any]:
    print("🕸️ [Node 9/9] Committing session tracking footprint entries to ledger log...")
    log_file = REPO_ROOT / "knowledge_base" / "wiki" / "Change_Ledger.md"
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_header = f"\n### Run Transaction Pipeline Execution: {timestamp}\n"
    
    compiled_bullets = ""
    for entry in state["execution_log_entries"]:
        compiled_bullets += f"- {entry}\n"
        
    if state["contradictions"]:
        compiled_bullets += f"- ⚠️ **Flagged Contradiction Context**: {'; '.join(state['contradictions'])}\n"

    # Append safely to end of tracking ledger
    existing_log = log_file.read_text(encoding="utf-8") if log_file.exists() else "# System Chronological Change Ledger\n"
    log_file.write_text(existing_log + log_header + compiled_bullets, encoding="utf-8")
    print("✨ [LangGraph] Complete pipeline processing cycle terminated cleanly.")
    return {}


## 3. Build and Compile the Multi-Node Flow Engine Map
workflow = StateGraph(WikiState)


# Add Nodes
workflow.add_node("read_source", read_source_node)
workflow.add_node("extract_claims", extract_claims_node)
workflow.add_node("extract_taxonomy", extract_taxonomy_node)
workflow.add_node("identify_contradictions", identify_contradictions_node)
workflow.add_node("write_summary_page", write_summary_page_node)
workflow.add_node("update_entity_pages", update_entity_pages_node)
workflow.add_node("update_concept_pages", update_concept_pages_node)
workflow.add_node("revise_topic_overview", revise_topic_overview_node)
workflow.add_node("append_log_and_index", append_log_and_index_node)

# Map execution edges
workflow.add_edge(START, "read_source")
workflow.add_edge("read_source", "extract_claims")
workflow.add_edge("extract_claims", "extract_taxonomy")
workflow.add_edge("extract_taxonomy", "identify_contradictions")
workflow.add_edge("identify_contradictions", "write_summary_page")
workflow.add_edge("write_summary_page", "update_entity_pages")
workflow.add_edge("update_entity_pages", "update_concept_pages")
workflow.add_edge("update_concept_pages", "revise_topic_overview")
workflow.add_edge("revise_topic_overview", "append_log_and_index")
workflow.add_edge("append_log_and_index", END)
# Compile graph topology
wiki_agent_graph = workflow.compile()


def run_langgraph_pipeline(source_files: List[str], category: str, target_topic: str, tags: str = "") -> Dict[str, Any]:
    """
    Global execution entry point for the stateful multi-node CMS workflow agent.
    Delegates all file writing safely to the internal Node graph execution steps.
    """
    initial_state: WikiState = {
        "source_files": source_files,
        "category": category,
        "target_topic": target_topic,
        "tags": tags,
        "raw_source_content": "",
        "extracted_entities": [],
        "extracted_concepts": [],
        "claims_and_key_info": [],
        "contradictions": [],
        "execution_log_entries": []
    }
    
    print("\n🚀 [LangGraph Pipeline] Starting Multi-Node Knowledge Compilation...")
    print(f"📂 Category Scope:  /{category}")
    print(f"🎯 Target Subject:  {target_topic}")
    print(f"📄 Processing:      {', '.join(source_files)}\n" + "-"*50)
    
    try:
        # Invoke the compiled LangGraph workflow state engine
        # Node 5 will automatically write the category and summary files to disk
        final_state = wiki_agent_graph.invoke(initial_state)
        
        print("-"*50 + f"\n✨ [LangGraph Success] Multi-node pipeline finalized execution cleanly!")
        return final_state
        
    except Exception as e:
        print(f"❌ [LangGraph Pipeline Error] Execution pipeline broke down: {e}")
        import sys
        sys.exit(1)