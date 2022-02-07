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

# pip install  googletrans=4.0.0rc1

class TranslatorWrapper:
    def __init__(self):
        while True:
            self.translator = Translator(service_urls=['translate.google.com'])
            self.translator.client_type = 'webapp'
            try:
                trial = self.translator.detect_legacy('Hello there')
                break
            except Exception as e:
                print(e)   # can be commented

    def translate(self, txt, retry=10):
        for i in range(retry):
            try:
                tran_txt = self.translator.translate(txt, dest='zh-cn').text
                if is_contain_chinese(tran_txt):
                    return tran_txt
                else:
                    print('not contain chinese, retry i={}, tran_txt={}'.format(i, tran_txt))
            except Exception as e:
                print('retry i={}, error={}'.format(i, e))

        raise Exception('translate timeout...')


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
    for kw in keyword_list + [topic]:
        if use_abs:
            query = '%28ti:{kw}+OR+abs:{kw}%29'.format(kw=kw)
        else:
            query = '%28ti:{kw}%29'.format(kw=kw)
        queries.append(query)
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
    print(translator.translate('hello world', retry=10))

    # parse input arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--search-query', type=str,
                        default='%28ti:CTR+OR+abs:CTR%29+AND+%28ti:graph+OR+abs:graph%29',
                        # cat:cs.CV+OR+cat:cs.AI+OR+cat:cs.LG+OR+cat:cs.CL+OR+cat:cs.NE+OR+cat:stat.ML
                        help='query used for arxiv API. See http://arxiv.org/help/api/user-manual#detailed_examples')
    parser.add_argument('--start-index', type=int, default=0, help='0 = most recent API result')
    parser.add_argument('--max-index', type=int, default=5, help='upper bound on paper index we will fetch')
    parser.add_argument('--results-per-iteration', type=int, default=10, help='passed to arxiv API')
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
    print('database has %d entries at start' % (len(db), ))
    num_added_total = 0
    DEBUG = True

    for keyword in [['graph'], ['cold', 'start'],
                    ['debias'], ['cross', 'domain'], ['meta', 'learning'],
                    ['click', 'through'],
                    ['Multi', 'task'],
                    ['Multi', 'Modal']]:
        is_first_line = True
        if isinstance(keyword, str): keyword = [keyword]
        search_query = generate_query(keyword, use_abs=False, topic='recommendation')
        print('generated query={} for {}'.format(search_query, "-".join(keyword)))

        with open('data/{}_{}.csv'.format("-".join(keyword), today.strftime('%Y-%m-%d')), 'w') as f:
            for i in range(args.start_index, args.max_index, args.results_per_iteration):
                print("Results %i - %i" % (i, i + args.results_per_iteration))
                query = 'search_query=%s&sortBy=lastUpdatedDate&start=%i&max_results=%i' % (search_query, i, args.results_per_iteration)
                response = fetch(base_url, query, retry=5)
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
                    if check_date is not None and year != check_date.tm_year and check_date.tm_mon - month > 2:
                        continue

                    if is_first_line:
                        is_first_line = False
                        f.write("{}\n".format(sep.join(fields+fy_fields)))

                    authors = ",".join([author['name'] for author in j['authors']])
                    record = [j['title'].replace('\n', ''),  j['summary'].replace('\n', ''), authors,
                              time.strftime('%Y-%m-%d', j['published_parsed']), time.strftime('%Y-%m-%d', j['updated_parsed']), j['id'], str(version),
                              j['arxiv_primary_category']['term']]

                    tran_title = translator.translate(record[fields.index('title')], retry=5)
                    tran_summary = translator.translate(record[fields.index('summary')], retry=5)

                    if DEBUG:
                        print('title={}, tran_title={}'.format(record[fields.index('title')], tran_title))
                        print('summary={}, tran_summary={}'.format(record[fields.index('summary')], tran_summary))

                    f.write(sep.join(record+[tran_title, tran_summary]) + "\n")

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
                    break

                print('Sleeping for %i seconds' % (args.wait_time,))
                time.sleep(args.wait_time + random.uniform(0, 3))

    # save the database before we quit, if we found anything new
    if num_added_total > 0:
        print('Saving database with %d papers to %s' % (len(db), Config.db_path))
        safe_pickle_dump(db, Config.db_path)
