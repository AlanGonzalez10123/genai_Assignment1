# import dependencies
from javalang.tokenizer import tokenize
from collections import defaultdict
from pathlib import Path
import pandas as pd
import subprocess
import statistics
import javalang
import requests
import random
import shutil
import glob
import json
import math
import os


# Mine and prepare data (replicate the pipeline we saw during lab)
def fetch_top_java_repos(num_repos=200, per_page=100):
    """
    Fetch top-starred Java repositories from GitHub API.
    Skips forked repos to avoid duplicate code.
    """
    repos = []
    page = 1

    while len(repos) < num_repos:
        url = "https://api.github.com/search/repositories"
        params = {
            "q": "language:java stars:>1000",
            "sort": "stars",
            "order": "desc",
            "per_page": per_page,
            "page": page
        }

        response = requests.get(url, params=params)

        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            break

        data = response.json()
        items = data.get("items", [])

        if not items:
            break

        for item in items:
            if item.get("fork", False):
                continue

            repos.append({
                "full_name": item["full_name"],
                "clone_url": item["clone_url"],
                "stars": item["stargazers_count"],
                "description": item.get("description", "")
            })

        page += 1

        if len(repos) >= num_repos:
            break

    return repos[:num_repos]

def clone_repo(clone_url, dest_dir):
    """
    Shallow clone a repository.
    Returns True if successful, False otherwise.
    """
    try:
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir)

        cmd = ["git", "clone", "--depth", "1", "--quiet", clone_url, dest_dir]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)

        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"  Timeout cloning {clone_url}")
        return False
    except Exception as e:
        print(f"  Error: {e}")
        return False


def find_java_files(repo_path):
    """
    Find all .java files in a repository.
    Excludes test files and common non-source directories.
    """
    java_files = []
    exclude_patterns = ["test", "tests", "example", "examples", "sample", "demo", "generated"]

    for root, dirs, files in os.walk(repo_path):
        root_lower = root.lower()
        if any(pattern in root_lower for pattern in exclude_patterns):
            continue

        for file in files:
            if file.endswith(".java"):
                java_files.append(os.path.join(root, file))

    return java_files


def select_java_files(java_files, max_files):
    """
    Randomly select up to max_files from the list.
    """
    if len(java_files) <= max_files:
        return java_files
    return random.sample(java_files, max_files)


def find_java_files(repo_path):
    """
    Find all .java files in a repository.
    Excludes test files and common non-source directories.
    """
    java_files = []
    exclude_patterns = ["test", "tests", "example", "examples", "sample", "demo", "generated"]

    for root, dirs, files in os.walk(repo_path):
        root_lower = root.lower()
        if any(pattern in root_lower for pattern in exclude_patterns):
            continue

        for file in files:
            if file.endswith(".java"):
                java_files.append(os.path.join(root, file))

    return java_files


def select_java_files(java_files, max_files):
    """
    Randomly select up to max_files from the list.
    """
    if len(java_files) <= max_files:
        return java_files
    return random.sample(java_files, max_files)


def read_file_content(file_path):
    """Read file content with multiple encoding fallbacks."""
    encodings = ['utf-8', 'latin-1', 'cp1252']

    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue

    return None


def extract_method_source(source_code, method_node, lines):
    """Extract the source code of a method by counting braces."""
    try:
        start_line = method_node.position.line - 1

        brace_count = 0
        started = False
        end_line = start_line

        for i in range(start_line, len(lines)):
            line = lines[i]
            for char in line:
                if char == '{':
                    brace_count += 1
                    started = True
                elif char == '}':
                    brace_count -= 1

            if started and brace_count == 0:
                end_line = i
                break

        method_lines = lines[start_line:end_line + 1]
        return '\n'.join(method_lines)

    except Exception:
        return None


def extract_methods_from_file(file_path, repo_name):
    """Parse a Java file and extract all methods."""
    methods = []

    source_code = read_file_content(file_path)
    if source_code is None:
        return methods

    lines = source_code.split('\n')

    try:
        tree = javalang.parse.parse(source_code)

        for path, node in tree.filter(javalang.tree.MethodDeclaration):
            method_source = extract_method_source(source_code, node, lines)

            if method_source:
                methods.append({
                    "repo": repo_name,
                    "file": os.path.basename(file_path),
                    "method_name": node.name,
                    "source": method_source
                })

    except javalang.parser.JavaSyntaxError:
        pass
    except Exception:
        pass

    return methods


