#!/bin/bash

# Usage: ./ongoing_printer.sh /path/to/binary [args...]

# Run the binary in background
"$@" &
pid=$!

# Print message to stderr until process ends
while kill -0 "$pid" 2>/dev/null; do
    echo "Ongoing..." >&2
    sleep 5
done

# Final newline on stderr for neatness
echo >&2

# Wait for process to actually finish and capture exit status
wait "$pid"
exit $?
