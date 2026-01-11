// Global state
let currentLanguage = 'he';
let allResponsa = [];

// Pagination configuration
const ITEMS_PER_PAGE = 60;
let currentPage = 1;
let currentResponsa = [];

/**
 * Load the main dataset (responsa.json) with a progress bar and offload parsing
 * to a Web Worker when available. The default implementation simply calls
 * fetch() and JSON.parse(), but here we use XMLHttpRequest to monitor
 * download progress.
 */
function loadResponsaWithProgress() {
  const progressContainer = document.getElementById('progressContainer');
  const progressBar = document.getElementById('loadingProgress');
  // Display progress bar
  if (progressContainer) {
    progressContainer.style.display = 'block';
  }
  const xhr = new XMLHttpRequest();
  xhr.open('GET', 'responsa.json', true);
  xhr.responseType = 'text';
  xhr.onprogress = function (event) {
    if (event.lengthComputable && progressBar) {
      const percent = (event.loaded / event.total) * 100;
      progressBar.value = percent;
    }
  };
  xhr.onload = function () {
    if (progressContainer) {
      progressContainer.style.display = 'none';
    }
    if (xhr.status >= 200 && xhr.status < 300) {
      const responseText = xhr.responseText;
      // Use Web Worker to parse large JSON without blocking the main thread
      if (typeof Worker !== 'undefined') {
        try {
          const worker = new Worker('worker.js');
          worker.postMessage(responseText);
          worker.onmessage = function (e) {
            allResponsa = e.data;
            currentResponsa = allResponsa;
            populateYearFilter();
            currentPage = 1;
            displayResponsa(currentResponsa);
            updateStatistics();
            worker.terminate();
          };
          worker.onerror = function (err) {
            console.error('Worker error:', err);
            // Fallback to synchronous parse
            parseResponsaSync(responseText);
            worker.terminate();
          };
        } catch (ex) {
          // Worker construction can fail on some browsers; fallback
          console.warn('Web Worker failed to start, falling back to synchronous parse.');
          parseResponsaSync(responseText);
        }
      } else {
        // Workers not supported; parse synchronously
        parseResponsaSync(responseText);
      }
    } else {
      console.error('Failed to load responsa.json via XHR:', xhr.status);
      document.getElementById('emptyState').style.display = 'block';
    }
  };
  xhr.onerror = function () {
    if (progressContainer) {
      progressContainer.style.display = 'none';
    }
    console.error('Error loading responsa.json via XHR');
    document.getElementById('emptyState').style.display = 'block';
  };
  xhr.send();
}

// Parse JSON synchronously and update UI. Used when Web Workers are unavailable
function parseResponsaSync(responseText) {
  try {
    allResponsa = JSON.parse(responseText);
    currentResponsa = allResponsa;
    populateYearFilter();
    currentPage = 1;
    displayResponsa(currentResponsa);
    updateStatistics();
  } catch (e) {
    console.error('Error parsing responsa.json:', e);
    document.getElementById('emptyState').style.display = 'block';
  }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function () {
  // Use the progress-enabled loader instead of simple fetch
  loadResponsaWithProgress();
  updateLanguage();
});

