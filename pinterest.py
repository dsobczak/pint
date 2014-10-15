#!/usr/bin/python

from scrapy.spider import Spider
from scrapy.selector import Selector
from scrapy.contrib.loader import ItemLoader
from scrapy.item import Item, Field
from scrapy.http import Request, FormRequest
from scrapy.contrib.loader.processor import TakeFirst, Join

import json
import re
import pdb
import warnings
import os
import sys

# Temporarily write JSON here
OUTFILENAME = 'output'


#
# SCRAPER CODE
#

class OutfilePipeline(object):
    def open_spider(self, spider):
        if(os.path.exists(OUTFILENAME)):
            os.remove(OUTFILENAME)

    def process_item(self, item, spider):
        with open(OUTFILENAME, 'ab') as outfile:
            json.dump(dict(item), outfile)
            outfile.write('\n')
        return item


class Record(Item):
    title = Field()
    description = Field()
    detail_url = Field()
    image_url = Field()
    dest_url = Field()
    dest_domain = Field()
    dest_title = Field()
    repin_count = Field()
    like_count = Field()


class PinterestSpider(Spider):
    name = "pinterest"
    allowed_domains = ["pinterest.com"]

    settings = {
        'DOWNLOAD_DELAY': 0.25,
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/38.0.2125.101 Safari/537.36',

        'ITEM_PIPELINES': {
            '__main__.OutfilePipeline': 500,
        },
    }

    DETAIL_URL = 'https://www.pinterest.com/pin/{}/'

    def __init__(self, start_url):
        self.start_url = start_url

    def start_requests(self):
        # Set initial request to passed-in URL
        yield Request(
            url = self.start_url,
            headers = {'X-Requested-With': 'XMLHttpRequest'})

    def parse(self, response):
        result = json.loads(response.body)

        # Handle first request differently
        if 'module' in result:
            result = result['module']['tree']['children'][1]
            pins = [p['data'] for p in result['children'][0]['children'] if p['name'] == 'Pin']
        else:
            pins = result['resource_response']['data']

        for pin in pins:
            yield Record(
                    title = pin['rich_summary']['display_name'] if pin['rich_summary'] else None,
                    description = pin['description'],
                    detail_url = self.DETAIL_URL.format(pin['id']),
                    image_url = pin['images']['orig']['url'],
                    dest_url = pin['link'],
                    dest_domain = pin['domain'],
                    dest_title = pin['title'],
                    repin_count = pin['repin_count'],
                    like_count = pin['like_count'])

        # GET NEXT PAGE
        return
        options = result['resource']['options']
        if options['bookmarks'][0] == '-end-':
            return
        
        # Get parameters for request
        if not hasattr(self, 'csrftoken'):
            csrfcookie = next(c for c in response.headers.getlist('Set-Cookie') if 'csrftoken' in c)
            self.csrftoken = re.search('csrftoken=(.+?);', csrfcookie).group(1)
        scheme = re.match('(.+?):', response.url).group(1)

        yield FormRequest(
            url = '{}://www.pinterest.com/resource/BoardFeedResource/get/'.format(scheme),
            dont_filter = True,
            headers = {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': self.csrftoken},
            formdata = {
                'source_url': options['board_url'],
                'data': '{{"options":{}}}'.format(json.dumps(options).replace(' ', ''))})


#
# SPIDER HANDLER
#

def run_spider(spider):
    """Setups item signal and run the spider"""
    # set up signal to catch items scraped
    from scrapy import log
    from scrapy import signals
    from scrapy.xlib.pydispatch import dispatcher

    def catch_exception(sender, failure, response, spider):
        print "Response: %s [%s]" % (response.body, response.meta)
        sys.stdout.flush()

    dispatcher.connect(catch_exception, signal=signals.spider_error)

    def catch_resp_dld(sender, response, request, spider):
        print "Downloaded (%s) Response %s" % (response.status, response.url)
        sys.stdout.flush()

    dispatcher.connect(catch_resp_dld, signal=signals.response_downloaded)

    # settings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from scrapy.conf import settings as default_settings

    default_settings.overrides.update({
        'LOG_ENABLED': False,
        'LOG_LEVEL': 'CRITICAL',
        'BOT_NAME': 'project',
    })
    # Update general settings with spider-specific ones
    for k,v in spider.settings.iteritems():
        if isinstance(v, dict) and k in default_settings.overrides:
            default_settings.overrides[k].update(v)
        else:
            default_settings.overrides[k] = v

    # set up crawler
    from twisted.internet import reactor
    from scrapy.crawler import Crawler

    crawler = Crawler(default_settings)
    crawler.signals.connect(reactor.stop, signal=signals.spider_closed)
    crawler.install()
    crawler.configure()

    # schedule spider
    crawler.crawl(spider)

    log.start_from_crawler(crawler)

    # start engine scrapy/twisted
    crawler.start()

    if not reactor.running:
        reactor.run()

    crawler.uninstall()


if __name__ == '__main__':
    run_spider(PinterestSpider(sys.argv[1]))
