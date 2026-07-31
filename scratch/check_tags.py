from html.parser import HTMLParser

class MyHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.depths = {}
        
    def handle_starttag(self, tag, attrs):
        if tag == "div":
            attrs_dict = dict(attrs)
            div_id = attrs_dict.get('id') or attrs_dict.get('class') or 'div'
            self.tags.append(div_id)
            self.depths[div_id] = len(self.tags)
            if 'videoWrap' in div_id:
                print(f"videoWrap is at depth {len(self.tags)}, inside {self.tags[:-1]}")

    def handle_endtag(self, tag):
        if tag == "div":
            if self.tags:
                self.tags.pop()

parser = MyHTMLParser()
with open("templates/index.html", "r", encoding="utf-8") as f:
    parser.feed(f.read())
