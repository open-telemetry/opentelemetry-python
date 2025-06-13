#!/bin/bash

OVERALL_EXIT_CODE=0
BRANCH_TO_COMPARE="main"
GRIFFE_CMD="griffe check -v -a $BRANCH_TO_COMPARE "

run_griffe_check() {
    local package_spec="$1"
    local package_name
    local search_path=""

    if [[ "$package_spec" == *"/"* ]]; then
        search_path=$(echo "$package_spec" | cut -d'/' -f1)
        package_name=$(echo "$package_spec" | cut -d'/' -f2)
        $GRIFFE_CMD -s "$search_path" "$package_name"
    else
        package_name="$package_spec"
        $GRIFFE_CMD "$package_name"
    fi
}

while read -r package; do
    if ! run_griffe_check "$package"; then
        OVERALL_EXIT_CODE=1
    fi
done < <(python "$(dirname "$0")/eachdist.py" list)

exit $OVERALL_EXIT_CODE
