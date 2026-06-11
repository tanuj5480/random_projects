# Wiki Knowledge Base Schema Specification

This document defines the strict structure, taxonomy, and frontmatter validation layout required for all documents within the local AI Wiki Knowledge Base repository. All programmatic scripts and LLMs must adhere to this file schema to ensure workspace parsing capability (e.g., inside Obsidian or custom scripts).

---

## 1. Directory Structure

The repository splits data concerns into distinct lifecycles:

*   `knowledge_base/data_lake/`: **RAW INPUTS**. Unparsed research files, academic PDFs, and website HTML text dumps. (*Git ignored*).
*   `knowledge_base/staging/`: **INTERMEDIATE LAYER**. Raw text extracted from the data lake, cleaned and optimized for local LLM digestion. (*Git ignored*).
*   `knowledge_base/wiki/`: **PRODUCTION SYSTEM**. The finalized, linking Markdown knowledge graph. (*Tracked in Git*).

---

## 2. YAML Frontmatter Schema

Every markdown document (`.md`) residing inside the `wiki/` directory must start with a strictly formatted YAML frontmatter block bound by three hyphens (`---`).

### Mandatory Keys Matrix

| Key | Data Type | Requirement | Description / Valid Options |
| :--- | :--- | :--- | :--- |
| `title` | String | **Required** | The explicit name of the topic, wrapped in double quotes. |
| `type` | String | **Required** | Must be one of: `entity`, `concept`, `summary`, `overview`. |
| `created` | Date | **Required** | Page creation date following `YYYY-MM-DD` ISO format. |
| `updated` | Date | **Required** | Last modification date following `YYYY-MM-DD` ISO format. |
| `tags` | Array | **Required** | YAML sequence of tags. Use an empty array `[]` if none exist. |
| `sources` | Array | **Required** | List of raw file references or origins from the `data_lake`. |

### Target Validation Example

```yaml
---
title: "Quantum Computing Basics"
type: concept
created: 2026-06-11
updated: 2026-06-11
tags:
  - physics
  - computing
sources:
  - "arxiv_paper_2401.pdf"
---
```

---

## 3. Taxonomy Classification Definitions (`type`)

To maintain structural clarity, categorize your new wiki items using these four core system schemas:

1.  **`entity`**: A concrete, bounded item. (e.g., a specific software library, historical figure, research company, or hardware component).
2.  **`concept`**: Abstract framework theories, mathematical architectures, design paradigms, or core ideas. (e.g., *Quantum Superposition*, *RAG Architectures*).
3.  **`summary`**: A concise breakdown or executive brief of a singular source item. (e.g., a summary of a specific paper or chapter).
4.  **`overview`**: High-level structural landing hubs that bridge multiple concepts or domains together to form a birds-eye view.

---

## 4. Markdown Structural Schema

Directly beneath the closing frontmatter delimiter (`---`), the document body must use the following standard Markdown anatomy for formatting consistency:

```markdown
# [Title Match from Frontmatter]

## Summary
<!-- A 2 to 3 sentence macro breakdown of the file content context -->

## Key Concepts
- **[Concept Title 1]**: Bulleted crisp definitions provided by the LLM pipeline processing.
- **[Concept Title 2]**: Explanatory details.

## References
- List out linking elements, local file targets, or citation details.
```