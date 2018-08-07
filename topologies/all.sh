python ../mockdevice.py 127.0.0.1 10000 10001 ssh ../devices/cisco_IOS.json &
python ../mockdevice.py 127.0.0.1 10001 10002 ssh ../devices/cisco_XR.json &
python ../mockdevice.py 127.0.0.1 10002 10003 ssh ../devices/huawei_VRP.json &

wait
