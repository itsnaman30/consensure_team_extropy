// Helper function to convert base64 to an ArrayBuffer
function base64ToArrayBuffer(base64) {
    var binary_string = window.atob(base64);
    var len = binary_string.length;
    var bytes = new Uint8Array(len);
    for (var i = 0; i < len; i++) {
        bytes[i] = binary_string.charCodeAt(i);
    }
    return bytes.buffer;
}

// Helper function to convert PCM audio data to WAV format
function pcmToWav(pcm16, sampleRate) {
    const numChannels = 1;
    const bytesPerSample = 2; // 16-bit PCM
    const blockAlign = numChannels * bytesPerSample;
    const byteRate = sampleRate * blockAlign;
    const dataSize = pcm16.byteLength;
    const buffer = new ArrayBuffer(44 + dataSize);
    const view = new DataView(buffer);

    // Write the WAV file header
    let offset = 0;
    // "RIFF" chunk descriptor
    view.setUint32(offset, 0x52494646, false); offset += 4;
    // File size (44 bytes for header + data size)
    view.setUint32(offset, 36 + dataSize, true); offset += 4;
    // "WAVE" format
    view.setUint32(offset, 0x57415645, false); offset += 4;
    // "fmt " sub-chunk
    view.setUint32(offset, 0x666d7420, false); offset += 4;
    // Sub-chunk size (16 for PCM)
    view.setUint32(offset, 16, true); offset += 4;
    // Audio format (1 for PCM)
    view.setUint16(offset, 1, true); offset += 2;
    // Number of channels
    view.setUint16(offset, numChannels, true); offset += 2;
    // Sample rate
    view.setUint32(offset, sampleRate, true); offset += 4;
    // Byte rate
    view.setUint32(offset, byteRate, true); offset += 4;
    // Block align
    view.setUint16(offset, blockAlign, true); offset += 2;
    // Bits per sample
    view.setUint16(offset, 16, true); offset += 2;
    // "data" sub-chunk
    view.setUint32(offset, 0x64617461, false); offset += 4;
    // Data size
    view.setUint32(offset, dataSize, true); offset += 4;

    // Write the PCM audio data
    const pcmArray = new Int16Array(buffer, offset);
    pcmArray.set(pcm16);

    return new Blob([buffer], { type: 'audio/wav' });
}

// DOM Elements
const tosInput = document.getElementById('tos-input');
const imageUpload = document.getElementById('image-upload');
const simplifyBtn = document.getElementById('simplify-btn');
const audioBtn = document.getElementById('audio-btn');
const languageSelect = document.getElementById('language-select');
const simplifiedOutput = document.getElementById('simplified-output');
const displayImage = document.getElementById('display-image');
const audioPlayer = document.getElementById('audio-player');
const audioBtnText = document.getElementById('audio-btn-text');
const loadingSpinner = document.getElementById('loading-spinner');

// State variables for the app
let lastSimplifiedText = '';
let lastLanguage = '';

// Core function to make text shorter and more user-friendly
function mockSimplifyText(text) {
    let simplifiedText = text;
    
    // Rule 1: Condense opening legal boilerplate
    simplifiedText = simplifiedText.replace(/Welcome to Connectify\. By accessing or using our services, you agree to be bound by these Terms of Service \("Terms"\)\. These Terms constitute a legally binding agreement between you and Connectify, Inc\. If you do not agree to these Terms, you may not access or use the services\./, 'By using our app, you agree to follow these rules.');
    
    // Rule 2: Simplify content and license clauses
    simplifiedText = simplifiedText.replace(/You retain ownership of any intellectual property rights that you hold in the content you submit, post, or display on or through the services\. However, by submitting content, you grant Connectify a worldwide, non-exclusive, royalty-free license to use, reproduce, adapt, publish, and distribute such content on behalf of the service\./, 'You own what you post, but you give us a license to use it.');
    
    // Rule 3: Simplify the "as-is" disclaimer
    simplifiedText = simplifiedText.replace(/The services are provided on an "as-is" and "as-available" basis without any warranties of any kind, either express or implied, including, but not limited to, implied warranties of merchantability, fitness for a particular purpose, or non-infringement\. We do not warrant that the services will be uninterrupted, secure, or free from errors\./, 'Our app comes with no guarantees. It might have bugs or stop working.');

    // Rule 4: Simplify a user's responsibility
    simplifiedText = simplifiedText.replace(/You represent and warrant that you have all the rights, power, and authority necessary to grant the rights granted herein to any content you submit\./, 'You promise you have the right to post any content you share.');

    // Final shorteners for clarity
    simplifiedText = simplifiedText.replace(/We reserve the right, at our sole discretion, to modify or replace these Terms at any time\./, 'We can change these rules at any time.');
    simplifiedText = simplifiedText.replace(/Your continued use of the services after any such changes constitutes your acceptance of the new Terms\./, 'By continuing to use our app, you agree to any new rules.');
    simplifiedText = simplifiedText.replace(/Your use of the services is at your sole risk\./, 'You use the app at your own risk.');

    // Add red color to the most critical parts
    simplifiedText = simplifiedText.replace('By using our app, you agree to follow these rules.', '<span class="text-red-500">By using our app, you agree to follow these rules.</span>');
    simplifiedText = simplifiedText.replace('but you give us a license to use it.', 'but you <span class="text-red-500">give us a license to use it</span>.');
    simplifiedText = simplifiedText.replace('Our app comes with no guarantees.', '<span class="text-red-500">Our app comes with no guarantees.</span>');
    simplifiedText = simplifiedText.replace('We can change these rules at any time.', '<span class="text-red-500">We can change these rules at any time.</span>');
    simplifiedText = simplifiedText.replace('You use the app at your own risk.', '<span class="text-red-500">You use the app at your own risk.</span>');
    
    return simplifiedText.trim();
}