// Helper to sanitize summary text for Mi Yodeya entries.
function sanitizeSummary(text, titleText) {
    if (!text) return '';
    const lines = String(text).split(/\r?\n/);
    const processedLines = [];
    for (let i = 0; i < lines.length; i++) {
        let line = lines[i].trim();
        if (line === '' || /^#+\s*/.test(line)) continue;
        let cutIndex = line.length;
        const idx2 = line.indexOf('##');
        if (idx2 !== -1 && idx2 < cutIndex) cutIndex = idx2;
        const idx3 = line.indexOf('###');
        if (idx3 !== -1 && idx3 < cutIndex) cutIndex = idx3;
        if (cutIndex < line.length) {
            line = line.substring(0, cutIndex).trim();
        }
        if (line === '') continue;
        processedLines.push(line);
    }
    if (processedLines.length === 0) return '';
    let summary = processedLines[0];
    if (titleText) {
        const titleNorm = String(titleText).trim().toLowerCase();
        const summaryNorm = summary.toLowerCase();
        if (summaryNorm === titleNorm || summaryNorm.startsWith(titleNorm)) {
            summary = processedLines.length > 1 ? processedLines[1] : '';
        }
    }
    return summary;
}

// Populate year filter
function populateYearFilter() {
    const yearFilter = document.getElementById('yearFilter');
    // Remove any dynamically added options to avoid duplication
    // Keep the first "all" option
    while (yearFilter.options.length > 1) {
      yearFilter.remove(1);
    }
    const years = [...new Set(allResponsa.map(r => r.year))].sort((a, b) => b - a);
    years.forEach(year => {
        const option = document.createElement('option');
        option.value = year;
        option.textContent = year;
        yearFilter.appendChild(option);
    });
}

// Display responsa cards (unchanged from original)
function displayResponsa(responsa) {
    const grid = document.getElementById('responsaGrid');
    const emptyState = document.getElementById('emptyState');
    grid.innerHTML = '';
    if (responsa.length === 0) {
        grid.style.display = 'none';
        emptyState.style.display = 'block';
        const paginationContainer = document.getElementById('paginationControls');
        if (paginationContainer) {
            paginationContainer.style.display = 'none';
        }
        return;
    }
    grid.style.display = 'grid';
    emptyState.style.display = 'none';
    const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
    const endIndex = startIndex + ITEMS_PER_PAGE;
    const pageItems = responsa.slice(startIndex, endIndex);
    pageItems.forEach(item => {
        const card = createResponsaCard(item);
        grid.appendChild(card);
    });
    renderPaginationControls(responsa.length);
}

// Create individual responsa card (unchanged)
function createResponsaCard(item) {
    const card = document.createElement('div');
    card.className = 'responsa-card';
    card.onclick = () => window.open(item.file, '_blank');
    const titleText = currentLanguage === 'he' ? item.title_he : item.title_en;
    const rawSummary = currentLanguage === 'he' ? item.summary_he : item.summary_en;
    let summaryText = sanitizeSummary(rawSummary, titleText);
    if (!summaryText) {
        summaryText = rawSummary || '';
    }
    const categoryText = currentLanguage === 'he' ? item.category_he : item.category_en;
    const readMoreText = currentLanguage === 'he' ? 'קרא עוד ←' : 'Read More →';
    const fileIcon = item.type === 'pdf' ? '📄' : '📝';
    const fileTypeLabel = item.type === 'pdf' ? 'PDF' : 'HTML';
    card.innerHTML = `
        <div class="card-header">
            <span class="card-number">#${item.number}</span>
            <h3 class="card-title">${titleText}</h3>
            <div class="card-meta">
                <span>📅 ${item.date}</span>
                <span>📖 ${item.year}</span>
                <span>${fileIcon} ${fileTypeLabel}</span>
            </div>
        </div>
        <div class="card-body">
            <p class="card-summary">${summaryText}</p>
            <span class="card-category">${categoryText}</span>
        </div>
        <div class="card-footer">
            <a href="${item.file}" class="card-link" onclick="event.stopPropagation()">${readMoreText}</a>
        </div>
    `;
    return card;
}

// Search functionality
function searchResponsa() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const categoryFilter = document.getElementById('categoryFilter').value;
    const yearFilter = document.getElementById('yearFilter').value;
    let filtered = allResponsa;
    if (searchTerm) {
        filtered = filtered.filter(item =>
            item.title_he.toLowerCase().includes(searchTerm) ||
            item.title_en.toLowerCase().includes(searchTerm) ||
            item.summary_he.toLowerCase().includes(searchTerm) ||
            item.summary_en.toLowerCase().includes(searchTerm) ||
            item.number.toString().includes(searchTerm)
        );
    }
    if (categoryFilter !== 'all') {
        filtered = filtered.filter(item => item.category === categoryFilter);
    }
    if (yearFilter !== 'all') {
        filtered = filtered.filter(item => item.year.toString() === yearFilter);
    }
    currentResponsa = filtered;
    currentPage = 1;
    displayResponsa(currentResponsa);
}

// Filter by category or year (delegates to search)
function filterResponsa() {
    searchResponsa();
}

