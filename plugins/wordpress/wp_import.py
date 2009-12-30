###Import post,page,category,tag from wordpress export file
import xml.etree.ElementTree as et
import logging
###import from wxr file
class import_wordpress:
    def __init__(self,source):
        self.categories=[]
        self.tags=[]
        self.entries=[]

        self.source=source
        self.doc=et.fromstring(source)
        #use namespace
        self.wpns='{http://wordpress.org/export/1.0/}'

        self.contentns="{http://purl.org/rss/1.0/modules/content/}"
        self.excerptns="{http://wordpress.org/export/1.0/excerpt/}"
        et._namespace_map[self.wpns]='wp'
        et._namespace_map[self.contentns]='content'
        et._namespace_map[self.excerptns]='excerpt'
        self.channel=self.doc.find('channel')
        self.dict={'category':self.wpns+'category','tag':self.wpns+'tag','item':'item'}
        self.cur_do=None

    def parse(self):
        categories=self.channel.findall(self.wpns+'category')
        #parse categories

        for cate in categories:
            slug=cate.findtext(self.wpns+'category_nicename')
            name=cate.findtext(self.wpns+'cat_name')
            self.categories.append({'slug':slug,'name':name})
        #parse tags
        tags=self.channel.findall(self.wpns+'tag')

        for tag in tags:
            slug=tag.findtext(self.wpns+'tag_slug')
            name=tag.findtext(self.wpns+'tag_name')
            self.tags.append({'slug':slug,'name':name})

        #parse entries
        items=self.channel.findall('item')

        for item in items:
            title=item.findtext('title')
            try:
                entry={}
                entry['title']=item.findtext('title')
                logging.info(title)
                entry['pubDate']=item.findtext('pubDate')
                entry['post_type']=item.findtext(self.wpns+'post_type')
                entry['content']= item.findtext(self.contentns+'encoded')
                entry['excerpt']= item.findtext(self.excerptns+'encoded')
                entry['post_id']=int(item.findtext(self.wpns+'post_id'))
                entry['post_name']=item.findtext(self.wpns+'post_name')
                entry['post_parent']=int(item.findtext(self.wpns+'post_parent'))
                entry['menu_order']=int(item.findtext(self.wpns+'menu_order'))

                entry['tags']=[]
                entry['categories']=[]

                cats=item.findall('category')

                for cat in cats:
                    if cat.attrib.has_key('nicename'):
                        nicename=cat.attrib['nicename']
                        cat_type=cat.attrib['domain']
                        if cat_type=='tag':
                            entry['tags'].append(cat.text)
                        else:
                            entry['categories'].append({'slug':nicename,'name':cat.text})

                pub_status=item.findtext(self.wpns+'status')
                if pub_status=='publish':
                    entry['published']=True
                else:
                    entry['published']=False

                entry['comments']=[]

                comments=item.findall(self.wpns+'comment')

                for com in comments:
                    try:
                        comment_approved=int(com.findtext(self.wpns+'comment_approved'))
                    except:
                        comment_approved=0
                    if comment_approved:
                        comment=dict(author=com.findtext(self.wpns+'comment_author'),
                                        content=com.findtext(self.wpns+'comment_content'),
                                        email=com.findtext(self.wpns+'comment_author_email'),
                                        weburl=com.findtext(self.wpns+'comment_author_url'),
                                        date=com.findtext(self.wpns+'comment_date')
                                        )
                self.entries.append(entry)
            except:
                logging.info("parse wordpress file error")
        self.total=self.count()
        self.cur_do=("begin","begin")

    def count(self):
        return len(self.categories)+len(self.entries)

    def pop(self):
        if len(self.categories)>0:
            self.cur_do=('cat',self.categories.pop())
            return self.cur_do

        if len(self.entries)>0:
            self.cur_do=('entry', self.entries.pop())
            return self.cur_do
        return None



