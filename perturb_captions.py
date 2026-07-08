import re, random, os

random.seed(42)

d = os.path.join(os.path.dirname(__file__), "corrected_dataset_extract")
captions = []
for f in sorted(os.listdir(d)):
    if f.endswith(".txt"):
        captions.append(open(os.path.join(d, f)).read().strip())

assert len(captions) == 31

COLORS = ["red", "blue", "black", "white", "gray", "crimson", "maroon", "acid-yellow",
          "hot-pink", "pink", "orange", "teal", "purple", "green", "yellow-green",
          "ultramarine-blue", "pale-yellow", "dark-blue", "olive", "violet", "magenta",
          "cobalt-blue", "burnt-orange", "rust-red"]

MEDIA = ["marker", "colored pencil", "watercolor-pencil", "ink", "acrylic", "graphite",
         "ballpoint pen", "oil-pastel", "poster-color", "charcoal", "crayon", "gouache",
         "wax-crayon", "dry-pastel", "felt-tip pen"]

GROUNDS = ["kraft cardboard", "notebook paper", "newsprint", "cream paper", "white background",
           "torn paper", "lined paper", "sketchbook page", "brown paper bag", "graph paper"]

def swap_one(text, vocab):
    for w in sorted(vocab, key=len, reverse=True):
        if re.search(r'\b' + re.escape(w) + r'\b', text):
            choices = [c for c in vocab if c != w]
            new = random.choice(choices)
            return re.sub(r'\b' + re.escape(w) + r'\b', new, text, count=1), True
    return text, False

def perturb(caption, n_swaps):
    text = caption
    for _ in range(n_swaps):
        vocab = random.choice([COLORS, MEDIA, GROUNDS])
        text, _ = swap_one(text, vocab)
    return text

TARGET = 200
per_base = TARGET // len(captions)
remainder = TARGET - per_base * len(captions)

results = []
for i, cap in enumerate(captions):
    count = per_base + (1 if i < remainder else 0)
    seen = set()
    tries = 0
    while len(seen) < count and tries < count * 20:
        tries += 1
        n_swaps = random.choice([1, 1, 2, 2, 3])
        variant = perturb(cap, n_swaps)
        if variant not in seen and variant != cap:
            seen.add(variant)
    results.extend(sorted(seen))

results = results[:TARGET]
while len(results) < TARGET:
    cap = random.choice(captions)
    variant = perturb(cap, random.choice([1,2,3]))
    if variant not in results:
        results.append(variant)

with open(os.path.join(os.path.dirname(__file__), "perturbed_prompts_200.txt"), "w") as f:
    for r in results:
        f.write(r + "\n")

print(f"wrote {len(results)} prompts")
