python ../mockdevice.py 0.0.0.0 20001 20002 ssh ../devices/cisco_XR.json &
python ../mockdevice.py 0.0.0.0 20002 20003 ssh ../devices/cisco_XR.json &

wait
