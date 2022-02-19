import pandas as pd
import os


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
          'meta-learning': '基于元学习的推荐',
          'Multi-task': '多任务学习',
          'Multi-Modal': '多模态',
          'debias': '纠偏',
          'click-through': '点击率预估',
          'recommendation': '推荐系统',
          'Contrastive-Learning': '对比学习',
          'causal': '因果推断',
          'push': 'push通知推荐',
          'fairness': '推荐的公平性',
          'reinforcement-learning': '基于强化学习的推荐'}

time = '2022-02-19'
sep = '\t'

for topic, alias_name in topics.items():
    markdown_papers = []
    print('topic={}'.format(topic))
    time_format_path = 'data/{}/csv/{}.csv'.format(time, topic)
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

    if not os.path.exists("data/{}/md".format(time)):
        os.mkdir("data/{}/md".format(time))

    with open('data/{}/md/{}_read_papers.md'.format(time, topic), 'w') as f:
        f.write('# {}\n\n'.format(alias_name))
        f.write("收录最新{}的前沿研究工作。\n\n".format(alias_name))
        for paper in markdown_papers:
            f.write("{}{}\n".format(paper[0], paper[1]))
