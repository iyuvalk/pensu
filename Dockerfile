FROM ubuntu:18.04
LABEL name="pensu" version="0.0.1" description="A streaming metrics AI data processor"

COPY . .
RUN apt-get update -y
RUN apt-get install -y python2.7 python-pip
RUN pip install --no-cache-dir -r requirements.txt

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


CMD ["python", "./pensu_metrics_analyzer.py"]