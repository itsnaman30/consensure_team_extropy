# ConsenSure: The Digital Textbook
# 📜 TOS & Regulations Analyzer

This project is a **Flask + Hugging Face + OCR (Tesseract)** application that lets you analyze Terms of Service (TOS) or regulations. It provides:

* ✅ **Extractive + Abstractive Summaries** using `sumy` and Hugging Face models
* ⚖️ **Risk Score Analysis** for different categories (privacy, user rights, etc.)
* 🔍 **Aggressive Language & Suspicious Clause Detection**
* 📷 **OCR from Uploaded Images or Camera Capture** (via Tesseract)
* 🌐 **Live Web UI** served via **ngrok tunnel** in Google Colab

---

## 🚀 Getting Started

You can run this project directly on **Google Colab** without needing to configure your local machine.

### 1. Open Google Colab

* Visit [Google Colab](https://colab.research.google.com/)
* Create a **new Python notebook**

---

### 2. Install Dependencies

In your first Colab cell, install required libraries:

```bash
!pip install flask pyngrok google-colab nltk sumy transformers pillow pytesseract
```

Additionally, install **Tesseract OCR**:

```bash
!apt-get install -y tesseract-ocr
```

---

### 3. Add Your ngrok Token

* Go to [ngrok](https://dashboard.ngrok.com/get-started/your-authtoken) and copy your **auth token**
* In Colab:

  * Open the **🔑 "Secrets" sidebar** (`Colab > Tools > User secrets`)
  * Add a new secret:

    * Key → `NGROK_AUTH_TOKEN`
    * Value → *your token*

This is required so that ngrok can generate a secure public URL.

---

### 4. Upload the Project Code

* Copy the provided `app.py` (Flask app code from this repo) into a Colab cell and run it.
* The script will:

  1. Authenticate ngrok using your token
  2. Start the Flask app on port `5000`
  3. Expose a **public ngrok URL**
  4. Automatically open the app in a new browser tab

---

### 5. Using the App

Once the app loads in your browser:

1. **Paste TOS text** into the textarea or
2. **Upload a photo** (screenshot of TOS) or
3. **Take a photo** with your camera (works in supported browsers)

Then click **Analyze**.
The app will show:

* Summary of the text
* Risk scores across multiple categories
* Aggressive phrases detected
* Suspicious clauses
* An **Overall Safety Score** (circular progress bar)

---

## 🛠 Troubleshooting

* ❌ *"FATAL ERROR: NGROK_AUTH_TOKEN secret not found"* → Make sure you added your ngrok token in Colab’s secret storage.
* ❌ *OCR failed* → Ensure Tesseract is installed (`!apt-get install -y tesseract-ocr`).
* ❌ *Model failed to load* → Check your internet connection (Hugging Face model is downloaded on first run).

---

## 📌 Notes

* This is a **prototype**, risk scoring is **heuristic-based**. For production, consider replacing it with fine-tuned LLM evaluations.
* Hugging Face model used: `ml6team/distilbart-tos-summarizer-tosdr`
* Colab free tier may disconnect; if it does, simply re-run the setup cells.

---

## 📖 License

This project is for **educational and research purposes only**. Use responsibly.

---