def contains_non_ascii(text):
    """Check if text contains non-ASCII characters."""
    try:
        text.encode('ascii')
        return False
    except UnicodeEncodeError:
        return True


def count_tokens(source_code):
    """Count the number of Java tokens in source code."""
    try:
        tokens = list(tokenize(source_code))
        return len(tokens)
    except:
        return 0


# TODO: Write your filtering functions here

def tokenize_method(source_code):
    """Tokenize Java source code into space-separated tokens."""
    try:
        tokens = list(tokenize(source_code))
        token_values = [token.value for token in tokens]
        return ' '.join(token_values)
    except:
        return None


def is_clean_method(tokenized_code):
    """Check if method is clean (single method, complete)."""
    method_keywords = tokenized_code.count("public ") + tokenized_code.count("private ") + tokenized_code.count("protected ")
    if method_keywords > 1:
        return False
    if not tokenized_code.endswith("}"):
        return False
    return True

def save_txt(data, filename):
    """Save tokenized methods to a text file (one per line)."""
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, 'w', encoding='utf-8', errors='replace') as f:
        for method in data:
            f.write(method['tokenized_code'] + '\n')
    return filepath


def collect_data():
    # Fetch repositories
    print("Fetching top Java repositories from GitHub...")
    repo_data = fetch_top_java_repos(num_repos=700)
    df_repos = pd.DataFrame(repo_data)

    print(f"\nFetched {len(df_repos)} repositories")
    print(f"\nTop 10 repos by stars:")
    print(df_repos.head(10))

    # Clone repositories
    cloned_repos = []
    failed_repos = []

    print(f"Cloning {len(df_repos)} repositories...\n")

    for idx, row in df_repos.iterrows():
        repo_name = row["full_name"]
        clone_url = row["clone_url"]

        safe_name = repo_name.replace("/", "_")
        dest_dir = os.path.join(CLONE_DIR, safe_name)

        print(f"[{idx+1}/{len(df_repos)}] Cloning {repo_name}...", end=" ")

        success = clone_repo(clone_url, dest_dir)

        if success:
            cloned_repos.append({
                "repo_name": repo_name,
                "local_path": dest_dir,
                "stars": row["stars"]
            })
            print("done")
        else:
            failed_repos.append(repo_name)
            print("failed")

    print(f"\n\nSummary:")
    print(f"  Successfully cloned: {len(cloned_repos)}")
    print(f"  Failed: {len(failed_repos)}")


    # Find and select Java files from each repo
    repo_java_files = {}
    all_selected_files = []

    print(f"Finding Java files (selecting up to {CLASSES_PER_REPO} per repo)...\n")

    for repo_info in cloned_repos:
        repo_name = repo_info["repo_name"]
        repo_path = repo_info["local_path"]

        java_files = find_java_files(repo_path)

        if not java_files:
            print(f"  {repo_name}: No Java files found")
            continue

        selected = select_java_files(java_files, max_files=CLASSES_PER_REPO)

        repo_java_files[repo_name] = {
            "total_files": len(java_files),
            "selected_files": [os.path.relpath(f, repo_path) for f in selected],
            "remaining_files": len(java_files) - len(selected)
        }

        all_selected_files.extend([(repo_name, f) for f in selected])
        print(f"  {repo_name}: {len(selected)}/{len(java_files)} files selected")

    print(f"\nTotal Java files selected: {len(all_selected_files)}")

    # Extract methods from all selected files
    all_methods = []

    print(f"Extracting methods from {len(all_selected_files)} files...\n")

    for i, (repo_name, file_path) in enumerate(all_selected_files):
        if (i + 1) % 100 == 0:
            print(f"  Processed {i + 1}/{len(all_selected_files)} files...")

        methods = extract_methods_from_file(file_path, repo_name)
        all_methods.extend(methods)

    print(f"\nTotal methods extracted: {len(all_methods)}")


    # Apply filters
    filtered_methods = []

    stats = {
        "total": len(all_methods),
        "non_ascii_dropped": 0,
        "too_short_dropped": 0,
        "kept": 0
    }

    print(f"Filtering {len(all_methods)} methods...\n")

    for method in all_methods:
        source = method["source"]

        if contains_non_ascii(source):
            stats["non_ascii_dropped"] += 1
            continue

        token_count = count_tokens(source)
        if token_count < MIN_TOKENS:
            stats["too_short_dropped"] += 1
            continue

        # TODO: Apply your filters here

        method["token_count"] = token_count
        filtered_methods.append(method)
        stats["kept"] += 1

    print(f"Filtering Results:")
    print(f"  Total methods:        {stats['total']}")
    print(f"  Dropped (non-ASCII):  {stats['non_ascii_dropped']}")
    print(f"  Dropped (< {MIN_TOKENS} tokens): {stats['too_short_dropped']}")
    print(f"  -------------------------")
    print(f"  Methods kept:         {stats['kept']}")


    # Tokenize all methods
    tokenized_methods = []

    print(f"Tokenizing {len(filtered_methods)} methods...\n")

    for method in filtered_methods:
        tokenized = tokenize_method(method["source"])

        if tokenized:
            tokenized_methods.append({
                "repo": method["repo"],
                "file": method["file"],
                "method_name": method["method_name"],
                "tokenized_code": tokenized,
                "token_count": method["token_count"]
            })

    print(f"Successfully tokenized: {len(tokenized_methods)} methods")

    # Show example
    print(f"\nExample tokenized method:")
    if tokenized_methods:
        example = tokenized_methods[0]
        print(f"  Repo: {example['repo']}")
        print(f"  File: {example['file']}")
        print(f"  Method: {example['method_name']}")
        print(f"  Tokens ({example['token_count']}):")
        print(f"  {example['tokenized_code'][:200]}..." if len(example['tokenized_code']) > 200 else f"  {example['tokenized_code']}")


    # Clean
    print(f"Before cleaning: {len(tokenized_methods)}")
    tokenized_methods = [m for m in tokenized_methods if is_clean_method(m['tokenized_code'])]
    print(f"After cleaning: {len(tokenized_methods)}")

    # Deduplicate
    seen = set()
    unique_methods = []
    for m in tokenized_methods:
        if m['tokenized_code'] not in seen:
            seen.add(m['tokenized_code'])
            unique_methods.append(m)

    print(f"After dedup: {len(unique_methods)}")
    tokenized_methods = unique_methods

    # Shuffle
    random.seed(42)
    random.shuffle(tokenized_methods)

    # Fixed validation and test sizes
    VAL_SIZE = 1000
    TEST_SIZE = 1000

    total_size = len(tokenized_methods)

    # First reserve validation and test sets
    val_data = tokenized_methods[:VAL_SIZE]
    test_data = tokenized_methods[VAL_SIZE:VAL_SIZE + TEST_SIZE]

    # Remaining data for training
    remaining_data = tokenized_methods[VAL_SIZE + TEST_SIZE:]

    T1_SIZE = 15000
    T2_SIZE = 25000
    T3_SIZE = 35000

    start = 0
    end = start + T1_SIZE
    T1 = remaining_data[start:end]

    start = end
    end = start + T2_SIZE
    T2 = remaining_data[start:end]

    start = end
    end = start + T3_SIZE
    T3 = remaining_data[start:end]

    print("\nDataset Split:")
    print(f"  T1: {len(T1)} methods")
    print(f"  T2: {len(T2)} methods")
    print(f"  T3: {len(T3)} methods")
    print(f"  Validation: {len(val_data)} methods")
    print(f"  Test: {len(test_data)} methods")


    print("Saving dataset files...\n")

    # Save training sets
    t1_path = save_txt(T1, "train_T1.txt")
    print(f"  Saved: {t1_path}")

    t2_path = save_txt(T2, "train_T2.txt")
    print(f"  Saved: {t2_path}")

    t3_path = save_txt(T3, "train_T3.txt")
    print(f"  Saved: {t3_path}")

    # Save validation and test
    val_path = save_txt(val_data, "val.txt")
    print(f"  Saved: {val_path}")

    test_path = save_txt(test_data, "test.txt")
    print(f"  Saved: {test_path}")


    # Save metadata
    metadata = {
        "description": "Metadata for N-gram dataset with three capped training sets.",
        "dataset_stats": {
            "T1_size": len(T1),
            "T2_size": len(T2),
            "T3_size": len(T3),
            "val_size": len(val_data),
            "test_size": len(test_data),
            "total_repos": len(repo_java_files),
            "min_tokens": MIN_TOKENS
        },
        "repos_used": repo_java_files
    }

    metadata_path = os.path.join(OUTPUT_DIR, "metadata.json")
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)

    print(f"  Saved: {metadata_path}")
    print(f"\nAll files saved to: {OUTPUT_DIR}/")


    all_token_counts = [m['token_count'] for m in tokenized_methods]

    print("=" * 50)
    print("         DATASET CREATION SUMMARY")
    print("=" * 50)

    print(f"\nRepositories:")
    print(f"   Cloned:    {len(cloned_repos)}")
    print(f"   Failed:    {len(failed_repos)}")

    print(f"\nJava Files:")
    print(f"   Selected:  {len(all_selected_files)}")

    print(f"\nMethods:")
    print(f"   Extracted: {stats['total']}")
    print(f"   Filtered:  {stats['total'] - stats['kept']} removed")
    print(f"   Final:     {len(tokenized_methods)}")

    print(f"\nToken Statistics:")
    print(f"   Min:    {min(all_token_counts)}")
    print(f"   Max:    {max(all_token_counts)}")
    print(f"   Mean:   {statistics.mean(all_token_counts):.1f}")
    print(f"   Median: {statistics.median(all_token_counts):.1f}")

    print(f"\nDataset Splits:")
    print(f"   T1 (≤15k):  {len(T1):,} methods")
    print(f"   T2 (≤25k):  {len(T2):,} methods")
    print(f"   T3 (≤35k):  {len(T3):,} methods")
    print(f"   Validation: {len(val_data):,} methods")
    print(f"   Test:       {len(test_data):,} methods")

    print(f"\nOutput Files:")
    print(f"   {OUTPUT_DIR}/train_T1.txt")
    print(f"   {OUTPUT_DIR}/train_T2.txt")
    print(f"   {OUTPUT_DIR}/train_T3.txt")
    print(f"   {OUTPUT_DIR}/val.txt")
    print(f"   {OUTPUT_DIR}/test.txt")
    print(f"   {OUTPUT_DIR}/metadata.json")


    print("\n" + "=" * 50)
    print("         DATASET READY FOR N-GRAM TRAINING")
    print("=" * 50)

