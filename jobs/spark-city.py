from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import StructType, StructField, StringType, TimestampType, DoubleType, IntegerType

from config import configuration


def main():
    spark = SparkSession.builder.appName("IOTStreaming") \
        .config("spark.jars.packages",
                "org.apache.spark:spark-sql-kafka-0-10_2.13:3.5.0,"
                "org.apache.hadoop:hadoop-aws:3.3.1,"
                "com.amazonaws:aws-java-sdk:1.11.469") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.hadoop.fs.s3a.access.key", configuration.get('AWS_ACCESS_KEY')) \
        .config("spark.hadoop.fs.s3a.secret.key", configuration.get('AWS_SECRET_KEY')) \
        .config('spark.hadoop.fs.s3a.aws.credentials.provider',
                'org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider') \
        .getOrCreate()

    spark.sparkContext.setLogLevel('WARN')

    # vehicle schema
    vehicle_schema = StructType([
        StructField("id", StringType(), True),
        StructField("deviceId", StringType(), True),
        StructField("timestamp", TimestampType(), True),
        StructField("location", StringType(), True),
        StructField("speed", DoubleType(), True),
        StructField("direction", StringType(), True),
        StructField("make", StringType(), True),
        StructField("model", StringType(), True),
        StructField("year", IntegerType(), True),
        StructField("fuelType", StringType(), True),
    ])

    # GPS schema
    gps_schema = StructType([
        StructField("id", StringType(), True),
        StructField("deviceId", StringType(), True),
        StructField("timestamp", TimestampType(), True),
        StructField("speed", DoubleType(), True),
        StructField("direction", StringType(), True),
        StructField("vehicleType", StringType(), True),
    ])

    # traffic schema
    traffic_schema = StructType([
        StructField("id", StringType(), True),
        StructField("deviceId", StringType(), True),
        StructField("cameraId", StringType(), True),
        StructField("location", StringType(), True),
        StructField("timestamp", TimestampType(), True),
        StructField("snapshot", StringType(), True),
    ])

    # weather Schema
    weather_schema = StructType([
        StructField("id", StringType(), True),
        StructField("deviceId", StringType(), True),
        StructField("location", StringType(), True),
        StructField("timestamp", TimestampType(), True),
        StructField("temperature", DoubleType(), True),
        StructField("weatherCondition", StringType(), True),
        StructField("precipitation", DoubleType(), True),
        StructField("windSpeed", DoubleType(), True),
        StructField("humidity", IntegerType(), True),
        StructField("airQualityIndex", DoubleType(), True),
    ])

    # emergency schema
    emergency_schema = StructType([
        StructField("id", StringType(), True),
        StructField("deviceId", StringType(), True),
        StructField("incidentId", StringType(), True),
        StructField("type", StringType(), True),
        StructField("timestamp", TimestampType(), True),
        StructField("location", StringType(), True),
        StructField("status", StringType(), True),
        StructField("description", StringType(), True),
    ])

    def read_kafka_topic(topic, schema):
        return (spark.readStream
                .format('kafka')
                .option('kafka.bootstrap.servers', 'broker:29092')
                .option('subscribe', topic)
                .option('startingOffsets', 'earliest')
                .load()
                .selectExpr('CAST (values AS STRING)')
                .select(from_json(col('value'), schema).alias('data'))
                .select('data.*')
                .withWatermark('timestamp', '2 minutes')
                )

    def stream_writer(input: DataFrame, checkpoint_folder, output):
        return (input.writeStream
                .format('parquet')
                .option('checkpointLocation', checkpoint_folder)
                .option('path', output)
                .outputMode('append')
                .start()
                )

    vehicle_df = read_kafka_topic('vehicle_data', vehicle_schema).alias('vehicle')
    gps_df = read_kafka_topic('gps_data', gps_schema).alias('gps')
    traffic_df = read_kafka_topic('traffic_data', traffic_schema).alias('traffic')
    weather_df = read_kafka_topic('weather_data', weather_schema).alias('weather')
    emergency_df = read_kafka_topic('emergency_data', emergency_schema).alias('emergency')

    # join all Dfs with id and timestamp
    # join
    query1 = stream_writer(vehicle_df, 's3a://aws-spark-data-streaming/checkpoints/vehicle_data',
                           's3a://aws-spark-data-streaming/data/vehicle_data')
    query2 = stream_writer(gps_df, 's3a://aws-spark-data-streaming/checkpoints/gps_data',
                           's3a://aws-spark-data-streaming/data/gps_data')
    query3 = stream_writer(traffic_df, 's3a://aws-spark-data-streaming/checkpoints/traffic_data',
                           's3a://aws-spark-data-streaming/data/traffic_data')
    query4 = stream_writer(weather_df, 's3a://aws-spark-data-streaming/checkpoints/weather_data',
                           's3a://aws-spark-data-streaming/data/weather_data')
    query5 = stream_writer(emergency_df, 's3a://aws-spark-data-streaming/checkpoints/emergency_data',
                           's3a://aws-spark-data-streaming/data/emergency_data')

    query5.awaitTermination()


if __name__ == "__main__":
    main()
