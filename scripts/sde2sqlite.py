# pylint: disable=E0401
import sys
import os
import shutil
import codecs
import yaml
import logbook

ROOT_PATH = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))

logbook.StreamHandler(sys.stdout).push_application()
logger = logbook.Logger(__name__)

LCID = dict(
    en='English',
    ja='Japanese',
    ru='Russian',
    de='German',
    fr='French',
    zh='Chinese'
)

CATEGORY_NAMES = [
    'Celestial',
    'Station',
    'Material',
    'Accessories',
    'Ship',
    'Module',
    'Charge',
    'Blueprint',
    'Entity',
    'Skill',
    'Commodity',
    'Drone',
    'Implant',
    'Deployable',
    'Starbase',
    'Asteroid',
    'Apparel',
    'Subsystem',
    'Ancient Relics',
    'Decryptors',
    'Infrastructure Upgrades',
    'Sovereignty Structures',
    'Planetary Interaction',
    'Planetary Resources',
    'Planetary Commodities',
    'Orbitals',
    'Special Edition Assets',
    'Structure',
    'Structure Module',
    'Fighter',
    'Infantry',
]

def load_yaml(path):
    logger.info('Load: ' + path)
    with codecs.open(path, 'r', 'utf-8') as file:
        data = yaml.load(file)

    return data

def clear_dir(dir_path):
    if not os.path.isdir(dir_path):
        os.mkdir(dir_path)

    for filename in os.listdir(dir_path):
        path = os.path.join(dir_path, filename)
        if os.path.isdir(path):
            shutil.rmtree(path)
        elif os.path.isfile(path):
            os.remove(path)

def main():
    sys.path.append(ROOT_PATH)
    import db
    from db import Information, Category, Group, Type

    os.chdir(os.path.dirname(__file__))

    clear_dir('locales')

    sessions = {}
    for lcid, name in LCID.items():
        sessions[lcid] = db.create_session(os.path.join('locales', lcid + '.db'))

    categories_yaml = load_yaml(os.path.join('sde', 'fsd', 'categoryIDs.yaml'))
    groups_yaml = load_yaml(os.path.join('sde', 'fsd', 'groupIDs.yaml'))
    types_yaml = load_yaml(os.path.join('sde', 'fsd', 'typeIDs.yaml'))

    category_ids = []
    group_ids = []

    def id_(key):
        try:
            value = items[key]
        except KeyError:
            value = 0
        return value

    def locale(key):
        try:
            value = items[key][lcid]
        except KeyError:
            value = ''
        return value.strip()

    for i, items in categories_yaml.items():
        name = items['name']['en']

        if name not in CATEGORY_NAMES:
            continue

        category_ids.append(i)

        for lcid, session in sessions.items():
            session.add(Category(id=i, name=locale('name')))

    for i, items in groups_yaml.items():
        category_id = id_('categoryID')
        if category_id not in category_ids:
            continue

        group_ids.append(i)

        for lcid, session in sessions.items():
            session.add(Group(id=i, categoryID=category_id, name=locale('name')))

    for i, items in types_yaml.items():
        group_id = id_('groupID')
        if group_id not in group_ids:
            continue

        for lcid, session in sessions.items():
            session.add(Type(
                id=i,
                groupID=group_id,
                name=locale('name'),
                description=locale('description')
            ))

    for lcid, session in sessions.items():
        session.add(Information(lcid=lcid, name=LCID[lcid]))
        session.commit()

if __name__ == '__main__':
    main()
