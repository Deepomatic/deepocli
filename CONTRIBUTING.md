# Development

To start developing on Deepomatic CLI, clone the repo:

```
git clone https://github.com/Deepomatic/deepocli
```

Changes should broadly follow the [PEP 8][pep-8] style conventions, and we recommend you set up your editor to automatically indicate non-conforming styles.
`flake8` checks are enforced by CI.

## Setup

### Using dmake

```bash
dmake shell deepocli
```

### Using a virtualenv

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r deploy/deepomatic-cli/requirements.dev.txt
pip install -e .
```

## Testing

```bash
pytest -vv
```
