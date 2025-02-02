"""
Queries arxiv API and downloads papers (the query is a parameter).
The script is intended to enrich an existing database pickle (by default db.p),
so this file will be loaded first, and then new results will be added to it.
"""

import os
import time
import pickle
import random
import argparse
import urllib.request
import feedparser
from utils import Config, safe_pickle_dump
from googletrans import Translator
import baidu_translator
import json
from requests import get
import requests
from urllib.parse import urlencode, quote

import execjs


class Py4Js():

    def __init__(self):
        self.ctx = execjs.compile(""" 
        function TL(a) { 
        var k = ""; 
        var b = 406644; 
        var b1 = 3293161072; 

        var jd = "."; 
        var $b = "+-a^+6"; 
        var Zb = "+-3^+b+-f"; 

        for (var e = [], f = 0, g = 0; g < a.length; g++) { 
            var m = a.charCodeAt(g); 
            128 > m ? e[f++] = m : (2048 > m ? e[f++] = m >> 6 | 192 : (55296 == (m & 64512) && g + 1 < a.length && 56320 == (a.charCodeAt(g + 1) & 64512) ? (m = 65536 + ((m & 1023) << 10) + (a.charCodeAt(++g) & 1023), 
            e[f++] = m >> 18 | 240, 
            e[f++] = m >> 12 & 63 | 128) : e[f++] = m >> 12 | 224, 
            e[f++] = m >> 6 & 63 | 128), 
            e[f++] = m & 63 | 128) 
        } 
        a = b; 
        for (f = 0; f < e.length; f++) a += e[f], 
        a = RL(a, $b); 
        a = RL(a, Zb); 
        a ^= b1 || 0; 
        0 > a && (a = (a & 2147483647) + 2147483648); 
        a %= 1E6; 
        return a.toString() + jd + (a ^ b) 
    }; 

    function RL(a, b) { 
        var t = "a"; 
        var Yb = "+"; 
        for (var c = 0; c < b.length - 2; c += 3) { 
            var d = b.charAt(c + 2), 
            d = d >= t ? d.charCodeAt(0) - 87 : Number(d), 
            d = b.charAt(c + 1) == Yb ? a >>> d: a << d; 
            a = b.charAt(c) == Yb ? a + d & 4294967295 : a ^ d 
        } 
        return a 
    } 
    """)

    def getTk(self, text):
        return self.ctx.call("TL", text)


# pip install  googletrans=4.0.0rc1

class TranslatorWrapper:
    def __init__(self):
        # ('https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl=en&tl=zh-cn&q={}', lambda res: eval(res.text)[0])
        self.END_POINT_LIST = [(
                               'https://translate.googleapis.com/translate_a/single?client=gtx&dt=t&sl=en&tl=zh-cn&q={}',
                               lambda res: json.loads(res.text)[0][0][0])]
        self.translator = Translator()
        self.baidu_translator = baidu_translator.Dict()
        self.test_case = 'graph neural networks'
        while True:
            try:
                # print(self._translate(self.test_case))
                print(self._translate_v3(self.test_case))
                # print(self._translate_v3(self.test_case))
                # print(self._translate_v4(self.test_case))
                break
            except Exception as e:
                print(e)  # can be commented

    def translate(self, txt, retry=10):
        for i in range(retry):
            try:
                tran_txt = self._translate_v3(txt)
                if is_contain_chinese(tran_txt):
                    return tran_txt
                else:
                    print('not contain chinese, retry i={}, tran_txt={}'.format(i, tran_txt))
            except Exception as e:
                time.sleep(2)
                print('retry i={}, error={}'.format(i, e))
        raise Exception('translate timeout...')

    def _translate(self, text):
        tran_txt = self.translator.translate(text, dest='zh-cn', ).text
        return tran_txt

    def _translate_v2(self, text):
        for endpoint, parse_func in self.END_POINT_LIST:
            try:
                url = endpoint.format(quote(text))
                print('url={}'.format(url))
                request_result = get(url)
                translated_text = parse_func(request_result)
                return translated_text
            except Exception as e:
                print('error occur, {}'.format(e))
        raise Exception('Error...')

    def _translate_v3(self, text):
        # open fanyi.baidu.com to get the code of language
        # https://fanyi.baidu.com/#zh/en/你好
        json = self.baidu_translator.dictionary(text, dst='zh', src='en')
        return json['trans_result']['data'][0]['dst']

    def _translate_v4(self, content):
        '''实现有道翻译的接口'''
        youdao_url = 'http://fanyi.youdao.com/translate?smartresult=dict&smartresult=rule'
        data = {}

        data['i'] = content
        data['from'] = 'AUTO'
        data['to'] = 'AUTO'
        data['smartresult'] = 'dict'
        data['client'] = 'fanyideskweb'
        data['salt'] = '1525141473246'
        data['sign'] = '47ee728a4465ef98ac06510bf67f3023'
        data['doctype'] = 'json'
        data['version'] = '2.1'
        data['keyfrom'] = 'fanyi.web'
        data['action'] = 'FY_BY_CLICKBUTTION'
        data['typoResult'] = 'false'
        data = urllib.parse.urlencode(data).encode('utf-8')

        youdao_response = urllib.request.urlopen(youdao_url, data)
        youdao_html = youdao_response.read().decode('utf-8')
        target = json.loads(youdao_html)

        trans = target['translateResult']
        ret = ''
        for i in range(len(trans)):
            line = ''
            for j in range(len(trans[i])):
                line = trans[i][j]['tgt']
            ret += line + '\n'

        return ret

    def _translate_v5(self, content):
        '''实现谷歌的翻译'''
        js = Py4Js()
        tk = js.getTk(content)

        if len(content) > 4891:
            print("翻译的长度超过限制！！！")
            return

        param = {'tk': tk, 'q': content}

        result = requests.get("""http://translate.google.cn/translate_a/single?client=t&sl=en 
            &tl=zh-CN&hl=zh-CN&dt=at&dt=bd&dt=ex&dt=ld&dt=md&dt=qca&dt=rw&dt=rm&dt=ss 
            &dt=t&ie=UTF-8&oe=UTF-8&clearbtn=1&otf=1&pc=1&srcrom=0&ssel=0&tsel=0&kc=2""", params=param)

        # 返回的结果为Json，解析为一个嵌套列表
        trans = result.json()[0]
        ret = ''
        for i in range(len(trans)):
            line = trans[i][0]
            if line != None:
                ret += trans[i][0]

        return ret


