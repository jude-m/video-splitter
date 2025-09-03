#!/usr/bin/env python3
"""
Video Splitter Web Server (Cross-platform FFmpeg version)
A simple Python web server that allows users to split videos by timestamps.
Works on Windows, macOS, and Linux with ffmpeg.
"""

import os
import re
import json
import tempfile
import shutil
import subprocess
import platform
from pathlib import Path
from flask import Flask, request, jsonify, send_file, render_template_string
from werkzeug.utils import secure_filename
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 1500 * 1024 * 1024  # 1.5GB max file size
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()

# Allowed video extensions
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm', 'flv', 'wmv', 'mpg', 'mpeg', 'm4v'}

# HTML template with embedded JavaScript
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Video Splitter</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }

        .container {
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            max-width: 600px;
            width: 100%;
        }

        h1 {
            text-align: center;
            margin-bottom: 30px;
            color: #333;
            font-size: 2.5em;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .form-group {
            margin-bottom: 25px;
        }

        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #555;
            font-size: 1.1em;
        }

        input[type="file"] {
            width: 100%;
            padding: 12px;
            border: 2px dashed #667eea;
            border-radius: 10px;
            background: #f8f9ff;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        input[type="file"]:hover {
            border-color: #764ba2;
            background: #f0f2ff;
        }

        input[type="text"] {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 14px;
            transition: border-color 0.3s ease;
        }

        input[type="text"]:focus {
            outline: none;
            border-color: #667eea;
        }

        textarea {
            width: 100%;
            padding: 15px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            resize: vertical;
            min-height: 100px;
            transition: border-color 0.3s ease;
        }

        textarea:focus {
            outline: none;
            border-color: #667eea;
        }

        .example {
            font-size: 0.9em;
            color: #777;
            margin-top: 5px;
            font-style: italic;
        }

        button {
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 1.2em;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        button:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
        }

        button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }

        .progress-container {
            margin-top: 20px;
            display: none;
        }

        .progress-bar {
            width: 100%;
            height: 20px;
            background: #e0e0e0;
            border-radius: 10px;
            overflow: hidden;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            width: 0%;
            transition: width 0.3s ease;
        }

        .progress-text {
            text-align: center;
            margin-top: 10px;
            font-weight: 600;
            color: #555;
        }

        .status {
            margin-top: 20px;
            padding: 15px;
            border-radius: 10px;
            display: none;
        }

        .status.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }

        .status.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }

        .status.info {
            background: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }

        .status.warning {
            background: #fff3cd;
            color: #856404;
            border: 1px solid #ffeaa7;
        }

        .file-info {
            margin-top: 15px;
            padding: 10px;
            background: #f8f9ff;
            border-radius: 8px;
            font-size: 0.9em;
            color: #555;
        }

        .download-links {
            margin-top: 20px;
            padding: 15px;
            background: #f8f9ff;
            border-radius: 10px;
            display: none;
        }

        .download-link {
            display: block;
            padding: 10px;
            margin: 5px 0;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            text-decoration: none;
            border-radius: 5px;
            text-align: center;
            transition: all 0.3s ease;
        }

        .download-link:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
        }

        .server-info {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: rgba(255, 255, 255, 0.9);
            padding: 10px 15px;
            border-radius: 10px;
            font-size: 0.9em;
            color: #666;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }

        .ffmpeg-status {
            margin-top: 10px;
            padding: 10px;
            background: #f0f0f0;
            border-radius: 5px;
            font-size: 0.9em;
        }

        .ffmpeg-status.available {
            background: #d4edda;
            color: #155724;
        }

        .ffmpeg-status.missing {
            background: #f8d7da;
            color: #721c24;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎬 Video Splitter</h1>
        
        <form id="uploadForm">
            <div class="form-group">
                <label for="videoFile">Select Video File:</label>
                <input type="file" id="videoFile" name="video" accept="video/*" required>
                <div class="file-info" id="fileInfo" style="display: none;"></div>
            </div>

            <div class="form-group">
                <label for="outputPath">Save Location:</label>
                <input type="text" id="outputPath" name="outputPath" placeholder="e.g., /Users/username/Desktop/clips or C:\Videos\clips">
                <div class="example">
                    Enter the folder path where clips will be saved.
                </div>
            </div>

            <div class="form-group">
                <label for="timestamps">Timestamps (comma-separated):</label>
                <textarea id="timestamps" name="timestamps" placeholder="Enter timestamps..." required></textarea>
                <div class="example">
                    Examples:<br>
                    • 1:34:30 - 1:40:43, 40:43 - 45:00<br>
                    • 12:34-43:56
                </div>
            </div>

            <button type="submit" id="splitBtn">🔪 Split Video</button>
        </form>

        <div class="progress-container" id="progressContainer">
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill"></div>
            </div>
            <div class="progress-text" id="progressText">Preparing...</div>
        </div>

        <div class="status" id="status"></div>
        
        <div class="download-links" id="downloadLinks"></div>
    </div>

    <script>
        // Set default output path based on OS
        window.addEventListener('load', function() {
            const outputPathField = document.getElementById('outputPath');
            
            // Set default path based on OS
            if (navigator.platform.includes('Mac')) {
                // macOS default
                outputPathField.value = '/Volumes/Share/Akampitha/Shortclips';
            } else if (navigator.platform.includes('Win')) {
                // Windows default
                outputPathField.value = '\\\\Arana\\Share\\Akampitha\\Shortclips';
            } else {
                // Linux or other OS - leave empty
                outputPathField.placeholder = 'Enter folder path for clips';
            }
        });

        // Handle file selection
        document.getElementById('videoFile').addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const fileInfo = document.getElementById('fileInfo');
                fileInfo.style.display = 'block';
                fileInfo.innerHTML = `
                    <strong>File:</strong> ${file.name}<br>
                    <strong>Size:</strong> ${(file.size / 1024 / 1024).toFixed(2)} MB<br>
                    <strong>Type:</strong> ${file.type}
                `;
            }
        });

        // Show status message
        function showStatus(message, type = 'info') {
            const status = document.getElementById('status');
            status.textContent = message;
            status.className = `status ${type}`;
            status.style.display = 'block';
        }

        // Update progress
        function updateProgress(percent, text) {
            const progressContainer = document.getElementById('progressContainer');
            const progressFill = document.getElementById('progressFill');
            const progressText = document.getElementById('progressText');
            
            progressContainer.style.display = 'block';
            progressFill.style.width = percent + '%';
            progressText.textContent = text;
        }

        // Handle form submission
        document.getElementById('uploadForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const file = document.getElementById('videoFile').files[0];
            const timestamps = document.getElementById('timestamps').value;
            const outputPath = document.getElementById('outputPath').value;
            
            if (!file || !timestamps) {
                showStatus('Please select a file and enter timestamps.', 'error');
                return;
            }
            
            if (!outputPath) {
                showStatus('Please specify a save location for the clips.', 'error');
                return;
            }
            
            const formData = new FormData();
            formData.append('video', file);
            formData.append('timestamps', timestamps);
            formData.append('outputPath', outputPath);
            
            const splitBtn = document.getElementById('splitBtn');
            splitBtn.disabled = true;
            splitBtn.textContent = 'Processing...';
            
            // Reset download links
            const downloadLinks = document.getElementById('downloadLinks');
            downloadLinks.style.display = 'none';
            downloadLinks.innerHTML = '';
            
            updateProgress(20, 'Uploading video...');
            showStatus('Uploading and processing video...', 'info');
            
            try {
                const response = await fetch('/split', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    updateProgress(100, 'Complete!');
                    
                    if (result.saved_to_path) {
                        showStatus(`Successfully saved ${result.clips.length} video clip(s) to: ${result.saved_to_path}`, 'success');
                        // Don't show download links if saved to path
                    } else {
                        showStatus(`Successfully created ${result.clips.length} video clip(s)!`, 'success');
                        
                        // Show download links
                        downloadLinks.style.display = 'block';
                        downloadLinks.innerHTML = '<h3>Download Clips:</h3>';
                        
                        result.clips.forEach(clip => {
                            const link = document.createElement('a');
                            link.href = `/download/${clip.id}`;
                            link.className = 'download-link';
                            link.textContent = `📥 ${clip.filename}`;
                            link.download = clip.filename;
                            downloadLinks.appendChild(link);
                        });
                    }
                } else {
                    showStatus(`Error: ${result.error}`, 'error');
                    updateProgress(0, '');
                }
            } catch (error) {
                showStatus(`Error: ${error.message}`, 'error');
                updateProgress(0, '');
            } finally {
                splitBtn.disabled = false;
                splitBtn.textContent = '🔪 Split Video';
            }
        });
    </script>
