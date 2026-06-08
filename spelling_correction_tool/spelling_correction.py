from pathlib import Path
import numpy as np
import collections
import time
import argparse
import Levenshtein

def read_function():
    unigram_freq = collections.Counter()

    script_dir = Path(__file__).resolve().parent
    absolute_file_path = script_dir / "data" / "unigram_freq.csv"

    with open(absolute_file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()
        for row in lines:
            word, cnt = row.split(",")
            unigram_freq[word] = cnt
    return unigram_freq


def spell_check(word, unigram_freq):

    if word in unigram_freq:
        # print ('this word is correctly spelled', str(word))
        return word
    
    alpha = 'abcdefghijklmnopqrstuvwxyz'
    
    # check elem deletion
    deleted_word = []
    for i in range(len(word)):
        new_word = word[:i] + word[i+1:]
        deleted_word.append(new_word)

    # check elem insertion
    inserted_word = []
    for i in range(len(word)):
        for j in alpha:
            new_word = word[:i] +str(j) + word[i:]
            inserted_word.append(new_word)

    # check elem transposition
    transposed_word = []
    for i in range(len(word)-1):
        ch1 = word[i]
        ch2 = word[i+1]
        new_word = word[:i] +str(ch2) + str(ch1) + word[i+2:]
        transposed_word.append(new_word)
    
    # check elem replacement
    replaced_word = []
    for i in range(len(word)):
        for j in alpha:
            new_word = word[:i] +str(j) + word[i+1:]
            replaced_word.append(new_word)
    
    final_word_lst = deleted_word + inserted_word + transposed_word + replaced_word
    final_dct = {}
    for elem in final_word_lst:
        if elem in unigram_freq:
            final_dct[elem] = unigram_freq[elem]

    # return [[key, int(val)] for key, val in sorted(final_dct.items(), key=lambda x: -1*int(x[1]))][:5]
    # check if there are any results to the 1 change lookup
    res = ''
    if len(final_dct) > 0:
        res = [key for key, val in sorted(final_dct.items(), key=lambda x: -1*int(x[1]))][:1][0]

    leven_dist_dct = collections.Counter()
    for key, val in unigram_freq.items():
        dist = Levenshtein.distance(key, word)
        if dist == 2:
            leven_dist_dct[key] = val

    res2 = [key for key, val in sorted(leven_dist_dct.items(), key=lambda x: -1*int(x[1]))][:1][0]
        
    return res if res != '' else res2

    
if __name__ == "__main__":

    # Initialize the parser
    parser = argparse.ArgumentParser(description="Process a list of words.")
    parser.add_argument("words", nargs="+", help="A list of words separated by spaces")

    args = parser.parse_args()

    # args.words is automatically a clean Python list
    print(f"Your words list: {args.words}")
    word_to_check = args.words
    
    # read the static lookup table for correct wordlist
    word_dct=read_function()
    word_pair = []

    # Start the timer
    start_time = time.perf_counter()
    for elem in word_to_check:
        corr_word = spell_check(elem, word_dct)
        word_pair.append((elem, corr_word))

    # End the timer
    end_time = time.perf_counter()
    execution_time = end_time - start_time

    print (word_pair)
    print ('Total execution time (ms):', round(execution_time*1000, 2))
    print ('avg per word execution time (ms):', round(execution_time*1000/len(word_to_check), 2))

    # OUTPUT
    # Your words list: ['speiling', 'misteke', 'executionw', 'mekanism', 'coding', 'chalenges']
    # [('speiling', 'spelling'), ('misteke', 'mistake'), ('executionw', 'execution'), ('mekanism', 'mechanism'), ('coding', 'coding'), ('chalenges', 'challenges')]
    # Total execution time (ms): 588.66
    # avg per word execution time (ms): 98.11