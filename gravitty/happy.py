# -*- coding: utf-8
import re
import os

SPECIAL_CHARS = ['.', ',', '!', '?', '\n', '+', '*', '-', '#', '@']

def hi(corpus, lower=3, upper=7):

    LANG = 'english'

    file_path = os.path.dirname(__file__)
    word_file = os.path.join(file_path, 'words/labMTwords-%s.csv'%LANG)
    scores_file = os.path.join(file_path, 'words/labMTscores-%s.csv'%LANG)

    word_list = open(word_file,'r').read().split('\n')
    scores  = open(scores_file,'r').read().split('\n')

    word_scores = {w: float(s.strip()) for w,s in zip(word_list, scores)
                   if s <= lower or s >= upper}

    pattern = '[' + '\\'.join(SPECIAL_CHARS) + ']'

    sentiment = []

    for text in corpus:

        text = re.sub(pattern, ' ', text.lower())

        words = [word for word in text.split(' ') if word]

        h = 0.  # sum of happiness scores

        f = 0   # sum of word freq.

        word_frequency = {} # dict with word frequency in text
        for word in words:
            if word in word_scores:
                word_frequency[word] = word_frequency.get(word, 0) + 1
                h += word_scores[word]
                f += 1

        if f > 0:
            sentiment.append(h/f)

        # else no word found in wordlist, maybe l and u too restrictive

    return sentiment
