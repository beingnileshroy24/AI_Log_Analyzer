import pandas as pd
import os
import re
import numpy as np
import hdbscan
import shutil
import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from config import PROCESSED_DIR, DOMAIN_KEYWORDS
from ingestor import UniversalIngestor

def clean_text(text):
    text = re.sub(r'\d+', '', text)
    text = re.sub(r'[^\w\s]', ' ', text)
    return str(text).lower().strip()

def run_clustering(staging_dir):
    print("\n🚀 STARTING AI CLUSTERING (HDBSCAN)...")
    
    all_log_data = []
    if not os.path.exists(staging_dir): return []

    ingestor = UniversalIngestor(staging_dir)

    # 1. Load Data
    for filename in os.listdir(staging_dir):
        filepath = os.path.join(staging_dir, filename)
        if os.path.isdir(filepath): continue
        
        try:
            content = ingestor.process_file(filepath)
            if content is None: continue

            if isinstance(content, pd.DataFrame):
                # Convert rows to string representation for clustering
                for _, row in content.head(1000).iterrows():
                    all_log_data.append({
                        'Original_Log': " | ".join(map(str, row.values)),
                        'Source_File': filename
                    })
            else:
                lines = content.splitlines()
                for line in lines:
                    if line.strip():
                        all_log_data.append({
                            'Original_Log': line.strip(),
                            'Source_File': filename
                        })
        except Exception as e:
            print(f"⚠️ Error processing {filename}: {e}")

    df_logs = pd.DataFrame(all_log_data)
    print(f"✅ Loaded {len(df_logs)} log lines.")

    if df_logs.empty: return []

    # 2. Vectorize
    df_logs['Cleaned_Log'] = df_logs['Original_Log'].apply(clean_text)
    
    my_stop_words = list(TfidfVectorizer(stop_words='english').get_stop_words())
    my_stop_words.extend(["info", "error", "warn", "timestamp", "at", "failed"])

    vectorizer = TfidfVectorizer(max_features=500, stop_words=my_stop_words)
    X = vectorizer.fit_transform(df_logs['Cleaned_Log'])
    X_dense = X.toarray()

    # 3. Clustering
    if len(df_logs) < 5:
        df_logs['Cluster_ID'] = -1
    else:
        clusterer = hdbscan.HDBSCAN(min_cluster_size=5, min_samples=2)
        df_logs['Cluster_ID'] = clusterer.fit_predict(X_dense)
    
    unique_clusters = sorted(df_logs['Cluster_ID'].unique())
    print(f"✅ Clusters Found: {unique_clusters}")

    # 4. Labeling
    cluster_map = {}
    for cid in unique_clusters:
        if cid == -1:
            cluster_map[cid] = "unstructured_log"
            continue
            
        indices = df_logs.index[df_logs['Cluster_ID'] == cid].tolist()
        centroid = np.mean(X_dense[indices], axis=0)
        top_indices = centroid.argsort()[-10:][::-1]
        top_terms = vectorizer.get_feature_names_out()[top_indices]

        best_match = "app_log"
        highest_score = 0
        for cat, keys in DOMAIN_KEYWORDS.items():
            score = sum(1 for term in top_terms if term in keys)
            if score > highest_score:
                highest_score = score
                best_match = cat
        
        cluster_map[cid] = best_match
        print(f"   👉 Cluster {cid} -> {best_match.upper()} (Terms: {list(top_terms)})")

    df_logs['Category'] = df_logs['Cluster_ID'].map(cluster_map)

    # 5. Distribute Result Data
    for cat in df_logs['Category'].unique():
        subset = df_logs[df_logs['Category'] == cat]
        dest = os.path.join(PROCESSED_DIR, cat)
        os.makedirs(dest, exist_ok=True)
        
        subset.to_csv(os.path.join(dest, f"hdbscan_{cat}.csv"), index=False)
        print(f"   📂 Saved Cluster Summary to {dest}")

    # 6. Move Source Files
    updates = []
    # Determine majority category for each source file
    for filename in df_logs['Source_File'].unique():
        file_subset = df_logs[df_logs['Source_File'] == filename]
        # Most frequent category
        winning_cat = file_subset['Category'].mode()[0]
        
        source_path = os.path.join(staging_dir, filename)
        dest_folder = os.path.join(PROCESSED_DIR, winning_cat)
        dest_path = os.path.join(dest_folder, filename)
        
        os.makedirs(dest_folder, exist_ok=True)
        
        try:
            if os.path.exists(source_path):
                shutil.move(source_path, dest_path)
                print(f"   🚚 Moved {filename} -> {winning_cat}/")
                
                # Metadata updates
                updates.append({
                    "Stored_Filename": filename,
                    "Category": winning_cat,
                    "Final_Path": dest_path,
                    "Cluster_ID": "Line-Level",
                    "Summary": f"Processed via HDBSCAN clustering. Majority category: {winning_cat}"
                })
        except Exception as e:
            print(f"   ❌ Error moving {filename}: {e}")

    return updates