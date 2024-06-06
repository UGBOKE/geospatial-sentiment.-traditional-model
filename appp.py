import streamlit as st
import pandas as pd
import numpy as np
import joblib
import re
from nltk import pos_tag, word_tokenize
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer
import nltk
import plotly.express as px
import pycountry
from datetime import datetime
import plotly.graph_objs as go
import plotly.express as px
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from sklearn.metrics import accuracy_score
import seaborn as sns
from sklearn.metrics import confusion_matrix, precision_score, recall_score, f1_score, classification_report
import requests
from io import BytesIO

nltk.download('averaged_perceptron_tagger')
nltk.download('punkt')
nltk.download('wordnet')
nltk.download('omw-1.4')
nltk.download('vader_lexicon')

# Helper functions
def preprocess(text_data):
    if pd.isnull(text_data):
        return ""
    cleaning_pattern = r'[^\w\s\']|_|\d|[^\x00-\x7F]+'
    cleaned_text = re.sub(cleaning_pattern, '', text_data)
    return cleaned_text

def get_wordnet_pos(treebank_tag):
    if treebank_tag.startswith('J'):
        return wordnet.ADJ
    elif treebank_tag.startswith('V'):
        return wordnet.VERB
    elif treebank_tag.startswith('N'):
        return wordnet.NOUN
    elif treebank_tag.startswith('R'):
        return wordnet.ADV
    else:
        return wordnet.NOUN  

def lemmatize_text(text):
    lemmatizer = WordNetLemmatizer()
    word_pos_tags = pos_tag(word_tokenize(text))
    lemmatized_words = [lemmatizer.lemmatize(word, get_wordnet_pos(tag)) for word, tag in word_pos_tags]
    return ' '.join(lemmatized_words)

def load_from_github(url):
    response = requests.get(url)
    return BytesIO(response.content)

@st.cache_data
def load_data_from_drive(url):
    response = requests.get(url)
    return pd.read_csv(BytesIO(response.content), encoding="latin1")

@st.cache_data
def load_model(url):
    response = requests.get(url)
    return joblib.load(BytesIO(response.content))

def get_country_name(alpha_2_code):
    try:
        return pycountry.countries.get(alpha_2=alpha_2_code).name
    except AttributeError:
        return "Unknown"
            
def create_wordcloud(text):
    wordcloud = WordCloud(width=800, height=400, background_color ='white').generate(text)
    return wordcloud
    
def plot_wordcloud(wordcloud):
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    plt.tight_layout(pad=0)
    plt.show()

def show_wordcloud_for_negative_reviews(df):
    negative_reviews = df[df['Actual_sentiment'] == 0]['title']
    combined_reviews = ' '.join(negative_reviews)
    wordcloud = create_wordcloud(combined_reviews)
    fig, ax = plt.subplots()
    ax.imshow(wordcloud, interpolation='bilinear')
    ax.axis('off')
    st.pyplot(fig)

def predict_data(input_data, vectorizer, model):
    if isinstance(input_data, pd.DataFrame):
        text_data = input_data['review'].apply(lambda x: lemmatize_text(preprocess(x)))
    else:
        text_data = pd.Series([lemmatize_text(preprocess(input_data))])
    text_features = vectorizer.transform(text_data)
    predictions = model.predict(text_features)
    return predictions

