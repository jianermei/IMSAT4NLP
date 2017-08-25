# coding:utf-8
import requests
import json
import pprint
import pickle
import os
from os.path import basename
import requests
import pprint
import MeCab as mc
import time
import codecs
import commands
from datetime import datetime
from os.path import expanduser
from shutil import copy2
import numpy as np
import jaconv
import sqlite3
import re
import db_tools
from collections import defaultdict
from collections import Counter

HOME = expanduser("~")
IPADIC_PATH = '/usr/local/lib/mecab/dic/ipadic/'
IPADIC_UTF8_PATH = '/var/lib/mecab/dic/ipadic-utf8/'
PROJECT_PATH = HOME + '/WuXiSampleData/'
FESS_FILE_SERVER = '10.155.37.21:8081'
TERMEXTRACT_SERVER = '10.120.175.86:9006'
USER_DIC_PATH = '/mecabdic'
FRAME_SIZE = 28 * 28  # size of picture's pixels in mnist
MECABEDFILE_PATH = './mecabedWordList.txt'
ROMAJIFILE_PATH = './romajiWordList.txt'
DATABASE_FILE = 'projectFileWithType.sqlite3'


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


def clear(word):
    word = jaconv.h2z(word)  # half-width character to full-width character
    word = word.encode('utf-8')
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
    return word


def recursive_len(item):
    if type(item) == list:
        return sum(recursive_len(subitem) for subitem in item)
    else:
        return 1


def addUserDic(dic_file):
    # find whether dic folder exists
    directory = HOME + USER_DIC_PATH
    if not os.path.exists(directory):
        os.makedirs(directory)
    # then copy dic into dic folder
    copy2(dic_file, directory)
    pass


def term2dic(terms_list):
    ts = str(int(time.time()))
    dic_name = 'user_' + ts + '.dic'
    word_list = []
    for terms in terms_list:
        for term in terms:
            word_list.append(term)

    # save word list to csv file(ipadic format)
    wordlist_name = 'wordlist_' + str(dic_name.split('.')[0]) + '.csv'
    f = codecs.open(wordlist_name, 'a', 'utf8')
    for i in range(word_list.__len__()):
        word = word_list[i]
        csv_line = word + u',,,1,名詞,一般,*,*,*,*,' + word + u',*,*,ByMeCabEst'
        f.write(csv_line + '\n')
    f.close()

    # convert csv file(ipadic format) to dic
    modelFile = './mecab-ipadic-2.7.0-20070801.model'
    dicdir = './mecab-ipadic-2.7.0-20070801'
    userdicCommand = '/usr/lib/mecab/mecab-dict-index ' + \
                    ' -m ' + modelFile + \
                    ' -d ' + dicdir + \
                    ' -f utf-8 -t utf-8 ' + \
                    ' -u ' + dic_name + \
                    '    ' + wordlist_name
    resp = commands.getoutput(userdicCommand)
    print('mecab creating result: ' + resp)
    
    return dic_name


def term_analysis(sentence):
    ret_list = []
    des = 'http://' + TERMEXTRACT_SERVER

    post_resp = requests.post(
        des+'/text',
        json.dumps({"count": 1, "textlist": [sentence]}),
        headers={'Content-Type': 'application/json'})
    # pprint.pprint(response.json())

    # TODO: it's a temporary method
    time.sleep(2)

    text_id = post_resp.json()['_id']
    print('text_id: ' + text_id)
    get_resp = requests.get(des + '/text' + '/' + text_id + '/keyword')
    term_list = get_resp.json()['_items'][0]['termlist']

    onetime = True
    for term in term_list:
         if onetime:
             print('term: ' + term['word'])
             onetime = False
         ret_list.append(term['word'])

    return ret_list


