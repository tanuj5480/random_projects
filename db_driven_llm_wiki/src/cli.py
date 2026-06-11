import argparse
from datetime import datetime
import re
import sys
from pathlib import Path

from utils import build_yaml_frontmatter, resolve_wiki_path, VALID_TYPES, WIKI_DIR, REPO_ROOT
from generator import assemble_and_save_wiki

def create_wiki_stub(category, title, page_type, tags=None, sources=None):
    """Creates an empty manual markdown file template with correct frontmatter headers."""
    target_file = resolve_wiki_path(category, title)
    
    if target_file.exists():
        print(f"❌ Error: Wiki page already exists at '{target_file.relative_to(REPO_ROOT)}'.")
        sys.exit(1)
        
    frontmatter = build_yaml_frontmatter(title, page_type, tags, sources)
    body = f"# {title.strip()}\n\n## Summary\n<!-- Fill in summary -->\n\n## Key Concepts\n- \n\n## References\n- "
    
    target_file.write_text(frontmatter + body, encoding="utf-8")
    print(f"✅ Created empty wiki stub: {target_file.relative_to(REPO_ROOT)}")

def update_wiki_timestamp(category, title):
    """Finds an existing file and bumps its 'updated:' parameter stamp value."""
    target_file = resolve_wiki_path(category, title)
    
    if not target_file.exists():
        print(f"❌ Error: Wiki page not found at '{target_file.relative_to(REPO_ROOT)}'")
        sys.exit(1)
        
    content = target_file.read_text(encoding="utf-8")
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    new_content, count = re.subn(r"^(updated:\s*)\d{4}-\d{2}-\d{2}", f"updated: {current_date}", content, flags=re.MULTILINE)
    
    if count == 0:
        print("❌ Error: Markdown file lacks a valid 'updated:' timestamp layout line.")
        sys.exit(1)
            
    target_file.write_text(new_content, encoding="utf-8")
    print(f"🔄 Updated timestamp to {current_date} for: {target_file.relative_to(REPO_ROOT)}")

def list_wikis():
    """Lists folders and pages within the central wiki knowledge architecture."""
    if not WIKI_DIR.exists() or not any(WIKI_DIR.iterdir()):
        print("📭 The wiki knowledge base is currently empty.")
        return

    print("📚 Current Wiki Knowledge Base:")
    for folder in sorted(WIKI_DIR.iterdir()):
        if folder.is_dir() and not folder.name.startswith("."):
            print(f"📁 {folder.name}/")
            for file in sorted(folder.glob("*.md")):
                print(f"   📄 {file.stem.replace('_', ' ')}")

def inspect_wiki():
    """Outputs basic schema validation parameters and file counts."""
    if not WIKI_DIR.exists():
        print("❌ Error: Directory path structures do not exist.")
        sys.exit(1)

    all_files = list(WIKI_DIR.rglob("*.md"))
    directories = [d for d in WIKI_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")]
    
    print("📊 Wiki Structural Inspection:")
    print("-" * 35)
    print(f"🔢 Total Wiki Pages:  {len(all_files)}")
    print(f"🗂️ Total Categories:  {len(directories)}")
    print("-" * 35)
    for d in sorted(directories):
        page_count = len(list(d.glob("*.md")))
        print(f"   • /{d.name} ({page_count} page{'s' if page_count != 1 else ''})")

def main():
    parser = argparse.ArgumentParser(description="CLI tool to manage your local AI Wiki Knowledge Base.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create", help="Build structural page components.")
    create_parser.add_argument("--category", "-c", required=True)
    create_parser.add_argument("--title", "-t", required=True)
    create_parser.add_argument("--type", "-type", required=True, choices=VALID_TYPES)
    create_parser.add_argument("--tags", "-g", default="")
    create_parser.add_argument("--sources", "-s", default="")
    create_parser.add_argument("--source-file", "-sf", default=None, help="Staging file target processing marker")

    update_parser = subparsers.add_parser("update", help="Bump modification parameters.")
    update_parser.add_argument("--category", "-c", required=True)
    update_parser.add_argument("--title", "-t", required=True)

    subparsers.add_parser("list")
    subparsers.add_parser("inspect")

    args = parser.parse_args()

    if args.command == "create":
        if args.source_file:
            assemble_and_save_wiki(args.source_file, args.category, args.title, args.type, args.tags)
        else:
            create_wiki_stub(args.category, args.title, args.type, args.tags, args.sources)
    elif args.command == "update":
        update_wiki_timestamp(args.category, args.title)
    elif args.command == "list":
        list_wikis()
    elif args.command == "inspect":
        inspect_wiki()

if __name__ == "__main__":
    main()