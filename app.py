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
                phrase.guess_node = phrase.guess_node.prev()
                # TODO: QUESTION: remove incremental guesses?
                if not phrase.guess_node:
                    print("FAILED. Ran out of word options")
                    # TODO Try one_two_fallback. Or another dictionary.
                    solving = False
                    continue
                
                print("went back to previous node. now at {}".format(phrase.guess_node.word))
                print("curr guess: {}; len(latest_options): {}".format(phrase.guess_node.curr_guess + 1, len(phrase.guess_node.latest_options)))
                next_guess = 'word'
                continue

        phrase.latest_phrase = phrase.replace_with_guess_and_exclude()
        phrase.update_guess_tree_opts()
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
    for k, v in phrase.init_phrase_opts.items():
        print("{} | {}".format(k, len(v)))

    return logging

class Node:
    def __init__(self, word, options):
        self.word = word
        self.options = options
        self.latest_options = self.options
        self.latest_word = "".join(["'" if x == "'" else "." for x in word])
        self.curr_guess = None
        self.incremental_guesses = []
        self.__prev = None
        self.__next = None

    def set_next(self, node):
        self.__next = node
        node.set_prev(self)

    def next(self):
        return self.__next

    def set_prev(self, node):
        self.__prev = node

    def prev(self):
        return self.__prev


class Phrase:
    def __init__(self, phrase, num_words=5000):
        # initial setup
        self.phrase = phrase
        # self.words = top_5K_words_rank_dict()
        # TODO: merged list is too big and takes too long
        # OPTIONS: 
        #   start with small list but go to deeper list when no solutions
        #   start with small list but go to deeper list when one word hits zero?
        #   create new list that is bigger than 5K but smaller than 330K that is faster. 50K?
        self.words, self.one_two_fallback = merged_word_dict(num_words=num_words)
        print("{} words in dict.".format(len(self.words)))
        self.numbers = list_to_numbers(self.words)
        self.phrase_list = self.phrase.split(" ")
        self.init_phrase_opts = self.setup_phrase_word_list()
        self.init_guess_counts = {}
        for k, v in self.init_phrase_opts.items():
            self.init_guess_counts[k] = len(v)
        self.guess_order = sorted(self.init_guess_counts, key=self.init_guess_counts.get)
        self.guess_tree = None
        self.last_node = self.setup_guess_tree()

        # For guessing
        self.guesses = {}
        self.guess_node = None
        self.latest_phrase = None

    # Functions for initial setup
    def setup_phrase_word_list(self):
        phrase_list_nums = list_to_numbers(self.phrase_list)
        phrase_list_options = {}
        for phrase_word, struct in phrase_list_nums.items():
            opts = self.get_phrase_word_opts(struct)
            phrase_list_options[phrase_word] = opts
        return phrase_list_options

    def get_phrase_word_opts(self, struct):
        opts = {}
        for w, n in self.numbers.items():
            if n == struct:
                # add potential word + rank
                opts[w] = self.words[w]
        opts_ordered = sorted(opts, key=opts.get)
        return opts_ordered

    def setup_guess_tree(self):
        latest = None
        for i in range(0, len(self.guess_order)):
            if i == 0: 
                self.guess_tree = Node(self.guess_order[i], self.init_phrase_opts[self.guess_order[i]])
                latest = self.guess_tree
            else:
                latest.set_next(Node(self.guess_order[i], self.init_phrase_opts[self.guess_order[i]]))
                latest = latest.next()
        return latest


    # Functions for guessing
    def return_node_by_word(self, word):
        marker = self.guess_tree
        while marker:
            if marker.word == word:
                return marker
            marker = marker.next()
        return None

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
        phrase_word = node.word
        guess_word = node.latest_options[node.curr_guess]
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
        next = self.guess_tree
        while next:
            new_word = []
            for l in next.word:
                if self.guesses.get(l):
                    new_word.append(self.guesses[l])
                elif l == "'":
                    new_word.append(l)
                else:
                    new_word.append("[^{}]".format(exclude))
            new_phrase.append("".join(new_word))
            next.latest_word = "".join(new_word)
            next = next.next()
        logging['replace'].append(time.time()-t2)

        return new_phrase


    def update_guess_tree_opts(self):
        t3 = time.time()
        next = self.guess_node.next()
        while next:
            new_opts = return_match_list(next.options, next.latest_word)
            next.latest_options = new_opts
            next = next.next()
        logging['update'].append(time.time() - t3)


    def make_next_node_guess(self):
        if self.guess_node:
            self.guess_node = self.guess_node.next()
        else:
            self.guess_node = self.guess_tree
        if not self.guess_node:
            print("No more nodes to guess")
            return False
        self.guess_node.curr_guess = 0
        self.word_to_guesses(self.guess_node)

    def make_next_word_guess(self):
        if (self.guess_node.curr_guess + 1) < len(self.guess_node.latest_options):
            print("making next word guess")
            # remove last guesses within node
            self.remove_word_to_guesses(self.guess_node)

            # go to next guess
            self.guess_node.curr_guess += 1
            self.guess_node.incremental_guesses = []
            self.word_to_guesses(self.guess_node)
            return True
        else:
            print("no more word guesses. removing guesses within node.")
            print("You must go back to the previous node and go to the next word guess there")
            self.remove_word_to_guesses(self.guess_node)
            self.guess_node.curr_guess = None
            self.guess_node.incremental_guesses = []
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
        next = self.guess_tree
        print("phrase word | num options | num latest options")
        while next:
            counts = "{} | {} | ".format(next.word, len(next.options))
            if next.curr_guess is not None:
                num_ones += 1
                one_phrase_words.append(next.word)
                one_answers.append(next.latest_options[next.curr_guess])
                counts += "1 | {}".format(next.latest_options[next.curr_guess])
            elif len(next.latest_options) == 0:
                num_zeroes += 1
                zero_phrase_words.append(next.word)
                counts += "0"
            elif len(next.latest_options) == 1:
                num_ones += 1
                one_phrase_words.append(next.word)
                one_answers.extend(next.latest_options)
                counts += "1 | {}".format(next.latest_options[0])
            else:
                counts += "{}".format(len(next.latest_options))
            print(counts)
            next = next.next()
        return num_zeroes, zero_phrase_words, num_ones, one_phrase_words, one_answers

    def status(self):
        num_zeroes, zeroes, num_ones, ones, one_answers = self.get_latest_counts()
        if num_zeroes > 0:
            print("Failed. [{}] words had no match".format(" ".join(zeroes)))
            return "failed"
        elif num_ones == len(self.guess_order):
            print("Success! All words solved! The answer is:")
            return "solved"
        else:
            print("Keep going.")
            return "continue"

    def get_solution(self):
        next = self.guess_tree
        solution = {}
        while next:
            if next.curr_guess is None:
                next.latest_word = next.latest_options[0]
            solution[next.word] = next.latest_word
            next = next.next()
        solved_phrase = []
        for word in self.phrase_list:
            solved_phrase.append(solution[word])
        print(" ".join(solved_phrase))
        return solved_phrase

