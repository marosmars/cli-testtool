
for i in `seq 10000 11000`;
do
	nc -z -v -w5 localhost $i &
	expect -c "spawn ssh cisco@localhost $i; send \"cisco\r\"; expect \"XE\"; sleep 3;" &
done

wait
