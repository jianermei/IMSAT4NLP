# coding:utf-8
from datetime import datetime
import requests
import json
import pprint
import os
from os.path import basename
import MeCab as mc
import commands
import codecs
import numpy as np
import pickle
import sqlite3
from random import randint
from operator import itemgetter
import bisect
from collections import Counter
from collections import defaultdict
import jaconv
import re
import csv
import collections

PICKLE_DATA = 'mecabed_data.npy'
IPADIC_PATH = '/usr/local/lib/mecab/dic/ipadic/'
IPADIC_UTF8_PATH = '/var/lib/mecab/dic/ipadic-utf8/'
PROJECT_PATH = u'/home/huang/trialdata'
FILECONTENT_PATH = './fileContent.txt'
WORDSFILE_PATH = './wordList.txt'
KAKASIFILE_PATH = './kakasiResult.txt'
DATASET_DIM = 28 * 28
DATABASE_FILE = 'projectfile.sqlite3'

def unpickle(filename):
    with open(filename, 'rb') as fo:
        p = pickle.load(fo)
    return p

def to_pickle(filename, obj):
    with open(filename, 'wb') as f:
        pickle.dump(obj, f, -1)
    pass

def get_filepaths(directory):
    """
    This function will generate the file names in a directory
    tree by walking the tree either top-down or bottom-up. For each
    directory in the tree rooted at directory top (including top itself),
    it yields a 3-tuple (dirpath, dirnames, filenames).
    """
    file_paths = []  # List which will store all of the full filepaths.

    # Walk the tree.
    for root, directories, files in os.walk(directory):
        for filename in files:
            # Join the two strings in order to form the full filepath.
            filepath = os.path.join(root, filename)
            file_paths.append(filepath)  # Add it to the list.

    return file_paths  # Self-explanatory.


def query_fessfile(query_words, db=None):
    des = 'http://10.155.37.21:8081'
    content_list = []
    # query_words =[u'GUI', u'VxWorks', u'Windows', u'医療', u'OS', u'通信', u'UI', u'リスク', u'課題', u'施策']
    # query_words = [u'憲章']

    #f = codecs.open(FILECONTENT_PATH, 'a', 'utf8')

    for query_word in query_words:
        file_idx = -1

        first_time = True
        old_query_word = None
        while True:
            base_url = des + '/fessfile/json?q=title:' + query_word.decode('utf-8')
            if '(' in base_url:
                base_url = base_url.replace('(', '\(')
            if ')' in base_url:
                base_url = base_url.replace(')', '\)')

            if first_time:
                first_time = False
                query_url = base_url
                pass

            response = requests.get(query_url)

            resp = response.json()['response']
            if 'result' in resp:
                resp_ret = resp['result']
                page_count = resp['page_count']
                page_number = resp['page_number']
                page_size = resp['page_size']
                record_count = resp['record_count']
            else:
                print('file name: ' + query_word)
                print('digest   : NONE')
                if old_query_word == query_word:
                    break
                else:
                    old_query_word = query_word
                    continue

            digest = [ret['digest'] for ret in resp_ret]
            # digest_list.append(digest)
            print('file name: ' + query_word)
            print('digest   : ' + digest[0])
            fileContent = [ret['content'] for ret in resp_ret
                                            if ret['content'] != '']
            if len(fileContent) > 0:
                content_list.append(fileContent)
                #for line in fileContent:
                #    f.write(line + '\n')
                file_idx = len(content_list) - 1

            if page_number * page_size >= record_count:
                break
            else:
                increasement = page_number * page_size
                query_url = base_url + '&start=' + str(increasement)
                pass
            pass

        if db is not None:
            db.execute(u"""INSERT INTO projectfilelist(FILE_NAME,FILE_LIST_IDX)
                    VALUES (?, ?)""", (query_word, file_idx,))
            db.commit()

    #f.close()
    return content_list