# Build N-Grams
#
#

def build_vocabulary(dataset, min_freq=3):
    freq = defaultdict(int)
    
    for method in dataset:
        tokens = method['tokenized_code'].split()
        for token in tokens:
            freq[token] += 1
    
    vocab = {token for token, count in freq.items() if count >= min_freq}
    return vocab

def replace_unknown_tokens(dataset, vocabulary):
    new_dataset = []
    
    for method in dataset:
        tokens = method['tokenized_code'].split()
        new_tokens = []
        
        for token in tokens:
            if token in vocabulary:
                new_tokens.append(token)
            else:
                new_tokens.append("<UNK>")
        
        new_dataset.append(new_tokens)
    
    return new_dataset

def add_sentence_tokens(tokens, n):
    """
    Add start and end tokens for an n-gram model.
    """
    start_tokens = ["<s>"] * (n - 1)
    end_tokens = ["</s>"]
    return start_tokens + tokens + end_tokens

def prepare_training_tokens(dataset, n, vocabulary=None):
    all_tokens = []

    for method in dataset:
        tokens = method['tokenized_code'].split()

        # Replace OOV tokens if vocabulary is provided
        if vocabulary is not None:
            tokens = [t if t in vocabulary else "<UNK>" for t in tokens]

        tokens = add_sentence_tokens(tokens, n)
        all_tokens.append(tokens)

    return all_tokens

