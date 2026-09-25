import argparse
import json
import mimetypes
import sys
import uuid
from pathlib import Path
from urllib import request, error


def _get_json(base_url, path):
    with request.urlopen(f'{base_url}{path}', timeout=10) as response:
        return response.status, json.loads(response.read().decode('utf-8'))


def _multipart_post_json(base_url, path, fields, file_field, file_path):
    boundary = f'----object-counter-{uuid.uuid4().hex}'
    chunks = []
    for name, value in fields.items():
        chunks.extend([
            f'--{boundary}\r\n'.encode(),
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
            str(value).encode(),
            b'\r\n',
        ])

    file_bytes = Path(file_path).read_bytes()
    content_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
    chunks.extend([
        f'--{boundary}\r\n'.encode(),
        f'Content-Disposition: form-data; name="{file_field}"; filename="{Path(file_path).name}"\r\n'.encode(),
        f'Content-Type: {content_type}\r\n\r\n'.encode(),
        file_bytes,
        b'\r\n',
        f'--{boundary}--\r\n'.encode(),
    ])

    req = request.Request(
        f'{base_url}{path}',
        data=b''.join(chunks),
        headers={'Content-Type': f'multipart/form-data; boundary={boundary}'},
        method='POST',
    )
    with request.urlopen(req, timeout=30) as response:
        return response.status, json.loads(response.read().decode('utf-8'))


def main():
    parser = argparse.ArgumentParser(description='Smoke-test a running object-counter app.')
    parser.add_argument('--base-url', default='http://127.0.0.1:5001')
    parser.add_argument('--image', default='resources/images/boy.jpg')
    parser.add_argument('--threshold', default='0.9')
    parser.add_argument('--model-name', default=None)
    args = parser.parse_args()

    image_path = Path(args.image)
    if not image_path.exists():
        raise SystemExit(f'image not found: {image_path}')

    try:
        status, models = _get_json(args.base_url, '/models')
        assert status == 200, status
        count_model_name = args.model_name or models['default_count_model']
        prediction_model_name = args.model_name or models['default_prediction_model']
        model_names = [model['name'] for model in models['models']]
        assert count_model_name in model_names
        assert prediction_model_name in model_names

        count_fields = {'threshold': args.threshold, 'model_name': count_model_name}
        status, count_payload = _multipart_post_json(args.base_url, '/object-count', count_fields, 'file', image_path)
        assert status == 200, status
        assert 'current_objects' in count_payload
        assert 'total_objects' in count_payload

        prediction_fields = {'threshold': args.threshold, 'model_name': prediction_model_name}
        status, prediction_payload = _multipart_post_json(args.base_url, '/predictions', prediction_fields, 'file', image_path)
        assert status == 200, status
        assert prediction_payload['model_name'] == prediction_model_name
        assert 'predictions' in prediction_payload

        run_id = prediction_payload['id']
        status, fetched_run = _get_json(args.base_url, f'/prediction-runs/{run_id}')
        assert status == 200, status
        assert fetched_run['id'] == run_id
    except error.HTTPError as exc:
        body = exc.read().decode('utf-8', errors='replace')
        raise SystemExit(f'HTTP {exc.code}: {body}') from exc
    except Exception as exc:
        raise SystemExit(f'smoke test failed: {exc}') from exc

    print(json.dumps({
        'ok': True,
        'base_url': args.base_url,
        'count_model_name': count_model_name,
        'prediction_model_name': prediction_model_name,
        'prediction_run_id': run_id,
    }, indent=2))


if __name__ == '__main__':
    main()
