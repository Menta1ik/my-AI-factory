# Release Notes v1.5.0-core

We are excited to introduce **v1.5.0-core** of the **My AI Factory** ecosystem! This release focuses on improving the stability of AI agent skill management under our **Zero-Dependency** philosophy, integrating modern execution environments (surfaces), and fixing critical issues in projecting and cleaning up installed skills.

---

## 🚀 Key Features

### 1. Support for Modern AI Surfaces
Added out-of-the-box integration and automated prompt deployment for cutting-edge coding agent platforms:
* **Claude Code** (the new powerful CLI developer tool by Anthropic)
* **OpenHands** (popular open-source software engineering agent platform)

All installed skills are now seamlessly projected and registered directly into these environments.

### 2. Advanced `vendor_as` & `subpath` Catalogs
Introduced support for complex monorepo configurations in `catalog.yaml`:
* Git subfolder filtering using the `subpath` directive (e.g., pulling only the necessary skill subfolder from a monorepo).
* Local cache sharing via the `vendor_as` directive, enabling multiple distinct skills to reuse a single repository clone, drastically saving time and disk footprint.

---

## 🛠 Bug Fixes & Stability Improvements

### 1. Critical Skill Removal Cleanup Fix (`cmd_remove`)
* **Problem**: Previously, when deleting a skill installed via `subpath` (like Anthropic's `canvas-design`), the installer looked for a directory matching the safe catalog name (`anthropics-skills-canvas-design`), whereas the actual folder on disk was named `canvas-design`. This left orphaned plugin files cluttering the coding surfaces.
* **Solution**: The `cmd_remove` engine in `factory.py` has been redesigned to resolve folder structures using `Path(subpath).name` alongside default slug options.
* **Outcome**: Safely cleanses **all 16 projection files and folders** across every supported surface (Cursor, Codex, OpenHands, OpenCode, Claude Code) without affecting other components.

### 2. Streamlined Catalog (`catalog.yaml`)
* Completely removed redundant office-related skills (`docx`, `pdf`, `pptx`, `xlsx`) and the experimental `skill-creator` generator tool.
* Retained and optimized robust developer integrations: Anthropic MCP Builder (`mcp-builder`), Canvas UI design guidelines (`canvas-design`), and the full suite of Vercel best practices.

---

## 🔒 Zero-Dependency Commitment
The `factory.py` core script remains strictly zero-dependency, relying exclusively on Python 3 standard library modules. YAML parsing, environment wiring, path routing, and configuration backups run instantly out-of-the-box in any environment.

---

## 🧪 Verification & Testing
* Successfully validated through end-to-end integration smoke tests using `tests/smoke_subpath.sh`.
* Verified robust projection cleanups via deep uninstallation verification scripts, guaranteeing stable execution.
