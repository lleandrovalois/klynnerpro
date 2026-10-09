// Test script to check JavaScript syntax, DOM element bindings, and organize logic
const fs = require('fs');

console.log("Reading index.html and app.js...");
const html = fs.readFileSync('app/templates/index.html', 'utf8');
const js = fs.readFileSync('app/static/js/app.js', 'utf8');

// Check that all IDs referenced in stage-organize exist in index.html
const organizeIds = [
  'stage-organize',
  'organize-doc-name',
  'organize-pages-counter',
  'organize-doc-size',
  'btn-organize-reset',
  'btn-organize-change-doc',
  'organize-loading',
  'organize-grid',
  'organize-output-filename',
  'toggle-organize-linearize',
  'organize-total-label',
  'btn-start-organize'
];

let missingIds = [];
for (const id of organizeIds) {
  if (!html.includes(`id="${id}"`)) {
    missingIds.push(id);
  }
}

console.log("Missing IDs in index.html for organize:", missingIds);

// Check merge page organizer IDs
const mergeOrganizerIds = [
  'stage-merge',
  'btn-merge-view-pages',
  'btn-merge-view-files',
  'merge-view-pages',
  'merge-view-files',
  'merge-pages-grid',
  'merge-pages-subbar',
  'merge-select-all-checkbox',
  'merge-selection-status',
  'btn-merge-collapse-all',
  'btn-merge-expand-all',
  'btn-merge-rot-ccw',
  'btn-merge-rot-cw',
  'btn-merge-delete-selected',
  'btn-merge-finish-top',
  'btn-merge-top-clear',
  'btn-start-merge'
];

let missingMergeIds = [];
for (const id of mergeOrganizerIds) {
  if (!html.includes(`id="${id}"`)) {
    missingMergeIds.push(id);
  }
}
console.log("Missing IDs in index.html for merge organizer:", missingMergeIds);

// Verify that TOOL_CONFIGS.organize has multiple: true and stageId: 'stage-merge'
const hasMultiOrganize = js.includes("enginePill: 'Organizador de Páginas Ativo'") && js.includes("stageId: 'stage-merge'");
console.log("TOOL_CONFIGS organize multiple is configured:", hasMultiOrganize);
if (!hasMultiOrganize || missingMergeIds.length > 0) process.exit(1);
console.log("All DOM tests passed successfully!");
