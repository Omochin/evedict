import threading
import time
import re
import pyperclip

class ClipboardThread(threading.Thread):
    def __init__(self, config, event):
        self.text = pyperclip.paste()
        self.config = config
        self.event = event
        threading.Thread.__init__(self)

    def update(self, text):
        pyperclip.copy(text)
        self.text = text

    def observe(self):
        try:
            text = pyperclip.paste()
        except:
            pass

        if not self.text == text and text:
            self.text = text

            match = re.search(r'<url=showinfo:(\d*)', self.text)
            if match:
                search_word = match.group(1)
            else:
                words = re.split(r'[<>{}\[\]]', self.text)
                search_word = [w.strip() for w in words if w.strip()][-1]

            url = '/%s/type/%s' % (self.config.lcid, search_word)
            self.event(url)

    def run(self):
        while True:
            if self.config.link_clipboard:
                self.observe()

            time.sleep(0.1)
