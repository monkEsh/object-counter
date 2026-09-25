const predictionForm = document.querySelector('#prediction-form');
const predictionFileInput = document.querySelector('#prediction-file');
const predictionThresholdInput = document.querySelector('#prediction-threshold');
const predictionModelInput = document.querySelector('#prediction-model-name');
const predictionModelOptions = document.querySelector('#prediction-model-options');
const predictionModelHelp = document.querySelector('#prediction-model-help');
const predictionSubmitButton = document.querySelector('#prediction-submit-button');
const predictionResetButton = document.querySelector('#prediction-reset-button');
const predictionStatusBadge = document.querySelector('#prediction-status-badge');
const predictionMessage = document.querySelector('#prediction-message');
const predictionPreviewPanel = document.querySelector('#prediction-preview-panel');
const predictionPreview = document.querySelector('#prediction-preview');
const predictionOutput = document.querySelector('#prediction-output');
const predictionRunId = document.querySelector('#prediction-run-id');
const predictionRunModel = document.querySelector('#prediction-run-model');
const predictionRunThreshold = document.querySelector('#prediction-run-threshold');
const predictionRunImagePath = document.querySelector('#prediction-run-image-path');
const predictionAnnotatedImage = document.querySelector('#prediction-annotated-image');
const predictionList = document.querySelector('#prediction-list');
const predictionJson = document.querySelector('#prediction-json');
const refreshRunsButton = document.querySelector('#refresh-runs-button');
const storedRunsMessage = document.querySelector('#stored-runs-message');
const storedRunsPanel = document.querySelector('#stored-runs-panel');
const storedRunsList = document.querySelector('#stored-runs-list');
const previousRunsButton = document.querySelector('#previous-runs-button');
const nextRunsButton = document.querySelector('#next-runs-button');
const runsPageLabel = document.querySelector('#runs-page-label');

const runsPageSize = 5;
let runsOffset = 0;

function setPredictionStatus(label, state = '') {
  predictionStatusBadge.textContent = label;
  predictionStatusBadge.className = `status-badge ${state}`.trim();
}

function setPredictionMessage(text, isError = false) {
  predictionMessage.textContent = text;
  predictionMessage.className = isError ? 'message error' : 'message';
}

function validatePredictionForm() {
  if (!predictionFileInput.files.length) {
    return 'Choose an image file before submitting.';
  }

  const threshold = Number(predictionThresholdInput.value);
  if (!Number.isFinite(threshold) || threshold < 0 || threshold > 1) {
    return 'Threshold must be a number between 0 and 1.';
  }

  return '';
}

function annotatedImageUrl(annotatedImagePath) {
  const fileName = (annotatedImagePath || '').split('/').pop();
  return fileName ? `/debug-images/${encodeURIComponent(fileName)}` : '';
}

function renderPredictionList(predictions) {
  predictionList.replaceChildren();

  if (!predictions || predictions.length === 0) {
    const empty = document.createElement('p');
    empty.className = 'message';
    empty.textContent = 'No predictions returned for this threshold.';
    predictionList.append(empty);
    return;
  }

  for (const prediction of predictions) {
    const row = document.createElement('div');
    row.className = 'prediction-row';

    const title = document.createElement('strong');
    title.textContent = prediction.class_name || 'unknown';

    const score = document.createElement('span');
    const scoreValue = Number(prediction.score);
    score.textContent = Number.isFinite(scoreValue)
      ? `${(scoreValue * 100).toFixed(1)}%`
      : 'n/a';

    const box = document.createElement('small');
    const coords = prediction.box || {};
    box.textContent = `box: xmin=${coords.xmin}, ymin=${coords.ymin}, xmax=${coords.xmax}, ymax=${coords.ymax}`;

    row.append(title, score, box);
    predictionList.append(row);
  }
}

function renderPredictionOutput(payload) {
  predictionRunId.textContent = payload.id || '';
  predictionRunModel.textContent = payload.model_name || '';
  predictionRunThreshold.textContent = payload.threshold ?? '';
  predictionRunImagePath.textContent = payload.annotated_image || '';

  const imageUrl = payload.annotated_image_url || annotatedImageUrl(payload.annotated_image);
  if (imageUrl) {
    predictionAnnotatedImage.src = `${imageUrl}?t=${Date.now()}`;
    predictionAnnotatedImage.hidden = false;
  } else {
    predictionAnnotatedImage.removeAttribute('src');
    predictionAnnotatedImage.hidden = true;
  }

  renderPredictionList(payload.predictions || []);
  predictionJson.textContent = JSON.stringify(payload, null, 2);
  predictionOutput.hidden = false;
}

function setStoredRunsMessage(text, isError = false) {
  storedRunsMessage.textContent = text;
  storedRunsMessage.className = isError ? 'message error' : 'message';
}

