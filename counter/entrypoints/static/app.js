const form = document.querySelector('#count-form');
const fileInput = document.querySelector('#file');
const thresholdInput = document.querySelector('#threshold');
const modelInput = document.querySelector('#model_name');
const modelOptions = document.querySelector('#model-options');
const modelHelp = document.querySelector('#model-help');
const submitButton = document.querySelector('#submit-button');
const resetButton = document.querySelector('#reset-button');
const statusBadge = document.querySelector('#status-badge');
const message = document.querySelector('#message');
const resultsGrid = document.querySelector('#results-grid');
const currentResults = document.querySelector('#current-results');
const totalResults = document.querySelector('#total-results');
const previewPanel = document.querySelector('#preview-panel');
const preview = document.querySelector('#preview');

function setStatus(label, state = '') {
  statusBadge.textContent = label;
  statusBadge.className = `status-badge ${state}`.trim();
}

function setMessage(text, isError = false) {
  message.textContent = text;
  message.className = isError ? 'message error' : 'message';
}

function normalizeRows(rows) {
  return [...(rows || [])].sort((a, b) => {
    const left = a.object_class || '';
    const right = b.object_class || '';
    return left.localeCompare(right);
  });
}

function renderRows(container, rows) {
  container.replaceChildren();

  const normalizedRows = normalizeRows(rows);
  if (normalizedRows.length === 0) {
    const empty = document.createElement('p');
    empty.className = 'message';
    empty.textContent = 'No objects returned.';
    container.append(empty);
    return;
  }

  for (const row of normalizedRows) {
    const item = document.createElement('div');
    item.className = 'result-row';

    const name = document.createElement('strong');
    name.textContent = row.object_class || 'unknown';

    const count = document.createElement('span');
    count.textContent = Number.isFinite(row.count) ? row.count : '0';

    item.append(name, count);
    container.append(item);
  }
}

async function loadModelAliases() {
  try {
    const response = await fetch('/models');
    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.error || `Request failed with ${response.status}`);
    }

    modelOptions.replaceChildren();
    for (const model of payload.models || []) {
      const option = document.createElement('option');
      option.value = model.name;
      option.label = model.display_name;
      modelOptions.append(option);
    }

    modelInput.placeholder = payload.default_model || 'current';
    modelHelp.textContent = payload.default_model
      ? `Leave blank to use the server default: ${payload.default_model}.`
      : 'Leave blank to use the server default model.';
  } catch (error) {
    modelHelp.textContent = 'Could not load model aliases; type one manually.';
  }
}

function validateForm() {
  if (!fileInput.files.length) {
    return 'Choose an image file before submitting.';
  }

  const threshold = Number(thresholdInput.value);
  if (!Number.isFinite(threshold) || threshold < 0 || threshold > 1) {
    return 'Threshold must be a number between 0 and 1.';
  }

  return '';
}

async function countObjects(event) {
  event.preventDefault();

  const validationError = validateForm();
  if (validationError) {
    setStatus('Error', 'error');
    setMessage(validationError, true);
    resultsGrid.hidden = true;
    return;
  }

  const body = new FormData();
  body.append('file', fileInput.files[0]);
  body.append('threshold', thresholdInput.value);

  const modelName = modelInput.value.trim();
  if (modelName) {
    body.append('model_name', modelName);
  }

  submitButton.disabled = true;
  setStatus('Counting', 'loading');
  setMessage('Sending image to the API...');
  resultsGrid.hidden = true;

  try {
    const response = await fetch('/object-count', {
      method: 'POST',
      body,
    });
    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.error || `Request failed with ${response.status}`);
    }

    renderRows(currentResults, payload.current_objects);
    renderRows(totalResults, payload.total_objects);
    resultsGrid.hidden = false;
    setStatus('Complete', 'success');
    setMessage('Object count completed.');
  } catch (error) {
    setStatus('Error', 'error');
    setMessage(error.message || 'Unable to count objects.', true);
  } finally {
    submitButton.disabled = false;
  }
}

function resetUi() {
  form.reset();
  thresholdInput.value = '0.9';
  preview.removeAttribute('src');
  previewPanel.hidden = true;
  resultsGrid.hidden = true;
  setStatus('Ready');
  setMessage('Submit an image to see results.');
}

function showPreview() {
  const file = fileInput.files[0];
  if (!file) {
    preview.removeAttribute('src');
    previewPanel.hidden = true;
    return;
  }

  preview.src = URL.createObjectURL(file);
  previewPanel.hidden = false;
}

form.addEventListener('submit', countObjects);
resetButton.addEventListener('click', resetUi);
fileInput.addEventListener('change', showPreview);
loadModelAliases();
