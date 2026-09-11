#!/usr/bin/env bash
# ==============================================================================
# git_helper.sh - Deterministic Git Suite runner for AI agents & developers.
#
# High-frequency usage:
#   /git        -> bash git_helper.sh [sync] "<message>"  (commit + push to origin)
#   /git commit -> bash git_helper.sh commit "<message>"  (local commit only)
#
# Subcommands:
#   commit    : Security scan + 10-step message validation + local git commit
#   sync      : Security scan + validation + commit + safe push to remote
#   status    : Working tree summary, unpushed commits, and security scan
#   draft     : Working tree status, security scan, and smart commit suggestion
#   validate  : Pre-flight commit message validator (10-step gate)
#   branch    : Standardized branch creation enforcing conventional prefixes
#   undo      : Safe soft reset of last commit (preserves staged changes)
#   audit     : Audit past N commits for Conventional Commits compliance
#   check-env : Environment diagnostics (Git, author, Bash/platform)
# ==============================================================================

set -uo pipefail

# ------------------------------------------------------------------------------
# Constants & Whitelists
# ------------------------------------------------------------------------------

ALLOWED_TYPES="feat fix docs refactor chore test"

COMMON_IMPERATIVE_VERBS=(
    "add" "adjust" "align" "allow" "apply" "author" "bump" "clarify"
    "clean" "configure" "consolidate" "correct" "create" "decouple"
    "define" "deprecate" "disable" "document" "downgrade" "enable"
    "enforce" "ensure" "expand" "expose" "extract" "fix" "format"
    "handle" "implement" "improve" "include" "init" "initialize"
    "integrate" "introduce" "migrate" "optimize" "organize" "patch"
    "prevent" "publish" "refactor" "release" "remove" "rename"
    "reorganize" "resolve" "revert" "revise" "rewrite" "set" "setup"
    "simplify" "split" "standardize" "streamline" "structure" "support"
    "sync" "synchronize" "test" "update" "upgrade" "validate" "verify"
)

# Allowed env templates (explicit exception for .env.example, etc.)
ALLOWED_ENV_TEMPLATES=(".env.example" ".env.sample" ".env.template" ".env.dist" ".env.ci")

LARGE_FILE_THRESHOLD_BYTES=$((10 * 1024 * 1024)) # 10 MB

# Pre-compiled Regex patterns for POSIX/Bash compatibility
RE_ENV='^\.env(\..+)?$'
RE_CRYPTO='\.(pem|key|pfx|p12|keystore)$'
RE_SSH='^id_(rsa|ed25519)(\.pub)?$'
RE_CREDS='(credential|service-account|client_secret).*\.json$'
RE_DB='\.(sqlite|db)$'

RE_DIFF_FILE='^\+\+\+ b/(.*)'
RE_DIFF_ADDED='^\+[^+]'
RE_PRIV_KEY='-----BEGIN ([A-Z]+ )?PRIVATE KEY-----'
RE_AWS='(A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}'
RE_TOKEN='(api[_-]?key|access[_-]?token|secret[_-]?key|private[_-]?token|auth[_-]?token)[[:space:]]*=[[:space:]]*['"'"'"][a-zA-Z0-9_\-]{20,}['"'"'"]'

RE_CONFLICT_START='^<{7} '
RE_CONFLICT_MID='^={7}$'
RE_CONFLICT_END='^>{7} '

RE_HEADER='^([a-zA-Z0-9_-]+)(\(([^)]+)\))?(!)?:\ *(.*)$'
RE_SCOPE='^[a-z0-9]+(-[a-z0-9]+)*$'
RE_TRAILING_DOT='\.$'
RE_PAST='(ed|ing)$'
RE_S='(es|s)$'
RE_WHITELIST_S='(pass|process)$'
RE_UPPER='^[A-Z]'
RE_ACRONYM='^[A-Z0-9]+$'
RE_SPACES='[[:space:]]{2,}'
RE_SNAKE='_'
RE_BULLET='^-\ '
RE_BREAKING='^BREAKING CHANGE:'
RE_BREAKING_DESC='^BREAKING CHANGE:\ *(.*)'

# ------------------------------------------------------------------------------
# Helper: Check if value is in array
# ------------------------------------------------------------------------------
is_in_array() {
    local target="$1"
    shift
    for item in "$@"; do
        if [[ "$item" == "$target" ]]; then
            return 0
        fi
    done
    return 1
}

# ------------------------------------------------------------------------------
# Tier 1: Security & Hygiene Gates
# ------------------------------------------------------------------------------

