"""Run 150-item RAGAS evaluation in batches with model rotation to avoid rate limits."""
import json, time, sys
from typing import List, Dict

BASE = "http://localhost:8000"
GOLDEN_FILE = r"C:\Users\abhay\Downloads\enterprise_rag_golden_dataset\golden_dataset.json"
DOC_ID = "a62be742-d5e6-4910-8875-0f005425f747"
EMAIL = "abhi@gmail.com"
PASSWORD = "test12345"

# Model selection for evaluation
# Using paid OpenRouter model to avoid free tier rate limits
# Evaluation: 10 QA pairs * 4 conditions = 40 total queries (minimal cost)
OPENROUTER_MODELS = [
    "meta-llama/llama-3.1-8b-instruct",  # Paid model, no rate limits
]

# Choose provider: "huggingface" or "openrouter"
PROVIDER = "openrouter"  # Using OpenRouter paid model
MODELS = OPENROUTER_MODELS

BATCH_SIZE = 5  # 10 items / 2 batches (minimal for policy proof)
MAX_ITEMS = 10  # Only use first 10 QA pairs for evaluation
CONDITIONS = ["auto", "similarity", "hybrid_bm25", "mmr_cross_encoder"]

def login_and_get_token() -> str:
    """Login and get auth token."""
    import requests
    print("Step 1: Login")
    r = requests.post(f"{BASE}/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    if r.status_code != 200:
        print(f"  Login failed: {r.status_code} {r.text[:200]}")
        sys.exit(1)
    token = r.json()["access_token"]
    print(f"  OK - token: {token[:30]}...")
    return token

def get_document_id(token: str) -> str:
    """Get document ID (verify or fallback to first doc)."""
    import requests
    print(f"\nStep 2: Verify document")
    r = requests.get(f"{BASE}/api/documents/{DOC_ID}", headers={"Authorization": f"Bearer {token}"})
    if r.status_code != 200:
        r2 = requests.get(f"{BASE}/api/documents/list?limit=5", headers={"Authorization": f"Bearer {token}"})
        docs = r2.json()
        if not docs:
            print("  No documents found. Upload enterprise_policy_source.txt first.")
            sys.exit(1)
        doc = docs[0]
        doc_id = doc["id"]
        print(f"  Using: {doc_id}")
    else:
        doc = r.json()
        doc_id = DOC_ID

    print(f"  title:    {doc.get('title','?')}")
    print(f"  chunks:   {doc.get('chunk_count','?')}")
    print(f"  chunking: {doc.get('chunking_strategy','?')}")
    print(f"  embed:    {str(doc.get('embedding_model','')).split('/')[-1]}")
    print(f"  status:   {doc.get('status','?')}")
    return doc_id

def load_golden_dataset(doc_id: str) -> List[Dict]:
    """Load and categorize golden dataset."""
    print(f"\nStep 3: Load golden dataset")
    with open(GOLDEN_FILE) as f:
        golden = json.load(f)
    items = golden["golden_items"]
    
    # Limit to first MAX_ITEMS to avoid rate limits
    items = items[:MAX_ITEMS]
    
    for item in items:
        item["document_id"] = doc_id
    print(f"  {len(items)} items (limited from full dataset) pinned to doc {doc_id[:8]}...")

    threshold = [i for i in items if "does an event" in i["question"].lower() or "how should an event" in i["question"].lower()]
    comparison = [i for i in items if i["question"].lower().startswith("compare")]
    factual = [i for i in items if i not in threshold and i not in comparison]
    print(f"  factual={len(factual)}  threshold={len(threshold)}  comparison={len(comparison)}")
    return items

def split_into_batches(items: List[Dict], batch_size: int) -> List[List[Dict]]:
    """Split items into batches."""
    batches = []
    for i in range(0, len(items), batch_size):
        batches.append(items[i:i + batch_size])
    return batches

def switch_model(model: str, provider: str):
    """Switch the generation model via admin API."""
    import requests
    print(f"\n  Switching to {provider} model: {model}")
    # This would require an admin endpoint to change the model
    # For now, we'll note that this needs to be implemented
    # or the user needs to manually change it in .env
    if provider == "huggingface":
        print(f"  NOTE: Manual model switch required - update .env with:")
        print(f"    GENERATION_PROVIDER=huggingface")
        print(f"    HF_MODEL={model}")
        print(f"  Then restart the backend server.")
    else:
        print(f"  NOTE: Manual model switch required - update .env with:")
        print(f"    GENERATION_PROVIDER=openrouter")
        print(f"    OPENROUTER_API_KEY=your_api_key")
        print(f"    OPENROUTER_MODEL={model}")
        print(f"  Then restart the backend server.")
        print(f"  Current model is a paid model - ensure you have credits in your OpenRouter account.")

def run_batch(batch: List[Dict], batch_num: int, model: str, token: str) -> Dict:
    """Run evaluation for a single batch."""
    import requests
    print(f"\n{'='*60}")
    print(f"Running Batch {batch_num + 1} with model: {model}")
    print(f"Items: {len(batch)} x {len(CONDITIONS)} conditions = {len(batch) * len(CONDITIONS)} queries")
    print(f"Estimated time: ~{len(batch) * len(CONDITIONS) * 9 // 60} min at ~9s/query")
    print(f"{'='*60}")

    payload = {
        "golden_items": batch,
        "conditions": CONDITIONS
    }

    start = time.time()
    er = requests.post(
        f"{BASE}/api/admin/evaluate",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=payload,
        timeout=7200
    )
    elapsed = time.time() - start

    print(f"  Response: {er.status_code}  ({elapsed/60:.1f} min)")
    if er.status_code != 200:
        print(f"  ERROR: {er.text[:600]}")
        return None

    result = er.json()
    
    # Print batch results
    print(f"\n  Batch {batch_num + 1} Results:")
    print(f"  {'Condition':<22} {'Overall':>7} {'Faith':>7} {'Relev':>7} {'Prec':>7} {'Recall':>7} {'Tokens':>7} {'ms/q':>7}")
    print("  " + "-" * 76)
    
    rows = sorted(result["results"], key=lambda x: x["overall_score"], reverse=True)
    for i, row in enumerate(rows):
        ph = " *placeholder*" if row.get("ragas_placeholder") else ""
        print(
            f"  {row['condition']:<19}"
            f" {row['overall_score']*100:>6.1f}%"
            f" {row['faithfulness']*100:>6.1f}%"
            f" {row['answer_relevancy']*100:>6.1f}%"
            f" {row['context_precision']*100:>6.1f}%"
            f" {(row['context_recall'] or 0)*100:>6.1f}%"
            f" {row['avg_tokens']:>7.0f}"
            f" {row['avg_latency_ms']:>6.0f}ms"
            + ph
        )
    
    return result

def main():
    """Main execution."""
    token = login_and_get_token()
    doc_id = get_document_id(token)
    items = load_golden_dataset(doc_id)
    
    # Split into batches
    batches = split_into_batches(items, BATCH_SIZE)
    print(f"\nStep 4: Split into {len(batches)} batches of {BATCH_SIZE} items each")
    
    all_results = []
    
    for batch_num, batch in enumerate(batches):
        # Rotate model for each batch
        model = MODELS[batch_num % len(MODELS)]
        
        # Note: User needs to manually switch model in .env and restart server
        # Or we could implement an admin endpoint for this
        if batch_num > 0:
            print(f"\n{'='*60}")
            print(f"PAUSE: Please switch model to '{model}' in .env file")
            switch_model(model, PROVIDER)
            print(f"Then restart the backend server and press Enter to continue...")
            print(f"{'='*60}")
            input()
        
        result = run_batch(batch, batch_num, model, token)
        if result:
            all_results.append({
                "batch_num": batch_num + 1,
                "model": model,
                "result": result
            })
        
        # Save intermediate results
        out = f"batch_{batch_num + 1}_results.json"
        with open(out, "w") as f:
            json.dump(all_results, f, indent=2)
        print(f"\n  Saved intermediate results -> {out}")
    
    # Aggregate final results
    print(f"\n{'='*80}")
    print("FINAL AGGREGATED RESULTS")
    print(f"{'='*80}")
    
    # Aggregate by condition across all batches
    condition_aggregates = {}
    for batch_data in all_results:
        for row in batch_data["result"]["results"]:
            cond = row["condition"]
            if cond not in condition_aggregates:
                condition_aggregates[cond] = {
                    "overall_score": 0,
                    "faithfulness": 0,
                    "answer_relevancy": 0,
                    "context_precision": 0,
                    "context_recall": 0,
                    "avg_tokens": 0,
                    "avg_latency_ms": 0,
                    "n_items": 0,
                    "count": 0
                }
            agg = condition_aggregates[cond]
            agg["overall_score"] += row["overall_score"]
            agg["faithfulness"] += row["faithfulness"]
            agg["answer_relevancy"] += row["answer_relevancy"]
            agg["context_precision"] += row["context_precision"]
            agg["context_recall"] += (row["context_recall"] or 0)
            agg["avg_tokens"] += row["avg_tokens"]
            agg["avg_latency_ms"] += row["avg_latency_ms"]
            agg["n_items"] += row["n_items"]
            agg["count"] += 1
    
    # Calculate averages
    for cond, agg in condition_aggregates.items():
        count = agg["count"]
        agg["overall_score"] /= count
        agg["faithfulness"] /= count
        agg["answer_relevancy"] /= count
        agg["context_precision"] /= count
        agg["context_recall"] /= count
        agg["avg_tokens"] /= count
        agg["avg_latency_ms"] /= count
    
    # Print aggregated results
    print(f"  {'Condition':<22} {'Overall':>7} {'Faith':>7} {'Relev':>7} {'Prec':>7} {'Recall':>7} {'Tokens':>7} {'ms/q':>7}")
    print("  " + "-" * 76)
    
    rows = sorted(condition_aggregates.items(), key=lambda x: x[1]["overall_score"], reverse=True)
    for cond, agg in rows:
        print(
            f"  {cond:<19}"
            f" {agg['overall_score']*100:>6.1f}%"
            f" {agg['faithfulness']*100:>6.1f}%"
            f" {agg['answer_relevancy']*100:>6.1f}%"
            f" {agg['context_precision']*100:>6.1f}%"
            f" {agg['context_recall']*100:>6.1f}%"
            f" {agg['avg_tokens']:>7.0f}"
            f" {agg['avg_latency_ms']:>6.0f}ms"
        )
    
    # Save final results
    final_out = r"C:\Users\abhay\Downloads\enterprise_rag_golden_dataset\eval_results_aggregated.json"
    with open(final_out, "w") as f:
        json.dump({
            "total_items": len(items),
            "n_batches": len(batches),
            "batch_size": BATCH_SIZE,
            "models_used": MODELS[:len(batches)],
            "condition_aggregates": condition_aggregates,
            "batch_results": all_results
        }, f, indent=2)
    print(f"\n  Saved final aggregated results -> {final_out}")

if __name__ == "__main__":
    main()
