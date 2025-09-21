#!/bin/sh

set -e

echo "Checking health for http://localhost:${PORT}..."
curl -f http://localhost:${PORT}
