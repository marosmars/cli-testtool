python ../mockdevice.py 0.0.0.0 11000 10001 ssh ../devices/leafspine/leaf1.json &
python ../mockdevice.py 0.0.0.0 11001 10002 ssh ../devices/leafspine/leaf2.json &
python ../mockdevice.py 0.0.0.0 11002 10003 ssh ../devices/leafspine/leaf3.json &
python ../mockdevice.py 0.0.0.0 11003 10004 ssh ../devices/leafspine/leaf4.json &
python ../mockdevice.py 0.0.0.0 11004 10005 ssh ../devices/leafspine/leaf5.json &
python ../mockdevice.py 0.0.0.0 12000 12001 ssh ../devices/leafspine/spine1.json &
python ../mockdevice.py 0.0.0.0 12001 12002 ssh ../devices/leafspine/spine2.json &

wait