def main():
    logo = 'https://github.com/UGBOKE/geospatial-sentiment-model/blob/main/Picture1.png'
    col1, col2 = st.columns([3,1])
    with col2: 
        st.image(logo, width=100)
    with col1:
        st.title('Geospatial Sentiment Dashboard')
    
    data_url = 'https://drive.google.com/file/d/16EV2Pz8pkr973dowSI7bnEGy-8Xzc2Gx/view?usp=drive_link'
    df = load_data_from_drive(data_url)
    df['title'] = df['title'].apply(preprocess)
    df['review'] = df['review'].apply(preprocess)
    
    page = st.sidebar.selectbox("Choose your page", ["Prediction", "Dashboard"])

    if page == "Prediction":
        st.subheader('Upload a CSV file or enter text for prediction')
        text_input = st.text_area("Enter Text")
        uploaded_file = st.file_uploader("Choose a CSV file")
        vectorizer_url = 'https://github.com/UGBOKE/geospatial-sentiment-model/blob/main/vectorizer.joblib'
        model_url = 'https://github.com/UGBOKE/geospatial-sentiment-model/blob/main/svm_model.joblib'

        vectorizer = load_model(vectorizer_url)
        model = load_model(model_url)
        
        if st.button('Predict'):
            if uploaded_file is not None:
                data = pd.read_csv(uploaded_file)
                data['review'] = data['review'].apply(preprocess)
                predictions = predict_data(data, vectorizer, model)
                data['predictions'] = predictions
                data['Sentiment_label'] = data['predictions'].map({1: 'Positive Sentiment', 0: 'Negative Sentiment'})
                st.write(data[['review', 'sentiment', 'predictions', 'Sentiment_label']])
                
                actual_sentiments = data['sentiment'].value_counts().sort_index()
                predicted_sentiments = data['predictions'].value_counts().sort_index()
                comparison_df = pd.DataFrame({
                    'Actual Sentiments': actual_sentiments,
                    'Predicted Sentiments': predicted_sentiments
                })
                fig = px.bar(comparison_df, barmode='group', title='Comparison of Actual and Predicted Sentiments')
                st.plotly_chart(fig, use_container_width=True)
                 
                accuracy = accuracy_score(data['sentiment'], data['predictions'])
                st.metric(label="Prediction Accuracy", value=f"{accuracy:.2%}")
                
                cm = confusion_matrix(data['sentiment'], data['predictions'])
                precision = precision_score(data['sentiment'], data['predictions'], zero_division=0)
                recall = recall_score(data['sentiment'], data['predictions'], zero_division=0)
                f1 = f1_score(data['sentiment'], data['predictions'], zero_division=0)
                
                st.subheader('Confusion Matrix')
                fig_cm, ax = plt.subplots()
                sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=ax)
                ax.set_xlabel('Predicted Labels')
                ax.set_ylabel('True Labels')
                ax.set_title('Confusion Matrix')
                st.pyplot(fig_cm)
                st.subheader('Performance Metrics')
                st.text('Precision: {:.2f}'.format(precision))
                st.text('Recall: {:.2f}'.format(recall))
                st.text('F1 Score: {:.2f}'.format(f1))

                st.subheader('Classification Report')
                report = classification_report(data['sentiment'], data['predictions'], output_dict=True)
                st.json(report)
                accuracy = accuracy_score(data['sentiment'], data['predictions'])
                st.metric(label="Prediction Accuracy", value=f"{accuracy:.2%}")

            elif text_input:
                processed_text = preprocess(text_input)
                prediction = predict_data(processed_text, vectorizer, model)
                sentiment = 'Positive Sentiment' if prediction[0] == 1 else 'Negative Sentiment'
                st.write("Prediction:", sentiment)

    elif page == "Dashboard":              
        df['country_name'] = df['store_location'].apply(get_country_name)
        st.subheader('Select Year Range')
        start_year, end_year = st.slider('Select year range', min_value=2018, max_value=2024, value=(2018, 2024))
        filtered_year_data = df[(df['date'] >= start_year) & (df['date'] <= end_year)]
        
        st.subheader('Select Month Range')
        start_month, end_month = st.select_slider('Select month range', options=list(range(1, 13)), value=(1, 12))
        filtered_month_data = filtered_year_data[
            (filtered_year_data['month'] >= start_month) & 
            (filtered_year_data['month'] <= end_month)
        ]        
        filtered_df = filtered_month_data

        total_sentiment_count = len(filtered_df)
        positive_count = filtered_df[filtered_df['Actual_sentiment'] == 1].shape[0]
        negative_count = filtered_df[filtered_df['Actual_sentiment'] == 0].shape[0]
        positive_percentage = (positive_count / total_sentiment_count) * 100
        negative_percentage = (negative_count / total_sentiment_count) * 100   
        average_sentiment = filtered_df['Actual_sentiment'].mean()

        col2, col3, col4 = st.columns([3,3,1])
        with col2:
            st.metric("Positive Sentiments", f"{positive_count} ({positive_percentage:.2f}%)")
        with col3:
            st.metric("Negative Sentiments", f"{negative_count} ({negative_percentage:.2f}%)")
        with col4:
            st.metric("Ratio", f"{average_sentiment:.2f}")        
        st.metric(label="Total Sentiments", value=total_sentiment_count)        

        sentiment_over_years = filtered_df.groupby('date')['Actual_sentiment'].value_counts().unstack().fillna(0)
        fig_years = px.line(
            sentiment_over_years, 
            x=sentiment_over_years.index, 
            y=sentiment_over_years.columns, 
            labels={'value': 'Number of Reviews', 'date': 'Year'}, 
            title='Sentiment Over Years'
        )
        fig_years.update_xaxes(dtick=1, tick0=min(sentiment_over_years.index), tickvals=sentiment_over_years.index)
        filtered_df['month'] = filtered_df['month'].astype(str).str.zfill(2)
        filtered_df['year_month'] = filtered_df['date'].astype(str) + '-' + filtered_df['month']
        sentiment_over_months = filtered_df.groupby(['year_month', 'Actual_sentiment']).size().unstack().fillna(0)
        fig_months = px.line(sentiment_over_months, x=sentiment_over_months.index, y=[1, 0], labels={'value': 'Number of Reviews', 'year_month': 'Month'}, title='Sentiment Over Months')

        col1, col2 = st.columns(2)

        with col1:
            st.plotly_chart(fig_years, use_container_width=True)
        with col2:
            st.plotly_chart(fig_months, use_container_width=True)

        top_reviews_by_country = filtered_df.groupby('country_name')['Actual_sentiment'].count().nlargest(5)
        bottom_reviews_by_country = filtered_df.groupby('country_name')['Actual_sentiment'].count().nsmallest(5)

        fig_top_reviews = px.bar(top_reviews_by_country, orientation='v', 
                                title="Top 5 Reviewed Countries",
                                labels={'value':'Number of Reviews', 'index':'Country'})
        fig_top_reviews.update_layout(xaxis_title="Country", yaxis_title="Number of Reviews")
        fig_top_reviews.update_traces(marker_color='blue')

        fig_bottom_reviews = px.bar(bottom_reviews_by_country, orientation='v', 
                                    title="Bottom 5 Reviewed Countries",
                                    labels={'value':'Number of Reviews', 'index':'Country'})
        fig_bottom_reviews.update_layout(xaxis_title="Country", yaxis_title="Number of Reviews")
        fig_bottom_reviews.update_traces(marker_color='red')

        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(fig_top_reviews, use_container_width=True)
        with col2:
            st.plotly_chart(fig_bottom_reviews, use_container_width=True)
        
        if st.button('Show Word Cloud for worst concerning words '):
            show_wordcloud_for_negative_reviews(filtered_df)  

        def determine_color(count):
            if count < 100:
                return 'red'
            elif count < 1000:
                return 'black'
            elif count < 10000:
                return 'blue'
            else:
                return 'orange'

        country_sentiment_counts = filtered_df.groupby('country_name')['Actual_sentiment'].value_counts().unstack(fill_value=0)
        country_sentiment_counts.columns = ['negative', 'positive'] if 0 in country_sentiment_counts.columns else ['positive']
        country_sentiment_counts.reset_index(inplace=True)
        country_sentiment_counts['positive_color'] = country_sentiment_counts['positive'].apply(determine_color)
        country_sentiment_counts['negative_color'] = country_sentiment_counts['negative'].apply(determine_color) if 'negative' in country_sentiment_counts.columns else 'black'

        color_legend = """
        #### Color Legend:
        - **Red**: Less than 100 counts
        - **Black**: Less than 1,000 counts
        - **Blue**: Less than 10,000 counts
        - **Orange**: Above 10,000 counts
        """

        fig_positive = px.scatter_geo(
            country_sentiment_counts,
            locations="country_name",
            locationmode='country names',
            text="country_name",
            hover_name="country_name",
            hover_data={
                'positive': True,
                'negative': True
            },
            projection="natural earth",
            title="Positive Sentiment Reviews by Country",
            size_max=15,
            color='positive_color',
            color_discrete_map={'red': 'red', 'black': 'black', 'blue': 'blue', 'orange': 'orange'}
        )

        fig_negative = px.scatter_geo(
            country_sentiment_counts,
            locations="country_name",
            locationmode='country names',
            text="country_name",
            hover_name="country_name",
            hover_data={
                'positive': True,
                'negative': True
            },
            projection="natural earth",
            title="Negative Sentiment Reviews by Country",
            size_max=15,
            color='negative_color',
            color_discrete_map={'red': 'red', 'black': 'black', 'blue': 'blue', 'orange': 'orange'}
        )

        fig_positive.update_traces(marker=dict(size=10))
        fig_negative.update_traces(marker=dict(size=10))

        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader('Positive Sentiment Map')
            st.plotly_chart(fig_positive, use_container_width=True)
            st.subheader('Negative Sentiment Map')
            st.plotly_chart(fig_negative, use_container_width=True)

        with col2:
            st.markdown(color_legend, unsafe_allow_html=True)

        country_sentiments = filtered_df.groupby('store_location')['Actual_sentiment'].agg(
            total_sentiments='count', 
            positive_sentiments='sum'
        )
        country_sentiments['positive_percent'] = (country_sentiments['positive_sentiments'] / country_sentiments['total_sentiments']) * 100
        country_sentiments['negative_percent'] = 100 - country_sentiments['positive_percent']
        country_sentiments['negative_sentiments'] = country_sentiments['total_sentiments'] - country_sentiments['positive_sentiments']

        country_sentiments['country_name'] = country_sentiments.index.map(get_country_name)
        sorted_countries = country_sentiments.sort_values(by='total_sentiments', ascending=False).reset_index()

        st.subheader('Search for a Country')
        search_query = st.text_input('Enter country name').lower()
        if search_query:
            search_results = sorted_countries[sorted_countries['country_name'].str.lower().str.contains(search_query)]
            if not search_results.empty:
                country_data = search_results.iloc[0]
                
                store_location = country_data['store_location']
                country_reviews = filtered_df[filtered_df['store_location'] == store_location]
                
                total_positive_sentiment = country_reviews[country_reviews['Actual_sentiment'] == 1].shape[0]
                total_negative_sentiment = country_reviews[country_reviews['Actual_sentiment'] == 0].shape[0]
                total_sentiments = country_reviews.shape[0]
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Positive Sentiment", total_positive_sentiment)
                with col2:
                    st.metric("Total Negative Sentiment", total_negative_sentiment)
                with col3:
                    st.metric("Total Sentiment", total_sentiments)

                fig = px.pie(
                    values=[country_data['positive_percent'], country_data['negative_percent']],
                    names=['Positive Percent', 'Negative Percent'],
                    title=f"Sentiment Distribution for {country_data['country_name']}"
                )
                st.plotly_chart(fig)
                
                negative_reviews = filtered_df[(filtered_df['store_location'] == country_data['store_location']) & (filtered_df['Actual_sentiment'] == 0)]
        
                if not negative_reviews.empty:
                    button_key = f"show_wordcloud_{country_data['store_location']}"
                    if st.button('Show concerning words for the above country', key=button_key):                        
                        if negative_reviews['title'].isna().all():
                            st.error("No titles available to generate a word cloud.")
                        else:
                            titles = negative_reviews['title'].dropna()
                            wordcloud = WordCloud(width=800, height=400, background_color='white').generate(' '.join(titles))
                            plt.figure(figsize=(10, 5))
                            plt.imshow(wordcloud, interpolation='bilinear')
                            plt.axis("off")
                            plt.title("Word Cloud for Negative Sentiments")
                            st.pyplot(plt)
                            top_words = list(wordcloud.words_.keys())[:5]
                            st.subheader("Titles containing top words from the word cloud:")
                            for word in top_words:
                                relevant_titles = titles[titles.str.contains(word, case=False, na=False)]
                                st.markdown(f"#### Titles containing the word: **{word}**")
                                for title in relevant_titles.head(5):
                                    st.write(title)
                                
                else:
                    st.warning("No negative reviews found. Please adjust your search or selection.")
        else:
            search_results = sorted_countries.head(20)
        st.subheader('Countries by Sentiment Count')
        st.table(search_results[['country_name', 'store_location', 'total_sentiments', 'positive_percent', 'negative_percent']])
        
        top_positive = sorted_countries.nlargest(20, 'positive_percent')
        top_negative = sorted_countries.nlargest(20, 'negative_percent')

        fig_positive = px.bar(top_positive, x='positive_percent', y='country_name',
                            orientation='h', title="Top 20 Countries by Positive Sentiment Percent",
                            text='positive_percent')
        fig_positive.update_layout(yaxis={'categoryorder':'total ascending'}, xaxis_title="Positive Sentiment Percent", yaxis_title="Country")
        fig_positive.update_traces(texttemplate='%{text:.2s}%', textposition='outside')

        fig_negative = px.bar(top_negative, x='negative_percent', y='country_name',
                            orientation='h', title="Top 20 Countries by Negative Sentiment Percent",
                            text='negative_percent')
        fig_negative.update_layout(yaxis={'categoryorder':'total ascending'}, xaxis_title="Negative Sentiment Percent", yaxis_title="Country")
        fig_negative.update_traces(texttemplate='%{text:.2s}%', textposition='outside')

        st.plotly_chart(fig_positive, use_container_width=True)
        st.plotly_chart(fig_negative, use_container_width=True)

        top_10_countries = sorted_countries.head(10)
        fig = px.bar(
            top_10_countries,
            x="country_name",
            y=["positive_percent", "negative_percent"],
            title="Positive and Negative Sentiment Percentages for Top 10 Countries",
            labels={"value": "Percentage", "variable": "Sentiment Type", "country_name": "Country"},
            barmode='group'
        )
        fig.update_layout(
            xaxis_title="Country",
            yaxis_title="Sentiment Percentage",
            legend_title="Sentiment Type",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)

        bottom_10_countries = sorted_countries.tail(10)
        fig = px.bar(
            bottom_10_countries,
            x="country_name",
            y=["positive_percent", "negative_percent"],
            title="Positive and Negative Sentiment Percentages for Bottom 10 Countries",
            labels={"value": "Percentage", "variable": "Sentiment Type", "country_name": "Country"},
            barmode='group'
        )
        fig.update_layout(
            xaxis_title="Country",
            yaxis_title="Sentiment Percentage",
            legend_title="Sentiment Type",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
