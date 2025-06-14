from flask import Flask, request, render_template, redirect, url_for, jsonify
import torch
from PIL import Image
import io
import base64
import re

app = Flask(__name__)

# Load custom YOLOv5 model
model = torch.hub.load('ultralytics/yolov5', 'custom', path='weights/best.pt', force_reload=False)

# Calorie dictionary
calorie_dict = {
    "bitter melon": 17, "brinjal": 25, "cabbage": 25, "calabash": 14,
    "capsicum": 20, "cauliflower": 25, "cherry": 50, "garlic": 149,
    "ginger": 80, "green chili": 40, "kiwi": 61, "lady finger": 33,
    "onion": 40, "potato": 77, "sponge gourd": 16, "tomato": 18,
    "apple": 52, "avocado": 160, "banana": 89, "cucumber": 16,
    "dragon fruit": 60, "egg": 155, "guava": 68, "mango": 60,
    "orange": 47, "oren": 42, "peach": 39, "pear": 57,
    "pineapple": 50, "strawberry": 32, "custard apple": 101, "watermelon": 30
}

# Store result
detection_result = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    global detection_result

    if 'file' not in request.files:
        return "No file uploaded", 400

    file = request.files['file']
    image = Image.open(file.stream).convert("RGB")
    results = model(image)

    detected_items = []
    total_calories = 0

    for _, row in results.pandas().xyxy[0].iterrows():
        name = row['name'].lower()
        detected_items.append({
            'name': row['name'],
            'confidence': f"{row['confidence']:.2f}"
        })
        total_calories += calorie_dict.get(name, 0)

    # Render boxes
    image_with_boxes = results.render()[0]
    pil_img = Image.fromarray(image_with_boxes)
    img_byte_arr = io.BytesIO()
    pil_img.save(img_byte_arr, format='JPEG')
    base64_image = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')

    detection_result = {
        'detected_items': detected_items,
        'image': base64_image,
        'total_calories': total_calories
    }

    return redirect(url_for('result'))

@app.route('/result')
def result():
    if not detection_result:
        return "No detection result available", 400
    return render_template('result.html', result=detection_result)

@app.route('/detect', methods=['POST'])
def detect():
    data = request.get_json()
    if not data or 'image' not in data:
        return jsonify({'error': 'No image data received'}), 400

    try:
        img_data = re.sub('^data:image/.+;base64,', '', data['image'])
        img_bytes = base64.b64decode(img_data)
        image = Image.open(io.BytesIO(img_bytes)).convert("RGB")

        results = model(image)

        detected_items = []
        for _, row in results.pandas().xyxy[0].iterrows():
            name = row['name'].lower()
            detected_items.append({
                'name': row['name'].capitalize(),
                'calories': calorie_dict.get(name, 0)
            })

        return jsonify({'detected_items': detected_items})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/live')
def live_detection():
    return render_template('live.html')

if __name__ == '__main__':
    app.run(debug=True)
