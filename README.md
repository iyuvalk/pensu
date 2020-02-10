# Pensu (Esperanto for "Think")
NuPic based anomaly detection production ready microservice

This project aims at developing a production ready microservice for making predictions and detecting anomalies in time-series data by using [Numenta's HTM algorithm from the NuPic package](https://www.numenta.org/).
Here's how it works:

1. It pulls metrics data from a Kafka topic (set by $PENSU_METRICS_KAFKA_TOPIC). The metric should be in Graphite's Carbon format, i.e: some.metric.category.and.name value unix-timestamp (for example "webservers.main-website.perf.cpu.usage 59 1587617182")
1. It creates two HTM models for that metric (if it cannot find a pre-existing one). One will be used for predictions and the other for anomaly detection
1. It sends the value and timestamp to the appropriate models
1. If the anomaly score is above $PENSU_ANOMALY_SCORE_THRESHOLD and anomaly likelihood is above $PENSU_ANOMALY_LIKELIHOOD_THRESHOLD and the prediction confidence is above $PENSU_MINIMUM_CONFIDENCE_FOR_REPORTING:
    1. It will set the value of the metric anomaly-direction to either 1 if the predicted value was lower than the current value or to -1 if the predicted value was higher than the current value 
    1. It will send a JSON object to the kafka topic named $PENSU_REPORTED_ANOMALIES_KAFKA_TOPIC
1. If no anomaly was detected (i.e. either the anomaly score is below $PENSU_ANOMALY_SCORE_THRESHOLD or the anomaly likelihood is below $PENSU_ANOMALY_LIKELIHOOD_THRESHOLD or the prediction confidence is below $PENSU_MINIMUM_CONFIDENCE_FOR_REPORTING) it will set the value of the metric anomaly-direction to 0
1. It will send the following metrics to the Kafka topic named $PENSU_REPORTED_ANOMALIES_KAFKA_TOPIC:
    1. pensu.anomaly_likelihood.metrics_analyzer.<metric name> (i.e pensu.anomaly_likelihood.metrics_analyzer.webservers.main-website.perf.cpu.usage)
    1. pensu.anomaly_score.metrics_analyzer.<metric name> (i.e pensu.anomaly_score.metrics_analyzer.webservers.main-website.perf.cpu.usage)
1. It will send the following metrics to the Kafka topic named $PENSU_PREDICTION_METRICS_KAFKA_TOPIC:
    1. pensu.prediction.metrics_analyzer.<metric name> (i.e pensu.prediction.metrics_analyzer.webservers.main-website.perf.cpu.usage)
    1. pensu.prediction_confidence.metrics_analyzer.<metric name> (i.e pensu.prediction_confidence.metrics_analyzer.webservers.main-website.perf.cpu.usage)

<br />
To make it easier to test this project, you'll find in the docker-compose folder a docker-compose.yml file that when launched (by running docker-compose up from that folder) it will start the following Docker containers:

1. pensu - The core of the system, this is where the HTM magic happens (-:
1. pensu_data_generator - A container that runs a simple script for generating the following five metrics:
   1. system load
   1. memory used
   1. traffic sent on eth0
   1. traffic sent on eth0
   1. test data downloaded from kaggle (see the script for details)
1. pensu_kafka1 - A kafka server that will be used by the system
1. pensu_zookeeper1 - A zookeeper that will be used by Kafka
1. pensu_grafana - A pre-configured grafana dashboard that will let you see the beautiful charts plotting all the metrics mentioned above
1. pensu_graphite - A service for storing the metrics mentioned above as well as the metrics generated by pensu 
1. pensu_logstash - A service for forwarding the various metrics generated by pensu from Kafka to Graphite (to allow them to be displayed on Grafana) 

After running docker-compose up, browse to http://localhost:3000 with the user admin and the initial password admin and select a password, then select the dashboard "Pensu Metrics" (the only dashboard there) and you'll be able to see the system in action.


#### OS Environment Variables used (with sample values):
The following list contains all the environment variables used in this project. Feel free to modify their values and see how the system would react:
```
ENV PENSU_PING_LISTEN_HOST="0.0.0.0"
ENV PENSU_PING_LISTEN_PORT=5555
ENV PENSU_MODELS_AUTOSAVE_INTERVAL=86400
ENV PENSU_PREDICTION_STEPS=5
ENV PENSU_ANOMALYCALC_FILENAME="pensu_anomaly_likelihood_calculator"
ENV PENSU_METRIC_NAMES_TEMPLATE="pensu.{{#anomaly_metric}}.metrics_analyzer"
ENV PENSU_KAFKA_CONSUMER_CLIENT_ID="pensu_consumer_{{#instance_id}}_{{#time_started}}"
ENV PENSU_KAFKA_CONSUMER_SESSION_TIMEOUT_MS=5000
ENV PENSU_KAFKA_CONSUMER_SERVER="kafka:9092"
ENV PENSU_KAFKA_PRODUCER_CLIENT_ID="pensu_producer_{{#instance_id}}_{{#time_started}}"
ENV PENSU_KAFKA_PRODUCER_SERVER="kafka:9092"
ENV PENSU_TOPICS_KAFKA_TOPIC="pensu_monitored_topics"
ENV PENSU_TOPICS_REPORT_INTERVAL=10
ENV PENSU_METRICS_KAFKA_TOPIC="metrics"
ENV PENSU_REPORTED_ANOMALIES_KAFKA_TOPIC="pensu.htm.anomaly_metrics"
ENV PENSU_PREDICTION_METRICS_KAFKA_TOPIC="pensu.htm.predictions"
ENV PENSU_ANOMALIES_METRICS_KAFKA_TOPIC="pensu_anomalies"
ENV PENSU_ALLOWED_TO_WORK_ON_METRICS=".*"
ENV PENSU_LOGGING_FORMAT="timestamp=%s;module=smart-onion_%s;method=%s;severity=%s;state=%s;metric/metric_family=%s;exception_msg=%s;exception_type=%s;message=%s"
ENV PENSU_ANOMALY_SCORE_THRESHOLD=0.99
ENV PENSU_ANOMALY_LIKELIHOOD_THRESHOLD=0.99999
ENV PENSU_MINIMUM_CONFIDENCE_FOR_REPORTING=0.9
ENV PENSU_MAX_ALLOWED_MODELS=10
ENV PENSU_MIN_SECONDS_BETWEEN_OVER_QUOTA_LOG_MSG=300
```

I hope that you'll find this project useful and if so (and of course if not) I'd be happy if you'll drop me a line... (-:

