#!/bin/bash

doorflow_api=
last_id=0

check_front_door(){
	result_front_door=$(curl -s -H 'Accept: application/json' -H 'Content-Type: application/json' -u ${doorflow_api}:xxx  https://api.doorflow.com/api/3/events/|jq -rS '.[] | select((.door_controller_id==5559) and (.person_name != null)) | [.updated_at,.id,.person_id,.person_name]|@tsv'|head -1)
	declare -a front_door_Array=($result_front_door)
	front_door_updated=$(date +%s -d "${front_door_Array[0]}")
	front_door_id=${front_door_Array[1]} 
	front_person_id=${front_door_Array[2]} 
	front_door_first=${front_door_Array[3]} 
	front_door_last=${front_door_Array[4]} 
}

check_warehouse(){
	result_warehouse_door=$(curl -s -H 'Accept: application/json' -H 'Content-Type: application/json' -u ${doorflow_api}:xxx  https://api.doorflow.com/api/3/events/|jq -rS '.[] | select(.door_controller_id==5828) | [.updated_at,.person_id,.person_name]|@tsv'|head -1)
	declare -a warehouse_door_Array=($result_warehouse_door)
	warehouse_door_updated=$(date +%s -d "${warehouse_door_Array[0]}")
	warehouse_person_id=${warehouse_door_Array[1]} 
}

check_time_till_warehouse(){
	result_warehouse_door=$(curl -s -H 'Accept: application/json' -H 'Content-Type: application/json' -u ${doorflow_api}:xxx  https://api.doorflow.com/api/3/events/|jq -rS --arg front_person_id "$front_person_id" '.[] | select(.door_controller_id==5828) | select(.person_id == ($front_person_id | tonumber)) | [.updated_at,.person_id,.person_name]|@tsv'|head -1)
	declare -a warehouse_door_Array=($result_warehouse_door)
	warehouse_door_updated=$(date +%s -d "${warehouse_door_Array[0]}")
	warehouse_person_id=${warehouse_door_Array[1]} 
	time_till_warehouse=$(expr ${warehouse_door_updated} - ${front_door_updated} 2>/dev/null)
	echo -e "\nfront = ${front_door_updated}\nwarehouse = ${warehouse_door_updated}\ndiff = ${time_till_warehouse}\n"
	if [ -z "${time_till_warehouse}" ] || [ "${warehouse_person_id}" != "${front_person_id}" ] ; then
		time_till_warehouse=0
	fi
		
}

while true; do
	h=$(date +%H)
	if [ "$h" -lt "12" ]; then
		greet="morning"
	elif [ "$h" -lt "18" ]; then
		greet="afternoon"
	else
		greet="evening"
	fi

	check_front_door

	if [ "$front_person_id" ] && [ "$front_door_id" != "$last_id" ]; then
		SECONDS=0
		echo "${front_door_first} ${front_door_last} badged into front door"
        	/home/pi/cheerled/cheer-text.py /dev/ttyUSB0 -s 1 -c red "Good $greet " -c green "$front_door_first"
		check_front_door
		check_warehouse
		until [ "${front_person_id}" = "${warehouse_person_id}" ] || [ "${SECONDS}" -ge "40" ] ;
		do
			check_warehouse
			sleep 1
		done	
		COUNT=0
#		check_time_till_warehouse
		echo "${front_door_first} ${front_door_last} badged into warehouse door after ${SECONDS}s"
	else
		let COUNT=COUNT+1
		if [ "$COUNT" = "1" ] ; then
        		/home/pi/cheerled/cheer-text.py /dev/ttyUSB0 -a scroll_up "Welcome to" 
			sleep 2
        		/home/pi/cheerled/cheer-text.py /dev/ttyUSB0 -a scroll_down "Lowell Makes" 
			sleep 2
        		/home/pi/cheerled/cheer-text.py /dev/ttyUSB0 "Welcome to Lowell Makes" 
		elif [ "$COUNT" = "2" ] ; then
        		/home/pi/cheerled/cheer-text.py /dev/ttyUSB0 -a pacman " " 
			sleep 1
		elif [ "$COUNT" = "3" ] ; then
        		/home/pi/cheerled/cheer-text.py /dev/ttyUSB0 "Welcome to Lowell Makes" 
			sleep 1
		elif [ "$COUNT" = "4" ] ; then
        		/home/pi/cheerled/cheer-text.py /dev/ttyUSB0 "Welcome to Lowell Makes" 
			sleep 1
			COUNT=0
		fi	
	fi
	last_id=${front_door_id}
	sleep 8
done
