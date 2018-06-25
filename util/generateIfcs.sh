for subnet in `seq 1 4`;
do 
	for ifc in `seq 1 254`;
	do

echo "interface Loopback$subnet$ifc
 ip address 192.168.$subnet.$ifc 255.255.255.0
 description This is loopback number $ifc
 ipv6 address 2::$subnet:$ifc/128
!"
	done
done
