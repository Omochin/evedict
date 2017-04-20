import sys
import os
import re
import collections
import logbook
import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.autoreload
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from clipboard_thread import ClipboardThread
from config import Config
import db
from db import Information, Category, Group, Type

def find_data_file(filename):
    if getattr(sys, 'frozen', False):
        datadir = os.path.dirname(sys.executable)
    else:
        datadir = os.path.dirname(__file__)

    return os.path.join(datadir, filename)

sessions = {}

logbook.StreamHandler(sys.stdout).push_application()
logger = logbook.Logger(__name__)

config = Config(find_data_file('config.yaml'))
config.locales = collections.OrderedDict()
config.host_address = ''

clipboard_thread = ClipboardThread(config, lambda url: UpdateHander.send_updates({'url': url}))

# Error Messages
def multiple_results_found(text):
    return '"%s" has too many results(over %d)' % (text, config.search_limit)

def no_result_found(text):
    return '"%s" is not found' % text

def uri_too_long():
    return 'Search word is too long'

class BaseHandler(tornado.web.RequestHandler):
    error_message = ''
    search_word = ''

    def write_error(self, status_code, exc_info=None, **kwargs):
        if not self.error_message:
            self.error_message = str(status_code)

        kwargs_ = {
            'title': str(status_code),
            'message': self.error_message,
            'search_word': self.search_word,
        }

        self.render('template.html', kwargs=update_template_kwargs(kwargs_))

    def update_valid_lcid(self, lcid):
        if lcid in config.locales:
            config.lcid = lcid
        else:
            config.lcid = config.default_lcid
            self.error_message = '"%s" Language is not supported' % lcid
            raise tornado.web.HTTPError(404)

    def render_template(self, template, kwargs):
        kwargs['template'] = template

        if 'path' not in kwargs:
            kwargs['path'] = self.request.path

        self.render('template.html', kwargs=update_template_kwargs(kwargs))

class DefaultHandler(BaseHandler):
    def prepare(self):
        raise tornado.web.HTTPError(404)

class QRCodeHandler(BaseHandler):
    def get(self):
        kwargs = {
            'host_address': config.host_address,
            'path': '/%s/home' % config.lcid,
        }
        self.render_template('qr_code.html', kwargs)

class PreferencesHandler(BaseHandler):
    OPTION_NAMES = ['link_clipboard', 'paste_result', 'launch_web_browser']

    def options(self):
        options = []
        texts = [
            'Link clipboard for search',
            'Paste a result into the clipboard',
            'Launch web browser at startup',
        ]

        for index, name in enumerate(self.OPTION_NAMES):
            options.append({
                'name': name,
                'text': texts[index],
                'checked': config.yaml[name],
            })

        return {'options': options}

    def get(self, lcid):
        self.update_valid_lcid(lcid)
        self.render_template('preferences.html', self.options())

    def post(self, lcid):
        self.update_valid_lcid(lcid)

        for name in self.OPTION_NAMES:
            config.save(name, self.get_argument(name, False) == 'on')

        if self.get_argument('default_lcid') in config.locales:
            config.default_lcid = self.get_argument('default_lcid')

        url = '/%s/home' % config.lcid
        UpdateHander.send_updates({'url': url})

class HomeHandler(BaseHandler):
    def get(self, lcid):
        self.update_valid_lcid(lcid)

        categories = sessions[config.default_lcid].query(Category)
        items = create_list_items(Category, categories, '/category/')
        kwargs = {
            'name': 'Evedict',
            'items': items,
        }
        self.render_template('list.html', kwargs)

