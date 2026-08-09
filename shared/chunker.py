import numpy as np
from .memory import embedder

def is_valid_chunk(chunk: str) -> bool:
    stripped = chunk.strip()
    if len(stripped) < 100:
        return False
    
    words = [w for w in stripped.split() if w.isalpha() and len(w) > 2]
    if len(words) < 10:
        return False
    
    digits = sum(c.isdigit() for c in stripped)
    if digits / len(stripped) > 0.3:
        return False
    return True


# ================================ Strategy 1 ================================
def chunk_fixed(text: str, size: int = 500, overlap: int = 100) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start += size - overlap  # overlap ensures no hard cuts
        
    return [c.strip() for c in chunks if c.strip()]


# ================================ Strategy 2 ================================
def chunk_recursive(text: str, size: int = 500, overlap: int = 50) -> list[str]:
    separators = ["\n\n", "\n", ". ", " "]
    
    def split(text: str, sep_idx: int = 0) -> list[str]:
        if len(text) <= size or sep_idx >= len(separators):
            return [text]
        sep = separators[sep_idx]
        parts = text.split(sep)
        chunks, current = [], ""
        for part in parts:
            if len(current) + len(part) + len(sep) <= size:
                current += part + sep
            else:
                if current.strip():
                    if len(current) > size:
                        chunks.extend(split(current, sep_idx + 1))
                    else:
                        chunks.append(current.strip())  # no added period
                current = part + sep
        if current.strip():
            chunks.append(current.strip())  # no added period
        return chunks
    
    return split(text)


# ================================ Strategy 3 ================================
def chunk_semantic(text: str, threshold: float = 0.3) -> list[str]:
    # Split into sentences first
    sentences = [s.strip() for s in text.replace("\n", " ").split(". ") if s.strip()]
    if len(sentences) <= 1:
        return sentences
    
    # Embed every sentence
    embeddings = embedder.encode(sentences)
    
    # Find breakpoints where adjacent sentences are dissimilar
    chunks, current_sentences = [], [sentences[0]]
    
    for i in range(1, len(sentences)):
        # Cosine similarity between adjacent sentences
        a, b = embeddings[i-1], embeddings[i]
        similarity = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
        
        if similarity < threshold:
            # Topic shift detected — start new chunk
            chunks.append(". ".join(current_sentences) + ".")
            current_sentences = [sentences[i]]
        else:
            current_sentences.append(sentences[i])
    
    if current_sentences:
        chunks.append(". ".join(current_sentences) + ".")
    
    return chunks
