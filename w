#!/bin/bash
# debug_kit/bin/w
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILDER="$REPO_ROOT/builder.py"
mkdir -p custom

# --- 1. SETUP SAFE BUILDER ---
if [ ! -f custom/make_watch_test.py ]; then
    cat "$BUILDER" \
      | sed "s/my_level/watch_level/g" \
      | sed "s/raise e/pass/g" \
      > custom/make_watch_test.py
fi

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
             elif [[ "$line" == "FAILED_METHOD:"* ]]; then
                 test_name=$(echo "$line" | cut -d' ' -f2)
                 new_buffer+="  [${red}FAIL${reset}] $test_name"$'\n'
                 has_tests_in_level=true
                 if [ -z "$first_fail_method" ]; then
                     first_fail_method="$test_name"
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
            python3 "$BUILDER" "$orig_file" "$first_fail_method" > /dev/null 2>&1
            
            # 1. GET FAIL LINE
            err_out=$(python3 custom/my_test.py 2>&1)
            fail_line=$(echo "$err_out" | grep -P "File \".*custom/my_test.py\", line \d+, in $first_fail_method" | tail -n 1 | grep -oP 'line \K\d+')
            if [ -z "$fail_line" ]; then fail_line=0; fi

            # 2. EXTRACT SOURCE
            source_code=$(python3 -c "
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
        lines = source.splitlines()[method_node.lineno-1 : method_node.end_lineno]
        rel_fail_idx = fail_line_abs - method_node.lineno
        if lines:
            indent = len(lines[0]) - len(lines[0].lstrip())
            lines = [line[indent:] for line in lines]
        code_str = '\n'.join(lines)
        if has_pygments:
            formatted = highlight(code_str, PythonLexer(), TerminalFormatter())
        else:
            formatted = code_str
        out_lines = formatted.splitlines()
        final_lines = []
        for i, line in enumerate(out_lines):
            if i == rel_fail_idx:
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
            
            # 3. RUN TRACEBACK
            raw_trace=$(python3 custom/my_test.py 2>&1)
            
            # 4. PARSE LOGS & COLORIZE EXECUTION
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
buf_trace = []
frame_buffer = []
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

def colorize_frame_line(line):
    pattern = r'(File \")(.*?)(\", line )(\d+)(, in )(.*)'
    match = re.search(pattern, line)
    if match:
        prefix, path, mid1, lineno, mid2, method = match.groups()
        return f'  {prefix}\033[34m{path}\033[0m{mid1}\033[32m{lineno}\033[0m{mid2}\033[33m{method}\033[0m\n'
    return line

def flush_frame(buffer, target_list):
    if not buffer: return
    full_text = ''.join(buffer)
    if 'timeout_decorator' in full_text: return
    if 'unittest' in full_text: return
    if 'getattr(test_instance' in full_text: return
    if 'sys.settrace' in full_text: return
    if 'decorator.py' in full_text: return
    buffer[0] = colorize_frame_line(buffer[0])
    target_list.extend(buffer)

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
        else:
            if 'Traceback (most recent call last)' in clean:
                 state = 3
                 buf_trace.append(f'\033[1;31m{line}\033[0m')
            else:
                buf_log.append(f'  \033[2m{line}\033[0m')
    elif state == 3 or state == 0:
        if line.lstrip().startswith('File '):
            flush_frame(frame_buffer, buf_trace)
            frame_buffer = [line]
        elif frame_buffer:
            frame_buffer.append(line)
        else:
            if not line.startswith(' '):
                buf_trace.append(f'\033[31m{line}\033[0m')
            else:
                buf_trace.append(line)

flush_frame(frame_buffer, buf_trace)

print('___SECTION_SEP___')
print('\\n'.join(failure_summary))
print('___SECTION_SEP___')
print(''.join(buf_log))
print('___SECTION_SEP___')
print(''.join(buf_trace))
")
            error_msg=$(echo "$parsed_sections" | awk 'BEGIN{RS="___SECTION_SEP___"} NR==2')
            exec_log=$(echo "$parsed_sections" | awk 'BEGIN{RS="___SECTION_SEP___"} NR==3')
            traceback=$(echo "$parsed_sections" | awk 'BEGIN{RS="___SECTION_SEP___"} NR==4')

            if [ -n "$error_msg" ]; then
                new_detail+=$'\n'"${bold}==========================================${reset}"$'\n'
                new_detail+="${bold}${red}FAILURE SUMMARY:${reset}"$'\n'
                colored_summary=$(echo "$error_msg" | python3 -c "
import sys, re
for line in sys.stdin:
    line = line.rstrip()
    # File reference line
    m = re.match(r'(File \")(.*?)(\", line )(\d+)(.*)', line)
    if m:
        print(f'  {m.group(1)}\033[34m{m.group(2)}\033[0m{m.group(3)}\033[32m{m.group(4)}\033[0m{m.group(5)}')
        continue
    # Error type header
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
    # Generic error line (e.g. TypeError: msg)
    m4 = re.match(r'(\w+(?:Error|Exception)):\s*(.*)', line)
    if m4:
        print(f'  \033[1;31m{m4.group(1)}:\033[0m {m4.group(2)}')
        continue
    print(f'  {line}')
")
                new_detail+="$colored_summary"
            fi

            new_detail+=$'\n'"${bold}==========================================${reset}"$'\n'
            new_detail+="${bold}FAILING METHOD SOURCE:${reset}"$'\n'
            new_detail+="$source_code"
            
            new_detail+=$'\n'"${bold}------------------------------------------${reset}"$'\n'
            new_detail+="${bold}CLEAN TRACEBACK:${reset}"$'\n'
            new_detail+="$traceback"
            
            new_detail+=$'\n'"${bold}------------------------------------------${reset}"$'\n'
            new_detail+="${bold}INTERACTIVE EXECUTION LOG:${reset}"$'\n'
            new_detail+="$exec_log"
        else
            new_detail+=$'\n'"${yellow}Could not locate source file containing '$first_fail_method'${reset}"
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

last_checksum=""
while true; do
    # CHANGED: Ensure checksum watches ALL py files
    current_checksum=$(find . "$test_source_dir" -name "*.py" -not -path "./custom/*" -exec stat -c %Y {} + 2>/dev/null | md5sum)
    if [ "$current_checksum" != "$last_checksum" ]; then
        if [ -n "$last_checksum" ]; then
            run_tests
            draw_screen
        fi
        last_checksum="$current_checksum"
    fi
    sleep 1
done