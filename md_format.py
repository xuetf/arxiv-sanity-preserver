import pandas as pd


def read_paper(data_path):
    try:
        data_pd = pd.read_csv(data_path, sep=sep)
        if len(data_pd) == 0:
            print('topic={} has no papers'.format(topic))
            return None
        return data_pd
    except:
        print('topic={} has no papers'.format(topic))
        return None


topics = {'graph': '基于Graph的推荐',
          'cold-start': '冷启动推荐',
          'cross-domain': '跨域推荐',
          'meta-learning': '元学习',
          'Multi-task': '多任务学习',
          'Multi-Modal': '多模态',
          'debias': '纠偏',
          'click-through': 'CTR'}

time = '2022-02-07'
sep = '\t'

markdown_papers = []
for topic, alias_name in topics.items():
    print('topic={}'.format(topic))
    time_format_path = 'data/{}_{}.csv'.format(topic, time)
    data_pd = read_paper(time_format_path)
    if data_pd is None:
        continue
    for row in data_pd.iterrows():
        idx = row[0]
        info = row[1]
        h1_title = '## {idx}. {tran_title}\n\n'.format(idx=idx+1, tran_title=info['tran_title'])
        summary_body = "**Title: {title}** \n\n **Published: {updated}**\n\n **Url: {url}**\n\n **Authors: {author}** \n\n {tran_summary} \n\n ```{summary}```\n".format(
                                                                                 title=info['title'],
                                                                                 updated=info['updated'],
                                                                                 author=info['authors'],
                                                                                 tran_summary=info['tran_summary'],
                                                                                 summary=info['summary'],
                                                                                 url=info['url'])

        # H1: title | trans_title
        markdown_papers.append([h1_title, summary_body])

    with open('data/{}_{}_read_papers.md'.format(topic, time), 'w') as f:
        f.write('# {}\n\n'.format(alias_name))
        for paper in markdown_papers:
            f.write("{}{}\n".format(paper[0], paper[1]))
