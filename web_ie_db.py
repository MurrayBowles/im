""" scrape PBase pages """

import datetime
from lxml import html
import os
import requests

from ie_fs import add_ie_folder_image_inst, add_ie_folder_name_tag, add_ie_folder_name_word_tags
from ie_fs import IEMsg, IEMsgType, IETag, IETagType

# page-contents directory to avoid web accesses while testing
use_test_pages = True
save_test_pages = True  # ignored if use_test_pages
test_dir_path = \
'c:\\\\Users\\Murray\\PycharmProjects\\im\\test\\import-export sources\\web pages'

# tag map: ( [ <base> list ], { <line type str>: [ <template list> ] )
# template: +<base digit> | -<base digit> | ? | N  (see IETagType)

show_tag_map = (
    [ 'band', 'event' ],
    {
        '1':    [ '-0' ],
        'T':    [ '+0' ],
        '1T':   [ '-1', '+0' ],
        '1TF':  [ '-1', '+0', 'N' ],
        '1F':   [ '-1', 'N' ],
        'TF':   [ '+0', 'N' ]
    }
)

people_tag_map = (
    [ 'event' ],
    {
        '1':    [ '-0' ],
        '1F':   [ '-0', 'N' ]
    }
)

# top-level gallery db_name => header line interpretation
gallery_tag_map = {
    'shows':        show_tag_map,
    'old shows':    show_tag_map,
    'people':       people_tag_map
}

# 'top_gallery' is
#   None      the 'murraybowles' entry page
#   'shows'   the shows gallery and its subgalleries
#   ...

def get_gallery_header_tags(header_list, base_gallery):
    """ return a list of IETags derived from the gallery headers """

    def line_type_str(lines):
        def is_fb_event(line):
            def is_fb_word(word):
                word = word.replace(' ', '').lower()
                return word in ['fbevent', 'fblink']
            return (
                line[0][0] == '[' and
                is_fb_word(line[1][0]) and
                line[2][0] == ']'
            )
        s = ''
        for l in lines:
            if len(l) == 1:
                s += '1'    # single line
            elif len(l) == 3 and is_fb_event(l):
                s += 'F'    # FBEvent line
            else:
                s += 'T'    # tags line
        return s

    def get_line_tags(line, line_type, template, bases, tags):
        """ append IETags for <line> to <tags> """
        tag_type = IETagType.from_code(template[0])
        base = bases[int(template[1])] if len(template) == 2 else None
        if line_type == '1':
            tags.append(IETag(tag_type, line[0][0], base, line[0][1]))
        elif line_type == 'T':
            for elt in line:
                tags.append(IETag(tag_type, elt[0], base, elt[1]))
        else: # line_type == 'F':
            tags.append(
                IETag(IETagType.NOTE, 'Facebook Event', None, line[1][1]))

    if len(header_list) == 0 or base_gallery is None:
        return [] # no autotagging

    assert len(header_list) == 1
    header = header_list[0]
    assert len(header) > 0
    assert header[0].text == ' BEGIN user desc '
    assert header[-1].text == ' END user desc '

    # read the lines and their items from the gallery header
    lines = []
    line = []
    lines.append(line)
    for elt in header:
        try:
            tag = elt.tag
            if tag == 'a':
                if 'href' in elt.attrib:
                    line.append((elt.text, elt.attrib['href']))
            elif tag == 'br':
                line = []
                lines.append(line)
        except:
            try:
                line.append((elt.text, None))
            except:
                pass
        try:
            tail = elt.tail
            if tail[0] == '\n':
                line = []
                lines.append(line)
            tail = tail.strip('\r\n')
            if tail.find(',') != -1:
                for item in tail.split(','):
                    item = item.strip(' ')
                    line.append((item, None))
            else:
                line.append((tail, None))
        except:
            pass
    lines = [[e for e in l if len(e[0]) != 0] for l in lines if len(l) != 0]
    lines = [l for l in lines if len(l) != 0]

    # collect the IETags for the lines
    tags = []
    lts = line_type_str(lines)
    if base_gallery in gallery_tag_map:
        tag_map = gallery_tag_map[base_gallery]
        if lts in tag_map[1]:
            templates = tag_map[1][lts]
            for x in range(len(lts)):
                # tagged according to the line's template
                get_line_tags(lines[x], lts[x], templates[x], tag_map[0], tags)
            return tags
    for x in range(len(lts)):
        # all tagged as UNBASED or NOTES
        get_line_tags(lines[x], lts[x], '?', [], tags)
    return tags

