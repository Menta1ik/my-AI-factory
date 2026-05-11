#!/usr/bin/env python3
"""
MY AI FACTORY — Smart Installer v1.0 (Python Edition)
Universal AI Environment for Gemini CLI, Claude Code, and Antigravity IDE.
"""

import os
import sys
import subprocess
import shutil
import csv
import re
import json
import argparse
from datetime import datetime
from pathlib import Path

# --- Configuration & Catalog ---

REPOS = [
    # (Name, URL, Package, Method)
    ("bmad-code-org/BMAD-METHOD", "https://github.com/bmad-code-org/BMAD-METHOD.git", "base", "npx"),
    ("vudovn/antigravity-kit", "https://github.com/vudovn/antigravity-kit.git", "base", "copy"),
    ("VoltAgent/awesome-agent-skills", "https://github.com/VoltAgent/awesome-agent-skills.git", "base", "copy"),
    ("vercel-labs/agent-browser", "https://github.com/vercel-labs/agent-browser.git", "base", "copy"),
    
    # Software Dev Pack
    ("nextlevelbuilder/ui-ux-pro-max-skill", "https://github.com/nextlevelbuilder/ui-ux-pro-max-skill.git", "software", "copy"),
    ("obra/superpowers", "https://github.com/obra/superpowers.git", "software", "copy"),
    ("coreyhaines31/marketingskills", "https://github.com/coreyhaines31/marketingskills.git", "software", "copy"),
    ("safishamsi/graphify", "https://github.com/safishamsi/graphify.git", "software", "copy"),
    ("pbakaus/impeccable", "https://github.com/pbakaus/impeccable.git", "software", "copy"),
    
    # Game Dev Pack
    ("bmad-code-org/bmad-module-game-dev-studio", "https://github.com/bmad-code-org/bmad-module-game-dev-studio.git", "gamedev", "npx"),
    ("Donchitos/Claude-Code-Game-Studios", "https://github.com/Donchitos/Claude-Code-Game-Studios.git", "gamedev", "copy"),
    ("JuliusBrussee/caveman", "https://github.com/JuliusBrussee/caveman.git", "gamedev", "copy"),
]

# --- UI Helpers ---

class UI:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    CYAN = '\033[0;36m'
    PURPLE = '\033[0;35m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

    theme_color = CYAN

    @classmethod
    def set_theme(cls, package):
        if package == "gamedev":
            cls.theme_color = cls.PURPLE
        else:
            cls.theme_color = cls.CYAN

    @classmethod
    def info(cls, msg): print(f"{cls.theme_color}i{cls.RESET}  {msg}")
    @classmethod
    def success(cls, msg): print(f"{UI.GREEN}✔{UI.RESET}  {msg}")
    @classmethod
    def warn(cls, msg): print(f"{UI.YELLOW}!{UI.RESET}  {msg}")
    @classmethod
    def error(cls, msg): print(f"{UI.RED}✘{UI.RESET}  {msg}")
    @classmethod
    def header(cls, msg): print(f"\n{UI.BOLD}{cls.theme_color}== {msg} =={UI.RESET}\n")
    @staticmethod
    def step(msg): print(f"  › {msg}")

# --- Core Logic ---