// Toggle language and update UI
function toggleLanguage() {
    currentLanguage = currentLanguage === 'he' ? 'en' : 'he';
    document.documentElement.lang = currentLanguage;
    document.body.dir = currentLanguage === 'he' ? 'rtl' : 'ltr';
    updateLanguage();
    currentResponsa = getFilteredResponsa();
    displayResponsa(currentResponsa);
}

// Update language-dependent elements
function updateLanguage() {
    const selects = document.querySelectorAll('select option');
    selects.forEach(option => {
        const text = currentLanguage === 'he' ? option.dataset.he : option.dataset.en;
        if (text) option.textContent = text;
    });
    const searchInput = document.getElementById('searchInput');
    searchInput.placeholder = currentLanguage === 'he' ? 'חיפוש...' : 'Search...';
}

// Get currently filtered responsa; used when toggling language
function getFilteredResponsa() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const categoryFilter = document.getElementById('categoryFilter').value;
    const yearFilter = document.getElementById('yearFilter').value;
    let filtered = allResponsa;
    if (searchTerm) {
        filtered = filtered.filter(item =>
            item.title_he.toLowerCase().includes(searchTerm) ||
            item.title_en.toLowerCase().includes(searchTerm) ||
            item.summary_he.toLowerCase().includes(searchTerm) ||
            item.summary_en.toLowerCase().includes(searchTerm)
        );
    }
    if (categoryFilter !== 'all') {
        filtered = filtered.filter(item => item.category === categoryFilter);
    }
    if (yearFilter !== 'all') {
        filtered = filtered.filter(item => item.year.toString() === yearFilter);
    }
    return filtered;
}

// Update statistics based on the full dataset
function updateStatistics() {
    document.getElementById('totalResponsa').textContent = allResponsa.length;
    if (allResponsa.length > 0) {
        const years = allResponsa.map(r => r.year);
        const latestYear = Math.max(...years);
        document.getElementById('latestYear').textContent = latestYear;
    }
}

/**
 * Render pagination controls below the responsa grid. This function creates
 * Previous/Next buttons and a page indicator based on the total number of
 * items. Buttons are disabled when on the first or last page. The labels
 * adjust to the current language.
 *
 * @param {number} totalItems - Total number of items in the current filtered list.
 */
function renderPaginationControls(totalItems) {
    let paginationContainer = document.getElementById('paginationControls');
    if (!paginationContainer) {
        paginationContainer = document.createElement('div');
        paginationContainer.id = 'paginationControls';
        paginationContainer.className = 'pagination-controls';
        const gridParent = document.getElementById('responsaGrid').parentNode;
        gridParent.appendChild(paginationContainer);
    }
    paginationContainer.innerHTML = '';
    const totalPages = Math.ceil(totalItems / ITEMS_PER_PAGE);
    if (totalPages <= 1) {
        paginationContainer.style.display = 'none';
        return;
    }
    paginationContainer.style.display = 'flex';
    const prevLabel = currentLanguage === 'he' ? 'הקודם' : 'Previous';
    const nextLabel = currentLanguage === 'he' ? 'הבא' : 'Next';
    const prevButton = document.createElement('button');
    prevButton.textContent = prevLabel;
    prevButton.disabled = currentPage === 1;
    prevButton.onclick = function (event) {
        event.preventDefault();
        if (currentPage > 1) {
            changePage(currentPage - 1);
        }
    };
    paginationContainer.appendChild(prevButton);
    const pageIndicator = document.createElement('span');
    pageIndicator.textContent = `${currentPage} / ${totalPages}`;
    pageIndicator.className = 'page-indicator';
    pageIndicator.style.margin = '0 1rem';
    paginationContainer.appendChild(pageIndicator);
    const nextButton = document.createElement('button');
    nextButton.textContent = nextLabel;
    nextButton.disabled = currentPage === totalPages;
    nextButton.onclick = function (event) {
        event.preventDefault();
        if (currentPage < totalPages) {
            changePage(currentPage + 1);
        }
    };
    paginationContainer.appendChild(nextButton);
}

// Change the current page and re-render the responsa grid
function changePage(page) {
    const totalPages = Math.ceil(currentResponsa.length / ITEMS_PER_PAGE);
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    displayResponsa(currentResponsa);
}