def scan_pbase_gallery_bytes(
    path, bytes, top_gallery,
    proc_gallery_link, proc_gallery_tag,  proc_image_link
):
    """ scrape date from the gallery page at <db_name>
        for each item in the gallery description area,
            call proc_gallery_tag(IETag)
        for each image thumbnail,
            call proc_image_link(url, image_name)
        for each gallery thumbnail,
            call proc_gallery_link(db_name)
    """

    tree = html.fromstring(bytes)

    # get IETags from the gallery header
    gallery_header_list = tree.xpath('//div[@class="galleryheader"]')
    tags = get_gallery_header_tags(gallery_header_list, top_gallery)
    for tag in tags:
        proc_gallery_tag(tag)

    # scan the thumbnails in the gallery
    thumb_div_list = tree.xpath('//div[@class="thumbnails"]')
    if len(thumb_div_list) == 0:
        pass
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
                # an image link
                image_name = img_attrs['alt']
                proc_image_link(url, image_name)
                pass
            else:
                # a gallery link
                prefix, child_path = url.split(':')
                proc_gallery_link(child_path)
            pass
    pass

def scan_pbase_gallery(
    path, top_gallery, proc_gallery_link, proc_gallery_tag,  proc_image_link
):
    if use_test_pages or save_test_pages:
        gallery_path_slash = path[2:].find('/')
        gallery_path = path[2+gallery_path_slash+1:]
        if gallery_path != 'murraybowles':
            gallery_path = os.path.basename(gallery_path)
        test_page_path = os.path.join(test_dir_path, gallery_path)
    else:
        test_page_path = '' # shut lint up

    if use_test_pages:
        try:
            f = open(test_page_path, 'rb')
        except:
            # the test directory doesn't have images of all pages
            # don't process the ones we don't have
            return
        bytes = f.read()
        f.close()
    else:
        url = 'http:' + path
        if top_gallery is not None:
            url += '&page=all'
        page = requests.get(url)
        bytes = page.content
        if save_test_pages:
            f = open(test_page_path, 'wb')
            f.write(bytes)
            f.close()

    scan_pbase_gallery_bytes(
        path, bytes, top_gallery,
        proc_gallery_link, proc_gallery_tag, proc_image_link)

def scan_web_page_children(ie_folder, top_gallery, child_paths):
    """ collect IEImages, IETags, and child paths for the gallery of <ie-folder>
        see scan_pbase_gallery()
    """
    got_gallery_tags = [False]
    def on_gallery_link(path):
        child_paths.append(path)
    def on_gallery_tag(tag):
        got_gallery_tags[0] = True
        ie_folder.add_tag(tag)
    def on_image_link(path, name):
        add_ie_folder_image_inst(
            ie_folder, path, name,
            high_res=False,
            mtime=datetime.datetime.now())
    scan_pbase_gallery(ie_folder.fs_path, top_gallery,
        on_gallery_link, on_gallery_tag, on_image_link)
    if got_gallery_tags[0]:
        # the standard case: there's a header with band tags,
        # and the folder db_name is a venue
        add_ie_folder_name_tag(ie_folder, 'venue')
    else:
        # who knows?
        add_ie_folder_name_word_tags(ie_folder, 'band, venue, place, event')
        ie_folder.msgs.append(
            IEMsg(IEMsgType.NAME_NEEDS_EDIT, ie_folder.db_name))

def _test_pbase_scan(gallery, top_gallery):
    def on_gallery_link(path):
        pass
    def on_gallery_tag(tag):
        pass
    def on_image_link(path, name):
        pass
    scan_pbase_gallery(
        '//www.pbase.com/murraybowles/' + gallery, top_gallery,
        on_gallery_link, on_gallery_tag, on_image_link)

if __name__=='__main__':
    _test_pbase_scan('170923_diana', 'shows')
    _test_pbase_scan('171007_virginia', 'shows')
    _test_pbase_scan('171007_blockers', 'shows')
    _test_pbase_scan('160816_7th_st', 'shows')
    _test_pbase_scan('160611_fern_and_gregs_birthday', 'people')
    pass