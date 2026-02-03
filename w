#!/bin/bash
# debug_kit/bin/w
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILDER="$REPO_ROOT/test_generator.py"
OUTPUT_PARSER="$REPO_ROOT/output_parser.py"
DEBUG_PREP="$REPO_ROOT/debug_prep.py"
mkdir -p custom

# --- 0. PARSE ARGS ---
STOP_ON_FIRST=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --stop-on-first|-f)
            STOP_ON_FIRST=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

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
last_debug_error=""
user_error_file=""
user_error_line=0
last_user_error_file=""
last_user_error_line=0
PUDB_BP_FILE="${HOME}/.config/pudb/saved-breakpoints-$(python3 -c 'import sys;print(f"{sys.version_info.major}.{sys.version_info.minor}")')"

# --- 4. CORE FUNCTION ---
run_tests() {
    # RESET ERRORS
    current_runtime_error=""
    last_debug_error=""

    # A. SELECT SOURCE
    if [ -d "custom_tests" ] && ls custom_tests/*.py >/dev/null 2>&1; then
        test_source_dir="custom_tests"
        display_source="CUSTOM TESTS ($test_source_dir)"
    else
        test_source_dir="tests"
        display_source="OFFICIAL TESTS ($test_source_dir)"
    fi

    # B. VALIDATE SOURCE (Fail Fast - Syntax Only)
    syntax_output=""
    is_syntax_error=false
    while IFS= read -r pyfile; do
        result=$(python3 -m py_compile "$pyfile" 2>&1)
        if [ $? -ne 0 ]; then
            is_syntax_error=true
            syntax_output+="$result"$'\n'
        fi
    done < <(find . -maxdepth 1 -name "*.py" -type f; find "$test_source_dir" -name "*.py" -type f)

    if [ "$is_syntax_error" = true ]; then
        current_syntax_error="$syntax_output"
        return
    fi

    # C. GENERATE RUNNERS
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

    # E. RUN SWEEP (stop after first file with failures) - real-time output
    stop_after_this_file=false
    for watch_file in $(ls custom/watch_*.py 2>/dev/null | sort -V); do
        file_label=$(basename "$watch_file" .py | sed 's/watch_//')
        file_start=$(date +%s)

        # Print file header immediately
        new_buffer+=$'\n'"${bold}File: ${file_label}${reset}"$'\n'
        printf '\033[2J\033[H'
        echo "${bold}Last Run: $last_run_time  ${blue}[$display_source]${reset}"
        echo -e "$new_buffer"

        has_tests_in_level=false
        raw_output=""

        # Stream output line by line for real-time display
        while IFS= read -r line; do
            raw_output+="$line"$'\n'
            if [[ "$line" == "passed:"* ]]; then
                test_name=$(echo "$line" | cut -d' ' -f2)
                new_buffer+="  [${green}PASS${reset}] $test_name"$'\n'
                has_tests_in_level=true
                passed_methods+=("$test_name")
                # Redraw
                printf '\033[2J\033[H'
                echo "${bold}Last Run: $last_run_time  ${blue}[$display_source]${reset}"
                echo -e "$new_buffer"
            elif [[ "$line" == "FAILED_METHOD:"* ]]; then
                test_name=$(echo "$line" | cut -d' ' -f2)
                new_buffer+="  [${red}FAIL${reset}] $test_name"$'\n'
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
                # Redraw
                printf '\033[2J\033[H'
                echo "${bold}Last Run: $last_run_time  ${blue}[$display_source]${reset}"
                echo -e "$new_buffer"
                # With --stop-on-first, stop reading more output
                if [ "$STOP_ON_FIRST" = true ]; then
                    break
                fi
            elif [[ "$line" == "skipped:"* ]]; then
                test_name=$(echo "$line" | cut -d' ' -f2)
                new_buffer+="  [${dim}SKIP${reset}] $test_name"$'\n'
                has_tests_in_level=true
                # Redraw
                printf '\033[2J\033[H'
                echo "${bold}Last Run: $last_run_time  ${blue}[$display_source]${reset}"
                echo -e "$new_buffer"
            elif [[ "$line" == "NO_TESTS_FOUND_IN_FILE" ]]; then
                new_buffer+="  [${yellow}WARNING${reset}] No methods starting with 'test_' found."$'\n'
                # Redraw
                printf '\033[2J\033[H'
                echo "${bold}Last Run: $last_run_time  ${blue}[$display_source]${reset}"
                echo -e "$new_buffer"
            fi
        done < <(python3 "$watch_file" 2>&1)

        # Update file header with elapsed time
        file_end=$(date +%s)
        file_elapsed=$((file_end - file_start))
        # Replace the file header line in buffer with one that includes time
        new_buffer=$(echo "$new_buffer" | sed "s/${bold}File: ${file_label}${reset}/${bold}File: ${file_label}${reset} ${dim}(${file_elapsed}s)${reset}/")

        # CRASH DETECTION
        if [ "$has_tests_in_level" = false ]; then
            if [[ "$raw_output" == *"Traceback"* ]] || [[ "$raw_output" == *"Error"* ]]; then
                 current_runtime_error=$(echo "$raw_output" | python3 "$OUTPUT_PARSER" crash 2>/dev/null || echo "$raw_output")
                 return
            fi
        fi

        # Stop processing more files if this file had failures
        if [ "$stop_after_this_file" = true ]; then
            break
        fi
    done

    # F. DEEP DIVE (Only if valid failure found)
    new_detail=""
    if [ -n "$first_fail_method" ]; then
        orig_file=$(grep -l "def $first_fail_method" "$test_source_dir"/*.py | head -n 1)

        if [ -n "$orig_file" ]; then
            first_fail_file="$orig_file"
            python3 "$BUILDER" "$orig_file" "$first_fail_method" > /dev/null 2>&1

            # 1. GET FAIL LINE (in test) AND USER ERROR LOCATION (in user code)
            err_out=$(python3 custom/debug_this_test.py 2>&1)
            fail_line=$(echo "$err_out" | grep -P "File \".*custom/debug_this_test.py\", line \d+, in $first_fail_method" | tail -n 1 | grep -oP 'line \K\d+')
            if [ -z "$fail_line" ]; then fail_line=0; fi
            first_fail_line="$fail_line"

            # Extract user code error location (file:line where exception originated)
            user_error_loc=$(echo "$err_out" | python3 "$OUTPUT_PARSER" user-error-loc "custom/debug_this_test.py" 2>/dev/null)
            if [ -n "$user_error_loc" ]; then
                user_error_file=$(echo "$user_error_loc" | cut -d: -f1)
                user_error_line=$(echo "$user_error_loc" | cut -d: -f2)
            else
                user_error_file=""
                user_error_line=0
            fi

            # 2. EXTRACT SOURCE
            source_and_error=$(python3 "$OUTPUT_PARSER" source custom/debug_this_test.py "$first_fail_method" "$fail_line" 2>/dev/null || echo "(source extraction failed)")

            # 3. RUN AND PARSE EXECUTION LOG + ERROR
            raw_trace=$(python3 custom/debug_this_test.py 2>&1)
            parsed_sections=$(echo "$raw_trace" | python3 "$OUTPUT_PARSER" trace 2>/dev/null || echo "___SECTION_SEP___${raw_trace}___SECTION_SEP___")
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
            # Remove breakpoints from the test file
            grep -v "custom/debug_this_test.py" "$PUDB_BP_FILE" > "${PUDB_BP_FILE}.tmp" 2>/dev/null && mv "${PUDB_BP_FILE}.tmp" "$PUDB_BP_FILE"
            # Also remove breakpoints from the user code file if we set one there
            if [ -n "$last_user_error_file" ] && [ "$last_user_error_line" -gt 0 ]; then
                grep -v "${last_user_error_file}:${last_user_error_line}:" "$PUDB_BP_FILE" > "${PUDB_BP_FILE}.tmp" 2>/dev/null && mv "${PUDB_BP_FILE}.tmp" "$PUDB_BP_FILE"
                last_user_error_file=""
                last_user_error_line=0
            fi
            last_debugged_method=""
        fi
    fi

    last_valid_buffer="$new_buffer"
    last_valid_detail="$new_detail"
}

# --- 5. UI UPDATE ---
draw_screen() {
    printf '\033[2J\033[3J\033[H'

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
    echo "${dim}  [d] debug (pudb)  [p] debug (pdb++)  |  run: help${reset}"
}

# --- 6. MAIN LOOP ---
trap 'printf "\n"; exit 0' INT TERM
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
        # Fix theme in pudb config in case it got wiped by prefs save
        PUDB_CFG="$HOME/.config/pudb/pudb.cfg"
        if [ -f "$PUDB_CFG" ]; then
            DARCULA_PATH="$REPO_ROOT/darcula.py"
            sed -i "s|^theme =.*|theme = $DARCULA_PATH|" "$PUDB_CFG"
        fi
    fi

    last_debugged_method="$first_fail_method"
    # Track user error location for cleanup later
    last_user_error_file="$user_error_file"
    last_user_error_line="$user_error_line"

    # Generate single-method test file
    builder_output=$(python3 "$BUILDER" "$first_fail_file" "$first_fail_method" 2>&1)
    if [ $? -ne 0 ]; then
        last_debug_error="Builder failed:\n$builder_output"
        draw_screen
        return
    fi

    # Prepare debug version (prep + preflight + setUp fallback in one step)
    debug_args=(debug custom/debug_this_test.py --method "$first_fail_method" --fail-line "$first_fail_line" --debugger "$debugger")
    if [ -n "$user_error_file" ] && [ "$user_error_line" -gt 0 ]; then
        debug_args+=(--user-error-file "$user_error_file" --user-error-line "$user_error_line")
    fi
    python3 "$DEBUG_PREP" "${debug_args[@]}" 2>/dev/null

    if [ $? -ne 0 ]; then
        # Last resort: inject a simple set_trace at top
        if [ "$debugger" = "pdbpp" ]; then
            sed -i '1s/^/import pdb; pdb.set_trace()\n/' custom/debug_this_test.py 2>/dev/null
        else
            sed -i '1s/^/import pudb; pudb.set_trace()\n/' custom/debug_this_test.py 2>/dev/null
        fi
    fi

    printf '\033[2J\033[3J\033[H'
    python3 custom/debug_this_test.py

    run_tests
    draw_screen
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
        fi
    fi
    current_checksum=$(find . "$test_source_dir" -name "*.py" -not -path "./custom/*" -exec stat -c %Y {} + 2>/dev/null | md5sum)
    if [ "$current_checksum" != "$last_checksum" ]; then
        if [ -n "$last_checksum" ]; then
            run_tests
            draw_screen
        fi
        last_checksum="$current_checksum"
    fi
done