def mecab_analysis(sentence):
    t = mc.Tagger('-Ochasen -d {}'.format(IPADIC_UTF8_PATH))
    sentence = sentence.replace('\n', ' ')
    text = sentence.decode('utf-8')

    # encoded_result = t.parse(text)
    # print encoded_result

    #f = codecs.open('./mecabedWordList.txt', 'a', 'utf8')
    #print('sentence: ' + text)
    #print('node:     ')

    node = t.parseToNode(text)
    ret_list = []
    while node.next:
        if node.surface != "":
            # print node.surface + '\t' + node.feature
            word_type = node.feature.split(",")[0]
            # if word_type in ["名詞", "形容詞", "動詞"]:
            if word_type in ["名詞"]:
                plain_word = node.feature.split(",")[6]
                if plain_word != "*":
                    #print('          ' + plain_word)
                    #f.write(plain_word.decode('utf-8') + '\n')
                    ret_list.append(plain_word.decode('utf-8'))
        node = node.next

    #f.close()
    return ret_list


def exportAll():
    mecabed_list = []
    conn = sqlite3.connect(DATABASE_FILE)
    sql = '''CREATE TABLE  IF NOT EXISTS  projectfilelist(
                             file_name TEXT,
                             file_list_idx INTEGER,
                             spos_wordset INTEGER,
                             epos_wordset INTEGER,
                             project_name TEXT,
                             file_category INTEGER
                             );'''
    conn.execute(sql)
    conn.execute(u"DELETE FROM projectfilelist")

    file_names = []
    project_names = []
    full_file_paths = get_filepaths(PROJECT_PATH)
    for file_path in full_file_paths:
        # if not os.path.splitext(basename(file_path))[1] in ['.ppt', '.pptx', '.pptm']:
        #     # only need ppt, pptx, pptm
        #     continue
        path = os.path.dirname(file_path)
        foundProject = False
        for folder in path.split('/'):
            regexp = re.compile('PJ\d{6}|T\d{5}')
            if regexp.search(folder):
                project_names.append(basename(folder))
                foundProject = True
                break
        if not foundProject:
            print('A particular project: ' + path)
        file_names.append(os.path.splitext(basename(file_path))[0])

    fess_contents_list = query_fessfile(query_words=file_names, db=conn)

    print('Parsing sentences... ' + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    file_idx = 0
    sPos = 0

    for fileContent in fess_contents_list:
        inc = 0
        for line in fileContent:
            mecabed_content = mecab_analysis(line)
            mecabed_list.append(mecabed_content)
            inc += len(mecabed_content)
            pass
        # TODO: update range of wordset(sum of size(mecabed_content))
        # find db cursor where file_idx is
        # update sPos and ePos
        ePos = 0
        if inc > 0:
            ePos = sPos + inc - 1
        else:
            ePos = sPos
        conn.execute(u"""UPDATE projectfilelist
                    SET spos_wordset = ?,
                        epos_wordset = ?
                    WHERE file_list_idx = ?""", (sPos, ePos, file_idx))
        conn.commit()

        if inc > 0:
            sPos = ePos + 1
        else:
            sPos = ePos
        file_idx += 1
    print('Parsing end. ' + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))

    cur = conn.cursor()
    cur.executemany('UPDATE projectfilelist SET project_name=? WHERE file_name=?', zip(project_names, file_names))
    conn.commit()
    conn.close()
    return mecabed_list


def romanize(wordfile, romajifile):
    # print('Romanization is running..! ' + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    # execCommand = 'cat ' + wordfile + ' | kakasi -Ja -Ha -Ka -Ea -s -i utf-8 -o utf-8 > ' + romajifile
    # resp = commands.getoutput('%s' % (execCommand))
    # print('Romanization done! (' + resp + ') ' + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    #
    # print('Collecting romaji words... (' + resp + ') ' + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    # with open(romajifile, 'r') as f:
    #     content = f.readlines()
    # content = [x.strip() for x in content]
    # print('Collecting romaji words done! (' + resp + ') ' + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    
    with open(wordfile, 'r') as f:
        words = f.readlines()
    words = [x.strip() for x in words]

    print('Romanization is running..! ' + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    rmf = codecs.open(romajifile, 'a', 'utf8')
    romajilist = ['' for x in xrange(len(words))]
    for word in words:
        word = jaconv.h2z(word.decode('utf-8')) # half-width character to full-width character
        word = word.decode('utf-8')
        word = word.replace('､', '')
        word = word.replace('－', '')
        word = word.replace('】', '')
        word = word.replace('①', '1')
        word = word.replace('②', '2')
        word = word.replace('③', '3')
        word = word.replace('④', '4')
        word = word.replace('⑤', '5')
        word = word.replace('⑥', '6')
        word = word.replace('⑦', '7')
        word = word.replace('⑧', '8')
        word = word.replace('⑨', '9')
        word = word.replace('⑩', '10')
        execCommand = 'echo ' + word + ' | kakasi -Ja -Ha -Ka -Ea -s -i utf-8 -o utf-8'
        resp = commands.getoutput('%s' % (execCommand))
        # print(word + ': ' + resp)
        romajilist.append(resp)
        rmf.write(resp.decode('utf-8') + '\n')
    print('Romanization done! ' + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))

    rmf.close()
    return romajilist
    pass


