#!/usr/bin/env bash
set -e

echo "=== Uploading Episoda Alpha MCP (Episodai) to PyPI ==="
if [ -z "$PYPI_TOKEN" ]; then
  read -s -p "Enter PyPI API Token (pypi-...): " PYPI_TOKEN
  echo ""
fi

python3 -m twine upload dist/episodai-2.1.0* -u __token__ -p "$PYPI_TOKEN"
echo "✓ Successfully published to https://pypi.org/project/episodai/"
