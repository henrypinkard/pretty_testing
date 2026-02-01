#!/bin/bash
# debug_kit/bin/w
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILDER="$REPO_ROOT/builder.py"
mkdir -p custom

# --- 1. SETUP SAFE BUILDER ---
cat "$BUILDER" \
  | sed "s/my_/watch_/g" \
  | sed "s/raise e/pass/g" \
  > custom/make_watch_test.py

# --- 2. COLORS ---
green=$(tput setaf 2)
red=$(tput setaf 1)
bold=$(tput bold)
reset=$(tput sgr0)
dim=$(tput dim)
blue=$(tput setaf 4)
yellow=$(tput setaf 3)

# --- 3. STATE ---
last_run_time=""
last_valid_buffer=""
last_valid_detail=""
current_syntax_error=""
current_runtime_error=""
is_syntax_error=false
test_source_dir="tests"
first_fail_file=""
last_debugged_method=""
first_fail_line=0
PUDB_BP_FILE="${HOME}/.config/pudb/saved-breakpoints-$(python3 -c 'import sys;print(f"{sys.version_info.major}.{sys.version_info.minor}")')"

# --- 4. CORE FUNCTION ---
run_tests() {
    # RESET ERRORS
    current_runtime_error=""
    
    # A. SELECT SOURCE
    # CHANGED: Look for *.py instead of level_*_tests.py
    if [ -d "custom_tests" ] && ls custom_tests/*.py >/dev/null 2>&1; then
        test_source_dir="custom_tests"
        display_source="CUSTOM TESTS ($test_source_dir)"
    else
        test_source_dir="tests"
        display_source="OFFICIAL TESTS ($test_source_dir)"
    fi

    # B. VALIDATE SOURCE (Fail Fast - Syntax Only)
    # CHANGED: Look for *.py
    files_to_check=$(find . -maxdepth 1 -name "*.py" -type f; find "$test_source_dir" -name "*.py" -type f)
    syntax_output=$(python3 -m py_compile $files_to_check 2>&1)
    
    if [ $? -ne 0 ]; then
        is_syntax_error=true
        current_syntax_error="$syntax_output"
        return
    fi

    # C. GENERATE RUNNERS
    # CHANGED: Remove generic watch files and loop over generic inputs
    rm -f custom/watch_*.py
    for f in "$test_source_dir"/*.py; do 
        [ -f "$f" ] || continue
        python3 custom/make_watch_test.py "$f" > /dev/null 2>&1
    done

    # D. SUCCESSFUL COMPILE
    is_syntax_error=false
    current_syntax_error=""
    last_run_time=$(date +"%H:%M:%S")
    new_buffer=""
    first_fail_method=""
    first_fail_file=""
    passed_methods=()
    failed_methods=()
    failed_files=()
    
    # E. RUN SWEEP
    # CHANGED: Look for any watch_*.py file
    for watch_file in $(ls custom/watch_*.py 2>/dev/null | sort -V); do
        # CHANGED: Use filename as label instead of extracting number
        file_label=$(basename "$watch_file" .py | sed 's/watch_//')
        new_buffer+=$'\n'"${bold}File: ${file_label}${reset}"$'\n'
        
        has_tests_in_level=false
        
        # 1. Capture ALL output
        raw_output=$(python3 "$watch_file" 2>&1)
        
        # 2. Parse for Test Results
        while IFS= read -r line; do
             if [[ "$line" == "passed:"* ]]; then
                 test_name=$(echo "$line" | cut -d' ' -f2)
                 new_buffer+="  [${green}PASS${reset}] $test_name"$'\n'
                 has_tests_in_level=true
                 passed_methods+=("$test_name")
             elif [[ "$line" == "FAILED_METHOD:"* ]]; then
                 test_name=$(echo "$line" | cut -d' ' -f2)
                 new_buffer+="  [${red}FAIL${reset}] $test_name"$'\n'
                 has_tests_in_level=true
                 failed_methods+=("$test_name")
                 if [ -z "$first_fail_method" ]; then
                     first_fail_method="$test_name"
                 fi
                 # Track source file with failure
                 fail_src="$test_source_dir/${file_label}.py"
                 if [ -f "$fail_src" ]; then
                     failed_files+=("$(cd "$(dirname "$fail_src")" && pwd)/$(basename "$fail_src")")
                 fi
             elif [[ "$line" == "NO_TESTS_FOUND_IN_FILE" ]]; then
                 new_buffer+="  [${yellow}WARNING${reset}] No methods starting with 'test_' found.$'\n'"
             fi
        done <<< "$raw_output"

        # 3. CRASH DETECTION (BLOCKING MODE)
        if [ "$has_tests_in_level" = false ]; then
            if [[ "$raw_output" == *"Traceback"* ]] || [[ "$raw_output" == *"Error"* ]]; then
                 # PROCESS & COLORIZE THE CRASH
                 current_runtime_error=$(echo "$raw_output" | python3 -c "
import sys, re
full_log = sys.stdin.read()
lines = full_log.splitlines()
last_frame_start = -1
for i, line in enumerate(lines):
    if line.strip().startswith('File \"'):
        last_frame_start = i
crash_lines = lines[last_frame_start:] if last_frame_start != -1 else lines
def colorize(text_lines):
    out = []
    for line in text_lines:
        match = re.search(r'(File \")(.*?)(\", line )(\d+)(, in )(.*)', line)
        if match:
            prefix, path, mid1, lineno, mid2, method = match.groups()
            out.append(f'  {prefix}\033[34m{path}\033[0m{mid1}\033[32m{lineno}\033[0m{mid2}\033[33m{method}\033[0m')
            continue
        if 'Error:' in line or 'Exception:' in line:
            out.append(f'\033[31m{line}\033[0m') 
            continue
        if '    ' in line:
             out.append(f'\033[1m{line}\033[0m') 
             continue
        out.append(line)
    return out
colored_lines = colorize(crash_lines)
print('\n'.join(colored_lines))
")
                 return  # STOP PROCESSING
            fi
        fi
    done

    # F. DEEP DIVE (Only if valid failure found)
    new_detail=""
    if [ -n "$first_fail_method" ]; then
        # CHANGED: Robust lookup. Find the file that contains the failing method.
        # This avoids all file-naming guesswork.
        orig_file=$(grep -l "def $first_fail_method" "$test_source_dir"/*.py | head -n 1)
        
        if [ -n "$orig_file" ]; then
            first_fail_file="$orig_file"
            python3 "$BUILDER" "$orig_file" "$first_fail_method" > /dev/null 2>&1
            
            # 1. GET FAIL LINE
            err_out=$(python3 custom/my_test.py 2>&1)
            fail_line=$(echo "$err_out" | grep -P "File \".*custom/my_test.py\", line \d+, in $first_fail_method" | tail -n 1 | grep -oP 'line \K\d+')
            if [ -z "$fail_line" ]; then fail_line=0; fi
            first_fail_line="$fail_line"

            # 2. EXTRACT SOURCE (up to failing line) + ERROR MESSAGE
            source_and_error=$(python3 -c "
import ast, re, os, sys
os.environ['TERM'] = 'xterm-256color'
try:
    from pygments import highlight
    from pygments.lexers import PythonLexer
    from pygments.formatters import TerminalFormatter
    has_pygments = True
except ImportError:
    has_pygments = False

file_path = 'custom/my_test.py'
target_name = '$first_fail_method'
fail_line_abs = int('$fail_line')
orig_file = '$orig_file'

try:
    with open(file_path, 'r') as f:
        source = f.read()

    tree = ast.parse(source)
    method_node = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == target_name:
            method_node = node
            break

    if method_node:
        rel_fail_idx = fail_line_abs - method_node.lineno
        # Only show lines up to and including the failing line
        end = fail_line_abs if fail_line_abs > 0 else method_node.end_lineno
        lines = source.splitlines()[method_node.lineno-1 : end]
        if lines:
            indent_size = len(lines[0]) - len(lines[0].lstrip())
            lines = [line[indent_size:] for line in lines]
        code_str = '\n'.join(lines)
        if has_pygments:
            formatted = highlight(code_str, PythonLexer(), TerminalFormatter())
        else:
            formatted = code_str
        out_lines = formatted.splitlines()
        final_lines = []
        for i, line in enumerate(out_lines):
            if i == rel_fail_idx and fail_line_abs > 0:
                line = f'\x1b[91m--> \x1b[0m{line}'
            else:
                line = f'    {line}'
            final_lines.append(line)
        print('\n'.join(final_lines))
    else:
        print('Method source not found.')
except Exception as e:
    print(f'Error extracting source: {e}')
")

            # 3. RUN AND PARSE EXECUTION LOG + ERROR
            raw_trace=$(python3 custom/my_test.py 2>&1)

            parsed_sections=$(echo "$raw_trace" | python3 -c "
import sys, re
try:
    from pygments import highlight
    from pygments.lexers import PythonLexer
    from pygments.formatters import TerminalFormatter
    has_pygments = True
except ImportError:
    has_pygments = False

state = 0
buf_log = []
failure_summary = []

def colorize_code(code_str):
    if has_pygments:
        try:
            return highlight(code_str, PythonLexer(), TerminalFormatter()).rstrip()
        except:
            pass
    code_str = re.sub(r'(\".*?\"|\'.*?\')', r'\033[32m\1\033[0m', code_str)
    code_str = re.sub(r'\b(\d+)\b', r'\033[36m\1\033[0m', code_str)
    keywords = r'\b(def|class|return|if|else|elif|while|for|in|try|except|import|from|as|pass|None|True|False)\b'
    code_str = re.sub(keywords, r'\033[33m\1\033[0m', code_str)
    code_str = re.sub(r'\b(self)\b', r'\033[35m\1\033[0m', code_str)
    return code_str

for line in sys.stdin:
    clean = re.sub(r'\x1b\[[0-9;]*m', '', line).strip()
    if '___TEST_START___' in clean: state = 1; continue
    if '___FAILURE_SUMMARY_START___' in clean: state = 5; continue
    if '___FAILURE_SUMMARY_END___' in clean: state = 1; continue

    if state == 5:
        failure_summary.append(line.strip())
        continue
    if state == 1:
        if clean.startswith('[EXE] '):
            code = clean.replace('[EXE] ', '')
            colored_code = colorize_code(code)
            buf_log.append(f'  \033[1;34m>>\033[0m {colored_code}\n')
        elif 'Traceback (most recent call last)' in clean:
            state = 3  # skip traceback lines
        else:
            buf_log.append(f'  \033[2m{line}\033[0m')
    elif state == 3:
        pass  # discard traceback

print('___SECTION_SEP___')
print('\\n'.join(failure_summary))
print('___SECTION_SEP___')
print(''.join(buf_log))
")
            error_msg=$(echo "$parsed_sections" | awk 'BEGIN{RS="___SECTION_SEP___"} NR==2')
            exec_log=$(echo "$parsed_sections" | awk 'BEGIN{RS="___SECTION_SEP___"} NR==3')

            # --- BUILD DETAIL: Source + Error + Exec Log ---
            new_detail+=$'\n'"${bold}==========================================${reset}"$'\n'
            new_detail+="${bold}${blue}$(basename "$orig_file")${reset} ${dim}:: ${first_fail_method}${reset}"$'\n'
            new_detail+="${bold}------------------------------------------${reset}"$'\n'
            new_detail+="$source_and_error"

            if [ -n "$error_msg" ]; then
                new_detail+=$'\n'
                colored_summary=$(echo "$error_msg" | python3 -c "
import sys, re
for line in sys.stdin:
    line = line.rstrip()
    if not line: continue
    # Error type header (standalone line like 'AssertionError:')
    if line.endswith(':') and ('Error' in line or 'Exception' in line):
        print(f'  \033[1;31m{line}\033[0m')
        continue
    # Actual value
    m2 = re.match(r'(\s*Actual:\s*)(.*)', line)
    if m2:
        print(f'  \033[1mActual:   \033[33m{m2.group(2)}\033[0m')
        continue
    # Expected value
    m3 = re.match(r'(\s*Expected:\s*)(.*)', line)
    if m3:
        print(f'  \033[1mExpected: \033[32m{m3.group(2)}\033[0m')
        continue
    # Generic error (e.g. TypeError: msg)
    m4 = re.match(r'(\w+(?:Error|Exception)):\s*(.*)', line)
    if m4:
        print(f'  \033[1;31m{m4.group(1)}:\033[0m {m4.group(2)}')
        continue
    print(f'  {line}')
")
                new_detail+="$colored_summary"
            fi

            if [ -n "$exec_log" ]; then
                new_detail+=$'\n'"${bold}------------------------------------------${reset}"$'\n'
                new_detail+="${bold}EXECUTION LOG:${reset}"$'\n'
                new_detail+="$exec_log"
            fi
        else
            new_detail+=$'\n'"${yellow}Could not locate source file containing '$first_fail_method'${reset}"
        fi
    fi

    # G. CLEAN BREAKPOINTS FOR LAST DEBUGGED METHOD IF IT NOW PASSES
    if [ -n "$last_debugged_method" ] && [ -f "$PUDB_BP_FILE" ]; then
        # Check if the method we were debugging is now passing
        method_still_failing=false
        for fm in "${failed_methods[@]}"; do
            if [ "$fm" = "$last_debugged_method" ]; then
                method_still_failing=true
                break
            fi
        done
        if [ "$method_still_failing" = false ]; then
            # Method passed — clear breakpoints from the generated debug file
            grep -v "custom/my_test.py" "$PUDB_BP_FILE" > "${PUDB_BP_FILE}.tmp" 2>/dev/null && mv "${PUDB_BP_FILE}.tmp" "$PUDB_BP_FILE"
            last_debugged_method=""
        fi
    fi

    last_valid_buffer="$new_buffer"
    last_valid_detail="$new_detail"
}

# --- 5. UI UPDATE ---
draw_screen() {
    # NUCLEAR CLEAR (Wipes everything + Scrollback)
    printf '\033[2J\033[3J\033[H'
    
    if [ "$is_syntax_error" = true ]; then
        # --- MODE 1: SYNTAX ERROR ---
        echo "${bold}Last Run: $(date +"%H:%M:%S")${reset}"
        echo ""
        echo "${bold}${red}==========================================${reset}"
        echo "${bold}${red}           COMPILATION ERROR              ${reset}"
        echo "${bold}${red}==========================================${reset}"
        echo ""
        echo "$current_syntax_error"
        
    elif [ -n "$current_runtime_error" ]; then
        # --- MODE 2: RUNTIME ERROR (CRASH) ---
        echo "${bold}Last Run: $(date +"%H:%M:%S")${reset}"
        echo ""
        echo "${bold}${red}==========================================${reset}"
        echo "${bold}${red}            EXECUTION ERROR               ${reset}"
        echo "${bold}${red}==========================================${reset}"
        echo ""
        echo -e "$current_runtime_error"
        
    else
        # --- MODE 3: DASHBOARD ---
        echo "${bold}Last Run: $last_run_time  ${blue}[$display_source]${reset}"
        echo -e "$last_valid_buffer"
        if [ -n "$last_valid_detail" ]; then echo -e "$last_valid_detail"; fi
    fi
}

# --- 6. MAIN LOOP ---
# INITIAL NUCLEAR CLEAR
printf '\033[2J\033[3J\033[H'
echo "${bold}Starting Test Monitor...${reset}"
run_tests
draw_screen

launch_pudb() {
    if [ -z "$first_fail_method" ] || [ -z "$first_fail_file" ]; then
        return
    fi
    # Track which method we're debugging for breakpoint cleanup
    last_debugged_method="$first_fail_method"
    # Ensure the single-method test file is generated
    python3 "$BUILDER" "$first_fail_file" "$first_fail_method" > /dev/null 2>&1
    # Prepare debug version: remove timeouts, inject set_trace at start of test method
    python3 -c "
import re, ast
with open('custom/my_test.py') as f:
    lines = f.readlines()
# Remove @timeout decorators
cleaned = [l for l in lines if not re.match(r'\s*@timeout\(', l)]
# Neuter signal.alarm
cleaned = [re.sub(r'signal\.alarm\(\w+\)', 'signal.alarm(0)', l) for l in cleaned]
# Find the test method, inject set_trace at start + breakpoint at fail line
import os
fail_line = $first_fail_line
removed = sum(1 for l in lines[:max(0,fail_line-1)] if re.match(r'\s*@timeout\(', l))
adj_fail = fail_line - removed if fail_line > 0 else 0
source = ''.join(cleaned)
tree = ast.parse(source)
my_test_abs = os.path.abspath('custom/my_test.py')
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == '$first_fail_method':
        body_line = node.body[0].lineno - 1  # 0-indexed
        indent = len(cleaned[body_line]) - len(cleaned[body_line].lstrip())
        inject_lines = ' ' * indent + 'import pudb; pudb.set_trace()\n'
        if adj_fail > 0:
            bp_target = adj_fail + 1  # +1 for the set_trace line we insert
            inject_lines += ' ' * indent + 'pudb._get_debugger().set_break(\"' + my_test_abs + '\", ' + str(bp_target) + ')\n'
        cleaned.insert(body_line, inject_lines)
        break
with open('custom/my_test.py', 'w') as f:
    f.writelines(cleaned)
"
    python3 custom/my_test.py
    # Back to dashboard — rerun tests (file may have changed) and redraw
    run_tests
    draw_screen
}

last_checksum=""
while true; do
    # Check for keypress (non-blocking, 1s timeout replaces sleep)
    if read -rsn1 -t 1 key 2>/dev/null; then
        if [ "$key" = "d" ]; then
            launch_pudb
            continue
        fi
    fi
    # CHANGED: Ensure checksum watches ALL py files
    current_checksum=$(find . "$test_source_dir" -name "*.py" -not -path "./custom/*" -exec stat -c %Y {} + 2>/dev/null | md5sum)
    if [ "$current_checksum" != "$last_checksum" ]; then
        if [ -n "$last_checksum" ]; then
            run_tests
            draw_screen
        fi
        last_checksum="$current_checksum"
    fi
done