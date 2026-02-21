# N-gram Java Code Token Predictor

A probabilistic N-gram language model for predicting Java code tokens at the method level.

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for dependency management, make sure it is installed. <br>
Then in the root folder run: <br>
```bash
uv sync
```
This command will sync the dependencies needed for running the script.

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
## Outputs

| File | Description |
|------|-------------|
| `Data/Assignment_1/dataset/ngram_dataset/` | Training, validation, and test `.txt` files |
| `results-self.json` | Predictions and perplexity on self-created test set |
| `results-provided.json` | Predictions and perplexity on provided test set |

## Hyperparameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| n | 3, 5, 7 | Best selected via validation perplexity |
| α (smoothing) | 0.01 | Higher values (0.1, 1.0) caused over-smoothing |
| min_freq | 3 | Minimum token frequency for vocabulary inclusion |
| Training set sizes | 15k / 25k / 35k | T1, T2, T3 respectively |


## Adding Your Own Test File
If you would like to test your own unique test file, simply add a new file to the root of this project with the name `my-test.txt` and it will run automatically after the provided file and the self-created test files run.
