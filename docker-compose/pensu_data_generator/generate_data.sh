#!/bin/bash

#The test data was downloaded from Kaggle at https://www.kaggle.com/shenba/time-series-datasets/download/LphTPFq528ElkH1LARMb%2Fversions%2FhmEYjUTESVU5R2UGyga3%2Ffiles%2Fdaily-minimum-temperatures-in-me.csv?datasetVersionNumber=1
DATA_FILE="daily-minimum-temperatures-in-me.csv"
DATA_COLUMN=2
START_AT_LINE=2
test_data_total_lines=$(cat $DATA_FILE | wc -l)
cur_line=$START_AT_LINE

while true; do
  echo my_stats.pensu_test_metrics.load.5min_avg `uptime | awk -F, '{print $6}' | awk '{print $1}'` `date +%s` | ./kafka_2.13-2.4.0/bin/kafka-console-producer.sh --broker-list pensu_kafka1:9092 --topic metrics
  echo my_stats.pensu_test_metrics.memory.used `free | grep '^Mem' | awk '{print $3}'` `date +%s` | ./kafka_2.13-2.4.0/bin/kafka-console-producer.sh --broker-list pensu_kafka1:9092 --topic metrics
  echo my_stats.pensu_test_metrics.network.rx_bytes.eth0 `ifconfig eth0 | grep 'RX packets' | awk '{print $5}'` `date +%s` | ./kafka_2.13-2.4.0/bin/kafka-console-producer.sh --broker-list pensu_kafka1:9092 --topic metrics
  echo my_stats.pensu_test_metrics.network.tx_bytes.eth0 `ifconfig eth0 | grep 'TX packets' | awk '{print $5}'` `date +%s` | ./kafka_2.13-2.4.0/bin/kafka-console-producer.sh --broker-list pensu_kafka1:9092 --topic metrics
  echo my_stats.pensu_test_metrics.test_data `sed "${cur_line}q;d" $DATA_FILE | sed 's/\r//g' | cut -d, -f${DATA_COLUMN}` `date +%s` | ./kafka_2.13-2.4.0/bin/kafka-console-producer.sh --broker-list pensu_kafka1:9092 --topic metrics

  sleep 1
  (( cur_line++ ))
  if [[ $cur_line -ge $test_data_total_lines ]]; then
    cur_line=$START_AT_LINE
  fi
done
