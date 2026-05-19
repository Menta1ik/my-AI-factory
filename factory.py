#!/usr/bin/env python3
"""
MY AI FACTORY — Smart Installer (Python Edition)
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
import time
import threading
import itertools
from pathlib import Path

VERSION = "1.3.0-core"

CATALOG_FILE = "catalog.yaml"

# --- Minimal YAML loader (zero deps) ---
# Supports only what catalog.yaml needs: mappings, lists of mappings,
# scalars, inline arrays `[a, b]`. Indentation = 2 spaces. No anchors,
# no multiline strings, no flow mappings. Comments (#) and blank lines ignored.

def _parse_scalar(value: str):
    value = value.strip()
    if not value:
        return ""
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(p) for p in inner.split(",")]
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    if value.lower() in ("null", "~"):
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value

def load_yaml(path: Path):
    """Tiny YAML loader: just enough for our catalog schema."""
    lines = []
    for raw in path.read_text().splitlines():
        stripped = raw.split("#", 1)[0].rstrip()
        if stripped.strip():
            lines.append(stripped)

    def indent_of(s: str) -> int:
        return len(s) - len(s.lstrip(" "))

    def parse_block(start: int, base_indent: int):
        """Returns (value, next_index). value is dict or list depending on first child."""
        if start >= len(lines):
            return None, start

        first = lines[start]
        cur_indent = indent_of(first)
        if cur_indent < base_indent:
            return None, start

        is_list = first.lstrip().startswith("- ")
        result = [] if is_list else {}
        i = start

        while i < len(lines):
            line = lines[i]
            ind = indent_of(line)
            if ind < cur_indent:
                break
            if ind > cur_indent:
                i += 1
                continue

            content = line.lstrip()

            if is_list:
                if not content.startswith("- "):
                    break
                item_body = content[2:]
                if ":" in item_body and not item_body.startswith("["):
                    key, _, val = item_body.partition(":")
                    item = {key.strip(): _parse_scalar(val)}
                    j = i + 1
                    while j < len(lines) and indent_of(lines[j]) > cur_indent:
                        sub = lines[j]
                        sub_ind = indent_of(sub)
                        if sub_ind == cur_indent + 2:
                            sub_content = sub.lstrip()
                            if ":" in sub_content:
                                k, _, v = sub_content.partition(":")
                                v = v.strip()
                                if v:
                                    item[k.strip()] = _parse_scalar(v)
                                else:
                                    nested, j2 = parse_block(j + 1, cur_indent + 4)
                                    item[k.strip()] = nested
                                    j = j2
                                    continue
                        j += 1
                    result.append(item)
                    i = j
                else:
                    result.append(_parse_scalar(item_body))
                    i += 1
            else:
                if ":" not in content:
                    break
                key, _, val = content.partition(":")
                val = val.strip()
                if val:
                    result[key.strip()] = _parse_scalar(val)
                    i += 1
                else:
                    nested, j = parse_block(i + 1, cur_indent + 2)
                    result[key.strip()] = nested
                    i = j

        return result, i

    data, _ = parse_block(0, 0)
    return data or {}

def load_catalog(start_dir: Path):
    """Find catalog.yaml next to factory.py, parse it, expand presets, return REPOS-shaped tuples."""
    catalog_path = Path(__file__).resolve().parent / CATALOG_FILE
    if not catalog_path.exists():
        raise FileNotFoundError(f"Catalog not found: {catalog_path}")
    data = load_yaml(catalog_path)
    repos = data.get("repos", [])
    presets = data.get("presets", {})
    return repos, presets

def repos_for_package(repos, presets, package):
    """Return [(name, url, primary_tag, method), ...] filtered for the given preset."""
    allowed_tags = set(presets.get(package, []))
    result = []
    for r in repos:
        tags = r.get("tags", []) or []
        if not allowed_tags or any(t in allowed_tags for t in tags):
            primary = "base" if "base" in tags else (tags[0] if tags else "software")
            result.append((r["name"], r["url"], primary, r.get("method", "copy")))
    return result

# --- UI Engine (Pure Gemini CLI Style) ---

class UI:
    # Colors
    CYAN = '\033[38;5;81m'
    GREY = '\033[38;5;242m'
    WHITE = '\033[38;5;255m'
    SUCCESS = '\033[38;5;78m'
    WARN = '\033[38;5;214m'
    ERROR = '\033[38;5;197m'
    BOLD = '\033[1m'
    RESET = '\033[0m'
    
    # Extended Palette
    MAGENTA = '\033[38;5;141m'
    GOLD = '\033[38;5;220m'

    theme_color = CYAN

    @classmethod
    def set_theme(cls, package):
        if package == "gamedev": cls.theme_color = cls.MAGENTA
        elif package == "full": cls.theme_color = cls.GOLD
        else: cls.theme_color = cls.CYAN

    @classmethod
    def typewriter(cls, text, delay=0.05):
        for char in text:
            sys.stdout.write(char)
            sys.stdout.flush()
            time.sleep(delay)
        sys.stdout.write("\n")

    @classmethod
    def banner(cls):
        print("\n")
        sys.stdout.write(f"   {cls.theme_color}{cls.BOLD}")
        cls.typewriter("███    ███  █████  ███     ███   █████   ███   ████   █   █", delay=0.005)
        cls.typewriter("   █   █   █   █      █   █  █        █    █   █  █   █   █ █ ", delay=0.005)
        cls.typewriter("   █████   █   ████   █████  █        █    █   █  ████     █  ", delay=0.005)
        cls.typewriter("   █   █   █   █      █   █  █        █    █   █  █  █     █  ", delay=0.005)
        cls.typewriter("   █   █  ███  █      █   █   ███     █     ███   █   █    █  ", delay=0.005)
        print(f"{cls.RESET}")
        print(f"   {cls.GREY}───────────────────────────────────────────────────────────{cls.RESET}")
        print(f"   {cls.GREY}  Cognitive Architecture Deployment Engine │ v{VERSION}{cls.RESET}")
        print(f"   {cls.GREY}───────────────────────────────────────────────────────────{cls.RESET}\n")
        time.sleep(0.4)

    @classmethod
    def system_info(cls):
        import platform
        info = f"System: {platform.system()} | {platform.release()} | Python {sys.version.split()[0]}"
        print(f"   {cls.GREY}󰋜 {info}{cls.RESET}\n")
        time.sleep(0.3)

    @classmethod
    def header(cls, msg):
        print(f"\n   {cls.theme_color}●{cls.RESET} {cls.BOLD}{cls.WHITE}{msg.upper()}{cls.RESET}")
        time.sleep(0.3)

    @classmethod
    def step(cls, msg, status="pending"):
        icon = f"{cls.theme_color}●{cls.RESET}" if status == "done" else f"{cls.GREY}○{cls.RESET}"
        print(f"   {cls.GREY}│{cls.RESET}  {icon} {msg}")
        time.sleep(0.05)

    @classmethod
    def info(cls, msg):
        print(f"   {cls.GREY}│{cls.RESET}  {msg}")

    @classmethod
    def success(cls, msg):
        print(f"   {cls.GREY}│{cls.RESET}  {cls.SUCCESS}✔ {msg}{cls.RESET}")
        time.sleep(0.1)

    @classmethod
    def warn(cls, msg):
        print(f"   {cls.GREY}│{cls.RESET}  {cls.WARN}⚠ {msg}{cls.RESET}")

    @classmethod
    def error(cls, msg):
        print(f"   {cls.GREY}│{cls.RESET}  {cls.ERROR}✘ {msg}{cls.RESET}")

    @classmethod
    def prompt_header(cls, msg):
        print(f"   {cls.GREY}┌{cls.RESET} {cls.BOLD}{msg}{cls.RESET}")

    @classmethod
    def prompt_option(cls, key, msg, color=None):
        c = color if color else cls.WHITE
        print(f"   {cls.GREY}│{cls.RESET} {key}. {c}{msg}{cls.RESET}")

    @classmethod
    def prompt_footer(cls):
        print(f"   {cls.GREY}└{cls.RESET}")

    @classmethod
    def prompt_input(cls, msg):
        return input(f"\n   {cls.theme_color}❯{cls.RESET} {cls.BOLD}{msg}{cls.RESET} ")

class Spinner:
    def __init__(self, message="Processing"):
        self.message = message
        self.spinner = itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'])
        self.stop_running = threading.Event()
        self.spin_thread = None

    def _spin(self):
        while not self.stop_running.is_set():
            sys.stdout.write(f"\r   {UI.GREY}│{UI.RESET}  {UI.theme_color}{next(self.spinner)}{UI.RESET} {self.message}...")
            sys.stdout.flush()
            time.sleep(0.1)

    def __enter__(self):
        self.spin_thread = threading.Thread(target=self._spin)
        self.spin_thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_running.set()
        self.spin_thread.join()
        sys.stdout.write("\r\033[K")

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
        self.catalog_repos, self.presets = load_catalog(self.target_dir)
        self.subpaths = {r["name"]: r["subpath"] for r in self.catalog_repos if r.get("subpath")}
        self.config_path = self.target_dir / "factory.config.json"
        self.config = self._load_config()
        self.lock_path = self.target_dir / "factory.lock.json"
        self.lock = self._load_lock()
        self.repos = self._resolve_repos()
        UI.set_theme(package)

    def _load_config(self) -> dict:
        if self.config_path.exists():
            try:
                return json.loads(self.config_path.read_text())
            except json.JSONDecodeError:
                UI.warn("factory.config.json is corrupt — treating as empty")
        return {"preset": self.package, "extras": [], "excluded": []}

    def _save_config(self):
        self.config_path.write_text(json.dumps(self.config, indent=2, ensure_ascii=False) + "\n")

    def _resolve_repos(self):
        """Combine preset + extras − excluded into the final repo list."""
        preset = self.config.get("preset", self.package)
        base = repos_for_package(self.catalog_repos, self.presets, preset)
        base_names = {r[0] for r in base}

        catalog_by_name = {r["name"]: r for r in self.catalog_repos}
        for name in self.config.get("extras", []):
            if name in base_names: continue
            r = catalog_by_name.get(name)
            if not r:
                UI.warn(f"Extra '{name}' is not in catalog.yaml — skipped")
                continue
            tags = r.get("tags", []) or []
            primary = "base" if "base" in tags else (tags[0] if tags else "software")
            base.append((r["name"], r["url"], primary, r.get("method", "copy")))

        excluded = set(self.config.get("excluded", []))
        return [r for r in base if r[0] not in excluded]

    def _load_lock(self) -> dict:
        if self.lock_path.exists():
            try:
                return json.loads(self.lock_path.read_text())
            except json.JSONDecodeError:
                UI.warn(f"factory.lock.json is corrupt — treating as empty")
                return {}
        return {}

    def _save_lock(self):
        from datetime import datetime
        payload = {
            "version": VERSION,
            "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "repos": self.lock.get("repos", {}),
        }
        self.lock = payload
        self.lock_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")

    def cmd_list(self):
        UI.header("Skill Catalog")
        installed_names = {r[0] for r in self.repos}
        preset = self.config.get("preset", self.package)
        UI.info(f"Preset: {preset}    Extras: {len(self.config.get('extras', []))}    Excluded: {len(self.config.get('excluded', []))}")
        print("")
        for r in self.catalog_repos:
            name = r["name"]
            tags = ", ".join(r.get("tags", []) or [])
            desc = r.get("description", "")
            mark = f"{UI.SUCCESS}●{UI.RESET}" if name in installed_names else f"{UI.GREY}○{UI.RESET}"
            print(f"   {mark} {UI.BOLD}{name}{UI.RESET}  {UI.GREY}[{tags}]{UI.RESET}")
            if desc:
                print(f"     {UI.GREY}{desc}{UI.RESET}")
        print("")

    def cmd_add(self, name: str):
        UI.header(f"Adding {name}")
        catalog_by_name = {r["name"]: r for r in self.catalog_repos}
        if name not in catalog_by_name:
            UI.error(f"'{name}' not found in catalog.yaml")
            UI.info("Run `factory.py list` to see available names.")
            return
        if name in (r[0] for r in self.repos):
            UI.info(f"{name} is already enabled by the current preset.")
            return

        excluded = self.config.setdefault("excluded", [])
        if name in excluded:
            excluded.remove(name)
        extras = self.config.setdefault("extras", [])
        if name not in extras:
            extras.append(name)

        self._save_config()
        self.repos = self._resolve_repos()

        r = catalog_by_name[name]
        self.setup_dirs()
        UI.header("Synchronizing")
        self.git_sync(r["name"], r["url"], respect_lock=False)
        self._save_lock()
        self.copy_skills()
        self.integrate()
        UI.success(f"{name} added")

    def cmd_remove(self, name: str):
        UI.header(f"Removing {name}")
        catalog_by_name = {r["name"]: r for r in self.catalog_repos}
        if name not in catalog_by_name:
            UI.error(f"'{name}' not found in catalog.yaml")
            return
        if name not in (r[0] for r in self.repos):
            UI.warn(f"{name} is not currently enabled.")
            return

        extras = self.config.setdefault("extras", [])
        excluded = self.config.setdefault("excluded", [])
        if name in extras:
            extras.remove(name)
        else:
            if name not in excluded:
                excluded.append(name)

        self._save_config()
        self.repos = self._resolve_repos()

        vendor_path = self.vendor_dir / name
        if vendor_path.exists():
            shutil.rmtree(vendor_path, ignore_errors=True)
        if self.lock.get("repos", {}).get(name):
            del self.lock["repos"][name]
            self._save_lock()

        safe_name = name.replace("/", "-")
        skill_path = self.skills_dir / safe_name
        if skill_path.exists():
            shutil.rmtree(skill_path, ignore_errors=True)

        self.integrate()
        UI.success(f"{name} removed")

    PROJECT_TEMPLATES = {
        "saas": {
            "mission": "Build a SaaS product with subscriptions, user accounts, and a usage-based pricing tier.",
            "stack_hint": "Frontend, backend API, auth, billing (Stripe), email, analytics.",
            "starter_tasks": [
                "Define core user persona and primary jobs-to-be-done",
                "Pick auth provider (Auth0/Clerk/Supabase/self-hosted)",
                "Design pricing tiers and decide on free-trial vs freemium",
                "Set up landing page with waitlist signup",
                "Wire up Stripe with at least one paid plan end-to-end",
            ],
        },
        "mobile": {
            "mission": "Ship a mobile app for iOS and Android with offline-first capabilities.",
            "stack_hint": "React Native / Flutter / native, deep linking, push notifications, App Store assets.",
            "starter_tasks": [
                "Decide on cross-platform vs native per platform",
                "Define minimum supported OS versions",
                "Sketch onboarding flow (5 screens max)",
                "Set up TestFlight + Play Console internal track",
                "Implement offline-first data sync for the core feature",
            ],
        },
        "game": {
            "mission": "Ship a game with a tight core loop, polished feel, and a clear monetization path.",
            "stack_hint": "Engine (Unity/Godot/Unreal), art pipeline, sound, balancing spreadsheet, store pages.",
            "starter_tasks": [
                "Write a one-page Game Design Document focused on the core loop",
                "Prototype the core mechanic in under 1 week as a greybox",
                "Decide on art direction and reference board",
                "Plan first playtest with 5 strangers",
                "Pick monetization model: premium / F2P / paid + DLC",
            ],
        },
        "marketing": {
            "mission": "Run a marketing site / launch campaign with measurable lead generation.",
            "stack_hint": "Landing page, SEO content, email capture, analytics, paid acquisition.",
            "starter_tasks": [
                "Define ICP and core value proposition in one sentence",
                "Write 3 landing page variations to A/B test",
                "Plan first 10 SEO articles around long-tail keywords",
                "Set up email capture with confirmed double opt-in",
                "Define week-1 KPIs: visits, signups, CAC",
            ],
        },
        "content": {
            "mission": "Build a content/publication site that compounds organic traffic over 12 months.",
            "stack_hint": "Static site, CMS, RSS, newsletter, search, comments, distribution.",
            "starter_tasks": [
                "Pick CMS (Notion/Sanity/Markdown-in-git)",
                "Define editorial calendar and posting cadence",
                "Set up analytics with a privacy-friendly provider",
                "Build email newsletter with auto-archive",
                "Plan distribution: Twitter, HN, niche communities",
            ],
        },
    }

    def cmd_init(self, project_type: str):
        UI.header(f"Initializing {project_type} project")
        tpl = self.PROJECT_TEMPLATES.get(project_type)
        if not tpl:
            UI.error(f"Unknown type '{project_type}'. Available: {', '.join(self.PROJECT_TEMPLATES)}")
            return

        self.setup_dirs()

        context_md = (
            f"# Project Context\n\n"
            f"## Mission\n{tpl['mission']}\n\n"
            f"## Stack Notes\n{tpl['stack_hint']}\n\n"
            f"## North-Star Metric\n_TODO: define the single number that proves the product is working._\n\n"
            f"## Constraints\n- Solo / small team\n- _TODO: budget, timeline, hard deadlines_\n\n"
            f"## Decisions log\nSee `.agent/.shared/DECISIONS.md`.\n"
        )
        (self.shared_dir / "CONTEXT.md").write_text(context_md)

        tasks_lines = "\n".join(f"- [ ] {t}" for t in tpl["starter_tasks"])
        (self.shared_dir / "TASKS.md").write_text(f"# Production Queue\n\n{tasks_lines}\n")

        if not (self.shared_dir / "DECISIONS.md").exists():
            (self.shared_dir / "DECISIONS.md").write_text("# Decision Ledger\n")

        UI.success(f"Seeded CONTEXT.md, TASKS.md ({len(tpl['starter_tasks'])} starter tasks)")
        UI.info(f"Next: `factory.py install` to bring in skills.")

    def cmd_doctor(self):
        UI.header("Factory Doctor")
        issues = 0

        # 1. External tools
        for tool in ["git", "npx", "pip3"]:
            if shutil.which(tool):
                UI.success(f"{tool}: found")
            else:
                UI.warn(f"{tool}: not in PATH (some installs will fail)")
                issues += 1

        # 2. Catalog repos vs vendor
        for name, url, pkg, method in self.repos:
            vendor_path = self.vendor_dir / name
            if not vendor_path.exists():
                UI.warn(f"{name}: enabled but not cloned — run `install`")
                issues += 1

        # 3. Lockfile coverage
        locked = self.lock.get("repos", {})
        enabled_names = {r[0] for r in self.repos}
        for name in enabled_names:
            if name not in locked:
                UI.warn(f"{name}: missing from factory.lock.json")
                issues += 1

        # 4. Symlinks in .claude/skills
        if self.claude_skills_dir.exists():
            broken = 0
            for skill_dir in self.claude_skills_dir.iterdir():
                link = skill_dir / "SKILL.md"
                if link.is_symlink() and not link.exists():
                    UI.warn(f"Broken symlink: {link.relative_to(self.target_dir)}")
                    broken += 1
            if broken:
                issues += broken
                UI.info(f"  → run `factory.py integrate` to rebuild links")
            else:
                UI.success(".claude/skills: symlinks OK")

        # 5. Duplicate IDs between custom/ and agents/
        custom_dir = self.agent_dir / "custom"
        agents_dir = self.agent_dir / "agents"
        if custom_dir.exists() and agents_dir.exists():
            custom_ids = {p.stem for p in custom_dir.glob("*.md")}
            agent_ids = {p.stem for p in agents_dir.glob("*.md")}
            overrides = custom_ids & agent_ids
            if overrides:
                UI.info(f"Custom overrides active: {', '.join(sorted(overrides))}")

        # 6. Vendor size
        if self.vendor_dir.exists():
            total = 0
            for p in self.vendor_dir.rglob("*"):
                try:
                    if p.is_file():
                        total += p.stat().st_size
                except OSError:
                    pass
            mb = total / (1024 * 1024)
            UI.info(f"Vendor footprint: {mb:.1f} MB at {self.vendor_dir.relative_to(self.target_dir)}")

        print("")
        if issues == 0:
            UI.success("All checks passed.")
        else:
            UI.warn(f"{issues} issue(s) found — see above.")
        print("")

    def _git_head_sha(self, repo_path: Path) -> str | None:
        try:
            out = subprocess.run(
                ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
                capture_output=True, text=True, check=True,
            )
            return out.stdout.strip()
        except (FileNotFoundError, subprocess.CalledProcessError):
            return None

    def setup_dirs(self):
        UI.header("Initializing Environment")
        dirs = [
            self.vendor_dir, 
            self.skills_dir, 
            self.claude_skills_dir, 
            self.shared_dir, 
            self.agent_dir / "custom", 
            self.agent_dir / "learned",
            self.agent_dir / "agents",
            self.agent_dir / "workflows",
            self.agent_dir / "tools",
            self.agent_dir / "rules"
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
            UI.step(f"Mapped: {d.relative_to(self.target_dir)}", status="done")

    def git_sync(self, name, url, respect_lock=True):
        """Clone or update a repo. If respect_lock and lock has a pinned SHA, checkout that SHA."""
        dest = self.vendor_dir / name
        locked_sha = (self.lock.get("repos", {}) or {}).get(name, {}).get("sha") if respect_lock else None

        msg = f"Syncing {name}" if (dest / ".git").exists() else f"Cloning {name}"
        with Spinner(msg):
            if (dest / ".git").exists():
                if locked_sha:
                    subprocess.run(["git", "-C", str(dest), "fetch", "--quiet", "--depth=1", "origin", locked_sha], check=False)
                    subprocess.run(["git", "-C", str(dest), "checkout", "--quiet", locked_sha], check=False)
                else:
                    subprocess.run(["git", "-C", str(dest), "pull", "--quiet", "--ff-only"], check=False)
            else:
                if locked_sha:
                    # Need full history to checkout an arbitrary SHA.
                    subprocess.run(["git", "clone", "--quiet", url, str(dest)], check=True)
                    subprocess.run(["git", "-C", str(dest), "checkout", "--quiet", locked_sha], check=False)
                else:
                    subprocess.run(["git", "clone", "--depth=1", "--quiet", url, str(dest)], check=True)

        sha = self._git_head_sha(dest)
        if sha:
            self.lock.setdefault("repos", {})[name] = {"url": url, "sha": sha}
            short = sha[:7]
            UI.success(f"{name} @ {short}")
        else:
            UI.success(f"{name} synchronized")

    def run_npx_install(self, name, vendor_path=None):
        error_detail = None
        with Spinner(f"Installing {name}"):
            cmd = ["npx", "bmad-method@latest", "install", "--directory", str(self.agent_dir), "--tools", "claude-code", "--yes"]
            if vendor_path: cmd += ["--custom-source", str(vendor_path)]
            try:
                subprocess.run(cmd, check=True, capture_output=True, text=True)
                success = True
            except FileNotFoundError:
                success = False
                error_detail = "npx not found in PATH"
            except subprocess.CalledProcessError as e:
                success = False
                error_detail = (e.stderr or e.stdout or "").strip().splitlines()[-1] if (e.stderr or e.stdout) else f"exit {e.returncode}"

        if success:
            UI.success(f"{name} deployed")
        else:
            UI.error(f"{name} failed: {error_detail}")

    def _ensure_venv(self) -> Path | None:
        """Create .agent-vendor/.venv if missing; return its python interpreter path."""
        venv_dir = self.vendor_dir / ".venv"
        py = venv_dir / "bin" / "python"
        if py.exists():
            return py
        try:
            subprocess.run(
                [sys.executable, "-m", "venv", str(venv_dir)],
                check=True, capture_output=True, text=True,
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            return None
        return py if py.exists() else None

    def run_pip_install(self, name, vendor_path):
        in_venv = sys.prefix != sys.base_prefix

        def _attempt(pip_cmd):
            try:
                subprocess.run(pip_cmd, check=True, capture_output=True, text=True)
                return True, None, ""
            except FileNotFoundError:
                return False, f"{pip_cmd[0]} not found in PATH", ""
            except subprocess.CalledProcessError as e:
                full = (e.stderr or "") + (e.stdout or "")
                tail = full.strip().splitlines()
                short = tail[-1] if tail else f"exit {e.returncode}"
                return False, short, full

        with Spinner(f"Installing {name} via pip"):
            success, error_detail, full_out = _attempt(["pip3", "install", "-e", str(vendor_path)])

            # PEP 668: system Python rejects pip installs on macOS / modern Linux.
            # Fall back to an isolated venv inside the factory's vendor dir.
            if not success and not in_venv and "externally-managed" in full_out:
                venv_py = self._ensure_venv()
                if venv_py:
                    success, error_detail, _ = _attempt([str(venv_py), "-m", "pip", "install", "-e", str(vendor_path)])
                    if success:
                        error_detail = f"installed into isolated venv at {venv_py.parent.parent.relative_to(self.target_dir)}"

        if success:
            UI.success(f"{name} deployed via pip")
            if error_detail:
                UI.info(error_detail)
        else:
            UI.error(f"{name} pip install failed: {error_detail}")

    def copy_skills(self):
        UI.header("Deploying Assets")
        SKIP_FILES = {"CHANGELOG.md", "CONTRIBUTING.md", "LICENSE.md", "CODE_OF_CONDUCT.md", "SECURITY.md", "README.npm.md"}
        import filecmp
        from datetime import datetime

        def safe_copy(src, dst, *, follow_symlinks=True):
            dst_path = Path(dst)
            if dst_path.exists() and dst_path.is_file():
                if not filecmp.cmp(src, dst, shallow=False):
                    date_str = datetime.now().strftime("%Y-%m-%d")
                    backup_base = self.vendor_dir / ".backups" / date_str
                    try:
                        rel_path = dst_path.relative_to(self.agent_dir)
                        backup_path = backup_base / rel_path
                        backup_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(dst, backup_path)
                    except ValueError:
                        pass
            return shutil.copy2(src, dst, follow_symlinks=follow_symlinks)

        target_agents_md = self.agent_dir / "AGENTS.md"
        if target_agents_md.exists():
            target_agents_md.unlink()

        for name, url, pkg, method in self.repos:
            src = self.vendor_dir / name
            subpath = self.subpaths.get(name)
            if method == "copy":
                UI.step(f"Injecting {name}")

                # Subpath mode: the catalog points to a specific skill folder inside the repo.
                # Copy that folder as a single skill — no smart-routing, no full-repo .md scan.
                if subpath:
                    src_skill = src / subpath
                    if not src_skill.exists():
                        UI.error(f"{name}: subpath '{subpath}' not found in repo")
                        continue
                    skill_id = src_skill.name
                    dest = self.skills_dir / skill_id
                    dest.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(src_skill, dest, dirs_exist_ok=True, copy_function=safe_copy, symlinks=False)
                    UI.success(f"Module Ready: {name} → {skill_id}")
                    continue

                # Smart routing for both .agent structure and flat repositories
                base_dirs_to_check = [src, src / ".agent"]
                routed_dirs: set[Path] = set()
                routed_files: set[Path] = set()

                for base_dir in base_dirs_to_check:
                    if not base_dir.exists(): continue

                    for folder in ["agents", "workflows", "flows", "rules", "tools", "skills"]:
                        src_folder = base_dir / folder
                        if src_folder.exists() and src_folder.is_dir():
                            dest_folder = self.agent_dir / folder
                            shutil.copytree(src_folder, dest_folder, dirs_exist_ok=True, copy_function=safe_copy, symlinks=False)
                            routed_dirs.add(src_folder.resolve())

                # Handle AGENTS.md merging
                for base_dir in base_dirs_to_check:
                    agents_md = base_dir / "AGENTS.md"
                    if agents_md.exists():
                        if target_agents_md.exists():
                            with open(target_agents_md, "a") as f:
                                f.write("\n\n" + agents_md.read_text(errors='ignore'))
                        else:
                            shutil.copy2(agents_md, target_agents_md)
                        routed_files.add(agents_md.resolve())

                # Fallback: copy remaining .md files to skills
                safe_name = name.replace("/", "-")
                dest = self.skills_dir / safe_name
                dest.mkdir(parents=True, exist_ok=True)

                md_files_copied = 0
                for md_file in src.rglob("*.md"):
                    if "node_modules" in str(md_file): continue
                    if md_file.name in SKIP_FILES or md_file.name.upper() in SKIP_FILES: continue

                    resolved = md_file.resolve()
                    if resolved in routed_files: continue
                    if any(resolved.is_relative_to(d) for d in routed_dirs): continue

                    safe_copy(md_file, dest / md_file.name)
                    md_files_copied += 1

                # Cleanup empty fallback directory
                if md_files_copied == 0:
                    try:
                        dest.rmdir()
                    except OSError:
                        pass
                
                UI.success(f"Module Ready: {name}")
            elif method == "npx":
                if name == "bmad-code-org/BMAD-METHOD": self.run_npx_install(name)
                else: self.run_npx_install(name, src)
            elif method == "pip":
                self.run_pip_install(name, src)

    def integrate(self):
        UI.header("Synthesizing Neural Links")
        
        discovered_skills = []
        seen_ids = set()

        # 1. User Space: Custom Agents (Highest Priority)
        # 2. Managed Space: Downloaded Agents
        for folder in ["custom", "agents"]:
            agent_dir = self.agent_dir / folder
            if agent_dir.exists():
                for agent_file in agent_dir.glob("*.md"):
                    agent_id = agent_file.stem
                    if agent_id not in seen_ids:
                        seen_ids.add(agent_id)
                        metadata = self.extract_metadata(agent_file)
                        discovered_skills.append({
                            "id": agent_id,
                            "name": metadata.get("name", agent_id.replace("-", " ").title()),
                            "desc": metadata.get("description", "Specialized Agent Persona"),
                            "path": agent_file
                        })

        # 3. Fallback: Skills Directory
        if self.skills_dir.exists():
            for skill_folder in self.skills_dir.iterdir():
                if not skill_folder.is_dir() or skill_folder.name.startswith("."): continue
                
                skill_id = skill_folder.name
                if skill_id in seen_ids: continue
                
                skill_file = skill_folder / "SKILL.md"
                if not skill_file.exists(): skill_file = skill_folder / "README.md"
                if not skill_file.exists():
                    md_files = list(skill_folder.glob("*.md"))
                    if md_files: skill_file = md_files[0]
                
                if skill_file and skill_file.exists():
                    seen_ids.add(skill_id)
                    metadata = self.extract_metadata(skill_file)
                    discovered_skills.append({
                        "id": skill_id,
                        "name": metadata.get("name", skill_folder.name),
                        "desc": metadata.get("description", "No description available."),
                        "path": skill_file
                    })

        with Spinner("Building Claude Code bridge"):
            for skill in discovered_skills:
                claude_skill_path = self.claude_skills_dir / skill["id"]
                claude_skill_path.mkdir(parents=True, exist_ok=True)
                target_link = claude_skill_path / "SKILL.md"
                if target_link.exists() or target_link.is_symlink(): target_link.unlink()
                try: os.symlink(os.path.relpath(skill["path"], claude_skill_path), target_link)
                except: shutil.copy2(skill["path"], target_link)
        UI.success("Neural Bridge: Online")

        if self.bmad_config_dir.exists():
            with Spinner("Registering in BMAD Core"):
                self.register_in_bmad(discovered_skills)
            UI.success("Manifests: Updated")

        self.generate_configs(discovered_skills)

    def extract_metadata(self, file_path):
        content = file_path.read_text(errors='ignore')
        metadata = {}
        match = re.search(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if match:
            yaml_block = match.group(1)
            for line in yaml_block.split('\n'):
                if ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        k, v = parts
                        metadata[k.strip()] = v.strip().strip('"').strip("'")
        if "name" not in metadata:
            h1_match = re.search(r'^#\s+(.*)', content, re.MULTILINE)
            if h1_match: metadata["name"] = h1_match.group(1).strip()
        return metadata

    def register_in_bmad(self, skills):
        manifest_path = self.bmad_config_dir / "skill-manifest.csv"
        help_path = self.bmad_config_dir / "bmad-help.csv"
        
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

    FACTORY_BEGIN = "<!-- AI-FACTORY:BEGIN — managed block, edits outside markers are preserved -->"
    FACTORY_END = "<!-- AI-FACTORY:END -->"

    def _write_managed_config(self, path: Path, title: str, body: str):
        """Write a config file, preserving any user-authored text outside the managed markers."""
        managed_block = f"{self.FACTORY_BEGIN}\n# {title}\n\n{body}\n{self.FACTORY_END}\n"

        if path.exists():
            existing = path.read_text(errors='ignore')
            if self.FACTORY_BEGIN in existing and self.FACTORY_END in existing:
                # Replace only the managed block, keep everything else.
                pattern = re.compile(
                    re.escape(self.FACTORY_BEGIN) + r".*?" + re.escape(self.FACTORY_END) + r"\n?",
                    re.DOTALL,
                )
                new_content = pattern.sub(managed_block, existing, count=1)
                path.write_text(new_content)
                return
            # User has edits but no markers — back up before overwriting.
            from datetime import datetime
            date_str = datetime.now().strftime("%Y-%m-%d")
            backup_path = self.vendor_dir / ".backups" / date_str / path.name
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, backup_path)

        path.write_text(managed_block)

    def generate_configs(self, skills):
        UI.info("Compiling Environment Manifests")
        skill_catalog_md = "\n".join([f"- **{s['name']}** (`{s['id']}`): {s['desc']}" for s in skills])
        role_table = "| Role | When to use |\n|---|---|\n| **Analyst** | Requirements, research, user stories |\n| **Architect** | System design, tech decisions |\n| **Dev** | Feature implementation |\n| **QA** | Testing, quality checks |"
        if self.package == "gamedev": role_table += "\n| **Game Designer** | Mechanics, GDD, balance, levels |\n| **Art Director** | Visual style, UI/HUD, aesthetics |"

        shared_body = f"## Startup Instructions\n1. Read `.agent/orchestrator.md` — your master guide.\n2. Read `.agent/.shared/CONTEXT.md` — project status.\n3. Check `.agent/.shared/TASKS.md` — active work.\n\n## BMAD Roles\n{role_table}\n\n## Available Skills\n{skill_catalog_md}"

        self._write_managed_config(self.target_dir / "GEMINI.md", "AI Factory — Gemini CLI", shared_body)
        self._write_managed_config(self.target_dir / "CLAUDE.md", "AI Factory — Claude Code", shared_body)
        self._write_managed_config(self.target_dir / ".antigravity.md", "AI Factory — Antigravity IDE", shared_body)

        orch_path = self.agent_dir / "orchestrator.md"
        orch_body = f"## Protocols\n- **Atomic Operation**: BMAD Roles.\n- **Cognitive Sync**: CONTEXT.md.\n\n## Roles\n{role_table}\n\n## Skill Matrix\n{skill_catalog_md}"
        self._write_managed_config(orch_path, "Master Neural Orchestrator", orch_body)

        self._generate_cursor_rules(skills)
        UI.success("Workspace configuration: Optimized")

    def _generate_cursor_rules(self, skills):
        """Project one .mdc file per skill into .cursor/rules/ (Agent Requested mode)."""
        rules_dir = self.target_dir / ".cursor" / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)

        for s in skills:
            src_path = s["path"]
            try:
                content = src_path.read_text(errors='ignore')
            except OSError:
                continue
            body = re.sub(r'^---\s*\n.*?\n---\s*\n', '', content, count=1, flags=re.DOTALL).lstrip()
            desc = (s.get("desc") or "").replace('"', "'").strip().splitlines()[0] if s.get("desc") else ""
            frontmatter = f"---\ndescription: \"{desc}\"\nalwaysApply: false\n---\n\n"
            (rules_dir / f"{s['id']}.mdc").write_text(frontmatter + body)

    def create_shared_placeholders(self):
        (self.shared_dir / "CONTEXT.md").write_text("# Project Context\n\n## Mission\nDefine objectives.")
        (self.shared_dir / "TASKS.md").write_text("# Production Queue\n- [ ] Audit")
        (self.shared_dir / "DECISIONS.md").write_text("# Decision Ledger")
        
        # Generate Multi-Agent Workflow
        workflow_dir = self.agent_dir / "workflows"
        workflow_dir.mkdir(parents=True, exist_ok=True)
        (workflow_dir / "pipeline.md").write_text(
            "# Multi-Agent Workflow: Feature Development\n\n"
            "You are the Orchestrator. Execute these steps sequentially without asking "
            "for confirmation between steps. For each step, adopt the specified persona "
            "by reading their profile from `.agent/agents/`.\n\n"
            "## Step 1: Analyst\n"
            "Read `.agent/.shared/CONTEXT.md` and the current task. Write a technical specification to `.agent/.shared/temp_spec.md`.\n\n"
            "## Step 2: Architect\n"
            "Read `temp_spec.md`. Append architectural decisions and system design to `.agent/.shared/DECISIONS.md`.\n\n"
            "## Step 3: Developer\n"
            "Read `temp_spec.md` and `DECISIONS.md`. Write the actual code to implement the feature.\n\n"
            "## Step 4: QA / Reviewer\n"
            "Review the written code against the spec. Run necessary tests or validations. Note any issues in `TASKS.md`.\n\n"
            "## Step 5: Cleanup\n"
            "Delete `temp_spec.md`. Provide a final summary of what was accomplished."
        )

def main():
    parser = argparse.ArgumentParser(description="AI Factory Installation Utility")
    parser.add_argument("action", choices=["install", "update", "integrate", "status", "list", "add", "remove", "doctor", "init"], nargs="?", default="install")
    parser.add_argument("name", nargs="?", help="Repo name (owner/repo) for add/remove")
    parser.add_argument("--package", choices=["software", "gamedev", "full"])
    parser.add_argument("--type", choices=["saas", "mobile", "game", "marketing", "content"], help="Project type for `init`")
    args = parser.parse_args()

    UI.banner()
    UI.system_info()
    
    package = args.package
    if not package and args.action == "install":
        UI.prompt_header("Select Configuration")
        UI.prompt_option("1", "Software Engineering", color=UI.CYAN)
        UI.prompt_option("2", "Game Development", color=UI.MAGENTA)
        UI.prompt_option("3", "Grandmaster Pack", color=UI.GOLD)
        UI.prompt_footer()
        
        try:
            choice = UI.prompt_input("Environment choice (1-3)").strip()
        except EOFError: choice = "1"
            
        if choice == "2": package = "gamedev"
        elif choice == "3": package = "full"
        else: package = "software"

    factory = Factory(os.getcwd(), package=package or "software")

    if args.action == "install":
        factory.setup_dirs()
        UI.header("Synchronizing Neural Assets")
        for name, url, pkg, method in factory.repos:
            factory.git_sync(name, url, respect_lock=True)
        factory._save_lock()

        factory.copy_skills()
        factory.create_shared_placeholders()
        factory.integrate()
        
        UI.header("DEPLOYMENT COMPLETE")
        UI.typewriter("   ⚡ Factory is now operational.", delay=0.03)
        print(f"\n   {UI.GREY}│{UI.RESET} {UI.BOLD}Next Steps:{UI.RESET}")
        print(f"   {UI.GREY}│{UI.RESET} 1. Initialize {UI.BOLD}.agent/.shared/CONTEXT.md{UI.RESET}")
        print(f"   {UI.GREY}└{UI.RESET} 2. Say: {UI.BOLD}'Read .agent/orchestrator.md and start'{UI.RESET}")
        print("")
    elif args.action == "update":
        UI.header("Synchronizing Neural Assets")
        for name, url, pkg, method in factory.repos:
            factory.git_sync(name, url, respect_lock=False)
        factory._save_lock()

        factory.copy_skills()
        factory.integrate()
        
        UI.header("UPDATE COMPLETE")
        UI.typewriter("   ⚡ Factory assets updated successfully.", delay=0.03)
        print("")
    elif args.action == "integrate":
        factory.integrate()

        UI.header("INTEGRATION COMPLETE")
        UI.typewriter("   ⚡ Neural links and manifests rebuilt.", delay=0.03)
        print("")
    elif args.action == "list":
        factory.cmd_list()
    elif args.action == "doctor":
        factory.cmd_doctor()
    elif args.action == "init":
        ptype = args.type
        if not ptype:
            UI.prompt_header("Select Project Type")
            UI.prompt_option("1", "SaaS Product", color=UI.CYAN)
            UI.prompt_option("2", "Mobile App", color=UI.CYAN)
            UI.prompt_option("3", "Game", color=UI.MAGENTA)
            UI.prompt_option("4", "Marketing Site", color=UI.GOLD)
            UI.prompt_option("5", "Content / Publication", color=UI.GOLD)
            UI.prompt_footer()
            try:
                choice = UI.prompt_input("Project type (1-5)").strip()
            except EOFError:
                choice = "1"
            ptype = {"1": "saas", "2": "mobile", "3": "game", "4": "marketing", "5": "content"}.get(choice, "saas")
        factory.cmd_init(ptype)
    elif args.action == "add":
        if not args.name:
            UI.error("Usage: factory.py add <owner/repo>")
        else:
            factory.cmd_add(args.name)
    elif args.action == "remove":
        if not args.name:
            UI.error("Usage: factory.py remove <owner/repo>")
        else:
            factory.cmd_remove(args.name)
    elif args.action == "status":
        UI.header("Factory Status")
        if not factory.lock_path.exists():
            UI.warn("No factory.lock.json — run `install` first.")
        else:
            UI.info(f"Lock generated at: {factory.lock.get('generated_at', 'unknown')}")
            UI.info(f"Factory version:   {factory.lock.get('version', 'unknown')}")
            print("")
            locked_repos = factory.lock.get("repos", {})
            for name, url, pkg, method in factory.repos:
                entry = locked_repos.get(name)
                if entry:
                    UI.success(f"{name} @ {entry['sha'][:7]}")
                else:
                    UI.warn(f"{name} — not in lockfile (run `install`)")
        print("")

if __name__ == "__main__":
    main()