def testing_setup():
    words = top_5K_words_rank_dict()
    numbers = list_to_numbers(words)
    phrase = "b am tmy ype ym avtlg jgyygp ykvt vtemtg ghug b mthe ype ym avtlg jgyygp ykvt deughc"
    phrase_opts = get_phrase_word_opts(phrase, numbers, words)
    guesses = {}
    for k, v in phrase_opts.items():
        guesses[k] = len(v)
    guess_order = sorted(guesses, key=guesses.get)
    return words, numbers, phrase, phrase_opts, guess_order


def check_guess(opts):
    one_word = 0
    corrects = []
    no_words = 0
    fails = []
    for k, v in opts.items():
        if len(v) == 1:
            one_word += 1
            corrects.append((k,v))
        elif len(v) == 0:
            no_words += 1
            fails.append(k)
    if no_words > 0:
        print("FAILED")
        print(fails)
    elif one_word > 0:
        print("{} words solved, {} words to go".format(one_word, len(opts) - one_word))
    else:
        print("no words solved yet")

def replace_with_guess(phrase, guess):
    phrase = phrase.split(" ")
    new_phrase = []
    for word in phrase:
        new_word = []
        for l in word:
            if guess.get(l):
                new_word.append(guess[l])
            else:
                new_word.append('.')
        new_phrase.append("".join(new_word))

    return new_phrase

def replace_with_guess_and_exclude(phrase, guess):
    phrase = phrase.split(" ")
    exclude = "".join([v for k, v in guess.items()])
    new_phrase = []
    for word in phrase:
        new_word = []
        for l in word:
            if guess.get(l):
                new_word.append(guess[l])
            else:
                new_word.append("[^{}]".format(exclude))
        new_phrase.append("".join(new_word))

    return new_phrase

def update_phrase_opts(phrase, phrase_opts, new_phrase):
    phrase_opts_1 = {}
    for i in range(0, len(new_phrase)):
        # TODO: also remove options that have a guessed letter that is not in pattern
        # e.g. gypr. guessed r=t and e=s -> keep 'cart', discard 'fast'
        new_opts = return_match_list(phrase_opts[phrase.split(" ")[i]], new_phrase[i])
        phrase_opts_1[phrase.split(" ")[i]] = new_opts

    return phrase_opts_1

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

def get_phrase_word_opts_old(phrase, numbers, words):
    phrase_list = phrase.split(" ")
    phrase_list_nums = list_to_numbers(phrase_list)
    phrase_list_options = {}
    for phrase_word, struct in phrase_list_nums.items():
        opts = []
        for word, num in numbers.items():
            if num == struct:
                opts.append(word)
        phrase_list_options[phrase_word] = opts
    return phrase_list_options

def get_phrase_word_opts(phrase, numbers, words):
    phrase_list = phrase.split(" ")
    phrase_list_nums = list_to_numbers(phrase_list)
    phrase_list_options = {}
    for phrase_word, struct in phrase_list_nums.items():
        opts = {}
        for word, num in numbers.items():
            if num == struct:
                # word: rank
                opts[word] = words[word]
        # sort dict with rank
        opts_ordered = sorted(opts, key=opts.get)
        phrase_list_options[phrase_word] = opts_ordered
    return phrase_list_options

def print_logs(logs):
    for log, vals in logs.items():
        print("{} - min: {} | max: {} | avg: {}".format(log, min(vals), max(vals), sum(vals)/len(vals)))

if __name__ == "__main__":
    main()