def build_ngram_model(token_lists, n):
    ngram_counts = defaultdict(int)
    context_counts = defaultdict(int)
    
    for tokens in token_lists:
        for i in range(len(tokens) - n + 1):
            ngram = tuple(tokens[i:i+n])
            context = tuple(tokens[i:i+n-1])
            
            ngram_counts[ngram] += 1
            context_counts[context] += 1
    
    return ngram_counts, context_counts

def compute_perplexity(dataset, n, ngram_counts, context_counts, vocabulary, alpha=0.01):
    total_log_prob = 0.0
    total_tokens = 0
    vocab_size = len(vocabulary)
    
    for method in dataset:
        tokens = method['tokenized_code'].split()
        
        # replace unknown tokens
        tokens = [t if t in vocabulary else "<UNK>" for t in tokens]
        
        # add boundary tokens
        tokens = add_sentence_tokens(tokens, n)
        
        for i in range(n - 1, len(tokens)):
            context = tuple(tokens[i - (n - 1):i])
            target = tokens[i]
            
            ngram = context + (target,)
            
            prob = smoothed_probability(
                ngram,
                ngram_counts,
                context_counts,
                vocab_size,
                alpha
            )
            
            if target != "<s>":
              total_log_prob += math.log(prob)
              total_tokens += 1
    
    perplexity = math.exp(-total_log_prob / total_tokens)
    return perplexity


