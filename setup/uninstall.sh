#! /bin/bash
printf '\033]2;Uninstalling...\a'
sleep 5

{
rm /bin/Invader
rm /usr/local/bin/Invader
rm -r ~/Invader
} &> /dev/null

echo -e "\033[1;32m[*] Uninstallation completed!\033[0m"
