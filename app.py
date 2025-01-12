import streamlit as st
import pandas as pd
import requests
import json
import plotly.express as px
import datetime

def process_chunk(chunk):
    chunk['mean_temp_city'] = chunk['temperature'].rolling(window=30, min_periods=0).median()
    chunk['std_temp_city'] = chunk['temperature'].rolling(window=30, min_periods=0).std()
    chunk = chunk.fillna({'std_temp_city': 0})
    chunk['anomaly'] = chunk.apply(
        lambda row: (row.temperature < row.std_temp_city - 2 * row.mean_temp_city) or \
          (row.temperature > row.mean_temp_city + 2 * row.std_temp_city), axis=1
        )

    chunk['mean_temp_season'] = chunk.groupby(['season'])['temperature'].transform(lambda x: x.rolling(window=30, min_periods=0).median())
    chunk['std_temp_season'] = chunk.groupby(['season'])['temperature'].transform(lambda x: x.rolling(window=30, min_periods=0).std())
    chunk = chunk.fillna({'std_temp_season': 0})

    chunk['mean_temp'] = chunk.groupby(['season'])['temperature'].transform('mean')
    chunk['std_temp'] = chunk.groupby(['season'])['temperature'].transform('std')

    return chunk

def get_weather(city_name, api_key):
    city_info_link = f"http://api.openweathermap.org/geo/1.0/direct?q={city_name}&limit=1&appid={api_key}"

    response = requests.get(city_info_link)
    if response.status_code == 200:
        content = response.json()[0]
        lat, lon = content['lat'], content['lon']

        weather_link = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
        response_weather = requests.get(weather_link)
        return response_weather.json()
    return None

def main():
    st.title("Анализ данных с использованием Streamlit")

    uploaded_file = st.file_uploader("Выберите CSV-файл", type=["csv"])
    
    if uploaded_file is not None:
        data = pd.read_csv(uploaded_file)
    else:
        st.write("Пожалуйста, загрузите CSV-файл.")

    if uploaded_file is not None:
        data = pd.read_csv(uploaded_file)
        
        city_name = st.selectbox("Выберите город", data['city'].unique())
        city_data = data[data['city']==city_name].copy()
        city_data['timestamp'] = city_data['timestamp'].apply(lambda date: datetime.datetime.strptime(date, '%Y-%m-%d').date())
        city_data = process_chunk(city_data)
        
        first_date = datetime.date(2010, 1, 1)
        last_date = datetime.date(2019, 12, 29)

        start_date, end_date = st.date_input(
            "Выберите даты, по которым хотите увидеть погоду. Минимальная дата - 1 января 2010 года, максимальная - 12 декабря 2019 года",
            (first_date, datetime.date(2010, 1, 1)),
            min_value=first_date,
            max_value=last_date,
            format="YYYY-MM-DD",
        )
        city_data_dates = city_data[(city_data.timestamp >= start_date) & (city_data.timestamp <= end_date)]
        fig = px.scatter(city_data_dates, x='timestamp', y='temperature', color='anomaly')
        st.plotly_chart(fig)

        api_key = st.text_input("Введите OpenWeatherMap API токен")
        
        st.write(f'Средняя температура и разброс в {city_name} по сезонам:')
        seasonal_stats = city_data.groupby('season')[['mean_temp', 'std_temp']].agg(lambda l: l.values[0])
        st.dataframe(seasonal_stats)

        current_weather = get_weather(city_name, api_key)
        cur_date = str(datetime.datetime.today()).split()[0]
        cur_month = int(cur_date.split('-')[1])
        if cur_month in [12, 1, 2]:
            cur_season = 'winter'
        elif cur_month in [3, 4, 5]:
            cur_season = 'spring'
        elif cur_month in [6, 7, 8]:
            cur_season = 'summer'
        else:
            cur_season = 'autumn'

        mean_temp, std_temp = seasonal_stats.reset_index()[
            seasonal_stats.reset_index()['season'] == cur_season
        ][['mean_temp', 'std_temp']].values[0]
        low_bound, high_bound = mean_temp - 2 * std_temp, mean_temp + 2 * std_temp
        is_weather_normal = 'неаномальная' if low_bound < current_weather['main']['temp'] < high_bound else 'аномальная'

        if current_weather:
            st.success(f"Температура в {city_name}: {current_weather['main']['temp']}°C. Температура {is_weather_normal}")
        else:
            st.error(f"Ошибка при запросе API")

if __name__ == "__main__":
    main()