function renderStoredRuns(runs, hasMore) {
  storedRunsList.replaceChildren();

  if (!runs.length) {
    setStoredRunsMessage(runsOffset === 0
      ? 'No stored prediction runs yet.'
      : 'No more stored prediction runs.');
    storedRunsPanel.hidden = runsOffset === 0;
    previousRunsButton.disabled = runsOffset === 0;
    nextRunsButton.disabled = true;
    runsPageLabel.textContent = `Offset ${runsOffset}`;
    return;
  }

  for (const run of runs) {
    const row = document.createElement('article');
    row.className = 'stored-run-row';

    const details = document.createElement('div');

    const title = document.createElement('strong');
    title.textContent = run.id;

    const meta = document.createElement('small');
    const predictionCount = Array.isArray(run.predictions) ? run.predictions.length : 0;
    meta.textContent = `${run.model_name} · threshold ${run.threshold} · ${predictionCount} predictions`;

    details.append(title, meta);

    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'secondary';
    button.textContent = 'View';
    button.addEventListener('click', () => loadPredictionRun(run.id));

    row.append(details, button);
    storedRunsList.append(row);
  }

  storedRunsPanel.hidden = false;
  previousRunsButton.disabled = runsOffset === 0;
  nextRunsButton.disabled = !hasMore;
  runsPageLabel.textContent = `Showing ${runsOffset + 1}-${runsOffset + runs.length}`;
  setStoredRunsMessage('Stored prediction runs loaded.');
}

async function loadStoredRuns(offset = runsOffset) {
  runsOffset = Math.max(0, offset);
  setStoredRunsMessage('Loading stored prediction runs...');

  try {
    const response = await fetch(`/prediction-runs?limit=${runsPageSize}&offset=${runsOffset}`);
    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.error || `Request failed with ${response.status}`);
    }

    renderStoredRuns(payload.prediction_runs || [], Boolean(payload.has_more));
  } catch (error) {
    setStoredRunsMessage(error.message || 'Unable to load stored prediction runs.', true);
  }
}

async function loadPredictionRun(predictionRunId) {
  setPredictionStatus('Loading', 'loading');
  setPredictionMessage('Loading stored prediction run...');

  try {
    const response = await fetch(`/prediction-runs/${encodeURIComponent(predictionRunId)}`);
    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.error || `Request failed with ${response.status}`);
    }

    renderPredictionOutput(payload);
    setPredictionStatus('Complete', 'success');
    setPredictionMessage('Stored prediction run loaded.');
  } catch (error) {
    setPredictionStatus('Error', 'error');
    setPredictionMessage(error.message || 'Unable to load prediction run.', true);
  }
}

async function loadPredictionModelAliases() {
  try {
    const response = await fetch('/models');
    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.error || `Request failed with ${response.status}`);
    }

    predictionModelOptions.replaceChildren();
    for (const model of payload.models || []) {
      const option = document.createElement('option');
      option.value = model.name;
      option.label = model.display_name;
      predictionModelOptions.append(option);
    }

    predictionModelInput.placeholder = payload.default_model || 'current';
    predictionModelHelp.textContent = payload.default_model
      ? `Leave blank to use the server default: ${payload.default_model}.`
      : 'Leave blank to use the server default model.';
  } catch (error) {
    predictionModelHelp.textContent = 'Could not load model aliases; type one manually.';
  }
}

async function generatePredictions(event) {
  event.preventDefault();

  const validationError = validatePredictionForm();
  if (validationError) {
    setPredictionStatus('Error', 'error');
    setPredictionMessage(validationError, true);
    predictionOutput.hidden = true;
    return;
  }

  const body = new FormData();
  body.append('file', predictionFileInput.files[0]);
  body.append('threshold', predictionThresholdInput.value);

  const modelName = predictionModelInput.value.trim();
  if (modelName) {
    body.append('model_name', modelName);
  }

  predictionSubmitButton.disabled = true;
  setPredictionStatus('Predicting', 'loading');
  setPredictionMessage('Sending image to the prediction API...');
  predictionOutput.hidden = true;

  try {
    const response = await fetch('/predictions', {
      method: 'POST',
      body,
    });
    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.error || `Request failed with ${response.status}`);
    }

    renderPredictionOutput(payload);
    await loadStoredRuns(0);
    setPredictionStatus('Complete', 'success');
    setPredictionMessage('Prediction run completed.');
  } catch (error) {
    setPredictionStatus('Error', 'error');
    setPredictionMessage(error.message || 'Unable to generate predictions.', true);
  } finally {
    predictionSubmitButton.disabled = false;
  }
}

function resetPredictionUi() {
  predictionForm.reset();
  predictionThresholdInput.value = '0.9';
  predictionPreview.removeAttribute('src');
  predictionPreviewPanel.hidden = true;
  predictionAnnotatedImage.removeAttribute('src');
  predictionOutput.hidden = true;
  setPredictionStatus('Ready');
  setPredictionMessage('Submit an image to see prediction output.');
}

function showPredictionPreview() {
  const file = predictionFileInput.files[0];
  if (!file) {
    predictionPreview.removeAttribute('src');
    predictionPreviewPanel.hidden = true;
    return;
  }

  predictionPreview.src = URL.createObjectURL(file);
  predictionPreviewPanel.hidden = false;
}

predictionForm.addEventListener('submit', generatePredictions);
predictionResetButton.addEventListener('click', resetPredictionUi);
predictionFileInput.addEventListener('change', showPredictionPreview);
refreshRunsButton.addEventListener('click', () => loadStoredRuns(runsOffset));
previousRunsButton.addEventListener('click', () => loadStoredRuns(runsOffset - runsPageSize));
nextRunsButton.addEventListener('click', () => loadStoredRuns(runsOffset + runsPageSize));
loadPredictionModelAliases();
loadStoredRuns();