def encode_feedparser_dict(d):
    """
  helper function to get rid of feedparser bs with a deep copy. 
  I hate when libs wrap simple things in their own classes.
  """
    if isinstance(d, feedparser.FeedParserDict) or isinstance(d, dict):
        j = {}
        for k in d.keys():
            j[k] = encode_feedparser_dict(d[k])
        return j
    elif isinstance(d, list):
        l = []
        for k in d:
            l.append(encode_feedparser_dict(k))
        return l
    else:
        return d


def parse_arxiv_url(url):
    """
  examples is http://arxiv.org/abs/1512.08756v2
  we want to extract the raw id and the version
  """
    ix = url.rfind('/')
    idversion = url[ix + 1:]  # extract just the id (and the version)
    parts = idversion.split('v')
    assert len(parts) == 2, 'error parsing url ' + url
    return parts[0], int(parts[1])


def generate_query(keyword_list, use_abs=False, topic='recommendation'):
    queries = []
    for kw in keyword_list:
        if use_abs:
            query = '%28ti:{kw}+OR+abs:{kw}%29'.format(kw=kw)
        else:
            query = '%28ti:{kw}%29'.format(kw=kw)
        queries.append(query)

    if isinstance(topic, str) and len(topic) > 0:
        topic = [topic]

    if len(topic) > 0 and isinstance(topic, list):
        topic_query = '%28'
        for i, t in enumerate(topic):
            if i == 0:
                topic_query += 'ti:{}'.format(t)
            else:
                topic_query += '+OR+ti:{}'.format(t)
        topic_query += '%29'
        print('topic query={}'.format(topic_query))
        queries.append(topic_query)

    return "+AND+".join(queries)


def fetch(base_url, query, retry=5):
    print('fetch, {}{}'.format(base_url, query))
    for i in range(retry):
        try:
            with urllib.request.urlopen(base_url + query) as url:
                return url.read()
        except:
            print('retry i={}'.format(i))

    raise Exception('fetch timeout...')


def is_contain_chinese(check_str):
    for ch in check_str:
        if u'\u4e00' <= ch <= u'\u9fff':
            return True
    return False


