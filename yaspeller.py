# -*- coding: utf-8 -*-
from threading import Thread, Lock
import urllib
import json
from StringIO import StringIO

import sublime, sublime_plugin

IGNORE_UPPERCASE = 1
IGNORE_DIGITS = 2
IGNORE_URLS = 4
FIND_REPEAT_WORDS = 8
IGNORE_LATIN = 16
NO_SUGGEST = 32
FLAG_LATIN = 128
BY_WORDS = 256
IGNORE_CAPITALIZATION = 512

SERVICE_URL = "http://speller.yandex.net/services/spellservice.json/checkText"
SERVICE_SYMBOLS_LIMIT = 10000 - 50 # minus length of other params of query (approximately)

class YaspellerCommand(sublime_plugin.TextCommand):
    regions = []
    regions_lock = Lock()

    def check_text(self, start, end, text):
        params = urllib.urlencode({
            'text': text.encode('utf-8'),
            'lang': 'ru',
            'options': IGNORE_LATIN | NO_SUGGEST

        })

        try:
            data = urllib.urlopen(SERVICE_URL, params)
            code = data.getcode()

            if code == 413:
                sublime.status_message("Text is too large.")
                return

            response = StringIO(data.read())
            blocks = json.load(response)
            regions = []
            for block in blocks:
                regions.append(
                    sublime.Region(start + block['pos'],
                                   start + block['pos'] + block['len'])
                )
            with self.regions_lock:
                self.regions.extend(regions)

        except IOError:
            sublime.status_message("There are some problems with connecting to service")

    def run(self, edit):
        regions = self.view.get_regions('yaspeller')

        if regions:
            return self.view.erase_regions('yaspeller')

        bufferSize = self.view.size()
        threads = []

        for buffer_start in xrange(0, bufferSize, SERVICE_SYMBOLS_LIMIT):
            if bufferSize < buffer_start + SERVICE_SYMBOLS_LIMIT:
                buffer_end = buffer_start + (bufferSize % SERVICE_SYMBOLS_LIMIT)
            else:
                buffer_end = buffer_start + SERVICE_SYMBOLS_LIMIT

            bufferRegion = sublime.Region(buffer_start, buffer_end)
            bufferText = self.view.substr(bufferRegion)

            thread = Thread(target=self.check_text, args=(buffer_start, buffer_end, bufferText))
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join(1)

        self.view.add_regions('yaspeller', self.regions, 'string')




