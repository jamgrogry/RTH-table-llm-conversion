import os
import csv
import ollama
from flask import Flask, request, jsonify, send_file, render_template, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def home():
    return render_template('index.html')

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
        messages=[{"role": "user", "content": "convert provided table into .csv format including triple backticks", "images": [filepath]}],
        options={
            "seed": 42,           # Fixes randomness for reproducibility
            "temperature": 0.7,   # Controls randomness (lower = more deterministic)
            "num_ctx": 2048,      # Context length
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
            "csv_data": csv_content  # Send CSV data for UI display
        })

    return jsonify({"error": "Failed to generate CSV"}), 500

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
