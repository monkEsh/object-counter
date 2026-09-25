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
loadPredictionModelAliases();