def saveWords(wordlist, filename):
    # save word list to csv file(ipadic format)
    print('Saving words... ' + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    f = codecs.open(filename, 'a', 'utf8')
    for list in wordlist:
        for word in list:
            f.write(word + '\n')
    f.close()
    print('Saving done! ' + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    pass


# porting from stringToTensor() of Crepe
def string2Vector(words, l):
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789-,;.!?:'\"/\\|_@#$%^&*~`+-=<>()[]{}^"
    dict = {}
    i = 0
    for c in alphabet:
        dict[c] = i
        i += 1

    num = len(words)
    dim = l
    t = np.zeros((num, dim), dtype=np.float32)

    idx = 0
    for word in words:
        s = word.lower()

        lvalue = len(s) - l
        rvalue = 0
        sPos = len(s)
        ePos = max(lvalue, rvalue)
        inc = -1

        for i in range(sPos, ePos, inc):
            if s[i-1] in alphabet:
                t[idx][len(s) - i] = dict[s[i-1]]
                pass
            pass
        pass
        idx += 1
    pass
    return t

def testSQLITE():
    conn = sqlite3.connect('test.sqlite3')
    sql = '''CREATE TABLE  IF NOT EXISTS  t01prefecture(
                             pref_cd INTEGER,
                             pref_name TEXT);'''
    conn.execute(sql)

    conn.execute(u"DELETE FROM t01prefecture")

    # コミットの試験
    pref_cd = 100
    pref_name = u"モテモテ国"
    conn.execute(u"""INSERT INTO t01prefecture(PREF_CD, PREF_NAME)
                VALUES (?, ?)""", (pref_cd, pref_name))

    pref_cd = 101
    pref_name = u"野望の国"
    conn.execute(u"""INSERT INTO t01prefecture(PREF_CD,PREF_NAME)
                VALUES (?, ?)""", (pref_cd, pref_name,))
    conn.commit()

    # ロールバックの試験
    pref_cd = 102
    pref_name = u"back"
    conn.execute(u"""INSERT INTO t01prefecture(PREF_CD,PREF_NAME)
                VALUES (?, ?)""", (pref_cd, pref_name,))
    conn.rollback()

    rows = conn.execute(u'SELECT * FROM t01prefecture WHERE pref_cd > ?', (0,))
    for row in rows:
        print(u"%d %s" % (row[0], row[1]))

    # ユーザ定義
    # 文字を連結するのみ
    class UserDef:
        def __init__(self):
            self.values = []

        def step(self, value):
            self.values.append(value)

        def finalize(self):
            return "/".join(map(str, self.values))

    #conn.create_aggregate("userdef", 1, UserDef)
    #rows = conn.execute(u'SELECT userdef(PREF_NAME) FROM t01prefecture')
    #for row in rows:
    #    print(u"%s" % (row[0]))

    conn.close()
    pass


def testSQLITE2():
    db = sqlite3.connect('projectfile.sqlite3')
    sql = '''CREATE TABLE  IF NOT EXISTS  projectfilelist(
                             file_name TEXT,
                             spos_wordset INTEGER,
                             epos_wordset INTEGER,
                             project_name TEXT,
                             file_category INTEGER
                             );'''
    db.execute(sql)

    db.execute(u"DELETE FROM projectfilelist")

    db.close()
    pass

def list_duplicates(seq):
    tally = defaultdict(list)
    for i, item in enumerate(seq):
        tally[item].append(i)
    return ((key, locs) for key, locs in tally.items()
            if len(locs) > 1)

def testSQLITE3():
    a = range(60000)  # type
    b = range(60000)  # idx

    for i in range(60000):
        a[i], b[i] = randint(1, 10), randint(1, 60000)

    for dup in sorted(list_duplicates(a)):
        print dup

    data = zip(a, b)
    print data

    sorted_data = sorted(data, key=itemgetter(1))
    print sorted_data

    fType = range(len(sorted_data))
    idx = range(len(sorted_data))
    for i in range(len(sorted_data)):
        fType[i] = sorted_data[i][0]
        idx[i] = sorted_data[i][1]

    print fType
    print idx

    # find max sorted_data[x][1] less than ePos
    target = 3382
    index = bisect.bisect(idx, target)
    print "Greater than target", idx[index]
    print "Smaller than or equal to target", idx[index - 1]

    # find most frequent in () ~ sorted_data[x][0]
    count = Counter(fType[0:idx[index]])
    freq = count.most_common()
    print freq

    pass

def testSQLITE4():
    
    conn = sqlite3.connect(DATABASE_FILE)
    cur = conn.cursor()
    cur.execute("SELECT spos_wordset, epos_wordset, file_name FROM projectfilelist")
    rows = cur.fetchall()
    fileNames = ["" for x in range(len(rows))]
    fileTypes = range(len(rows))
    i = 0
    for row in rows:
        fileName = row[2]
        fileNames[i] = fileName
        fileType = randint(1, 10)
        fileTypes[i] = fileType
        if row[0] is not None:
            print fileName + str(row[0]) + ', ' + str(row[1])
        i += 1
    
    cur.executemany('UPDATE projectfilelist SET file_category=? WHERE file_name=?', zip(fileTypes, fileNames))
    conn.commit()
    conn.close()
    pass

def loadCSV():
    project_names = []
    file_types = []
    with open('projectFile.csv', 'rb') as f:
        reader = csv.reader(f)
        your_list = list(reader)
    
    first_item = True
    for item in your_list:
        if first_item:
            first_item = False
            continue
        project_names.append(item[4])
        file_types.append(item[5])

    for dup in sorted(list_duplicates(project_names)):
        #print '-----------------------'
        #print dup
        project_name = dup[0]
        part_file_types = []
        for file_type_idx in dup[1]:
            part_file_types.append(file_types[file_type_idx])
        #print(project_name)
        #print part_file_types
        counter = collections.Counter(part_file_types)
        #print(counter)
        print(project_name + ', ' + str(counter.keys()[0]))
    pass


def saveProjectContents():
    filename = 'ProjectType9Contents.txt'
    file_names = []
    full_file_paths = get_filepaths(u'/home/huang/ProjectType9')
    for file_path in full_file_paths:
        # if not os.path.splitext(basename(file_path))[1] in ['.ppt', '.pptx', '.pptm']:
        #     # only need ppt, pptx, pptm
        #     continue
        file_names.append(os.path.splitext(basename(file_path))[0])

    fess_contents_list = query_fessfile(query_words=file_names)
    f = codecs.open(filename, 'a', 'utf8')
    for fileContent in fess_contents_list:
        inc = 0
        for line in fileContent:
            f.write(line + '\n')
    f.close()

    pass

#testSQLITE()

#testSQLITE2()

#testSQLITE3()

#testSQLITE4()

#loadCSV()

#saveProjectContents()

#words = exportAll()
#to_pickle(PICKLE_DATA, words)
#words = unpickle(PICKLE_DATA)
#print('read words ' + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))

#saveWords(words, WORDSFILE_PATH)
#romajiWords = romanize(WORDSFILE_PATH, KAKASIFILE_PATH)
#dataset = string2Vector(romajiWords, DATASET_DIM)

def load_word_set():
    #words = exportAll()
    #to_pickle(PICKLE_DATA, words)
    #words = unpickle(PICKLE_DATA)
    #print('read words ' + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))

    #saveWords(words, WORDSFILE_PATH)
    #romajiWords = romanize(WORDSFILE_PATH, KAKASIFILE_PATH)
    with open(KAKASIFILE_PATH, 'r') as f:
        romajiWords = f.readlines()
    romajiWords = [x.strip() for x in romajiWords]
    dataset = string2Vector(romajiWords, DATASET_DIM)
    
    return dataset

pass
