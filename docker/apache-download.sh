#!/bin/bash
# Apache mirror bullshit download script

if [ "$#" -ne 1 ]; then
    echo "Argument must be file path to apache download. (e.g. spark/spark-2.3.1/spark-2.3.1-bin-hadoop2.7.tgz )"
    exit 1
fi

FILE_PATH=$1 
FILE_NAME=$(basename $FILE_PATH)
REDIRECT_BASE_URL="https://www.apache.org/dyn/closer.cgi?action=download&filename="
ARCHIVE_BASE_URL="https://archive.apache.org/dist/"

echo "downloading $FILE_PATH from mirror"
CODE=`wget --server-response -O $FILE_NAME "$REDIRECT_BASE_URL$FILE_PATH" 2>&1 | tee /dev/fd/2 | grep "  HTTP" | tail -1 | colrm 1 11 | colrm 4`
if [ "$CODE" = "200" ];
then
    exit 0;
fi


# Dear Apache Software Foundation,
# At the time that this script was written we could not find a way to find a mirror of an archive. The archive
# site linked to the mirror resolver for the main mirrors... which do not contain the files we need.
# If this becomes/is possible, please let us know how to do this! 

echo "$FILE_PATH not found on mirror, trying archive: $ARCHIVE_BASE_URL$FILE_PATH"
CODE=`wget --server-response -O $FILE_NAME "$ARCHIVE_BASE_URL$FILE_PATH" 2>&1 | tee /dev/fd/2 | grep "  HTTP" | tail -1 | colrm 1 11 | colrm 4`
if [ "$CODE" = "200" ];
then
    exit 0;
fi

echo "failed to download $FILE_PATH"
exit 1