</body>
</html>
'''

def check_ffmpeg():
    """Check if ffmpeg is available"""
    try:
        # Try different possible ffmpeg commands
        ffmpeg_cmd = 'ffmpeg.exe' if platform.system() == 'Windows' else 'ffmpeg'
        result = subprocess.run([ffmpeg_cmd, '-version'], 
                              capture_output=True, 
                              text=True, 
                              check=False)
        return result.returncode == 0, ffmpeg_cmd
    except FileNotFoundError:
        return False, None

def get_ffmpeg_command():
    """Get the appropriate ffmpeg command for the OS"""
    if platform.system() == 'Windows':
        # Try different possible locations on Windows
        possible_paths = [
            'ffmpeg.exe',  # In PATH or same directory
            r'C:\ffmpeg\bin\ffmpeg.exe',  # Common installation path
            r'C:\Program Files\ffmpeg\bin\ffmpeg.exe',
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ffmpeg.exe')  # Same directory as script
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
            try:
                result = subprocess.run([path, '-version'], 
                                      capture_output=True, 
                                      check=False)
                if result.returncode == 0:
                    return path
            except:
                continue
        
        # Fallback to hoping it's in PATH
        return 'ffmpeg.exe'
    else:
        return 'ffmpeg'

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def parse_timestamp(timestamp):
    """Parse timestamp string to seconds"""
    parts = timestamp.strip().split(':')
    if len(parts) == 2:  # mm:ss
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:  # hh:mm:ss
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    else:
        raise ValueError(f"Invalid timestamp format: {timestamp}")

def parse_timestamp_ranges(timestamps_text):
    """Parse comma-separated timestamp ranges"""
    ranges = []
    for range_str in timestamps_text.split(','):
        range_str = range_str.strip()
        if not range_str:
            continue
        
        parts = range_str.split('-')
        if len(parts) != 2:
            raise ValueError(f"Invalid range format: {range_str}")
        
        start = parse_timestamp(parts[0].strip())
        end = parse_timestamp(parts[1].strip())
        
        if start >= end:
            raise ValueError(f"Invalid range: start time must be before end time in {range_str}")
        
        ranges.append({
            'start': start,
            'end': end,
            'start_str': parts[0].strip(),
            'end_str': parts[1].strip()
        })
    
    return ranges

def get_first_word(filename):
    """Get first word from filename - works with Unicode"""
    # Remove file extension
    name_without_ext = os.path.splitext(filename)[0]
    
    # Split on space first (most common)
    if ' ' in name_without_ext:
        return name_without_ext.split(' ')[0]
    
    # Try other delimiters
    for delimiter in ['_', '-', '.']:
        if delimiter in name_without_ext:
            return name_without_ext.split(delimiter)[0]
    
    # No delimiter found, return whole name
    return name_without_ext if name_without_ext else "clip"

# Store for temporary clip files
temp_clips = {}

@app.route('/')
def index():
    """Serve the main HTML page"""
    import socket
    hostname = socket.gethostname()
    try:
        # Get actual IP address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = socket.gethostbyname(hostname)
    
    server_address = f"{local_ip}:8080"
    return render_template_string(HTML_TEMPLATE, server_address=server_address)

@app.route('/check-ffmpeg')
def check_ffmpeg_route():
    """Check if ffmpeg is available"""
    available, _ = check_ffmpeg()
    if available:
        return jsonify({'available': True, 'message': 'FFmpeg is installed and ready'})
    else:
        if platform.system() == 'Windows':
            message = 'Please install FFmpeg. Download from: https://ffmpeg.org/download.html#build-windows'
        else:
            message = 'Please install FFmpeg. On macOS: brew install ffmpeg, On Linux: sudo apt install ffmpeg'
        return jsonify({'available': False, 'message': message})

@app.route('/split', methods=['POST'])
def split_video():
    """Handle video splitting using ffmpeg directly"""
    try:
        # Check if ffmpeg is available
        ffmpeg_cmd = get_ffmpeg_command()
        
        # Check if video file was uploaded
        if 'video' not in request.files:
            return jsonify({'error': 'No video file provided'}), 400
        
        file = request.files['video']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Allowed types: ' + ', '.join(ALLOWED_EXTENSIONS)}), 400
        
        # Get timestamps
        timestamps = request.form.get('timestamps', '')
        if not timestamps:
            return jsonify({'error': 'No timestamps provided'}), 400
        
        # Get output path (optional)
        output_path = request.form.get('outputPath', '').strip()
        save_to_path = False
        
        # Validate output path if provided
        if output_path:
            output_path = os.path.expanduser(output_path)  # Expand ~ to home directory
            if not os.path.exists(output_path):
                try:
                    os.makedirs(output_path, exist_ok=True)
                    save_to_path = True
                except Exception as e:
                    return jsonify({'error': f'Cannot create output directory: {str(e)}'}), 400
            elif not os.path.isdir(output_path):
                return jsonify({'error': 'Output path must be a directory'}), 400
            else:
                save_to_path = True
        
        # Parse timestamps
        try:
            ranges = parse_timestamp_ranges(timestamps)
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        
        original_filename = file.filename  # Keep the original with Sinhala text
        safe_filename = secure_filename(file.filename)  # For safe file operations, Save uploaded file temporarily

        # If secure_filename stripped everything, use a generic name
        if not safe_filename or safe_filename == '.mp4':
            safe_filename = 'temp_video.mp4'

        temp_dir = tempfile.mkdtemp()
        input_path = os.path.join(temp_dir, safe_filename)
        file.save(input_path)
        
        # Process video
        clips_info = []
        first_word = get_first_word(original_filename)
        
        try:
            for i, range_info in enumerate(ranges, 1):  # Start counting from 1
                # Create output filename with incremental number
                output_filename = f"{first_word}-{i}-[{range_info['start_str'].replace(':', '_')} - {range_info['end_str'].replace(':', '_')}].mp4"
                
                # Determine output path
                if save_to_path:
                    # Save directly to user-specified path
                    clip_output_path = os.path.join(output_path, output_filename)
                else:
                    # Save to temp directory for download
                    clip_output_path = os.path.join(temp_dir, output_filename)
                
                # Calculate duration
                duration = range_info['end'] - range_info['start']
                
                # Build ffmpeg command
                cmd = [
                    ffmpeg_cmd,
                    '-i', input_path,
                    '-ss', str(range_info['start']),
                    '-t', str(duration),
                    '-c', 'copy',  # Copy codecs (no re-encoding for speed)
                    '-avoid_negative_ts', 'make_zero',
                    '-y',  # Overwrite output file
                    clip_output_path
                ]
                
                # Run ffmpeg
                logger.info(f"Running ffmpeg command: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    logger.error(f"FFmpeg error: {result.stderr}")
                    # Try again with re-encoding if copy failed
                    cmd = [
                        ffmpeg_cmd,
                        '-i', input_path,
                        '-ss', str(range_info['start']),
                        '-t', str(duration),
                        '-c:v', 'libx264',
                        '-c:a', 'aac',
                        '-y',
                        clip_output_path
                    ]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    
                    if result.returncode != 0:
                        raise Exception(f"FFmpeg failed: {result.stderr}")
                
                # Store clip info only if not saving to path (for download)
                if not save_to_path:
                    clip_id = f"clip_{i}_{os.urandom(8).hex()}"
                    temp_clips[clip_id] = {
                        'path': clip_output_path,
                        'filename': output_filename,
                        'temp_dir': temp_dir
                    }
                    
                    clips_info.append({
                        'id': clip_id,
                        'filename': output_filename
                    })
                else:
                    clips_info.append({
                        'filename': output_filename
                    })
            
            # Clean up temp files if saved to path
            if save_to_path:
                shutil.rmtree(temp_dir, ignore_errors=True)
                return jsonify({
                    'success': True,
                    'clips': clips_info,
                    'saved_to_path': output_path
                })
            else:
                return jsonify({
                    'success': True,
                    'clips': clips_info
                })
            
        except Exception as e:
            # Clean up on error
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise
        
    except Exception as e:
        logger.error(f"Error splitting video: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/download/<clip_id>')
def download_clip(clip_id):
    """Download a processed clip"""
    if clip_id not in temp_clips:
        return jsonify({'error': 'Clip not found'}), 404
    
    clip_info = temp_clips[clip_id]
    
    # Send file
    return send_file(
        clip_info['path'],
        as_attachment=True,
        download_name=clip_info['filename'],
        mimetype='video/mp4'
    )

def cleanup_temp_files():
    """Clean up any remaining temporary files"""
    for clip_id, clip_info in list(temp_clips.items()):
        try:
            if 'temp_dir' in clip_info and os.path.exists(clip_info['temp_dir']):
                shutil.rmtree(clip_info['temp_dir'], ignore_errors=True)
            del temp_clips[clip_id]
        except Exception as e:
            logger.error(f"Error cleaning up temp file: {e}")

if __name__ == '__main__':
    import atexit
    import socket
    
    # Register cleanup function
    atexit.register(cleanup_temp_files)
    
    # Check for ffmpeg
    ffmpeg_available, _ = check_ffmpeg()
    
    # Get local IP address
    hostname = socket.gethostname()
    try:
        # This gets the actual IP address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = socket.gethostbyname(hostname)
    
    print("\n" + "="*60)
    print("🎬 Video Splitter Server")
    print("="*60)
    
    if not ffmpeg_available:
        print("\n⚠️  WARNING: FFmpeg not found!")
        print("\nTo install FFmpeg:")
        if platform.system() == 'Windows':
            print("  1. Download from: https://ffmpeg.org/download.html#build-windows")
            print("  2. Extract to C:\\ffmpeg")
            print("  3. Add C:\\ffmpeg\\bin to your PATH")
            print("\n  OR place ffmpeg.exe in the same folder as this script")
        elif platform.system() == 'Darwin':  # macOS
            print("  Run: brew install ffmpeg")
        else:  # Linux
            print("  Run: sudo apt install ffmpeg")
        print("\n" + "="*60)
    else:
        print("✅ FFmpeg is installed and ready!")
    
    print(f"\nServer starting...")
    print(f"Local access: http://localhost:8080")
    print(f"Network access: http://{local_ip}:8080")
    print("\nShare the network address with others on your local network")
    print("Press Ctrl+C to stop the server\n")
    print("="*60 + "\n")
    
    # Run the server
    # Using port 8080 to avoid conflicts with macOS services (AirPlay uses 5000)
    port = 8080
    print(f"\n🔌 Using port {port} (change if needed)")
    app.run(host='0.0.0.0', port=port, debug=False)