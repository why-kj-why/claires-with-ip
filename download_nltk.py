import nltk
import os

# Define the directory where you want to download the NLTK data
nltk_data_dir = 'nltk_data'

# Create the directory if it doesn't exist
if not os.path.exists(nltk_data_dir):
    os.makedirs(nltk_data_dir)

# Download the required NLTK datasets
nltk.download('stopwords', download_dir=nltk_data_dir)
nltk.download('punkt', download_dir=nltk_data_dir)
