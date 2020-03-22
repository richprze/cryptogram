import csv
import re
import time

logging = {'while_node': [], 'while_word': [], 'replace': [], 'update': [], 'match': []}

def main():
    # phrase = Phrase("b am tmy ype ym avtlg jgyygp ykvt vtemtg ghug b mthe ype ym avtlg jgyygp ykvt deughc")
    phrase_input = input("Enter encrypted phrase: ")
    num_words = int(input("Max number words in dict: "))
    start = time.time()
    print(phrase_input)
    phrase = Phrase(phrase_input, num_words)
    solving = True
    next_guess = 'node'
    phrase.get_latest_counts()
    num_guesses = {'node': 0, 'word': 0, 'total': 0}
    while solving:
        if next_guess == 'node':
            t1 = time.time()
            phrase.make_next_node_guess()
            num_guesses['node'] += 1
            num_guesses['total'] += 1
        else:
            t1 = time.time()
            res = phrase.make_next_word_guess()
            num_guesses['word'] += 1
            num_guesses['total'] += 1
            if not res:
                phrase.i -= 1
                # TODO: QUESTION: remove incremental guesses?
                if phrase.i < 0:
                    print("FAILED. Ran out of word options")
                    # TODO Try one_two_fallback. Or another dictionary.
                    solving = False
                    continue

                phrase.latest_phrase = phrase.replace_with_guess_and_exclude()
                # run update with all options
                phrase.update_word_list_opts()
                # updated locked options
                phrase.set_locked_options("all")

                print("went back to previous node. now at {}".format(phrase.word_list[phrase.i].word))
                print("curr guess: {}; len(latest_options): {}".format(phrase.word_list[phrase.i].curr_guess + 1, len(phrase.word_list[phrase.i].latest_options)))
                next_guess = 'word'
                continue

        phrase.latest_phrase = phrase.replace_with_guess_and_exclude()
        phrase.update_word_list_opts(opt_type="locked")
        result = phrase.status()
        # log while loop time
        if next_guess == 'node':
            logging['while_node'].append(time.time() - t1)
        else:
            logging['while_word'].append(time.time() - t1)

        if result == "continue":
            next_guess = 'node'
        elif result == "failed":
            next_guess = 'word'
        else:
            solving = False
            answer = phrase.get_solution()

    print("Took {} guesses - {} node guesses, {} word guesses".format(num_guesses['total'], num_guesses['node'], num_guesses['word']))
    print("Took {} seconds".format(time.time()-start))
    print("initial counts:")
    print("TODO...")

    return logging

class Node:
    def __init__(self, word, options):
        self.word = word
        self.options = options
        self.locked_options = self.options
        self.latest_options = self.options
        self.latest_word = "".join(["'" if x == "'" else "." for x in word])
        self.curr_guess = None
        self.incremental_guesses = []

    def num_options(self):
        return len(self.options)

    def num_locked_options(self):
        return len(self.locked_options)

    def num_latest_options(self):
        return len(self.latest_options)