def smoothed_probability(ngram, ngram_counts, context_counts, vocab_size, alpha=0.01):
    context = ngram[:-1]
    
    ngram_count = ngram_counts.get(ngram, 0)
    context_count = context_counts.get(context, 0)
    
    numerator = ngram_count + alpha
    denominator = context_count + alpha * vocab_size
    
    return numerator / denominator

def read_tokenized_methods_from_txt(path):
    methods = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                methods.append(line)
    return methods

def predict_next_token(context, ngram_counts, context_counts, vocabulary, alpha=0.01):
    vocab_size = len(vocabulary)
    best_token = None
    best_prob = -1.0
    
    for token in vocabulary:
        ngram = tuple(context) + (token,)
        prob = smoothed_probability(
            ngram,
            ngram_counts,
            context_counts,
            vocab_size,
            alpha
        )
        
        if prob > best_prob:
            best_prob = prob
            best_token = token
    
    return best_token, best_prob

def evaluate_single_method(
    tokenized_code,
    n,
    ngram_counts,
    context_counts,
    vocabulary,
    alpha=1.0
):
    tokens = tokenized_code.split()
    
    # replace unknown tokens
    tokens = [t if t in vocabulary else "<UNK>" for t in tokens]
    
    # add boundary tokens
    tokens = add_sentence_tokens(tokens, n)
    
    predictions = []
    
    for i in range(n - 1, len(tokens)):
        context = tokens[i - (n - 1):i]
        ground_truth = tokens[i]
        
        pred_token, pred_prob = predict_next_token(
            context,
            ngram_counts,
            context_counts,
            vocabulary,
            alpha
        )
        
        predictions.append({
            "context": context,
            "predToken": pred_token,
            "predProbability": pred_prob,
            "groundTruth": ground_truth
        })
    
    return predictions

def evaluate_test_file(
    test_file_path,
    test_set_name,
    n,
    ngram_counts,
    context_counts,
    vocabulary,
    alpha=1
):
    print(f"\nEvaluating test set: {test_set_name}")
    print(f"Loading methods from: {test_file_path}")
    
    methods = read_tokenized_methods_from_txt(test_file_path)
    print(f"Total methods to evaluate: {len(methods)}")
    
    total_log_prob = 0.0
    total_tokens = 0
    
    data = []
    
    for idx, method in enumerate(methods):
        
        if (idx + 1) % 50 == 0:
            print(f"  Processed {idx + 1}/{len(methods)} methods...")
        
        predictions = evaluate_single_method(
            method,
            n,
            ngram_counts,
            context_counts,
            vocabulary,
            alpha
        )
        
        # accumulate perplexity from ground truth probabilities
        for p in predictions:
            context = p["context"]
            gt = p["groundTruth"]
            
            ngram = tuple(context) + (gt,)
            prob = smoothed_probability(
                ngram,
                ngram_counts,
                context_counts,
                len(vocabulary),
                alpha
            )
            
            total_log_prob += math.log(prob)
            total_tokens += 1
        
        data.append({
            "index": f"ID{idx+1}",
            "tokenizedCode": method,
            "contextWindow": n,
            "predictions": predictions
        })
    
    print(f"\nFinished evaluating {len(methods)} methods.")
    print(f"Total tokens evaluated: {total_tokens}")
    
    perplexity = math.exp(-total_log_prob / total_tokens)
    
    print(f"Final Perplexity: {perplexity:.4f}")
    
    return {
        "testSet": test_set_name,
        "perplexity": perplexity,
        "data": data
    }

def write_json(output, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)



