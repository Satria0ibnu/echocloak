from datetime import timedelta
import os
import secrets
import uuid
from flask import Flask, render_template, request, send_file, jsonify, session
from werkzeug.utils import secure_filename
from stegano import hide_audio_in_images, extract_audio_from_images

app = Flask(__name__)

# Generate a secure secret key
secret_key = secrets.token_hex(32)
app.config['SECRET_KEY'] = secret_key

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
ALLOWED_AUDIO_EXTENSIONS = {'mp3'}
ALLOWED_IMAGE_EXTENSIONS = {'png'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=10)

@app.route('/')
def index():
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())  # Generate a unique user ID for each session
    return render_template('index.html')

@app.route('/hide_audio', methods=['POST'])
def hide_audio():
    user_id = session['user_id']
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

    audio_path = os.path.join(app.config['UPLOAD_FOLDER'], user_id, secure_filename(audio_file.filename))
    audio_file.save(audio_path)

    image_paths = []
    for image_file in image_files:
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], user_id, secure_filename(image_file.filename))
        image_file.save(image_path)
        image_paths.append(image_path)

    try:
        modified_images = hide_audio_in_images(audio_path, image_paths)
        return jsonify({'message': 'Audio hidden successfully', 'files': modified_images}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/extract_audio', methods=['POST'])
def extract_audio():
    user_id = session['user_id']
    if 'images' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    image_files = request.files.getlist('images')

    if not image_files:
        return jsonify({'error': 'No selected files'}), 400

    for image_file in image_files:
        if not allowed_file(image_file.filename, ALLOWED_IMAGE_EXTENSIONS):
            return jsonify({'error': 'Invalid image file format'}), 400

    image_paths = []
    for image_file in image_files:
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], user_id, secure_filename(image_file.filename))
        image_file.save(image_path)
        image_paths.append(image_path)

    output_audio_path = os.path.join(app.config['OUTPUT_FOLDER'], user_id, 'extracted_audio.mp3')

    try:
        extract_audio_from_images(image_paths, output_audio_path)
        return jsonify({'message': 'Audio extracted successfully', 'file': output_audio_path}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<path:filename>')
def download_file(filename):
    return send_file(filename, as_attachment=True)

@app.teardown_request
def cleanup_request(exception):
    if exception:
        return
    user_id = session.get('user_id')
    if user_id:
        cleanup_user_files(user_id)

def cleanup_user_files(user_id):
    uploads_folder = os.path.join(app.config['UPLOAD_FOLDER'], user_id)
    outputs_folder = os.path.join(app.config['OUTPUT_FOLDER'], user_id)
    for folder in [uploads_folder, outputs_folder]:
        if os.path.exists(folder):
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                os.remove(file_path)
            os.rmdir(folder)

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    app.run(debug=True)