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
    protect: {
      heroTitle: 'Proteja seu PDF com Senha e Criptografia AES-256',
      heroSub: 'Criptografia militar de alta segurança (AES-128 / AES-256 bits). Bloqueie impressões, cópias de texto e alterações não autorizadas com restrições granulares de permissão.',
      dropHeading: 'Arraste o arquivo PDF que deseja proteger com senha',
      dropSub: 'ou clique para selecionar do computador',
      dropBadges: ['Criptografia AES-256 / AES-128', 'Bloqueio de cópia e impressão', 'Senhas de usuário e mestre'],
      multiple: false,
      enginePill: 'Criptografia QPDF Ativa',
      stageId: 'stage-protect',
    },
    unlock: {
      heroTitle: 'Desproteja e Remova Restrições do seu PDF',
      heroSub: 'Elimine senhas e bloqueios de permissão (impressão, cópia, edição) de documentos conhecidos pelo usuário, gerando uma versão livre e editável.',
      dropHeading: 'Arraste o arquivo PDF protegido',
      dropSub: 'ou clique para selecionar do computador',
      dropBadges: ['Desbloqueio de permissões instantâneo', 'Remoção de senha de abertura', 'Saída limpa e desprotegida'],
      multiple: false,
      enginePill: 'Desbloqueador QPDF Ativo',
      stageId: 'stage-unlock',
    },
    redact: {
      heroTitle: 'Anonimize e Tarje Dados Sensíveis Irreversivelmente',
      heroSub: 'Expurgo físico permanente sob as tarjas: elimine CPF, CNPJ, e-mails, telefones, cartões e palavras-chave. Higienização total de metadados ocultos e XMP (LGPD e sigilo).',
      dropHeading: 'Arraste o arquivo PDF para tarjar e anonimizar',
      dropSub: 'ou clique para selecionar do computador',
      dropBadges: ['Tarjas físicas permanentes (LGPD)', 'Filtro automático de CPF, e-mail e fone', 'Expurgo de metadados XMP ocultos'],
      multiple: false,
      enginePill: 'Anonimizador PyMuPDF Ativo',
      stageId: 'stage-redact',
    },
    'pdf-to-word': {
      heroTitle: 'Converta Documentos PDF para Microsoft Word (.docx)',
      heroSub: 'Reconstrução de tabelas, fontes, parágrafos e imagens para um documento DOCX 100% editável com fidelidade estrutural.',
      dropHeading: 'Arraste o arquivo PDF para converter em Word',
      dropSub: 'ou clique para selecionar do computador',
      dropBadges: ['Word 100% editável (.docx)', 'Reconstrução de tabelas e estilos', 'Conversão total ou por páginas'],
      multiple: false,
      enginePill: 'Conversor PDF2DOCX Ativo',
      stageId: 'stage-pdf-to-word',
    },
    'word-to-pdf': {
      heroTitle: 'Converta Arquivos Word (.docx, .doc) para PDF',
      heroSub: 'Conversão de alta fidelidade com motor dual (LibreOffice + Python Fallback), gerando PDF padronizado para impressão e envio seguro.',
      dropHeading: 'Arraste seu documento Word (.docx ou .doc) aqui',
      dropSub: 'ou clique para selecionar do computador',
      dropBadges: ['Suporte a .docx e .doc', 'Formatação e paginação preservadas', 'Otimização com Fast Web View'],
      multiple: false,
      enginePill: 'Conversor Word2PDF Ativo',
      stageId: 'stage-word-to-pdf',
    },
    'image-to-pdf': {
      heroTitle: 'Converta Imagens para Documentos PDF',
      heroSub: 'Converta fotos e ilustrações (JPG, PNG, WebP, TIFF) em um arquivo PDF estruturado. Ajuste a ordem das páginas, tamanho da folha (A4, Carta ou Ajustar à Imagem), orientação e margens.',
      dropHeading: 'Arraste suas imagens aqui (múltiplas)',
      dropSub: 'ou clique para selecionar fotos e ilustrações do computador',
      dropBadges: ['Suporte a JPG, PNG, WebP e TIFF', 'Ajuste de margens e orientação', 'Reordenação interativa das fotos'],
      multiple: true,
      enginePill: 'Conversor Img2PDF Ativo',
      stageId: 'stage-image-to-pdf',
    },
    watermark: {
      heroTitle: 'Insira Marca d\'água em Arquivos PDF',
      heroSub: 'Proteja seus documentos adicionando carimbos de confidencialidade, cópias controladas, textos personalizados ou logotipos com transparência, rotação e repetição em grade.',
      dropHeading: 'Arraste o arquivo PDF que receberá a marca d\'água',
      dropSub: 'ou clique para selecionar do computador',
      dropBadges: ['Texto ou logotipo com transparência', 'Mosaico anti-cópia em toda a página', 'Camada frente (overlay) ou fundo'],
      multiple: false,
      enginePill: 'Carimbador QPDF Ativo',
      stageId: 'stage-watermark',
    },
    footer: {
      heroTitle: 'Personalize o Rodapé, Cabeçalho e Numeração do PDF',
      heroSub: 'Adicione rodapé, cabeçalho institucional, texto personalizado ou numeração de páginas (ex: Página 1 de 10) com estamparia vetorial em alta resolução.',
      dropHeading: 'Arraste o arquivo PDF que receberá o rodapé ou numeração',
      dropSub: 'ou clique para selecionar do computador',
      dropBadges: ['Numeração de páginas ({page} de {total})', 'Rodapé ou Cabeçalho com alinhamento', 'Cores e fontes vetoriais customizadas'],
      multiple: false,
      enginePill: 'Estampador Vetorial Ativo',
      stageId: 'stage-footer',
    },
    'remove-footer': {
      heroTitle: 'Remova Rodapés, Cabeçalhos e Numeração do PDF',
      heroSub: 'Elimine fisicamente textos de rodapé, marcas indesejadas, numeração de páginas ou corte faixas de margem com expurgo vetorial irreversível.',
      dropHeading: 'Arraste o arquivo PDF para remover rodapé ou cabeçalho',
      dropSub: 'ou clique para selecionar do computador',
      dropBadges: ['Expurgo físico por margem', 'Remoção cirúrgica de textos específicos', 'Detecção automática de numeração'],
      multiple: false,
      enginePill: 'Expurgador QPDF Ativo',
      stageId: 'stage-remove-footer',
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
    isDocxResult: false,

    // Juntar PDF
    mergeFiles: [], // { id, name, menuTitle, size, pageCount, fileObj, isUploaded, serverSavedName }

    // Imagem para PDF
    imageFiles: [], // { id, name, size, fileObj, isUploaded, serverSavedName, previewUrl }

    // Ferramentas de 1 Documento
    activeDoc: null, // { name, size, pageCount, serverSavedName, fileObj, pdfDoc }

    // Marca d'água (imagem opcional)
    watermarkImageDoc: null, // { name, size, fileObj, serverSavedName, previewUrl }

    // Organizar
    organizeItems: [], // [ { uid, origPage, rotation: 0, canvas: canvasEl } ]
    draggedOrganizeIdx: null,

    // Girar
    rotateMap: {}, // { [pageNum: number]: rotationAngle: number }

    // Extrair
    extractSelected: new Set(), // Set<number> (1-based)

    // Redigir / Anonimizar
    redactCustomTerms: [],
  };

  // Cache de miniaturas geradas
  const thumbnailCache = new Map();

  // Elementos do DOM Compartilhados
  // Elementos da Barra de Navegação com Menus Suspensos por Categoria
  const categoryNavBar = document.getElementById('category-nav-bar');
  const navActiveToolTitle = document.getElementById('nav-active-tool-title');
  const btnOpenAllTools = document.getElementById('btn-open-all-tools');

  const allToolsModal = document.getElementById('all-tools-modal');
  const btnCloseAllToolsModal = document.getElementById('btn-close-all-tools-modal');
  const btnCloseAllToolsFooter = document.getElementById('btn-close-all-tools-footer');
  const allToolsSearchInput = document.getElementById('all-tools-search-input');
  const btnClearToolsSearch = document.getElementById('btn-clear-tools-search');
  const toolsSearchEmpty = document.getElementById('tools-search-empty');

  const TOOL_CATEGORIES = {
    merge: 'pages',
    split: 'pages',
    organize: 'pages',
    rotate: 'pages',
    extract: 'pages',

    footer: 'edit',
    'remove-footer': 'edit',
    watermark: 'edit',

    protect: 'security',
    unlock: 'security',
    redact: 'security',

    'pdf-to-word': 'convert',
    'word-to-pdf': 'convert',
    'image-to-pdf': 'convert',
  };

  const TOOL_SHORT_NAMES = {
    merge: 'Juntar PDF',
    split: 'Dividir PDF',
    organize: 'Organizar Páginas',
    rotate: 'Girar Páginas',
    extract: 'Extrair Páginas',
    protect: 'Proteger PDF',
    unlock: 'Desproteger PDF',
    redact: 'Tarjar & Anonimizar',
    'pdf-to-word': 'PDF para Word',
    'word-to-pdf': 'Word para PDF',
    'image-to-pdf': 'Imagem para PDF',
    watermark: 'Marca d\'água',
    footer: 'Rodapé & Numeração',
    'remove-footer': 'Remover Rodapé',
  };

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

  // Elementos do Modal da Lupa de Páginas (Zoom Inspector)
  const pageZoomModal = document.getElementById('page-zoom-modal');
  const zoomPageBadge = document.getElementById('zoom-page-badge');
  const zoomLevelLabel = document.getElementById('zoom-level-label');
  const btnZoomIn = document.getElementById('btn-zoom-in');
  const btnZoomOut = document.getElementById('btn-zoom-out');
  const btnZoomFit = document.getElementById('btn-zoom-fit');
  const btnZoomRot = document.getElementById('btn-zoom-rot');
  const btnCloseZoomModal = document.getElementById('btn-close-zoom-modal');
  const btnZoomCloseFooter = document.getElementById('btn-zoom-close-footer');
  const btnZoomPrevPage = document.getElementById('btn-zoom-prev-page');
  const btnZoomNextPage = document.getElementById('btn-zoom-next-page');
  const zoomCanvasContainer = document.getElementById('zoom-canvas-container');
  const zoomLoadingIndicator = document.getElementById('zoom-loading-indicator');
  const zoomPageCanvas = document.getElementById('zoom-page-canvas');

  // Estado da Lupa de Páginas
  const zoomState = {
    isOpen: false,
    currentPage: 1,
    zoomScale: 1.0,
    rotation: 0,
    activeItemRef: null,
    sourceContext: null, // 'organize', 'rotate', 'extract'
    renderTask: null,
  };

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
  const mergeFooterTextInput = document.getElementById('merge-footer-text');

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

  // Elementos Proteger PDF
  const stageProtect = document.getElementById('stage-protect');
  const protectDocName = document.getElementById('protect-doc-name');
  const protectDocPages = document.getElementById('protect-doc-pages');
  const protectDocSize = document.getElementById('protect-doc-size');
  const btnProtectChangeDoc = document.getElementById('btn-protect-change-doc');
  const protectUserPwd = document.getElementById('protect-user-pwd');
  const protectOwnerPwd = document.getElementById('protect-owner-pwd');
  const pwdMeterBar = document.getElementById('pwd-meter-bar');
  const pwdMeterText = document.getElementById('pwd-meter-text');
  const toggleAllowPrint = document.getElementById('toggle-allow-print');
  const toggleAllowCopy = document.getElementById('toggle-allow-copy');
  const toggleAllowModify = document.getElementById('toggle-allow-modify');
  const toggleAllowAnnotate = document.getElementById('toggle-allow-annotate');
  const protectOutputFilename = document.getElementById('protect-output-filename');
  const toggleProtectLinearize = document.getElementById('toggle-protect-linearize');
  const btnStartProtect = document.getElementById('btn-start-protect');

  // Elementos Desproteger PDF
  const stageUnlock = document.getElementById('stage-unlock');
  const unlockDocName = document.getElementById('unlock-doc-name');
  const unlockDocPages = document.getElementById('unlock-doc-pages');
  const unlockDocSize = document.getElementById('unlock-doc-size');
  const btnUnlockChangeDoc = document.getElementById('btn-unlock-change-doc');
  const unlockPassword = document.getElementById('unlock-password');
  const unlockOutputFilename = document.getElementById('unlock-output-filename');
  const toggleUnlockLinearize = document.getElementById('toggle-unlock-linearize');
  const btnStartUnlock = document.getElementById('btn-start-unlock');

  // Elementos Redigir / Anonimizar PDF
  const stageRedact = document.getElementById('stage-redact');
  const redactDocName = document.getElementById('redact-doc-name');
  const redactDocPages = document.getElementById('redact-doc-pages');
  const redactDocSize = document.getElementById('redact-doc-size');
  const btnRedactChangeDoc = document.getElementById('btn-redact-change-doc');
  const presetCpf = document.getElementById('preset-cpf');
  const presetCnpj = document.getElementById('preset-cnpj');
  const presetEmail = document.getElementById('preset-email');
  const presetPhone = document.getElementById('preset-phone');
  const presetCard = document.getElementById('preset-card');
  const redactCustomTermInput = document.getElementById('redact-custom-term-input');
  const btnAddRedactTerm = document.getElementById('btn-add-redact-term');
  const redactTermsContainer = document.getElementById('redact-terms-container');
  const toggleCleanMetadata = document.getElementById('toggle-clean-metadata');
  const redactOutputFilename = document.getElementById('redact-output-filename');
  const toggleRedactLinearize = document.getElementById('toggle-redact-linearize');
  const btnStartRedact = document.getElementById('btn-start-redact');

  // Elementos PDF para Word (.docx)
  const stagePdfToWord = document.getElementById('stage-pdf-to-word');
  const p2wDocName = document.getElementById('p2w-doc-name');
  const p2wDocPages = document.getElementById('p2w-doc-pages');
  const p2wDocSize = document.getElementById('p2w-doc-size');
  const btnP2wChangeDoc = document.getElementById('btn-p2w-change-doc');
  const p2wModeAll = document.getElementById('p2w-mode-all');
  const p2wModeRange = document.getElementById('p2w-mode-range');
  const p2wRangeInputsBox = document.getElementById('p2w-range-inputs-box');
  const p2wStartPage = document.getElementById('p2w-start-page');
  const p2wEndPage = document.getElementById('p2w-end-page');
  const p2wOutputFilename = document.getElementById('p2w-output-filename');
  const btnStartP2w = document.getElementById('btn-start-p2w');

  // Elementos Word para PDF (.pdf)
  const stageWordToPdf = document.getElementById('stage-word-to-pdf');
  const w2pDocName = document.getElementById('w2p-doc-name');
  const w2pDocPages = document.getElementById('w2p-doc-pages');
  const w2pDocSize = document.getElementById('w2p-doc-size');
  const btnW2pChangeDoc = document.getElementById('btn-w2p-change-doc');
  const w2pOutputFilename = document.getElementById('w2p-output-filename');
  const toggleW2pLinearize = document.getElementById('toggle-w2p-linearize');
  const btnStartW2p = document.getElementById('btn-start-w2p');

  // Elementos Imagem para PDF (.pdf)
  const stageImageToPdf = document.getElementById('stage-image-to-pdf');
  const i2pFilesCounter = document.getElementById('i2p-files-counter');
  const i2pFileList = document.getElementById('i2p-file-list');
  const btnI2pAddMore = document.getElementById('btn-i2p-add-more');
  const btnI2pClearAll = document.getElementById('btn-i2p-clear-all');
  const i2pOutputFilename = document.getElementById('i2p-output-filename');
  const toggleI2pLinearize = document.getElementById('toggle-i2p-linearize');
  const i2pTotalSizeLabel = document.getElementById('i2p-total-size-label');
  const btnStartI2p = document.getElementById('btn-start-i2p');

  // Elementos Marca d'água (.pdf)
  const stageWatermark = document.getElementById('stage-watermark');
  const wmDocName = document.getElementById('wm-doc-name');
  const wmDocPages = document.getElementById('wm-doc-pages');
  const wmDocSize = document.getElementById('wm-doc-size');
  const btnWmChangeDoc = document.getElementById('btn-wm-change-doc');
  const wmTypeText = document.getElementById('wm-type-text');
  const wmTypeImage = document.getElementById('wm-type-image');
  const wmTextControls = document.getElementById('wm-text-controls');
  const wmImageControls = document.getElementById('wm-image-controls');
  const wmTextInput = document.getElementById('wm-text-input');
  const wmFontSize = document.getElementById('wm-font-size');
  const wmFontSizeVal = document.getElementById('wm-font-size-val');
  const wmFontColor = document.getElementById('wm-font-color');
  const wmColorPreviewVal = document.getElementById('wm-color-preview-val');
  const wmImgFileInput = document.getElementById('wm-img-file-input');
  const wmImgUploadPrompt = document.getElementById('wm-img-upload-prompt');
  const wmImgPreviewBox = document.getElementById('wm-img-preview-box');
  const wmImgPreview = document.getElementById('wm-img-preview');
  const wmImgName = document.getElementById('wm-img-name');
  const btnWmRemoveImg = document.getElementById('btn-wm-remove-img');
  const wmImageScale = document.getElementById('wm-image-scale');
  const wmScaleVal = document.getElementById('wm-scale-val');
  const wmOpacity = document.getElementById('wm-opacity');
  const wmOpacityVal = document.getElementById('wm-opacity-val');
  const wmRotation = document.getElementById('wm-rotation');
  const wmPosition = document.getElementById('wm-position');
  const wmLayer = document.getElementById('wm-layer');
  const wmPagesSelect = document.getElementById('wm-pages-select');
  const wmCustomPagesBox = document.getElementById('wm-custom-pages-box');
  const wmCustomPagesInput = document.getElementById('wm-custom-pages-input');
  const wmOutputFilename = document.getElementById('wm-output-filename');
  const toggleWmLinearize = document.getElementById('toggle-wm-linearize');
  const btnStartWatermark = document.getElementById('btn-start-watermark');

  // Elementos Personalizar Rodapé (.pdf)
  const stageFooter = document.getElementById('stage-footer');
  const footerDocName = document.getElementById('footer-doc-name');
  const footerDocPages = document.getElementById('footer-doc-pages');
  const footerDocSize = document.getElementById('footer-doc-size');
  const btnFooterChangeDoc = document.getElementById('btn-footer-change-doc');
  const footerPositionSelect = document.getElementById('footer-position-select');
  const footerAlignmentSelect = document.getElementById('footer-alignment-select');
  const footerTextInput = document.getElementById('footer-text-input');
  const footerFontSize = document.getElementById('footer-font-size');
  const footerFontSizeVal = document.getElementById('footer-font-size-val');
  const footerMarginOffset = document.getElementById('footer-margin-offset');
  const footerMarginVal = document.getElementById('footer-margin-val');
  const footerFontColor = document.getElementById('footer-font-color');
  const footerColorVal = document.getElementById('footer-color-val');
  const footerStartNum = document.getElementById('footer-start-num');
  const toggleFooterSkipFirst = document.getElementById('toggle-footer-skip-first');
  const footerOutputFilename = document.getElementById('footer-output-filename');
  const toggleFooterLinearize = document.getElementById('toggle-footer-linearize');
  const footerSummaryLabel = document.getElementById('footer-summary-label');
  const btnStartFooter = document.getElementById('btn-start-footer');
  const footerPreviewSheet = document.getElementById('footer-preview-sheet');
  const footerPreviewHeaderSlot = document.getElementById('footer-preview-header-slot');
  const footerPreviewFooterSlot = document.getElementById('footer-preview-footer-slot');

  // Elementos Remover Rodapé (.pdf)
  const stageRemoveFooter = document.getElementById('stage-remove-footer');
  const rfDocName = document.getElementById('rf-doc-name');
  const rfDocPages = document.getElementById('rf-doc-pages');
  const rfDocSize = document.getElementById('rf-doc-size');
  const btnRfChangeDoc = document.getElementById('btn-rf-change-doc');
  const rfModeMargin = document.getElementById('rf-mode-margin');
  const rfModeText = document.getElementById('rf-mode-text');
  const rfMarginControls = document.getElementById('rf-margin-controls');
  const rfTextControls = document.getElementById('rf-text-controls');
  const rfTargetArea = document.getElementById('rf-target-area');
  const rfMarginHeight = document.getElementById('rf-margin-height');
  const rfMarginHeightVal = document.getElementById('rf-margin-height-val');
  const rfFillColor = document.getElementById('rf-fill-color');
  const rfAutoPageNumbers = document.getElementById('rf-auto-page-numbers');
  const rfCustomText = document.getElementById('rf-custom-text');
  const rfTextPageNumbers = document.getElementById('rf-text-page-numbers');
  const rfPreviewSheet = document.getElementById('rf-preview-sheet');
  const rfCutZoneHeader = document.getElementById('rf-cut-zone-header');
  const rfCutZoneFooter = document.getElementById('rf-cut-zone-footer');
  const rfPagesSelect = document.getElementById('rf-pages-select');
  const rfCustomPagesBox = document.getElementById('rf-custom-pages-box');
  const rfCustomPagesInput = document.getElementById('rf-custom-pages-input');
  const toggleRfSkipFirst = document.getElementById('toggle-rf-skip-first');
  const rfOutputFilename = document.getElementById('rf-output-filename');
  const toggleRfLinearize = document.getElementById('toggle-rf-linearize');
  const rfSummaryLabel = document.getElementById('rf-summary-label');
  const btnStartRemoveFooter = document.getElementById('btn-start-remove-footer');

  // =========================================================================
  // INICIALIZAÇÃO
  // =========================================================================
  init();

  function init() {
    if (fileInput) {
      fileInput.multiple = true;
      fileInput.setAttribute('multiple', 'multiple');
    }
    generateSessionId();
    setupNavigation();
    setupCategoryRibbon();
    setupDropzone();
    setupPasswordToggles();
    setupMergeEvents();
    setupSplitEvents();
    setupOrganizeEvents();
    setupRotateEvents();
    setupExtractEvents();
    setupProtectEvents();
    setupUnlockEvents();
    setupRedactEvents();
    setupPdfToWordEvents();
    setupWordToPdfEvents();
    setupImageToPdfEvents();
    setupWatermarkEvents();
    setupFooterEvents();
    setupRemoveFooterEvents();
    setupModalAndPix();
    setupVisitCounter();
    setupZoomModalEvents();
    setupAllToolsCatalogEvents();
    setupCategoryDropdowns();
    setupFeedbackSection();

    // Suporte a hash da URL (ex: #split, #protect, #image-to-pdf, #watermark)
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
  // NAVEGAÇÃO ENTRE FERRAMENTAS & CATEGORIAS
  // =========================================================================
  function setupNavigation() {
    const navButtons = document.querySelectorAll('.tool-nav-btn');
    navButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const targetTool = btn.dataset.tool;
        if (targetTool) {
          if (targetTool !== state.activeTool) {
            switchTool(targetTool);
          } else {
            // Se o usuário clicar na ferramenta já ativa e o modal estiver aberto, apenas fecha o modal
            if (allToolsModal && !allToolsModal.classList.contains('hidden')) {
              allToolsModal.classList.add('hidden');
              document.body.style.overflow = '';
            }
            closeAllCategoryDropdowns();
          }
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

  function setupCategoryDropdowns() {
    const wrappers = document.querySelectorAll('.cat-dropdown-wrapper');
    if (!wrappers.length) return;

    wrappers.forEach(wrapper => {
      const trigger = wrapper.querySelector('.cat-dropdown-trigger');
      if (!trigger) return;

      trigger.addEventListener('click', (e) => {
        e.stopPropagation();
        const isOpen = wrapper.classList.contains('open');

        // Fecha todos os outros dropdowns
        closeAllCategoryDropdowns();

        if (!isOpen) {
          wrapper.classList.add('open');
          trigger.setAttribute('aria-expanded', 'true');
        }
      });
    });

    // Fecha dropdowns ao clicar fora
    document.addEventListener('click', (e) => {
      if (!e.target.closest('.cat-dropdown-wrapper')) {
        closeAllCategoryDropdowns();
      }
    });

    // Fecha dropdowns ao pressionar Escape
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        closeAllCategoryDropdowns();
      }
    });
  }

  function closeAllCategoryDropdowns() {
    document.querySelectorAll('.cat-dropdown-wrapper').forEach(w => {
      w.classList.remove('open');
      const trigger = w.querySelector('.cat-dropdown-trigger');
      if (trigger) trigger.setAttribute('aria-expanded', 'false');
    });
  }

  function setupCategoryRibbon() {
    const categoryPills = document.querySelectorAll('.tool-category-pill');
    if (!categoryPills.length) return;

    categoryPills.forEach(pill => {
      pill.addEventListener('click', () => {
        const selectedCat = pill.dataset.cat || 'all';
        applyCategoryFilter(selectedCat);
      });
    });
  }

  function applyCategoryFilter(selectedCat) {
    const categoryPills = document.querySelectorAll('.tool-category-pill');
    const navButtons = document.querySelectorAll('.tool-nav-btn');

    // 1. Atualiza visual da pílula selecionada
    categoryPills.forEach(p => {
      if (p.dataset.cat === selectedCat) {
        p.classList.add('active');
      } else {
        p.classList.remove('active');
      }
    });

    let currentToolVisible = false;
    let firstVisibleTool = null;

    // 2. Mostra/Oculta apenas as ferramentas pertinentes à categoria selecionada
    navButtons.forEach(btn => {
      const btnCat = btn.dataset.category;
      const isVisible = (selectedCat === 'all' || btnCat === selectedCat);

      if (isVisible) {
        btn.classList.remove('hidden-by-category');
        btn.style.display = '';
        if (!firstVisibleTool) {
          firstVisibleTool = btn.dataset.tool;
        }
        if (btn.dataset.tool === state.activeTool) {
          currentToolVisible = true;
        }
      } else {
        btn.classList.add('hidden-by-category');
        btn.style.display = 'none';
      }
    });

    // 3. Se a ferramenta atual não pertence à categoria selecionada,
    // comuta automaticamente para a primeira ferramenta visível
    if (!currentToolVisible && firstVisibleTool) {
      switchTool(firstVisibleTool);
    }
  }

  function setupAllToolsCatalogEvents() {
    if (!allToolsModal) return;

    function openCatalog() {
      allToolsModal.classList.remove('hidden');
      document.body.style.overflow = 'hidden';
      if (allToolsSearchInput) {
        allToolsSearchInput.value = '';
        if (btnClearToolsSearch) btnClearToolsSearch.classList.add('hidden');
        filterToolsCatalog('');
        setTimeout(() => allToolsSearchInput.focus(), 60);
      }
    }

    function closeCatalog() {
      allToolsModal.classList.add('hidden');
      document.body.style.overflow = '';
    }

    if (btnOpenAllTools) {
      btnOpenAllTools.addEventListener('click', openCatalog);
    }

    if (btnCloseAllToolsModal) {
      btnCloseAllToolsModal.addEventListener('click', closeCatalog);
    }

    if (btnCloseAllToolsFooter) {
      btnCloseAllToolsFooter.addEventListener('click', closeCatalog);
    }

    // Fechar ao clicar no backdrop (overlay)
    allToolsModal.addEventListener('click', (e) => {
      if (e.target === allToolsModal) {
        closeCatalog();
      }
    });

    // Tecla de atalho global: Ctrl+K, Cmd+K, ou '/' para abrir; Escape para fechar
    window.addEventListener('keydown', (e) => {
      // Se pressionar Escape e o modal estiver aberto, fecha
      if (e.key === 'Escape' && !allToolsModal.classList.contains('hidden')) {
        closeCatalog();
        return;
      }

      // Atalho Ctrl+K ou Cmd+K
      if ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K')) {
        e.preventDefault();
        if (allToolsModal.classList.contains('hidden')) {
          openCatalog();
        } else {
          closeCatalog();
        }
        return;
      }

      // Atalho '/' quando o usuário não estiver digitando em nenhum input/textarea
      if (e.key === '/' && allToolsModal.classList.contains('hidden')) {
        const activeTag = document.activeElement ? document.activeElement.tagName.toLowerCase() : '';
        const isEditable = document.activeElement ? document.activeElement.isContentEditable : false;
        if (activeTag !== 'input' && activeTag !== 'textarea' && !isEditable) {
          e.preventDefault();
          openCatalog();
        }
      }
    });

    // Busca em tempo real
    if (allToolsSearchInput) {
      allToolsSearchInput.addEventListener('input', () => {
        const query = allToolsSearchInput.value.trim().toLowerCase();
        if (btnClearToolsSearch) {
          if (query.length > 0) {
            btnClearToolsSearch.classList.remove('hidden');
          } else {
            btnClearToolsSearch.classList.add('hidden');
          }
        }
        filterToolsCatalog(query);
      });
    }

    // Botão de limpar busca
    if (btnClearToolsSearch) {
      btnClearToolsSearch.addEventListener('click', () => {
        allToolsSearchInput.value = '';
        btnClearToolsSearch.classList.add('hidden');
        filterToolsCatalog('');
        allToolsSearchInput.focus();
      });
    }

    function removeAccents(str) {
      return (str || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    }

    function filterToolsCatalog(query) {
      const cards = allToolsModal.querySelectorAll('.all-tools-card');
      const catGroups = allToolsModal.querySelectorAll('.tools-cat-group');
      let visibleCount = 0;

      cards.forEach(card => {
        if (!query) {
          card.classList.remove('hidden');
          card.style.display = '';
          visibleCount++;
          return;
        }

        const toolKey = card.dataset.tool || '';
        const keywords = (card.dataset.keywords || '').toLowerCase();
        const titleEl = card.querySelector('.card-title');
        const descEl = card.querySelector('.card-desc');
        const titleText = titleEl ? titleEl.textContent.toLowerCase() : '';
        const descText = descEl ? descEl.textContent.toLowerCase() : '';

        // Normalização de acentos para busca rápida
        const normQuery = removeAccents(query);
        const normTarget = removeAccents(`${toolKey} ${keywords} ${titleText} ${descText}`);

        if (normTarget.includes(normQuery)) {
          card.classList.remove('hidden');
          card.style.display = '';
          visibleCount++;
        } else {
          card.classList.add('hidden');
          card.style.display = 'none';
        }
      });

      // Oculta/exibe grupos de categoria caso nenhum card do grupo esteja visível
      catGroups.forEach(group => {
        const groupCards = group.querySelectorAll('.all-tools-card');
        const hasVisible = Array.from(groupCards).some(c => !c.classList.contains('hidden') && c.style.display !== 'none');
        group.style.display = hasVisible ? '' : 'none';
      });

      // Exibe estado de busca vazia se nada coincidir
      if (toolsSearchEmpty) {
        if (visibleCount === 0) {
          toolsSearchEmpty.classList.remove('hidden');
        } else {
          toolsSearchEmpty.classList.add('hidden');
        }
      }
    }
  }

  function switchTool(toolKey) {
    if (!TOOL_CONFIGS[toolKey]) return;
    state.activeTool = toolKey;

    // Fecha todos os menus suspensos de categorias
    closeAllCategoryDropdowns();

    // Se o catálogo modal estiver aberto, fecha
    if (allToolsModal && !allToolsModal.classList.contains('hidden')) {
      allToolsModal.classList.add('hidden');
      document.body.style.overflow = '';
    }

    // Atualiza categoria ativa na barra de navegação
    const activeCat = TOOL_CATEGORIES[toolKey] || 'pages';
    document.querySelectorAll('.cat-dropdown-wrapper').forEach(wrapper => {
      const trigger = wrapper.querySelector('.cat-dropdown-trigger');
      if (!trigger) return;
      if (wrapper.dataset.category === activeCat) {
        trigger.classList.add('active-category');
      } else {
        trigger.classList.remove('active-category');
      }
    });

    // Atualiza o indicador da ferramenta ativa na barra
    if (navActiveToolTitle) {
      navActiveToolTitle.textContent = TOOL_SHORT_NAMES[toolKey] || toolKey;
    }

    // Se a ferramenta alvo estiver oculta pela categoria atual, sincroniza a categoria
    const targetBtn = document.querySelector(`.tool-nav-btn[data-tool="${toolKey}"]`);
    if (targetBtn && targetBtn.classList.contains('hidden-by-category')) {
      const toolCat = targetBtn.dataset.category || 'all';
      applyCategoryFilter(toolCat);
    }

    // Atualiza classes ativas na barra de ferramentas e no catálogo
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
    fileInput.multiple = true;
    fileInput.setAttribute('multiple', 'multiple');
    fileInput.accept = (toolKey === 'word-to-pdf') 
      ? '.docx,.doc,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/msword'
      : (toolKey === 'image-to-pdf')
      ? 'image/png,image/jpeg,image/jpg,image/webp,image/bmp,image/tiff,.png,.jpg,.jpeg,.webp,.bmp,.tiff,.tif'
      : '.pdf,application/pdf';

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
    } else if (toolKey === 'image-to-pdf') {
      if (state.imageFiles.length > 0) {
        dropzone.classList.add('hidden');
        stageImageToPdf.classList.remove('hidden');
        renderImageFileList();
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
    } else if (toolKey === 'protect') {
      initProtectWorkspace();
    } else if (toolKey === 'unlock') {
      initUnlockWorkspace();
    } else if (toolKey === 'redact') {
      initRedactWorkspace();
    } else if (toolKey === 'pdf-to-word') {
      initPdfToWordWorkspace();
    } else if (toolKey === 'word-to-pdf') {
      initWordToPdfWorkspace();
    } else if (toolKey === 'watermark') {
      initWatermarkWorkspace();
    } else if (toolKey === 'footer') {
      initFooterWorkspace();
    } else if (toolKey === 'remove-footer') {
      initRemoveFooterWorkspace();
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
    const isWordUpload = state.activeTool === 'word-to-pdf';
    const isImageUpload = state.activeTool === 'image-to-pdf';
    const validFiles = [];

    for (let i = 0; i < fileListObj.length; i++) {
      const file = fileListObj[i];
      const lower = file.name.toLowerCase();
      if (isWordUpload) {
        if (lower.endsWith('.docx') || lower.endsWith('.doc')) {
          validFiles.push(file);
        } else {
          showToast(`O arquivo "${file.name}" foi ignorado. Selecione um arquivo Word (.docx ou .doc).`, 'error');
        }
      } else if (isImageUpload) {
        const imgExts = ['.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff', '.tif'];
        const isImg = imgExts.some(ext => lower.endsWith(ext)) || file.type.startsWith('image/');
        if (isImg) {
          validFiles.push(file);
        } else {
          showToast(`O arquivo "${file.name}" foi ignorado por não ser uma imagem compatível.`, 'error');
        }
      } else {
        if (lower.endsWith('.pdf') || file.type === 'application/pdf') {
          validFiles.push(file);
        } else {
          showToast(`O arquivo "${file.name}" foi ignorado por não ser PDF.`, 'error');
        }
      }
    }

    if (validFiles.length === 0) return;

    if (state.activeTool === 'merge') {
      // Adiciona à lista de mesclagem
      validFiles.forEach(file => {
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
      showToast(`${validFiles.length} arquivo(s) adicionado(s) à unificação.`, 'info');

    } else if (state.activeTool === 'image-to-pdf') {
      // Adiciona à lista de imagens para PDF
      validFiles.forEach(file => {
        const fileId = 'img_' + Math.random().toString(36).substring(2, 9) + '_' + Date.now();
        const previewUrl = URL.createObjectURL(file);
        state.imageFiles.push({
          id: fileId,
          serverSavedName: null,
          name: file.name,
          size: file.size,
          fileObj: file,
          isUploaded: false,
          previewUrl: previewUrl,
        });
      });

      dropzone.classList.add('hidden');
      stageImageToPdf.classList.remove('hidden');
      renderImageFileList();
      showToast(`${validFiles.length} imagem(ns) adicionada(s) à conversão.`, 'info');

    } else {
      // Ferramenta de documento único
      const targetFile = validFiles[0];
      if (validFiles.length > 1) {
        showToast(`Carregado "${targetFile.name}". (Esta ferramenta processa 1 arquivo por vez; para juntar vários documentos, use a aba "Juntar PDF").`, 'info');
      }
      await loadActiveDocument(targetFile);
    }
  }

  async function loadActiveDocument(fileObj) {
    try {
      showToast(`Carregando documento "${fileObj.name}"...`, 'info');

      const isWord = fileObj.name.toLowerCase().endsWith('.docx') || fileObj.name.toLowerCase().endsWith('.doc');
      let pdfDoc = null;
      let pageCount = 1;

      // Lê com PDF.js para renderização de miniaturas (apenas para PDFs)
      if (!isWord && window.pdfjsLib) {
        try {
          const arrayBuffer = await fileObj.arrayBuffer();
          const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer });
          pdfDoc = await loadingTask.promise;
          pageCount = pdfDoc ? pdfDoc.numPages : 1;
        } catch (pdfErr) {
          console.warn('PDF.js aviso ao abrir pré-visualização:', pdfErr);
        }
      }

      state.activeDoc = {
        name: fileObj.name,
        size: fileObj.size,
        pageCount: pageCount,
        serverSavedName: null,
        fileObj: fileObj,
        pdfDoc: pdfDoc,
      };

      // Limpa cache de miniaturas ao carregar novo documento
      thumbnailCache.clear();

      dropzone.classList.add('hidden');
      activateSingleDocToolStage(state.activeTool);
      showToast(isWord ? `Documento Word "${fileObj.name}" carregado!` : `Documento carregado com ${state.activeDoc.pageCount} páginas.`, 'success');

      // Dispara upload em segundo plano para já deixar pronto no servidor
      uploadSingleDocInBackground();

    } catch (err) {
      console.error('Erro ao ler documento:', err);
      showToast('Falha ao abrir o documento no navegador.', 'error');
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
            if (state.activeTool === 'word-to-pdf' && w2pDocPages) {
              w2pDocPages.textContent = `${state.activeDoc.pageCount} pág${state.activeDoc.pageCount > 1 ? 's' : ''}`;
            }
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
    state.redactCustomTerms = [];
    state.imageFiles = [];
    state.watermarkImageDoc = null;
    thumbnailCache.clear();

    document.querySelectorAll('.tool-stage').forEach(el => el.classList.add('hidden'));
    dropzone.classList.remove('hidden');
    fileInput.value = '';
    fileInput.multiple = true;
    fileInput.setAttribute('multiple', 'multiple');
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
        menu_footer_text: mergeFooterTextInput ? mergeFooterTextInput.value : undefined,
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

      <div class="page-card-preview-wrapper" title="Clique para inspecionar com a lupa">
        <canvas class="page-thumbnail-canvas" id="canvas-org-${item.uid}"></canvas>
        <div class="thumbnail-hover-lens">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
            <circle cx="11" cy="11" r="8"/>
            <line x1="21" y1="21" x2="16.65" y2="16.65"/>
            <line x1="11" y1="8" x2="11" y2="14"/>
            <line x1="8" y1="11" x2="14" y2="11"/>
          </svg>
          <span>Ampliar</span>
        </div>
        ${item.rotation !== 0 ? `<span class="page-rotation-badge">+${item.rotation}°</span>` : ''}
      </div>

      <div class="page-card-actions">
        <button type="button" class="card-action-btn btn-card-zoom" title="Inspecionar detalhes (Lupa)">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/></svg>
        </button>
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

    // Evento de abertura da Lupa (no preview ou no botão específico)
    card.querySelector('.page-card-preview-wrapper').addEventListener('click', (e) => {
      e.stopPropagation();
      openPageZoomModal(item.origPage, item.rotation, item, 'organize');
    });

    card.querySelector('.btn-card-zoom').addEventListener('click', (e) => {
      e.stopPropagation();
      openPageZoomModal(item.origPage, item.rotation, item, 'organize');
    });

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

        <div class="page-card-preview-wrapper" title="Clique para inspecionar com a lupa">
          <canvas class="page-thumbnail-canvas" id="canvas-rot-${p}"></canvas>
          <div class="thumbnail-hover-lens">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
              <circle cx="11" cy="11" r="8"/>
              <line x1="21" y1="21" x2="16.65" y2="16.65"/>
              <line x1="11" y1="8" x2="11" y2="14"/>
              <line x1="8" y1="11" x2="14" y2="11"/>
            </svg>
            <span>Ampliar</span>
          </div>
          ${angle !== 0 ? `<span class="page-rotation-badge">+${angle}°</span>` : ''}
        </div>

        <div class="page-card-actions">
          <button type="button" class="card-action-btn btn-rot-left" title="Girar 90° anti-horário">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2.5 2v6h6M2.66 15.57a10 10 0 1 0 .57-8.38L-2.4 1.52"/></svg>
            <span style="font-size:0.75rem;margin-left:3px;">-90°</span>
          </button>
          <button type="button" class="card-action-btn btn-card-rot-zoom" title="Inspecionar detalhes (Lupa)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/></svg>
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

      // Evento de abertura da Lupa
      card.querySelector('.page-card-preview-wrapper').addEventListener('click', (e) => {
        e.stopPropagation();
        openPageZoomModal(p, state.rotateMap[p] || 0, null, 'rotate');
      });

      card.querySelector('.btn-card-rot-zoom').addEventListener('click', (e) => {
        e.stopPropagation();
        openPageZoomModal(p, state.rotateMap[p] || 0, null, 'rotate');
      });

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

        <div class="page-card-header" style="padding-left: 2rem; display: flex; align-items: center; justify-content: space-between;">
          <span class="page-badge-order">Pág. ${p}</span>
          <button type="button" class="card-action-btn btn-card-ext-zoom" title="Inspecionar página (Lupa)" style="width:24px;height:24px;padding:0;z-index:2;">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/></svg>
          </button>
        </div>

        <div class="page-card-preview-wrapper" title="Clique para inspecionar com a lupa">
          <canvas class="page-thumbnail-canvas" id="canvas-ext-${p}"></canvas>
          <div class="thumbnail-hover-lens">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
              <circle cx="11" cy="11" r="8"/>
              <line x1="21" y1="21" x2="16.65" y2="16.65"/>
              <line x1="11" y1="8" x2="11" y2="14"/>
              <line x1="8" y1="11" x2="14" y2="11"/>
            </svg>
            <span>Ampliar</span>
          </div>
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

      // Lupa na página
      card.querySelector('.page-card-preview-wrapper').addEventListener('click', (e) => {
        e.stopPropagation();
        openPageZoomModal(p, 0, null, 'extract');
      });

      card.querySelector('.btn-card-ext-zoom').addEventListener('click', (e) => {
        e.stopPropagation();
        openPageZoomModal(p, 0, null, 'extract');
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
  // MODAL DE LUPA / ZOOM INSPECTOR DE PÁGINAS (ALTA RESOLUÇÃO VIA PDF.JS)
  // =========================================================================
  function setupZoomModalEvents() {
    if (!pageZoomModal) return;

    if (btnCloseZoomModal) btnCloseZoomModal.addEventListener('click', closePageZoomModal);
    if (btnZoomCloseFooter) btnZoomCloseFooter.addEventListener('click', closePageZoomModal);

    pageZoomModal.addEventListener('click', (e) => {
      if (e.target === pageZoomModal) {
        closePageZoomModal();
      }
    });

    if (btnZoomIn) {
      btnZoomIn.addEventListener('click', () => {
        changeZoomScale(0.25);
      });
    }

    if (btnZoomOut) {
      btnZoomOut.addEventListener('click', () => {
        changeZoomScale(-0.25);
      });
    }

    if (btnZoomFit) {
      btnZoomFit.addEventListener('click', () => {
        zoomState.zoomScale = 1.0;
        renderZoomPage();
      });
    }

    if (btnZoomRot) {
      btnZoomRot.addEventListener('click', () => {
        rotateCurrentZoomPage();
      });
    }

    if (btnZoomPrevPage) {
      btnZoomPrevPage.addEventListener('click', () => {
        navigateZoomPage(-1);
      });
    }

    if (btnZoomNextPage) {
      btnZoomNextPage.addEventListener('click', () => {
        navigateZoomPage(1);
      });
    }

    // Atalhos de teclado quando a lupa está aberta
    document.addEventListener('keydown', (e) => {
      if (!zoomState.isOpen) return;

      if (e.key === 'Escape') {
        e.preventDefault();
        closePageZoomModal();
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        navigateZoomPage(-1);
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        navigateZoomPage(1);
      } else if (e.key === '+' || e.key === '=') {
        e.preventDefault();
        changeZoomScale(0.25);
      } else if (e.key === '-' || e.key === '_') {
        e.preventDefault();
        changeZoomScale(-0.25);
      } else if (e.key === '0') {
        e.preventDefault();
        zoomState.zoomScale = 1.0;
        renderZoomPage();
      } else if (e.key === 'r' || e.key === 'R') {
        e.preventDefault();
        rotateCurrentZoomPage();
      }
    });

    // Zoom com Ctrl + Roda do Mouse dentro do contêiner
    if (zoomCanvasContainer) {
      zoomCanvasContainer.addEventListener('wheel', (e) => {
        if (!zoomState.isOpen) return;
        if (e.ctrlKey) {
          e.preventDefault();
          if (e.deltaY < 0) {
            changeZoomScale(0.15);
          } else {
            changeZoomScale(-0.15);
          }
        }
      }, { passive: false });
    }
  }

  function changeZoomScale(delta) {
    let newScale = zoomState.zoomScale + delta;
    newScale = Math.max(0.5, Math.min(3.5, newScale));
    newScale = Math.round(newScale * 100) / 100;
    if (newScale !== zoomState.zoomScale) {
      zoomState.zoomScale = newScale;
      renderZoomPage();
    }
  }

  function rotateCurrentZoomPage() {
    zoomState.rotation = (zoomState.rotation + 90) % 360;

    // Se estiver em Organizar, sincroniza o item e o card na grade
    if (zoomState.sourceContext === 'organize' && zoomState.activeItemRef) {
      zoomState.activeItemRef.rotation = zoomState.rotation;
      const curIdx = state.organizeItems.indexOf(zoomState.activeItemRef);
      if (curIdx >= 0) {
        const card = organizeGrid.querySelector(`.page-card[data-index="${curIdx}"]`);
        if (card) {
          const thumbCanvas = card.querySelector('.page-thumbnail-canvas');
          applyPageRotationStyle(thumbCanvas, zoomState.rotation);
          let rotBadge = card.querySelector('.page-rotation-badge');
          if (zoomState.rotation !== 0) {
            if (rotBadge) {
              rotBadge.textContent = `+${zoomState.rotation}°`;
            } else {
              const newBadge = document.createElement('span');
              newBadge.className = 'page-rotation-badge';
              newBadge.textContent = `+${zoomState.rotation}°`;
              card.querySelector('.page-card-preview-wrapper').appendChild(newBadge);
            }
          } else if (rotBadge) {
            rotBadge.remove();
          }
        }
      }
    } else if (zoomState.sourceContext === 'rotate') {
      state.rotateMap[zoomState.currentPage] = zoomState.rotation;
      updateRotateDisplay();
    }

    renderZoomPage();
  }

  async function openPageZoomModal(pageNum, initialRotation = 0, itemRef = null, context = 'organize') {
    if (!state.activeDoc || !state.activeDoc.pdfDoc) {
      showToast('Documento PDF não carregado para inspeção.', 'error');
      return;
    }

    zoomState.isOpen = true;
    zoomState.currentPage = pageNum;
    zoomState.rotation = (initialRotation || 0) % 360;
    zoomState.activeItemRef = itemRef;
    zoomState.sourceContext = context;
    zoomState.zoomScale = 1.0;

    updateZoomNavAndBadge();
    pageZoomModal.classList.remove('hidden');

    if (zoomCanvasContainer) {
      zoomCanvasContainer.scrollTop = 0;
      zoomCanvasContainer.scrollLeft = 0;
    }

    await renderZoomPage();
  }

  function closePageZoomModal() {
    zoomState.isOpen = false;
    if (zoomState.renderTask) {
      try {
        zoomState.renderTask.cancel();
      } catch (err) {}
      zoomState.renderTask = null;
    }
    pageZoomModal.classList.add('hidden');
  }

  function updateZoomNavAndBadge() {
    if (zoomState.sourceContext === 'organize' && zoomState.activeItemRef) {
      const curIdx = state.organizeItems.indexOf(zoomState.activeItemRef);
      const total = state.organizeItems.length;
      zoomPageBadge.textContent = `Página ${zoomState.activeItemRef.origPage} (#${curIdx + 1} de ${total})`;
      btnZoomPrevPage.disabled = curIdx <= 0;
      btnZoomNextPage.disabled = curIdx >= total - 1;
    } else {
      const total = state.activeDoc.pageCount;
      zoomPageBadge.textContent = `Página ${zoomState.currentPage} de ${total}`;
      btnZoomPrevPage.disabled = zoomState.currentPage <= 1;
      btnZoomNextPage.disabled = zoomState.currentPage >= total;
    }

    zoomLevelLabel.textContent = `${Math.round(zoomState.zoomScale * 100)}%`;
  }

  async function navigateZoomPage(delta) {
    if (zoomState.sourceContext === 'organize' && zoomState.activeItemRef) {
      const curIdx = state.organizeItems.indexOf(zoomState.activeItemRef);
      const nextIdx = curIdx + delta;
      if (nextIdx >= 0 && nextIdx < state.organizeItems.length) {
        zoomState.activeItemRef = state.organizeItems[nextIdx];
        zoomState.currentPage = zoomState.activeItemRef.origPage;
        zoomState.rotation = zoomState.activeItemRef.rotation || 0;
        updateZoomNavAndBadge();
        if (zoomCanvasContainer) {
          zoomCanvasContainer.scrollTop = 0;
          zoomCanvasContainer.scrollLeft = 0;
        }
        await renderZoomPage();
      }
    } else {
      const nextP = zoomState.currentPage + delta;
      if (nextP >= 1 && nextP <= state.activeDoc.pageCount) {
        zoomState.currentPage = nextP;
        if (zoomState.sourceContext === 'rotate') {
          zoomState.rotation = state.rotateMap[nextP] || 0;
        } else {
          zoomState.rotation = 0;
        }
        updateZoomNavAndBadge();
        if (zoomCanvasContainer) {
          zoomCanvasContainer.scrollTop = 0;
          zoomCanvasContainer.scrollLeft = 0;
        }
        await renderZoomPage();
      }
    }
  }

  async function renderZoomPage() {
    if (!state.activeDoc || !state.activeDoc.pdfDoc || !zoomPageCanvas) return;

    if (zoomState.renderTask) {
      try {
        zoomState.renderTask.cancel();
      } catch (e) {}
      zoomState.renderTask = null;
    }

    zoomLoadingIndicator.classList.remove('hidden');
    zoomLevelLabel.textContent = `${Math.round(zoomState.zoomScale * 100)}%`;

    const pageNum = (zoomState.sourceContext === 'organize' && zoomState.activeItemRef)
      ? zoomState.activeItemRef.origPage
      : zoomState.currentPage;

    try {
      const page = await state.activeDoc.pdfDoc.getPage(pageNum);
      
      const baseViewport = page.getViewport({ scale: 1.0, rotation: zoomState.rotation });
      const containerHeight = (zoomCanvasContainer && zoomCanvasContainer.clientHeight > 200)
        ? (zoomCanvasContainer.clientHeight - 80)
        : 720;
      
      const fitScale = Math.max(0.7, Math.min(2.0, containerHeight / baseViewport.height));
      const renderScale = fitScale * zoomState.zoomScale;

      const viewport = page.getViewport({ scale: renderScale, rotation: zoomState.rotation });

      zoomPageCanvas.width = viewport.width;
      zoomPageCanvas.height = viewport.height;

      const ctx = zoomPageCanvas.getContext('2d');
      ctx.clearRect(0, 0, zoomPageCanvas.width, zoomPageCanvas.height);

      const renderTask = page.render({
        canvasContext: ctx,
        viewport: viewport
      });

      zoomState.renderTask = renderTask;
      await renderTask.promise;
      zoomState.renderTask = null;

    } catch (err) {
      if (err && err.name === 'RenderingCancelledException') {
        return;
      }
      console.warn('Erro ao renderizar página na lupa:', err);
    } finally {
      zoomLoadingIndicator.classList.add('hidden');
    }
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
    state.isDocxResult = !!opts.isDocx;

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
    if (opts.isZip) {
      btnDownloadText.textContent = 'Baixar Arquivos (.ZIP)';
    } else if (opts.isDocx) {
      btnDownloadText.textContent = 'Baixar Documento Word (.DOCX)';
    } else {
      btnDownloadText.textContent = 'Baixar Documento (.PDF)';
    }

    if (opts.isZip || opts.isDocx || !opts.previewUrl) {
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
  // RIBBON DE CATEGORIAS E FILTRAGEM
  // =========================================================================
  function setupCategoryRibbon() {
    const ribbon = document.getElementById('tool-categories-ribbon');
    if (!ribbon) return;
    const pills = ribbon.querySelectorAll('.tool-category-pill');
    pills.forEach(pill => {
      pill.addEventListener('click', () => {
        const cat = pill.dataset.cat;
        pills.forEach(p => p.classList.remove('active'));
        pill.classList.add('active');

        const navBtns = document.querySelectorAll('.tool-nav-btn');
        let currentStillVisible = false;
        let firstVisibleTool = null;

        navBtns.forEach(btn => {
          const btnCat = btn.dataset.category;
          if (cat === 'all' || btnCat === cat) {
            btn.style.display = 'flex';
            if (!firstVisibleTool) firstVisibleTool = btn.dataset.tool;
            if (btn.dataset.tool === state.activeTool) currentStillVisible = true;
          } else {
            btn.style.display = 'none';
          }
        });

        if (!currentStillVisible && firstVisibleTool) {
          switchTool(firstVisibleTool);
        }
      });
    });
  }

  // =========================================================================
  // ALTERNÂNCIA DE SENHAS E MEDIDOR DE FORÇA
  // =========================================================================
  function setupPasswordToggles() {
    document.querySelectorAll('.btn-pwd-toggle').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        const targetId = btn.dataset.target;
        const input = document.getElementById(targetId);
        if (!input) return;
        if (input.type === 'password') {
          input.type = 'text';
          btn.textContent = '🙈';
        } else {
          input.type = 'password';
          btn.textContent = '👁';
        }
      });
    });
  }

  function updatePasswordMeter(pwd) {
    if (!pwdMeterBar || !pwdMeterText) return;
    if (!pwd) {
      pwdMeterBar.style.setProperty('--meter-pct', '0%');
      pwdMeterBar.style.setProperty('--meter-color', '#EF4444');
      pwdMeterText.textContent = 'Força da senha';
      pwdMeterText.style.color = 'var(--text-muted)';
      return;
    }

    let score = 0;
    if (pwd.length >= 6) score += 20;
    if (pwd.length >= 10) score += 20;
    if (pwd.length >= 14) score += 10;
    if (/[A-Z]/.test(pwd)) score += 15;
    if (/[a-z]/.test(pwd)) score += 10;
    if (/[0-9]/.test(pwd)) score += 15;
    if (/[^A-Za-z0-9]/.test(pwd)) score += 10;
    score = Math.min(100, score);

    let text = 'Fraca';
    let color = '#EF4444';
    if (score >= 85) {
      text = 'Excelente (Militar)';
      color = '#06B6D4';
    } else if (score >= 65) {
      text = 'Forte';
      color = '#10B981';
    } else if (score >= 40) {
      text = 'Média';
      color = '#F59E0B';
    }

    pwdMeterBar.style.setProperty('--meter-pct', `${score}%`);
    pwdMeterBar.style.setProperty('--meter-color', color);
    pwdMeterText.textContent = `Força: ${text}`;
    pwdMeterText.style.color = color;
  }

  // =========================================================================
  // FERRAMENTA 6: PROTEGER PDF (ENCRYPT / AES-256)
  // =========================================================================
  function setupProtectEvents() {
    if (btnProtectChangeDoc) btnProtectChangeDoc.addEventListener('click', resetCurrentDocument);
    if (protectUserPwd) {
      protectUserPwd.addEventListener('input', (e) => {
        updatePasswordMeter(e.target.value);
      });
    }
    if (btnStartProtect) btnStartProtect.addEventListener('click', onExecuteProtect);
  }

  function initProtectWorkspace() {
    if (!state.activeDoc) return;
    if (protectDocName) protectDocName.textContent = state.activeDoc.name;
    if (protectDocPages) protectDocPages.textContent = `${state.activeDoc.pageCount} pág${state.activeDoc.pageCount > 1 ? 's' : ''}`;
    if (protectDocSize) protectDocSize.textContent = formatBytes(state.activeDoc.size);

    const base = cleanFileNameToTitle(state.activeDoc.name).replace(/\s+/g, '_');
    if (protectOutputFilename) protectOutputFilename.value = `${base}_protegido`;
  }

  async function onExecuteProtect() {
    if (!state.activeDoc) return;

    const userPwd = (protectUserPwd.value || '').trim();
    const ownerPwd = (protectOwnerPwd.value || '').trim();

    if (!userPwd && !ownerPwd) {
      showToast('Por favor, defina ao menos a senha de abertura ou a senha mestra para proteger o PDF.', 'error');
      protectUserPwd.focus();
      return;
    }

    await ensureDocUploaded(state.activeDoc);

    const encLevelRadio = document.querySelector('input[name="enc-level"]:checked');
    const encAlgorithm = encLevelRadio ? encLevelRadio.value : 'aes-256';

    const permissions = {
      allow_printing: toggleAllowPrint ? toggleAllowPrint.checked : false,
      allow_copying: toggleAllowCopy ? toggleAllowCopy.checked : false,
      allow_modifying: toggleAllowModify ? toggleAllowModify.checked : false,
      allow_annotating: toggleAllowAnnotate ? toggleAllowAnnotate.checked : false,
    };

    let cleanName = protectOutputFilename.value.trim() || 'documento_protegido';
    if (!cleanName.toLowerCase().endsWith('.pdf')) cleanName += '.pdf';

    startProcessingUI('Protegendo Documento PDF...', `Aplicando criptografia ${encAlgorithm.toUpperCase()} e restrições com QPDF C++...`);

    try {
      updateProcessingStep(1, 'Validando chaves de segurança e permissões...', 30);
      await delay(200);

      updateProcessingStep(2, `Criptografando com ${encAlgorithm.toUpperCase()} militar...`, 60);

      const payload = {
        session_id: state.sessionId,
        file_id: state.activeDoc.serverSavedName,
        user_password: userPwd,
        owner_password: ownerPwd,
        encryption_algorithm: encAlgorithm,
        permissions: permissions,
        output_filename: cleanName,
        linearize: toggleProtectLinearize ? toggleProtectLinearize.checked : true,
      };

      updateProcessingStep(3, 'Finalizando dicionário de segurança e permissões...', 85);

      const res = await fetch('/api/protect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errJson = await res.json();
        throw new Error(errJson.detail || 'Falha ao proteger o documento PDF.');
      }

      const data = await res.json();
      updateProgress(100, 'PDF protegido com sucesso!');
      await delay(300);

      showResultUI({
        title: 'Documento Protegido com Sucesso!',
        filename: data.output_filename,
        downloadUrl: data.download_url,
        previewUrl: data.preview_url,
        isZip: false,
        label1: 'Criptografia',
        val1: data.metrics.encryption_applied.toUpperCase(),
        label2: 'Total de Páginas',
        val2: `${data.metrics.total_pages} págs`,
        sizeBytes: data.metrics.output_bytes,
        durationSec: data.metrics.duration_seconds,
      });

    } catch (e) {
      console.error(e);
      showToast(e.message || 'Erro ao proteger o PDF.', 'error');
      stopProcessingUI(stageProtect);
    }
  }

  // =========================================================================
  // FERRAMENTA 7: DESPROTEGER PDF (DECRYPT / UNLOCK)
  // =========================================================================
  function setupUnlockEvents() {
    if (btnUnlockChangeDoc) btnUnlockChangeDoc.addEventListener('click', resetCurrentDocument);
    if (btnStartUnlock) btnStartUnlock.addEventListener('click', onExecuteUnlock);
  }

  function initUnlockWorkspace() {
    if (!state.activeDoc) return;
    if (unlockDocName) unlockDocName.textContent = state.activeDoc.name;
    if (unlockDocPages) unlockDocPages.textContent = `${state.activeDoc.pageCount} pág${state.activeDoc.pageCount > 1 ? 's' : ''}`;
    if (unlockDocSize) unlockDocSize.textContent = formatBytes(state.activeDoc.size);

    const base = cleanFileNameToTitle(state.activeDoc.name).replace(/\s+/g, '_');
    if (unlockOutputFilename) unlockOutputFilename.value = `${base}_desprotegido`;
  }

  async function onExecuteUnlock() {
    if (!state.activeDoc) return;

    await ensureDocUploaded(state.activeDoc);

    const pwd = (unlockPassword ? unlockPassword.value : '').trim();
    let cleanName = unlockOutputFilename.value.trim() || 'documento_desprotegido';
    if (!cleanName.toLowerCase().endsWith('.pdf')) cleanName += '.pdf';

    startProcessingUI('Desprotegendo Documento PDF...', 'Removendo senhas e restrições de permissão com motor QPDF C++...');

    try {
      updateProcessingStep(1, 'Autenticando credenciais do PDF...', 30);
      await delay(200);

      updateProcessingStep(2, 'Expurgando travas de impressão, cópia e edição...', 65);

      const payload = {
        session_id: state.sessionId,
        file_id: state.activeDoc.serverSavedName,
        password: pwd,
        output_filename: cleanName,
        linearize: toggleUnlockLinearize ? toggleUnlockLinearize.checked : true,
      };

      updateProcessingStep(3, 'Gravando arquivo sem criptografia e otimizando...', 85);

      const res = await fetch('/api/unlock', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errJson = await res.json();
        throw new Error(errJson.detail || 'Falha ao desproteger o documento PDF.');
      }

      const data = await res.json();
      updateProgress(100, 'PDF desbloqueado com sucesso!');
      await delay(300);

      showResultUI({
        title: 'Documento Desbloqueado com Sucesso!',
        filename: data.output_filename,
        downloadUrl: data.download_url,
        previewUrl: data.preview_url,
        isZip: false,
        label1: 'Status Criptografia',
        val1: 'Livre / Removida',
        label2: 'Total de Páginas',
        val2: `${data.metrics.total_pages} págs`,
        sizeBytes: data.metrics.output_bytes,
        durationSec: data.metrics.duration_seconds,
      });

    } catch (e) {
      console.error(e);
      showToast(e.message || 'Erro ao desbloquear o PDF. Verifique se a senha informada está correta.', 'error');
      stopProcessingUI(stageUnlock);
    }
  }

  // =========================================================================
  // FERRAMENTA 8: REDIGIR / ANONIMIZAR DADOS (LGPD)
  // =========================================================================
  function setupRedactEvents() {
    if (btnRedactChangeDoc) btnRedactChangeDoc.addEventListener('click', resetCurrentDocument);

    if (btnAddRedactTerm && redactCustomTermInput) {
      btnAddRedactTerm.addEventListener('click', addRedactTerm);
      redactCustomTermInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          addRedactTerm();
        }
      });
    }

    if (btnStartRedact) btnStartRedact.addEventListener('click', onExecuteRedact);
  }

  function initRedactWorkspace() {
    if (!state.activeDoc) return;
    if (redactDocName) redactDocName.textContent = state.activeDoc.name;
    if (redactDocPages) redactDocPages.textContent = `${state.activeDoc.pageCount} pág${state.activeDoc.pageCount > 1 ? 's' : ''}`;
    if (redactDocSize) redactDocSize.textContent = formatBytes(state.activeDoc.size);

    const base = cleanFileNameToTitle(state.activeDoc.name).replace(/\s+/g, '_');
    if (redactOutputFilename) redactOutputFilename.value = `${base}_anonimizado`;
    renderRedactTerms();
  }

  function renderRedactTerms() {
    if (!redactTermsContainer) return;
    redactTermsContainer.innerHTML = '';
    state.redactCustomTerms.forEach((term, idx) => {
      const tag = document.createElement('span');
      tag.className = 'term-tag';
      tag.innerHTML = `<span>${escapeHtml(term)}</span><button type="button" class="term-tag-remove" data-idx="${idx}" title="Remover termo">&times;</button>`;
      tag.querySelector('.term-tag-remove').addEventListener('click', () => {
        state.redactCustomTerms.splice(idx, 1);
        renderRedactTerms();
      });
      redactTermsContainer.appendChild(tag);
    });
  }

  function addRedactTerm() {
    const val = (redactCustomTermInput.value || '').trim();
    if (!val) return;
    if (!state.redactCustomTerms.includes(val)) {
      state.redactCustomTerms.push(val);
      renderRedactTerms();
    }
    redactCustomTermInput.value = '';
    redactCustomTermInput.focus();
  }

  async function onExecuteRedact() {
    if (!state.activeDoc) return;

    const presets = [];
    if (presetCpf && presetCpf.checked) presets.push('cpf');
    if (presetCnpj && presetCnpj.checked) presets.push('cnpj');
    if (presetEmail && presetEmail.checked) presets.push('email');
    if (presetPhone && presetPhone.checked) presets.push('phone');
    if (presetCard && presetCard.checked) presets.push('credit_card');

    if (presets.length === 0 && state.redactCustomTerms.length === 0) {
      showToast('Selecione ao menos um padrão pré-configurado (CPF, CNPJ, E-mail, etc.) ou adicione palavras-chave para tarjar.', 'error');
      return;
    }

    await ensureDocUploaded(state.activeDoc);

    let cleanName = redactOutputFilename.value.trim() || 'documento_anonimizado';
    if (!cleanName.toLowerCase().endsWith('.pdf')) cleanName += '.pdf';

    startProcessingUI('Tarjando e Anonimizando PDF...', 'Expurgando glifos, imagens e metadados sensíveis irreversivelmente...');

    try {
      updateProcessingStep(1, 'Escaneando texto das páginas em busca de padrões sensíveis...', 30);
      await delay(200);

      updateProcessingStep(2, 'Aplicando tarjas físicas definitivas (expurgo binário)...', 65);

      const payload = {
        session_id: state.sessionId,
        file_id: state.activeDoc.serverSavedName,
        patterns: presets,
        custom_terms: state.redactCustomTerms,
        clean_metadata: toggleCleanMetadata ? toggleCleanMetadata.checked : true,
        output_filename: cleanName,
        linearize: toggleRedactLinearize ? toggleRedactLinearize.checked : true,
      };

      updateProcessingStep(3, 'Higienizando metadados XMP ocultos e linearizando...', 85);

      const res = await fetch('/api/redact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errJson = await res.json();
        throw new Error(errJson.detail || 'Falha ao tarjar e anonimizar o documento.');
      }

      const data = await res.json();
      updateProgress(100, 'Anonimização concluída com sucesso!');
      await delay(300);

      showResultUI({
        title: 'Documento Anonimizado com Sucesso!',
        filename: data.output_filename,
        downloadUrl: data.download_url,
        previewUrl: data.preview_url,
        isZip: false,
        label1: 'Tarjas Aplicadas',
        val1: `${data.metrics.redactions_applied} itens`,
        label2: 'Páginas Processadas',
        val2: `${data.metrics.total_pages} págs`,
        sizeBytes: data.metrics.output_bytes,
        durationSec: data.metrics.duration_seconds,
      });

    } catch (e) {
      console.error(e);
      showToast(e.message || 'Erro durante a anonimização do PDF.', 'error');
      stopProcessingUI(stageRedact);
    }
  }

  // =========================================================================
  // FERRAMENTA 9: PDF PARA WORD (.DOCX)
  // =========================================================================
  function setupPdfToWordEvents() {
    if (btnP2wChangeDoc) btnP2wChangeDoc.addEventListener('click', resetCurrentDocument);

    const rangeRadios = document.querySelectorAll('input[name="p2w-range-mode"]');
    rangeRadios.forEach(radio => {
      radio.addEventListener('change', () => {
        if (p2wRangeInputsBox) {
          if (radio.value === 'range' && radio.checked) {
            p2wRangeInputsBox.classList.remove('hidden');
          } else {
            p2wRangeInputsBox.classList.add('hidden');
          }
        }
      });
    });

    if (btnStartP2w) btnStartP2w.addEventListener('click', onExecutePdfToWord);
  }

  function initPdfToWordWorkspace() {
    if (!state.activeDoc) return;
    if (p2wDocName) p2wDocName.textContent = state.activeDoc.name;
    if (p2wDocPages) p2wDocPages.textContent = `${state.activeDoc.pageCount} pág${state.activeDoc.pageCount > 1 ? 's' : ''}`;
    if (p2wDocSize) p2wDocSize.textContent = formatBytes(state.activeDoc.size);

    if (p2wStartPage) {
      p2wStartPage.min = 1;
      p2wStartPage.max = state.activeDoc.pageCount;
      p2wStartPage.value = 1;
    }
    if (p2wEndPage) {
      p2wEndPage.min = 1;
      p2wEndPage.max = state.activeDoc.pageCount;
      p2wEndPage.value = state.activeDoc.pageCount;
    }

    const base = cleanFileNameToTitle(state.activeDoc.name).replace(/\s+/g, '_');
    if (p2wOutputFilename) p2wOutputFilename.value = `${base}_word`;
  }

  async function onExecutePdfToWord() {
    if (!state.activeDoc) return;

    await ensureDocUploaded(state.activeDoc);

    const rangeModeRadio = document.querySelector('input[name="p2w-range-mode"]:checked');
    const isRange = rangeModeRadio && rangeModeRadio.value === 'range';

    let startPage = null;
    let endPage = null;

    if (isRange) {
      startPage = parseInt(p2wStartPage.value, 10) || 1;
      endPage = parseInt(p2wEndPage.value, 10) || state.activeDoc.pageCount;
      if (startPage > endPage) [startPage, endPage] = [endPage, startPage];
    }

    let cleanName = p2wOutputFilename.value.trim() || 'documento_convertido';
    if (!cleanName.toLowerCase().endsWith('.docx')) cleanName += '.docx';

    startProcessingUI('Convertendo PDF para Word (.docx)...', 'Reconstruindo fluxo de parágrafos, tabelas e estilos...');

    try {
      updateProcessingStep(1, 'Extraindo e analisando geometrias de texto e tabelas...', 30);
      await delay(250);

      updateProcessingStep(2, 'Gerando documento Microsoft Word estruturado (.docx)...', 65);

      const payload = {
        session_id: state.sessionId,
        file_id: state.activeDoc.serverSavedName,
        start_page: startPage,
        end_page: endPage,
        output_filename: cleanName,
      };

      updateProcessingStep(3, 'Finalizando empacotamento DOCX e tabelas de estilos...', 85);

      const res = await fetch('/api/convert/pdf-to-word', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errJson = await res.json();
        throw new Error(errJson.detail || 'Falha ao converter PDF para Word.');
      }

      const data = await res.json();
      updateProgress(100, 'Conversão para Word concluída!');
      await delay(300);

      showResultUI({
        title: 'Arquivo Word (.docx) Criado com Sucesso!',
        filename: data.output_filename,
        downloadUrl: data.download_url,
        previewUrl: data.preview_url,
        isZip: false,
        isDocx: true,
        label1: 'Páginas Convertidas',
        val1: `${data.metrics.pages_converted} págs`,
        label2: 'Formato de Saída',
        val2: 'DOCX Editável',
        sizeBytes: data.metrics.output_bytes,
        durationSec: data.metrics.duration_seconds,
      });

    } catch (e) {
      console.error(e);
      showToast(e.message || 'Erro durante a conversão de PDF para Word.', 'error');
      stopProcessingUI(stagePdfToWord);
    }
  }

  // =========================================================================
  // FERRAMENTA 10: WORD PARA PDF (.PDF)
  // =========================================================================
  function setupWordToPdfEvents() {
    if (btnW2pChangeDoc) btnW2pChangeDoc.addEventListener('click', resetCurrentDocument);
    if (btnStartW2p) btnStartW2p.addEventListener('click', onExecuteWordToPdf);
  }

  function initWordToPdfWorkspace() {
    if (!state.activeDoc) return;
    if (w2pDocName) w2pDocName.textContent = state.activeDoc.name;
    if (w2pDocPages) w2pDocPages.textContent = `${state.activeDoc.pageCount} pág${state.activeDoc.pageCount > 1 ? 's' : ''}`;
    if (w2pDocSize) w2pDocSize.textContent = formatBytes(state.activeDoc.size);

    const base = cleanFileNameToTitle(state.activeDoc.name).replace(/\s+/g, '_');
    if (w2pOutputFilename) w2pOutputFilename.value = `${base}_pdf`;
  }

  async function onExecuteWordToPdf() {
    if (!state.activeDoc) return;

    await ensureDocUploaded(state.activeDoc);

    let cleanName = w2pOutputFilename.value.trim() || 'documento_convertido';
    if (!cleanName.toLowerCase().endsWith('.pdf')) cleanName += '.pdf';

    startProcessingUI('Convertendo Word para PDF...', 'Renderizando layout, estilos e tabelas com motor de alta precisão...');

    try {
      updateProcessingStep(1, 'Compilando documento Word (.docx/.doc)...', 30);
      await delay(250);

      updateProcessingStep(2, 'Renderizando tipografia e paginação em documento PDF...', 65);

      const payload = {
        session_id: state.sessionId,
        file_id: state.activeDoc.serverSavedName,
        output_filename: cleanName,
        linearize: toggleW2pLinearize ? toggleW2pLinearize.checked : true,
      };

      updateProcessingStep(3, 'Aplicando Fast Web View (linearização) e finalizando...', 85);

      const res = await fetch('/api/convert/word-to-pdf', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errJson = await res.json();
        throw new Error(errJson.detail || 'Falha ao converter Word para PDF.');
      }

      const data = await res.json();
      updateProgress(100, 'Conversão para PDF concluída!');
      await delay(300);

      showResultUI({
        title: 'Documento PDF Criado com Sucesso!',
        filename: data.output_filename,
        downloadUrl: data.download_url,
        previewUrl: data.preview_url,
        isZip: false,
        isDocx: false,
        label1: 'Motor Utilizado',
        val1: data.metrics.engine ? data.metrics.engine.toUpperCase() : 'DUAL ENGINE',
        label2: 'Total de Páginas',
        val2: `${data.metrics.total_pages} págs`,
        sizeBytes: data.metrics.output_bytes,
        durationSec: data.metrics.duration_seconds,
      });

    } catch (e) {
      console.error(e);
      showToast(e.message || 'Erro durante a conversão de Word para PDF.', 'error');
      stopProcessingUI(stageWordToPdf);
    }
  }

  // =========================================================================
  // FERRAMENTA 11: IMAGEM PARA PDF (.PDF)
  // =========================================================================
  let draggedImageIndex = null;

  function setupImageToPdfEvents() {
    if (btnI2pAddMore) btnI2pAddMore.addEventListener('click', () => fileInput.click());
    if (btnI2pClearAll) {
      btnI2pClearAll.addEventListener('click', () => {
        if (confirm('Deseja realmente remover todas as imagens selecionadas?')) {
          state.imageFiles = [];
          renderImageFileList();
        }
      });
    }

    if (btnStartI2p) btnStartI2p.addEventListener('click', onExecuteImageToPdf);
  }

  function renderImageFileList() {
    if (!i2pFileList) return;
    i2pFileList.innerHTML = '';

    if (state.imageFiles.length === 0) {
      if (stageImageToPdf) stageImageToPdf.classList.add('hidden');
      dropzone.classList.remove('hidden');
      return;
    }

    if (i2pFilesCounter) {
      i2pFilesCounter.textContent = `${state.imageFiles.length} imagen${state.imageFiles.length > 1 ? 's' : ''}`;
    }

    let totalBytes = 0;

    state.imageFiles.forEach((item, index) => {
      totalBytes += item.size;

      const li = document.createElement('li');
      li.className = 'file-item';
      li.draggable = true;
      li.dataset.index = index;

      li.innerHTML = `
        <div class="file-item-left">
          <div class="drag-handle" title="Arraste para reordenar a página">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="9" cy="6" r="1.5"/><circle cx="15" cy="6" r="1.5"/>
              <circle cx="9" cy="12" r="1.5"/><circle cx="15" cy="12" r="1.5"/>
              <circle cx="9" cy="18" r="1.5"/><circle cx="15" cy="18" r="1.5"/>
            </svg>
          </div>
          <div class="file-order-badge">Pág ${index + 1}</div>
          <img src="${item.previewUrl}" alt="Miniatura" class="i2p-thumb-preview">
          <div class="file-details">
            <div class="file-meta-row">
              <strong class="file-original-name" title="${escapeHtml(item.name)}">${escapeHtml(item.name)}</strong>
              <span class="meta-separator">&bull;</span>
              <span class="file-size">${formatBytes(item.size)}</span>
            </div>
          </div>
        </div>

        <div class="file-item-right">
          <button type="button" class="btn-icon btn-move-up" title="Mover para cima" ${index === 0 ? 'disabled style="opacity:0.3;cursor:default;"' : ''}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="18 15 12 9 6 15"/></svg>
          </button>
          <button type="button" class="btn-icon btn-move-down" title="Mover para baixo" ${index === state.imageFiles.length - 1 ? 'disabled style="opacity:0.3;cursor:default;"' : ''}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
          </button>
          <button type="button" class="btn-icon btn-icon-danger btn-remove" title="Remover esta imagem">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>
      `;

      setupImageDragDrop(li, index);

      li.querySelector('.btn-move-up').addEventListener('click', (e) => {
        e.stopPropagation();
        if (index > 0) swapImageFiles(index, index - 1);
      });

      li.querySelector('.btn-move-down').addEventListener('click', (e) => {
        e.stopPropagation();
        if (index < state.imageFiles.length - 1) swapImageFiles(index, index + 1);
      });

      li.querySelector('.btn-remove').addEventListener('click', (e) => {
        e.stopPropagation();
        state.imageFiles.splice(index, 1);
        renderImageFileList();
      });

      i2pFileList.appendChild(li);
    });

    if (i2pTotalSizeLabel) {
      i2pTotalSizeLabel.textContent = formatBytes(totalBytes);
    }

    if (state.imageFiles.length > 0 && i2pOutputFilename && (!i2pOutputFilename.value || i2pOutputFilename.value === 'imagens_convertidas')) {
      const base = cleanFileNameToTitle(state.imageFiles[0].name).replace(/\s+/g, '_');
      i2pOutputFilename.value = `${base}_album`;
    }
  }

  function swapImageFiles(i, j) {
    const tmp = state.imageFiles[i];
    state.imageFiles[i] = state.imageFiles[j];
    state.imageFiles[j] = tmp;
    renderImageFileList();
  }

  function setupImageDragDrop(element, index) {
    element.addEventListener('dragstart', (e) => {
      draggedImageIndex = index;
      element.classList.add('dragging');
      e.dataTransfer.effectAllowed = 'move';
      e.dataTransfer.setData('text/plain', index);
    });

    element.addEventListener('dragend', () => {
      element.classList.remove('dragging');
      draggedImageIndex = null;
    });

    element.addEventListener('dragover', (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
    });

    element.addEventListener('drop', (e) => {
      e.preventDefault();
      e.stopPropagation();
      const targetIndex = index;
      if (draggedImageIndex !== null && draggedImageIndex !== targetIndex) {
        const moved = state.imageFiles.splice(draggedImageIndex, 1)[0];
        state.imageFiles.splice(targetIndex, 0, moved);
        renderImageFileList();
      }
    });
  }

  async function onExecuteImageToPdf() {
    if (state.imageFiles.length === 0) {
      showToast('Por favor, adicione ao menos uma imagem para converter.', 'error');
      return;
    }

    await ensureFilesUploaded(state.imageFiles);

    startProcessingUI('Convertendo Imagens para PDF...', 'Ajustando geometrias, margens e compilando páginas...');

    try {
      updateProcessingStep(1, 'Lendo e otimizando resoluções das imagens...', 25);
      await delay(200);

      updateProcessingStep(2, 'Renderizando documento PDF com alta fidelidade...', 65);

      const sizeRadio = document.querySelector('input[name="i2p-page-size"]:checked');
      const orientRadio = document.querySelector('input[name="i2p-orientation"]:checked');
      const marginRadio = document.querySelector('input[name="i2p-margin"]:checked');

      let cleanName = (i2pOutputFilename ? i2pOutputFilename.value.trim() : '') || 'imagens_convertidas';
      if (!cleanName.toLowerCase().endsWith('.pdf')) cleanName += '.pdf';

      const payload = {
        session_id: state.sessionId,
        image_files: state.imageFiles.map(f => f.serverSavedName),
        page_size: sizeRadio ? sizeRadio.value : 'a4',
        orientation: orientRadio ? orientRadio.value : 'auto',
        margin: marginRadio ? marginRadio.value : 'none',
        output_filename: cleanName,
        linearize: toggleI2pLinearize ? toggleI2pLinearize.checked : true,
      };

      updateProcessingStep(3, 'Aplicando Fast Web View (linearização) e finalizando...', 85);

      const res = await fetch('/api/convert/image-to-pdf', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errJson = await res.json();
        throw new Error(errJson.detail || 'Falha ao converter imagens para PDF.');
      }

      const data = await res.json();
      updateProgress(100, 'Conversão de imagens concluída com sucesso!');
      await delay(300);

      showResultUI({
        title: 'Imagens Convertidas para PDF!',
        filename: data.output_filename,
        downloadUrl: data.download_url,
        previewUrl: data.preview_url,
        isZip: false,
        isDocx: false,
        label1: 'Imagens Inseridas',
        val1: `${data.metrics.total_images} fotos`,
        label2: 'Total de Páginas',
        val2: `${data.metrics.total_pages} págs`,
        sizeBytes: data.metrics.output_bytes,
        durationSec: data.metrics.duration_seconds,
      });

    } catch (e) {
      console.error(e);
      showToast(e.message || 'Erro durante a conversão das imagens.', 'error');
      stopProcessingUI(stageImageToPdf);
    }
  }

  // =========================================================================
  // FERRAMENTA 12: INSERIR MARCA D'ÁGUA EM PDF (.PDF)
  // =========================================================================
  function setupWatermarkEvents() {
    if (btnWmChangeDoc) btnWmChangeDoc.addEventListener('click', resetCurrentDocument);

    // Alternador de tipo (Texto vs Imagem)
    if (wmTypeText && wmTypeImage) {
      wmTypeText.addEventListener('change', () => {
        if (wmTextControls) wmTextControls.classList.remove('hidden');
        if (wmImageControls) wmImageControls.classList.add('hidden');
      });
      wmTypeImage.addEventListener('change', () => {
        if (wmTextControls) wmTextControls.classList.add('hidden');
        if (wmImageControls) wmImageControls.classList.remove('hidden');
      });
    }

    // Botões de texto pré-configurado
    document.querySelectorAll('.wm-preset-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        if (wmTextInput && btn.dataset.text) {
          wmTextInput.value = btn.dataset.text;
        }
      });
    });

    // Sliders com feedback em tempo real
    if (wmFontSize && wmFontSizeVal) {
      wmFontSize.addEventListener('input', () => {
        wmFontSizeVal.textContent = `${wmFontSize.value} pt`;
      });
    }

    if (wmOpacity && wmOpacityVal) {
      wmOpacity.addEventListener('input', () => {
        wmOpacityVal.textContent = `${wmOpacity.value}%`;
      });
    }

    if (wmImageScale && wmScaleVal) {
      wmImageScale.addEventListener('input', () => {
        wmScaleVal.textContent = `${wmImageScale.value}%`;
      });
    }

    // Seletor de cor e bolinhas pré-definidas
    if (wmFontColor && wmColorPreviewVal) {
      wmFontColor.addEventListener('input', () => {
        wmColorPreviewVal.textContent = wmFontColor.value.toUpperCase();
      });
    }

    document.querySelectorAll('.color-dot').forEach(dot => {
      dot.addEventListener('click', () => {
        if (wmFontColor && dot.dataset.color) {
          wmFontColor.value = dot.dataset.color;
          if (wmColorPreviewVal) wmColorPreviewVal.textContent = dot.dataset.color.toUpperCase();
        }
      });
    });

    // Seletor de páginas
    if (wmPagesSelect && wmCustomPagesBox) {
      wmPagesSelect.addEventListener('change', () => {
        if (wmPagesSelect.value === 'custom') {
          wmCustomPagesBox.classList.remove('hidden');
        } else {
          wmCustomPagesBox.classList.add('hidden');
        }
      });
    }

    // Upload de Imagem de Marca d'água
    if (wmImgUploadPrompt && wmImgFileInput) {
      wmImgUploadPrompt.addEventListener('click', () => wmImgFileInput.click());
      wmImgFileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files.length > 0) {
          handleWatermarkImageFile(e.target.files[0]);
          wmImgFileInput.value = '';
        }
      });
    }

    if (btnWmRemoveImg) {
      btnWmRemoveImg.addEventListener('click', () => {
        state.watermarkImageDoc = null;
        if (wmImgPreviewBox) wmImgPreviewBox.classList.add('hidden');
        if (wmImgUploadPrompt) wmImgUploadPrompt.classList.remove('hidden');
      });
    }

    if (btnStartWatermark) btnStartWatermark.addEventListener('click', onExecuteWatermark);
  }

  async function handleWatermarkImageFile(file) {
    const previewUrl = URL.createObjectURL(file);
    state.watermarkImageDoc = {
      name: file.name,
      size: file.size,
      fileObj: file,
      serverSavedName: null,
      previewUrl: previewUrl,
    };

    if (wmImgPreview) wmImgPreview.src = previewUrl;
    if (wmImgName) wmImgName.textContent = file.name;
    if (wmImgUploadPrompt) wmImgUploadPrompt.classList.add('hidden');
    if (wmImgPreviewBox) wmImgPreviewBox.classList.remove('hidden');

    // Upload em segundo plano da imagem
    try {
      const formData = new FormData();
      formData.append('session_id', state.sessionId);
      formData.append('files', file, file.name);

      const res = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });

      if (res.ok) {
        const data = await res.json();
        if (data.files && data.files.length > 0) {
          state.watermarkImageDoc.serverSavedName = data.files[0].saved_filename;
        }
      }
    } catch (e) {
      console.warn('Erro ao subir logotipo de marca d\'água em segundo plano:', e);
    }
  }

  function initWatermarkWorkspace() {
    if (!state.activeDoc) return;
    if (wmDocName) wmDocName.textContent = state.activeDoc.name;
    if (wmDocPages) wmDocPages.textContent = `${state.activeDoc.pageCount} pág${state.activeDoc.pageCount > 1 ? 's' : ''}`;
    if (wmDocSize) wmDocSize.textContent = formatBytes(state.activeDoc.size);

    const base = cleanFileNameToTitle(state.activeDoc.name).replace(/\s+/g, '_');
    if (wmOutputFilename) wmOutputFilename.value = `${base}_marca_dagua`;
  }

  async function onExecuteWatermark() {
    if (!state.activeDoc) return;
    await ensureDocUploaded(state.activeDoc);

    const isImageMode = wmTypeImage && wmTypeImage.checked;
    if (isImageMode) {
      if (!state.watermarkImageDoc) {
        showToast('Por favor, carregue a imagem do logotipo para a marca d\'água.', 'error');
        return;
      }
      if (!state.watermarkImageDoc.serverSavedName) {
        await ensureDocUploaded(state.watermarkImageDoc);
      }
    } else {
      if (!wmTextInput || !wmTextInput.value.trim()) {
        showToast('Por favor, digite o texto da marca d\'água.', 'error');
        return;
      }
    }

    startProcessingUI('Inserindo Marca d\'água...', 'Renderizando carimbos com transparência, rotação e QPDF C++...');

    try {
      updateProcessingStep(1, 'Lendo geometria das páginas do documento...', 25);
      await delay(200);

      updateProcessingStep(2, 'Calculando e desenhando camadas de marca d\'água...', 60);

      let cleanName = (wmOutputFilename ? wmOutputFilename.value.trim() : '') || 'documento_marca_dagua';
      if (!cleanName.toLowerCase().endsWith('.pdf')) cleanName += '.pdf';

      let pagesVal = wmPagesSelect ? wmPagesSelect.value : 'all';
      if (pagesVal === 'custom' && wmCustomPagesInput) {
        pagesVal = wmCustomPagesInput.value.trim() || 'all';
      }

      const payload = {
        session_id: state.sessionId,
        file_id: state.activeDoc.serverSavedName,
        watermark_type: isImageMode ? 'image' : 'text',
        text: wmTextInput ? wmTextInput.value.trim() : 'CONFIDENCIAL',
        font_size: wmFontSize ? (parseInt(wmFontSize.value, 10) || 48) : 48,
        font_color: wmFontColor ? wmFontColor.value : '#DC2626',
        opacity: wmOpacity ? (parseInt(wmOpacity.value, 10) || 25) / 100 : 0.25,
        rotation: wmRotation ? (parseInt(wmRotation.value, 10) || -45) : -45,
        position: wmPosition ? wmPosition.value : 'center',
        watermark_image_id: isImageMode && state.watermarkImageDoc ? state.watermarkImageDoc.serverSavedName : null,
        image_scale: wmImageScale ? (parseInt(wmImageScale.value, 10) || 50) / 100 : 0.5,
        layer: wmLayer ? wmLayer.value : 'overlay',
        pages: pagesVal,
        output_filename: cleanName,
        linearize: toggleWmLinearize ? toggleWmLinearize.checked : true,
      };

      updateProcessingStep(3, 'Fundindo camadas com o conteúdo original e linearizando...', 85);

      const res = await fetch('/api/watermark', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errJson = await res.json();
        throw new Error(errJson.detail || 'Falha ao aplicar marca d\'água.');
      }

      const data = await res.json();
      updateProgress(100, 'Marca d\'água aplicada com sucesso!');
      await delay(300);

      showResultUI({
        title: 'Marca d\'água Aplicada com Sucesso!',
        filename: data.output_filename,
        downloadUrl: data.download_url,
        previewUrl: data.preview_url,
        isZip: false,
        isDocx: false,
        label1: 'Páginas Carimbadas',
        val1: `${data.metrics.pages_watermarked} de ${data.metrics.total_pages} págs`,
        label2: 'Configuração',
        val2: `${data.metrics.watermark_type === 'image' ? 'Logotipo' : 'Texto'} (${data.metrics.position.toUpperCase()})`,
        sizeBytes: data.metrics.output_bytes,
        durationSec: data.metrics.duration_seconds,
      });

    } catch (e) {
      console.error(e);
      showToast(e.message || 'Erro ao aplicar marca d\'água no PDF.', 'error');
      stopProcessingUI(stageWatermark);
    }
  }

  // =========================================================================
  // FERRAMENTA 13: PERSONALIZAR RODAPÉ E NUMERAÇÃO DE PÁGINAS (.PDF)
  // =========================================================================
  function setupFooterEvents() {
    if (btnFooterChangeDoc) btnFooterChangeDoc.addEventListener('click', resetCurrentDocument);

    // Botões de tags e modelos rápidos
    document.querySelectorAll('.footer-tag-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        if (footerTextInput && btn.dataset.tag) {
          footerTextInput.value = btn.dataset.tag;
          updateFooterPreview();
        }
      });
    });

    // Atualização em tempo real de inputs e sliders
    if (footerTextInput) {
      footerTextInput.addEventListener('input', updateFooterPreview);
    }

    if (footerPositionSelect) {
      footerPositionSelect.addEventListener('change', updateFooterPreview);
    }

    if (footerAlignmentSelect) {
      footerAlignmentSelect.addEventListener('change', updateFooterPreview);
    }

    if (footerFontSize && footerFontSizeVal) {
      footerFontSize.addEventListener('input', () => {
        footerFontSizeVal.textContent = `${footerFontSize.value} pt`;
        updateFooterPreview();
      });
    }

    if (footerMarginOffset && footerMarginVal) {
      footerMarginOffset.addEventListener('input', () => {
        footerMarginVal.textContent = `${footerMarginOffset.value} pt`;
      });
    }

    if (footerFontColor && footerColorVal) {
      footerFontColor.addEventListener('input', () => {
        footerColorVal.textContent = footerFontColor.value.toUpperCase();
        updateFooterPreview();
      });
    }

    const footerDots = document.querySelectorAll('#stage-footer .color-dot');
    footerDots.forEach(dot => {
      dot.addEventListener('click', () => {
        if (footerFontColor && dot.dataset.color) {
          footerFontColor.value = dot.dataset.color;
          if (footerColorVal) footerColorVal.textContent = dot.dataset.color.toUpperCase();
          updateFooterPreview();
        }
      });
    });

    if (footerStartNum) {
      footerStartNum.addEventListener('input', updateFooterPreview);
    }

    if (btnStartFooter) {
      btnStartFooter.addEventListener('click', onExecuteFooter);
    }
  }

  function initFooterWorkspace() {
    if (!state.activeDoc) return;
    if (footerDocName) footerDocName.textContent = state.activeDoc.name;
    if (footerDocPages) footerDocPages.textContent = `${state.activeDoc.pageCount} pág${state.activeDoc.pageCount > 1 ? 's' : ''}`;
    if (footerDocSize) footerDocSize.textContent = formatBytes(state.activeDoc.size);

    const base = cleanFileNameToTitle(state.activeDoc.name).replace(/\s+/g, '_');
    if (footerOutputFilename) footerOutputFilename.value = `${base}_com_rodape`;

    updateFooterPreview();
  }

  function updateFooterPreview() {
    if (!footerPreviewSheet) return;

    const text = footerTextInput ? footerTextInput.value : 'Página {page} de {total}';
    const pos = footerPositionSelect ? footerPositionSelect.value : 'footer';
    const align = footerAlignmentSelect ? footerAlignmentSelect.value : 'center';
    const size = footerFontSize ? parseFloat(footerFontSize.value) || 9 : 9;
    const color = footerFontColor ? footerFontColor.value : '#64748B';

    const totalP = (state.activeDoc && state.activeDoc.pageCount) ? state.activeDoc.pageCount : 12;
    const startNum = footerStartNum ? parseInt(footerStartNum.value, 10) || 1 : 1;
    const sampleText = text
      .replace(/\{page\}/gi, startNum)
      .replace(/\{total\}/gi, totalP)
      .replace(/\{date\}/gi, new Date().toLocaleDateString('pt-BR'))
      .replace(/\{file\}/gi, (state.activeDoc ? state.activeDoc.name : 'documento.pdf').substring(0, 16));

    const scaledSize = Math.max(9, Math.min(14, size));

    if (pos === 'header') {
      if (footerPreviewHeaderSlot) {
        footerPreviewHeaderSlot.style.display = 'block';
        footerPreviewHeaderSlot.style.textAlign = align;
        footerPreviewHeaderSlot.style.fontSize = `${scaledSize}px`;
        footerPreviewHeaderSlot.style.color = color;
        footerPreviewHeaderSlot.textContent = sampleText;
      }
      if (footerPreviewFooterSlot) {
        footerPreviewFooterSlot.style.display = 'none';
      }
    } else {
      if (footerPreviewFooterSlot) {
        footerPreviewFooterSlot.style.display = 'block';
        footerPreviewFooterSlot.style.textAlign = align;
        footerPreviewFooterSlot.style.fontSize = `${scaledSize}px`;
        footerPreviewFooterSlot.style.color = color;
        footerPreviewFooterSlot.textContent = sampleText;
      }
      if (footerPreviewHeaderSlot) {
        footerPreviewHeaderSlot.style.display = 'none';
      }
    }

    if (footerSummaryLabel) {
      const posLabel = (pos === 'header') ? 'Cabeçalho' : 'Rodapé';
      const alignLabel = { left: 'Esquerda', center: 'Centro', right: 'Direita' }[align] || align;
      footerSummaryLabel.textContent = `${posLabel} (${alignLabel}) • ${size}pt`;
    }
  }

  async function onExecuteFooter() {
    if (!state.activeDoc) return;
    await ensureDocUploaded(state.activeDoc);

    const text = footerTextInput ? footerTextInput.value.trim() : '{page}';
    if (!text) {
      showToast('Por favor, informe o texto ou tags para o rodapé/cabeçalho.', 'error');
      return;
    }

    startProcessingUI('Personalizando Rodapé...', 'Estampando texto vetorial de alta definição e aplicando Fast Web View...');

    try {
      updateProcessingStep(1, 'Lendo geometria e dimensões das páginas do PDF...', 25);
      await delay(200);

      updateProcessingStep(2, 'Substituindo tags dinâmicas e desenhando vetores...', 60);

      let cleanName = (footerOutputFilename ? footerOutputFilename.value.trim() : '') || 'documento_com_rodape';
      if (!cleanName.toLowerCase().endsWith('.pdf')) cleanName += '.pdf';

      const payload = {
        session_id: state.sessionId,
        file_id: state.activeDoc.serverSavedName,
        footer_text: text,
        position: footerPositionSelect ? footerPositionSelect.value : 'footer',
        alignment: footerAlignmentSelect ? footerAlignmentSelect.value : 'center',
        font_size: footerFontSize ? parseFloat(footerFontSize.value) || 9.0 : 9.0,
        font_color: footerFontColor ? footerFontColor.value : '#64748B',
        skip_first_page: toggleFooterSkipFirst ? toggleFooterSkipFirst.checked : false,
        page_start_number: footerStartNum ? parseInt(footerStartNum.value, 10) || 1 : 1,
        margin_offset: footerMarginOffset ? parseFloat(footerMarginOffset.value) || 25.0 : 25.0,
        output_filename: cleanName,
        linearize: toggleFooterLinearize ? toggleFooterLinearize.checked : true,
      };

      updateProcessingStep(3, 'Otimizando e linearizando estrutura do arquivo...', 85);

      const res = await fetch('/api/footer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errJson = await res.json();
        throw new Error(errJson.detail || 'Falha ao estampar rodapé no PDF.');
      }

      const data = await res.json();
      updateProgress(100, 'Rodapé aplicado com perfeição!');
      await delay(300);

      const posLabel = (data.metrics.position === 'header') ? 'Cabeçalho' : 'Rodapé';
      const alignLabel = { left: 'Esquerda', center: 'Centro', right: 'Direita' }[data.metrics.alignment] || data.metrics.alignment;

      showResultUI({
        title: 'Rodapé Personalizado com Sucesso!',
        filename: data.output_filename,
        downloadUrl: data.download_url,
        previewUrl: data.preview_url,
        isZip: false,
        isDocx: false,
        label1: 'Páginas Estampadas',
        val1: `${data.metrics.pages_processed} de ${data.metrics.total_pages} págs`,
        label2: 'Disposição',
        val2: `${posLabel} (${alignLabel})`,
        sizeBytes: data.metrics.output_bytes,
        durationSec: data.metrics.duration_seconds,
      });

    } catch (e) {
      console.error(e);
      showToast(e.message || 'Erro ao estampar rodapé no documento.', 'error');
      stopProcessingUI(stageFooter);
    }
  }

  // =========================================================================
  // FERRAMENTA 14: REMOVER RODAPÉ E CABEÇALHO (.PDF)
  // =========================================================================
  function setupRemoveFooterEvents() {
    if (btnRfChangeDoc) btnRfChangeDoc.addEventListener('click', resetCurrentDocument);

    // Alternador de modo (Margem vs Texto)
    if (rfModeMargin && rfModeText) {
      rfModeMargin.addEventListener('change', () => {
        if (rfMarginControls) rfMarginControls.classList.remove('hidden');
        if (rfTextControls) rfTextControls.classList.add('hidden');
        updateRemoveFooterPreview();
      });
      rfModeText.addEventListener('change', () => {
        if (rfMarginControls) rfMarginControls.classList.add('hidden');
        if (rfTextControls) rfTextControls.classList.remove('hidden');
        updateRemoveFooterPreview();
      });
    }

    // Botões de texto pré-configurado
    document.querySelectorAll('.rf-preset-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        if (rfCustomText && btn.dataset.text) {
          rfCustomText.value = btn.dataset.text;
          updateRemoveFooterPreview();
        }
      });
    });

    // Slider de altura da margem com feedback em tempo real
    if (rfMarginHeight && rfMarginHeightVal) {
      rfMarginHeight.addEventListener('input', () => {
        const val = rfMarginHeight.value;
        const cm = (val * 0.0352).toFixed(1);
        rfMarginHeightVal.textContent = `${val} pt (~${cm} cm)`;
        updateRemoveFooterPreview();
      });
    }

    if (rfTargetArea) {
      rfTargetArea.addEventListener('change', updateRemoveFooterPreview);
    }

    if (rfCustomText) {
      rfCustomText.addEventListener('input', updateRemoveFooterPreview);
    }

    // Seletor de páginas
    if (rfPagesSelect && rfCustomPagesBox) {
      rfPagesSelect.addEventListener('change', () => {
        if (rfPagesSelect.value === 'custom') {
          rfCustomPagesBox.classList.remove('hidden');
        } else {
          rfCustomPagesBox.classList.add('hidden');
        }
      });
    }

    if (btnStartRemoveFooter) {
      btnStartRemoveFooter.addEventListener('click', onExecuteRemoveFooter);
    }
  }

  function initRemoveFooterWorkspace() {
    if (!state.activeDoc) return;
    if (rfDocName) rfDocName.textContent = state.activeDoc.name;
    if (rfDocPages) rfDocPages.textContent = `${state.activeDoc.pageCount} pág${state.activeDoc.pageCount > 1 ? 's' : ''}`;
    if (rfDocSize) rfDocSize.textContent = formatBytes(state.activeDoc.size);

    const base = cleanFileNameToTitle(state.activeDoc.name).replace(/\s+/g, '_');
    if (rfOutputFilename) rfOutputFilename.value = `${base}_sem_rodape`;

    updateRemoveFooterPreview();
  }

  function updateRemoveFooterPreview() {
    if (!rfPreviewSheet) return;

    const isMarginMode = !rfModeText || !rfModeText.checked;
    const target = rfTargetArea ? rfTargetArea.value : 'footer';
    const height = rfMarginHeight ? parseInt(rfMarginHeight.value, 10) || 35 : 35;

    // Escala proporcional para a miniatura (folha tem ~170px de altura total)
    const previewZoneHeight = Math.max(18, Math.min(55, Math.round(height * 0.9)));

    if (rfCutZoneHeader) {
      if (isMarginMode && (target === 'header' || target === 'both')) {
        rfCutZoneHeader.classList.remove('hidden');
        rfCutZoneHeader.style.height = `${previewZoneHeight}px`;
      } else {
        rfCutZoneHeader.classList.add('hidden');
      }
    }

    if (rfCutZoneFooter) {
      if (isMarginMode && (target === 'footer' || target === 'both')) {
        rfCutZoneFooter.classList.remove('hidden');
        rfCutZoneFooter.style.height = `${previewZoneHeight}px`;
      } else {
        rfCutZoneFooter.classList.add('hidden');
      }
    }

    if (rfSummaryLabel) {
      if (isMarginMode) {
        const areaLabel = { footer: 'Rodapé', header: 'Cabeçalho', both: 'Rodapé & Cabeçalho' }[target] || target;
        rfSummaryLabel.textContent = `Faixa: ${areaLabel} (${height} pt)`;
      } else {
        const txt = (rfCustomText && rfCustomText.value.trim()) ? `"${rfCustomText.value.trim().substring(0, 15)}..."` : 'Numeração';
        rfSummaryLabel.textContent = `Busca de Texto: ${txt}`;
      }
    }
  }

  async function onExecuteRemoveFooter() {
    if (!state.activeDoc) return;
    await ensureDocUploaded(state.activeDoc);

    const isMarginMode = !rfModeText || !rfModeText.checked;
    const customTxt = rfCustomText ? rfCustomText.value.trim() : '';
    const removePageNums = isMarginMode
      ? (rfAutoPageNumbers ? rfAutoPageNumbers.checked : true)
      : (rfTextPageNumbers ? rfTextPageNumbers.checked : true);

    if (!isMarginMode && !customTxt && !removePageNums) {
      showToast('Por favor, informe um texto ou marque para remover números de página.', 'error');
      return;
    }

    startProcessingUI('Removendo Rodapé...', 'Expurgando elementos físicos da página com motor C++ QPDF...');

    try {
      updateProcessingStep(1, 'Lendo estrutura e calculando margens de corte...', 25);
      await delay(200);

      updateProcessingStep(2, 'Expurgando permanentemente dados e aplicando preenchimento...', 60);

      let cleanName = (rfOutputFilename ? rfOutputFilename.value.trim() : '') || 'documento_sem_rodape';
      if (!cleanName.toLowerCase().endsWith('.pdf')) cleanName += '.pdf';

      let pagesVal = rfPagesSelect ? rfPagesSelect.value : 'all';
      if (pagesVal === 'custom' && rfCustomPagesInput) {
        pagesVal = rfCustomPagesInput.value.trim() || 'all';
      }

      const payload = {
        session_id: state.sessionId,
        file_id: state.activeDoc.serverSavedName,
        mode: isMarginMode ? 'margin' : 'text',
        target_area: rfTargetArea ? rfTargetArea.value : 'footer',
        margin_height: rfMarginHeight ? parseFloat(rfMarginHeight.value) || 35.0 : 35.0,
        fill_color: rfFillColor ? rfFillColor.value : '#FFFFFF',
        custom_text: customTxt || null,
        remove_page_numbers: removePageNums,
        skip_first_page: toggleRfSkipFirst ? toggleRfSkipFirst.checked : false,
        pages: pagesVal,
        output_filename: cleanName,
        linearize: toggleRfLinearize ? toggleRfLinearize.checked : true,
      };

      updateProcessingStep(3, 'Reconstruindo documento e linearizando com Fast Web View...', 85);

      const res = await fetch('/api/remove-footer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errJson = await res.json();
        throw new Error(errJson.detail || 'Falha ao remover rodapé do PDF.');
      }

      const data = await res.json();
      updateProgress(100, 'Rodapé removido com sucesso!');
      await delay(300);

      const modeTitle = (data.metrics.mode === 'margin') ? 'Faixa de Margem' : 'Busca Cirúrgica';

      showResultUI({
        title: 'Rodapé Removido com Sucesso!',
        filename: data.output_filename,
        downloadUrl: data.download_url,
        previewUrl: data.preview_url,
        isZip: false,
        isDocx: false,
        label1: 'Páginas Processadas',
        val1: `${data.metrics.pages_processed} de ${data.metrics.total_pages} págs`,
        label2: 'Método Aplicado',
        val2: `${modeTitle} (${data.metrics.target_area.toUpperCase()})`,
        sizeBytes: data.metrics.output_bytes,
        durationSec: data.metrics.duration_seconds,
      });

    } catch (e) {
      console.error(e);
      showToast(e.message || 'Erro ao remover rodapé do PDF.', 'error');
      stopProcessingUI(stageRemoveFooter);
    }
  }

  // =========================================================================
  // MODAL DE PRÉ-VISUALIZAÇÃO & BOTÕES DE PIX
  // =========================================================================
  function setupModalAndPix() {
    btnPreview.addEventListener('click', () => {
      if (state.isDocxResult) {
        showToast('Documentos Word (.docx) devem ser baixados para edição no Microsoft Word ou LibreOffice.', 'info');
        return;
      }
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
      } else if (state.activeTool === 'image-to-pdf') {
        if (stageImageToPdf) stageImageToPdf.classList.remove('hidden');
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
  // CONTADOR DE VISITAS PERSISTENTE
  // =========================================================================
  function setupVisitCounter() {
    const counterPillText = document.getElementById('visit-counter-text');
    const footerVisitsText = document.getElementById('footer-visits-count');
    if (!counterPillText && !footerVisitsText) return;

    let visitorToken = null;
    try {
      visitorToken = localStorage.getItem('klynner_visitor_token');
      if (!visitorToken) {
        visitorToken = 'vis_' + Math.random().toString(36).substring(2, 12) + '_' + Date.now();
        localStorage.setItem('klynner_visitor_token', visitorToken);
      }
    } catch (e) {
      visitorToken = 'vis_' + Date.now();
    }

    fetch('/api/stats/visit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ visitor_token: visitorToken })
    })
      .then(res => res.json())
      .then(data => {
        if (data && data.success && data.stats) {
          const total = data.stats.total_visits || 1;
          const formatted = Number(total).toLocaleString('pt-BR');
          if (counterPillText) {
            counterPillText.textContent = `${formatted} visitas`;
          }
          if (footerVisitsText) {
            footerVisitsText.textContent = `${formatted} acessos registrados`;
          }
        }
      })
      .catch(err => {
        console.debug('Analytics offline:', err);
        if (counterPillText) counterPillText.textContent = '1+ visitas';
      });
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

  // =========================================================================
  // CAIXA DE SUGESTÕES, COMENTÁRIOS E FEEDBACK
  // =========================================================================
  function setupFeedbackSection() {
    const feedbackForm = document.getElementById('feedback-form');
    const feedbackCatChips = document.querySelectorAll('.feedback-cat-chip');
    const starsPicker = document.getElementById('feedback-stars-picker');
    const starBtns = starsPicker ? starsPicker.querySelectorAll('.star-btn') : [];
    const ratingLegend = document.getElementById('feedback-rating-legend');
    const inputName = document.getElementById('feedback-input-name');
    const inputEmail = document.getElementById('feedback-input-email');
    const inputMessage = document.getElementById('feedback-input-message');
    const charCounter = document.getElementById('feedback-char-counter');
    const btnSubmit = document.getElementById('btn-submit-feedback');
    const btnSubmitText = document.getElementById('btn-submit-feedback-text');
    const spinnerFeedback = document.getElementById('spinner-feedback');
    const successCard = document.getElementById('feedback-success-card');
    const btnAnother = document.getElementById('btn-feedback-another');
    const cardsGrid = document.getElementById('feedback-cards-grid');
    const boardTotalCount = document.getElementById('board-total-count');
    const btnRefresh = document.getElementById('btn-refresh-feedbacks');
    const headerBtnFeedback = document.getElementById('header-btn-feedback');

    if (!feedbackForm) return;

    let currentCategory = 'sugestao';
    let currentRating = 5;

    const RATING_TEXTS = {
      1: 'Precisa melhorar (1/5) ⭐',
      2: 'Regular (2/5) ⭐⭐',
      3: 'Bom (3/5) ⭐⭐⭐',
      4: 'Muito bom (4/5) ⭐⭐⭐⭐',
      5: 'Excelente (5/5) ⭐⭐⭐⭐⭐',
    };

    // 1. Seleção de Categoria (Chips)
    feedbackCatChips.forEach(chip => {
      chip.addEventListener('click', () => {
        feedbackCatChips.forEach(c => {
          c.classList.remove('active');
          c.setAttribute('aria-checked', 'false');
        });
        chip.classList.add('active');
        chip.setAttribute('aria-checked', 'true');
        currentCategory = chip.dataset.cat || 'sugestao';
      });
    });

    // 2. Avaliação por Estrelas
    function renderStars(rating, isHover = false) {
      starBtns.forEach(btn => {
        const val = parseInt(btn.dataset.val, 10);
        if (isHover) {
          if (val <= rating) {
            btn.classList.add('hover-active');
          } else {
            btn.classList.remove('hover-active');
          }
        } else {
          btn.classList.remove('hover-active');
          if (val <= rating) {
            btn.classList.add('active');
          } else {
            btn.classList.remove('active');
          }
        }
      });
      if (ratingLegend && RATING_TEXTS[rating]) {
        ratingLegend.textContent = RATING_TEXTS[rating];
      }
    }

    starBtns.forEach(btn => {
      const val = parseInt(btn.dataset.val, 10);
      btn.addEventListener('mouseenter', () => {
        renderStars(val, true);
      });
      btn.addEventListener('mouseleave', () => {
        renderStars(currentRating, false);
      });
      btn.addEventListener('click', () => {
        currentRating = val;
        renderStars(currentRating, false);
      });
    });

    // 3. Contador de Caracteres
    if (inputMessage && charCounter) {
      inputMessage.addEventListener('input', () => {
        const len = inputMessage.value.length;
        charCounter.textContent = `${len} / 2000`;
        if (len >= 1900) {
          charCounter.style.color = '#F43F5E';
        } else {
          charCounter.style.color = '';
        }
      });
    }

    // 4. Envio do Formulário
    feedbackForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const message = (inputMessage ? inputMessage.value : '').trim();
      if (!message || message.length < 3) {
        showToast('Por favor, escreva uma mensagem com ao menos 3 caracteres.', 'error');
        if (inputMessage) inputMessage.focus();
        return;
      }

      const nameVal = (inputName ? inputName.value : '').trim();
      const emailVal = (inputEmail ? inputEmail.value : '').trim();

      // UI Loading
      if (btnSubmit) btnSubmit.disabled = true;
      if (spinnerFeedback) spinnerFeedback.classList.remove('hidden');
      if (btnSubmitText) btnSubmitText.textContent = 'Enviando...';

      try {
        const resp = await fetch('/api/feedback', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            category: currentCategory,
            name: nameVal || null,
            email: emailVal || null,
            rating: currentRating,
            message: message,
            tool_context: state.activeTool || null,
          }),
        });

        const data = await resp.json();
        if (resp.ok && data.success) {
          showToast('Obrigado! Sua mensagem foi enviada com sucesso.', 'success');
          feedbackForm.classList.add('hidden');
          if (successCard) successCard.classList.remove('hidden');
          loadRecentFeedbacks();
        } else {
          showToast(data.detail || 'Ocorreu um erro ao enviar seu feedback. Tente novamente.', 'error');
        }
      } catch (err) {
        console.error('Erro ao enviar feedback:', err);
        showToast('Erro de conexão ao enviar feedback.', 'error');
      } finally {
        if (btnSubmit) btnSubmit.disabled = false;
        if (spinnerFeedback) spinnerFeedback.classList.add('hidden');
        if (btnSubmitText) btnSubmitText.textContent = 'Enviar Mensagem';
      }
    });

    // 5. Botão "Enviar outra mensagem"
    if (btnAnother) {
      btnAnother.addEventListener('click', () => {
        if (inputMessage) inputMessage.value = '';
        if (charCounter) charCounter.textContent = '0 / 2000';
        currentRating = 5;
        renderStars(5, false);
        currentCategory = 'sugestao';
        feedbackCatChips.forEach(c => {
          c.classList.toggle('active', c.dataset.cat === 'sugestao');
          c.setAttribute('aria-checked', c.dataset.cat === 'sugestao' ? 'true' : 'false');
        });
        if (successCard) successCard.classList.add('hidden');
        feedbackForm.classList.remove('hidden');
        if (inputMessage) inputMessage.focus();
      });
    }

    // 6. Carregar Mural da Comunidade
    async function loadRecentFeedbacks() {
      if (!cardsGrid) return;
      try {
        const res = await fetch('/api/feedback/recent');
        if (!res.ok) throw new Error('Falha ao carregar mural');
        const data = await res.json();

        if (boardTotalCount && data.total !== undefined) {
          boardTotalCount.textContent = `${data.total} mensagem${data.total === 1 ? '' : 's'}`;
        }

        const items = data.feedbacks || [];
        if (items.length === 0) {
          cardsGrid.innerHTML = `
            <div class="feedback-loading-placeholder">
              Nenhuma mensagem pública no momento. Deixe a primeira sugestão acima!
            </div>
          `;
          return;
        }

        const CAT_LABELS = {
          sugestao: { label: '💡 Sugestão', cls: 'cat-badge-sugestao' },
          bug: { label: '🐛 Bug', cls: 'cat-badge-bug' },
          elogio: { label: '⭐ Elogio', cls: 'cat-badge-elogio' },
          outro: { label: '💬 Comentário', cls: 'cat-badge-outro' },
        };

        const cardsHtml = items.map(item => {
          const catInfo = CAT_LABELS[item.category] || CAT_LABELS.sugestao;
          const starsStr = '★'.repeat(Math.max(1, Math.min(5, item.rating || 5))) +
                           '☆'.repeat(5 - Math.max(1, Math.min(5, item.rating || 5)));
          const initials = (item.name || 'U').substring(0, 2).toUpperCase();
          const dateStr = item.created_at ? new Date(item.created_at).toLocaleDateString('pt-BR') : '';

          return `
            <div class="feedback-item-card">
              <div class="feedback-item-header">
                <div class="feedback-item-user">
                  <div class="feedback-user-avatar">${escapeHtml(initials)}</div>
                  <span class="feedback-user-name">${escapeHtml(item.name || 'Usuário')}</span>
                </div>
                <span class="feedback-item-cat-badge ${catInfo.cls}">${catInfo.label}</span>
              </div>
              <div class="feedback-item-stars" title="${item.rating || 5} de 5 estrelas">${starsStr}</div>
              <p class="feedback-item-message">${escapeHtml(item.message || '')}</p>
              <div class="feedback-item-footer">
                <span>${item.tool_context ? 'Ferramenta: ' + escapeHtml(TOOL_SHORT_NAMES[item.tool_context] || item.tool_context) : 'Klynner PRO'}</span>
                <span>${dateStr}</span>
              </div>
            </div>
          `;
        }).join('');

        cardsGrid.innerHTML = cardsHtml;
      } catch (err) {
        console.warn('Erro ao carregar feedbacks recentes:', err);
        cardsGrid.innerHTML = `
          <div class="feedback-loading-placeholder">
            Carregamento do mural temporariamente indisponível.
          </div>
        `;
      }
    }

    if (btnRefresh) {
      btnRefresh.addEventListener('click', loadRecentFeedbacks);
    }

    // Scroll suave pelo Header Pill
    if (headerBtnFeedback) {
      headerBtnFeedback.addEventListener('click', (e) => {
        e.preventDefault();
        const section = document.getElementById('feedback-section');
        if (section) {
          section.scrollIntoView({ behavior: 'smooth', block: 'start' });
          setTimeout(() => {
            if (inputMessage) inputMessage.focus();
          }, 600);
        }
      });
    }

    // Carrega na inicialização
    loadRecentFeedbacks();
  }

})();