class CategoryHandler(BaseHandler):
    def get(self, lcid, search_id):
        self.update_valid_lcid(lcid)

        parent = {'text': 'Home', 'link': '/home'}

        try:
            category = sessions[config.default_lcid].query(Category) \
                        .filter_by(id=search_id).one()
            name = category.name
            groups = category.groups
            items = create_list_items(Group, groups, '/group/')

            if config.lcid != config.default_lcid:
                try:
                    locale_name = sessions[config.lcid] \
                                    .query(Category) \
                                    .filter_by(id=category.id).one().name

                    name = '%s(%s)' % (category.name, locale_name)
                except:
                    pass
        except NoResultFound:
            self.error_message = 'Category ID %s is not found' % search_id
            raise tornado.web.HTTPError(404)

        kwargs = {
            'title': name,
            'name': name,
            'items': items,
            'id_text': 'Category ID is %d' % category.id,
            'parent': parent,
        }
        self.render_template('list.html', kwargs)

class GroupHandler(BaseHandler):
    def get(self, lcid, search_id):
        self.update_valid_lcid(lcid)

        parent = {}

        try:
            group = sessions[config.default_lcid].query(Group).filter_by(id=search_id).one()
            name = group.name
            types = group.types
            items = create_list_items(Type, types, '/type/')
            parent['link'] = '/category/%d' % group.category.id
            parent['text'] = group.category.name

            if config.lcid != config.default_lcid:
                try:
                    locale_group = sessions[config.lcid] \
                                    .query(Group) \
                                    .filter_by(id=group.id).one()

                    name = '%s(%s)' % (group.name, locale_group.name)
                    parent['text'] = '%s(%s)' % (group.category.name, locale_group.category.name)
                except:
                    pass
        except NoResultFound:
            self.error_message = 'Group ID %s is not found' % search_id
            raise tornado.web.HTTPError(404)

        kwargs = {
            'title': name,
            'name': name,
            'items': items,
            'id_text': 'Group ID is %d' % group.id,
            'parent': parent,
        }
        self.render_template('list.html', kwargs)

class TypeHandler(BaseHandler):
    def get(self, lcid, search_word):
        self.update_valid_lcid(lcid)

        if len(search_word) > config.uri_len_limit:
            self.error_message = uri_too_long()
            raise tornado.web.HTTPError(414)

        try:
            results = render_type(search_word)

            kwargs = {
                'title': results['name'],
                'search_word': results['search_word'],
                'content': results['content'],
                'path': self.request.path,
            }

            if 'footer' in results:
                kwargs['footer'] = results['footer']

            self.render('template.html', kwargs=update_template_kwargs(kwargs))

        except MultipleResultsFound:
            self.error_message = multiple_results_found(search_word)
            self.search_word = search_word
            raise tornado.web.HTTPError(400)
        except NoResultFound:
            self.error_message = no_result_found(search_word)
            self.search_word = search_word
            raise tornado.web.HTTPError(404)

class UpdateHander(tornado.websocket.WebSocketHandler):
    waiters = set()

    def open(self):
        UpdateHander.waiters.add(self)

    def on_close(self):
        UpdateHander.waiters.remove(self)

    def on_message(self, message):
        parsed = tornado.escape.json_decode(message)
        UpdateHander.send_updates(parsed)

    @classmethod
    def send_updates(cls, kwargs):
        for waiter in cls.waiters:
            try:
                waiter.write_message(kwargs)
            except:
                logger.error('Error sending message')


def update_template_kwargs(base_kwargs):
    kwargs = {
        'lcid': config.lcid,
        'default_lcid': config.default_lcid,
        'locales': config.locales,
        'link_to': link_to,
    }

    try:
        match = re.match(r'^/../(.*)', base_kwargs['path'])
        if match:
            base_kwargs['path'] = match.group(1)
    except:
        base_kwargs['path'] = 'home'

    dicts = [base_kwargs, kwargs]
    return {k: v for dic in dicts for k, v in dic.items()}

def create_list_items(table_class, rows, path):
    items = []

    for row in rows:
        item = {}
        item['link'] = '%s%d' % (path, row.id)
        item['name'] = row.name

        if config.lcid != config.default_lcid:
            try:
                item['locale'] = sessions[config.lcid].query(table_class) \
                                                        .filter_by(id=row.id).one().name
            except NoResultFound:
                item['locale'] = row.name

        items.append(item)

    return items

