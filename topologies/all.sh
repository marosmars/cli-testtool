python ../mockdevice.py 0.0.0.0 10000 10001 ssh ../devices/cisco_IOS.json &
python ../mockdevice.py 0.0.0.0 10001 10002 ssh ../devices/cisco_XR.json &
python ../mockdevice.py 0.0.0.0 10002 10003 ssh ../devices/huawei_VRP.json &

wait
