# 🏭 My AI Factory v1.0

**My AI Factory** is a high-tech AI development ecosystem that transforms your project into an intelligent hub. It automatically deploys, links, and orchestrates world-class AI best practices and tools into a single, unified workspace.

The intelligent Python-based installer provides seamless integration across three environments: **Gemini CLI**, **Claude Code**, and **Antigravity IDE**.

---

## 🚀 Quick Start

Deploy the complete development environment with a single command from your project root:

```bash
git clone https://github.com/Menta1ik/my-AI-factory.git && python3 my-AI-factory/factory.py install
```

---

## 🛠 Integrated Repositories

We have selected and integrated the best tools for every stage of development:

### 🧩 Platform Core
*   **[BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD):** A fundamental Agile development methodology driven by AI. Provides roles for PM, Architect, Developer, and QA.
*   **[Antigravity Kit](https://github.com/vudovn/antigravity-kit):** Professional templates and structure for IDE-oriented development.
*   **[Awesome Agent Skills](https://github.com/VoltAgent/awesome-agent-skills):** A curated collection of ready-to-use skills for everyday tasks.
*   **[Agent Browser](https://github.com/vercel-labs/agent-browser):** A powerful tool for autonomous navigation and testing in real browsers.

### 🏭 "Software Dev" Pack
*   **[UI/UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill):** Professional interface and design system engineering.
*   **[Marketing Skills](https://github.com/coreyhaines31/marketingskills):** A library of marketing strategies, SEO, and copywriting.
*   **[Impeccable CSS](https://github.com/pbakaus/impeccable):** Frontend quality standards and auditing.
*   **[Superpowers](https://github.com/obra/superpowers):** Enhanced agent capabilities for executing complex multi-step tasks.
*   **[Graphify](https://github.com/safishamsi/graphify):** Visualization of your project's architecture and dependencies.

### 🎮 "Game Dev" Pack
*   **[BMAD Game Studio](https://github.com/bmad-code-org/bmad-module-game-dev-studio):** Specialized roles for game development: Game Designer, Level Designer, Art Director.
*   **[Claude Game Studios](https://github.com/Donchitos/Claude-Code-Game-Studios):** Workflows and processes for game studios.
*   **[Caveman Engine](https://github.com/JuliusBrussee/caveman):** Reference utilities and logic for game engines.

---

## 🌟 Smart Installer v1.0 Advantages

Unlike simple copy scripts, our Python installer performs **Deep Integration**:

1.  **Deep Linking for Claude Code:** 
    Automatically creates symbolic links in `.agent/.claude/skills/`. Claude instantly recognizes third-party skills as native tools.
2.  **Intent Routing for Gemini CLI:**
    Dynamically generates rules in `GEMINI.md`. Gemini receives clear instructions on which expert skill to invoke for a specific task.
3.  **Cross-Agent Orchestration:**
    All skills are registered in BMAD manifests. You can invite a "Marketer" to a meeting with an "Architect" via Party Mode.
4.  **Single Source of Truth:**
    The `orchestrator.md` master file synchronizes context across all AI tools. What Gemini knows, Claude knows too.
5.  **Automatic Metadata Parsing:**
    The installer reads `SKILL.md` from third-party repos, extracting descriptions and versions to keep your knowledge base up to date.

---

## 🗂 Project Structure

```
my-project/
├── my-AI-factory/        ← Smart Control Center
├── .agent/               ← Project Nervous System (git-tracked)
│   ├── orchestrator.md   ← MASTER map of all knowledge and experts
│   ├── skills/           ← Library of all installed skills
│   ├── .claude/skills/   ← Native links for Claude Code
│   ├── .shared/          ← Shared memory (CONTEXT, TASKS, DECISIONS)
│   ├── custom/           ← Your unique domain agents
│   └── learned/          ← Self-learning knowledge base
├── GEMINI.md             ← Instructions for Gemini CLI
└── CLAUDE.md             ← Instructions for Claude Code
```

---

## 🛠 Management Commands

| Command | Description |
|---|---|
| `python3 factory.py install` | Install chosen pack (Software/Game/Full) |
| `python3 factory.py update` | Update all repositories without losing your data |
| `python3 factory.py integrate` | Rebuild links and manifests (after adding your own skills) |

---

## 🤝 Contributing

Your "Factory" is built on Open Source principles. We encourage you to use and extend these tools to create better products.

*[my-AI-factory](https://github.com/Menta1ik/my-AI-factory)*
