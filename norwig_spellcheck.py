import json
import os
from collections import Counter
from gdriveloader import preprocess


class NorwigSpellcheck:
    def __init__(self, client_id):
        self.index_path = os.path.join("drive_files", client_id, "index.json")
        self.vocabulary = Counter()
        index = json.load(open(self.index_path))
        for token in index:
            self.vocabulary[token] = sum(index[token].values())

    def P(self, word):
        "Probability of `word`."
        N = sum(self.vocabulary.values())
        return self.vocabulary[word] / N

    def correction(self, query):
        query_prep = preprocess(query)
        "Most probable spelling correction for word."
        query_res = " ".join([max(self.candidates(word), key=self.P) for word in query_prep])
        return query_res

    def candidates(self, word):
        "Generate possible spelling corrections for word."
        return self.known([word]) or self.known(self.edits1(word)) or self.known(self.edits2(word)) or [word]

    def known(self, words):
        "The subset of `words` that appear in the dictionary of WORDS."
        return set(w for w in words if w in self.vocabulary)

    def edits1(self, word):
        "All edits that are one edit away from `word`."
        letters = 'abcdefghijklmnopqrstuvwxyz' + ''.join([chr(i) for i in range(ord('а'), ord('я') + 1)])
        splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
        deletes = [L + R[1:] for L, R in splits if R]
        transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R) > 1]
        replaces = [L + c + R[1:] for L, R in splits if R for c in letters]
        inserts = [L + c + R for L, R in splits for c in letters]
        return set(deletes + transposes + replaces + inserts)

    def edits2(self, word):
        "All edits that are two edits away from `word`."
        return (e2 for e1 in self.edits1(word) for e2 in self.edits1(e1))
