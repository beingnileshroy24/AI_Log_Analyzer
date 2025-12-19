import pandas as pd
import os
import re
import numpy as np
import hdbscan
from sklearn.feature_extraction.text import TfidfVectorizer
from config import PROCESSED_DIR

def clean_text(text):
    text = re.sub(r'\d+', '', text)
    text = re.sub(r'[^\w\s]', ' ', text)
    return str(text).lower().strip()

def run_clustering(staging_dir):
    print("\n🚀 STARTING AI CLUSTERING (HDBSCAN)...")
    
    all_log_data = []
    if not os.path.exists(staging_dir): return

    # 1. Load Data
    for filename in os.listdir(staging_dir):
        filepath = os.path.join(staging_dir, filename)
        if filename.lower().endswith(('.txt', '.log', '.csv')):
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                for line in lines:
                    if line.strip():
                        all_log_data.append({'Original_Log': line.strip()})
            except: pass

    df_logs = pd.DataFrame(all_log_data)
    print(f"✅ Loaded {len(df_logs)} log lines.")

    if df_logs.empty: return

    # 2. Vectorize
    df_logs['Cleaned_Log'] = df_logs['Original_Log'].apply(clean_text)
    
    my_stop_words = list(TfidfVectorizer(stop_words='english').get_stop_words())
    my_stop_words.extend(["info", "error", "warn", "timestamp", "at", "failed"])

    vectorizer = TfidfVectorizer(max_features=500, stop_words=my_stop_words)
    X = vectorizer.fit_transform(df_logs['Cleaned_Log'])
    X_dense = X.toarray()

    # 3. Clustering
    clusterer = hdbscan.HDBSCAN(min_cluster_size=5, min_samples=2)
    df_logs['Cluster_ID'] = clusterer.fit_predict(X_dense)
    unique_clusters = sorted(df_logs['Cluster_ID'].unique())
    print(f"✅ Clusters Found: {unique_clusters}")

    # 4. Labeling
    domain_keywords = {
        "agreement": ["contract", "signed", "nda", "terms"],
        "system_log": ["cpu", "disk", "kernel", "boot", "service"],
        "app_log": ["login", "http", "api", "json", "exception"],
        "governance_log": ["audit", "policy", "compliance", "gdpr"]
    }

    cluster_map = {}
    for cid in unique_clusters:
        if cid == -1:
            cluster_map[cid] = "unstructured_log" # Noise
            continue
            
        indices = df_logs.index[df_logs['Cluster_ID'] == cid].tolist()
        centroid = np.mean(X_dense[indices], axis=0)
        top_indices = centroid.argsort()[-10:][::-1]
        top_terms = vectorizer.get_feature_names_out()[top_indices]

        best_match = "app_log"
        highest_score = 0
        for cat, keys in domain_keywords.items():
            score = sum(1 for term in top_terms if term in keys)
            if score > highest_score:
                highest_score = score
                best_match = cat
        
        cluster_map[cid] = best_match
        print(f"   👉 Cluster {cid} -> {best_match.upper()} (Terms: {list(top_terms)})")

    df_logs['Category'] = df_logs['Cluster_ID'].map(cluster_map)

    # 5. Distribute
    for cat in df_logs['Category'].unique():
        subset = df_logs[df_logs['Category'] == cat]
        dest = os.path.join(PROCESSED_DIR, cat)
        if not os.path.exists(dest): dest = os.path.join(PROCESSED_DIR, "unstructured_log")
        
        subset.to_csv(os.path.join(dest, f"hdbscan_{cat}.csv"), index=False)
        print(f"   📂 Saved {len(subset)} rows to {dest}")