#! /bin/bash
printf '\033]2;Uninstalling...\a'
sleep 5

{
rm /bin/invader
rm /usr/local/bin/invader
rm -r ~/invader
} &> /dev/null

echo -e "\033[1;32m[*] Uninstallation completed!\033[0m"
