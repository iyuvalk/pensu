FROM ubuntu:18.04
LABEL name="pensu_data_generator" version="0.0.1" description="A streaming metrics AI data processor"

COPY . .
RUN apt-get update -y
RUN apt-get install -y python2.7 python-pip
RUN apt-get install net-tools -y
RUN apt-get install default-jdk -y
RUN apt-get install wget -y
RUN wget http://www-us.apache.org/dist/kafka/2.4.0/kafka_2.13-2.4.0.tgz
RUN tar xzf kafka_2.13-2.4.0.tgz

CMD ["./generate_data.sh"]