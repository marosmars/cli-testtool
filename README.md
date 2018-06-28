# Dealing with too many files open :

```
echo "fs.file-max=500000
" | sudo tee --append /etc/sysctl.conf

sudo sysctl -p

echo "
*               hard nofile 10000
*               soft nofile 10000
root            hard nofile 10000
root            soft nofile 10000 
`whoami`        hard nofile 10000
`whoami`        soft nofile 10000
" | sudo tee --append /etc/security/limits.conf

echo "LOGOUT and LOGIN again so that the limits apply"
```

## Running the script to simulated device:

```
sudo pip install MockSSH==1.4.5

python mockdevice.py 127.0.0.1 9999 11000 devices/cisco_IOS.json
```

## Running the script to mount devices in ODL:

```
./generateMount.sh 127.0.0.1 10000 10100
```

# .json files to represent a device :

To unescape device condig for the JSON file, use https://codebeautify.org/json-escape-unescape

# Notes :

Relies on MockSSH package
Scaling: This runs multiple processes and each process handles only a certain number of ports (defined by batch parameter in the script)