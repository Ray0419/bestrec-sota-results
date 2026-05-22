"""Preprocess Amazon Reviews 2023 with proper deduplication.

CRITICAL FIX: Deduplicate (user_id, item_id) pairs BEFORE k-core filtering.
The original preprocessing kept multiple reviews of the same item by the same
user as separate interactions, which makes the k-core filter "pass" users
who only ever interacted with 1 unique item (just rated it 5 times). EASE
and other CF methods require unique user-item pairs.

Strategy: keep the LATEST rating per (user, item) pair.
"""
import os, sys, json, pickle, time
from collections import defaultdict
import numpy as np
import torch
from tqdm import tqdm

ROOT = "C:/Users/rayxc/Documents/R"
DATASET_FILES = {
    'beauty': ('All_Beauty.jsonl', 'meta_All_Beauty.jsonl'),
    'books': ('Books.jsonl', 'meta_Books.jsonl'),
    'fashion': ('Amazon_Fashion.jsonl', 'meta_Amazon_Fashion.jsonl'),
    'instruments': ('Musical_Instruments.jsonl', 'meta_Musical_Instruments.jsonl'),
}
K_CORE = 5


def load_raw_dedup(dataset):
    """Load + deduplicate (user, item) pairs by keeping last occurrence."""
    inter_file, meta_file = DATASET_FILES[dataset]
    inter_path = os.path.join(ROOT, "data", dataset, inter_file)
    meta_path = os.path.join(ROOT, "data", dataset, meta_file)

    user2id, item2id = {}, {}
    # Use dict keyed by (user, item) for dedup
    inter_map = {}  # (uid, iid) -> {rating, review, timestamp}

    print(f'  Reading interactions: {inter_path}')
    n_lines = 0
    with open(inter_path, 'r', encoding='utf-8') as f:
        for line in tqdm(f, desc='inter', unit='line'):
            n_lines += 1
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            uid_raw = rec.get('user_id')
            iid_raw = rec.get('parent_asin')
            rating = rec.get('rating')
            if uid_raw is None or iid_raw is None or rating is None:
                continue
            review_text = rec.get('text', '') or ''
            review_title = rec.get('title', '') or ''
            full_review = (review_title + ' ' + review_text).strip()
            ts = rec.get('timestamp', 0) or 0
            if uid_raw not in user2id:
                user2id[uid_raw] = len(user2id)
            if iid_raw not in item2id:
                item2id[iid_raw] = len(item2id)
            uid = user2id[uid_raw]; iid = item2id[iid_raw]
            key = (uid, iid)
            existing = inter_map.get(key)
            if existing is None or ts >= existing['ts']:
                inter_map[key] = {'rating': float(rating), 'review': full_review, 'ts': ts}

    print(f'  {n_lines:,} raw lines -> {len(inter_map):,} unique (user, item) pairs')

    interactions = []
    for (uid, iid), v in inter_map.items():
        interactions.append({
            'user_id': uid, 'item_id': iid,
            'rating': v['rating'], 'review': v['review'],
        })

    print(f'  Reading metadata: {meta_path}')
    item_metadata = {}
    with open(meta_path, 'r', encoding='utf-8') as f:
        for line in tqdm(f, desc='meta', unit='line'):
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            pasin = rec.get('parent_asin')
            if pasin not in item2id:
                continue
            idx = item2id[pasin]
            price = rec.get('price', 0.0)
            try: price_f = float(price) if price else 0.0
            except (ValueError, TypeError): price_f = 0.0
            try: avg_r = float(rec.get('average_rating', 0.0) or 0.0)
            except (ValueError, TypeError): avg_r = 0.0
            try: rat_n = float(rec.get('rating_number', 0.0) or 0.0)
            except (ValueError, TypeError): rat_n = 0.0
            item_metadata[idx] = {
                'title': rec.get('title', '') or '',
                'avg_rating': avg_r, 'rating_num': rat_n, 'price': price_f,
            }
    for i in range(len(item2id)):
        if i not in item_metadata:
            item_metadata[i] = {'title': '', 'avg_rating': 0.0,
                                'rating_num': 0.0, 'price': 0.0}

    return {
        'interactions': interactions,
        'user2id': user2id, 'item2id': item2id,
        'item_metadata': item_metadata,
        'num_users': len(user2id), 'num_items': len(item2id),
    }


