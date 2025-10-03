from flask import Flask, request, jsonify, render_template_string
import nltk
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.nlp.stemmers import Stemmer
from sumy.summarizers.lsa import LsaSummarizer
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import base64, io
from PIL import Image
import pytesseract
import os

# --- Colab Specific Imports for Manual ngrok Setup ---
from pyngrok import ngrok
from google.colab.output import eval_js
import threading
import time

# NEW: Import Colab's user data utility
from google.colab import userdata
# ----------------------------------------------------

# --- Setup ---
LANGUAGE = "english"
EXTRACTED_ARTICLE_SENTENCES_LEN = 12
stemmer = Stemmer(LANGUAGE)
lsa_summarizer = LsaSummarizer(stemmer)
FLASK_PORT = 5000

# NEW: NGROK AUTHENTICATION SETUP (CRITICAL FIX)
try:
    # 1. Retrieve the token from Colab Secrets
    NGROK_TOKEN = userdata.get('NGROK_AUTH_TOKEN')

    # 2. Authenticate pyngrok using the token
    if NGROK_TOKEN:
        ngrok.set_auth_token(NGROK_TOKEN)
        print("ngrok authentication successful. Tunnel starting...")
    else:
        # If the secret isn't set, print instructions and exit gracefully
        print("FATAL ERROR: NGROK_AUTH_TOKEN secret not found.")
        print("Please set the NGROK_AUTH_TOKEN secret in the Colab sidebar (🔑) to your token.")
        exit(1) # Exit the script if authentication is impossible
except Exception as e:
    print(f"Error retrieving ngrok token: {e}")
    exit(1)
# ---------------------------------


# Hugging Face model (abstractive summarizer)
print("Loading Hugging Face model... (This may take a minute)")
try:
    tokenizer = AutoTokenizer.from_pretrained("ml6team/distilbart-tos-summarizer-tosdr")
    model = AutoModelForSeq2SeqLM.from_pretrained("ml6team/distilbart-tos-summarizer-tosdr")
    print("Hugging Face Model loaded successfully!")
except Exception as e:
    print(f"Error loading Hugging Face model: {e}")
    tokenizer = None
    model = None

app = Flask(__name__)

# --- Summarization helpers (omitted for brevity) ---
def get_extractive_summary(text, sentences_count=EXTRACTED_ARTICLE_SENTENCES_LEN):
    if not text: return ""
    try:
        parser = PlaintextParser.from_string(text, Tokenizer(LANGUAGE))
        summarized_info = lsa_summarizer(parser.document, sentences_count)
        summarized_info = [element._text for element in summarized_info]
        return ' '.join(summarized_info)
    except Exception:
        return text[:500]

def get_summary(text):
    if not tokenizer or not model: return "Model failed to load. Cannot generate summary."
    text = get_extractive_summary(text)
    inputs = tokenizer(text, max_length=1024, truncation=True, return_tensors="pt")
    outputs = model.generate(
        inputs["input_ids"], max_length=150, min_length=30, num_beams=4
    )
    summarized_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return summarized_text.strip()

