#!/bin/bash
while read line; do
        echo "$(date): ${line}"
done
