#!/bin/bash
# debug_kit/bin/w
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILDER="$REPO_ROOT/test_generator.py"
OUTPUT_PARSER="$REPO_ROOT/output_parser.py"
DEBUG_PREP="$REPO_ROOT/debug_prep.py"
mkdir -p _pretty_testing_

# --- 0. PARSE ARGS ---
STOP_EARLY=false
NO_REFRESH=false
FAILED_ONLY=false
CUSTOM_TEST_DIR=""
TEST_TIMEOUT=2
while [[ $# -gt 0 ]]; do
    case "$1" in
        --stop|-s)
            STOP_EARLY=true
            shift
            ;;
        --no-refresh|-n)
            NO_REFRESH=true
            shift
            ;;
        --failed|-f)
            FAILED_ONLY=true
            shift
            ;;
        --test-dir|-t)
            CUSTOM_TEST_DIR="$2"
            shift 2
            ;;
        --timeout|-T)
            TEST_TIMEOUT="$2"
            shift 2
            ;;
        -[sfn]*)
            # Handle combined short flags like -sf, -fs, -sfn, etc.
            flags="${1#-}"
            shift
            while [ -n "$flags" ]; do
                c="${flags%"${flags#?}"}"
                flags="${flags#?}"
                case "$c" in
                    s) STOP_EARLY=true ;;
                    f) FAILED_ONLY=true ;;
                    n) NO_REFRESH=true ;;
                esac
            done
            ;;
        *)
            shift
            ;;
    esac
done
export PRETTY_TESTING_TIMEOUT="$TEST_TIMEOUT"

# --- 1. SETUP SAFE BUILDER ---
cat "$BUILDER" \
  | sed "s/debug_this_test_/watch_/g" \
  | sed "s/debug_this_test\\.py/watch_.py/g" \
  | sed "s/raise e/pass/g" \
  > _pretty_testing_/make_watch_test.py

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
last_debug_error=""
user_error_file=""
user_error_line=0
# Track previous test results to detect status changes
declare -A prev_test_status=()  # test_name -> "pass" or "fail"
declare -A prev_file_has_fail=()  # file_label -> "1" if any test failed
TEST_STATUS_FILE="_pretty_testing_/.test_status"
FILE_STATUS_FILE="_pretty_testing_/.file_status"
# Load previous test status from file if it exists
if [ -f "$TEST_STATUS_FILE" ]; then
    while IFS='=' read -r name status; do
        [ -n "$name" ] && prev_test_status["$name"]="$status"
    done < "$TEST_STATUS_FILE"
fi
# Load previous file status
if [ -f "$FILE_STATUS_FILE" ]; then
    while IFS='=' read -r name status; do
        [ -n "$name" ] && prev_file_has_fail["$name"]="$status"
    done < "$FILE_STATUS_FILE"
fi
PUDB_BP_FILE="${HOME}/.config/pudb/saved-breakpoints-$(python3 -c 'import sys;print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
last_debugged_method=""

