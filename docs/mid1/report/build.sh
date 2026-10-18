#!/bin/sh
# Builds the FYP-1 Mid report with tectonic (brew install tectonic). Output: build.pdf
cd "$(dirname "$0")" && tectonic -X compile build.tex "$@"
