# pylint: disable=E0401
import sys
import os
import time
import requests
import logbook

ROOT_PATH = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
TYPES_PATH = os.path.join('images', 'types')

logbook.StreamHandler(sys.stdout).push_application()
logger = logbook.Logger(__name__)

def main():
    sys.path.append(ROOT_PATH)
    import db
    from db import Category

    os.chdir(os.path.dirname(__file__))

    if not os.path.isdir(TYPES_PATH):
        os.makedirs(TYPES_PATH)

    session = db.create_session(os.path.join(ROOT_PATH, 'locales', 'en.db'))
    category = session.query(Category).filter_by(name='Ship').one()

    for group in category.groups:
        for type_ in group.types:
            ext = '.png'
            image_path = os.path.join(TYPES_PATH, '%d%s' % (type_.id, ext))

            if os.path.isfile(image_path):
                logger.info('PASS - %d' % type_.id)
                continue

            image_url = 'https://image.eveonline.com/Render/%d_512%s' % (type_.id, ext)
            response = requests.get(image_url, allow_redirects=False, timeout=10)

            if response.status_code != 200:
                logger.error('ERROR - status code %d: %d' % (response.status_code, type_.id))
                continue

            content_type = response.headers["content-type"]
            if 'image' not in content_type:
                logger.error('ERROR - Content-Type: ' + content_type)
                continue

            with open(image_path, 'wb') as fout:
                logger.info('SUCCESS - %d' % type_.id)
                fout.write(response.content)

            time.sleep(10)

if __name__ == '__main__':
    main()
