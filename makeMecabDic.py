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

IPADIC_PATH = '/usr/local/lib/mecab/dic/ipadic/'
IPADIC_UTF8_PATH = '/var/lib/mecab/dic/ipadic-utf8/'
PROJECT_PATH = u'./trialdata/'

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

def query_fessfile():
    des = 'http://10.155.37.21:8081'
    digest_list = []
    content_list = []
    # query_words =[u'GUI', u'VxWorks', u'Windows', u'医療', u'OS', u'通信', u'UI', u'リスク', u'課題', u'施策']
    # query_words = [u'憲章']
    file_names = []

    full_file_paths = get_filepaths(PROJECT_PATH)
    for file_path in full_file_paths:
        file_names.append(os.path.splitext(basename(file_path))[0])

    for query_word in file_names:
        response = requests.get(
            des + '/fessfile/json?q=title:' + query_word.encode('utf-8'))
        # response.encoding = response.apparent_encoding
        # pprint.pprint(response.json())

        if 'result' in response.json()['response']:
            resp_ret = response.json()['response']['result']
        else:
            print('file name: ' + query_word)
            print('digest   : NONE')
            continue

        digest = [ret['digest'] for ret in resp_ret]
        # digest_list.append(digest)
        print('file name: ' + query_word)
        print('digest   : ' + digest[0])
        content = [ret['content'] for ret in resp_ret]
        content_list.append(content)
        pass

    return content_list

TERMEXTRACT_SERVER = '10.120.175.86'
TERMEXTRACT_PORT = '9006'

def term_analysis(sentence):
    ret_list = []
    des = 'http://' + TERMEXTRACT_SERVER + ':' + TERMEXTRACT_PORT

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

def term2dic(terms_list):
    dic_name = 'projectTrialData.dic'
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

    pass

def makeMecabDic():
    terms_list = []
    print('query fess ' + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    fess_contents_list = query_fessfile()

    print('get term ' + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    for contents in fess_contents_list:
        for content in contents:
            terms = term_analysis(content)
            terms_list.append(terms)
            pass

    print('create dic ' + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    term2dic(terms_list)

    pass

makeMecabDic()