# --- 4. CORE FUNCTION ---
run_tests() {
    # RESET ERRORS
    current_runtime_error=""
    last_debug_error=""

    # Track current run's test status (will become prev_test_status after this run)
    declare -A cur_test_status=()
    declare -A cur_file_has_fail=()  # Track which files have failures this run

    # A. SELECT SOURCE
    if [ -n "$CUSTOM_TEST_DIR" ]; then
        # User specified a custom test directory with -t/--test-dir
        test_source_dir="$CUSTOM_TEST_DIR"
        display_source="TESTS ($test_source_dir)"
    elif [ -d "custom_tests" ] && ls custom_tests/*.py >/dev/null 2>&1; then
        test_source_dir="custom_tests"
        display_source="CUSTOM TESTS ($test_source_dir)"
    else
        test_source_dir="tests"
        display_source="OFFICIAL TESTS ($test_source_dir)"
    fi

    # B. VALIDATE SOURCE (Fail Fast - Syntax Only)
    # In failed-only mode, only check files that will actually be run
    syntax_output=""
    is_syntax_error=false
    if [ "$FAILED_ONLY" = true ]; then
        # Only check root-level .py files + test files that had failures
        check_files=$(find . -maxdepth 1 -name "*.py" -type f)
        for f in "$test_source_dir"/*.py; do
            [ -f "$f" ] || continue
            file_label=$(basename "$f" .py)
            if [ "${prev_file_has_fail[$file_label]}" = "1" ]; then
                check_files+=$'\n'"$f"
            fi
        done
    else
        check_files=$(find . -maxdepth 1 -name "*.py" -type f; find "$test_source_dir" -name "*.py" -type f)
    fi

    # Batch syntax check in a single Python process
    syntax_output=$(echo "$check_files" | python3 -c "
import sys, py_compile
errors = []
for line in sys.stdin:
    f = line.strip()
    if not f: continue
    try:
        py_compile.compile(f, doraise=True)
    except py_compile.PyCompileError as e:
        errors.append(str(e))
if errors:
    print('\n'.join(errors))
    sys.exit(1)
" 2>&1)
    if [ $? -ne 0 ]; then
        is_syntax_error=true
        current_syntax_error="$syntax_output"
        return
    fi

    # C. GENERATE RUNNERS
    rm -f _pretty_testing_/watch_*.py

    # Write run list for failed-only mode (only failed tests, everything else ignored)
    if [ "$FAILED_ONLY" = true ]; then
        : > _pretty_testing_/.run_tests
        for key in "${!prev_test_status[@]}"; do
            if [ "${prev_test_status[$key]}" = "fail" ]; then
                echo "$key" >> _pretty_testing_/.run_tests
            fi
        done
    else
        rm -f _pretty_testing_/.run_tests
    fi

    for f in "$test_source_dir"/*.py; do
        [ -f "$f" ] || continue
        # In failed-only mode, skip files where all tests passed
        if [ "$FAILED_ONLY" = true ]; then
            file_label=$(basename "$f" .py)
            if [ "${prev_file_has_fail[$file_label]}" != "1" ]; then
                continue
            fi
        fi
        python3 _pretty_testing_/make_watch_test.py "$f" > /dev/null 2>&1
        # -sf combo: only need the first file with failures
        if [ "$FAILED_ONLY" = true ] && [ "$STOP_EARLY" = true ]; then
            break
        fi
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

    # E. RUN SWEEP (stop after first file with failures) - real-time output
    stop_after_this_file=false
    declare -A file_times
    declare -a file_order
    declare -A file_tests

    # Print live progress header (incremental — no full redraws)
    printf '\033[?25l\033[2J\033[3J\033[H'
    printf '\033[K%s\n' "${bold}Last Run: $last_run_time  ${blue}[$display_source]${reset}"

    for watch_file in $(ls _pretty_testing_/watch_*.py 2>/dev/null | sort -V); do
        file_label=$(basename "$watch_file" .py | sed 's/watch_//')
        file_order+=("$file_label")
        file_start=$(date +%s.%N)
        file_tests[$file_label]=""

        has_tests_in_level=false
        raw_output=""

        # Print file header for live progress
        printf '\033[K\n\033[K%s\n' "${bold}File: ${file_label}${reset}"

        # Stream output line by line — print each result incrementally
        while IFS= read -r line; do
            # Only collect raw output for crash detection (before first test result)
            if [ "$has_tests_in_level" = false ]; then
                raw_output+="$line"$'\n'
            fi
            if [[ "$line" == "passed:"* ]]; then
                test_name="${line#passed: }"
                # Highlight if status changed from fail to pass
                if [ "${prev_test_status[$test_name]}" = "fail" ]; then
                    tline="${bold}${green}→ [PASS] $test_name${reset}"
                else
                    tline="  [${green}PASS${reset}] $test_name"
                fi
                file_tests[$file_label]+="$tline"$'\n'
                printf '\033[K%s\n' "$tline"
                cur_test_status[$test_name]="pass"
                has_tests_in_level=true
                passed_methods+=("$test_name")
            elif [[ "$line" == "FAILED_METHOD:"* ]]; then
                test_name="${line#FAILED_METHOD: }"
                # Highlight if status changed from pass to fail
                if [ "${prev_test_status[$test_name]}" = "pass" ]; then
                    tline="${bold}${red}→ [FAIL] $test_name${reset}"
                else
                    tline="  [${red}FAIL${reset}] $test_name"
                fi
                file_tests[$file_label]+="$tline"$'\n'
                printf '\033[K%s\n' "$tline"
                cur_test_status[$test_name]="fail"
                cur_file_has_fail[$file_label]="1"
                has_tests_in_level=true
                failed_methods+=("$test_name")
                stop_after_this_file=true
                if [ -z "$first_fail_method" ]; then
                    first_fail_method="$test_name"
                fi
                fail_src="$test_source_dir/${file_label}.py"
                if [ -f "$fail_src" ]; then
                    failed_files+=("$(cd "$(dirname "$fail_src")" && pwd)/$(basename "$fail_src")")
                fi
                # Default: stop on first failure (unless -a/--all)
                if [ "$STOP_EARLY" = true ]; then
                    break
                fi
            elif [[ "$line" == "skipped:"* ]]; then
                test_name="${line#skipped: }"
                tline="  [${dim}SKIP${reset}] $test_name"
                file_tests[$file_label]+="$tline"$'\n'
                printf '\033[K%s\n' "$tline"
                has_tests_in_level=true
            elif [[ "$line" == "NO_TESTS_FOUND_IN_FILE" ]]; then
                tline="  [${yellow}WARNING${reset}] No methods starting with 'test_' found."
                file_tests[$file_label]+="$tline"$'\n'
                printf '\033[K%s\n' "$tline"
            fi
        done < <(python3 "$watch_file" 2>&1)

        # Record elapsed time with one decimal place
        file_end=$(date +%s.%N)
        file_elapsed=$(echo "$file_end - $file_start" | bc)
        file_elapsed=$(printf "%.1f" "$file_elapsed")
        file_times[$file_label]="${file_elapsed}s"

        # CRASH DETECTION
        if [ "$has_tests_in_level" = false ]; then
            if [[ "$raw_output" == *"Traceback"* ]] || [[ "$raw_output" == *"Error"* ]]; then
                 current_runtime_error=$(echo "$raw_output" | python3 "$OUTPUT_PARSER" crash 2>/dev/null || echo "$raw_output")
                 return
            fi
        fi

        # Stop processing more files if this file had failures (unless --all mode)
        if [ "$stop_after_this_file" = true ] && [ "$STOP_EARLY" = true ]; then
            break
        fi
    done

    # Build final buffer for draw_screen
    new_buffer=""
    for fl in "${file_order[@]}"; do
        local ftime="${file_times[$fl]:-}"
        new_buffer+=$'\n'"${bold}File: ${fl}${reset} ${dim}(${ftime})${reset}"$'\n'
        new_buffer+="${file_tests[$fl]}"
    done

    # F. DEEP DIVE (Only if valid failure found)
    new_detail=""
    if [ -n "$first_fail_method" ]; then
        orig_file=$(grep -l "def $first_fail_method" "$test_source_dir"/*.py | head -n 1)

        if [ -n "$orig_file" ]; then
            first_fail_file="$orig_file"
            python3 "$BUILDER" "$orig_file" "$first_fail_method" > /dev/null 2>&1

            # 1. RUN TEST ONCE — reuse output for all analysis
            test_output=$(python3 _pretty_testing_/debug_this_test.py 2>&1)
            fail_line=$(echo "$test_output" | python3 "$OUTPUT_PARSER" extract-fail-line "debug_this_test.py" "$first_fail_method" 2>/dev/null)
            if [ -z "$fail_line" ] || [ "$fail_line" = "0" ]; then fail_line=0; fi
            first_fail_line="$fail_line"

            # Extract user code error location (file:line where exception originated)
            user_error_loc=$(echo "$test_output" | python3 "$OUTPUT_PARSER" user-error-loc "_pretty_testing_/debug_this_test.py" 2>/dev/null)
            if [ -n "$user_error_loc" ]; then
                user_error_file=$(echo "$user_error_loc" | cut -d: -f1)
                user_error_line=$(echo "$user_error_loc" | cut -d: -f2)
            else
                user_error_file=""
                user_error_line=0
            fi

            # 2. EXTRACT SOURCE
            source_and_error=$(python3 "$OUTPUT_PARSER" source _pretty_testing_/debug_this_test.py "$first_fail_method" "$fail_line" 2>/dev/null || echo "(source extraction failed)")

            # 3. PARSE EXECUTION LOG + ERROR from same output
            parsed_sections=$(echo "$test_output" | python3 "$OUTPUT_PARSER" trace 2>/dev/null || echo "___SECTION_SEP___${test_output}___SECTION_SEP___")
            error_msg=$(echo "$parsed_sections" | awk 'BEGIN{RS="___SECTION_SEP___"} NR==2')
            exec_log=$(echo "$parsed_sections" | awk 'BEGIN{RS="___SECTION_SEP___"} NR==3')

            # --- BUILD DETAIL ---
            new_detail+=$'\n'"${bold}==========================================${reset}"$'\n'
            new_detail+="${bold}${blue}$(basename "$orig_file")${reset} ${dim}:: ${first_fail_method}${reset}"$'\n'
            new_detail+="${bold}------------------------------------------${reset}"$'\n'
            new_detail+="$source_and_error"

            if [ -n "$error_msg" ]; then
                new_detail+=$'\n\n'
                colored_summary=$(echo "$error_msg" | python3 "$OUTPUT_PARSER" error 2>/dev/null || echo "$error_msg")
                new_detail+="$colored_summary"
                new_detail+=$'\n'
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
        method_still_failing=false
        for fm in "${failed_methods[@]}"; do
            if [ "$fm" = "$last_debugged_method" ]; then
                method_still_failing=true
                break
            fi
        done
        if [ "$method_still_failing" = false ]; then
            # Test passed — clear all saved breakpoints (test file + user code)
            : > "$PUDB_BP_FILE"
            last_debugged_method=""
        fi
    fi

    last_valid_buffer="$new_buffer"
    last_valid_detail="$new_detail"

    # Update previous test status for next run's comparison
    for key in "${!cur_test_status[@]}"; do
        prev_test_status[$key]="${cur_test_status[$key]}"
    done

    # Save test status to file for persistence across sessions
    : > "$TEST_STATUS_FILE"  # truncate/create file
    for key in "${!prev_test_status[@]}"; do
        echo "${key}=${prev_test_status[$key]}" >> "$TEST_STATUS_FILE"
    done

    # Update file-level failure status
    # Only update files that were actually run this time
    for key in "${file_order[@]}"; do
        if [ "${cur_file_has_fail[$key]}" = "1" ]; then
            prev_file_has_fail[$key]="1"
        else
            # File was run and had no failures - clear it
            unset prev_file_has_fail[$key]
        fi
    done
    : > "$FILE_STATUS_FILE"
    for key in "${!prev_file_has_fail[@]}"; do
        echo "${key}=${prev_file_has_fail[$key]}" >> "$FILE_STATUS_FILE"
    done
}

# --- 5. UI UPDATE ---
draw_screen() {
    printf '\033[?25l\033[2J\033[3J\033[H'

    if [ "$is_syntax_error" = true ]; then
        echo "${bold}Last Run: $(date +"%H:%M:%S")${reset}"
        echo ""
        echo "${bold}${red}==========================================${reset}"
        echo "${bold}${red}           COMPILATION ERROR              ${reset}"
        echo "${bold}${red}==========================================${reset}"
        echo ""
        echo "$current_syntax_error" | python3 "$OUTPUT_PARSER" syntax 2>/dev/null || echo "$current_syntax_error"

    elif [ -n "$current_runtime_error" ]; then
        echo "${bold}Last Run: $(date +"%H:%M:%S")${reset}"
        echo ""
        echo "${bold}${red}==========================================${reset}"
        echo "${bold}${red}            EXECUTION ERROR               ${reset}"
        echo "${bold}${red}==========================================${reset}"
        echo ""
        echo -e "$current_runtime_error"

    else
        echo "${bold}Last Run: $last_run_time  ${blue}[$display_source]${reset}"
        echo -e "$last_valid_buffer"
        if [ -n "$last_valid_detail" ]; then echo -e "$last_valid_detail"; fi
        if [ -n "$last_debug_error" ]; then
            echo ""
            echo "${bold}${red}==========================================${reset}"
            echo "${bold}${red}         LAST DEBUG SESSION ERROR         ${reset}"
            echo "${bold}${red}==========================================${reset}"
            echo ""
            echo -e "$last_debug_error"
        fi
    fi

    # Help line
    echo ""
    local mode_info=""
    if [ "$STOP_EARLY" = true ]; then
        mode_info+="  ${yellow}[--stop]${reset}"
    fi
    if [ "$NO_REFRESH" = true ]; then
        mode_info+="  ${yellow}[--no-refresh]${reset}"
    fi
    if [ "$FAILED_ONLY" = true ]; then
        mode_info+="  ${yellow}[--failed]${reset}"
    fi
    if [ -n "$CUSTOM_TEST_DIR" ]; then
        mode_info+="  ${yellow}[-t $CUSTOM_TEST_DIR]${reset}"
    fi
    if [ "$TEST_TIMEOUT" != "2" ]; then
        mode_info+="  ${yellow}[-T ${TEST_TIMEOUT}s]${reset}"
    fi
    echo "${dim}  [d] PUDB  [p] PDB++  [q] Quit  |  -s stop@fail  -f failed-only  -n no-refresh  -t <dir>  -T <sec>${mode_info}${reset}"
}

# --- 6. MAIN LOOP ---
# Hide cursor during operation, restore on exit
printf '\033[?25l'
trap 'printf "\033[?25h\n"; exit 0' INT TERM EXIT
printf '\033[2J\033[3J\033[H'
echo "${bold}Starting Test Monitor...${reset}"
run_tests
draw_screen

launch_debugger() {
    local debugger="$1"  # "pudb" or "pdbpp"
    if [ -z "$first_fail_method" ] || [ -z "$first_fail_file" ]; then
        return
    fi
    last_debug_error=""

    if [ "$debugger" = "pudb" ]; then
        # Fix theme and variable display in pudb config
        PUDB_CFG="$HOME/.config/pudb/pudb.cfg"
        if [ -f "$PUDB_CFG" ]; then
            DARCULA_PATH="$REPO_ROOT/darcula.py"
            sed -i "s|^theme =.*|theme = $DARCULA_PATH|" "$PUDB_CFG"
            # Set variable representation to repr (shows actual values)
            sed -i "s|^stringifier =.*|stringifier = default|" "$PUDB_CFG"
        fi
    fi

    last_debugged_method="$first_fail_method"

    # Show launching message
    printf '\033[2J\033[H'
    echo "${dim}Launching $debugger for $first_fail_method...${reset}"

    # Clear stale breakpoints for debug_this_test.py BEFORE regenerating
    # The file is regenerated every time with different line numbers, so
    # saved breakpoints would point to wrong lines anyway
    if [ -f "$PUDB_BP_FILE" ]; then
        # Note: grep -v returns exit code 1 when no lines are output (all filtered),
        # so we use || true to ensure mv always runs
        { grep -v "debug_this_test.py" "$PUDB_BP_FILE" || true; } > "${PUDB_BP_FILE}.tmp" 2>/dev/null
        mv "${PUDB_BP_FILE}.tmp" "$PUDB_BP_FILE"
    fi

    # Generate single-method test file
    builder_output=$(python3 "$BUILDER" "$first_fail_file" "$first_fail_method" 2>&1)
    if [ $? -ne 0 ]; then
        last_debug_error="Builder failed:\n$builder_output"
        draw_screen
        return
    fi

    # Write error summary to temp file for debug_prep to inject
    if [ -n "$last_valid_detail" ]; then
        {
            echo -e "${dim}[Error Summary - Press 'o' to return to PUDB]${reset}"
            echo ""
            echo -e "$last_valid_detail"
        } > _pretty_testing_/.error_summary
    else
        rm -f _pretty_testing_/.error_summary
    fi

    # Prepare debug version (prep + preflight + setUp fallback in one step)
    debug_args=(debug _pretty_testing_/debug_this_test.py --method "$first_fail_method" --fail-line "$first_fail_line" --debugger "$debugger")
    if [ -n "$user_error_file" ] && [ "$user_error_line" -gt 0 ]; then
        debug_args+=(--user-error-file "$user_error_file" --user-error-line "$user_error_line")
    fi
    python3 "$DEBUG_PREP" "${debug_args[@]}" 2>/dev/null

    if [ $? -ne 0 ]; then
        # Last resort: inject a simple set_trace at top
        if [ "$debugger" = "pdbpp" ]; then
            sed -i '1s/^/import pdb; pdb.set_trace()\n/' _pretty_testing_/debug_this_test.py 2>/dev/null
        else
            sed -i '1s/^/import pudb; pudb.set_trace()\n/' _pretty_testing_/debug_this_test.py 2>/dev/null
        fi
    fi

    printf '\033[2J\033[3J\033[H'
    PRETTY_TESTING_DEBUG=1 python3 _pretty_testing_/debug_this_test.py

    run_tests
    draw_screen

    # Update checksum to current state so edits made during debugging
    # don't trigger an immediate refresh
    if [ -d "custom_tests" ] && ls custom_tests/*.py >/dev/null 2>&1; then
        watch_dir="custom_tests"
    else
        watch_dir="tests"
    fi
    watched_files=$(find . -maxdepth 1 -name "*.py" -type f 2>/dev/null; find "$watch_dir" -name "*.py" -type f 2>/dev/null)
    last_checksum=$(echo "$watched_files" | sort | xargs md5sum 2>/dev/null | md5sum)
}


last_checksum=""
while true; do
    if read -rsn1 -t 1 key 2>/dev/null; then
        if [ "$key" = "d" ]; then
            launch_debugger pudb
            continue
        elif [ "$key" = "p" ]; then
            launch_debugger pdbpp
            continue
        elif [ "$key" = "q" ] || [ "$key" = $'\x03' ]; then
            # q or Ctrl+C: quit
            printf '\033[?25h\n'
            exit 0
        fi
    fi
    # Determine test source dir for checksum (same logic as run_tests)
    if [ -d "custom_tests" ] && ls custom_tests/*.py >/dev/null 2>&1; then
        watch_dir="custom_tests"
    else
        watch_dir="tests"
    fi
    # Only watch: root-level *.py files + watch_dir/*.py (not tool files, not _pretty_testing_/)
    watched_files=$(find . -maxdepth 1 -name "*.py" -type f 2>/dev/null; find "$watch_dir" -name "*.py" -type f 2>/dev/null)
    current_checksum=$(echo "$watched_files" | sort | xargs md5sum 2>/dev/null | md5sum)
    if [ "$NO_REFRESH" = false ] && [ "$current_checksum" != "$last_checksum" ]; then
        if [ -n "$last_checksum" ]; then
            # Small delay to let file writes complete (avoid race with editor flush)
            sleep 0.1
            # Recompute checksum after delay to get final state
            watched_files=$(find . -maxdepth 1 -name "*.py" -type f 2>/dev/null; find "$watch_dir" -name "*.py" -type f 2>/dev/null)
            current_checksum=$(echo "$watched_files" | sort | xargs md5sum 2>/dev/null | md5sum)
            last_checksum="$current_checksum"
            run_tests
            draw_screen
            # Don't recompute checksum after run_tests - if user edited during
            # the run, we WANT to detect that change on the next iteration
        fi
        last_checksum="$current_checksum"
    fi
done
