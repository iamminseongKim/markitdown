document.addEventListener('DOMContentLoaded', () => {
    // Initialize Lucide Icons
    lucide.createIcons();

    // DOM Elements
    const useGeminiCheckbox = document.getElementById('use-gemini');
    const geminiKeyWrapper = document.getElementById('gemini-key-wrapper');
    const geminiApiKeyInput = document.getElementById('gemini-api-key');
    const toggleKeyVisibilityBtn = document.getElementById('toggle-key-visibility');
    const eyeIcon = document.getElementById('eye-icon');
    
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const fileInfoCard = document.getElementById('file-info-card');
    const selectedFileName = document.getElementById('selected-file-name');
    const selectedFileSize = document.getElementById('selected-file-size');
    const cancelUploadBtn = document.getElementById('cancel-upload');
    const convertBtn = document.getElementById('convert-btn');

    const loadingPanel = document.getElementById('loading-panel');
    const loadingStatus = document.getElementById('loading-status');
    const resultPanel = document.getElementById('result-panel');
    const resetBtn = document.getElementById('reset-btn');

    // Metrics
    const metricTime = document.getElementById('metric-time');
    const metricChars = document.getElementById('metric-chars');
    const metricWords = document.getElementById('metric-words');
    const metricSize = document.getElementById('metric-size');

    // Tabs
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');
    const copyBtn = document.getElementById('copy-btn');
    const downloadBtn = document.getElementById('download-btn');
    const previewContainer = document.getElementById('preview-container');
    const rawMarkdownTextarea = document.getElementById('raw-markdown-textarea');

    // Toast
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toast-message');

    // State Variables
    let currentFile = null;
    let convertedMarkdown = '';
    let originalFileName = '';

    // --- Gemini Configuration Setup ---
    
    // Load saved API Key on load
    const savedKey = localStorage.getItem('gemini_api_key');
    if (savedKey) {
        geminiApiKeyInput.value = savedKey;
    }

    // Toggle key wrapper visibility based on checkbox
    useGeminiCheckbox.addEventListener('change', () => {
        if (useGeminiCheckbox.checked) {
            geminiKeyWrapper.classList.remove('hidden');
        } else {
            geminiKeyWrapper.classList.add('hidden');
        }
    });

    // Save API key when user inputs it
    geminiApiKeyInput.addEventListener('input', () => {
        localStorage.setItem('gemini_api_key', geminiApiKeyInput.value.trim());
    });

    // Toggle API Key visibility
    toggleKeyVisibilityBtn.addEventListener('click', () => {
        if (geminiApiKeyInput.type === 'password') {
            geminiApiKeyInput.type = 'text';
            eyeIcon.setAttribute('data-lucide', 'eye-off');
        } else {
            geminiApiKeyInput.type = 'password';
            eyeIcon.setAttribute('data-lucide', 'eye');
        }
        lucide.createIcons(); // Refresh the icon
    });

    // --- Drag and Drop File Handlers ---

    // Prevent default behaviors for drag events
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    // Add/remove dragover styling class
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.add('dragover'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.remove('dragover'), false);
    });

    // Handle dropped files
    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            handleFileSelection(files[0]);
        }
    });

    // Handle file input selection click
    fileInput.addEventListener('change', (e) => {
        if (fileInput.files.length > 0) {
            handleFileSelection(fileInput.files[0]);
        }
    });

    // Format file size helper
    function formatBytes(bytes, decimals = 2) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }

    // Process selected file
    function handleFileSelection(file) {
        currentFile = file;
        originalFileName = file.name;
        selectedFileName.textContent = file.name;
        selectedFileSize.textContent = formatBytes(file.size);
        
        dropZone.parentNode.classList.add('hidden'); // Hide the dropzone card wrapper
        fileInfoCard.classList.remove('hidden');    // Show the selected file info card
    }

    // Cancel selection
    cancelUploadBtn.addEventListener('click', () => {
        resetWorkspace();
    });

    // --- File Conversion Execution ---

    convertBtn.addEventListener('click', async () => {
        if (!currentFile) return;

        const useLLM = useGeminiCheckbox.checked;
        const apiKey = geminiApiKeyInput.value.trim();

        if (useLLM && !apiKey) {
            alert('Gemini API를 사용하려면 API Key를 입력하셔야 합니다.');
            geminiApiKeyInput.focus();
            return;
        }

        // Show loading state
        fileInfoCard.classList.add('hidden');
        loadingPanel.classList.remove('hidden');

        // Dynamic status text intervals
        let statusIdx = 0;
        const statusMessages = [
            '파일 전송 중...',
            '문서 구조 분석 중...',
            '마크다운 변환 엔진 구동 중...',
            '텍스트 데이터 추출 및 변환 중...',
            '레이아웃 복원 작업 중...'
        ];
        
        if (useLLM) {
            statusMessages.splice(2, 0, '구글 Gemini AI 분석 진행 중 (OCR 및 설명 생성)...');
        }

        const statusInterval = setInterval(() => {
            statusIdx = (statusIdx + 1) % statusMessages.length;
            loadingStatus.textContent = statusMessages[statusIdx];
        }, 3000);

        // Build request payload
        const formData = new FormData();
        formData.append('file', currentFile);
        formData.append('use_llm', useLLM);
        if (useLLM) {
            formData.append('gemini_api_key', apiKey);
        }

        try {
            const response = await fetch('/api/convert', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || '변환 과정에서 예상치 못한 오류가 발생했습니다.');
            }

            // Success: populate metrics and results
            metricTime.textContent = `${data.conversion_time_seconds}초`;
            metricChars.textContent = Number(data.character_count).toLocaleString();
            metricWords.textContent = Number(data.word_count).toLocaleString();
            metricSize.textContent = formatBytes(data.size_bytes);

            convertedMarkdown = data.markdown;
            
            // Populate Raw Markdown View
            rawMarkdownTextarea.value = convertedMarkdown;

            // Populate Rendered Preview View
            if (typeof marked !== 'undefined') {
                previewContainer.innerHTML = marked.parse(convertedMarkdown);
            } else {
                previewContainer.innerHTML = `<pre>${escapeHTML(convertedMarkdown)}</pre>`;
            }

            // Show results
            loadingPanel.classList.add('hidden');
            resultPanel.classList.remove('hidden');

        } catch (error) {
            console.error(error);
            alert(`오류 발생: ${error.message}`);
            loadingPanel.classList.add('hidden');
            fileInfoCard.classList.remove('hidden');
        } finally {
            clearInterval(statusInterval);
        }
    });

    // Reset workspace function
    function resetWorkspace() {
        currentFile = null;
        convertedMarkdown = '';
        originalFileName = '';
        fileInput.value = '';
        rawMarkdownTextarea.value = '';
        previewContainer.innerHTML = '';
        
        dropZone.parentNode.classList.remove('hidden');
        fileInfoCard.classList.add('hidden');
        loadingPanel.classList.add('hidden');
        resultPanel.classList.add('hidden');
        
        // Reset loading status default text
        loadingStatus.textContent = '파일 전송 중...';
    }

    resetBtn.addEventListener('click', resetWorkspace);

    // Escape HTML helper
    function escapeHTML(str) {
        return str.replace(/[&<>'"]/g, 
            tag => ({
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                "'": '&#39;',
                '"': '&quot;'
            }[tag] || tag)
        );
    }

    // --- Tab Functionality ---

    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');

            // Toggle active buttons
            tabButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Toggle active panes
            tabPanes.forEach(pane => {
                if (pane.id === `tab-${targetTab}`) {
                    pane.classList.add('active');
                } else {
                    pane.classList.remove('active');
                }
            });
        });
    });

    // --- Copy and Download Actions ---

    // Clipboard Copy
    copyBtn.addEventListener('click', async () => {
        if (!convertedMarkdown) return;
        try {
            await navigator.clipboard.writeText(convertedMarkdown);
            showToast('클립보드에 성공적으로 복사되었습니다!');
        } catch (err) {
            console.error('Copy failed: ', err);
            // Fallback for older browsers
            rawMarkdownTextarea.select();
            document.execCommand('copy');
            showToast('클립보드에 복사되었습니다.');
        }
    });

    // File Download
    downloadBtn.addEventListener('click', () => {
        if (!convertedMarkdown) return;

        // Generate markdown filename
        let downloadName = 'converted.md';
        if (originalFileName) {
            const pos = originalFileName.lastIndexOf('.');
            const baseName = pos > 0 ? originalFileName.substring(0, pos) : originalFileName;
            downloadName = `${baseName}.md`;
        }

        const blob = new Blob([convertedMarkdown], { type: 'text/markdown;charset=utf-8;' });
        const link = document.createElement('a');
        
        if (navigator.msSaveBlob) { // IE 10+
            navigator.msSaveBlob(blob, downloadName);
        } else {
            const url = URL.createObjectURL(blob);
            link.href = url;
            link.setAttribute('download', downloadName);
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
        }
    });

    // Toast Utility
    function showToast(message) {
        toastMessage.textContent = message;
        toast.classList.remove('hidden');
        
        // Hide after 3 seconds
        setTimeout(() => {
            toast.classList.add('hidden');
        }, 3000);
    }
});