def render_type(search_word):
    results = {'search_word': ''}
    lorder = tornado.template.Loader(find_data_file('templates'))

    def replace(html):
        html = re.sub(
            r'<a href=showinfo:(\d*)>(.*)</a>',
            lambda m: link_to(m.group(2), '/type/' + m.group(1)),
            html
        )
        html = re.sub(r'<font color=".*">', '<font color="orange">', html)
        return html

    def update_results2description(found_lcid, found_type):
        if found_lcid != config.default_lcid:
            type_ = sessions[config.default_lcid].query(Type).filter_by(id=found_type.id).one()
        else:
            type_ = found_type

        name = type_.name
        content_kwargs = {
            'name': type_.name,
            'description': replace(type_.description),
            'locale_name': '',
            'locale_description': '',
            'lcid': config.lcid,
            'default_lcid': config.default_lcid,
        }
        footer_kwargs = {}
        parent = {
            'link': '/group/%d' % type_.group.id,
            'text': type_.group.name,
        }

        if config.lcid != config.default_lcid:
            try:
                locale_type = sessions[config.lcid].query(Type).filter_by(id=type_.id).one()
                name = '%s(%s)' % (locale_type.name, type_.name)
                content_kwargs['locale_name'] = locale_type.name
                content_kwargs['locale_description'] = replace(locale_type.description)
                parent['text'] = '%s(%s)' % (type_.group.name, locale_type.group.name)
            except:
                pass

        content_kwargs['parent'] = parent
        footer_kwargs['parent'] = parent
        footer_kwargs['id_text'] = 'Type ID is %d' % type_.id

        try:
            if 'en' in config.locales:
                if found_lcid == 'en':
                    en_type = found_type
                elif config.default_lcid == 'en':
                    en_type = type_
                else:
                    en_type = sessions['en'].query(Type).filter_by(id=type_.id).one()

                content_kwargs['uniwiki'] = en_type.name
        except:
            pass

        image_path = ['static', 'images', 'types', '%d.png' % type_.id]
        if os.path.isfile(find_data_file(os.path.join(*image_path))):
            content_kwargs['image'] = '/' + '/'.join(image_path)

        results['name'] = name
        results['search_word'] = type_.name
        content_html = lorder.load('description.html').generate(
            kwargs=update_template_kwargs(content_kwargs)
        )
        footer_html = lorder.load('footer.html').generate(
            kwargs=update_template_kwargs(footer_kwargs)
        )
        results['content'] = tornado.escape.to_basestring(content_html)
        results['footer'] = tornado.escape.to_basestring(footer_html)

        if config.paste_result:
            clipboard_thread.update(type_.name)

        return results

    def search(lcid):
        try:
            query = sessions[lcid].query(Type)
            if search_word.isdigit():
                types = query.filter_by(id=search_word)
            else:
                types = query.filter(Type.name.contains(search_word))

            update_results2description(lcid, types.one())
        except MultipleResultsFound:
            if types.count() > config.search_limit:
                raise MultipleResultsFound()
            else:
                html = ''
                groups = collections.OrderedDict()

                list_lorder = lorder.load('list.html')

                for type_ in types.all():
                    group = type_.group

                    if group not in groups:
                        groups[group] = []

                    if lcid == config.default_lcid:
                        groups[group].append(type_)
                    else:
                        default_type = sessions[config.default_lcid].query(Type) \
                                        .filter_by(id=type_.id).one()
                        groups[group].append(default_type)

                for group, types_ in groups.items():
                    name = group.name
                    try:
                        locale_group = sessions[config.lcid].query(Group) \
                                        .filter_by(id=group.id).one()
                        name = '%s(%s)' % (locale_group.name, group.name)
                    except:
                        pass

                    kwargs = {
                        'name': name,
                        'items': create_list_items(Type, types_, '/type/'),
                    }

                    html += tornado.escape.to_basestring(
                        list_lorder.generate(kwargs=update_template_kwargs(kwargs))
                    )
                    html += '<hr />'

                results['content'] = html
                results['name'] = search_word
                results['search_word'] = search_word
        except NoResultFound:
            return False

        return True

    search_lcids = [config.default_lcid, config.lcid]

    if 'en' in config.locales:
        search_lcids.insert(0, 'en')

    for search_lcid in sorted(set(search_lcids), key=search_lcids.index):
        if search(search_lcid):
            return results

    raise NoResultFound()