// Function to simplify text and display it section by section
simplifyBtn.addEventListener('click', async () => {
    const tosText = tosInput.value;
    const selectedLanguage = languageSelect.value;

    if (!tosText) {
        simplifiedOutput.innerHTML = `<p class="text-center text-red-500 italic">Please paste some text to simplify.</p>`;
        return;
    }

    simplifiedOutput.innerHTML = ''; // Clear previous output
    simplifyBtn.disabled = true;
    simplifyBtn.classList.add('opacity-50', 'cursor-not-allowed');

    // Split the text into sections based on double newlines
    const sections = tosText.split(/\n\n+/).filter(section => section.trim() !== '');
    let allSimplifiedText = '';

    for (let i = 0; i < sections.length; i++) {
        const section = sections[i];
        
        // Create a new card for each section
        const sectionCard = document.createElement('div');
        sectionCard.className = 'bg-white rounded-lg p-4 shadow-md mb-4 border border-gray-200';
        sectionCard.innerHTML = `<h3 class="font-bold text-lg text-gray-800">Section ${i + 1}</h3>`;
        simplifiedOutput.appendChild(sectionCard);

        // Simulate a delay for a more realistic user experience
        await new Promise(resolve => setTimeout(resolve, 500));

        // Use the mock function to get a simplified version
        const simplifiedSectionText = mockSimplifyText(section);
        
        sectionCard.innerHTML += `<p class="mt-2 text-gray-700">${simplifiedSectionText}</p>`;
        allSimplifiedText += ' ' + simplifiedSectionText;
    }
    
    lastSimplifiedText = allSimplifiedText.trim();
    lastLanguage = selectedLanguage;
    simplifyBtn.disabled = false;
    simplifyBtn.classList.remove('opacity-50', 'cursor-not-allowed');

    if (sections.length > 0) {
        simplifiedOutput.prepend(document.createElement('hr'));
        simplifiedOutput.prepend(document.createElement('hr'));
        simplifiedOutput.prepend(document.createElement('br'));
        const summaryHeader = document.createElement('h3');
        summaryHeader.className = 'font-bold text-lg mb-2 text-gray-800';
        summaryHeader.textContent = 'Simplified Summary:';
        simplifiedOutput.prepend(summaryHeader);
    }
});

// Function to handle image upload
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

// Function to generate and play audio
audioBtn.addEventListener('click', async () => {
    if (!lastSimplifiedText) {
        simplifiedOutput.innerHTML = `<p class="text-center text-red-500 italic">Please simplify some text first to generate audio.</p>`;
        return;
    }

    // This is a mocked audio response to ensure the button works.
    audioBtnText.classList.add('hidden');
    loadingSpinner.classList.remove('hidden');
    audioBtn.disabled = true;

    // Simulate an audio generation process
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    audioBtnText.classList.remove('hidden');
    loadingSpinner.classList.add('hidden');
    audioBtn.disabled = false;

    audioPlayer.classList.add('hidden');
    simplifiedOutput.innerHTML += `<p class="mt-4 text-center text-green-500 font-bold">Audio playback is not available in this demo. For a full version, please ensure your API key is correctly configured.</p>`;
});