if __name__ == "__main__":
    import datetime

    today = datetime.datetime.today()
    year = today.year
    month = today.month
    sep = '\t'
    fields = ['title', 'summary', 'authors', 'published', 'updated', 'url', 'version', 'cate']
    fy_fields = ['tran_title', 'tran_summary']
    translator = TranslatorWrapper()

    # parse input arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--search-query', type=str,
                        default='%28ti:CTR+OR+abs:CTR%29+AND+%28ti:graph+OR+abs:graph%29',
                        # cat:cs.CV+OR+cat:cs.AI+OR+cat:cs.LG+OR+cat:cs.CL+OR+cat:cs.NE+OR+cat:stat.ML
                        help='query used for arxiv API. See http://arxiv.org/help/api/user-manual#detailed_examples')
    parser.add_argument('--start-index', type=int, default=0, help='0 = most recent API result')
    parser.add_argument('--max-index', type=int, default=5, help='upper bound on paper index we will fetch')
    parser.add_argument('--results-per-iteration', type=int, default=100, help='passed to arxiv API')
    parser.add_argument('--wait-time', type=float, default=5.0,
                        help='lets be gentle to arxiv API (in number of seconds)')
    parser.add_argument('--break-on-no-added', type=int, default=1,
                        help='break out early if all returned query papers are already in db? 1=yes, 0=no')
    args = parser.parse_args()

    # misc hardcoded variables
    base_url = 'http://export.arxiv.org/api/query?'  # base api query url
    print('Searching arXiv for %s' % (args.search_query,))

    # lets load the existing database to memory
    try:
        db = pickle.load(open(Config.db_path, 'rb'))
    except Exception as e:
        print('error loading existing database:')
        print(e)
        print('starting from an empty database')
        db = {}

    # -----------------------------------------------------------------------------
    # main loop where we fetch the new results
    print('database has %d entries at start' % (len(db),))
    num_added_total = 0
    DEBUG = True

    for keyword in [['reinforcement', 'learning'], ['push'], ['graph'], ['cold', 'start'], ['debias'],
                    ['cross', 'domain'], ['meta', 'learning'],
                    ['click-through'], ['Contrastive', 'Learning'], ['causal'],
                    ['Multi', 'task'], ['fairness'], ['bandits'],
                    ['Multi', 'Modal'], ['Point', 'Interest'], ['recommendation']]:
        is_first_line = True
        if isinstance(keyword, str): keyword = [keyword]
        search_query = generate_query(keyword, use_abs=False, topic=['recommend', 'notification'])
        print('generated query={} for {}'.format(search_query, "-".join(keyword)))

        date = today.strftime('%Y-%m-%d')
        if not os.path.exists("data/{}/csv".format(date)):
            os.makedirs("data/{}/csv".format(date))

        with open('data/{}/csv/{}.csv'.format(date, "-".join(keyword)), 'w') as f:
            for i in range(args.start_index, args.max_index, args.results_per_iteration):
                print("Results %i - %i" % (i, i + args.results_per_iteration))
                query = 'search_query=%s&sortBy=lastUpdatedDate&start=%i&max_results=%i' % (
                search_query, i, args.results_per_iteration)
                response = fetch(base_url, query, retry=10)
                parse = feedparser.parse(response)
                num_added = 0
                num_skipped = 0
                for e in parse.entries:

                    j = encode_feedparser_dict(e)

                    rawid, version = parse_arxiv_url(j['id'])
                    j['_rawid'] = rawid
                    j['_version'] = version

                    # 读取最新的文章
                    check_date = j['updated_parsed'] if j['updated_parsed'] is not None else j['published_parsed']
                    if check_date is not None and year - check_date.tm_year > 0:
                        continue

                    if check_date.tm_mon - month > 3:
                        continue

                    if is_first_line:
                        is_first_line = False
                        f.write("{}\n".format(sep.join(fields + fy_fields)))

                    authors = ",".join([author['name'] for author in j['authors']])
                    record = [j['title'].replace('\n', ''), j['summary'].replace('\n', ''), authors,
                              time.strftime('%Y-%m-%d', j['published_parsed']),
                              time.strftime('%Y-%m-%d', j['updated_parsed']), j['id'], str(version),
                              j['arxiv_primary_category']['term']]

                    tran_title = translator.translate(record[fields.index('title')], retry=10)
                    tran_summary = translator.translate(record[fields.index('summary')], retry=10)

                    if DEBUG:
                        print('title={}, tran_title={}'.format(record[fields.index('title')], tran_title))
                        print('summary={}, tran_summary={}'.format(record[fields.index('summary')], tran_summary))

                    f.write(sep.join(record + [tran_title, tran_summary]) + "\n")

                    print('Paper %s added %s' % (j['updated'].encode('utf-8'), j['title'].encode('utf-8')))
                    # add to our database if we didn't have it before, or if this is a new version
                    if not rawid in db or j['_version'] > db[rawid]['_version']:
                        db[rawid] = j
                        print('Updated %s added %s' % (j['updated'].encode('utf-8'), j['title'].encode('utf-8')))
                        num_added += 1
                        num_added_total += 1
                    else:
                        num_skipped += 1

                # print some information
                print('Added %d papers, already had %d.' % (num_added, num_skipped))

                if len(parse.entries) == 0:
                    print('Received no results from arxiv. Rate limiting? Exiting. Restart later maybe.')
                    print(response)
                    break

                if num_added == 0 and args.break_on_no_added == 1:
                    print('No new papers were added. Assuming no new papers exist. Exiting.')

                print('Sleeping for %i seconds' % (args.wait_time,))
                time.sleep(args.wait_time + random.uniform(0, 3))

    # save the database before we quit, if we found anything new
    if num_added_total > 0:
        print('Saving database with %d papers to %s' % (len(db), Config.db_path))
        safe_pickle_dump(db, Config.db_path)