def kcore_filter(interactions, k):
    inters = list(interactions)
    prev = -1
    while len(inters) != prev:
        prev = len(inters)
        uc, ic = defaultdict(int), defaultdict(int)
        for i in inters:
            uc[i['user_id']] += 1; ic[i['item_id']] += 1
        inters = [i for i in inters if uc[i['user_id']] >= k and ic[i['item_id']] >= k]
    return inters


def reindex(interactions, item_meta_orig):
    users = sorted(set(i['user_id'] for i in interactions))
    items = sorted(set(i['item_id'] for i in interactions))
    u2n = {o: n for n, o in enumerate(users)}
    i2n = {o: n for n, o in enumerate(items)}
    new_inters = [{'user_id': u2n[i['user_id']], 'item_id': i2n[i['item_id']],
                   'rating': i['rating'], 'review': i['review']} for i in interactions]
    new_meta = {n: item_meta_orig.get(o, {'title':'unknown','price':0.0,
                                          'avg_rating':0.0,'rating_num':0})
                for n, o in enumerate(items)}
    return new_inters, new_meta, len(users), len(items)


def encode_titles(item_meta, n_items, save_path):
    from sentence_transformers import SentenceTransformer
    sbert = SentenceTransformer('all-MiniLM-L6-v2',
                                 device='cuda' if torch.cuda.is_available() else 'cpu')
    titles = [item_meta[i]['title'] for i in range(n_items)]
    emb = sbert.encode(titles, batch_size=512, show_progress_bar=True, convert_to_numpy=True)
    item_title_emb = torch.tensor(emb, dtype=torch.float32)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    torch.save(item_title_emb, save_path)
    return item_title_emb


def main():
    if len(sys.argv) < 2:
        print("Usage: preprocess_v2.py <dataset>")
        sys.exit(1)
    dataset = sys.argv[1]

    # NEW v5 cache to keep separate from old (potentially-leaked) v4 cache
    cache_dir = os.path.join(ROOT, "cache", dataset)
    raw_path = os.path.join(cache_dir, "raw_data_dedup.pkl")
    if os.path.exists(raw_path):
        print(f"Cached: {raw_path}")
        data = pickle.load(open(raw_path, "rb"))
    else:
        os.makedirs(cache_dir, exist_ok=True)
        t0 = time.time()
        data = load_raw_dedup(dataset)
        print(f"  Raw loaded: {data['num_users']:,} users / {data['num_items']:,} items / "
              f"{len(data['interactions']):,} unique pairs | {time.time()-t0:.1f}s")
        pickle.dump(data, open(raw_path, "wb"))

    print(f"\nApplying {K_CORE}-core filter...")
    filtered = kcore_filter(data['interactions'], K_CORE)
    interactions, item_meta, n_users, n_items = reindex(filtered, data['item_metadata'])
    print(f"After {K_CORE}-core: {n_users:,} users / {n_items:,} items / {len(interactions):,} inters")
    if n_users:
        print(f"Density: {len(interactions)/n_users:.2f} inters/user")

    title_path = os.path.join(cache_dir, "v5", f"item_title_{K_CORE}core_dedup.pt")
    if not os.path.exists(title_path):
        encode_titles(item_meta, n_items, title_path)
    else:
        print(f"  Cached titles: {title_path}")

    print(f"\n=== {dataset.upper()} (DEDUP) SUMMARY ===")
    print(f"  raw users:           {data['num_users']:,}")
    print(f"  raw items:           {data['num_items']:,}")
    print(f"  unique (u,i) pairs:  {len(data['interactions']):,}")
    print(f"  k-{K_CORE} users:           {n_users:,}")
    print(f"  k-{K_CORE} items:           {n_items:,}")
    print(f"  k-{K_CORE} inters:          {len(interactions):,}")


if __name__ == "__main__":
    main()
