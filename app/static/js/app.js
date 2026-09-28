/**
 * PDF Merger Pro - Gerenciamento de Upload, Reordenação e Menu de Documentos
 */

(function () {
  'use strict';

  // Estado da Aplicação
  const state = {
    sessionId: null,
    files: [], // Array de { id, name, menuTitle, size, pageCount, fileObj, isUploaded, serverSavedName }
    isProcessing: false,
    downloadUrl: null,
    previewUrl: null,
    outputFilename: 'documento_unificado.pdf',
  };

  // Elementos do DOM
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('file-input');
  const filesStage = document.getElementById('files-stage');
  const fileList = document.getElementById('file-list');
  const filesCounter = document.getElementById('files-counter');
  const totalSizeLabel = document.getElementById('total-size-label');
  const btnAddMore = document.getElementById('btn-add-more');
  const btnClearAll = document.getElementById('btn-clear-all');
  const btnStartMerge = document.getElementById('btn-start-merge');

  const outputFilenameInput = document.getElementById('output-filename');
  const toggleVisualMenu = document.getElementById('toggle-visual-menu');
  const toggleBookmarks = document.getElementById('toggle-bookmarks');
  const toggleLinearize = document.getElementById('toggle-linearize');

  const processingStage = document.getElementById('processing-stage');
  const processingTitle = document.getElementById('processing-status-title');
  const processingDesc = document.getElementById('processing-status-desc');
  const progressFill = document.getElementById('progress-fill');
  const progressPct = document.getElementById('progress-pct');

  const resultStage = document.getElementById('result-stage');
  const resultFilenameDisplay = document.getElementById('result-filename-display');
  const metricFiles = document.getElementById('metric-files');
  const metricPages = document.getElementById('metric-pages');
  const metricSize = document.getElementById('metric-size');
  const metricTime = document.getElementById('metric-time');
  const btnDownload = document.getElementById('btn-download');
  const btnPreview = document.getElementById('btn-preview');
  const btnReset = document.getElementById('btn-reset');

  const previewModal = document.getElementById('preview-modal');
  const btnCloseModal = document.getElementById('btn-close-modal');
  const pdfViewerFrame = document.getElementById('pdf-viewer-frame');
  const modalFilename = document.getElementById('modal-filename');
  const modalBtnDownload = document.getElementById('modal-btn-download');
  const toastContainer = document.getElementById('toast-container');

  // Inicialização
  init();

  function init() {
    setupEventListeners();
    generateSessionId();
  }

  function generateSessionId() {
    state.sessionId = 'sess_' + Math.random().toString(36).substring(2, 11) + '_' + Date.now();
  }

  function setupEventListeners() {
    dropzone.addEventListener('click', () => fileInput.click());
    btnAddMore.addEventListener('click', () => fileInput.click());

    ['dragenter', 'dragover'].forEach(eventName => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.add('dragover');
      });
    });

    ['dragleave', 'drop'].forEach(eventName => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove('dragover');
      });
    });

    dropzone.addEventListener('drop', (e) => {
      const droppedFiles = e.dataTransfer.files;
      if (droppedFiles.length > 0) {
        handleFilesAdded(droppedFiles);
      }
    });

    fileInput.addEventListener('change', (e) => {
      if (e.target.files.length > 0) {
        handleFilesAdded(e.target.files);
        fileInput.value = '';
      }
    });

    btnClearAll.addEventListener('click', () => {
      if (confirm('Deseja realmente remover todos os arquivos selecionados?')) {
        resetApp(false);
      }
    });

    btnStartMerge.addEventListener('click', onMergeClicked);
    btnReset.addEventListener('click', () => resetApp(true));

    // Modal de Pré-Visualização
    btnPreview.addEventListener('click', () => {
      if (state.previewUrl) {
        pdfViewerFrame.src = state.previewUrl;
        modalFilename.textContent = state.outputFilename;
        modalBtnDownload.href = state.downloadUrl;
        modalBtnDownload.setAttribute('download', state.outputFilename);
        previewModal.classList.remove('hidden');
      }
    });

    btnCloseModal.addEventListener('click', () => {
      previewModal.classList.add('hidden');
      pdfViewerFrame.src = '';
    });

    previewModal.addEventListener('click', (e) => {
      if (e.target === previewModal) {
        previewModal.classList.add('hidden');
        pdfViewerFrame.src = '';
      }
    });
  }

  function cleanFileNameToTitle(filename) {
    return filename.replace(/\.[^/.]+$/, '').replace(/[_-]/g, ' ').trim();
  }

  function handleFilesAdded(fileListObj) {
    const validPdfs = [];
    for (let i = 0; i < fileListObj.length; i++) {
      const file = fileListObj[i];
      if (file.name.toLowerCase().endsWith('.pdf') || file.type === 'application/pdf') {
        validPdfs.push(file);
      } else {
        showToast(`O arquivo "${file.name}" foi ignorado por não ser um PDF.`, 'error');
      }
    }

    if (validPdfs.length === 0) return;

    validPdfs.forEach(file => {
      const fileId = 'f_' + Math.random().toString(36).substring(2, 9) + '_' + Date.now();
      const defaultTitle = cleanFileNameToTitle(file.name);

      state.files.push({
        id: fileId,
        serverSavedName: null,
        name: file.name,
        menuTitle: defaultTitle,
        size: file.size,
        pageCount: null,
        fileObj: file,
        isUploaded: false,
      });
    });

    renderFileList();
    showToast(`${validPdfs.length} arquivo(s) adicionado(s). Itens do menu gerados automaticamente.`, 'info');
  }

  function renderFileList() {
    fileList.innerHTML = '';

    if (state.files.length === 0) {
      filesStage.classList.add('hidden');
      dropzone.classList.remove('hidden');
      return;
    }

    dropzone.classList.add('hidden');
    filesStage.classList.remove('hidden');

    filesCounter.textContent = `${state.files.length} arquivo${state.files.length > 1 ? 's' : ''}`;

    let totalBytes = 0;

    state.files.forEach((fileItem, index) => {
      totalBytes += fileItem.size;

      const li = document.createElement('li');
      li.className = 'file-item';
      li.draggable = true;
      li.dataset.index = index;

      li.innerHTML = `
        <div class="file-item-left">
          <div class="drag-handle" title="Arraste para reordenar a sequência">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="9" cy="6" r="1.5"/><circle cx="15" cy="6" r="1.5"/>
              <circle cx="9" cy="12" r="1.5"/><circle cx="15" cy="12" r="1.5"/>
              <circle cx="9" cy="18" r="1.5"/><circle cx="15" cy="18" r="1.5"/>
            </svg>
          </div>
          <div class="file-order-badge">${index + 1}</div>
          <div class="file-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
              <line x1="16" y1="13" x2="8" y2="13"></line>
              <line x1="16" y1="17" x2="8" y2="17"></line>
            </svg>
          </div>
          <div class="file-details">
            <div class="menu-title-box">
              <span class="menu-label-tag">Menu:</span>
              <input type="text" class="menu-title-input" value="${escapeHtml(fileItem.menuTitle)}" placeholder="Nome do item no menu..." title="Edite como este item deve aparecer no menu de saída">
            </div>
            <div class="file-meta-row">
              <span class="file-original-name" title="Arquivo original: ${escapeHtml(fileItem.name)}">${escapeHtml(fileItem.name)}</span>
              <span class="meta-separator">&bull;</span>
              <span class="file-size">${formatBytes(fileItem.size)}</span>
              ${fileItem.pageCount ? `<span class="file-badge-pages">${fileItem.pageCount} pág${fileItem.pageCount > 1 ? 's' : ''}</span>` : ''}
              ${fileItem.isUploaded ? '<span class="pill-dot" title="Pronto no servidor"></span>' : ''}
            </div>
          </div>
        </div>

        <div class="file-item-right">
          <button type="button" class="btn-icon btn-move-up" title="Mover para cima" ${index === 0 ? 'disabled style="opacity:0.3;cursor:default;"' : ''}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="18 15 12 9 6 15"/></svg>
          </button>
          <button type="button" class="btn-icon btn-move-down" title="Mover para baixo" ${index === state.files.length - 1 ? 'disabled style="opacity:0.3;cursor:default;"' : ''}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
          </button>
          <button type="button" class="btn-icon btn-icon-danger btn-remove" title="Remover este arquivo">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>
      `;

      // Atualiza o menuTitle quando o usuário digitar
      const titleInput = li.querySelector('.menu-title-input');
      titleInput.addEventListener('input', (e) => {
        fileItem.menuTitle = e.target.value.trim() || cleanFileNameToTitle(fileItem.name);
      });
      // Previne que clicar no input ative drag
      titleInput.addEventListener('mousedown', (e) => e.stopPropagation());

      setupDragAndDropItem(li, index);

      const btnUp = li.querySelector('.btn-move-up');
      const btnDown = li.querySelector('.btn-move-down');
      const btnRemove = li.querySelector('.btn-remove');

      if (index > 0) {
        btnUp.addEventListener('click', (e) => {
          e.stopPropagation();
          swapFiles(index, index - 1);
        });
      }

      if (index < state.files.length - 1) {
        btnDown.addEventListener('click', (e) => {
          e.stopPropagation();
          swapFiles(index, index + 1);
        });
      }

      btnRemove.addEventListener('click', (e) => {
        e.stopPropagation();
        state.files.splice(index, 1);
        renderFileList();
      });

      fileList.appendChild(li);
    });

    totalSizeLabel.textContent = formatBytes(totalBytes);
  }

  function swapFiles(idx1, idx2) {
    const temp = state.files[idx1];
    state.files[idx1] = state.files[idx2];
    state.files[idx2] = temp;
    renderFileList();
  }

  let draggedIndex = null;

  function setupDragAndDropItem(element, index) {
    element.addEventListener('dragstart', (e) => {
      draggedIndex = index;
      element.classList.add('dragging');
      e.dataTransfer.effectAllowed = 'move';
      e.dataTransfer.setData('text/plain', index);
    });

    element.addEventListener('dragend', () => {
      element.classList.remove('dragging');
      draggedIndex = null;
    });

    element.addEventListener('dragover', (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
    });

    element.addEventListener('drop', (e) => {
      e.preventDefault();
      e.stopPropagation();
      const targetIndex = index;
      if (draggedIndex !== null && draggedIndex !== targetIndex) {
        const movedItem = state.files.splice(draggedIndex, 1)[0];
        state.files.splice(targetIndex, 0, movedItem);
        renderFileList();
      }
    });
  }

  async function onMergeClicked() {
    if (state.files.length < 2) {
      showToast('Por favor, adicione pelo menos 2 arquivos PDF para unificar.', 'error');
      return;
    }

    if (state.isProcessing) return;
    state.isProcessing = true;

    filesStage.classList.add('hidden');
    processingStage.classList.remove('hidden');

    try {
      updateProcessingStep(1, 'Gravando arquivos em disco com streaming direto...', 15);

      const filesToUpload = state.files.filter(f => !f.isUploaded);

      if (filesToUpload.length > 0) {
        const formData = new FormData();
        formData.append('session_id', state.sessionId);

        filesToUpload.forEach(f => {
          formData.append('files', f.fileObj, f.name);
        });

        const uploadRes = await fetchWithProgress('/api/upload', formData, (percent) => {
          const mappedPct = 10 + Math.round((percent * 0.45));
          updateProgress(mappedPct, `Transferindo dados para o servidor... (${percent}%)`);
        });

        if (!uploadRes.success) {
          throw new Error(uploadRes.detail || 'Falha no upload dos arquivos.');
        }

        uploadRes.files.forEach(serverFile => {
          const match = state.files.find(f => f.name === serverFile.name && !f.serverSavedName);
          if (match) {
            match.serverSavedName = serverFile.saved_filename;
            match.pageCount = serverFile.page_count;
            match.isUploaded = true;
          }
        });
      }

      updateProcessingStep(2, 'Gerando página de menu e concatenando páginas com QPDF...', 60);
      await delay(200);

      updateProcessingStep(3, 'Criando links clicáveis e menu lateral de navegação...', 80);

      let cleanName = outputFilenameInput.value.trim() || 'documento_unificado';
      if (!cleanName.toLowerCase().endsWith('.pdf')) {
        cleanName += '.pdf';
      }
      state.outputFilename = cleanName;

      // Monta a lista ordenada contendo o ID no servidor e o nome customizado para o menu
      const fileOrderPayload = state.files.map(f => ({
        id: f.serverSavedName,
        menu_title: f.menuTitle || cleanFileNameToTitle(f.name)
      }));

      const mergePayload = {
        session_id: state.sessionId,
        file_order: fileOrderPayload,
        output_filename: cleanName,
        create_visual_menu: toggleVisualMenu ? toggleVisualMenu.checked : true,
        add_bookmarks: toggleBookmarks.checked,
        linearize: toggleLinearize.checked,
      };

      updateProcessingStep(4, 'Linearizando (Fast Web View) e salvando arquivo com menu...', 92);

      const mergeResponse = await fetch('/api/merge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(mergePayload),
      });

      if (!mergeResponse.ok) {
        const errJson = await mergeResponse.json();
        throw new Error(errJson.detail || 'Erro ao processar unificação.');
      }

      const mergeResult = await mergeResponse.json();

      updateProgress(100, 'Menu de Documentos e arquivo unificado prontos!');
      await delay(300);

      displayResults(mergeResult);

    } catch (error) {
      console.error('Erro na unificação:', error);
      showToast(error.message || 'Ocorreu um erro ao juntar os PDFs.', 'error');
      processingStage.classList.add('hidden');
      filesStage.classList.remove('hidden');
    } finally {
      state.isProcessing = false;
    }
  }

  function updateProgress(percent, subtitle) {
    progressFill.style.width = `${percent}%`;
    progressPct.textContent = `${percent}%`;
    if (subtitle) {
      processingDesc.textContent = subtitle;
    }
  }

  function updateProcessingStep(stepNum, message, percent) {
    updateProgress(percent, message);

    for (let i = 1; i <= 4; i++) {
      const stepEl = document.getElementById(`step-${i}`);
      if (stepEl) {
        if (i < stepNum) {
          stepEl.className = 'step-item step-completed';
          stepEl.querySelector('.step-bullet').textContent = '✓';
        } else if (i === stepNum) {
          stepEl.className = 'step-item step-active';
          stepEl.querySelector('.step-bullet').textContent = '⚙';
        } else {
          stepEl.className = 'step-item';
          stepEl.querySelector('.step-bullet').textContent = '•';
        }
      }
    }
  }

  function displayResults(data) {
    processingStage.classList.add('hidden');
    resultStage.classList.remove('hidden');

    state.downloadUrl = data.download_url;
    state.previewUrl = data.preview_url;

    resultFilenameDisplay.textContent = data.output_filename;
    metricFiles.textContent = `${data.metrics.total_files} itens`;
    metricPages.textContent = `${data.metrics.total_pages} págs`;
    metricSize.textContent = formatBytes(data.metrics.merged_bytes);
    metricTime.textContent = `${data.metrics.duration_seconds}s`;

    btnDownload.href = data.download_url;
    btnDownload.setAttribute('download', data.output_filename);

    showToast('PDF com Menu de Documentos gerado com sucesso!', 'success');
  }

  function resetApp(deleteSession = true) {
    if (deleteSession && state.sessionId) {
      fetch(`/api/session/${state.sessionId}`, { method: 'DELETE' }).catch(() => {});
    }

    state.files = [];
    state.isProcessing = false;
    state.downloadUrl = null;
    state.previewUrl = null;
    generateSessionId();

    resultStage.classList.add('hidden');
    processingStage.classList.add('hidden');
    filesStage.classList.add('hidden');
    dropzone.classList.remove('hidden');

    updateProgress(0, '');
  }

  function fetchWithProgress(url, formData, onProgress) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', url);

      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) {
          const percent = Math.round((e.loaded / e.total) * 100);
          onProgress(percent);
        }
      };

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            resolve(JSON.parse(xhr.responseText));
          } catch (e) {
            reject(new Error('Resposta inválida do servidor.'));
          }
        } else {
          try {
            const err = JSON.parse(xhr.responseText);
            reject(new Error(err.detail || 'Erro na requisição.'));
          } catch (e) {
            reject(new Error(`Erro HTTP ${xhr.status}`));
          }
        }
      };

      xhr.onerror = () => reject(new Error('Falha de conexão com o servidor.'));
      xhr.send(formData);
    });
  }

  function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    let iconSvg = '';
    if (type === 'success') {
      iconSvg = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#34D399" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>';
    } else if (type === 'error') {
      iconSvg = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#EF4444" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>';
    } else {
      iconSvg = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#38BDF8" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>';
    }

    toast.innerHTML = `${iconSvg}<span>${escapeHtml(message)}</span>`;
    toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.remove();
    }, 4000);
  }

  function formatBytes(bytes, decimals = 1) {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

})();
