#!/usr/local/env python3

import os
from os.path import basename
from glob import glob
import markdown
from bs4 import BeautifulSoup

def generate_index_html(files):
    # generate tbody
    text = ''
    for fp in files:
        date, name = fp.split('-', 1)
        href, _ = fp.split('.md')
        text += f'<tr><td>{date}</td>'
        text += f'<td><a href="{href}.html">{name}</a></td></tr>'
    text = f'<tbody>{text}</tbody>'

    # parse index.html
    with open('./docs/index.html', encoding='utf-8') as fp:
        index_doc = fp.read()
    soup = BeautifulSoup(index_doc, 'html.parser')
    soup.find('tbody').replaceWith(BeautifulSoup(text, 'html.parser'))
    
    html = soup.prettify('utf-8')
    with open('./docs/index.html', 'w', encoding='utf-8') as fp:
        fp.write(str(html, encoding='utf-8'))

def convert_markdown_to_html(files):
    with open('./docs/template.html', encoding='utf-8') as fp:
        template_doc = fp.read()
    template = BeautifulSoup(template_doc, 'html.parser')
    
    exts = ['markdown.extensions.extra', 'markdown.extensions.codehilite','markdown.extensions.tables','markdown.extensions.toc']
    for fp in files:
        with open(fp, encoding='utf-8') as f:
            content = f.read()
            ret = markdown.markdown(content, extensions=exts)
            ret = f'<main role="main"><div class="container">{ret}</div></main>'
            newname, _ = fp.split('.md')
            newpath = f'./docs/{newname}.html'
            template.find('title').replaceWith(BeautifulSoup(f'<title>{newname}</title>', 'html.parser'))
            template.find('main').replaceWith(BeautifulSoup(ret, 'html.parser'))
            html = template.prettify('utf-8')
            with open(newpath, 'w', encoding='utf-8') as fp:
                fp.write(str(html, encoding='utf-8'))

if __name__ == "__main__":
    files = [basename(fp) for fp in glob("./20*.md")]
    generate_index_html(files)
    convert_markdown_to_html(files)
