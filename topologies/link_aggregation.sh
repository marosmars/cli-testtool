python ../mockdevice.py 0.0.0.0 13001 13002 ssh ../devices/cisco_XR.json &
python ../mockdevice.py 0.0.0.0 13002 13003 ssh ../devices/cisco_XR.json &

wait
