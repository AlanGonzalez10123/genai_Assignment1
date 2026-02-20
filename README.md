# N-gram Java Code Token Predictor

A probabilistic N-gram language model for predicting Java code tokens at the method level.

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for dependency management, make sure it is installed. <br>
Then in the root folder run: <br>
```bash
uv sync
```

## Usage

All training, validation, and evaluation are handled by a single script. The workflow has two stages:

**Stage 1: Data collection (automatic, only runs once):**
```bash
uv run python main.py
```
The script automatically checks whether the dataset files already exist in the output directory. If they do, data collection is skipped and it proceeds straight to training. If they do not exist (i.e. first run), it will clone repositories, extract methods, and save the dataset files to `Data/Assignment_1/dataset/ngram_dataset/`. This may take over an hour on the first run.

**Stage 2: Training and evaluation (runs every time):**
After data collection, `main.py` loads the saved `.txt` files, trains all 9 model configurations, selects the best via validation perplexity, and evaluates on both test sets automatically.<br>
If you wish to retrain the model again after data collection, running the same command again will automatically do it without needing to re-collect data.
```bash
uv run python main.py
```