def link_to(text, url, **kwargs):
    if 'align_language' not in kwargs:
        kwargs['align_language'] = True

    if kwargs['align_language']:
        url = "/%s%s" % (config.lcid, url)

    del kwargs['align_language']
    onclick = "updater.link_to('%s')" % url

    if 'class_' in kwargs:
        kwargs['class'] = kwargs['class_']
        del kwargs['class_']

    attribute_text = ''
    for elem, value in kwargs.items():
        if elem == 'icon':
            text = "<img src=%s>&nbsp;%s" % (value, text)
            continue
        attribute_text += '%s="%s" ' % (elem, value)

    return '<a href="%s" onclick="%s" %s>%s</a>' %  (url, onclick, attribute_text, text)

def main():
    Config.default_lcid = Config.register('default_lcid')
    Config.lcid = Config.register('lcid')
    Config.search_limit = Config.register('search_limit')
    Config.uri_len_limit = Config.register('uri_len_limit')
    Config.host_port = Config.register('host_port')
    Config.link_clipboard = Config.register('link_clipboard')
    Config.paste_result = Config.register('paste_result')
    Config.launch_web_browser = Config.register('launch_web_browser')

    locales_path = os.path.join(find_data_file('locales'))

    any_lcid = ''
    for filename in os.listdir(locales_path):
        filepath = os.path.join(locales_path, filename)
        if not os.path.isfile(filepath):
            continue

        ext = os.path.splitext(filepath)[-1].lower()
        if ext == '.db':
            try:
                session = db.create_session(filepath, check_same_thread=False)
                information = session.query(Information).one()
                config.locales[information.lcid] = information.name
                sessions[information.lcid] = session
                any_lcid = information.lcid
            except:
                pass

    if config.lcid not in config.locales:
        config.lcid = any_lcid

    if config.default_lcid not in config.locales:
        config.default_lcid = any_lcid

    clipboard_thread.setDaemon(True)
    clipboard_thread.start()

    handlers = [
        (r'/update', UpdateHander),
        (r'/', QRCodeHandler),
        (r'/(..)/home', HomeHandler),
        (r'/(..)/preferences', PreferencesHandler),
        (r'/(..)/category/(.*)', CategoryHandler),
        (r'/(..)/group/(.*)', GroupHandler),
        (r'/(..)/type/(.*)', TypeHandler),
    ]

    setting = {
        'template_path': find_data_file('templates'),
        'static_path': find_data_file('static'),
        'default_handler_class': DefaultHandler,
        'debug': True,
    }

    host_name = '127.0.0.1'
    tornado.web.Application(handlers, **setting).listen(config.host_port)

    logger.info('Server is up.')

    import webbrowser
    import netifaces
    import qrcode
    import IPy

    loopback_addresses = IPy.IP('127.0.0.0/8')
    for iface_name in netifaces.interfaces():
        iface_data = netifaces.ifaddresses(iface_name)
        data = iface_data.get(netifaces.AF_INET)

        if data:
            ip_ = IPy.IP(data[0]['addr'])
            if ip_.iptype() == 'PRIVATE' and ip_ not in loopback_addresses:
                host_name = ip_
                break

    config.host_address = "http://%s:%d" % (host_name, config.host_port)
    qrcode_image = qrcode.make(config.host_address)
    qrcode_image.save(os.path.join('static', 'images', 'qr_code.png'))

    if config.launch_web_browser:
        webbrowser.open(config.host_address)

    tornado.ioloop.IOLoop.instance().start()

if __name__ == '__main__':
    main()
