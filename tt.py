from flask import Flask, request, jsonify, send_from_directory, render_template_string
import os
import subprocess
import threading
import time
import ast
import sys

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
running_scripts = {}

def run_script(file_path):
    while True:
        process = subprocess.Popen(['python', file_path])
        process.wait()
        if file_path not in running_scripts or not running_scripts[file_path]:
            break
        time.sleep(1)

def install_dependencies(file_path):
    with open(file_path, 'r') as file:
        source_code = file.read()
    
    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        return f'SyntaxError: {str(e)}'
    
    dependencies = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                dependencies.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            dependencies.add(node.module)
    
    # Install the required dependencies using pip
    for dependency in dependencies:
        subprocess.call([sys.executable, '-m', 'pip', 'install', dependency])
    
    return f'Dependencies installed successfully: {", ".join(dependencies)}'

@app.route('/')
def index():
    files = os.listdir(UPLOAD_FOLDER)
    html_content = """
<!DOCTYPE html>
<html lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>رفع الملفات وتشغيلها</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f0f0f0;
            margin: 0;
            padding: 0;
        }

        header {
            background-color: #000;
            color: #fff;
            text-align: center;
            padding: 20px 0;
        }

        main {
            background-color: #fff;
            padding: 20px;
            margin: 20px;
            border-radius: 10px;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
        }

        footer {
            background-color: #eee;
            padding: 20px;
            text-align: center;
            margin-top: 20px;
        }

        form {
            margin-bottom: 20px;
        }

        input[type="file"] {
            margin-right: 10px;
        }

        button {
            background-color: #4caf50;
            color: #fff;
            border: none;
            padding: 10px 20px;
            cursor: pointer;
            border-radius: 5px;
        }

        button:hover {
            background-color: #45a049;
        }

        ul {
            list-style-type: none;
            padding: 0;
        }

        li {
            margin-bottom: 10px;
        }

        li button {
            background-color: #f44336;
            color: #fff;
            border: none;
            padding: 5px 10px;
            cursor: pointer;
            border-radius: 3px;
        }

        li button:hover {
            background-color: #d32f2f;
        }
    </style>
</head>
<body>
    <header>
        <h1>رفع الملفات وتشغيلها</h1>
    </header>
    <main>
        <form id="uploadForm" enctype="multipart/form-data">
            <input type="file" id="fileInput" name="file" accept=".py">
            <button type="button" onclick="uploadFile()">رفع الملف</button>
        </form>
        <div id="message"></div>
        <h2>الملفات المرفوعة</h2>
        <ul id="fileList">
            {% for file in files %}
                <li>{{ file }} <button onclick="deleteFile('{{ file }}')">حذف</button></li>
            {% endfor %}
        </ul>
    </main>
    <footer>
        <p>تواصل معنا: example@example.com</p>
        <p>تابعنا على الشبكات الاجتماعية</p>
        <!-- يمكنك إضافة رموز وصلات لوسائط التواصل الاجتماعي هنا -->
    </footer>

    <script>
        async function uploadFile() {
            const formData = new FormData(document.getElementById('uploadForm'));
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            document.getElementById('message').innerText = result.message;
            loadFiles();
        }

        async function loadFiles() {
            const response = await fetch('/files');
            const files = await response.json();
            const fileList = document.getElementById('fileList');
            fileList.innerHTML = '';
            files.forEach(file => {
                const li = document.createElement('li');
                li.textContent = file;
                const deleteButton = document.createElement('button');
                deleteButton.innerText = 'حذف';
                deleteButton.onclick = () => deleteFile(file);
                li.appendChild(deleteButton);
                fileList.appendChild(li);
            });
        }

        async function deleteFile(fileName) {
            const response = await fetch(`/delete/${fileName}`, {
                method: 'DELETE'
            });
            const result = await response.json();
            document.getElementById('message').innerText = result.message;
            loadFiles();
        }

        loadFiles();
    </script>
</body>
</html>
"""
    return render_template_string(html_content, files=files)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'message': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    if os.path.exists(file_path):
        return jsonify({'message': 'File already exists', 'exists': True}), 409
    file.save(file_path)
    running_scripts[file_path] = True
    threading.Thread(target=run_script, args=(file_path,)).start()
    dependencies_result = install_dependencies(file_path)
    return jsonify({'message': 'File uploaded successfully', 'dependencies': dependencies_result}), 200

@app.route('/files', methods=['GET'])
def list_files():
    files = os.listdir(UPLOAD_FOLDER)
    return jsonify(files), 200

@app.route('/delete/<filename>', methods=['DELETE'])
def delete_file(filename):
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        running_scripts[file_path] = False
        os.remove(file_path)
        return jsonify({'message': 'File deleted successfully'}), 200
    return jsonify({'message': 'File not found'}), 404

if __name__ == '__main__':
    app.run(debug=True)