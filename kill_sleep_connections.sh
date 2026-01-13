#!/bin/bash

# --- Configuration ---
DB_USER="eaurqb"
DB_PASS="eaur2025!!"
DB_HOST=24.144.88.39
DB_NAME="miseaurac_db"    # not used for KILL, but required by mysql CLI
TARGET_USER="eaurqb"
TARGET_HOST="178.62.215.167%" # Target host pattern for sleeping connections

# --- Fetch sleeping connection IDs ---
IDS=$(mysql -u"$DB_USER" -p"$DB_PASS" -h "$DB_HOST" -N -e \
"SELECT id FROM information_schema.processlist
 WHERE user='$TARGET_USER' 
   AND host LIKE '$TARGET_HOST'
   AND command='Sleep';")

# --- Kill each connection ---
if [ -z "$IDS" ]; then
    echo "No sleeping connections found for $TARGET_USER@$TARGET_HOST."
else
    for id in $IDS; do
        echo "Killing connection ID: $id"
        mysql -u"$DB_USER" -p"$DB_PASS" -h "$DB_HOST" -N -e "KILL $id;"
    done
    echo "Done."
fi
