#!/usr/bin/env bash
# ============================================================
# TRUST — install.sh
# Trustable Reviews via Universal Skills & Tooling
# "O review de IA em que dá pra confiar"
# ============================================================
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/seu-user/trust/main/install.sh | bash
#
# What this script does:
#   1. Checks prerequisites (Python 3.11+, git, Claude Code)
#   2. Clones the TRUST framework to ~/.trust/
#   3. Installs Python dependencies
#   4. Links skills to Claude Code's skills directory
#   5. Links commands to Claude Code's commands directory
#   6. Prints next steps
# ============================================================

set -euo pipefail

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

TRUST_REPO="https://github.com/seu-user/trust.git"
TRUST_HOME="${TRUST_HOME:-$HOME/.trust}"
CLAUDE_SKILLS_DIR="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
CLAUDE_COMMANDS_DIR="${CLAUDE_COMMANDS_DIR:-$HOME/.claude/commands}"

# --- Helpers ---
ok()   { echo -e "  ${GREEN}✓${NC}  $*"; }
warn() { echo -e "  ${YELLOW}⚠${NC}  $*"; }
fail() { echo -e "  ${RED}✗${NC}  $*"; exit 1; }
step() { echo -e "\n${CYAN}${BOLD}$*${NC}"; }

# --- Header ---
echo ""
echo -e "${BOLD}TRUST — Trustable Reviews via Universal Skills & Tooling${NC}"
echo -e "${CYAN}\"O review de IA em que dá pra confiar\"${NC}"
echo ""

# ============================================================
# Step 1 — Prerequisites
# ============================================================
step "1/5  Checking prerequisites..."

# Python 3.11+
if command -v python3 &>/dev/null; then
    PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
    PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
    if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 11 ]; then
        ok "Python $PY_VERSION"
    else
        warn "Python $PY_VERSION found (3.11+ recommended). Some scripts may not work."
    fi
else
    fail "Python 3 not found. Install Python 3.11+ and retry."
fi

# git
if command -v git &>/dev/null; then
    GIT_VERSION=$(git --version | awk '{print $3}')
    ok "git $GIT_VERSION"
else
    fail "git not found. Install git and retry."
fi

# pip
if command -v pip3 &>/dev/null || python3 -m pip --version &>/dev/null 2>&1; then
    ok "pip available"
else
    warn "pip not found. Python dependencies may need manual installation."
fi

# Claude Code (optional but expected)
if command -v claude &>/dev/null; then
    ok "Claude Code found"
else
    warn "Claude Code CLI not found. Install it from claude.ai/code to use slash commands."
fi

# ============================================================
# Step 2 — Clone or update TRUST
# ============================================================
step "2/5  Installing TRUST framework..."

if [ -d "$TRUST_HOME" ]; then
    echo "  Existing installation found at $TRUST_HOME"
    echo -n "  Updating... "
    git -C "$TRUST_HOME" pull --quiet origin main && echo "done" || warn "Update failed. Using existing version."
else
    echo "  Cloning to $TRUST_HOME..."
    git clone --quiet "$TRUST_REPO" "$TRUST_HOME"
    ok "Cloned to $TRUST_HOME"
fi

# ============================================================
# Step 3 — Python dependencies
# ============================================================
step "3/5  Installing Python dependencies..."

REQUIREMENTS="$TRUST_HOME/requirements.txt"
if [ -f "$REQUIREMENTS" ]; then
    python3 -m pip install --quiet -r "$REQUIREMENTS"
    ok "Dependencies installed"
else
    # Minimal deps inline
    python3 -m pip install --quiet "PyYAML>=6.0"
    ok "PyYAML installed"
fi

# ============================================================
# Step 4 — Link skills and commands to Claude Code
# ============================================================
step "4/5  Linking skills and commands to Claude Code..."

# Skills
if [ -d "$TRUST_HOME/skills" ]; then
    mkdir -p "$CLAUDE_SKILLS_DIR"
    for skill_dir in "$TRUST_HOME"/skills/*/; do
        skill_name=$(basename "$skill_dir")
        target="$CLAUDE_SKILLS_DIR/$skill_name"
        if [ -L "$target" ]; then
            rm "$target"
        fi
        ln -s "$skill_dir" "$target"
        ok "Skill linked: $skill_name"
    done
else
    warn "No skills directory found in $TRUST_HOME"
fi

# Commands
if [ -d "$TRUST_HOME/commands" ]; then
    mkdir -p "$CLAUDE_COMMANDS_DIR"
    for cmd_file in "$TRUST_HOME"/commands/*.md; do
        cmd_name=$(basename "$cmd_file")
        target="$CLAUDE_COMMANDS_DIR/$cmd_name"
        if [ -L "$target" ]; then
            rm "$target"
        fi
        ln -s "$cmd_file" "$target"
        ok "Command linked: $cmd_name"
    done
else
    warn "No commands directory found in $TRUST_HOME"
fi

# ============================================================
# Step 5 — Shell configuration
# ============================================================
step "5/5  Configuring shell..."

TRUST_BIN="$TRUST_HOME/bin"
TRUST_EXPORT="export PATH=\"\$PATH:$TRUST_BIN\""
TRUST_HOME_EXPORT="export TRUST_HOME=\"$TRUST_HOME\""

# Detect shell config file
SHELL_RC=""
if [ -n "${ZSH_VERSION:-}" ] || [ "$(basename "${SHELL:-}")" = "zsh" ]; then
    SHELL_RC="$HOME/.zshrc"
elif [ -n "${BASH_VERSION:-}" ] || [ "$(basename "${SHELL:-}")" = "bash" ]; then
    SHELL_RC="$HOME/.bashrc"
    [ -f "$HOME/.bash_profile" ] && SHELL_RC="$HOME/.bash_profile"
fi

if [ -n "$SHELL_RC" ]; then
    # Add TRUST_HOME if not already present
    if ! grep -q "TRUST_HOME" "$SHELL_RC" 2>/dev/null; then
        echo "" >> "$SHELL_RC"
        echo "# TRUST framework" >> "$SHELL_RC"
        echo "$TRUST_HOME_EXPORT" >> "$SHELL_RC"
        echo "$TRUST_EXPORT" >> "$SHELL_RC"
        ok "Added TRUST_HOME to $SHELL_RC"
    else
        ok "TRUST_HOME already in $SHELL_RC"
    fi
else
    warn "Could not detect shell config. Add manually to your shell rc:"
    echo ""
    echo "    $TRUST_HOME_EXPORT"
    echo "    $TRUST_EXPORT"
fi

# Export for current session
export TRUST_HOME="$TRUST_HOME"
export PATH="$PATH:$TRUST_BIN"

# ============================================================
# Done
# ============================================================
echo ""
echo -e "${GREEN}${BOLD}✅ TRUST installed successfully!${NC}"
echo ""
echo -e "${BOLD}Next steps:${NC}"
echo ""
echo "  1. Reload your shell:"
echo "       source ${SHELL_RC:-~/.bashrc}"
echo ""
echo "  2. Create your team's setup repo:"
echo "       /trust init pilot"
echo ""
echo "  3. Verify everything is connected:"
echo "       /trust doctor"
echo ""
echo "  4. Run your first review:"
echo "       cd ~/work/your-product-repo"
echo "       /trust review-pr"
echo ""
echo -e "  📖 Docs: ${CYAN}https://github.com/seu-user/trust${NC}"
echo ""
