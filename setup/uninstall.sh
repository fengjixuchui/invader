#! /bin/bash
sleep 1

{
rm /bin/invader
rm /usr/local/bin/invader
rm -r ~/invader
} &> /dev/null

echo -e "\033[1;32mUninstallation completed!\033[0m"
