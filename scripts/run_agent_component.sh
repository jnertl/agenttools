#!/usr/bin/env bash
# Usage: run_agent_component.sh <component> [--issue <num>] [--repo <owner/repo>] [--ticket-file <path>]
# Components: middlewaresw, mwclientwithgui, integration_testing
# Environment overrides supported via exports: WORKSPACE, SOURCE_ROOT_DIR, PROVIDER, MODEL, GITHUB_TOKEN, issue, repository_full_name
# The script will run the agenttools agent with the appropriate SYSTEM_PROMPT_FILE and ISSUE_TICKET_FOR_* env vars,
# then process the generated agent response, check for git diffs in the relevant repo, and create a PR/comment if changes exist.

set -euo pipefail

PROGNAME=$(basename "$0")

if [ $# -lt 1 ]; then
  echo "Usage: $PROGNAME <component> [--issue <num>] [--repo <owner/repo>] [--ticket-file <path>]"
  exit 2
fi

COMPONENT=$1
shift

# ensure AGENT_LOG is set and writable
if [ -z "${AGENT_LOG:-}" ]; then
  echo "AGENT_LOG is not set. Export AGENT_LOG (path to agent log file) and retry." >>${AGENT_LOG}
  exit 2
fi

# ensure AGENT_RESPONSE_FILE is set and writable
if [ -z "${AGENT_RESPONSE_FILE:-}" ]; then
  echo "AGENT_RESPONSE_FILE is not set. Export AGENT_RESPONSE_FILE (path to agent response file) and retry." >>${AGENT_LOG}
  exit 2
fi

# ensure AGENT_TOOLS_DIR is set, exists, and we're running from it
if [ -z "${AGENT_TOOLS_DIR:-}" ]; then
  echo "AGENT_TOOLS_DIR is not set. Export AGENT_TOOLS_DIR and run this script from that directory." >>${AGENT_LOG}
  exit 2
fi

# ensure WORKSPACE is set and is a directory
if [ -z "${WORKSPACE:-}" ]; then
  echo "WORKSPACE is not set. Export WORKSPACE (path to workspace dir) and retry." >>${AGENT_LOG}
  exit 2
fi

# ensure SOURCE_ROOT_DIR is set and is a directory
if [ -z "${SOURCE_ROOT_DIR:-}" ]; then
  echo "SOURCE_ROOT_DIR is not set. Export SOURCE_ROOT_DIR (path to source root dir) and retry." >>${AGENT_LOG}
  exit 2
fi

# ensure GITHUB_TOKEN is set and is a directory
if [ -z "${GITHUB_TOKEN:-}" ]; then
  echo "GITHUB_TOKEN is not set. Export GITHUB_TOKEN (GitHub token) and retry." >>${AGENT_LOG}
  exit 2
fi

# flags
while [[ $# -gt 0 ]]; do
  case "$1" in
    --issue)
      issue="$2"; shift 2;;
    --repo)
      repository_full_name="$2"; shift 2;;
    --ticket-file)
      ISSUE_TICKET_ANALYSIS="$2"; shift 2;;
    --provider)
      PROVIDER="$2"; shift 2;;
    --model)
      MODEL="$2"; shift 2;;
    --help)
      echo "Usage: $PROGNAME <component> [--issue <num>] [--repo <owner/repo>] [--ticket-file <path>] [--provider <provider>] [--model <model>]" >>${AGENT_LOG}; exit 0;;
    *)
      echo "Unknown arg: $1" >>${AGENT_LOG}; exit 2;;
  esac
done

# ensure agenttools virtualenv exists (best-effort - assumes already bootstrapped in CI as in pipeline)
# Activate if available
if [ -d "$AGENT_TOOLS_DIR/agent_venv" ]; then
  # shellcheck disable=SC1090
  source "$AGENT_TOOLS_DIR/agent_venv/bin/activate"
fi

