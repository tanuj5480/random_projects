from pathlib import Path
import numpy as np
import collections
import heapq
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
    word_set = set()

    # check elem deletion
    for i in range(len(word)):
        new_word = word[:i] + word[i+1:]
        word_set.add(new_word)

    # check elem insertion
    for i in range(len(word)):
        for j in alpha:
            new_word = word[:i] +str(j) + word[i:]
            word_set.add(new_word)

    # check elem transposition
    for i in range(len(word)-1):
        ch1 = word[i]
        ch2 = word[i+1]
        new_word = word[:i] +str(ch2) + str(ch1) + word[i+2:]
        word_set.add(new_word)
    
    # check elem replacement
    for i in range(len(word)):
        for j in alpha:
            new_word = word[:i] +str(j) + word[i+1:]
            word_set.add(new_word)
    
    final_dct = {}
    for elem in word_set:
        if elem in unigram_freq:
            final_dct[elem] = int(unigram_freq[elem])

    # return [[key, int(val)] for key, val in sorted(final_dct.items(), key=lambda x: -1*int(x[1]))][:5]
    # check if there are any results to the 1 change lookup
    # maintain a heap, so we do not incur the sorting cost incase there are a lot of candidates
    res = []
    k=1
    if len(final_dct) > 0:
        for key, val in final_dct.items():
            if k > 0:
                heapq.heappush(res, (-1*val, key))
                k-=1
            else:
                if val > -1*res[0][0]:
                    heapq.heappop(res)
                    heapq.heappush(res, (-val, key))


    leven_dist_dct = collections.Counter()
    for key, val in unigram_freq.items():
        dist = Levenshtein.distance(key, word)
        if dist == 2:
            leven_dist_dct[key] = int(val)

    # print (leven_dist_dct)
    res2=[]
    k2=1
    for key, val in leven_dist_dct.items():
        if k2 > 0:
            heapq.heappush(res2, (-1*val, key))
            k2-=1
        else:
            if val > -1*res2[0][0]:
                heapq.heappop(res2)
                heapq.heappush(res2, (-val, key))


    return res[0][1] if res else res2[0][1]

    
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

    avg_word_time_ms = round(execution_time*1000/len(word_to_check), 2)
    words_per_sec = 1000.0/avg_word_time_ms
    print (word_pair)
    print ('Total execution time (ms):', round(execution_time*1000, 2))
    print ('avg per word execution time (ms):', avg_word_time_ms)
    print ('words per sec:', words_per_sec)

    # OUTPUT
    # Your words list: ['speiling', 'misteke', 'executionw', 'mekanism', 'coding', 'chalenges']
    # [('speiling', 'spelling'), ('misteke', 'mistake'), ('executionw', 'execution'), ('mekanism', 'mechanism'), ('coding', 'coding'), ('chalenges', 'challenges')]
    # Total execution time (ms): 588.66
    # avg per word execution time (ms): 98.11