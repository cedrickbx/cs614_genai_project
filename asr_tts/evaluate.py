import json
from difflib import SequenceMatcher
import os

REFERENCE_FILE = "reference_sentences.txt"
LOG_FILE = "logs/interactions.jsonl"
OUTPUT_FILE = "logs/asr_hit_rate_results.txt"


def load_references(path=REFERENCE_FILE):
    """Load reference sentences from file."""
    with open(path, "r") as f:
        refs = [line.strip().lower() for line in f if line.strip()]
    print(f"📘 Loaded {len(refs)} reference sentences.")
    return refs


def evaluate_asr_hit_rate(log_file=LOG_FILE, references=None, output_file=OUTPUT_FILE):
    """Compare each transcript to its reference and compute similarity scores."""
    if references is None:
        raise ValueError("Reference sentences not loaded.")

    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # Load ASR logs
    with open(log_file, "r") as f:
        logs = [json.loads(line) for line in f]

    # Compare up to the smaller of the two counts
    n = min(len(logs), len(references))
    scores = []

    with open(output_file, "w") as out:
        out.write("=== ASR Batch Evaluation Results ===\n\n")

        for i in range(n):
            entry = logs[i]
            transcript = entry.get("transcript", "").lower().strip()
            ref = references[i]

            similarity = SequenceMatcher(None, transcript, ref).ratio() * 100
            scores.append(similarity)

            # Write to file
            out.write(f"[{i+1}]\n")
            out.write(f"Transcript: {transcript}\n")
            out.write(f"Reference : {ref}\n")
            out.write(f"Hit Rate  : {similarity:.2f}%\n\n")

            # Print progress to console
            print(f"[{i+1}] {similarity:.2f}% match")

        # Compute average
        avg_hit = sum(scores) / n if n > 0 else 0
        out.write(f"Average ASR Hit Rate across {n} sentences: {avg_hit:.2f}%\n")
        print(f"\nAverage ASR Hit Rate across {n} sentences: {avg_hit:.2f}%")

    print(f"Results saved to: {output_file}")
    return avg_hit


if __name__ == "__main__":
    refs = load_references()
    evaluate_asr_hit_rate(references=refs)
