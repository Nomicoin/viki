import png, array, os
import PIL.Image, PIL.ExifTags
import markdown, pygit2
import genxid
from io import BytesIO
from markdown.extensions.wikilinks import WikiLinkExtension

class Asset(object):
    def __init__(self, blob, metadata):
        self.blob = blob
        self.metadata = metadata
        self.name = metadata['asset']['name']
        self.xlink = metadata['base']['xlink']
        self.contentType = ''
        self.title = ''

    def isValid(self):
        return False

    def checkExtension(self, extensions):
        ext = self.metadata['asset']['ext']
        return ext in extensions

    def addMetadata(self):
        self.metadata['asset']['content-type'] = self.contentType
        self.metadata['asset']['title'] = self.title

class Text(Asset):
    def __init__(self, blob, metadata):
        super(Text, self).__init__(blob, metadata)

    def isValid(self):
        return not self.blob.is_binary

    def addMetadata(self):
        lines = self.blob.data.count('\n')
        self.metadata['text'] = { 'lines': lines }

        self.contentType = "text/plain"
        super(Text, self).addMetadata()


class Markdown(Text):
    def __init__(self, blob, metadata):
        super(Text, self).__init__(blob, metadata)

    def isValid(self):
        return self.checkExtension(['.md']) and super(Markdown, self).isValid()

    def addMetadata(self):
        html = markdown.markdown(self.blob.data, 
                                 extensions=[WikiLinkExtension(base_url='/wiki/', end_url='.html')])
        self.metadata['markdown'] = { 'asHtml': self.xlink }
        self.metadata['as'] = { 'html': html }

        title = os.path.basename(self.name)
        title = os.path.splitext(title)[0]
        self.title = title.replace("-", " ")

        super(Markdown, self).addMetadata()


class Image(Asset):
    def __init__(self, blob, metadata):
        super(Image, self).__init__(blob, metadata)
        self.format = ''
        self.width = 0
        self.height = 0
        self.colorDepth = 0

    def isValid(self):
        return self.blob.is_binary

    def addMetadata(self):
        self.metadata['image'] = { 
            'width': self.width,
            'height': self.height,
            'colorDepth': self.colorDepth,
            'format': self.format
        }
        self.contentType = self.format
        super(Image, self).addMetadata()

class Png(Image):
    def __init__(self, blob, metadata):
        super(Png, self).__init__(blob, metadata)
        self.format = "image/png"

    def isValid(self):
        return self.checkExtension(['.png']) and super(Png, self).isValid()

    def addMetadata(self):
        try:
            data = array.array('B', self.blob.data)
            r = png.Reader(data)
            self.width, self.height, pixels, meta = r.read()
            self.metadata['png'] = meta
            super(Png, self).addMetadata()
        except:
            print "error reading png", self.name

class Jpeg(Image):
    def __init__(self, blob, metadata):
        super(Jpeg, self).__init__(blob, metadata)
        self.format = "image/jpeg"

    def isValid(self):
        return self.checkExtension(['.jpg', '.jpeg']) and super(Jpeg, self).isValid()

    def addMetadata(self):
        try:
            bio = BytesIO(self.blob.data)
            print bio
            bio.seek(0)
            img = PIL.Image.open(bio)
            exif = {
                PIL.ExifTags.TAGS[k]: v
                for k, v in img._getexif().items()
                if k in PIL.ExifTags.TAGS
            }
            self.metadata['jpeg'] = exif
            self.width = exif['ExifImageWidth']
            self.height = exif['ExifImageHeight']
            super(Jpeg, self).addMetadata()
        except:
            print "error reading jpeg", self.name

class Gif(Image):
    def __init__(self, blob, metadata):
        super(Gif, self).__init__(blob, metadata)
        self.format = "image/gif"

    def isValid(self):
        return self.checkExtension(['.gif']) and super(Gif, self).isValid()

    def addMetadata(self):
        self.metadata['gif'] = {}
        super(Gif, self).addMetadata()

allTypes = [
    lambda blob, meta: Text(blob, meta),
    lambda blob, meta: Markdown(blob, meta),
    lambda blob, meta: Png(blob, meta),
    lambda blob, meta: Jpeg(blob, meta),
    lambda blob, meta: Gif(blob, meta),
]
