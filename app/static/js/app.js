/**
 * Klynner PDF PRO - Suíte Completa de Alta Performance para PDFs
 * Gerencia:
 * 1. Juntar PDF (com Menu de Documentos e Marcadores QPDF)
 * 2. Dividir / Split PDF (por intervalos, avulsas em ZIP, ou páginas específicas)
 * 3. Organizar e Reordenar Páginas (miniaturas PDF.js com Drag & Drop, duplicação e exclusão)
 * 4. Girar Páginas (individualmente ou em lote: 90°, 180°, 270°)
 * 5. Extrair Páginas (seleção visual sincronizada por miniaturas ou intervalos, em PDF ou ZIP)
 */

(function () {
  'use strict';

  // Configuração do Worker do PDF.js
  if (window.pdfjsLib) {
    pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
  }

  // Configurações contextuais de cada ferramenta
  const TOOL_CONFIGS = {
    merge: {
      heroTitle: 'Junte arquivos PDF grandes com Menu de Documentos',
      heroSub: 'O arquivo final incluirá um <strong>Menu Interativo</strong> onde cada item corresponde ao nome do arquivo original, com navegação instantânea tanto na primeira página quanto no menu lateral do leitor de PDF.',
      dropHeading: 'Arraste seus arquivos PDF aqui (múltiplos)',
      dropSub: 'ou clique para selecionar documentos do computador',
      dropBadges: ['Menu de itens por arquivo', 'Suporte a múltiplos gigabytes', 'Reordenação interativa'],
      multiple: true,
      enginePill: 'Menu Interativo Ativo',
      stageId: 'stage-merge',
    },
    split: {
      heroTitle: 'Divida seu documento PDF em intervalos ou páginas avulsas',
      heroSub: 'Separe por intervalos customizados (ex: págs. 1-5, 6-10), quebre o documento em partes ou exporte cada página individual em um arquivo avulso compactado (.ZIP).',
      dropHeading: 'Arraste o arquivo PDF que deseja dividir',
      dropSub: 'ou clique para selecionar do computador',
      dropBadges: ['Quebra por faixas (ex: 1-5, 6-10)', 'Exportar páginas avulsas (.ZIP)', 'Processamento C++ instantâneo'],
      multiple: false,
      enginePill: 'Divisor QPDF Ativo',
      stageId: 'stage-split',
    },
    organize: {
      heroTitle: 'Reorganize, duplique ou exclua páginas do PDF',
      heroSub: 'Visualização completa em grade das miniaturas (thumbnails) com arrastar-e-soltar (drag and drop) para reorganizar, duplicar páginas importantes ou excluir páginas desnecessárias.',
      dropHeading: 'Arraste o arquivo PDF para organizar as páginas',
      dropSub: 'ou clique para selecionar do computador',
      dropBadges: ['Miniaturas em alta resolução', 'Arrastar e soltar (Drag & Drop)', 'Duplicação e exclusão instantânea'],
      multiple: false,
      enginePill: 'Organizador Visual Ativo',
      stageId: 'stage-organize',
    },
    rotate: {
      heroTitle: 'Gire páginas de PDF para corrigir a orientação',
      heroSub: 'Rotação individual por página ou em lote (90°, 180°, 270°) com visualização em tempo real das miniaturas para corrigir páginas invertidas ou digitalizadas de lado.',
      dropHeading: 'Arraste o arquivo PDF para girar as páginas',
      dropSub: 'ou clique para selecionar do computador',
      dropBadges: ['Girar 90°, 180° ou 270°', 'Em lote (todas, pares, ímpares)', 'Preservação de qualidade e texto'],
      multiple: false,
      enginePill: 'Rotacionador QPDF Ativo',
      stageId: 'stage-rotate',
    },
    extract: {
      heroTitle: 'Extraia páginas específicas e gere um novo PDF',
      heroSub: 'Gere um novo documento PDF contendo apenas as páginas selecionadas visualmente ou digitando intervalos numéricos, com opção de mesclar em PDF único ou salvar páginas avulsas em ZIP.',
      dropHeading: 'Arraste o arquivo PDF para extrair páginas',
      dropSub: 'ou clique para selecionar do computador',
      dropBadges: ['Seleção visual por miniaturas', 'Filtros rápidos (Pares, Ímpares)', 'Exportar como PDF único ou ZIP'],
      multiple: false,
      enginePill: 'Extrator QPDF Ativo',
      stageId: 'stage-extract',
    },
  };

  // Estado Central da Aplicação
  const state = {
    sessionId: null,
    activeTool: 'merge',
    isProcessing: false,
    downloadUrl: null,
    previewUrl: null,
    outputFilename: '',
    isZipResult: false,

    // Juntar PDF
    mergeFiles: [], // { id, name, menuTitle, size, pageCount, fileObj, isUploaded, serverSavedName }

    // Ferramentas de 1 Documento (Split, Organize, Rotate, Extract)
    activeDoc: null, // { name, size, pageCount, serverSavedName, fileObj, pdfDoc }

    // Organizar
    organizeItems: [], // [ { uid, origPage, rotation: 0, canvas: canvasEl } ]
    draggedOrganizeIdx: null,

    // Girar
    rotateMap: {}, // { [pageNum: number]: rotationAngle: number }

    // Extrair
    extractSelected: new Set(), // Set<number> (1-based)
  };

  // Cache de miniaturas geradas
  const thumbnailCache = new Map();

  // Elementos do DOM Compartilhados
  const toolsNavContainer = document.getElementById('tools-nav-bar');
  const heroTitle = document.getElementById('hero-title');
  const heroSubtitle = document.getElementById('hero-subtitle');
  const engineStatusText = document.getElementById('engine-status-text');

  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('file-input');
  const dropzoneHeading = document.getElementById('dropzone-heading');
  const dropzoneSub = document.getElementById('dropzone-sub');
  const dropzoneBadges = document.getElementById('dropzone-badges');

  const processingStage = document.getElementById('processing-stage');
  const processingTitle = document.getElementById('processing-status-title');
  const processingDesc = document.getElementById('processing-status-desc');
  const progressFill = document.getElementById('progress-fill');
  const progressPct = document.getElementById('progress-pct');

  const resultStage = document.getElementById('result-stage');
  const resultStatusTitle = document.getElementById('result-status-title');
  const resultFilenameDisplay = document.getElementById('result-filename-display');
  const metricLabel1 = document.getElementById('metric-label-1');
  const metricFiles = document.getElementById('metric-files');
  const metricLabel2 = document.getElementById('metric-label-2');
  const metricPages = document.getElementById('metric-pages');
  const metricSize = document.getElementById('metric-size');
  const metricTime = document.getElementById('metric-time');
  const btnDownload = document.getElementById('btn-download');
  const btnDownloadText = document.getElementById('btn-download-text');
  const btnPreview = document.getElementById('btn-preview');
  const btnReset = document.getElementById('btn-reset');

  const previewModal = document.getElementById('preview-modal');
  const btnCloseModal = document.getElementById('btn-close-modal');
  const pdfViewerFrame = document.getElementById('pdf-viewer-frame');
  const modalFilename = document.getElementById('modal-filename');
  const modalBtnDownload = document.getElementById('modal-btn-download');
  const toastContainer = document.getElementById('toast-container');

  // Elementos Juntar PDF
  const stageMerge = document.getElementById('stage-merge');
  const fileList = document.getElementById('file-list');
  const filesCounter = document.getElementById('files-counter');
  const totalSizeLabel = document.getElementById('total-size-label');
  const btnAddMore = document.getElementById('btn-add-more');
  const btnClearAll = document.getElementById('btn-clear-all');
  const btnStartMerge = document.getElementById('btn-start-merge');
  const outputFilenameMerge = document.getElementById('output-filename');
  const toggleVisualMenu = document.getElementById('toggle-visual-menu');
  const toggleBookmarks = document.getElementById('toggle-bookmarks');
  const toggleLinearize = document.getElementById('toggle-linearize');

  // Elementos Dividir PDF
  const stageSplit = document.getElementById('stage-split');
  const splitDocName = document.getElementById('split-doc-name');
  const splitDocPages = document.getElementById('split-doc-pages');
  const splitDocSize = document.getElementById('split-doc-size');
  const btnSplitChangeDoc = document.getElementById('btn-split-change-doc');
  const splitRangesInput = document.getElementById('split-ranges-input');
  const rangesChipsList = document.getElementById('ranges-chips-list');
  const splitControlsRanges = document.getElementById('split-controls-ranges');
  const splitControlsAll = document.getElementById('split-controls-all');
  const splitBurstCount = document.getElementById('split-burst-count');
  const splitOutputFilename = document.getElementById('split-output-filename');
  const toggleSplitLinearize = document.getElementById('toggle-split-linearize');
  const btnStartSplit = document.getElementById('btn-start-split');

  // Elementos Organizar Páginas
  const stageOrganize = document.getElementById('stage-organize');
  const organizeDocName = document.getElementById('organize-doc-name');
  const organizePagesCounter = document.getElementById('organize-pages-counter');
  const organizeDocSize = document.getElementById('organize-doc-size');
  const btnOrganizeReset = document.getElementById('btn-organize-reset');
  const btnOrganizeChangeDoc = document.getElementById('btn-organize-change-doc');
  const organizeLoading = document.getElementById('organize-loading');
  const organizeGrid = document.getElementById('organize-grid');
  const organizeOutputFilename = document.getElementById('organize-output-filename');
  const toggleOrganizeLinearize = document.getElementById('toggle-organize-linearize');
  const organizeTotalLabel = document.getElementById('organize-total-label');
  const btnStartOrganize = document.getElementById('btn-start-organize');

  // Elementos Girar Páginas
  const stageRotate = document.getElementById('stage-rotate');
  const rotateDocName = document.getElementById('rotate-doc-name');
  const rotateDocPages = document.getElementById('rotate-doc-pages');
  const rotateDocSize = document.getElementById('rotate-doc-size');
  const btnRotateChangeDoc = document.getElementById('btn-rotate-change-doc');
  const btnRotateAllCw = document.getElementById('btn-rotate-all-cw');
  const btnRotateAllCcw = document.getElementById('btn-rotate-all-ccw');
  const btnRotateAll180 = document.getElementById('btn-rotate-all-180');
  const btnRotateEvens = document.getElementById('btn-rotate-evens');
  const btnRotateOdds = document.getElementById('btn-rotate-odds');
  const btnRotateReset = document.getElementById('btn-rotate-reset');
  const rotateLoading = document.getElementById('rotate-loading');
  const rotateGrid = document.getElementById('rotate-grid');
  const rotateOutputFilename = document.getElementById('rotate-output-filename');
  const toggleRotateLinearize = document.getElementById('toggle-rotate-linearize');
  const rotateModifiedLabel = document.getElementById('rotate-modified-label');
  const btnStartRotate = document.getElementById('btn-start-rotate');

  // Elementos Extrair Páginas
  const stageExtract = document.getElementById('stage-extract');
  const extractDocName = document.getElementById('extract-doc-name');
  const extractDocPages = document.getElementById('extract-doc-pages');
  const extractDocSize = document.getElementById('extract-doc-size');
  const btnExtractChangeDoc = document.getElementById('btn-extract-change-doc');
  const extractRangesInput = document.getElementById('extract-ranges-input');
  const btnExtractAll = document.getElementById('btn-extract-all');
  const btnExtractNone = document.getElementById('btn-extract-none');
  const btnExtractInvert = document.getElementById('btn-extract-invert');
  const btnExtractEvens = document.getElementById('btn-extract-evens');
  const btnExtractOdds = document.getElementById('btn-extract-odds');
  const extractLoading = document.getElementById('extract-loading');
  const extractGrid = document.getElementById('extract-grid');
  const extractOutputFilename = document.getElementById('extract-output-filename');
  const toggleExtractLinearize = document.getElementById('toggle-extract-linearize');
  const extractSelectedLabel = document.getElementById('extract-selected-label');
  const btnStartExtract = document.getElementById('btn-start-extract');

  // =========================================================================
  // INICIALIZAÇÃO
  // =========================================================================
  init();

  function init() {
    generateSessionId();
    setupNavigation();
    setupDropzone();
    setupMergeEvents();
    setupSplitEvents();
    setupOrganizeEvents();
    setupRotateEvents();
    setupExtractEvents();
    setupModalAndPix();

    // Suporte a hash da URL (ex: #split, #organize)
    const hash = window.location.hash.replace('#', '');
    if (TOOL_CONFIGS[hash]) {
      switchTool(hash);
    } else {
      switchTool('merge');
    }
  }

  function generateSessionId() {
    state.sessionId = 'sess_' + Math.random().toString(36).substring(2, 11) + '_' + Date.now();
  }

  // =========================================================================
  // NAVEGAÇÃO ENTRE FERRAMENTAS
  // =========================================================================
  function setupNavigation() {
    const navButtons = document.querySelectorAll('.tool-nav-btn');
    navButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const targetTool = btn.dataset.tool;
        if (targetTool && targetTool !== state.activeTool) {
          switchTool(targetTool);
        }
      });
    });

    window.addEventListener('hashchange', () => {
      const hash = window.location.hash.replace('#', '');
      if (TOOL_CONFIGS[hash] && hash !== state.activeTool) {
        switchTool(hash);
      }
    });
  }

  function switchTool(toolKey) {
    if (!TOOL_CONFIGS[toolKey]) return;
    state.activeTool = toolKey;

    // Atualiza classes ativas na barra de ferramentas
    document.querySelectorAll('.tool-nav-btn').forEach(btn => {
      if (btn.dataset.tool === toolKey) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    // Atualiza cabeçalho e dropzone
    const cfg = TOOL_CONFIGS[toolKey];
    heroTitle.textContent = cfg.heroTitle;
    heroSubtitle.innerHTML = cfg.heroSub;
    engineStatusText.textContent = cfg.enginePill;
    dropzoneHeading.textContent = cfg.dropHeading;
    dropzoneSub.textContent = cfg.dropSub;
    fileInput.multiple = cfg.multiple;

    dropzoneBadges.innerHTML = cfg.dropBadges
      .map(b => `<span class="dropzone-badge">${escapeHtml(b)}</span>`)
      .join('');

    // Sincroniza hash sem scroll desnecessário
    if (window.location.hash !== '#' + toolKey) {
      history.replaceState(null, '', '#' + toolKey);
    }

    // Se estiver em progresso ou resultado, limpa para a nova ferramenta
    processingStage.classList.add('hidden');
    resultStage.classList.add('hidden');

    // Oculta todos os estágios das ferramentas
    document.querySelectorAll('.tool-stage').forEach(el => el.classList.add('hidden'));

    // Verifica se a ferramenta já possui dados carregados
    if (toolKey === 'merge') {
      if (state.mergeFiles.length > 0) {
        dropzone.classList.add('hidden');
        stageMerge.classList.remove('hidden');
        renderMergeFileList();
      } else {
        dropzone.classList.remove('hidden');
      }
    } else {
      if (state.activeDoc) {
        dropzone.classList.add('hidden');
        activateSingleDocToolStage(toolKey);
      } else {
        dropzone.classList.remove('hidden');
      }
    }
  }

  function activateSingleDocToolStage(toolKey) {
    const stageId = TOOL_CONFIGS[toolKey].stageId;
    const stageEl = document.getElementById(stageId);
    if (!stageEl) return;

    stageEl.classList.remove('hidden');

    if (toolKey === 'split') {
      initSplitWorkspace();
    } else if (toolKey === 'organize') {
      initOrganizeWorkspace();
    } else if (toolKey === 'rotate') {
      initRotateWorkspace();
    } else if (toolKey === 'extract') {
      initExtractWorkspace();
    }
  }

  // =========================================================================
  // GESTÃO DO DROPZONE & UPLOAD
  // =========================================================================
  function setupDropzone() {
    dropzone.addEventListener('click', () => fileInput.click());

    ['dragenter', 'dragover'].forEach(name => {
      dropzone.addEventListener(name, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.add('dragover');
      });
    });

    ['dragleave', 'drop'].forEach(name => {
      dropzone.addEventListener(name, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove('dragover');
      });
    });

    dropzone.addEventListener('drop', (e) => {
      const droppedFiles = e.dataTransfer.files;
      if (droppedFiles.length > 0) {
        handleIncomingFiles(droppedFiles);
      }
    });

    fileInput.addEventListener('change', (e) => {
      if (e.target.files.length > 0) {
        handleIncomingFiles(e.target.files);
        fileInput.value = '';
      }
    });
  }

  async function handleIncomingFiles(fileListObj) {
    const validPdfs = [];
    for (let i = 0; i < fileListObj.length; i++) {
      const file = fileListObj[i];
      if (file.name.toLowerCase().endsWith('.pdf') || file.type === 'application/pdf') {
        validPdfs.push(file);
      } else {
        showToast(`O arquivo "${file.name}" foi ignorado por não ser PDF.`, 'error');
      }
    }

    if (validPdfs.length === 0) return;

    if (state.activeTool === 'merge') {
      // Adiciona à lista de mesclagem
      validPdfs.forEach(file => {
        const fileId = 'f_' + Math.random().toString(36).substring(2, 9) + '_' + Date.now();
        state.mergeFiles.push({
          id: fileId,
          serverSavedName: null,
          name: file.name,
          menuTitle: cleanFileNameToTitle(file.name),
          size: file.size,
          pageCount: null,
          fileObj: file,
          isUploaded: false,
        });
      });

      dropzone.classList.add('hidden');
      stageMerge.classList.remove('hidden');
      renderMergeFileList();
      showToast(`${validPdfs.length} arquivo(s) adicionado(s) à unificação.`, 'info');

    } else {
      // Ferramenta de documento único (Split, Organize, Rotate, Extract)
      const targetFile = validPdfs[0];
      await loadActiveDocument(targetFile);
    }
  }

  async function loadActiveDocument(fileObj) {
    try {
      showToast(`Carregando documento "${fileObj.name}"...`, 'info');

      // Lê com PDF.js para renderização de miniaturas
      let pdfDoc = null;
      if (window.pdfjsLib) {
        const arrayBuffer = await fileObj.arrayBuffer();
        const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer });
        pdfDoc = await loadingTask.promise;
      }

      state.activeDoc = {
        name: fileObj.name,
        size: fileObj.size,
        pageCount: pdfDoc ? pdfDoc.numPages : 1,
        serverSavedName: null,
        fileObj: fileObj,
        pdfDoc: pdfDoc,
      };

      // Limpa cache de miniaturas ao carregar novo documento
      thumbnailCache.clear();

      dropzone.classList.add('hidden');
      activateSingleDocToolStage(state.activeTool);
      showToast(`Documento carregado com ${state.activeDoc.pageCount} páginas.`, 'success');

      // Dispara upload em segundo plano para já deixar pronto no servidor
      uploadSingleDocInBackground();

    } catch (err) {
      console.error('Erro ao ler PDF:', err);
      showToast('Falha ao abrir o documento PDF no navegador.', 'error');
    }
  }

  async function uploadSingleDocInBackground() {
    if (!state.activeDoc || state.activeDoc.serverSavedName) return;

    try {
      const formData = new FormData();
      formData.append('session_id', state.sessionId);
      formData.append('files', state.activeDoc.fileObj, state.activeDoc.name);

      const res = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });

      if (res.ok) {
        const data = await res.json();
        if (data.files && data.files.length > 0) {
          state.activeDoc.serverSavedName = data.files[0].saved_filename;
          if (data.files[0].page_count) {
            state.activeDoc.pageCount = data.files[0].page_count;
          }
        }
      }
    } catch (e) {
      console.warn('Upload prévio em segundo plano falhou (será reenviado na execução):', e);
    }
  }

  function resetCurrentDocument() {
    state.activeDoc = null;
    state.organizeItems = [];
    state.rotateMap = {};
    state.extractSelected.clear();
    thumbnailCache.clear();

    document.querySelectorAll('.tool-stage').forEach(el => el.classList.add('hidden'));
    dropzone.classList.remove('hidden');
    fileInput.value = '';
  }

  // =========================================================================
  // FERRAMENTA 1: JUNTAR PDF (MERGE)
  // =========================================================================
  function setupMergeEvents() {
    btnAddMore.addEventListener('click', () => fileInput.click());
    btnClearAll.addEventListener('click', () => {
      if (confirm('Deseja realmente remover todos os arquivos selecionados?')) {
        state.mergeFiles = [];
        renderMergeFileList();
      }
    });

    btnStartMerge.addEventListener('click', onExecuteMerge);
  }

  function renderMergeFileList() {
    fileList.innerHTML = '';

    if (state.mergeFiles.length === 0) {
      stageMerge.classList.add('hidden');
      dropzone.classList.remove('hidden');
      return;
    }

    filesCounter.textContent = `${state.mergeFiles.length} arquivo${state.mergeFiles.length > 1 ? 's' : ''}`;

    let totalBytes = 0;

    state.mergeFiles.forEach((item, index) => {
      totalBytes += item.size;

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
              <input type="text" class="menu-title-input" value="${escapeHtml(item.menuTitle)}" placeholder="Nome do item no menu..." title="Edite como este item deve aparecer no menu de saída">
            </div>
            <div class="file-meta-row">
              <span class="file-original-name" title="Arquivo: ${escapeHtml(item.name)}">${escapeHtml(item.name)}</span>
              <span class="meta-separator">&bull;</span>
              <span class="file-size">${formatBytes(item.size)}</span>
              ${item.pageCount ? `<span class="file-badge-pages">${item.pageCount} pág${item.pageCount > 1 ? 's' : ''}</span>` : ''}
            </div>
          </div>
        </div>

        <div class="file-item-right">
          <button type="button" class="btn-icon btn-move-up" title="Mover para cima" ${index === 0 ? 'disabled style="opacity:0.3;cursor:default;"' : ''}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="18 15 12 9 6 15"/></svg>
          </button>
          <button type="button" class="btn-icon btn-move-down" title="Mover para baixo" ${index === state.mergeFiles.length - 1 ? 'disabled style="opacity:0.3;cursor:default;"' : ''}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
          </button>
          <button type="button" class="btn-icon btn-icon-danger btn-remove" title="Remover este arquivo">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>
      `;

      const titleInput = li.querySelector('.menu-title-input');
      titleInput.addEventListener('input', (e) => {
        item.menuTitle = e.target.value.trim() || cleanFileNameToTitle(item.name);
      });
      titleInput.addEventListener('mousedown', (e) => e.stopPropagation());

      setupMergeDragDrop(li, index);

      li.querySelector('.btn-move-up').addEventListener('click', (e) => {
        e.stopPropagation();
        if (index > 0) swapMergeFiles(index, index - 1);
      });

      li.querySelector('.btn-move-down').addEventListener('click', (e) => {
        e.stopPropagation();
        if (index < state.mergeFiles.length - 1) swapMergeFiles(index, index + 1);
      });

      li.querySelector('.btn-remove').addEventListener('click', (e) => {
        e.stopPropagation();
        state.mergeFiles.splice(index, 1);
        renderMergeFileList();
      });

      fileList.appendChild(li);
    });

    totalSizeLabel.textContent = formatBytes(totalBytes);
  }

  function swapMergeFiles(i, j) {
    const tmp = state.mergeFiles[i];
    state.mergeFiles[i] = state.mergeFiles[j];
    state.mergeFiles[j] = tmp;
    renderMergeFileList();
  }

  let draggedMergeIndex = null;
  function setupMergeDragDrop(element, index) {
    element.addEventListener('dragstart', (e) => {
      draggedMergeIndex = index;
      element.classList.add('dragging');
      e.dataTransfer.effectAllowed = 'move';
      e.dataTransfer.setData('text/plain', index);
    });

    element.addEventListener('dragend', () => {
      element.classList.remove('dragging');
      draggedMergeIndex = null;
    });

    element.addEventListener('dragover', (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
    });

    element.addEventListener('drop', (e) => {
      e.preventDefault();
      e.stopPropagation();
      const targetIndex = index;
      if (draggedMergeIndex !== null && draggedMergeIndex !== targetIndex) {
        const moved = state.mergeFiles.splice(draggedMergeIndex, 1)[0];
        state.mergeFiles.splice(targetIndex, 0, moved);
        renderMergeFileList();
      }
    });
  }

  async function onExecuteMerge() {
    if (state.mergeFiles.length < 2) {
      showToast('Por favor, adicione ao menos 2 arquivos PDF para unificar.', 'error');
      return;
    }

    await ensureFilesUploaded(state.mergeFiles);

    startProcessingUI('Unificando PDFs com Menu de Documentos...', 'Gerando página de sumário e marcadores clicáveis...');

    try {
      updateProcessingStep(1, 'Gravando arquivos em disco rígido...', 20);
      await delay(200);

      updateProcessingStep(2, 'Calculando estrutura de páginas e gerando sumário visual...', 50);
      await delay(200);

      updateProcessingStep(3, 'Inserindo hiperlinks clicáveis e marcadores com QPDF C++...', 75);

      let cleanName = outputFilenameMerge.value.trim() || 'documento_unificado';
      if (!cleanName.toLowerCase().endsWith('.pdf')) cleanName += '.pdf';

      const payload = {
        session_id: state.sessionId,
        file_order: state.mergeFiles.map(f => ({
          id: f.serverSavedName,
          menu_title: f.menuTitle || cleanFileNameToTitle(f.name)
        })),
        output_filename: cleanName,
        create_visual_menu: toggleVisualMenu.checked,
        add_bookmarks: toggleBookmarks.checked,
        linearize: toggleLinearize.checked,
      };

      updateProcessingStep(4, 'Linearizando (Fast Web View) e salvando documento final...', 90);

      const res = await fetch('/api/merge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errJson = await res.json();
        throw new Error(errJson.detail || 'Falha ao processar unificação.');
      }

      const data = await res.json();
      updateProgress(100, 'PDF com Menu de Documentos pronto!');
      await delay(300);

      showResultUI({
        title: 'PDF com Menu de Documentos Criado!',
        filename: data.output_filename,
        downloadUrl: data.download_url,
        previewUrl: data.preview_url,
        isZip: false,
        label1: 'Itens no Menu',
        val1: `${data.metrics.total_files} itens`,
        label2: 'Total de Páginas',
        val2: `${data.metrics.total_pages} págs`,
        sizeBytes: data.metrics.merged_bytes,
        durationSec: data.metrics.duration_seconds,
      });

    } catch (e) {
      console.error(e);
      showToast(e.message || 'Erro durante a unificação dos PDFs.', 'error');
      stopProcessingUI(stageMerge);
    }
  }

  // =========================================================================
  // FERRAMENTA 2: DIVIDIR / SPLIT PDF
  // =========================================================================
  function setupSplitEvents() {
    btnSplitChangeDoc.addEventListener('click', resetCurrentDocument);

    const splitModeInputs = document.querySelectorAll('input[name="split-mode"]');
    splitModeInputs.forEach(input => {
      input.addEventListener('change', () => {
        state.splitMode = input.value;
        if (state.splitMode === 'all_pages') {
          splitControlsRanges.classList.add('hidden');
          splitControlsAll.classList.remove('hidden');
        } else {
          splitControlsRanges.classList.remove('hidden');
          splitControlsAll.classList.add('hidden');
        }
        updateSplitRangesChips();
      });
    });

    splitRangesInput.addEventListener('input', updateSplitRangesChips);
    btnStartSplit.addEventListener('click', onExecuteSplit);
  }

  function initSplitWorkspace() {
    if (!state.activeDoc) return;

    splitDocName.textContent = state.activeDoc.name;
    splitDocPages.textContent = state.activeDoc.pageCount;
    splitDocSize.textContent = formatBytes(state.activeDoc.size);
    splitBurstCount.textContent = state.activeDoc.pageCount;

    // Sugere intervalos padrão com base no número de páginas
    const totalP = state.activeDoc.pageCount;
    if (totalP <= 3) {
      splitRangesInput.value = '1, 2, 3'.substring(0, totalP * 3);
    } else {
      const half = Math.floor(totalP / 2);
      splitRangesInput.value = `1-${half}, ${half + 1}-${totalP}`;
    }

    const baseStem = cleanFileNameToTitle(state.activeDoc.name);
    splitOutputFilename.value = `${baseStem}_dividido`;

    updateSplitRangesChips();
  }

  function updateSplitRangesChips() {
    rangesChipsList.innerHTML = '';
    const totalP = state.activeDoc ? state.activeDoc.pageCount : 100;
    const val = splitRangesInput.value.trim();

    if (!val) {
      rangesChipsList.innerHTML = '<span class="input-hint">Digite intervalos acima (ex: 1-5, 6-10)</span>';
      return;
    }

    const tokens = val.split(',').map(s => s.trim()).filter(Boolean);
    tokens.forEach((tok, idx) => {
      const chip = document.createElement('span');
      chip.className = 'range-chip';
      chip.textContent = `Parte ${idx + 1}: ${tok}`;
      rangesChipsList.appendChild(chip);
    });
  }

  async function onExecuteSplit() {
    if (!state.activeDoc) return;
    await ensureDocUploaded(state.activeDoc);

    startProcessingUI('Dividindo documento PDF...', 'Extraindo faixas de páginas com QPDF C++...');

    try {
      updateProcessingStep(1, 'Lendo estrutura e cabeçalhos do documento...', 25);
      await delay(200);

      updateProcessingStep(2, 'Separando páginas e criando partes...', 60);

      const baseName = splitOutputFilename.value.trim() || 'documento_dividido';
      const payload = {
        session_id: state.sessionId,
        file_id: state.activeDoc.serverSavedName,
        mode: state.splitMode,
        range_input: splitRangesInput.value.trim(),
        output_filename: baseName,
        linearize: toggleSplitLinearize.checked,
      };

      updateProcessingStep(3, 'Empacotando e finalizando arquivos...', 85);

      const res = await fetch('/api/split', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errJson = await res.json();
        throw new Error(errJson.detail || 'Erro ao dividir PDF.');
      }

      const data = await res.json();
      updateProgress(100, 'Divisão de PDF concluída com sucesso!');
      await delay(300);

      showResultUI({
        title: 'PDF Dividido com Sucesso!',
        filename: data.output_filename,
        downloadUrl: data.download_url,
        previewUrl: data.preview_url,
        isZip: data.is_zip,
        label1: 'Arquivos Gerados',
        val1: `${data.metrics.files_generated} arquivo(s)`,
        label2: 'Páginas Originais',
        val2: `${data.metrics.total_source_pages} págs`,
        sizeBytes: data.metrics.output_bytes,
        durationSec: data.metrics.duration_seconds,
      });

    } catch (e) {
      console.error(e);
      showToast(e.message || 'Erro ao dividir o documento.', 'error');
      stopProcessingUI(stageSplit);
    }
  }

  // =========================================================================
  // FERRAMENTA 3: ORGANIZAR E REORDENAR PÁGINAS
  // =========================================================================
  function setupOrganizeEvents() {
    btnOrganizeChangeDoc.addEventListener('click', resetCurrentDocument);
    btnOrganizeReset.addEventListener('click', () => {
      if (confirm('Deseja restaurar a ordem original das páginas?')) {
        initOrganizeWorkspace();
      }
    });

    btnStartOrganize.addEventListener('click', onExecuteOrganize);
  }

  async function initOrganizeWorkspace() {
    if (!state.activeDoc) return;

    organizeDocName.textContent = state.activeDoc.name;
    organizeDocSize.textContent = formatBytes(state.activeDoc.size);
    const baseStem = cleanFileNameToTitle(state.activeDoc.name);
    organizeOutputFilename.value = `${baseStem}_organizado`;

    const totalP = state.activeDoc.pageCount;
    state.organizeItems = [];

    for (let p = 1; p <= totalP; p++) {
      state.organizeItems.push({
        uid: 'pg_' + p + '_' + Date.now() + '_' + Math.random().toString(36).substring(2, 6),
        origPage: p,
        rotation: 0,
      });
    }

    updateOrganizeCounter();
    await renderOrganizeGrid();
  }

  function updateOrganizeCounter() {
    const count = state.organizeItems.length;
    organizePagesCounter.textContent = count;
    organizeTotalLabel.textContent = `${count} página${count !== 1 ? 's' : ''}`;
  }

  async function renderOrganizeGrid() {
    organizeGrid.innerHTML = '';
    organizeLoading.classList.add('active');

    for (let i = 0; i < state.organizeItems.length; i++) {
      const item = state.organizeItems[i];
      const card = createOrganizePageCard(item, i);
      organizeGrid.appendChild(card);
    }

    organizeLoading.classList.remove('active');
  }

  function createOrganizePageCard(item, index) {
    const card = document.createElement('div');
    card.className = 'page-card';
    card.draggable = true;
    card.dataset.index = index;

    card.innerHTML = `
      <div class="page-card-header">
        <span class="page-badge-order">#${index + 1}</span>
        <span class="page-badge-orig">Pág. ${item.origPage}</span>
        <div class="page-card-drag-handle" title="Arraste para reposicionar">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="9" cy="6" r="1.5"/><circle cx="15" cy="6" r="1.5"/><circle cx="9" cy="12" r="1.5"/><circle cx="15" cy="12" r="1.5"/><circle cx="9" cy="18" r="1.5"/><circle cx="15" cy="18" r="1.5"/></svg>
        </div>
      </div>

      <div class="page-card-preview-wrapper">
        <canvas class="page-thumbnail-canvas" id="canvas-org-${item.uid}"></canvas>
        ${item.rotation !== 0 ? `<span class="page-rotation-badge">+${item.rotation}°</span>` : ''}
      </div>

      <div class="page-card-actions">
        <button type="button" class="card-action-btn btn-card-rot" title="Girar 90° horário">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
        </button>
        <button type="button" class="card-action-btn btn-card-dup" title="Duplicar esta página">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        </button>
        <button type="button" class="card-action-btn card-action-btn-danger btn-card-del" title="Excluir página">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>
    `;

    // Renderiza a miniatura no canvas
    const canvas = card.querySelector(`#canvas-org-${item.uid}`);
    applyPageRotationStyle(canvas, item.rotation);
    renderThumbnailPage(item.origPage, canvas);

    // Eventos dos botões do card
    card.querySelector('.btn-card-rot').addEventListener('click', (e) => {
      e.stopPropagation();
      item.rotation = (item.rotation + 90) % 360;
      applyPageRotationStyle(canvas, item.rotation);
      const rotBadge = card.querySelector('.page-rotation-badge');
      if (item.rotation !== 0) {
        if (rotBadge) {
          rotBadge.textContent = `+${item.rotation}°`;
        } else {
          const newBadge = document.createElement('span');
          newBadge.className = 'page-rotation-badge';
          newBadge.textContent = `+${item.rotation}°`;
          card.querySelector('.page-card-preview-wrapper').appendChild(newBadge);
        }
      } else if (rotBadge) {
        rotBadge.remove();
      }
    });

    card.querySelector('.btn-card-dup').addEventListener('click', (e) => {
      e.stopPropagation();
      const newItem = {
        uid: 'pg_' + item.origPage + '_' + Date.now() + '_' + Math.random().toString(36).substring(2, 6),
        origPage: item.origPage,
        rotation: item.rotation,
      };
      state.organizeItems.splice(index + 1, 0, newItem);
      updateOrganizeCounter();
      renderOrganizeGrid();
      showToast(`Página ${item.origPage} duplicada com sucesso.`, 'info');
    });

    card.querySelector('.btn-card-del').addEventListener('click', (e) => {
      e.stopPropagation();
      if (state.organizeItems.length <= 1) {
        showToast('O documento não pode ficar sem nenhuma página.', 'error');
        return;
      }
      state.organizeItems.splice(index, 1);
      updateOrganizeCounter();
      renderOrganizeGrid();
    });

    // Drag and Drop para reordenar
    setupOrganizeCardDrag(card, index);

    return card;
  }

  function setupOrganizeCardDrag(card, index) {
    card.addEventListener('dragstart', (e) => {
      state.draggedOrganizeIdx = index;
      card.classList.add('dragging');
      e.dataTransfer.effectAllowed = 'move';
      e.dataTransfer.setData('text/plain', index);
    });

    card.addEventListener('dragend', () => {
      card.classList.remove('dragging');
      state.draggedOrganizeIdx = null;
      document.querySelectorAll('.page-card').forEach(c => c.classList.remove('drag-over'));
    });

    card.addEventListener('dragover', (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
      card.classList.add('drag-over');
    });

    card.addEventListener('dragleave', () => {
      card.classList.remove('drag-over');
    });

    card.addEventListener('drop', (e) => {
      e.preventDefault();
      e.stopPropagation();
      card.classList.remove('drag-over');

      const targetIdx = index;
      if (state.draggedOrganizeIdx !== null && state.draggedOrganizeIdx !== targetIdx) {
        const moved = state.organizeItems.splice(state.draggedOrganizeIdx, 1)[0];
        state.organizeItems.splice(targetIdx, 0, moved);
        renderOrganizeGrid();
      }
    });
  }

  async function onExecuteOrganize() {
    if (!state.activeDoc || state.organizeItems.length === 0) return;
    await ensureDocUploaded(state.activeDoc);

    startProcessingUI('Reorganizando páginas do PDF...', 'Montando nova sequência estrutural...');

    try {
      updateProcessingStep(1, 'Compilando lista ordenada de páginas...', 30);
      await delay(200);

      updateProcessingStep(2, 'Construindo novo documento com motor QPDF C++...', 65);

      let cleanName = organizeOutputFilename.value.trim() || 'documento_reorganizado';
      if (!cleanName.toLowerCase().endsWith('.pdf')) cleanName += '.pdf';

      const pageActions = state.organizeItems.map(item => ({
        page: item.origPage,
        rotation: item.rotation,
      }));

      const payload = {
        session_id: state.sessionId,
        file_id: state.activeDoc.serverSavedName,
        page_actions: pageActions,
        output_filename: cleanName,
        linearize: toggleOrganizeLinearize.checked,
      };

      updateProcessingStep(3, 'Aplicando Fast Web View e gravando saída...', 85);

      const res = await fetch('/api/organize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errJson = await res.json();
        throw new Error(errJson.detail || 'Erro ao organizar PDF.');
      }

      const data = await res.json();
      updateProgress(100, 'PDF reorganizado com sucesso!');
      await delay(300);

      showResultUI({
        title: 'Páginas Reorganizadas com Sucesso!',
        filename: data.output_filename,
        downloadUrl: data.download_url,
        previewUrl: data.preview_url,
        isZip: false,
        label1: 'Páginas Finais',
        val1: `${data.metrics.final_pages} págs`,
        label2: 'Páginas Originais',
        val2: `${data.metrics.total_source_pages} págs`,
        sizeBytes: data.metrics.output_bytes,
        durationSec: data.metrics.duration_seconds,
      });

    } catch (e) {
      console.error(e);
      showToast(e.message || 'Erro ao organizar páginas.', 'error');
      stopProcessingUI(stageOrganize);
    }
  }

  // =========================================================================
  // FERRAMENTA 4: GIRAR PÁGINAS (ROTATE)
  // =========================================================================
  function setupRotateEvents() {
    btnRotateChangeDoc.addEventListener('click', resetCurrentDocument);

    btnRotateAllCw.addEventListener('click', () => rotateAllPagesBy(90));
    btnRotateAllCcw.addEventListener('click', () => rotateAllPagesBy(270)); // -90 = 270
    btnRotateAll180.addEventListener('click', () => rotateAllPagesBy(180));

    btnRotateEvens.addEventListener('click', () => rotateFilteredPages(p => p % 2 === 0, 90));
    btnRotateOdds.addEventListener('click', () => rotateFilteredPages(p => p % 2 !== 0, 90));

    btnRotateReset.addEventListener('click', () => {
      state.rotateMap = {};
      updateRotateDisplay();
      showToast('Todas as rotações foram restauradas ao original.', 'info');
    });

    btnStartRotate.addEventListener('click', onExecuteRotate);
  }

  async function initRotateWorkspace() {
    if (!state.activeDoc) return;

    rotateDocName.textContent = state.activeDoc.name;
    rotateDocPages.textContent = state.activeDoc.pageCount;
    rotateDocSize.textContent = formatBytes(state.activeDoc.size);
    const baseStem = cleanFileNameToTitle(state.activeDoc.name);
    rotateOutputFilename.value = `${baseStem}_rotacionado`;

    state.rotateMap = {};
    updateRotateModifiedCounter();
    await renderRotateGrid();
  }

  function rotateAllPagesBy(degrees) {
    const totalP = state.activeDoc ? state.activeDoc.pageCount : 0;
    for (let p = 1; p <= totalP; p++) {
      const cur = state.rotateMap[p] || 0;
      state.rotateMap[p] = (cur + degrees) % 360;
    }
    updateRotateDisplay();
  }

  function rotateFilteredPages(filterFn, degrees) {
    const totalP = state.activeDoc ? state.activeDoc.pageCount : 0;
    let modified = 0;
    for (let p = 1; p <= totalP; p++) {
      if (filterFn(p)) {
        const cur = state.rotateMap[p] || 0;
        state.rotateMap[p] = (cur + degrees) % 360;
        modified++;
      }
    }
    updateRotateDisplay();
    showToast(`${modified} página(s) giradas em 90°.`, 'info');
  }

  function updateRotateModifiedCounter() {
    let count = 0;
    Object.values(state.rotateMap).forEach(angle => {
      if (angle % 360 !== 0) count++;
    });
    rotateModifiedLabel.textContent = `${count} página${count !== 1 ? 's' : ''}`;
  }

  function updateRotateDisplay() {
    updateRotateModifiedCounter();

    const totalP = state.activeDoc ? state.activeDoc.pageCount : 0;
    for (let p = 1; p <= totalP; p++) {
      const angle = (state.rotateMap[p] || 0) % 360;
      const card = rotateGrid.querySelector(`.page-card[data-page="${p}"]`);
      if (card) {
        const canvas = card.querySelector('.page-thumbnail-canvas');
        if (canvas) applyPageRotationStyle(canvas, angle);

        let badge = card.querySelector('.page-rotation-badge');
        if (angle !== 0) {
          if (!badge) {
            badge = document.createElement('span');
            badge.className = 'page-rotation-badge';
            card.querySelector('.page-card-preview-wrapper').appendChild(badge);
          }
          badge.textContent = `+${angle}°`;
        } else if (badge) {
          badge.remove();
        }
      }
    }
  }

  async function renderRotateGrid() {
    rotateGrid.innerHTML = '';
    rotateLoading.classList.add('active');

    const totalP = state.activeDoc ? state.activeDoc.pageCount : 0;

    for (let p = 1; p <= totalP; p++) {
      const card = document.createElement('div');
      card.className = 'page-card';
      card.dataset.page = p;

      const angle = (state.rotateMap[p] || 0) % 360;

      card.innerHTML = `
        <div class="page-card-header">
          <span class="page-badge-order">Pág. ${p}</span>
        </div>

        <div class="page-card-preview-wrapper">
          <canvas class="page-thumbnail-canvas" id="canvas-rot-${p}"></canvas>
          ${angle !== 0 ? `<span class="page-rotation-badge">+${angle}°</span>` : ''}
        </div>

        <div class="page-card-actions">
          <button type="button" class="card-action-btn btn-rot-left" title="Girar 90° anti-horário">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2.5 2v6h6M2.66 15.57a10 10 0 1 0 .57-8.38L-2.4 1.52"/></svg>
            <span style="font-size:0.75rem;margin-left:3px;">-90°</span>
          </button>
          <button type="button" class="card-action-btn btn-rot-right" title="Girar 90° horário">
            <span style="font-size:0.75rem;margin-right:3px;">+90°</span>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
          </button>
        </div>
      `;

      const canvas = card.querySelector(`#canvas-rot-${p}`);
      applyPageRotationStyle(canvas, angle);
      renderThumbnailPage(p, canvas);

      card.querySelector('.btn-rot-left').addEventListener('click', () => {
        const cur = state.rotateMap[p] || 0;
        state.rotateMap[p] = (cur + 270) % 360;
        updateRotateDisplay();
      });

      card.querySelector('.btn-rot-right').addEventListener('click', () => {
        const cur = state.rotateMap[p] || 0;
        state.rotateMap[p] = (cur + 90) % 360;
        updateRotateDisplay();
      });

      rotateGrid.appendChild(card);
    }

    rotateLoading.classList.remove('active');
  }

  async function onExecuteRotate() {
    if (!state.activeDoc) return;
    await ensureDocUploaded(state.activeDoc);

    startProcessingUI('Rotacionando páginas do PDF...', 'Aplicando ângulos com motor QPDF C++...');

    try {
      updateProcessingStep(1, 'Calculando mapa de rotação das páginas...', 30);
      await delay(200);

      updateProcessingStep(2, 'Rotacionando no nível binário sem re-rasterizar...', 65);

      let cleanName = rotateOutputFilename.value.trim() || 'documento_rotacionado';
      if (!cleanName.toLowerCase().endsWith('.pdf')) cleanName += '.pdf';

      const payload = {
        session_id: state.sessionId,
        file_id: state.activeDoc.serverSavedName,
        page_rotations: state.rotateMap,
        output_filename: cleanName,
        linearize: toggleRotateLinearize.checked,
      };

      updateProcessingStep(3, 'Linearizando e salvando saída...', 85);

      const res = await fetch('/api/rotate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errJson = await res.json();
        throw new Error(errJson.detail || 'Erro ao rotacionar PDF.');
      }

      const data = await res.json();
      updateProgress(100, 'Páginas rotacionadas com sucesso!');
      await delay(300);

      showResultUI({
        title: 'Páginas Rotacionadas com Sucesso!',
        filename: data.output_filename,
        downloadUrl: data.download_url,
        previewUrl: data.preview_url,
        isZip: false,
        label1: 'Páginas Rotacionadas',
        val1: `${data.metrics.pages_rotated} págs`,
        label2: 'Total de Páginas',
        val2: `${data.metrics.total_pages} págs`,
        sizeBytes: data.metrics.output_bytes,
        durationSec: data.metrics.duration_seconds,
      });

    } catch (e) {
      console.error(e);
      showToast(e.message || 'Erro ao rotacionar páginas.', 'error');
      stopProcessingUI(stageRotate);
    }
  }

  // =========================================================================
  // FERRAMENTA 5: EXTRAIR PÁGINAS (EXTRACT)
  // =========================================================================
  function setupExtractEvents() {
    btnExtractChangeDoc.addEventListener('click', resetCurrentDocument);

    btnExtractAll.addEventListener('click', () => {
      const totalP = state.activeDoc ? state.activeDoc.pageCount : 0;
      state.extractSelected.clear();
      for (let p = 1; p <= totalP; p++) state.extractSelected.add(p);
      syncExtractUIFromSet();
    });

    btnExtractNone.addEventListener('click', () => {
      state.extractSelected.clear();
      syncExtractUIFromSet();
    });

    btnExtractInvert.addEventListener('click', () => {
      const totalP = state.activeDoc ? state.activeDoc.pageCount : 0;
      for (let p = 1; p <= totalP; p++) {
        if (state.extractSelected.has(p)) {
          state.extractSelected.delete(p);
        } else {
          state.extractSelected.add(p);
        }
      }
      syncExtractUIFromSet();
    });

    btnExtractEvens.addEventListener('click', () => {
      const totalP = state.activeDoc ? state.activeDoc.pageCount : 0;
      state.extractSelected.clear();
      for (let p = 2; p <= totalP; p += 2) state.extractSelected.add(p);
      syncExtractUIFromSet();
    });

    btnExtractOdds.addEventListener('click', () => {
      const totalP = state.activeDoc ? state.activeDoc.pageCount : 0;
      state.extractSelected.clear();
      for (let p = 1; p <= totalP; p += 2) state.extractSelected.add(p);
      syncExtractUIFromSet();
    });

    // Input manual de intervalos
    extractRangesInput.addEventListener('input', () => {
      const totalP = state.activeDoc ? state.activeDoc.pageCount : 100;
      const parsed = parseRangesToSet(extractRangesInput.value, totalP);
      state.extractSelected = parsed;
      syncGridSelectionFromSet();
      updateExtractSelectedCounter();
    });

    btnStartExtract.addEventListener('click', onExecuteExtract);
  }

  async function initExtractWorkspace() {
    if (!state.activeDoc) return;

    extractDocName.textContent = state.activeDoc.name;
    extractDocPages.textContent = state.activeDoc.pageCount;
    extractDocSize.textContent = formatBytes(state.activeDoc.size);
    const baseStem = cleanFileNameToTitle(state.activeDoc.name);
    extractOutputFilename.value = `${baseStem}_extraidas`;

    // Seleciona a página 1 por padrão
    state.extractSelected.clear();
    state.extractSelected.add(1);

    syncExtractUIFromSet();
    await renderExtractGrid();
  }

  function syncExtractUIFromSet() {
    const arr = Array.from(state.extractSelected).sort((a, b) => a - b);
    extractRangesInput.value = formatPagesToRanges(arr);
    syncGridSelectionFromSet();
    updateExtractSelectedCounter();
  }

  function syncGridSelectionFromSet() {
    const cards = extractGrid.querySelectorAll('.page-card');
    cards.forEach(card => {
      const p = parseInt(card.dataset.page, 10);
      if (state.extractSelected.has(p)) {
        card.classList.add('selected');
      } else {
        card.classList.remove('selected');
      }
    });
  }

  function updateExtractSelectedCounter() {
    const count = state.extractSelected.size;
    const total = state.activeDoc ? state.activeDoc.pageCount : 0;
    extractSelectedLabel.textContent = `${count} de ${total} página${count !== 1 ? 's' : ''} selecionada${count !== 1 ? 's' : ''}`;
  }

  async function renderExtractGrid() {
    extractGrid.innerHTML = '';
    extractLoading.classList.add('active');

    const totalP = state.activeDoc ? state.activeDoc.pageCount : 0;

    for (let p = 1; p <= totalP; p++) {
      const card = document.createElement('div');
      card.className = 'page-card page-card-selectable' + (state.extractSelected.has(p) ? ' selected' : '');
      card.dataset.page = p;

      card.innerHTML = `
        <div class="page-select-checkbox">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
        </div>

        <div class="page-card-header" style="padding-left: 2rem;">
          <span class="page-badge-order">Pág. ${p}</span>
        </div>

        <div class="page-card-preview-wrapper">
          <canvas class="page-thumbnail-canvas" id="canvas-ext-${p}"></canvas>
        </div>
      `;

      card.addEventListener('click', () => {
        if (state.extractSelected.has(p)) {
          state.extractSelected.delete(p);
        } else {
          state.extractSelected.add(p);
        }
        syncExtractUIFromSet();
      });

      const canvas = card.querySelector(`#canvas-ext-${p}`);
      renderThumbnailPage(p, canvas);

      extractGrid.appendChild(card);
    }

    extractLoading.classList.remove('active');
  }

  async function onExecuteExtract() {
    if (!state.activeDoc) return;
    if (state.extractSelected.size === 0) {
      showToast('Selecione pelo menos uma página para extrair.', 'error');
      return;
    }

    await ensureDocUploaded(state.activeDoc);

    const modeInput = document.querySelector('input[name="extract-mode"]:checked');
    const extractMode = modeInput ? modeInput.value : 'merge';

    startProcessingUI('Extraindo páginas do PDF...', 'Isolando conteúdo com motor QPDF C++...');

    try {
      updateProcessingStep(1, 'Compilando páginas selecionadas...', 30);
      await delay(200);

      updateProcessingStep(2, extractMode === 'merge' ? 'Gerando PDF único enxuto...' : 'Criando PDFs individuais para empacotamento ZIP...', 65);

      const baseName = extractOutputFilename.value.trim() || 'paginas_extraidas';
      const sortedPages = Array.from(state.extractSelected).sort((a, b) => a - b);

      const payload = {
        session_id: state.sessionId,
        file_id: state.activeDoc.serverSavedName,
        selected_pages: sortedPages,
        mode: extractMode,
        output_filename: baseName,
        linearize: toggleExtractLinearize.checked,
      };

      updateProcessingStep(3, 'Finalizando compressão e links...', 85);

      const res = await fetch('/api/extract', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errJson = await res.json();
        throw new Error(errJson.detail || 'Erro ao extrair páginas.');
      }

      const data = await res.json();
      updateProgress(100, 'Extração de páginas concluída com sucesso!');
      await delay(300);

      showResultUI({
        title: 'Páginas Extraídas com Sucesso!',
        filename: data.output_filename,
        downloadUrl: data.download_url,
        previewUrl: data.preview_url,
        isZip: data.is_zip,
        label1: 'Páginas Extraídas',
        val1: `${data.metrics.extracted_pages_count} págs`,
        label2: 'Arquivos Gerados',
        val2: `${data.metrics.files_count} arquivo(s)`,
        sizeBytes: data.metrics.output_bytes,
        durationSec: data.metrics.duration_seconds,
      });

    } catch (e) {
      console.error(e);
      showToast(e.message || 'Erro ao extrair páginas.', 'error');
      stopProcessingUI(stageExtract);
    }
  }

  // =========================================================================
  // RENDERIZAÇÃO DE MINIATURAS VIA PDF.JS
  // =========================================================================
  async function renderThumbnailPage(pageNum, canvas) {
    if (!state.activeDoc || !state.activeDoc.pdfDoc || !canvas) return;

    const cacheKey = `${state.activeDoc.name}_p${pageNum}`;
    if (thumbnailCache.has(cacheKey)) {
      const cached = thumbnailCache.get(cacheKey);
      canvas.width = cached.width;
      canvas.height = cached.height;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(cached.image, 0, 0);
      return;
    }

    try {
      const page = await state.activeDoc.pdfDoc.getPage(pageNum);
      const viewport = page.getViewport({ scale: 0.35 });
      canvas.width = viewport.width;
      canvas.height = viewport.height;
      const ctx = canvas.getContext('2d');

      await page.render({
        canvasContext: ctx,
        viewport: viewport
      }).promise;

      // Salva no cache
      createImageBitmap(canvas).then(bitmap => {
        thumbnailCache.set(cacheKey, { image: bitmap, width: canvas.width, height: canvas.height });
      }).catch(() => {});

    } catch (err) {
      console.warn(`Erro ao renderizar miniatura da página ${pageNum}:`, err);
    }
  }

  function applyPageRotationStyle(element, rotationAngle) {
    if (!element) return;
    const angle = (rotationAngle || 0) % 360;
    element.style.transform = `rotate(${angle}deg)`;
  }

  // =========================================================================
  // FLUXO DE PROCESSAMENTO E RESULTADO COMPARTILHADOS
  // =========================================================================
  function startProcessingUI(title, subtitle) {
    state.isProcessing = true;
    document.querySelectorAll('.tool-stage').forEach(el => el.classList.add('hidden'));
    dropzone.classList.add('hidden');
    resultStage.classList.add('hidden');

    processingTitle.textContent = title;
    processingDesc.textContent = subtitle;
    progressFill.style.width = '10%';
    progressPct.textContent = '10%';
    processingStage.classList.remove('hidden');

    // Reseta bullets
    for (let i = 1; i <= 4; i++) {
      const s = document.getElementById(`step-${i}`);
      if (s) {
        s.className = 'step-item';
        s.querySelector('.step-bullet').textContent = '•';
      }
    }
  }

  function updateProgress(percent, subtitle) {
    progressFill.style.width = `${percent}%`;
    progressPct.textContent = `${percent}%`;
    if (subtitle) processingDesc.textContent = subtitle;
  }

  function updateProcessingStep(stepNum, message, percent) {
    updateProgress(percent, message);
    for (let i = 1; i <= 4; i++) {
      const s = document.getElementById(`step-${i}`);
      if (s) {
        if (i < stepNum) {
          s.className = 'step-item step-completed';
          s.querySelector('.step-bullet').textContent = '✓';
        } else if (i === stepNum) {
          s.className = 'step-item step-active';
          s.querySelector('.step-bullet').textContent = '⚙';
        } else {
          s.className = 'step-item';
          s.querySelector('.step-bullet').textContent = '•';
        }
      }
    }
  }

  function stopProcessingUI(fallbackStage) {
    state.isProcessing = false;
    processingStage.classList.add('hidden');
    if (fallbackStage) fallbackStage.classList.remove('hidden');
  }

  function showResultUI(opts) {
    state.isProcessing = false;
    processingStage.classList.add('hidden');
    resultStage.classList.remove('hidden');

    state.downloadUrl = opts.downloadUrl;
    state.previewUrl = opts.previewUrl;
    state.outputFilename = opts.filename;
    state.isZipResult = opts.isZip;

    resultStatusTitle.textContent = opts.title;
    resultFilenameDisplay.textContent = opts.filename;

    metricLabel1.textContent = opts.label1;
    metricFiles.textContent = opts.val1;
    metricLabel2.textContent = opts.label2;
    metricPages.textContent = opts.val2;
    metricSize.textContent = formatBytes(opts.sizeBytes);
    metricTime.textContent = `${opts.durationSec}s`;

    btnDownload.href = opts.downloadUrl;
    btnDownload.setAttribute('download', opts.filename);
    btnDownloadText.textContent = opts.isZip ? 'Baixar Arquivos (.ZIP)' : 'Baixar Documento (.PDF)';

    if (opts.isZip || !opts.previewUrl) {
      btnPreview.style.display = 'none';
    } else {
      btnPreview.style.display = 'inline-flex';
    }

    showToast(opts.title, 'success');
  }

  // =========================================================================
  // UPLOADS E UTILITÁRIOS DE REDE
  // =========================================================================
  async function ensureDocUploaded(docObj) {
    if (docObj.serverSavedName) return;

    const formData = new FormData();
    formData.append('session_id', state.sessionId);
    formData.append('files', docObj.fileObj, docObj.name);

    const res = await fetchWithProgress('/api/upload', formData, (pct) => {
      updateProgress(10 + Math.round(pct * 0.2), `Enviando arquivo ao servidor... (${pct}%)`);
    });

    if (!res.success || !res.files || res.files.length === 0) {
      throw new Error(res.detail || 'Falha no upload do arquivo.');
    }

    docObj.serverSavedName = res.files[0].saved_filename;
    docObj.pageCount = res.files[0].page_count || docObj.pageCount;
  }

  async function ensureFilesUploaded(filesArray) {
    const unuploaded = filesArray.filter(f => !f.isUploaded);
    if (unuploaded.length === 0) return;

    const formData = new FormData();
    formData.append('session_id', state.sessionId);
    unuploaded.forEach(f => formData.append('files', f.fileObj, f.name));

    const res = await fetchWithProgress('/api/upload', formData, (pct) => {
      updateProgress(10 + Math.round(pct * 0.35), `Transferindo ${unuploaded.length} arquivos... (${pct}%)`);
    });

    if (!res.success) {
      throw new Error(res.detail || 'Falha no upload dos arquivos.');
    }

    res.files.forEach(serverFile => {
      const match = filesArray.find(f => f.name === serverFile.name && !f.serverSavedName);
      if (match) {
        match.serverSavedName = serverFile.saved_filename;
        match.pageCount = serverFile.page_count;
        match.isUploaded = true;
      }
    });
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

  // =========================================================================
  // MODAL DE PRÉ-VISUALIZAÇÃO & BOTÕES DE PIX
  // =========================================================================
  function setupModalAndPix() {
    btnPreview.addEventListener('click', () => {
      if (state.previewUrl && !state.isZipResult) {
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

    btnReset.addEventListener('click', () => {
      resultStage.classList.add('hidden');
      if (state.activeTool === 'merge') {
        stageMerge.classList.remove('hidden');
      } else {
        const stageId = TOOL_CONFIGS[state.activeTool].stageId;
        const stageEl = document.getElementById(stageId);
        if (stageEl) stageEl.classList.remove('hidden');
      }
    });

    // Botões PIX
    const btnCopyPixKey = document.getElementById('btn-copy-pix-key');
    const pixKeyInput = document.getElementById('pix-key-input');
    if (btnCopyPixKey && pixKeyInput) {
      btnCopyPixKey.addEventListener('click', () => {
        copyToClipboard(pixKeyInput.value, 'Chave PIX copiada! Muito obrigado pelo apoio ao projeto.');
      });
    }

    const btnCopyPixPayload = document.getElementById('btn-copy-pix-payload');
    const pixPayloadInput = document.getElementById('pix-payload-input');
    if (btnCopyPixPayload && pixPayloadInput) {
      btnCopyPixPayload.addEventListener('click', () => {
        copyToClipboard(pixPayloadInput.value, 'Código PIX Copia e Cola copiado com sucesso!');
      });
    }
  }

  // =========================================================================
  // HELPERS (TOAST, PARSING DE INTERVALOS, FORMATAÇÃO)
  // =========================================================================
  function parseRangesToSet(rangeStr, maxPages) {
    const set = new Set();
    const tokens = rangeStr.split(',').map(s => s.trim()).filter(Boolean);

    tokens.forEach(tok => {
      const matchRange = tok.match(/^(\d+)\s*-\s*(\d+)$/);
      if (matchRange) {
        let s = parseInt(matchRange[1], 10);
        let e = parseInt(matchRange[2], 10);
        if (s > e) [s, e] = [e, s];
        for (let p = Math.max(1, s); p <= Math.min(e, maxPages); p++) {
          set.add(p);
        }
      } else {
        const matchSingle = tok.match(/^(\d+)$/);
        if (matchSingle) {
          const p = parseInt(matchSingle[1], 10);
          if (p >= 1 && p <= maxPages) set.add(p);
        }
      }
    });

    return set;
  }

  function formatPagesToRanges(sortedArr) {
    if (!sortedArr || sortedArr.length === 0) return '';
    const ranges = [];
    let start = sortedArr[0];
    let end = sortedArr[0];

    for (let i = 1; i < sortedArr.length; i++) {
      if (sortedArr[i] === end + 1) {
        end = sortedArr[i];
      } else {
        ranges.push(start === end ? `${start}` : `${start}-${end}`);
        start = end = sortedArr[i];
      }
    }
    ranges.push(start === end ? `${start}` : `${start}-${end}`);
    return ranges.join(', ');
  }

  function cleanFileNameToTitle(filename) {
    return filename.replace(/\.[^/.]+$/, '').replace(/[_-]/g, ' ').trim();
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

  function copyToClipboard(text, successMsg) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text)
        .then(() => showToast(successMsg, 'success'))
        .catch(() => fallbackCopyText(text, successMsg));
    } else {
      fallbackCopyText(text, successMsg);
    }
  }

  function fallbackCopyText(text, successMsg) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-9999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    try {
      document.execCommand('copy');
      showToast(successMsg, 'success');
    } catch (err) {
      showToast('Selecione e copie o texto manualmente.', 'error');
    }
    document.body.removeChild(textArea);
  }

})();