scan_security() {
    local -n _violations=$1
    local -n _warnings=$2
    _violations=()
    _warnings=()

    # Get list of staged files
    local staged_files
    staged_files=$(git diff --cached --name-only 2>/dev/null || true)
    if [[ -z "$staged_files" ]]; then
        return 0
    fi

    while IFS= read -r filepath; do
        [[ -z "$filepath" ]] && continue
        local filename
        filename=$(basename "$filepath")

        # 1. Environment files check with .env.example exception
        if [[ "$filename" =~ $RE_ENV ]]; then
            if is_in_array "$filename" "${ALLOWED_ENV_TEMPLATES[@]}"; then
                # Allowed template file
                :
            else
                _violations+=("$filepath: Matches sensitive file pattern '^\\.env(\\..+)?$' (untracked environment file)")
            fi
        # 2. Cryptographic keys and certificates
        elif [[ "$filename" =~ $RE_CRYPTO ]]; then
            _violations+=("$filepath: Sensitive cryptographic key/certificate file")
        # 3. SSH keys
        elif [[ "$filename" =~ $RE_SSH ]]; then
            _violations+=("$filepath: Sensitive SSH key file")
        # 4. Credential files
        elif [[ "$filename" =~ $RE_CREDS ]]; then
            _violations+=("$filepath: Sensitive credentials or service account JSON")
        # 5. Local database files
        elif [[ "$filename" =~ $RE_DB ]]; then
            _violations+=("$filepath: Local SQLite or database binary file")
        fi

        # 6. File size and binary format warnings
        if [[ -f "$filepath" ]]; then
            local size
            size=$(stat -c%s "$filepath" 2>/dev/null || stat -f%z "$filepath" 2>/dev/null || wc -c < "$filepath" 2>/dev/null || echo 0)
            if [[ "$size" -gt $LARGE_FILE_THRESHOLD_BYTES ]]; then
                local mb=$(( size / 1048576 ))
                _warnings+=("$filepath: Large file (${mb}MB) exceeds 10MB threshold")
            fi

            local ext="${filename##*.}"
            case "$ext" in
                zip|tar|gz|tgz|rar|7z|iso|bin|exe|dmg)
                    _warnings+=("$filepath: Binary archive or executable format ('.$ext')")
                    ;;
            esac
        fi
    done <<< "$staged_files"

    # 7. Scan staged diff additions for secret tokens & merge conflict markers
    local diff_out
    diff_out=$(git diff --cached -U0 2>/dev/null || true)
    if [[ -n "$diff_out" ]]; then
        local current_file="unknown"
        while IFS= read -r line; do
            if [[ "$line" =~ $RE_DIFF_FILE ]]; then
                current_file="${BASH_REMATCH[1]}"
                continue
            fi

            # Check only added lines (starts with + but not +++)
            if [[ "$line" =~ $RE_DIFF_ADDED ]]; then
                local added_content="${line:1}"
                local trimmed_content
                trimmed_content="$(echo "$added_content" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"

                # Conflict markers
                if [[ "$trimmed_content" =~ $RE_CONFLICT_START || "$trimmed_content" =~ $RE_CONFLICT_MID || "$trimmed_content" =~ $RE_CONFLICT_END ]]; then
                    _violations+=("$current_file: Unresolved merge conflict marker detected: '$trimmed_content'")
                    continue
                fi

                # Cryptographic private key header
                if [[ "$added_content" =~ $RE_PRIV_KEY ]]; then
                    _violations+=("$current_file: Detected potential secret: Private cryptographic key block")
                    continue
                fi

                # AWS Access Key ID
                if [[ "$added_content" =~ $RE_AWS ]]; then
                    _violations+=("$current_file: Detected potential secret: AWS Access Key ID")
                    continue
                fi

                # Generic secret / token assignment (case insensitive via shopt if needed)
                if [[ "$added_content" =~ $RE_TOKEN ]]; then
                    _violations+=("$current_file: Detected potential secret: Generic API secret/token assignment")
                    continue
                fi
            fi
        done <<< "$diff_out"
    fi

    if [[ ${#_violations[@]} -gt 0 ]]; then
        return 1
    fi
    return 0
}

# ------------------------------------------------------------------------------
# Tier 2: 10-Step Conventional Commits Validation Gate
# ------------------------------------------------------------------------------

validate_commit_message() {
    local full_message="$1"
    VALIDATION_PASSED=0
    STEP_RESULTS=()

    if [[ -z "${full_message//[[:space:]]/}" ]]; then
        VALIDATION_PASSED=1
        STEP_RESULTS+=("1|validate_presence|[FAIL]|Commit message is completely empty")
        return 1
    fi

    # Split header and body
    local header
    header="$(echo "$full_message" | head -n 1 | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"

    local body_lines=()
    local line_num=0
    while IFS= read -r line; do
    line_num=$((line_num + 1))
        if [[ $line_num -gt 1 ]]; then
            local stripped
            stripped="$(echo "$line" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
            if [[ -n "$stripped" ]]; then
                body_lines+=("$stripped")
            fi
        fi
    done <<< "$full_message"

    # Step 1: Structure: <type>(<scope>): <description> or <type>(<scope>)!: <description>
    local commit_type=""
    local scope=""
    local is_breaking=""
    local description=""

    if [[ "$header" =~ $RE_HEADER ]]; then
        commit_type="${BASH_REMATCH[1]}"
        local has_parens="${BASH_REMATCH[2]}"
        scope="${BASH_REMATCH[3]}"
        is_breaking="${BASH_REMATCH[4]}"
        description="${BASH_REMATCH[5]}"

        if [[ -z "$has_parens" || -z "$scope" ]]; then
            VALIDATION_PASSED=1
            STEP_RESULTS+=("1|validate_structure|[FAIL]|Scope is missing. Format must be \`<type>(<scope>): <description>\`")
            return 1
        fi

        if [[ -z "$description" ]]; then
            VALIDATION_PASSED=1
            STEP_RESULTS+=("1|validate_structure|[FAIL]|Description is missing after scope and colon")
            return 1
        fi

        STEP_RESULTS+=("1|validate_structure|[PASS]|Structure parsed successfully: type='$commit_type', scope='$scope'")
    else
        VALIDATION_PASSED=1
        STEP_RESULTS+=("1|validate_structure|[FAIL]|Header does not match standard pattern: \`<type>(<scope>): <description>\`")
        return 1
    fi

    # Step 2: Type whitelist
    local type_valid=false
    for t in $ALLOWED_TYPES; do
        if [[ "$commit_type" == "$t" ]]; then
            type_valid=true
            break
        fi
    done
    if $type_valid; then
        STEP_RESULTS+=("2|validate_type|[PASS]|Type '$commit_type' is whitelisted")
    else
        VALIDATION_PASSED=1
        STEP_RESULTS+=("2|validate_type|[FAIL]|Type '$commit_type' is invalid. Strictly allowed types: [$ALLOWED_TYPES]")
    fi

    # Step 3: Scope format (lowercase alphanumeric / kebab-case)
    if [[ "$scope" =~ $RE_SCOPE ]]; then
        STEP_RESULTS+=("3|validate_scope|[PASS]|Scope '$scope' is valid kebab-case")
    else
        VALIDATION_PASSED=1
        STEP_RESULTS+=("3|validate_scope|[FAIL]|Scope '$scope' must be lowercase alphanumeric or kebab-case (e.g. 'git', 'workflow')")
    fi

    # Step 4: Header length (<= 120 chars)
    local header_len=${#header}
    if [[ $header_len -le 120 ]]; then
        STEP_RESULTS+=("4|validate_header_length|[PASS]|Header length ($header_len/120 chars) within limit")
    else
        VALIDATION_PASSED=1
        STEP_RESULTS+=("4|validate_header_length|[FAIL]|Header length ($header_len chars) exceeds maximum limit of 120 chars")
    fi

    # Step 5: Description length (>= 10 chars)
    local desc_len=${#description}
    if [[ $desc_len -ge 10 ]]; then
        STEP_RESULTS+=("5|validate_description_length|[PASS]|Description ($desc_len chars >= 10) is sufficiently detailed")
    else
        VALIDATION_PASSED=1
        STEP_RESULTS+=("5|validate_description_length|[FAIL]|Description ($desc_len chars) is too short. Minimum required is 10 chars")
    fi

    # Step 6: No trailing period in header
    if [[ "$header" =~ $RE_TRAILING_DOT ]]; then
        VALIDATION_PASSED=1
        STEP_RESULTS+=("6|validate_no_trailing_period|[FAIL]|Header line must not end with a period ('.')")
    else
        STEP_RESULTS+=("6|validate_no_trailing_period|[PASS]|No trailing period in header")
    fi

    # Step 7: English imperative verb
    local first_word
    first_word="$(echo "$description" | awk '{print $1}')"
    local first_word_lower
    first_word_lower="$(echo "$first_word" | tr '[:upper:]' '[:lower:]')"

    local verb_ok=false
    for v in "${COMMON_IMPERATIVE_VERBS[@]}"; do
        if [[ "$first_word_lower" == "$v" ]]; then
            verb_ok=true
            break
        fi
    done

    if $verb_ok; then
        STEP_RESULTS+=("7|validate_english_imperative_verb|[PASS]|Leading verb '$first_word_lower' is an approved English imperative verb")
    elif [[ "$first_word_lower" =~ $RE_PAST ]]; then
        VALIDATION_PASSED=1
        STEP_RESULTS+=("7|validate_english_imperative_verb|[FAIL]|Leading word '$first_word' appears to be past tense or gerund. Use imperative present tense (e.g. 'add', 'update', 'fix')")
    elif [[ "$first_word_lower" =~ $RE_S ]] && [[ ! "$first_word_lower" =~ $RE_WHITELIST_S ]]; then
        VALIDATION_PASSED=1
        STEP_RESULTS+=("7|validate_english_imperative_verb|[FAIL]|Leading word '$first_word' appears to be 3rd-person singular or plural. Use imperative present tense (e.g. 'add', 'update', 'fix')")
    else
        VALIDATION_PASSED=1
        STEP_RESULTS+=("7|validate_english_imperative_verb|[FAIL]|Leading word '$first_word' is not a recognized English imperative verb. Examples: add, fix, update, implement, refactor...")
    fi

    # Step 8: Casing and spacing
    local casing_ok=true
    local first_char="${description:0:1}"
    if [[ "$first_char" =~ $RE_UPPER ]]; then
        if [[ ! "$first_word" =~ $RE_ACRONYM || ${#first_word} -lt 2 ]]; then
            casing_ok=false
            local suggested_desc="$(echo "${first_char}" | tr '[:upper:]' '[:lower:]')${description:1}"
            VALIDATION_PASSED=1
            STEP_RESULTS+=("8|validate_casing_and_spacing|[FAIL]|Description should start with lowercase letter: '$suggested_desc'")
        fi
    fi

    if $casing_ok; then
        if [[ "$description" =~ $RE_SPACES ]]; then
            VALIDATION_PASSED=1
            STEP_RESULTS+=("8|validate_casing_and_spacing|[FAIL]|Description contains multiple consecutive spaces; use single normal spaces")
        elif [[ ! "$description" =~ [[:space:]] && "$description" =~ $RE_SNAKE ]]; then
            VALIDATION_PASSED=1
            STEP_RESULTS+=("8|validate_casing_and_spacing|[FAIL]|Description '$description' looks like snake_case. Use standard space-separated words")
        else
            STEP_RESULTS+=("8|validate_casing_and_spacing|[PASS]|Casing and spacing format are clean")
        fi
    fi

    # Step 9: Body bullets format
    local bullets_ok=true
    if [[ ${#body_lines[@]} -gt 0 ]]; then
        local b_idx=0
        for bline in "${body_lines[@]}"; do
            b_idx=$((b_idx + 1))
            if [[ ! "$bline" =~ $RE_BULLET && ! "$bline" =~ $RE_BREAKING ]]; then
                bullets_ok=false
                VALIDATION_PASSED=1
                STEP_RESULTS+=("9|validate_body_bullets|[FAIL]|Body line $b_idx does not start with bullet '- ': '$bline'")
                break
            fi
            if [[ ${#bline} -gt 120 ]]; then
                bullets_ok=false
                VALIDATION_PASSED=1
                STEP_RESULTS+=("9|validate_body_bullets|[FAIL]|Body bullet $b_idx exceeds 120 chars (${#bline} chars)")
                break
            fi
        done
        if $bullets_ok; then
            STEP_RESULTS+=("9|validate_body_bullets|[PASS]|Body bullets (${#body_lines[@]} lines) formatted correctly")
        fi
    else
        STEP_RESULTS+=("9|validate_body_bullets|[PASS]|No body lines provided (optional)")
    fi

    # Step 10: Breaking change footer specification
    local bc_ok=true
    for bline in "${body_lines[@]}"; do
        if [[ "$bline" =~ $RE_BREAKING_DESC ]]; then
            local bc_desc="${BASH_REMATCH[1]}"
            if [[ ${#bc_desc} -lt 5 ]]; then
                bc_ok=false
                VALIDATION_PASSED=1
                STEP_RESULTS+=("10|validate_breaking_change|[FAIL]|BREAKING CHANGE description is too short")
                break
            fi
        fi
    done
    if $bc_ok; then
        STEP_RESULTS+=("10|validate_breaking_change|[PASS]|Breaking change footer specification valid")
    fi

    return $VALIDATION_PASSED
}

# ------------------------------------------------------------------------------
# Report Printing & JSON Helpers
# ------------------------------------------------------------------------------

print_validation_report() {
    local header="$1"
    echo "======================================================================"
    echo " COMMIT MESSAGE PRE-FLIGHT VALIDATION REPORT"
    echo "======================================================================"
    echo "Candidate Header: $header"
    echo "----------------------------------------------------------------------"
    for item in "${STEP_RESULTS[@]}"; do
        IFS="|" read -r step name status msg <<< "$item"
        printf "Step %-2s/10 %-35s %-6s : %s\n" "$step" "$name" "$status" "$msg"
    done
    echo "======================================================================"
    if [[ $VALIDATION_PASSED -eq 0 ]]; then
        echo ">>> RESULT: 100% VALIDATED. Message is safe for git commit."
    else
        echo ">>> RESULT: VALIDATION FAILED. Please resolve errors before committing."
    fi
    echo "======================================================================"
}

# ------------------------------------------------------------------------------
# Inference Engine (Scope & Type Detection)
# ------------------------------------------------------------------------------

infer_scope_and_type() {
    local -n _inferred_scope=$1
    local -n _inferred_type=$2

    local changed_files
    changed_files=$(git status --porcelain 2>/dev/null | awk '{print $NF}' || true)

    if [[ -z "$changed_files" ]]; then
        _inferred_scope="root"
        _inferred_type="chore"
        return
    fi

    # Determine type
    local all_docs=true
    local all_tests=true
    local all_configs=true

    while IFS= read -r f; do
        [[ -z "$f" ]] && continue
        if [[ ! "$f" =~ \.md$ && ! "$f" =~ ^docs/ ]]; then
            all_docs=false
        fi
        if [[ ! "$f" =~ test && ! "$f" =~ \.spec\.[a-z]+$ && ! "$f" =~ \.test\.[a-z]+$ ]]; then
            all_tests=false
        fi
        if [[ "$f" != "package.json" && "$f" != "pnpm-lock.yaml" && "$f" != "pyproject.toml" && "$f" != ".gitignore" && ! "$f" =~ ^\.github/ ]]; then
            all_configs=false
        fi
    done <<< "$changed_files"

    if $all_docs; then
        _inferred_type="docs"
    elif $all_tests; then
        _inferred_type="test"
    elif $all_configs; then
        _inferred_type="chore"
    else
        _inferred_type="feat"
    fi

    # Determine scope from first file
    local target_file
    target_file=$(echo "$changed_files" | head -n 1)
    target_file="${target_file//\\//}"

    if [[ "$target_file" =~ skills/([^/]+) ]]; then
        _inferred_scope="${BASH_REMATCH[1]}"
    elif [[ "$target_file" =~ docs/([^/]+) ]]; then
        _inferred_scope="${BASH_REMATCH[1]}"
    elif [[ "$target_file" =~ ^\.changeset/ ]]; then
        _inferred_scope="release"
    elif [[ "$target_file" =~ ^\.github/ ]]; then
        if [[ "$target_file" =~ release ]]; then
            _inferred_scope="release"
        else
            _inferred_scope="ci"
        fi
    elif [[ "$target_file" =~ ^(package\.json|pnpm-lock\.yaml|pyproject\.toml)$ ]]; then
        _inferred_scope="deps"
    else
        local top_dir="${target_file%%/*}"
        if [[ -n "$top_dir" && "$top_dir" != "$target_file" ]]; then
            _inferred_scope="$(echo "$top_dir" | tr '[:upper:]' '[:lower:]' | sed -e 's/[^a-z0-9-]/-/g' -e 's/^-//' -e 's/-$//')"
        else
            _inferred_scope="root"
        fi
    fi
}

# ------------------------------------------------------------------------------
# Subcommand: validate
# ------------------------------------------------------------------------------

cmd_validate() {
    local message="$1"
    local as_json="$2"

    validate_commit_message "$message"
    local header
    header="$(echo "$message" | head -n 1)"

    if [[ "$as_json" == "true" ]]; then
        echo "{"
        echo "  \"passed\": $([[ $VALIDATION_PASSED -eq 0 ]] && echo "true" || echo "false"),"
        echo "  \"header\": \"$(echo "$header" | sed 's/"/\\"/g')\","
        echo "  \"reports\": ["
        local count=${#STEP_RESULTS[@]}
        local idx=0
        for item in "${STEP_RESULTS[@]}"; do
            idx=$((idx + 1))
            IFS="|" read -r step name status msg <<< "$item"
            local passed=$([[ "$status" == "[PASS]" ]] && echo "true" || echo "false")
            echo "    {"
            echo "      \"step\": $step,"
            echo "      \"name\": \"$name\","
            echo "      \"passed\": $passed,"
            echo "      \"message\": \"$(echo "$msg" | sed 's/"/\\"/g')\""
            echo -n "    }"
            [[ $idx -lt $count ]] && echo "," || echo ""
        done
        echo "  ]"
        echo "}"
    else
        print_validation_report "$header"
    fi

    return $VALIDATION_PASSED
}

# ------------------------------------------------------------------------------
# Subcommand: draft
# ------------------------------------------------------------------------------

cmd_draft() {
    local as_json="$1"

    local status_raw
    status_raw=$(git status --porcelain 2>/dev/null || true)

    if [[ -z "$status_raw" ]]; then
        if [[ "$as_json" == "true" ]]; then
            echo '{ "status": "clean", "staged_files": [], "unstaged_files": [] }'
        else
            echo "Working tree is completely clean. Nothing to commit."
        fi
        return 0
    fi

    local staged=()
    local unstaged=()

    while IFS= read -r line; do
        [[ -z "$line" ]] && continue
        local idx_status="${line:0:1}"
        local wrk_status="${line:1:1}"
        local file="${line:3}"

        if [[ "$idx_status" =~ [MADR] ]]; then
            staged+=("$file")
        fi
        if [[ "$wrk_status" =~ [MD] || "$idx_status" == "?" ]]; then
            unstaged+=("$file")
        fi
    done <<< "$status_raw"

    local violations=()
    local warnings=()
    scan_security violations warnings || true

    local inferred_scope="root"
    local inferred_type="feat"
    infer_scope_and_type inferred_scope inferred_type

    if [[ "$as_json" == "true" ]]; then
        echo "{"
        echo "  \"staged_count\": ${#staged[@]},"
        echo "  \"unstaged_count\": ${#unstaged[@]},"
        echo "  \"security_passed\": $([[ ${#violations[@]} -eq 0 ]] && echo "true" || echo "false"),"
        echo "  \"inferred_scope\": \"$inferred_scope\","
        echo "  \"inferred_type\": \"$inferred_type\","
        echo "  \"suggested_template\": \"$inferred_type($inferred_scope): <imperative_verb> <description>\""
        echo "}"
        return 0
    fi

    echo "======================================================================"
    echo " GIT STATUS SUMMARY & DRAFT SUGGESTIONS"
    echo "======================================================================"
    echo "Staged files (${#staged[@]}):"
    for f in "${staged[@]}"; do
        echo "  + $f"
    done
    if [[ ${#staged[@]} -eq 0 ]]; then
        echo "  (No files currently staged. Use 'git add <files>' first)"
    fi

    echo ""
    echo "Unstaged/Untracked files (${#unstaged[@]}):"
    for f in "${unstaged[@]}"; do
        echo "  - $f"
    done

    echo ""
    echo "--- Security & Hygiene Pre-Scan ---"
    if [[ ${#violations[@]} -eq 0 ]]; then
        echo "[PASS] No sensitive files, tokens, or merge conflict markers detected."
        echo "       (Note: .env.example / templates are explicitly allowed)"
    else
        echo "[FAIL] Security violations found:"
        for v in "${violations[@]}"; do
            echo "  ! $v"
        done
    fi

    if [[ ${#warnings[@]} -gt 0 ]]; then
        echo ""
        echo "--- Warnings ---"
        for w in "${warnings[@]}"; do
            echo "  ? $w"
        done
    fi

    echo ""
    echo "--- Smart Suggestions ---"
    echo "Inferred Scope: '$inferred_scope' | Inferred Type: '$inferred_type'"
    echo "Template: $inferred_type($inferred_scope): <imperative_verb> <description (10-120 chars)>"
    echo "======================================================================"
    return 0
}

# ------------------------------------------------------------------------------
# Subcommand: status
# ------------------------------------------------------------------------------

cmd_status() {
    local as_json="$1"

    local branch
    branch=$(git branch --show-current 2>/dev/null || echo "detached")
    local status_raw
    status_raw=$(git status -s 2>/dev/null || true)
    local unpushed_raw
    unpushed_raw=$(git log "@{u}..HEAD" --oneline 2>/dev/null || true)

    local staged=()
    local unstaged=()
    while IFS= read -r line; do
        [[ -z "$line" ]] && continue
        local idx_status="${line:0:1}"
        local wrk_status="${line:1:1}"
        local file="${line:3}"
        if [[ "$idx_status" =~ [MADR] ]]; then
            staged+=("$file")
        fi
        if [[ "$wrk_status" =~ [MD] || "$idx_status" == "?" ]]; then
            unstaged+=("$file")
        fi
    done <<< "$status_raw"

    local unpushed=()
    while IFS= read -r line; do
        [[ -z "$line" ]] && continue
        unpushed+=("$line")
    done <<< "$unpushed_raw"

    local violations=()
    local warnings=()
    scan_security violations warnings || true

    if [[ "$as_json" == "true" ]]; then
        echo "{"
        echo "  \"branch\": \"$branch\","
        echo "  \"staged_count\": ${#staged[@]},"
        echo "  \"unstaged_count\": ${#unstaged[@]},"
        echo "  \"unpushed_count\": ${#unpushed[@]},"
        echo "  \"security_passed\": $([[ ${#violations[@]} -eq 0 ]] && echo "true" || echo "false")"
        echo "}"
        return 0
    fi

    echo "======================================================================"
    echo " REPOSITORY STATUS OVERVIEW (Branch: $branch)"
    echo "======================================================================"
    echo "Staged changes   : ${#staged[@]} files"
    for f in "${staged[@]}"; do
        echo "  + $f"
    done
    echo "Unstaged changes : ${#unstaged[@]} files"
    for f in "${unstaged[@]}"; do
        echo "  - $f"
    done
    echo "Unpushed commits : ${#unpushed[@]} commits"
    for c in "${unpushed[@]}"; do
        echo "  * $c"
    done
    echo "======================================================================"
    return 0
}

# ------------------------------------------------------------------------------
# Subcommand: commit
# ------------------------------------------------------------------------------

cmd_commit() {
    local full_message="$1"
    local as_json="$2"

    local status_raw
    status_raw=$(git status --porcelain 2>/dev/null || true)
    if [[ -z "$status_raw" ]]; then
        echo "[NO CHANGES] Working tree is completely clean. No changes detected to commit."
        return 0
    fi

    local staged_diff
    staged_diff=$(git diff --cached --name-only 2>/dev/null || true)
    if [[ -z "$staged_diff" ]]; then
        echo "ERROR: [NO STAGED CHANGES] Changes exist in working tree, but none are staged." >&2
        echo "Please stage files using 'git add <files>' first before committing." >&2
        return 1
    fi

    # 1. Run Tier 1: Security & Hygiene Scan
    local violations=()
    local warnings=()
    if ! scan_security violations warnings; then
        echo "" >&2
        echo "======================================================================" >&2
        echo " [SECURITY ALERT] Commit Aborted Due to Security Violations" >&2
        echo "======================================================================" >&2
        for v in "${violations[@]}"; do
            echo "  ! $v" >&2
        done
        echo "======================================================================" >&2
        return 1
    fi

    # 2. Run Tier 2: 10-Step Message Validation
    validate_commit_message "$full_message"
    local header
    header="$(echo "$full_message" | head -n 1)"

    if [[ "$as_json" != "true" ]]; then
        print_validation_report "$header"
    fi

    if [[ $VALIDATION_PASSED -ne 0 ]]; then
        echo "ERROR: Commit aborted due to pre-flight validation failure." >&2
        return 1
    fi

    # 3. Execute git commit
    if [[ "$as_json" != "true" ]]; then
        echo ""
        echo "Executing git commit..."
    fi

    local commit_output
    if ! commit_output=$(git commit -m "$full_message" 2>&1); then
        echo "Git commit failed:" >&2
        echo "$commit_output" >&2
        return 1
    fi

    local log_out
    log_out=$(git log -1 --stat 2>/dev/null || true)

    if [[ "$as_json" == "true" ]]; then
        echo "{"
        echo "  \"status\": \"committed\","
        echo "  \"message\": \"$(echo "$header" | sed 's/"/\\"/g')\""
        echo "}"
    else
        echo "$commit_output"
        echo ""
        echo "Commit successful! Latest commit verified:"
        echo "$log_out"
    fi

    return 0
}

# ------------------------------------------------------------------------------
# Subcommand: sync
# ------------------------------------------------------------------------------

cmd_sync() {
    local full_message="$1"
    local as_json="$2"

    if ! cmd_commit "$full_message" "$as_json"; then
        return 1
    fi

    local branch
    branch=$(git branch --show-current 2>/dev/null || echo "HEAD")

    if [[ "$as_json" != "true" ]]; then
        echo ""
        echo "--- Syncing to Remote Repository ---"
        echo "Pushing to origin/$branch..."
    fi

    local push_output
    if ! push_output=$(git push origin "$branch" 2>&1); then
        # Check if upstream tracking needs to be set
        if echo "$push_output" | grep -Eq "(no upstream branch|set-upstream)"; then
            if [[ "$as_json" != "true" ]]; then
                echo "Setting upstream tracking for branch '$branch'..."
            fi
            if ! push_output=$(git push --set-upstream origin "$branch" 2>&1); then
                echo "Git push failed:" >&2
                echo "$push_output" >&2
                return 1
            fi
        else
            echo "Git push failed:" >&2
            echo "$push_output" >&2
            return 1
        fi
    fi

    if [[ "$as_json" == "true" ]]; then
        echo "{"
        echo "  \"status\": \"synced\","
        echo "  \"branch\": \"$branch\""
        echo "}"
    else
        echo "Successfully committed and pushed to origin/$branch!"
    fi
    return 0
}

# ------------------------------------------------------------------------------
# Subcommand: branch
# ------------------------------------------------------------------------------

cmd_branch() {
    local branch_name="$1"
    local as_json="$2"

    local valid_prefixes="feat/ fix/ chore/ docs/ refactor/ test/"
    local prefix_ok=false
    for p in $valid_prefixes; do
        if [[ "$branch_name" == "$p"* ]]; then
            prefix_ok=true
            break
        fi
    done

    if ! $prefix_ok; then
        local err="Branch '$branch_name' must start with one of: $valid_prefixes"
        if [[ "$as_json" == "true" ]]; then
            echo "{ \"error\": \"$err\" }"
        else
            echo "ERROR: $err" >&2
        fi
        return 1
    fi

    local out
    if ! out=$(git checkout -b "$branch_name" 2>&1); then
        echo "Branch creation failed:" >&2
        echo "$out" >&2
        return 1
    fi

    if [[ "$as_json" == "true" ]]; then
        echo "{ \"status\": \"created\", \"branch\": \"$branch_name\" }"
    else
        echo "Created and switched to branch '$branch_name' successfully."
    fi
    return 0
}

# ------------------------------------------------------------------------------
# Subcommand: undo
# ------------------------------------------------------------------------------

cmd_undo() {
    local as_json="$1"

    local last_commit
    last_commit=$(git log -1 --oneline 2>/dev/null || true)
    if [[ -z "$last_commit" ]]; then
        echo "ERROR: No commits found to undo." >&2
        return 1
    fi

    local out
    if ! out=$(git reset --soft HEAD~1 2>&1); then
        echo "Undo failed:" >&2
        echo "$out" >&2
        return 1
    fi

    if [[ "$as_json" == "true" ]]; then
        echo "{ \"status\": \"undone\", \"reverted_commit\": \"$(echo "$last_commit" | sed 's/"/\\"/g')\" }"
    else
        echo "Undid commit: '$last_commit' (changes preserved in staging area)."
    fi
    return 0
}

# ------------------------------------------------------------------------------
# Subcommand: audit
# ------------------------------------------------------------------------------

cmd_audit() {
    local limit="${1:-10}"
    local as_json="$2"

    local total=0
    local compliant_count=0
    local audit_items=()

    local cur_hash=""
    local cur_subject=""
    local cur_body=""
    local in_body=false

    while IFS= read -r line || [[ -n "$line" ]]; do
        if [[ "$line" =~ ^COMMIT:(.*) ]]; then
            cur_hash="${BASH_REMATCH[1]}"
            cur_subject=""
            cur_body=""
            in_body=false
        elif [[ "$line" =~ ^SUBJECT:(.*) ]]; then
            cur_subject="${BASH_REMATCH[1]}"
            in_body=false
        elif [[ "$line" == "BODY:" ]]; then
            in_body=true
        elif [[ "$line" == "END_COMMIT" ]]; then
            if [[ -n "$cur_hash" ]]; then
                total=$((total + 1))
                local full_commit_msg="$cur_subject"
                local clean_body="$(echo "$cur_body" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
                [[ -n "$clean_body" ]] && full_commit_msg="$full_commit_msg"$'\n\n'"$clean_body"

                validate_commit_message "$full_commit_msg"
                if [[ $VALIDATION_PASSED -eq 0 ]]; then
                    compliant_count=$((compliant_count + 1))
                    audit_items+=("$cur_hash@@@[PASS]@@@$cur_subject@@@")
                else
                    local failing_reasons=""
                    for sr in "${STEP_RESULTS[@]}"; do
                        IFS="|" read -r s_num s_name s_stat s_msg <<< "$sr"
                        if [[ "$s_stat" == "[FAIL]" ]]; then
                            failing_reasons="$failing_reasons; $s_msg"
                        fi
                    done
                    failing_reasons="${failing_reasons#; }"

                    # Generate suggested rewrite
                    local suggested=""
                    if [[ "$cur_subject" =~ $RE_HEADER ]]; then
                        local raw_t="${BASH_REMATCH[1]}"
                        local raw_s="${BASH_REMATCH[3]}"
                        local raw_d="${BASH_REMATCH[5]}"
                        local clean_t="chore"
                        for at in $ALLOWED_TYPES; do
                            [[ "$raw_t" == "$at" ]] && clean_t="$raw_t"
                        done
                        local clean_s="${raw_s:-general}"
                        clean_s=$(echo "$clean_s" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9-]/-/g')
                        local v_first
                        v_first=$(echo "$raw_d" | awk '{print $1}' | tr '[:upper:]' '[:lower:]')
                        local is_v_ok=false
                        for pv in "${COMMON_IMPERATIVE_VERBS[@]}"; do
                            [[ "$v_first" == "$pv" ]] && is_v_ok=true
                        done
                        $is_v_ok || v_first="update"
                        local v_rest
                        v_rest=$(echo "$raw_d" | cut -d' ' -f2- | sed 's/\.$//')
                        suggested="$clean_t($clean_s): $v_first $v_rest"
                    else
                        local s_words
                        s_words=$(echo "$cur_subject" | sed 's/\.$//')
                        suggested="chore(general): update $s_words"
                    fi

                    audit_items+=("$cur_hash@@@[FAIL]@@@$cur_subject@@@$failing_reasons@@@$suggested")
                fi
            fi
            cur_hash=""
            cur_subject=""
            cur_body=""
            in_body=false
        elif $in_body; then
            cur_body="$cur_body"$'\n'"$line"
        fi
    done < <(git log -n "$limit" --pretty=format:"COMMIT:%h%nSUBJECT:%s%nBODY:%b%nEND_COMMIT" 2>/dev/null || true)

    if [[ $total -eq 0 ]]; then
        echo "No commit history found to audit." >&2
        return 1
    fi

    local score=100
    if [[ $total -gt 0 ]]; then
        score=$(( (compliant_count * 100) / total ))
    fi

    if [[ "$as_json" == "true" ]]; then
        echo "{"
        echo "  \"total_commits\": $total,"
        echo "  \"compliant_commits\": $compliant_count,"
        echo "  \"compliance_score\": $score"
        echo "}"
        return 0
    fi

    echo "======================================================================"
    echo " GIT COMMIT HISTORY AUDIT & COMPLIANCE REPORT (Last $total Commits)"
    echo "======================================================================"
    echo "Analyzed: $total commits | Compliant: $compliant_count ($score%) | Non-compliant: $(( total - compliant_count ))"
    echo "----------------------------------------------------------------------"
    for item in "${audit_items[@]}"; do
        local ihash="${item%%@@@*}"
        local remainder="${item#*@@@}"
        local istat="${remainder%%@@@*}"
        remainder="${remainder#*@@@}"
        local isub="${remainder%%@@@*}"
        remainder="${remainder#*@@@}"
        local jreasons="${remainder%%@@@*}"
        local jsuggest="${remainder#*@@@}"

        if [[ "$istat" == "[PASS]" ]]; then
            echo "[PASS] $ihash $isub"
        else
            echo "[FAIL] $ihash \"$isub\""
            IFS=";" read -ra reason_arr <<< "$jreasons"
            for r in "${reason_arr[@]}"; do
                local clean_r="$(echo "$r" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
                [[ -n "$clean_r" ]] && echo "       ! $clean_r"
            done
            if [[ -n "$jsuggest" && "$jsuggest" != "$item" ]]; then
                echo "       >>> Suggested Rewrite: $jsuggest"
            fi
        fi
    done
    echo "======================================================================"
    echo "Overall Compliance Score: $score/100"
    echo "======================================================================"
    return 0
}

# ------------------------------------------------------------------------------
# Subcommand: check-env
# ------------------------------------------------------------------------------

cmd_check_env() {
    local as_json="$1"

    local git_ver
    git_ver=$(git --version 2>/dev/null || echo "")
    local git_ok=$([[ -n "$git_ver" ]] && echo "true" || echo "false")

    local user_name
    user_name=$(git config user.name 2>/dev/null || echo "")
    local user_email
    user_email=$(git config user.email 2>/dev/null || echo "")
    local author_ok=$([[ -n "$user_name" && -n "$user_email" ]] && echo "true" || echo "false")

    local bash_ver="${BASH_VERSION:-unknown}"
    local os_platform
    os_platform=$(uname -s 2>/dev/null || echo "$OSTYPE")

    local all_ok=$([[ "$git_ok" == "true" && "$author_ok" == "true" ]] && echo "true" || echo "false")

    if [[ "$as_json" == "true" ]]; then
        echo "{"
        echo "  \"all_ok\": $all_ok,"
        echo "  \"git\": {"
        echo "    \"installed\": $git_ok,"
        echo "    \"version\": \"$git_ver\","
        echo "    \"user_name\": \"$user_name\","
        echo "    \"user_email\": \"$user_email\""
        echo "  },"
        echo "  \"environment\": {"
        echo "    \"bash_version\": \"$bash_ver\","
        echo "    \"platform\": \"$os_platform\""
        echo "  }"
        echo "}"
        [[ "$all_ok" == "true" ]] && return 0 || return 1
    fi

    echo "======================================================================"
    echo " ENVIRONMENT DIAGNOSTIC (NATIVE BASH GIT SUITE)"
    echo "======================================================================"
    echo "Platform       : $os_platform (Bash $bash_ver) [PASS]"
    if [[ "$git_ok" == "true" ]]; then
        echo "Git Executable : $git_ver [PASS]"
    else
        echo "Git Executable : NOT FOUND [FAIL]"
        echo "  ! Please install Git (e.g. 'sudo apt install git' or 'brew install git')"
    fi

    if [[ "$author_ok" == "true" ]]; then
        echo "Git Author     : $user_name <$user_email> [PASS]"
    else
        echo "Git Author     : Incomplete configuration [WARN]"
        [[ -z "$user_name" ]] && echo "  ! Missing user.name (run: git config --global user.name 'Your Name')"
        [[ -z "$user_email" ]] && echo "  ! Missing user.email (run: git config --global user.email 'you@example.com')"
    fi
    echo "======================================================================"
    echo "All native runtime requirements checked (No Python required)."
    echo "======================================================================"
    [[ "$all_ok" == "true" ]] && return 0 || return 1
}

# ------------------------------------------------------------------------------
# Usage / Help
# ------------------------------------------------------------------------------

show_help() {
    cat << 'EOF'
git_helper.sh - Deterministic Git Suite runner for AI agents & developers.

High-Frequency Usage:
  bash git_helper.sh "<message>"          # Commit + push to remote (/git default)
  bash git_helper.sh commit "<message>"   # Commit local only (/git commit)
  bash git_helper.sh status               # Show staged, unstaged & security status
  bash git_helper.sh undo                 # Safely undo last commit (retains staging)

Subcommands:
  sync      Validate, commit and push to remote upstream branch
  commit    Validate and execute local git commit
  status    Overview of working tree, branch, unpushed commits, and security
  draft     Inspect git status, security scan, and suggest commit scopes/drafts
  validate  Validate a commit message string (10-step Conventional Commits)
  branch    Create and checkout branch enforcing conventional prefixes (feat/, fix/...)
  undo      Safe soft reset of last commit
  audit     Audit past N commits for Conventional Commits compliance
  check-env Diagnostic check of Git and environment

Message Options (for commit/sync):
  "<message>"              Pass full commit message directly as argument
  -m, --message <desc>     Imperative description (10-120 chars)
  -t, --type <type>        Whitelisted commit type (feat, fix, docs, refactor, chore, test)
  -s, --scope <scope>      Lowercase kebab-case scope
  -b, --bullet <bullet>    Optional body bullet point (repeatable)
  --raw <message>          Raw full commit message
  --json                   Output machine-readable JSON format
EOF
}

# ------------------------------------------------------------------------------
# Main Dispatcher
# ------------------------------------------------------------------------------

main() {
    local subcommand=""
    local as_json=false
    local opt_type=""
    local opt_scope=""
    local opt_desc=""
    local opt_raw=""
    local opt_bullets=()
    local opt_limit=10
    local positional_args=()

    # Parse command-line arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --json)
                as_json=true
                shift
                ;;
            -t|--type)
                opt_type="$2"
                shift 2
                ;;
            -s|--scope)
                opt_scope="$2"
                shift 2
                ;;
            -m|--message)
                opt_desc="$2"
                shift 2
                ;;
            -b|--bullet)
                opt_bullets+=("$2")
                shift 2
                ;;
            --raw)
                opt_raw="$2"
                shift 2
                ;;
            -n|--limit)
                opt_limit="$2"
                shift 2
                ;;
            -h|--help|help)
                show_help
                return 0
                ;;
            *)
                positional_args+=("$1")
                shift
                ;;
        esac
    done

    # Determine subcommand
    local first_pos="${positional_args[0]:-}"
    case "$first_pos" in
        commit|sync|status|draft|validate|branch|undo|audit|check-env)
            subcommand="$first_pos"
            positional_args=("${positional_args[@]:1}")
            ;;
        *)
            # If no known subcommand is passed:
            if [[ -n "$first_pos" || -n "$opt_raw" || -n "$opt_desc" || -n "$opt_type" ]]; then
                # User passed a message or flags directly -> Default to 'sync' (/git workflow)
                subcommand="sync"
            else
                # No args provided at all -> if staged changes exist, run draft; otherwise status
                subcommand="draft"
            fi
            ;;
    esac

    # Dispatch subcommand
    case "$subcommand" in
        validate)
            local msg="${opt_raw:-${positional_args[0]:-}}"
            if [[ -z "$msg" ]]; then
                echo "ERROR: Message required for validate. Usage: git_helper.sh validate \"<message>\"" >&2
                return 1
            fi
            cmd_validate "$msg" "$as_json"
            ;;
        draft)
            cmd_draft "$as_json"
            ;;
        status)
            cmd_status "$as_json"
            ;;
        branch)
            local bname="${positional_args[0]:-}"
            if [[ -z "$bname" ]]; then
                echo "ERROR: Branch name required. Usage: git_helper.sh branch <name>" >&2
                return 1
            fi
            cmd_branch "$bname" "$as_json"
            ;;
        undo)
            cmd_undo "$as_json"
            ;;
        audit)
            cmd_audit "$opt_limit" "$as_json"
            ;;
        check-env)
            cmd_check_env "$as_json"
            ;;
        commit|sync)
            local full_msg=""
            if [[ -n "$opt_raw" ]]; then
                full_msg="$opt_raw"
            elif [[ -n "${positional_args[0]:-}" ]]; then
                full_msg="${positional_args[0]}"
                if [[ ${#opt_bullets[@]} -gt 0 ]]; then
                    local bstr=""
                    for b in "${opt_bullets[@]}"; do
                        local clean_b="${b#- }"
                        bstr="$bstr"$'\n'"- $clean_b"
                    done
                    full_msg="$full_msg"$'\n'"$bstr"
                fi
            elif [[ -n "$opt_desc" ]]; then
                if [[ -n "$opt_type" && -n "$opt_scope" ]]; then
                    full_msg="$opt_type($opt_scope): $opt_desc"
                else
                    # If only description was given via -m, check if it already has type(scope)
                    full_msg="$opt_desc"
                fi
                if [[ ${#opt_bullets[@]} -gt 0 ]]; then
                    local bstr=""
                    for b in "${opt_bullets[@]}"; do
                        local clean_b="${b#- }"
                        bstr="$bstr"$'\n'"- $clean_b"
                    done
                    full_msg="$full_msg"$'\n'"$bstr"
                fi
            else
                echo "ERROR: Commit message is required." >&2
                echo "Usage examples:" >&2
                echo "  git_helper.sh \"feat(auth): implement jwt refresh\"" >&2
                echo "  git_helper.sh commit \"fix(api): handle timeout\"" >&2
                echo "  git_helper.sh -t feat -s auth -m \"implement jwt refresh\"" >&2
                return 1
            fi

            if [[ "$subcommand" == "commit" ]]; then
                cmd_commit "$full_msg" "$as_json"
            else
                cmd_sync "$full_msg" "$as_json"
            fi
            ;;
    esac
}

main "$@"