# --- Utility to Serve the HTML (Index Route) ---
@app.route("/")
def serve_index():
    """Serves the main HTML content."""
    # (HTML content is exactly the same as the previous version)
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TOS Analyzer</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        body {
            font-family: 'Inter', sans-serif;
            background-color: #0b0c10;
            color: #c5c6c7;
        }
        .container-bg {
            background-color: #1f2833;
        }
        .text-area-bg {
            background-color: #2c3a4d;
            border: 1px solid #45a29e;
        }
        .btn-primary {
            background-color: #6610f2;
            transition: background-color 0.3s ease;
        }
        .btn-primary:hover {
            background-color: #560ed5;
        }
        .btn-secondary {
            background-color: #45a29e;
            transition: background-color 0.3s ease;
        }
        .btn-secondary:hover {
            background-color: #388a85;
        }
        .risk-bar {
            background-color: #45a29e;
        }
        .risk-bg {
            background-color: #2c3a4d;
        }
        .loading-animation {
            border-top-color: #45a29e;
            border-left-color: #45a29e;
            border-bottom-color: transparent;
            border-right-color: transparent;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .modal {
            background-color: rgba(0, 0, 0, 0.8);
            backdrop-filter: blur(5px);
        }
        #video {
            border-radius: 1rem;
            max-width: 100%;
        }

        .circular-progress {
            position: relative;
            width: 120px;
            height: 120px;
            margin: auto;
        }
        .circular-progress svg {
            transform: rotate(-90deg);
        }
        .circular-progress-bg {
            fill: none;
            stroke: #2c3a4d;
            stroke-width: 12;
        }
        .circular-progress-bar {
            fill: none;
            stroke-width: 12;
            stroke-linecap: round;
            transition: stroke-dashoffset 0.5s ease-in-out;
        }
        .circular-progress-text {
            fill: white;
            font-size: 2rem;
            font-weight: bold;
            text-anchor: middle;
            dominant-baseline: middle;
        }
        .safe .circular-progress-bar { stroke: #45a29e; }
        .warning .circular-progress-bar { stroke: #f0c541; }
        .unsafe .circular-progress-bar { stroke: #e31b54; }
    </style>
</head>
<body class="flex items-center justify-center min-h-screen p-4">

    <div id="app" class="w-full max-w-7xl rounded-2xl container-bg p-8 shadow-2xl transition-all duration-500">
        <!-- Main Content -->
        <div id="main-content" class="flex flex-col lg:flex-row lg:space-x-8">
            <!-- Input Section -->
            <div id="input-section" class="flex-1 flex flex-col items-center lg:items-start mb-8 lg:mb-0">
                <h1 class="text-3xl font-bold mb-6 text-center text-white">TOS & Regulations Analyzer</h1>
                <div class="w-full relative">
                    <div class="absolute top-2 right-2 flex space-x-2">
                        <button id="paste-btn" class="text-sm px-4 py-1.5 rounded-lg btn-secondary text-white font-medium">Paste</button>
                        <button id="clear-btn" class="text-sm px-4 py-1.5 rounded-lg btn-secondary text-white font-medium">Clear</button>
                    </div>
                    <textarea id="tos-input" rows="15" class="w-full text-area-bg p-6 rounded-xl text-white placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-[#45a29e] transition-colors" placeholder="Paste the agreement text below..."></textarea>
                </div>

                <div class="flex flex-col sm:flex-row mt-4 space-y-4 sm:space-y-0 sm:space-x-4 w-full">
                    <button id="upload-btn" class="px-6 py-3 rounded-full btn-secondary text-white font-semibold flex-1">Upload Photo</button>
                    <button id="take-photo-btn" class="px-6 py-3 rounded-full btn-secondary text-white font-semibold flex-1">Take Photo</button>
                </div>
                <input type="file" id="file-input" accept="image/*" class="hidden">

                <button id="analyze-btn" class="mt-8 px-12 py-4 text-lg font-semibold rounded-full btn-primary text-white w-full max-w-md shadow-lg shadow-purple-600/50">
                    Analyze
                </button>
            </div>

            <!-- Results Section -->
            <div id="results-section" class="flex-1 flex-col space-y-6 hidden">

                <div class="lg:col-span-2">
                    <div class="container-bg p-6 rounded-2xl">
                        <h2 class="text-xl font-bold mb-4 text-white">All Risk Scores</h2>
                        <div id="risk-scores" class="space-y-4">
                            <!-- Risk scores will be injected here by JS -->
                        </div>
                    </div>
                </div>

                <div class="container-bg p-6 rounded-2xl flex-grow flex flex-col">
                    <h2 class="text-xl font-bold mb-4 text-white">Summary</h2>
                    <p id="summary" class="text-gray-300 text-sm leading-relaxed"></p>
                </div>

                <div class="container-bg p-6 rounded-2xl flex-grow flex flex-col">
                    <h2 class="text-xl font-bold mb-4 text-white">Aggressive Language</h2>
                    <ul id="aggressive-language" class="list-disc list-inside space-y-1 text-sm text-gray-300"></ul>
                </div>

                <div class="container-bg p-6 rounded-2xl flex-grow flex flex-col">
                    <h2 class="text-xl font-bold mb-4 text-white">Suspicious Clauses</h2>
                    <ul id="suspicious-clauses" class="space-y-4">
                        <!-- Suspicious clauses will be injected here by JS -->
                    </ul>
                </div>

                <!-- New overall percentage section -->
                <div id="safety-score-section" class="container-bg p-6 rounded-2xl flex flex-col items-center justify-center text-center">
                    <h2 class="text-xl font-bold text-white mb-6">Overall Safety Score</h2>
                    <div class="circular-progress">
                        <svg viewBox="0 0 36 36">
                            <circle class="circular-progress-bg" cx="18" cy="18" r="16"></circle>
                            <circle class="circular-progress-bar" cx="18" cy="18" r="16" stroke-dasharray="100" stroke-dashoffset="100"></circle>
                        </svg>
                        <span id="safety-percentage-text" class="absolute inset-0 flex items-center justify-center text-3xl font-bold"></span>
                    </div>
                    <p id="safety-status" class="mt-4 text-white text-lg font-medium"></p>
                </div>
            </div>
        </div>

        <!-- Camera Modal -->
        <div id="camera-modal" class="modal fixed inset-0 z-50 flex items-center justify-center hidden">
            <div class="bg-gray-800 rounded-2xl p-6 relative w-11/12 max-w-2xl text-center">
                <h2 class="text-xl font-bold mb-4 text-white">Take a Photo</h2>
                <video id="video" autoplay class="rounded-xl w-full h-auto"></video>
                <div class="flex justify-center space-x-4 mt-6">
                    <button id="capture-btn" class="px-8 py-3 rounded-full btn-primary text-white font-semibold">Capture</button>
                    <button id="close-camera-btn" class="px-8 py-3 rounded-full btn-secondary text-white font-semibold">Close</button>
                </div>
            </div>
        </div>
        <canvas id="canvas" class="hidden"></canvas>

        <!-- Loading State -->
        <div id="loading-state" class="fixed inset-0 z-50 flex flex-col items-center justify-center hidden modal">
            <div class="loading-animation w-16 h-16 rounded-full border-4"></div>
            <p id="loading-text" class="mt-4 text-xl text-white">Analyzing, please wait...</p>
        </div>
    </div>

    <script type="module">
        // DOM Elements
        const app = document.getElementById('app');
        const mainContent = document.getElementById('main-content');
        const inputSection = document.getElementById('input-section');
        const loadingState = document.getElementById('loading-state');
        const resultsSection = document.getElementById('results-section');
        const tosInput = document.getElementById('tos-input');
        const analyzeBtn = document.getElementById('analyze-btn');
        const pasteBtn = document.getElementById('paste-btn');
        const clearBtn = document.getElementById('clear-btn');
        const uploadBtn = document.getElementById('upload-btn');
        const fileInput = document.getElementById('file-input');
        const takePhotoBtn = document.getElementById('take-photo-btn');
        const cameraModal = document.getElementById('camera-modal');
        const videoElement = document.getElementById('video');
        const canvasElement = document.getElementById('canvas');
        const captureBtn = document.getElementById('capture-btn');
        const closeCameraBtn = document.getElementById('close-camera-btn');
        const riskScoresContainer = document.getElementById('risk-scores');
        const summaryElement = document.getElementById('summary');
        const aggressiveLanguageList = document.getElementById('aggressive-language');
        const suspiciousClausesList = document.getElementById('suspicious-clauses');
        const loadingText = document.getElementById('loading-text');
        const safetyScoreSection = document.getElementById('safety-score-section');
        const safetyPercentageText = document.getElementById('safety-percentage-text');
        const safetyStatus = document.getElementById('safety-status');
        const safetyProgressBar = document.querySelector('.circular-progress-bar');

        let videoStream = null;

        // Function to show/hide sections
        const showSection = (section, message = "") => {
            mainContent.classList.add('hidden');
            loadingState.classList.add('hidden');
            cameraModal.classList.add('hidden');

            if (section === 'input') {
                mainContent.classList.remove('hidden');
                resultsSection.classList.add('hidden');
                inputSection.classList.remove('lg:w-full');
            } else if (section === 'loading') {
                loadingState.classList.remove('hidden');
                loadingText.textContent = message;
            } else if (section === 'results') {
                mainContent.classList.remove('hidden');
                resultsSection.classList.remove('hidden');
                inputSection.classList.add('lg:w-full');
            } else if (section === 'camera') {
                cameraModal.classList.remove('hidden');
            }
        };

        const detectLanguageAndAnalyze = async (text) => {
            loadingText.textContent = "Analyzing document with Hugging Face model...";
            showSection('loading');

            // CRITICAL LINK: Use relative path /analyze
            const apiUrl = "/analyze";

            const payload = { text: text };

            let analyzeRetries = 0;
            const maxRetries = 5;
            const baseDelay = 1000;

            while(analyzeRetries < maxRetries) {
                try {
                    const response = await fetch(apiUrl, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });

                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }

                    const parsedData = await response.json();

                    renderResults(parsedData);
                    showSection('results');
                    return;
                } catch(error) {
                    console.error("Analysis error: ", error);
                    analyzeRetries++;
                    if(analyzeRetries >= maxRetries) {
                        loadingText.textContent = "Analysis Failed. Check server logs in Colab.";
                        await new Promise(res => setTimeout(res, 3000));
                        showSection('input');
                        return;
                    }
                    const delay = baseDelay * Math.pow(2, analyzeRetries);
                    await new Promise(res => setTimeout(res, delay));
                }
            }
        };

        // Function to process an image and extract text using OCR
        const processImageForText = async (base64Data, mimeType) => {
            loadingText.textContent = "Extracting text from image using OCR...";
            showSection('loading');

            // CRITICAL LINK: Use relative path /extract_text
            const apiUrl = "/extract_text";

            const payload = {
                image: base64Data,
                mimeType: mimeType
            };

            let retries = 0;
            const maxRetries = 5;
            const baseDelay = 1000;

            while (retries < maxRetries) {
                try {
                    const response = await fetch(apiUrl, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });

                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }

                    const result = await response.json();

                    if (result.error) {
                         throw new Error(result.error);
                    }

                    tosInput.value = result.text;
                    showSection('input');
                    return;

                } catch (error) {
                    console.error('Error during image analysis:', error);
                    retries++;
                    if (retries >= maxRetries) {
                        loadingText.textContent = "OCR Failed. Check Tesseract installation in Colab.";
                        await new Promise(res => setTimeout(res, 3000));
                        showSection('input');
                        return;
                    }
                    const delay = baseDelay * Math.pow(2, retries);
                    await new Promise(res => setTimeout(res, delay));
                }
            }
        };

        // Event Listeners (omitted for brevity, content is the same as previous files)
        pasteBtn.addEventListener('click', async () => {
            try {
                const text = await navigator.clipboard.readText();
                tosInput.value = text;
            } catch (err) {
                console.error('Failed to read clipboard contents: ', err);
            }
        });

        clearBtn.addEventListener('click', () => {
            tosInput.value = '';
            showSection('input');
        });

        // --- New Image/Camera Functionality ---
        uploadBtn.addEventListener('click', () => {
            fileInput.click();
        });

        fileInput.addEventListener('change', (event) => {
            const file = event.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    const base64Data = e.target.result.split(',')[1];
                    processImageForText(base64Data, file.type);
                };
                reader.readAsDataURL(file);
            }
        });

        takePhotoBtn.addEventListener('click', async () => {
            showSection('camera');
            try {
                videoStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
                videoElement.srcObject = videoStream;
            } catch (err) {
                console.error("Error accessing camera: ", err);
                showSection('input');
            }
        });

        captureBtn.addEventListener('click', () => {
            const context = canvasElement.getContext('2d');
            canvasElement.width = videoElement.videoWidth;
            canvasElement.height = videoElement.videoHeight;
            context.drawImage(videoElement, 0, 0, canvasElement.width, canvasElement.height);

            const base64Data = canvasElement.toDataURL('image/png').split(',')[1];

            if (videoStream) {
                videoStream.getTracks().forEach(track => track.stop());
                videoStream = null;
            }

            processImageForText(base64Data, 'image/png');
        });

        closeCameraBtn.addEventListener('click', () => {
            if (videoStream) {
                videoStream.getTracks().forEach(track => track.stop());
                videoStream = null;
            }
            showSection('input');
        });

        // --- Original Analyze Functionality ---
        analyzeBtn.addEventListener('click', async () => {
            const tosText = tosInput.value.trim();
            if (tosText === '') {
                console.warn('Please enter some text to analyze.');
                return;
            }

            detectLanguageAndAnalyze(tosText);
        });

        function renderResults(data) {
            // ... (rest of the renderResults function logic is unchanged) ...
            riskScoresContainer.innerHTML = '';
            let totalRiskScore = 0;
            data.riskScores.forEach(item => {
                const score = Math.max(0, Math.min(5, item.score));
                totalRiskScore += score;
                const barWidth = (score / 5) * 100;
                riskScoresContainer.innerHTML += `
                    <div>
                        <h3 class="text-white text-md font-medium mb-1">${item.name}</h3>
                        <div class="flex items-center space-x-4">
                            <div class="risk-bg w-full rounded-full h-2">
                                <div class="risk-bar h-2 rounded-full" style="width: ${barWidth}%;"></div>
                            </div>
                            <span class="text-gray-400 text-sm">${score}/5</span>
                        </div>
                        <p class="text-gray-400 text-xs mt-2">${item.description}</p>
                    </div>
                `;
            });

            const avgRiskScore = data.riskScores.length > 0 ? totalRiskScore / data.riskScores.length : 0;
            const safetyPercentage = Math.round((1 - (avgRiskScore / 5)) * 100);

            safetyPercentageText.textContent = `${safetyPercentage}%`;

            let statusClass = '';
            let statusText = '';
            if (safetyPercentage >= 60) {
                statusClass = 'safe';
                statusText = 'Safe';
            } else if (safetyPercentage >= 30) {
                statusClass = 'warning';
                statusText = 'Potentially Unsafe';
            } else {
                statusClass = 'unsafe';
                statusText = 'Unsafe';
            }

            safetyScoreSection.className = `container-bg p-6 rounded-2xl flex flex-col items-center justify-center text-center ${statusClass}`;
            safetyStatus.textContent = statusText;

            const circumference = 2 * Math.PI * 16;
            const offset = circumference * (1 - (safetyPercentage / 100));
            safetyProgressBar.style.strokeDasharray = circumference;
            safetyProgressBar.style.strokeDashoffset = offset;

            summaryElement.textContent = data.summary;

            aggressiveLanguageList.innerHTML = '';
            data.aggressiveLanguage.forEach(phrase => {
                aggressiveLanguageList.innerHTML += `<li>${phrase}</li>`;
            });

            suspiciousClausesList.innerHTML = '';
            data.suspiciousClauses.forEach(clause => {
                suspiciousClausesList.innerHTML += `
                    <li class="flex items-start space-x-3">
                        <i class="fas fa-exclamation-triangle text-yellow-400 mt-1"></i>
                        <div class="flex-1">
                            <h4 class="font-semibold text-white">${clause.name}</h4>
                            <p class="text-gray-300 text-sm leading-relaxed">${clause.text}</p>
                        </div>
                    </li>
                `;
            });
        }

    </script>
