from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
import psycopg2
from datetime import datetime
import requests

dag = DAG(
    dag_id='etl_airflow_rest_api_dag',
    start_date=datetime(2025, 3, 10),
    schedule_interval='@hourly'
)

api_key = '015b954e6c7c1f1fbe16d20d7752a52c'
cities = ["Dhaka", "Delhi", "Islamabad", "London", "New York", "Tokyo", "Sydney"]
conn = psycopg2.connect(
    database = 'postgres',
    user = 'postgres',
    password = '1418',
    host = 'localhost',
    port = '5432'
)

def featch_weather_data():
    weather_data = []
    for city in cities:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        response = requests.get(url)
        data = response.json()
        weather_data.append({
                'city': data['name'],
                'temperature': data['main']['temp'],
                'humidity': data['main']['humidity']
            })
    return weather_data


task_fetch_weather=PythonOperator(
    task_id='fetch_task',
    python_callable=featch_weather_data,
    provide_context = True,
    dag = dag
)


task_create_table=SQLExecuteQueryOperator(
    task_id='create_table',
    conn_id='postgres',
    sql="""
        CREATE TABLE IF NOT EXISTS weather_data_api(
            city VARCHAR(50),
            temperature NUMERIC(10,2),
            humidity NUMERIC(10,2),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """,
    dag= dag
)

def load_to_postgres(**context):
    weather_data = context['ti'].xcom_pull(task_ids = 'fetch_task')
    pg_hook = PostgresHook(postgres_conn_id = 'postgres')
    insert_query = """
    INSERT INTO weather_data_api (city, temperature, humidity)
    VALUES(%s, %s, %s);
    """
    for data in weather_data:
        pg_hook.run(insert_query, parameters=(data['city'], data['temperature'], data['humidity']))


task_load_weather = PythonOperator(
    task_id = 'load_weather_task',
    python_callable= load_to_postgres,
    provide_context = True,
    dag=dag
)

task_fetch_weather >> task_create_table >> task_load_weather
