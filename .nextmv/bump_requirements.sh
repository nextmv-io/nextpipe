#!/bin/bash

# This script bumps the nextpipe version in all requirements.txt files of the project.

# Usage: bump_requirements.sh <new_version>
# Example: bump_requirements.sh v0.1.0
# The 'v' prefix will get stripped off automatically.

set -euo pipefail

# Check if the version argument is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <new_version>"
  exit 1
fi
# Get the new version from the first argument
NEW_VERSION=$1
# Remove the 'v' prefix if it exists
if [[ $NEW_VERSION == v* ]]; then
  NEW_VERSION=${NEW_VERSION:1}
fi

# Change to the project root directory
# This assumes the script is located in the .nextmv directory
# and the project root is one level up
cd "$(dirname "$0")/.." || exit 1

# Find all requirements.txt files in the project
REQUIREMENTS_FILES=$(find . -name "requirements.txt")
# Check if any requirements.txt files were found
if [ -z "$REQUIREMENTS_FILES" ]; then
  echo "No requirements.txt files found."
  exit 1
fi

# Loop through each requirements.txt file and update the nextpipe version
for FILE in $REQUIREMENTS_FILES; do
  # In-place update the nextpipe version
  sed -i "s/nextpipe==.*/nextpipe==$NEW_VERSION/" "$FILE"
done
