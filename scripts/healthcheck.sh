#!/bin/sh

set -e

echo "Checking health for http://127.0.0.1:${PORT}/health/..."
curl -f http://127.0.0.1:${PORT}/health/