# Generate output files
if __name__ == "__main__":
    # Configuration
    CLONE_DIR = "Data/Assignment_1/dataset/java_repos"
    OUTPUT_DIR = "Data/Assignment_1/dataset/ngram_dataset"

    CLASSES_PER_REPO = 40   # Java files to sample per repo
    MIN_TOKENS = 10         # Minimum tokens per method

    VAL_SIZE = 1000
    TEST_SIZE = 1000

    # Create directories
    os.makedirs(CLONE_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Setup complete!")
    print(f"Clone directory: {CLONE_DIR}")
    print(f"Output directory: {OUTPUT_DIR}")


    #collect_data()

    # Load pre-saved datasets from disk (avoids re-cloning)
    def load_txt_as_dataset(filename):
        """Load a tokenized .txt file back into the list-of-dicts format expected by the model functions."""
        filepath = os.path.join(OUTPUT_DIR, filename)
        dataset = []
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    dataset.append({'tokenized_code': line})
        return dataset

    T1 = load_txt_as_dataset("train_T1.txt")
    T2 = load_txt_as_dataset("train_T2.txt")
    T3 = load_txt_as_dataset("train_T3.txt")
    val_data = load_txt_as_dataset("val.txt")
    test_data = load_txt_as_dataset("test.txt")

    print(f"Loaded T1: {len(T1)}, T2: {len(T2)}, T3: {len(T3)}, val: {len(val_data)}, test: {len(test_data)}")

    vocab_T1 = build_vocabulary(T1)
    vocab_T2 = build_vocabulary(T2)
    vocab_T3 = build_vocabulary(T3)

    print("Vocabulary sizes:")
    print("T1:", len(vocab_T1))
    print("T2:", len(vocab_T2))
    print("T3:", len(vocab_T3))

    val_tokens_T1 = replace_unknown_tokens(val_data, vocab_T1)
    test_tokens_T1 = replace_unknown_tokens(test_data, vocab_T1)

    train_tokens_T1_3gram = prepare_training_tokens(T1, 5, vocabulary=vocab_T1)


    # prepare training tokens
    train_tokens = prepare_training_tokens(T1, 3)

    # build model
    ngram_counts, context_counts = build_ngram_model(train_tokens, 3)

    # compute validation perplexity
    val_perplexity = compute_perplexity(
        val_data,
        3,
        ngram_counts,
        context_counts,
        vocab_T1.union({"<s>", "</s>", "<UNK>"})
    )

    print("Validation Perplexity:", val_perplexity)


    training_sets = {
        "T1": T1,
        "T2": T2,
        "T3": T3
    }

    n_values = [3, 5, 7]

    results = []

    for train_name, train_data in training_sets.items():
        
        # Build vocabulary
        vocab = build_vocabulary(train_data)
        vocab.update({"<s>", "</s>", "<UNK>"})
        print(len(vocab))
        
        for n in n_values:
            print(f"\nTraining {n}-gram on {train_name}...")
            
            # Prepare padded training tokens
            train_tokens = prepare_training_tokens(train_data, n, vocabulary=vocab)
            
            # Build model
            ngram_counts, context_counts = build_ngram_model(train_tokens, n)
            
            
            # Compute validation perplexity
            val_perplexity = compute_perplexity(
                val_data,
                n,
                ngram_counts,
                context_counts,
                vocab
            )
            
            print(f"Validation Perplexity: {val_perplexity:.4f}")
            
            results.append({
                "train_set": train_name,
                "n": n,
                "perplexity": val_perplexity,
                "model": (ngram_counts, context_counts, vocab)
            })


    best_model = min(results, key=lambda x: x["perplexity"])

    print("\nBest configuration:")
    print("Training set:", best_model["train_set"])
    print("n:", best_model["n"])
    print("Validation perplexity:", best_model["perplexity"])


    best_ngram_counts, best_context_counts, best_vocab = best_model["model"]
    best_n = best_model["n"]

    # Self-created test set
    self_results = evaluate_test_file(
        "Data/Assignment_1/dataset/ngram_dataset/test.txt",
        "self_created.txt",
        best_n,
        best_ngram_counts,
        best_context_counts,
        best_vocab
    )

    write_json(self_results, "results-self.json")


    # Provided test set
    provided_results = evaluate_test_file(
        "provided.txt",
        "provided.txt",
        best_n,
        best_ngram_counts,
        best_context_counts,
        best_vocab
    )

    write_json(provided_results, "results-provided.json")