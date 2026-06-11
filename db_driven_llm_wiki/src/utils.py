from datetime import datetime
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WIKI_DIR = REPO_ROOT / "knowledge_base" / "wiki"
VALID_TYPES = ["entity", "concept", "summary", "overview"]

def build_yaml_frontmatter(title, page_type, tags=None, sources=None):
    """Generates a strict schema-compliant YAML frontmatter string block."""
    if page_type not in VALID_TYPES:
        print(f"❌ Error: Invalid type '{page_type}'. Must be one of: {', '.join(VALID_TYPES)}")
        sys.exit(1)

    tag_list = [t.strip() for t in tags.split(",")] if tags else []
    yaml_tags = "\n" + "\n".join(f"  - {t}" for t in tag_list) if tag_list else " []"
    
    source_list = [s.strip() for s in sources.split(",")] if sources else []
    yaml_sources = "\n" + "\n".join(f"  - \"{s}\"" for s in source_list) if source_list else " []"

    current_date = datetime.now().strftime("%Y-%m-%d")

    return (
        "---\n"
        f"title: \"{title.strip()}\"\n"
        f"type: {page_type}\n"
        f"created: {current_date}\n"
        f"updated: {current_date}\n"
        f"tags:{yaml_tags}\n"
        f"sources:{yaml_sources}\n"
        "---\n\n"
    )

def resolve_wiki_path(category, title):
    """Returns the standardized system target file path for a wiki page."""
    category_slug = category.strip().title()
    title_slug = title.strip().replace(" ", "_").title()
    target_dir = WIKI_DIR / category_slug
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir / f"{title_slug}.md"