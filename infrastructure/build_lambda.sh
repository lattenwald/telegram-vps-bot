#!/bin/bash
set -e

# Build script for Lambda deployment package with dependencies
# This script packages the Lambda function code with its dependencies

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="$SCRIPT_DIR/lambda_build"

echo "Building Lambda deployment package..."

# Clean previous build
rm -rf "$BUILD_DIR"

# Create build directory
mkdir -p "$BUILD_DIR"

# Install dependencies to build directory
echo "Installing dependencies..."
pip install -q -r "$PROJECT_ROOT/requirements.txt" -t "$BUILD_DIR" 2>&1 | grep -v "dependency conflicts" || true

# Copy source code
echo "Copying source code..."
cp -r "$PROJECT_ROOT/src/"* "$BUILD_DIR/"

echo "✓ Lambda deployment package ready: $BUILD_DIR"
