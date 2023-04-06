import datetime
import joblib
from math import radians
from sml import cc_features

import pandas as pd
import numpy as np
import plotly.express as px
from matplotlib import pyplot
import warnings

import hopsworks
from sml import synthetic_data

import streamlit as st

import folium
from streamlit_folium import st_folium
import json

time_now = int(datetime.datetime.now().timestamp() * 1000)
start_date = (datetime.datetime.now() - datetime.timedelta(hours=24)).date()
end_date = (datetime.datetime.now()).date()
synthetic_data.set_random_seed(12345)
credit_cards = [cc["cc_num"] for cc in synthetic_data.generate_list_credit_card_numbers()]
lat = 0
long = 0

warnings.filterwarnings("ignore")

project = hopsworks.login()
fs = project.get_feature_store()

@st.cache(allow_output_mutation=True, suppress_st_warning=True)
def retrive_dataset(start_date, end_date):
    st.write(36 * "-")
    print_fancy_header('\n💾 Dataset Retrieving...')
    feature_view = fs.get_feature_view("transactions_fraud_online_fv", 1)
    batch_data = feature_view.get_batch_data(start_time = start_date, end_time = end_date)
    batch_data.drop(["cc_num", "datetime"], axis = 1, inplace=True)
    return batch_data


@st.cache(suppress_st_warning=True, allow_output_mutation=True)
def get_feature_views():
    fv = fs.get_feature_view("transactions_fraud_online_fv", 1)
    latest_record_fv = fs.get_feature_view("latest_recorded_transactions_fraud_online_fv", 1)
    return fv, latest_record_fv


@st.cache(allow_output_mutation=True,suppress_st_warning=True)
def get_model(project = project):
    mr = project.get_model_registry()
    model = mr.get_model("transactions_fraud_online_xgboost", version = 1)
    model_dir = model.download()
    return joblib.load(model_dir + "/xgboost.pkl")

def explore_data(batch_data):
    st.write(36 * "-")
    print_fancy_header('\n👁 Data Exploration...')
    labels = ["Normal", "Fraudulent"]
    unique, counts = np.unique(batch_data.fraud.values, return_counts=True)
    values = counts.tolist()

    def plot_pie(values, labels):
        fig = px.pie(values=values, names=labels, title='Distribution of predicted fraud transactions')
        return fig

    fig1 = plot_pie(values, labels)
    st.plotly_chart(fig1)


def print_fancy_header(text, font_size=24):
    res = f'<span style="color:#ff5f27; font-size: {font_size}px;">{text}</span>'
    st.markdown(res, unsafe_allow_html=True)

def transform_preds(predictions):
    return ['Fraud' if pred == 1 else 'Not Fraud' for pred in predictions]    

progress_bar = st.sidebar.header('⚙️ Working Progress')
progress_bar = st.sidebar.progress(0)
st.title('🆘 Fraud transactions detection 🆘')

st.write(36 * "-")
print_fancy_header('\n📡 Connecting to Hopsworks Feature Store...')

st.write(36 * "-")
print_fancy_header('\n🤖 Connecting to Model Registry on Hopsworks...')
model = get_model(project)
st.write(model)
st.write("✅ Connected!")

progress_bar.progress(40)

st.write(36 * "-")
print_fancy_header('\n✨ Fetch batch data and predict')
fv, latest_record_fv = get_feature_views()

batch_data = retrive_dataset(start_date, end_date)
st.write("✅ Retrieved!")
progress_bar.progress(55)

if st.button('📊 Make a prediction'):
    predictions = model.predict(batch_data)
    predictions = transform_preds(predictions)
    batch_data_to_explore = batch_data.copy()
    batch_data_to_explore['fraud'] = predictions
    explore_data(batch_data_to_explore)

st.button("Re-run")
