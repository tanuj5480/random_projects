import numpy as np
import collections


def read_function():
    unigram_freq = collections.Counter()
    with open("data/unigram_freq.csv", "r", encoding="utf-8") as file:
        lines = file.readlines()
        for row in lines:
            word, cnt = row.split(",")
            unigram_freq[word] = cnt
    return unigram_freq


def spell_check(word, unigram_freq):

    if word in unigram_freq:
        print ('this word is correctly spelled', str(word))
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
    return [key for key, val in sorted(final_dct.items(), key=lambda x: -1*int(x[1]))][:1][0]

    
if __name__ == "__main__":

    word_dct=read_function()
    word_to_check = ['speiling', 'misteke', 'executionw', 'coding', 'chalenges']
    word_pair = []
    for elem in word_to_check:
        corr_word = spell_check(elem, word_dct)
        word_pair.append((elem, corr_word))

    print (word_pair)