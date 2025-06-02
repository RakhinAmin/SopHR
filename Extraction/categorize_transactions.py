import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Load Excel
xls = pd.ExcelFile('bank_statement.xlsx')
df = xls.parse('Sheet1')  # Rename if needed
categories_df = xls.parse('Categories')  # Single column: 'Category'

# Extract and clean descriptions
descriptions = df['Description'].astype(str).str.strip().tolist()

# Step 1: Generate semantic embeddings (meaning vectors)
model = SentenceTransformer('all-MiniLM-L6-v2')
embeddings = model.encode(descriptions)

# Step 2: Smart k selection
max_k = min(len(df), len(categories_df))
if max_k < 2:
    raise ValueError("Too few transactions or categories.")
k = max_k

# Step 3: Cluster based on meaning
kmeans = KMeans(n_clusters=k, random_state=42)
df['Cluster'] = kmeans.fit_predict(embeddings)

# Step 4: Get cluster centers
cluster_centroids = kmeans.cluster_centers_

# Step 5: Encode category labels to vectors
category_labels = categories_df['Category'].astype(str).str.strip().tolist()
category_vectors = model.encode(category_labels)

# Step 6: Match each cluster centroid to closest category
similarity = cosine_similarity(cluster_centroids, category_vectors)
cluster_to_category = {
    i: category_labels[np.argmax(similarity[i])]
    for i in range(k)
}

# Step 7: Assign to each transaction
df['Category'] = df['Cluster'].map(cluster_to_category)

# Save output
df.to_excel('auto_categorized_semantic.xlsx', index=False)
print("✅ Smart categorization done using semantic similarity.")
