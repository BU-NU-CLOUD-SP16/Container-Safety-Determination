#!/bin/bash
#####################################################################
# Author: Rahul Sharma <rahuls@ccs.neu.edu>                         #
#                                                                   #
# Script to find OS version running. It relies on either the        #
# python module within the OS or /etc/os-release file. If both      #
# are not present, then one needs to look into /etc directory for   #
# other files like /etc/redhat-release or that OS's conventions     #
# to store name/version info.                                       #
#                                                                   #
# Usecase: this script will be loaded to container and executed     #
#          to figure out the OS version running within container.   #
#                                                                   #
# Example:                                                          #
# docker run -v src:/scripts ubuntu /bin/sh /scripts/platform.sh    #
#                                                                   #
#####################################################################

exists()
{
  command -v $1 >/dev/null 2>&1
}

if exists python
then
  echo "import platform" > temp.py
  echo "print(platform.dist()[0]+':'+platform.dist()[1])" >> temp.py
  python temp.py
elif exists python3
then
  echo "import platform" > temp.py
  echo "print(platform.dist()[0]+':'+platform.dist()[1])" >> temp.py
  python3 temp.py
elif [ -e /etc/os-release ]
then
  #source <filename> sometimes don't work with /bin/sh. Hence using "."
  . /etc/os-release
  echo $ID:$VERSION_ID
else
  echo "Can't determine OS version"
fi
