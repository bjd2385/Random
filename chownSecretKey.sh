#! /bin/bash
# Change ownership of root file in /datto/array1/.recv/ to `secretkey`.
#
# Syntax verified with ShellCheck v0.5.0.
# © Vin Presciutti


# Color text.
blue=$(tput setaf 6)
red=$(tput setaf 1)
norm=$(tput setaf 7)
purp=$(tput setaf 5)
green=$(tput setaf 2)


##
# Get a valid file in /datto/array1/.recv/ from a user.
getFile()
{
    local ROOTFILENAME

    while true
    do
        read -r -p "${blue}Enter file name from /datto/array1/.recv: ${norm}" \
            ROOTFILENAME
    
        # Ensure this is a valid file.
        if ! [ "$ROOTFILENAME" ]
        then
            printf "ERROR: Please enter a valid filename\\n" 1>&2
        elif ! [ -e "/datto/array1/.recv/$ROOTFILENAME" ]
        then
            printf "ERROR: File \"/datto/array1/.recv/%s\" does not exist" \
                "$ROOTFILENAME" 1>&2
        else
            break
        fi
    done

    # Print to stdout to capture return value.
    printf "%s" "$ROOTFILENAME"

    return 0
}


##
# Change owernship of root file to secret key.
main()
{
    local ROOTFILENAME ROOTDEVID ROOTSECRETKEY CHOWNCONFIRM

    ROOTFILENAME="$(getFile)"

    # Set deviceID from the format of the send file name.
    # awk reads in reverse because there is the potential for an agent name to 
    # have a hyphen in it. This would create problems with the hyphen delimiter 
    # if reading from beginning to end.
    ROOTDEVID="$(echo "/datto/array1/.recv/$ROOTFILENAME" \
        | awk -F "[.-]" '{ print $(NF-5) }')"
    ROOTSECRETKEY="$(grep "$ROOTDEVID" /etc/passwd | awk -F "[/:]" '{ print $1 }')"

    # Get confirmation of the change from user.
    read -r -p "\\n${blue}This will change ownership of file \
        ${purp}$ROOTFILENAME${blue} to secret key ${purp}$ROOTSECRETKEY${blue}\
        for devID ${purp}$ROOTDEVID${blue}.\\nIs this correct? ${red}Y/N: ${norm}" \
        CHOWNCONFIRM

    if [[ "$CHOWNCONFIRM" =~ ^[Yy] ]]
    then
        chown "$ROOTSECRETKEY:www-data" "/datto/array1/.recv/$ROOTFILENAME"

        printf "Chowned. %s is now owned by secret key %s for devID %s\\n" \
            "${green}$ROOTFILENAME${norm}"\
            "${green}$ROOTSECRETKEY${norm}"\
            "${green}$ROOTDEVID${norm}"

        # Show the result.
        printf "\\n"
        ls -lash "/datto/array1/.recv/$ROOTFILENAME"
        printf "\\n"

        return 0
    else
        printf "%s\\n\\n" "${red}Script terminated. No changes made.${norm}" 1>&2
        return 1
    fi
}


main

# Clean up
unset -f getFile main
unset -v blue red norm purp green

exit 0