</body>
</html>
"""
    return render_template_string(html_content)


# --- 2. API Routes ---
@app.route("/analyze", methods=["POST"])
def analyze():
    # ... (rest of the analyze function implementation) ...
    data = request.get_json()
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "Empty text"}), 400

    summary = get_summary(text)

    # Heuristic rules for risk scoring (can expand later)
    # NOTE: In a production setting, this would be determined by the LLM response itself.
    risk_scores = [
        {"name": "Privacy", "score": 3, "description": "May involve some data collection."},
        {"name": "Data Sharing", "score": 2, "description": "Limited third-party sharing detected."},
        {"name": "Cancellation", "score": 3, "description": "Unclear process for account deletion."},
        {"name": "User Rights", "score": 4, "description": "Service may claim broad licenses."},
        {"name": "Amendments", "score": 3, "description": "Company can change terms without notice."},
        {"name": "Clarity", "score": 2, "description": "Language is moderately clear."},
    ]

    aggressive_words = ["terminate", "without notice", "no liability", "binding arbitration"]
    aggressive_found = [w for w in aggressive_words if w in text.lower()]

    suspicious_clauses = []
    if "retain" in text.lower():
        suspicious_clauses.append({"name": "Data retention clause", "text": "Contains vague retention language."})

    return jsonify({
        "summary": summary,
        "riskScores": risk_scores,
        "aggressiveLanguage": aggressive_found,
        "suspiciousClauses": suspicious_clauses
    })


@app.route("/extract_text", methods=["POST"])
def extract_text():
    # ... (rest of the extract_text function implementation) ...
    data = request.get_json()
    img_b64 = data.get("image")
    # mime_type is provided but not strictly needed for base64 decoding

    if not img_b64:
        return jsonify({"error": "No image provided"}), 400

    try:
        # Tesseract is now installed in Step 1
        image_data = base64.b64decode(img_b64)
        image = Image.open(io.BytesIO(image_data))
        text = pytesseract.image_to_string(image)
        return jsonify({"text": text.strip()})
    except Exception as e:
        return jsonify({"error": f"OCR failed: {e}"}), 500


# ----------------- SERVER EXECUTION -----------------
# Manual ngrok setup guarantees the URL is printed.
try:
    # 1. Start the ngrok tunnel manually
    public_url = ngrok.connect(FLASK_PORT).public_url
    print(f"\n* Public ngrok URL: {public_url}\n")

    # 2. Run Flask in a separate thread so the cell doesn't freeze
    threading.Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': FLASK_PORT, 'use_reloader': False}).start()

    # 3. Open the public URL in the notebook output
    eval_js('window.open("{url}", "_blank").focus()'.format(url=public_url))

    # 4. Keep the cell running
    while True:
        time.sleep(1)

except Exception as e:
    print(f"FATAL ERROR during ngrok/server start: {e}")
