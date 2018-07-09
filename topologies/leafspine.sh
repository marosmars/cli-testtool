python ../mockdevice.py 127.0.0.1 10000 10001 ssh ../devices/leafspine/leaf1.json &
python ../mockdevice.py 127.0.0.1 10001 10002 ssh ../devices/leafspine/leaf2.json &
python ../mockdevice.py 127.0.0.1 10002 10003 ssh ../devices/leafspine/leaf3.json &
python ../mockdevice.py 127.0.0.1 10003 10004 ssh ../devices/leafspine/leaf4.json &
python ../mockdevice.py 127.0.0.1 10004 10005 ssh ../devices/leafspine/leaf5.json &
python ../mockdevice.py 127.0.0.1 12000 12001 ssh ../devices/leafspine/spine1.json &
python ../mockdevice.py 127.0.0.1 12001 12002 ssh ../devices/leafspine/spine2.json &

wait