# helper to run agent for a given prompt and repo
run_component() {
  local component="$1"
  local prompt_file="$2"
  local ticket_env_var="$3"
  local git_repo_dir="$4"
  local git_remote_repo_url="$5"

  echo "Running agent for component: $component" >>${AGENT_LOG}

  rm -f "$AGENT_RESPONSE_FILE" || true
  export "$ticket_env_var"="$ISSUE_TICKET_ANALYSIS"
  export SYSTEM_PROMPT_FILE="$prompt_file"

  bash "./scripts/ongoing_printer.sh" \
    python -m agenttools.agent --provider "$PROVIDER" --silent --model "$MODEL" --response-file "$AGENT_RESPONSE_FILE" --query "Analyse"

  python "./scripts/clean_markdown_utf8.py" \
      "$AGENT_RESPONSE_FILE" "$WORKSPACE/${component}_analysis.md"

  # detect git diff
  GIT_DIFF=$(git -C "$git_repo_dir" diff || true)
  AGENT_RESPONSE_CONTENT=$(cat "$WORKSPACE/${component}_analysis.md" || echo "No response generated.")

  if [ -n "$GIT_DIFF" ]; then
    BRANCH_NAME="issue_${issue}_${component}_updates_$(date +%Y%m%d%H%M%S)"
    TITLE="${component} updates for issue #${issue}"

    # create PR in the remote repository using provided scripts
    response=$(python "$AGENT_TOOLS_DIR/scripts/github_pr.py" \
      --local \
      --git-dir "$git_repo_dir" \
      --repo "$git_remote_repo_url" \
      --head "$BRANCH_NAME" \
      --base "main" \
      --title "$TITLE" \
      --body "Automated updates for ${component} based on issue #${issue}." \
      --commit-message "Commit ${component} updates for issue #${issue}" \
      --token "$GITHUB_TOKEN" || true)

    echo "Created PR response: $response" >> "$AGENT_LOG" || true

    BRANCH_URL=$(printf '%s\n' "$response" | sed -n 's/^[[:space:]]*Branch URL:[[:space:]]*//p' | head -n1 || true)
    if [ -n "$BRANCH_URL" ]; then
      echo "Found Branch URL: $BRANCH_URL" >> "$AGENT_LOG" || true
      AGENT_RESPONSE_CONTENT=$(printf '%s\n\n**See branch [%s](%s)**\n' "$AGENT_RESPONSE_CONTENT" "$BRANCH_NAME" "$BRANCH_URL")
    else
      echo "No Branch URL found in response" >> "$AGENT_LOG" || true
    fi
  else
    echo "No git diff for $component" >> "$AGENT_LOG" || true
  fi

  python "$AGENT_TOOLS_DIR/scripts/github_comment.py" \
      --repo "$repository_full_name" \
      --issue "$issue" \
      --body "$AGENT_RESPONSE_CONTENT" \
      --token "$GITHUB_TOKEN" || true
}

# dispatch
case "$COMPONENT" in
  middlewaresw)
    run_component "middlewaresw" "${WORKSPACE}/system_prompts/middlewaresw_developer.txt" \
        "ISSUE_TICKET_FOR_MIDDLEWARESW" \
        "${SOURCE_ROOT_DIR}/middlewaresw" \
        "https://github.com/jnertl/middlewaresw.git"
    ;;
  mwclientwithgui)
    run_component "mwclientwithgui" "${WORKSPACE}/system_prompts/mwclientwithgui_developer.txt" \
        "ISSUE_TICKET_FOR_MWCLIENTWITHGUI" "${SOURCE_ROOT_DIR}/mwclientwithgui" \
        "https://github.com/jnertl/mwclientwithgui.git"
    ;;
  integration_testing)
    run_component "integration_testing" "${WORKSPACE}/system_prompts/integration_testing.txt" \
        "ISSUE_TICKET_FOR_INTEGRATION_TESTING" "${SOURCE_ROOT_DIR}/testing" \
        "https://github.com/jnertl/testing.git"
    ;;
  *)
    echo "Unknown component: $COMPONENT" >>${AGENT_LOG}; exit 2;;
esac

# done
exit 0
