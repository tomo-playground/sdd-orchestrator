#!/bin/bash
cd "$(dirname "$0")/frontend"
npx next dev --webpack --hostname 0.0.0.0
