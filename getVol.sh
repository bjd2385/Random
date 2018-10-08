#! /bin/bash
# Print included volumes in snapshots in /home/agents/*/.zfs/snapshot/.
#
# Syntax verified with shellcheck v0.5.0
# https://github.com/koalaman/shellcheck
#
# Brandon Doyle, October 7, 2018


##
# Collect UUID from the user that we wish to collect volinfo about.
getUUID()
{
    # Is this sustainable?
    #local agents="$(snapctl list 2>&1)"

    # Let's create our own that respects column widths. Redirect to 
    # stderr so we can pipe this whole script to `column` independently.
    for agent in /home/agents/*
    do
        local id="${agent##*/}"
        local path="/datto/config/keys/$id.agentInfo"

        # Ensure this directory wasn't just `created'
        if ! [ -e "$path" ]
        then
            printf "ERROR: %s does not have %s\\n" "$id" "\".agentInfo\"" 1>&2
            continue
        fi
        
        printf "%s,%s\\n" "$id" "$(grep -oP     \
            "\"hostName\";s:[0-9]+:\"\\K[^\"]+" \
            "/datto/config/keys/$id.agentInfo")"
    done | column -s ',' -t 1>&2

    local agents
    agents="$(find /home/agents/ -maxdepth 1 -mindepth 1 -type d \
        | wc -l)"

    if [ "$agents" -eq 0 ]
    then
        printf "No agents found" 1>&2
        return
    fi

    # Get user input, now that we've provided them with their options.
    local UUID

    while true
    do
        read -r -p "Enter UUID: " UUID

        # Ensure this is a valid identifier
        if ! [ -d "/home/agents/$UUID" ]
        then
            printf "ERROR: \"%s\" doesn't exist\\n" "$UUID" 1>&2
            continue
        else
            break
        fi
    done

    # Use STDOUT as return.
    printf "%s" "$UUID"

    return 0
}


##
# Loop over the UUID's snapshots (if they exist) and print volinfo.
getSnapshots()
{
    if [ "$#" -ne  1 ]
    then
        printf "getSnapshots() requires 1 argument, received %d\\n" "$#" 1>&2
        return
    fi

    local UUID="$1"

    # Ensure it's a valid id (again, for safety)
    if ! [ -d "/home/agents/$UUID" ]
    then
        printf "ERROR: \"%s\" doesn't exist\\n" "$UUID" 1>&2
        return
    fi

    # Loop over this agent's snapshots and list included directories.
    for epoch in /home/agents/"$UUID"/.zfs/snapshot/*
    do 
        timestamp="$(echo "$epoch" | grep -oP "[0-9]+$")" 

        if [ "$timestamp" ]
        then
            convertedDate="$(date -d@"$timestamp")"
            printf "%s: " "$convertedDate"

            # Volumes
            volt="$epoch/voltab"

            if [ -e "$volt" ]
            then 
                # Match and output all volumes on the same line.
                match="$(grep -oP "(?<=(\"mountpoint\":\"))[A-Z]" "$volt" \
                    | awk '{ printf "%s:\\ ",$0,NR % 7 ? " " : "\n"; }')"

                if ! [ "$match" ]
                then 
                    printf "* No volumes included in voltab\\n"
                else 
                    printf "%s\\n" "$match"
                fi
            else 
                printf "voltab doesn't exist\\n"
            fi

            # 
        else
            printf "No snapshots\\n"
        fi
    done

    return 0
}


uuid="$(getUUID)"
getSnapshots "$uuid"

# Clean up local environment
unset -f getUUID
unset -f getSnapshots
unset uuid

exit 0