class Factory:
    def __init__(self, target_dir, package='software'):
        self.target_dir = Path(target_dir).resolve()
        self.package = package
        self.vendor_dir = self.target_dir / ".agent-vendor"
        self.agent_dir = self.target_dir / ".agent"
        self.skills_dir = self.agent_dir / "skills"
        self.claude_skills_dir = self.agent_dir / ".claude" / "skills"
        self.shared_dir = self.agent_dir / ".shared"
        self.bmad_config_dir = self.agent_dir / "_bmad" / "_config"
        UI.set_theme(package)

    def setup_dirs(self):
        UI.header(f"Creating Directory Structure ({self.package.upper()})")
        dirs = [self.vendor_dir, self.skills_dir, self.claude_skills_dir, self.shared_dir, self.agent_dir / "custom", self.agent_dir / "learned"]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
            UI.step(f"Ready: {d.relative_to(self.target_dir)}")

    def git_sync(self, name, url):
        dest = self.vendor_dir / name
        if (dest / ".git").exists():
            UI.step(f"Updating {name}...")
            subprocess.run(["git", "-C", str(dest), "pull", "--quiet"], check=False)
        else:
            UI.step(f"Cloning {name}...")
            subprocess.run(["git", "clone", "--depth=1", "--quiet", url, str(dest)], check=True)

    def run_npx_install(self, name, vendor_path=None):
        UI.info(f"Running BMAD installer for {name}...")
        try:
            # We add --tools claude-code to satisfy the installer's requirement for non-interactive mode
            cmd = ["npx", "bmad-method@latest", "install", "--directory", str(self.agent_dir), "--tools", "claude-code", "--yes"]
            if vendor_path:
                cmd += ["--custom-source", str(vendor_path)]
            subprocess.run(cmd, check=True)
            UI.success(f"{name} installed successfully")
        except subprocess.CalledProcessError:
            UI.error(f"Installer for {name} failed")

    def copy_skills(self):
        UI.header("Deploying Skills")
        for name, url, pkg, method in REPOS:
            if pkg != "base" and pkg != self.package and self.package != "full":
                continue
            
            src = self.vendor_dir / name
            if method == "copy":
                safe_name = name.replace("/", "-")
                dest = self.skills_dir / safe_name
                dest.mkdir(parents=True, exist_ok=True)
                
                UI.step(f"Copying {name} instructions...")
                for md_file in src.rglob("*.md"):
                    if "node_modules" in str(md_file): continue
                    shutil.copy2(md_file, dest / md_file.name)
                UI.success(f"{name} deployed to {dest.relative_to(self.target_dir)}")
            elif method == "npx":
                if name == "bmad-code-org/BMAD-METHOD":
                    self.run_npx_install(name)
                else:
                    self.run_npx_install(name, src)

    def integrate(self):
        UI.header("Smart Integration & Weaving")
        
        discovered_skills = []
        
        # 1. Scan for skills in .agent/skills/
        if self.skills_dir.exists():
            for skill_folder in self.skills_dir.iterdir():
                if not skill_folder.is_dir() or skill_folder.name.startswith("."):
                    continue
                
                # Find the main skill file (SKILL.md or README.md or first .md)
                skill_file = skill_folder / "SKILL.md"
                if not skill_file.exists():
                    skill_file = skill_folder / "README.md"
                if not skill_file.exists():
                    md_files = list(skill_folder.glob("*.md"))
                    if md_files: skill_file = md_files[0]
                
                if skill_file and skill_file.exists():
                    metadata = self.extract_metadata(skill_file)
                    discovered_skills.append({
                        "id": skill_folder.name,
                        "name": metadata.get("name", skill_folder.name),
                        "desc": metadata.get("description", "No description available."),
                        "path": skill_file
                    })

        # 2. Integrate with Claude Code (Symlinks)
        UI.info("Integrating with Claude Code...")
        for skill in discovered_skills:
            claude_skill_path = self.claude_skills_dir / skill["id"]
            claude_skill_path.mkdir(parents=True, exist_ok=True)
            target_link = claude_skill_path / "SKILL.md"
            if target_link.exists() or target_link.is_symlink():
                target_link.unlink()
            
            try:
                os.symlink(os.path.relpath(skill["path"], claude_skill_path), target_link)
                UI.step(f"Linked: {skill['id']} → Claude")
            except Exception:
                shutil.copy2(skill["path"], target_link)
                UI.step(f"Copied: {skill['id']} → Claude (fallback)")

        # 3. Integrate with BMAD (CSV Registration)
        if self.bmad_config_dir.exists():
            UI.info("Registering skills in BMAD manifests...")
            self.register_in_bmad(discovered_skills)

        # 4. Generate Instruction Files
        self.generate_configs(discovered_skills)

    def extract_metadata(self, file_path):
        content = file_path.read_text(errors='ignore')
        metadata = {}
        # Simple YAML frontmatter parser
        match = re.search(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if match:
            yaml_block = match.group(1)
            for line in yaml_block.split('\n'):
                if ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        k, v = parts
                        metadata[k.strip()] = v.strip().strip('"').strip("'")
        
        # Fallback to H1 for name
        if "name" not in metadata:
            h1_match = re.search(r'^#\s+(.*)', content, re.MULTILINE)
            if h1_match:
                metadata["name"] = h1_match.group(1).strip()
        
        return metadata

    def register_in_bmad(self, skills):
        manifest_path = self.bmad_config_dir / "skill-manifest.csv"
        help_path = self.bmad_config_dir / "bmad-help.csv"
        
        # Update skill-manifest.csv
        if manifest_path.exists():
            existing_ids = set()
            with open(manifest_path, 'r', newline='') as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                rows = list(reader)
                existing_ids = {row['canonicalId'] for row in rows}
            
            new_rows = []
            for s in skills:
                if s['id'] not in existing_ids:
                    new_rows.append({
                        "canonicalId": s['id'],
                        "name": s['id'],
                        "description": s['desc'],
                        "module": "external",
                        "path": f"skills/{s['id']}/{s['path'].name}"
                    })
            
            if new_rows:
                with open(manifest_path, 'a', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writerows(new_rows)
                UI.step(f"Added {len(new_rows)} skills to skill-manifest.csv")

        # Update bmad-help.csv
        if help_path.exists():
            with open(help_path, 'r', newline='') as f:
                reader = csv.reader(f)
                header_row = next(reader)
                rows = list(reader)
                existing_skills = {row[1] for row in rows}
            
            new_help_rows = []
            for s in skills:
                if s['id'] not in existing_skills:
                    new_help_rows.append([
                        "External", s['id'], s['name'], "EXT", s['desc'], "", "", "anytime", "", "", "false", "", ""
                    ])
            
            if new_help_rows:
                with open(help_path, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerows(new_help_rows)
                UI.step(f"Added {len(new_help_rows)} entries to bmad-help.csv")

    def generate_configs(self, skills):
        UI.info("Generating Environment Configs...")
        
        skill_catalog_md = "\n".join([f"- **{s['name']}** (`{s['id']}`): {s['desc']}" for s in skills])
        
        role_table = """| Role | When to use |
|---|---|
| **Analyst** | Requirements, research, user stories |
| **Architect** | System design, tech decisions |
| **Dev** | Feature implementation |
| **QA** | Testing, quality checks |"""

        if self.package == "gamedev":
            role_table += """
| **Game Designer** | Mechanics, GDD, balance, levels |
| **Art Director** | Visual style, UI/HUD, aesthetics |"""

        shared_body = f"""## Startup Instructions
1. Read `.agent/orchestrator.md` — your master guide.
2. Read `.agent/.shared/CONTEXT.md` — project status.
3. Check `.agent/.shared/TASKS.md` — active work.

## BMAD Roles
{role_table}

## Available Skills (External)
{skill_catalog_md}

## Example Prompts
- "Use the `{skills[0]['id'] if skills else 'ui-ux-pro-max'}` skill to analyze..."
- "Act as BMAD Game Designer and outline the core loop..."
"""

        # Environment Files
        (self.target_dir / "GEMINI.md").write_text(f"# My AI Factory — Gemini CLI ({self.package.upper()})\n\n{shared_body}")
        (self.target_dir / "CLAUDE.md").write_text(f"# My AI Factory — Claude Code ({self.package.upper()})\n\n{shared_body}")
        (self.target_dir / ".antigravity.md").write_text(f"# My AI Factory — Antigravity IDE ({self.package.upper()})\n\n{shared_body}")
        
        # Orchestrator
        orch_path = self.agent_dir / "orchestrator.md"
        orch_content = f"""# Master Orchestrator ({self.package.upper()})
This project uses a multi-agent ecosystem.

## Protocols
- **Roleplay**: Adopt BMAD roles.
- **Context**: Always check `.agent/.shared/CONTEXT.md`.
- **Memory**: Update `.agent/.shared/TASKS.md` and `DECISIONS.md`.

## BMAD Roles
{role_table}

## Skill Catalog
### External Skills
{skill_catalog_md}
"""
        orch_path.write_text(orch_content)
        UI.success("All configuration files generated")

    def create_shared_placeholders(self):
        ctx_body = "# Project Context\n\n## Description\nInitial setup."
        if self.package == "gamedev":
            ctx_body += "\n\n## Game Design Document (GDD)\n- Core Loop: \n- Mechanics: \n- Setting: "
        
        (self.shared_dir / "CONTEXT.md").write_text(ctx_body)
        (self.shared_dir / "TASKS.md").write_text("# Task Queue\n\n- [ ] Initial project audit\n- [ ] Define core architecture")
        (self.shared_dir / "DECISIONS.md").write_text("# Architectural Decisions\n\n| Date | Decision | Rationale |\n|---|---|---|")

def main():
    parser = argparse.ArgumentParser(description="My AI Factory Installer")
    parser.add_argument("action", choices=["install", "update", "integrate"], nargs="?", default="install", help="Action to perform")
    parser.add_argument("--package", choices=["software", "gamedev", "full"], help="Package to install")
    args = parser.parse_args()

    UI.header("WELCOME TO MY AI FACTORY v3.0")
    
    package = args.package
    if not package and args.action == "install":
        print(f"  {UI.BOLD}Select your target environment:{UI.RESET}")
        print(f"  1) {UI.CYAN}Software Dev{UI.RESET} (Web, APIs, SaaS, Platforms)")
        print(f"  2) {UI.PURPLE}Game Dev{UI.RESET}     (Unity, Godot, Mechanics, GDD)")
        print(f"  3) {UI.BOLD}Full Pack{UI.RESET}    (Everything combined)")
        blank = input(f"\n  Choose [1/2/3, default: 1]: ").strip()
        if blank == "2": package = "gamedev"
        elif blank == "3": package = "full"
        else: package = "software"

    factory = Factory(os.getcwd(), package=package or "software")

    if args.action == "install":
        factory.setup_dirs()
        UI.header("Syncing Repositories")
        for name, url, pkg, method in REPOS:
            if pkg == "base" or pkg == factory.package or factory.package == "full":
                factory.git_sync(name, url)
        # BMAD Core and Modules
        factory.copy_skills()
        factory.create_shared_placeholders()
        factory.integrate()
        UI.success(f"INSTALLATION COMPLETE ({factory.package.upper()})")
        
        print(f"\n  {UI.BOLD}Next Steps:{UI.RESET}")
        print(f"  1. Open GEMINI.md or CLAUDE.md to see your new instructions.")
        print(f"  2. Describe your project in .agent/.shared/CONTEXT.md")
        print(f"  3. Start a session by saying: 'Read .agent/orchestrator.md and start'")
        print("")

if __name__ == "__main__":
    main()