class Phrase:
    def __init__(self, phrase, num_words=5000):
        # initial setup
        self.phrase = phrase
        # self.words = top_5K_words_rank_dict()
        self.words, self.one_two_fallback = merged_word_dict(num_words=num_words)
        print("{} words in dict.".format(len(self.words)))
        self.numbers = list_to_numbers(self.words)
        self.phrase_list = self.phrase.split(" ")
        self.word_list = []
        self.setup_phrase_word_list()
        self.i = -1
        # keep order up to curr_i, sort rest
        self.sort_word_list()
        # self.word_list = sorted(self.word_list, key=lambda word: word.num_options())

        # For guessing
        self.guesses = {}
        self.latest_phrase = None

    # Functions for initial setup
    def setup_phrase_word_list(self):
        for word in set(self.phrase_list):
            number = word_to_number(word)
            opts = self.get_phrase_word_opts(number)
            self.word_list.append(Node(word, opts))
            # self.word_list.append({'word': word, 'options': opts, 'num_options': len(opts)})

    def get_phrase_word_opts(self, struct):
        opts = {}
        for w, n in self.numbers.items():
            if n == struct:
                # add potential word + rank
                opts[w] = self.words[w]
        opts_ordered = sorted(opts, key=opts.get)
        return opts_ordered

    def sort_word_list(self):
        new_order = self.word_list[:self.i+1]
        new_order.extend(sorted(self.word_list[self.i+1:], key=lambda word: word.num_options()))
        self.word_list = new_order

    # Adds guessed letters to the guesses dict
    def word_to_guesses(self, node):
        phrase_word = node.word
        guess_word = node.latest_options[node.curr_guess]
        for i in range(0, len(phrase_word)):
            if not self.guesses.get(phrase_word[i]):
                self.guesses[phrase_word[i]] = guess_word[i]
                # need to know which letter guesses we're net new, so they can be removed if wrong
                node.incremental_guesses.append(phrase_word[i])

    def remove_word_to_guesses(self, node):
        for r in node.incremental_guesses:
            if self.guesses.get(r):
                del(self.guesses[r])
                print("{} removed from guesses".format(r))
            else:
                print("{} already removed from guesses".format(r))

    def replace_with_guess_and_exclude(self):
        t2 = time.time()
        exclude = "".join([v for k, v in self.guesses.items()])
        new_phrase = []
        for node in self.word_list:
            new_word = []
            for l in node.word:
                if self.guesses.get(l):
                    new_word.append(self.guesses[l])
                elif l == "'":
                    new_word.append(l)
                else:
                    new_word.append("[^{}]".format(exclude))
            new_phrase.append("".join(new_word))
            node.latest_word = "".join(new_word)
        logging['replace'].append(time.time()-t2)

        return new_phrase


    def update_word_list_opts(self, opt_type="all"):
        print("updating word list opts")
        t3 = time.time()
        i = self.i + 1
        print("i: ", i)
        for node in self.word_list[i:]:
            print("updating {} node".format(node.word))
            options = node.options if opt_type == "all" else node.locked_options
            new_opts = return_match_list(options, node.latest_word)
            node.latest_options = new_opts
        logging['update'].append(time.time() - t3)

    def set_locked_options(self, opt_type):
        i = self.i + 1
        for node in self.word_list[i:]:
            node.locked_options = node.latest_options if opt_type == 'latest' else node.options


    def make_next_node_guess(self):
        self.i += 1
        if self.i == len(self.word_list):
            print("No more nodes to guess")
            return False
        self.word_list[self.i].curr_guess = 0
        self.word_to_guesses(self.word_list[self.i])
        self.set_locked_options("latest")

    def make_next_word_guess(self):
        self.word_list[self.i].curr_guess += 1
        if self.word_list[self.i].curr_guess < self.word_list[self.i].num_latest_options():
            print("making next word guess")
            # remove last guesses within node
            self.remove_word_to_guesses(self.word_list[self.i])

            # go to next guess
            self.word_list[self.i].incremental_guesses = []
            self.word_to_guesses(self.word_list[self.i])
            return True
        else:
            print("no more word guesses. removing guesses within node.")
            print("You must go back to the previous node and go to the next word guess there")
            self.remove_word_to_guesses(self.word_list[self.i])
            self.word_list[self.i].curr_guess = None
            self.word_list[self.i].incremental_guesses = []
            # TODO: do I need to reset latest_word? Or will that be handled?
            # SHOULD get updated with next replace_and_remnove
            return False

    # functions to check results
    def get_latest_counts(self):
        num_zeroes = 0
        num_ones = 0
        zero_phrase_words = []
        one_phrase_words = []
        one_answers = []
        print("phrase word | num options | num latest options | num locked options")
        for node in self.word_list:
            counts = "{} | {} | ".format(node.word, node.num_options())
            if node.curr_guess is not None:
                num_ones += 1
                one_phrase_words.append(node.word)
                one_answers.append(node.latest_options[node.curr_guess])
                counts += "1 | {} | {}".format(node.latest_options[node.curr_guess], node.num_locked_options())
            elif node.num_latest_options() == 0:
                num_zeroes += 1
                zero_phrase_words.append(node.word)
                counts += "0"
            elif node.num_latest_options() == 1:
                num_ones += 1
                one_phrase_words.append(node.word)
                one_answers.extend(node.latest_options)
                counts += "1 | {} | {}".format(node.latest_options[0], node.num_locked_options())
            else:
                counts += "{} | {}".format(node.num_latest_options(), node.num_locked_options())
            print(counts)
        return num_zeroes, zero_phrase_words, num_ones, one_phrase_words, one_answers

    def status(self):
        num_zeroes, zeroes, num_ones, ones, one_answers = self.get_latest_counts()
        if num_zeroes > 0:
            print("Failed. [{}] words had no match".format(" ".join(zeroes)))
            return "failed"
        elif num_ones == len(self.word_list):
            print("Success! All words solved! The answer is:")
            return "solved"
        else:
            print("Keep going.")
            return "continue"

    def get_solution(self):
        solution = {}
        for node in self.word_list:
            if node.curr_guess is None:
                node.latest_word = node.latest_options[0]
            solution[node.word] = node.latest_word
        solved_phrase = []
        for word in self.phrase_list:
            solved_phrase.append(solution[word])
        print(" ".join(solved_phrase))
        return solved_phrase