def query_fessfile(query_words, db=None):
    des = 'http://' + FESS_FILE_SERVER
    content_list = []
    # query_words =[u'GUI', u'VxWorks', u'Windows', u'医療', u'OS', u'通信', u'UI', u'リスク', u'課題', u'施策']
    # query_words = [u'憲章']

    #f = codecs.open(FILECONTENT_PATH, 'a', 'utf8')

    for query_word in query_words:
        file_idx = -1

        first_time = True
        old_query_word = None
        while True:
            base_url = des + '/fessfile/json?q=title:' + query_word
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
            print('file name: ' + query_word.encode('utf-8'))
            print('digest   : ' + digest[0].encode('utf-8'))
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


def makeMecabDic():
    print('query fess ' + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    terms_list = []
    file_names = []

    full_file_paths = get_filepaths(PROJECT_PATH)
    for file_path in full_file_paths:
        file_names.append(os.path.splitext(basename(file_path))[0].decode('utf-8'))
        
    fess_contents_list = query_fessfile(query_words=file_names)

    print('get term ' + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    for contents in fess_contents_list:
        for content in contents:
            terms = term_analysis(content)
            terms_list.append(terms)
            pass

    print('create dic ' + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    dic_file = term2dic(terms_list)
    addUserDic(dic_file)


def mecab_analysis(sentence):
    t = mc.Tagger('-Ochasen -d {}'.format(IPADIC_UTF8_PATH))
    sentence = sentence.replace('\n', ' ')
    text = sentence.encode('utf-8')

    # encoded_result = t.parse(text)
    # print encoded_result

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

    return ret_list


# porting from stringToTensor() of Crepe
def strings2Tensor(words, l):
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

    
def romanize(wordlist):
    mecabed_file = MECABEDFILE_PATH
    romaji_file = ROMAJIFILE_PATH
    num_word = recursive_len(wordlist)
    romajilist = ['' for x in xrange(num_word)]

    # save word list to csv file(ipadic format)
    print('Romanization mecabed words... ' + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    f = codecs.open(mecabed_file, 'a', 'utf8')
    rf = codecs.open(romaji_file, 'a', 'utf8')
    
    for list in wordlist:
        for word in list:
            f.write(word + '\n')
            word = clear(word)
            execCommand = 'echo ' + word + ' | kakasi -Ja -Ha -Ka -Ea -s -i utf-8 -o utf-8'
            resp = commands.getoutput('%s' % (execCommand))
            # print(word + ': ' + resp)
            romajilist.append(resp)
            rf.write(resp.decode('utf-8') + '\n')
            
    rf.close()
    f.close()
    print('Romanization done! ' + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))


def get_project_name(file_path):
    pj_name = ''
    dir_path = os.path.dirname(file_path)

    foundProject = False
    for folder in dir_path.split('/'):
        regexp = re.compile('PJ\d{6}|T\d{5}')  # PJ123456 or T12345
        if regexp.search(folder):
            pj_name = basename(folder)
            foundProject = True
            break
    
    if not foundProject:
        print('A particular project: ' + dir_path)

    return pj_name


def loadWords():
    conn = db_tools.init(DATABASE_FILE)
    mecabed_list = []
    file_names = []
    project_names = []
    
    full_file_paths = get_filepaths(PROJECT_PATH)
    for file_path in full_file_paths:
        project_name = get_project_name(file_path)
        project_names.append(project_name.decode('utf-8'))
        file_names.append(os.path.splitext(basename(file_path))[0].decode('utf-8'))
    
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
        # TODO: update range of file's word index(num of words in fileContent)
        sPos = db_tools.update_word_index(conn=conn, file_idx=file_idx, word_cursor=sPos, num_word=inc)
        file_idx += 1
    print('Parsing end. ' + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    
    db_tools.update_project_name(conn, file_names, project_names)
    
    db_tools.close(conn)
    
    return mecabed_list


def loadWordSet():
    words = loadWords()
    
    romanize(words)
    with open(ROMAJIFILE_PATH, 'r') as f:
        romajis = f.readlines()
    romajiWords = [x.strip() for x in romajis]

    dataset = strings2Tensor(romajiWords, FRAME_SIZE)
    
    return dataset


def list_duplicates(seq):
    tally = defaultdict(list)
    for i, item in enumerate(seq):
        tally[item].append(i)
    return ((key, locs) for key, locs in tally.items()
            if len(locs) >= 1)


def find_project_type(db_file=DATABASE_FILE):
    conn = db_tools.open_db(db_file)
    rows = db_tools.get_rows(conn)
    project_names = []
    file_types = []
    project_type_dic = {}

    for row in rows:
        project_name = row[4]  # project_name
        file_category = row[5]  # file_category
        project_names.append(project_name)
        file_types.append(file_category)

    for dup in sorted(list_duplicates(project_names)):
        #print '-----------------------'
        #print dup
        project_name = dup[0]
        part_file_types = []
        for file_type_idx in dup[1]:
            part_file_types.append(file_types[file_type_idx])
        #print(project_name)
        #print part_file_types
        counter = Counter(part_file_types)
        #print(counter)
        print(project_name + ', ' + str(counter.keys()[0]))
        project_type_dic[project_name] = counter.keys()[0]

    db_tools.close(conn)
    return project_type_dic


def find_project_file(db_file=DATABASE_FILE):
    conn = db_tools.open_db(db_file)
    rows = db_tools.get_rows(conn)
    project_file_dic = {}
    
    for row in rows:
        file_name = row[0]  # file_name
        project_name = row[4]  # project_name
        
        if project_name not in project_file_dic:
            project_file_dic[project_name] = []
        project_file_dic[project_name].append(file_name)

    db_tools.close(conn)
    return project_file_dic


def find_project_term(project_file):
    project_term_dic = {}
    
    for project_name in project_file:
        file_names = project_file[project_name]
        fess_contents_list = query_fessfile(query_words=file_names)
        
        terms_list = []
        print('get term ' + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
        for contents in fess_contents_list:
            for content in contents:
                terms = term_analysis(content)
                terms_list.append(terms)

        project_term_dic[project_name] = terms_list
    
    return project_term_dic


def makeJSON(db_file=DATABASE_FILE, json_type='a'):
    project_type = find_project_type(db_file)
    project_file = find_project_file(db_file)
    project_term = find_project_term(project_file)
    
    type_project_dict = {}
    for k, v in project_type.iteritems():
        type_project_dict.setdefault(v, []).append(k)

    if json_type is '0' or 'a':
        json0 = []
        for type, projects in type_project_dict.iteritems():
            # print('type:      ' + str(type))
            # print ('projects: ')
            # print(projects)
        
            project_term_dic = {}
            project_term_dic['name'] = projects
            project_term_dic['keyword'] = []
        
            for project in projects:
                # print('project name: ' + project)
                term_lists = project_term[project]
                for term_list in term_lists:
                    # print('term: ' + term_list[0])
                    project_term_dic['keyword'] += term_list
                project_term_dic['keyword'] = list(set(project_term_dic['keyword']))
            json0.append(project_term_dic)
    
        f0 = open('json0.txt', 'w')
        f0.write(json.dumps(json0))
        f0.close()
    
    if json_type is '1' or 'a':
        json1 = {}
        for type, projects in type_project_dict.iteritems():
            # print('type:      ' + str(type))
            # print ('projects: ')
            # print(projects)

            json1[type] = {}
            for project in projects:
                # print('project name: ' + project)
                term_lists = project_term[project]
                for term_list in term_lists:
                    # print('term: ' + term_list[0])
                    term_project_dict = dict((term, project) for term in term_list)
                    json1[type].update(term_project_dict)
    
        f1 = open('json1.txt', 'w')
        f1.write(json.dumps(json1))
        f1.close()

    if json_type is '2' or 'a':
        json2 = {}
        for type, projects in type_project_dict.iteritems():
            # print('type:      ' + str(type))
            # print ('projects: ')
            # print(projects)
            if type not in json2:
                json2[type] = []
        
            for project in projects:
                # print('project name: ' + project)
                term_lists = project_term[project]
                for term_list in term_lists:
                    # print('term: ' + term_list[0])
                    json2[type] += term_list
            json2[type] = list(set(json2[type]))
    
        f2 = open('json2.txt', 'w')
        f2.write(json.dumps(json2))
        f2.close()
