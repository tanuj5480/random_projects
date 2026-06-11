import os
import sys
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
from utils import build_yaml_frontmatter, resolve_wiki_path, REPO_ROOT

STAGING_DIR = REPO_ROOT / "knowledge_base" / "staging"

load_dotenv()

client = OpenAI(
    base_url=os.getenv("LLM_PROVIDER_URL", "http://localhost:11434/v1"),
    api_key="ollama-local",
    timeout=600.0
)

def run_ai_generation(staging_filename, title, page_type):
    """Reads staging data, requests content from local LLM, and prints response."""
    source_file = STAGING_DIR / staging_filename
    if not source_file.exists():
        print(f"❌ Error: Staging source file not found at: {source_file.relative_to(REPO_ROOT)}")
        sys.exit(1)
        
    print(f"📖 Reading source data from: {staging_filename}...")
    source_content = source_file.read_text(encoding="utf-8")
    
    system_prompt = (
        "You are an expert knowledge management engineer. Your task is to process the user's "
        "provided text document and format it into a specific markdown structural schema. "
        "Do NOT include any introduction greeting, do NOT include any wrapping markdown triple-backticks, "
        "and do NOT include any YAML frontmatter block. Output only the markdown body layout.\n\n"
        "Your output must follow this precise markdown layout architecture:\n"
        f"# {title}\n\n"
        "## Summary\n"
        "[Provide a crisp 2 to 3 sentence high-level overview of the material context]\n\n"
        "## Key Concepts\n"
        "- **[Concept Name]**: [Clean definition or explanation]\n"
        "- **[Concept Name]**: [Clean definition or explanation]\n\n"
        "## References\n"
        f"- Material compiled from primary source: {staging_filename}\n"
    )
    
    try:
        response = client.chat.completions.create(
            model=os.getenv("LLM_MODEL_NAME", "llama3.1"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Target Classification: {page_type}\n\nDocument:\n{source_content}"}
            ],
            temperature=0.2,
            extra_body={
                "options": {
                "num_ctx": 32768  # Allows Ollama to process roughly 24,000 words at once
                }
            }
        )
        # Safe extraction: works whether choices behaves like an object or a list
        if isinstance(response.choices, list):
            choice = response.choices[0]
        else:
            choice = response.choices[0]
            
        # Extract content checking both dictionary and attribute styles
        if hasattr(choice, "message"):
            return choice.message.content
        elif "message" in choice:
            return choice["message"]["content"]
        else:
            # Fallback direct string dump if the structure is completely flattened
            return str(choice)
    except Exception as e:
        print(f"❌ LLM Provider Error: Is Ollama running? Error details: {e}")
        sys.exit(1)

def assemble_and_save_wiki(staging_filename, category, title, page_type, tags=""):
    """Orchestrates frontmatter structure building and appends local AI outputs."""
    target_file = resolve_wiki_path(category, title)
    
    if target_file.exists():
        print(f"❌ Error: Wiki page already exists at '{target_file.relative_to(REPO_ROOT)}'.")
        sys.exit(1)
        
    # 1. Get YAML header
    frontmatter = build_yaml_frontmatter(title, page_type, tags, staging_filename)
    
    # 2. Get AI processed body
    markdown_body = run_ai_generation(staging_filename, title, page_type)
    
    # 3. Save fully composed page
    target_file.write_text(frontmatter + markdown_body, encoding="utf-8")
    print(f"✨ Successfully generated AI wiki file: {target_file.relative_to(REPO_ROOT)}")