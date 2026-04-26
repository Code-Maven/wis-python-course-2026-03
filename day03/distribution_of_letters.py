from collections import Counter
import string

def letter_distribution(text):
    # Normalize: lowercase and keep only letters
    filtered = [ch.lower() for ch in text if ch.isalpha()]

    total = len(filtered)
    counts = Counter(filtered)

    # Sort alphabetically
    distribution = dict(sorted(counts.items()))

    return distribution, total

def print_distribution(distribution, total):
    print(f"Total letters: {total}\n")
    print("Letter | Count | Frequency (%)")
    print("-" * 30)

    for letter, count in distribution.items():
        freq = (count / total) * 100
        print(f"{letter:>6} | {count:>5} | {freq:>10.2f}")
        #print(f"{letter} | {count} | {freq}")

if __name__ == "__main__":
    text = input("Enter text: ")

    distribution, total = letter_distribution(text)
    print_distribution(distribution, total)
#else:
#    print("I am loaded as a module")
