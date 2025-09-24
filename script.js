const analyzeBtn = document.getElementById('analyze-btn');
const tosInput = document.getElementById('tos-input');
const simplifiedOutput = document.getElementById('simplified-output');
const analyzeBtnText = document.getElementById('analyze-btn-text');
const loadingSpinner = document.getElementById('loading-spinner');
const languageSelect = document.getElementById('language-select');
const imageUpload = document.getElementById('image-upload');
const displayImage = document.getElementById('display-image');

// Function to handle image upload preview
imageUpload.addEventListener('change', (event) => {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            displayImage.src = e.target.result;
            displayImage.classList.remove('hidden');
        };
        reader.readAsDataURL(file);
    }
});

analyzeBtn.addEventListener('click', async () => {
    const tosText = tosInput.value;
    const imageFile = imageUpload.files[0];
    const selectedLanguage = languageSelect.value;

    if (!tosText && !imageFile) {
        simplifiedOutput.innerHTML = `<p class="text-center text-red-500 italic">Please paste some text or upload an image to analyze.</p>`;
        return;
    }

    simplifiedOutput.innerHTML = '';
    analyzeBtn.disabled = true;
    analyzeBtnText.classList.add('hidden');
    loadingSpinner.classList.remove('hidden');

    try {
        const apiKey = "AIzaSyC3gSI8BfjPdWyDt_ueq1lwXJsurfezu_0";
        const apiUrl = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key=${apiKey}`;

        let payload;
        if (tosText) {
            // Case 1: Text input
            const userQuery = `Summarize the following Terms of Service text into a single, easy-to-read paragraph. Avoid special characters and bullet points. The summary should be in ${selectedLanguage}.
            
            Text:
            ${tosText}`;
            payload = {
                contents: [{ parts: [{ text: userQuery }] }],
                systemInstruction: {
                    parts: [{ text: "You are a helpful assistant that summarizes legal documents and translates them into simple, user-friendly language." }]
                },
            };
        } else if (imageFile) {
            // Case 2: Image input
            const userQuery = `Summarize the text found in this image. The summary should be concise and easy to understand for a general user and should be in ${selectedLanguage}.`;
            const base64Data = await new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onloadend = () => resolve(reader.result.split(',')[1]);
                reader.onerror = reject;
                reader.readAsDataURL(imageFile);
            });

            payload = {
                contents: [{
                    parts: [
                        { text: userQuery },
                        { inlineData: { mimeType: imageFile.type, data: base64Data } }
                    ]
                }],
                systemInstruction: {
                    parts: [{ text: "You are a helpful assistant that summarizes legal documents from images and translates them into simple, user-friendly language." }]
                },
            };
        }

        const response = await fetch(apiUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(`API call failed with status: ${response.status}, message: ${JSON.stringify(errorData)}`);
        }

        const result = await response.json();
        const candidate = result.candidates?.[0];
        const generatedText = candidate?.content?.parts?.[0]?.text;

        if (generatedText) {
            simplifiedOutput.innerHTML = `<div class="p-4 bg-white rounded-lg shadow-inner border border-gray-300">
                <p class="text-gray-800 leading-relaxed whitespace-pre-wrap">${generatedText}</p>
            </div>`;
        } else {
            simplifiedOutput.innerHTML = `<p class="text-center text-red-500 italic">Could not generate a summary. Please try again.</p>`;
        }

    } catch (error) {
        console.error("Error calling the API:", error);
        simplifiedOutput.innerHTML = `<p class="text-center text-red-500 italic">An error occurred: ${error.message}. Please check the console for more details.</p>`;
    } finally {
        analyzeBtn.disabled = false;
        analyzeBtnText.classList.remove('hidden');
        loadingSpinner.classList.add('hidden');
    }
});
