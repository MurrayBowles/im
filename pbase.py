''' scrape PBase pages '''

from lxml import html
import requests

class PBasePage:

    def __init__(
        self, name, url, thumb_url
    ):
        self.name = name
        self.url = url
        self.thumb_url = thumb_url
        self.is_image = url.find('/image/') != -1
        children = []

    @classmethod
    def from_url(cls, url):
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
                item = PBaseItem(
                    name=img.attrs['alt']
                url = a.attrs['href']
                thumb_url = img_attrs['src']


if __name__=='__main__':
    page = requests.get('http://www.pbase.com/murraybowles')
    proc_page(page)