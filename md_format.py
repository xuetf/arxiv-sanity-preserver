import pandas as pd

topics = {'graph': '基于Graph的推荐'}
time = '2022-01-30'
sep = '\t'

markdown_papers = []
for topic, alias_name in topics.items():
    time_format = 'data/{}_{}.csv'.format(topic, time)
    data_pd = pd.read_csv(time_format, sep=sep)
    print(data_pd)
    for row in data_pd.iterrows():
        idx = row[0]
        info = row[1]
        h1_title = '## {idx}. {tran_title}\n\n'.format(idx=idx+1, tran_title=info['tran_title'])
        summary_body = "**Title: {title}** \n\n **Published: {updated}**\n\n **Authors: {author}** \n\n {tran_summary} \n\n ```{summary}```\n".format(
                                                                                 title=info['title'],
                                                                                 updated=info['updated'],
                                                                                 author=info['authors'],
                                                                                 tran_summary=info['tran_summary'],
                                                                                 summary=info['summary'])

        # H1: title | trans_title
        markdown_papers.append([h1_title, summary_body])

    with open('data/{}_{}_read_papers.md'.format(topic, time), 'w') as f:
        f.write('# {}\n\n'.format(alias_name))
        for paper in markdown_papers:
            f.write("{}{}\n".format(paper[0], paper[1]))
