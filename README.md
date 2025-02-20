# RTH table conversion LLM Web App

This is a Flask-based web application that allows users to upload an image of a handwriten data-table, extract text using an LLM (specifically `Llama3.2-Vision`), and convert the output into a CSV file that can be downloaded.

## Installation

### Clone the Repository
```bash
git clone https://github.com/ jamgrogry/RTH-table-llm-conversion.git
cd RTH-table-llm-conversion
```

### Set Up a Virtual Environment

python -m venv venv
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate      # Windows

### Install Dependencies

pip install -r requirements.txt

### Install LLM Model

ollama pull llama3.2-vision:11b

### Run the Flask App

python app.py

shoud run at http://127.0.0.1:5000/.

(will also need to install 'Llama3.2-Vision:11b' through ollama)