def return_match_list(options, match_phrase):
    t4 = time.time()
    new_opts = []
    for opt in options:
        if re.match("".join(match_phrase), opt):
            new_opts.append(opt)
    logging['match'].append(time.time()-t4)
    return new_opts

def words_freq_dict(fn='words1.txt'):
    with open(fn) as f:
        words = dict(x.split() for x in f.readlines())
        return words

def words_rank_dict(fn='words1.txt'):
    with open(fn) as f:
        cnt = 1
        words = {}
        for line in f.readlines():
            words[line.split()[0]] = cnt
            cnt += 1
        return words

def words_list(fn='words1.txt'):
    with open(fn) as f:
        words = list(x.split()[0] for x in f.readlines())
        return words

def contractions_list(fn='contractions.txt'):
    with open(fn) as f:
         words = list(x.rstrip() for x in f.readlines())
         return words

def cont_rank_dict(conts, words):
    cont_dict = {}
    for cont in conts:
        if words.get(cont.replace("'", '')):
            cont_dict[cont] = words[cont.replace("'", '')]
        else:
            cont_dict[cont] = 0
    return cont_dict

def top_5K_words_rank_dict(fn='top5K.csv'):
    with open(fn) as f:
        print(__name__)
        reader = csv.reader(f)
        words = {}
        cnt = 0
        for row in reader:
            if cnt == 0:
                row[0] = row[0].strip('\ufeff')
            # keep highest rank
            if not words.get(row[0].lower()):
                words[row[0].lower()] = int(row[1])
            cnt += 1
        return words

def merged_word_dict(fn1='top5K.csv', fn2='words1.txt', num_words=50000):
    # get first list
    num_words = max(5000, num_words)
    num = 0
    one_two_fallback = {}
    with open(fn1) as f:
        reader = csv.reader(f)
        words = {}
        cnt = 0
        max_rank = 0
        for row in reader:
            if cnt == 0:
                row[0] = row[0].strip('\ufeff')
            # keep highest rank
            if not words.get(row[0].lower()):
                words[row[0].lower()] = int(row[1])
                max_rank = max(max_rank, int(row[1]))
                num += 1
            cnt += 1

    with open(fn2) as f:
        cnt = max_rank + 1
        for line in f.readlines():
            # keep highest rank
            if not words.get(line.split()[0].lower()):
                # Only use one and two letter words from 5K list
                if len(line.split()[0]) > 2:
                    words[line.split()[0].lower()] = cnt
                    num += 1
                else:
                    one_two_fallback[line.split()[0].lower()] = cnt
            cnt += 1
            if num >= num_words:
                break

    return words, one_two_fallback


def top_5K_words_full_dict(fn='top5K.csv'):
    with open(fn) as f:
        reader = csv.reader(f)
        words = {}
        for row in reader:
            if words.get(row[0].lower()):
                words[row[0].lower()]['multi'] = True
                words[row[0].lower()]['others'].append({
                    'rank': row[1],
                    'frequency': row[2],
                    'dispersion': row[3],
                    'length': row[4],
                    'part': row[5]
                    })
            else:
                words[row[0].lower()] = {
                    'rank': row[1],
                    'frequency': row[2],
                    'dispersion': row[3],
                    'length': row[4],
                    'part': row[5],
                    'multi': False,
                    'others': []
                    }
        return words

def word_to_number(word):
    cnt = 1
    used = {}
    struct = []
    for l in word.lower():
        if not used.get(l):
            used[l] = cnt
            struct.append(cnt)
            cnt += 1
        else:
            struct.append(used[l])
    return int(''.join(map(str, struct)))

def list_to_numbers(words):
    numbers = {}
    for word in words:
        numbers[word] = word_to_number(word)
    return numbers

def print_logs(logs):
    for log, vals in logs.items():
        print("{} - min: {} | max: {} | avg: {}".format(log, min(vals), max(vals), sum(vals)/len(vals)))

if __name__ == "__main__":
    main()
