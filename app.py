import os
import magic
from flask import Flask, render_template, request, send_file, jsonify
from werkzeug.utils import secure_filename
from stegano import hide_audio_in_images, extract_audio_from_images
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'flac', 'ogg'}
ALLOWED_IMAGE_EXTENSIONS = {'png'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def validate_file_type(file_path, expected_mime_types):
    mime = magic.Magic(mime=True)
    file_mime_type = mime.from_file(file_path)
    return any(file_mime_type.startswith(expected_type) for expected_type in expected_mime_types)

def cleanup_old_files():
    for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER]:
        for file in os.listdir(folder):
            file_path = os.path.join(folder, file)
            if os.path.isfile(file_path):
                os.remove(file_path)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/hide_audio', methods=['POST'])
def hide_audio():
    if 'audio' not in request.files or 'images' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    audio_file = request.files['audio']
    image_files = request.files.getlist('images')

    if audio_file.filename == '' or not image_files:
        return jsonify({'error': 'No selected file'}), 400

    if not allowed_file(audio_file.filename, ALLOWED_AUDIO_EXTENSIONS):
        return jsonify({'error': 'Invalid audio file format'}), 400

    for image_file in image_files:
        if not allowed_file(image_file.filename, ALLOWED_IMAGE_EXTENSIONS):
            return jsonify({'error': 'Invalid image file format'}), 400

    audio_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(audio_file.filename))
    audio_file.save(audio_path)
    
    if not validate_file_type(audio_path, ['audio/']):
        os.remove(audio_path)
        return jsonify({'error': 'Invalid audio file content'}), 400

    image_paths = []
    for image_file in image_files:
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(image_file.filename))
        image_file.save(image_path)
        if not validate_file_type(image_path, ['image/png']):
            os.remove(image_path)
            return jsonify({'error': 'Invalid image file content'}), 400
        image_paths.append(image_path)

    try:
        modified_images = hide_audio_in_images(audio_path, image_paths)
        if not modified_images:
            return jsonify({'error': 'Failed to hide audio in images'}), 400
        return jsonify({'message': 'Audio hidden successfully', 'files': modified_images}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

@app.route('/extract_audio', methods=['POST'])
def extract_audio():
    if 'images' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    image_files = request.files.getlist('images')

    if not image_files:
        return jsonify({'error': 'No selected files'}), 400

    image_paths = []
    for image_file in image_files:
        if not allowed_file(image_file.filename, ALLOWED_IMAGE_EXTENSIONS):
            return jsonify({'error': 'Invalid image file format'}), 400
        
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(image_file.filename))
        image_file.save(image_path)
        
        if not validate_file_type(image_path, ['image/png']):
            os.remove(image_path)
            return jsonify({'error': 'Invalid image file content'}), 400
        
        image_paths.append(image_path)

    output_audio_path = os.path.join(app.config['OUTPUT_FOLDER'], 'extracted_audio.mp3')

    try:
        output_audio_path = extract_audio_from_images(image_paths, output_audio_path)
        if not output_audio_path:
            return jsonify({'error': 'Failed to extract audio from images'}), 400
        return jsonify({'message': 'Audio extracted successfully', 'file': output_audio_path}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<path:filename>')
def download_file(filename):
    return send_file(filename, as_attachment=True)

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    
    cleanup_old_files()
    
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=cleanup_old_files, trigger="interval", hours=3)
    scheduler.start()
    
    app.run(debug=True)