# -*- coding: utf-8
import re
import os

SPECIAL_CHARS = ['.', ',', '!', '?', '\n', '+', '*', '-', '#', '@']

def hi(corpus, lower=3, upper=7):
    '''
    Finds the sentiment for each document from the corpus using wordscore.
    Wordscore is a simplistic approach to sentiment analysis, rating each
    word on a range from 1 to 9, 1 being very sad, 9 being very happy.

    Requires a 'words'folder to be placed in the same directory as this
    file. The words directory should contain a csv file for all words and
    another csv with all corresponding sentiment scores.

    These files are for english with this project. Files for other
    languages can be downloaded at
    http://www.uvm.edu/storylab/share/papers/dodds2014a/data.html. Be sure
    to change the LANG parameter (hardcoded for the sake of this project) if
    you choose to use a different language.

    This code is incorporate with license (see license_happy.txt) from
    https://github.com/luisgustavoneves/happy.

    corpus: List of documents (as strings).
    lower: Words having a score below this bound will be considered. This
    prevents words without strong sentiment from being included in the
    sentiment scores.
    upper: Words having a score above this bound will be considered.

    return: Average sentiment per document, one per document.
    '''

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

        # else no word found in wordlist, maybe lower/upper are too restrictive

    return sentiment
