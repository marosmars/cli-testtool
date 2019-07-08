#!/bin/bash
set -e

# Usage ./generateMount.sh 127.0.0.1 10000 10050

IP=$1
LOW_PORT=$2
HIGH_PORT=$3
PROTOCOL=$4
PORT_NUM=`expr $HIGH_PORT - $LOW_PORT`
MOUNT_ID_PREFIX="cli-"

# These two variables values are dynamically replaced by 'password-setup.sh'
# script in FRINX Machine.
USERNAME="admin"
PASSWORD="admin"

# Remove all cli nodes
echo "Removing all cli nodes"
curl -u "${USERNAME}:${PASSWORD}" -H "Content-Type: application/json" -X DELETE http://localhost:8181/restconf/config/network-topology:network-topology/topology/cli/
echo "

Waiting a bit ...

"
sleep 20s

body="{
    \"network-topology:node\" :
    ["

# \"cli-topology:keepalive-delay\": 250,
# \"cli-topology:keepalive-initial-delay\": 400,
# \"cli-topology:keepalive-timeout\" : 200,

for port in `seq $LOW_PORT $HIGH_PORT`;
do
  body="$body
      {
      \"network-topology:node-id\" : \"$MOUNT_ID_PREFIX$port\",

      \"cli-topology:host\" : \"$IP\",
      \"cli-topology:port\" : \"$port\",
      \"cli-topology:transport-type\" : \"$PROTOCOL\",

      \"cli-topology:device-type\" : \"ios\",
      \"cli-topology:device-version\" : \"15.3\",

      \"cli-topology:username\" : \"cisco\",
      \"cli-topology:password\" : \"cisco\",

      \"cli-topology:journal-size\": 150,
      \"cli-topology:dry-run-journal-size\": 180,

      \"reconcile\": false
    }"

  if [ "$port" -ne "$HIGH_PORT" ]; then
   body="$body    ,";
  fi

done

body="$body
    ]
}"

echo "Sending mount requests"
#echo $body

curl -s -u "${USERNAME}:${PASSWORD}" -d @- -H "Content-Type: application/json" -X POST http://localhost:8181/restconf/config/network-topology:network-topology/topology/cli/ <<CURL_DATA
$body
CURL_DATA

START=$(date +%s.%N)

while (true);
do
	connected=`curl -s -u "${USERNAME}:${PASSWORD}" -H "Content-Type: application/json" -X GET http://localhost:8181/restconf/operational/network-topology:network-topology/topology/cli/ | grep -o 'connection-status":"connected"' | wc -l`

	reconciled=`curl -s -u "${USERNAME}:${PASSWORD}" -H "Content-Type: application/json" -X GET http://localhost:8181/restconf/operational/network-topology:network-topology/topology/uniconfig/?depth=3 | grep -o "$MOUNT_ID_PREFIX" | wc -l`
	END=$(date +%s.%N)
	DIFF=$(echo "$END - $START" | bc)
	echo "Currently connected: $connected, took: $DIFF seconds"
	echo "Currently reconciled: $reconciled, took: $DIFF seconds"

	if [ "$PORT_NUM" -le "$connected" ]; then
		echo "All devices($PORT_NUM) connected in $DIFF seconds"
		if [ "$PORT_NUM" -le "$reconciled" ]; then
			echo "All devices($PORT_NUM) reconciled in uniconfig in $DIFF seconds"
			break
		fi
	fi
	sleep 10s
done


END=$(date +%s.%N)
DIFF=$(echo "$END - $START" | bc)
echo "Time spent: $DIFF seconds"
data_size=`curl -s -u "${USERNAME}:${PASSWORD}" -H "Content-Type: application/json" -X GET http://localhost:8181/restconf/operational/network-topology:network-topology/topology/uniconfig/ | wc -c`
echo "Total data of json.bytes in uniconfig: $data_size bytes"

