''' scrape PBase pages '''

import datetime
from lxml import html
import re
import requests

from ie_fs import add_ie_folder_image_inst

def proc_page(page):
    items = []
    tree = html.fromstring(page.content)
    thumb_div_list = tree.xpath('//div[@class="thumbnails"]')
    thumb_div = thumb_div_list[0]
    center = thumb_div[0]
    table = center[0]
    for tr in table:
        for td in tr:
            a = td[0]
            a_attrs = a.attrib
            img = a[0]
            img_attrs = img.attrib
            url = a_attrs['href']
            thumb_url = img_attrs['src']
            pass
    pass

leading_date_space = re.compile(r'^\d{6,6} ')

def scan_web_page_children(ie_folder, child_paths, top_level):
    path = ie_folder.fs_path
    url = 'http:' + path
    if not top_level:
        url += '&page=all'
    page = requests.get(url)
    tree = html.fromstring(page.content)
    thumb_div_list = tree.xpath('//div[@class="thumbnails"]')
    thumb_div = thumb_div_list[0]
    if thumb_div[0].tag == 'center':
        center = thumb_div[0]
        table = center[0]
    else:
        assert len(thumb_div) >= 2
        table = thumb_div[1][0]
    assert table.tag == 'table'
    row = 0
    for tr in table:
        row += 1
        datum = 0
        for td in tr:
            datum += 1
            if len(td) == 0:
                continue
            a = td[0]
            if a.tag != 'a':
                continue
            a_attrs = a.attrib
            if len(a) == 0:
                continue
            img = a[0]
            img_attrs = img.attrib
            url = a_attrs['href']
            thumb_url = img_attrs['src']
            if url.find('/image/') != -1:
                # an image
                image_name = img_attrs['alt']
                add_ie_folder_image_inst(
                    ie_folder, url, image_name,
                    high_res=False,
                    mtime = datetime.datetime.now)
                pass
            else:
                # a child page
                prefix, child_path = url.split(':')
                child_paths.append(child_path)
            pass
    pass

if __name__=='__main__':
    page = requests.get('http://www.pbase.com/murraybowles')
    proc_page(page)