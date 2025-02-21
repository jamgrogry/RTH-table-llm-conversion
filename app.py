import os
import csv
import sqlite3
import ollama
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
DB_NAME = "database.db"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/setup_database', methods=['POST'])
def setup_database():
    """Creates an empty SQLite database if it doesn't exist."""
    if os.path.exists(DB_NAME):
        return jsonify({"message": "Database already exists!"}), 400

    conn = sqlite3.connect(DB_NAME)
    conn.close()
    
    return jsonify({"message": "New database created successfully!"})

@app.route('/open_database', methods=['POST'])
def open_database():
    """Checks if the database exists and is accessible."""
    if not os.path.exists(DB_NAME):
        return jsonify({"message": "Database not found. Create one first."})
    
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.close()
        return jsonify({"message": "Database exists and is accessible!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    # Process image using LLM (Llama3.2-Vision)
    response = ollama.chat(
        model="llama3.2-vision:11b",
        messages=[{"role": "user", "content": "convert provided table into .csv format with 5 columns including triple backticks", "images": [filepath]}],
        options={
            "seed": 42,
            "temperature": 0.7,
            "num_ctx": 2048,
        }
    )

    llm_text = response.get("message", {}).get("content", "")
    csv_content = extract_csv_from_response(llm_text)

    if csv_content:
        csv_filename = "output.csv"
        csv_path = os.path.join(UPLOAD_FOLDER, csv_filename)
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(csv_content)

        return jsonify({
            "csv_url": f"/uploads/{csv_filename}",
            "csv_data": csv_content
        })

    return jsonify({"error": "Failed to generate CSV"}), 500

import re

@app.route('/upload_to_database', methods=['POST'])
def upload_to_database():
    """Dynamically saves CSV data into the SQLite database."""
    if not os.path.exists(DB_NAME):
        return jsonify({"error": "Database does not exist. Create one first."}), 400

    csv_data = request.json.get("csv_data", [])
    if not csv_data:
        return jsonify({"error": "No CSV data provided!"}), 400

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Extract headers and clean them
    raw_headers = csv_data[0]  # First row is the header
    headers = []

    seen = {}
    for col in raw_headers:
        # Remove special characters and replace spaces with underscores
        clean_col = re.sub(r'\W+', '_', col.strip()).lower()

        # Ensure unique column names by appending a counter if needed
        count = seen.get(clean_col, 0)
        if count > 0:
            clean_col = f"{clean_col}_{count}"  # Rename duplicate
        seen[clean_col] = count + 1  # Increment count

        headers.append(clean_col)

    # Drop the old table if it exists
    cursor.execute("DROP TABLE IF EXISTS extracted_data")

    # Create table dynamically
    create_table_query = f'''
    CREATE TABLE extracted_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        {", ".join([f'"{col}" TEXT' for col in headers])}
    )
    '''
    cursor.execute(create_table_query)

    # Prepare placeholders (?,?,?)
    column_placeholders = ", ".join(["?" for _ in headers])

    # Insert data (skip the header row)
    for row in csv_data[1:]:
        # Ensure correct number of columns
        while len(row) < len(headers):  
            row.append("")  # Fill missing columns with empty strings
        while len(row) > len(headers):  
            row = row[:len(headers)]  # Trim extra columns
        
        cursor.execute(f'INSERT INTO extracted_data ({", ".join(headers)}) VALUES ({column_placeholders})', row)

    conn.commit()
    conn.close()

    return jsonify({"message": "Data successfully saved to the database!"})




def extract_csv_from_response(text):
    """Extract CSV data from model response."""
    if '```' in text:
        csv_part = text.split('```')[1].strip()
        rows = [row.split(",") for row in csv_part.split("\n") if row]
        return rows
    return None

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == "__main__":
    app.run(debug=True)
