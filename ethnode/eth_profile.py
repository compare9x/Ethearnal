import os
import random
import string
import config
import io
import json
import cherrypy

from toolkit import tools
from toolkit import basemodel
from toolkit.store import CrudJsonStore

from randomavatar.randomavatar import Avatar


class EthearnalProfileModel(basemodel.BaseModel):
    SPEC_PREFIX = 'spe'
    dict_cls = dict
    list_cls = list
    none_cls = basemodel.none_cls

    FIELDS_SPEC = {
        'first': ('text', 'UTF-8', basemodel.blank_st_cls),
        'last': ('text', 'UTF-8', basemodel.blank_st_cls),
        'title': ('text', 'UTF-8', basemodel.blank_st_cls),
        'nick': ('text', 'UTF-8', basemodel.blank_st_cls),
        'skills': ('list', 'text', basemodel.empty_ls_cls),
    }

    first = ''
    last = ''
    title = ''
    nick = ''
    skills = []

    def __init__(self):
        super(EthearnalProfileModel, self).__init__()


class EthearnalProfileController(object):
    '''
    Carry about profile stuff
    '''
    PERSONAL_DIRECTORY_NAME = 'personal'
    PROFILE_JSON_FILE_NAME = 'profile.json'
    PROFILE_HTML_FILE_NAME = 'profile.html'
    PROFILE_IMAGE_FILE_NAME = 'profile_img.png'
    JOB_POSTS_JSON_FILE_NAME = 'job_posts.json'

    def __init__(self, data_dir=config.data_dir, personal_dir=None):
        self.data_dir = os.path.abspath(data_dir)
        if personal_dir:
            self.personal_dir = os.path.abspath(personal_dir)
        else:
            self.personal_dir = os.path.abspath('%s/%s' % (self.data_dir, self.PERSONAL_DIRECTORY_NAME))
            tools.mkdir(self.personal_dir)

        self.profile_json_file_name = '%s/%s' % (self.personal_dir, self.PROFILE_JSON_FILE_NAME)
        self.profile_html_file_name = '%s/%s' % (self.personal_dir, self.PROFILE_HTML_FILE_NAME)
        self.profile_image_file_name = '%s/%s' % (self.personal_dir, self.PROFILE_IMAGE_FILE_NAME)
        self.job_post_json_store_fn = '%s/%s' % (self.personal_dir, self.JOB_POSTS_JSON_FILE_NAME)

        self.model = EthearnalProfileModel()

        # create empty profile if not found
        if not os.path.isfile(self.profile_json_file_name):
            self.model.to_json_file(self.profile_json_file_name)
        else:
            self.model.from_json_file(self.profile_json_file_name)

        # create empty profile html if not found
        if not os.path.isfile(self.profile_html_file_name):
            # todo
            pass
        else:
            # todo
            pass

        # create generated avatar if not found
        if not os.path.isfile(self.profile_image_file_name):
            self.generate_random_avatar(filename=self.profile_image_file_name)

    def get_profile_image_bytes(self):
        bts = None
        with open(self.profile_image_file_name, 'rb') as fs:
            bts = fs.read()
        return bts

    @staticmethod
    def generate_random_avatar(filename=None, n=10):
        if not filename:
            raise ValueError('Please set a file path where to save generated avatar')
        st = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(n))
        avatar = Avatar(rows=13, columns=13)
        image_byte_array = avatar.get_image(string=st,
                                            width=89,
                                            height=89,
                                            pad=10)

        return avatar.save(image_byte_array=image_byte_array,
                           save_location=filename)
    @property
    def data(self):
        return self.model.from_json_file(self.profile_json_file_name).to_json()


class EthearnalProfileView(object):
    exposed = True

    def __init__(self, eth_profile):
        self.profile = eth_profile
        self.query_dispatch = {
            'avatar': self.avatar,
            'data': self.data,
            'html': self.html,
            'guid': self.guid,
        }

    def GET(self, q):
        # todo fix this keep profile in object
        if q in self.query_dispatch:
            return self.query_dispatch[q]()
        else:
            return 'todo: 404'

    def avatar(self):
        cherrypy.response.headers['Content-Type'] = "image/png"
        fs = io.BytesIO(self.profile.get_profile_image_bytes())
        fs.seek(0)
        return cherrypy.lib.file_generator(fs)

    def data(self):
        return self.profile.data

    def html(self):
        if not os.path.isfile(self.profile.profile_html_file_name):
            return ""  # todo 404

        bts = None
        with open(self.profile.profile_html_file_name, 'rb') as fp:
            fs = io.BytesIO(fp.read())
            fs.seek(0)
        return cherrypy.lib.file_generator(fs)

    def guid(self):
        import hashlib
        return hashlib.sha256(self.profile.data.encode('utf-8')).hexdigest()


class EthearnalJobPostModel(basemodel.BaseModel):
    SPEC_PREFIX = 'spe'
    dict_cls = dict
    list_cls = list
    none_cls = basemodel.none_cls

    FIELDS_SPEC = {
        'title': ('text', 'UTF-8', basemodel.blank_st_cls),
        'description': ('text', 'UTF-8', basemodel.blank_st_cls),
    }

    title = ''
    description = ''

    def __init__(self, title=None, description=None):
        super(EthearnalJobPostModel, self).__init__()
        if not title or not description:
            raise ValueError('Title and/or description are required to post a job')
        self.title = title
        self.description = description

    def __hash__(self):
        st = '%s%s' % (self.title, self.description)
        return hash(st)


class EthearnalJobPostController(object):

    def __init__(self, eth_profile: EthearnalProfileController):
        self.profile = eth_profile
        self.crud = CrudJsonStore(self.profile.job_post_json_store_fn)


class EthearnalJobView(object):
    exposed = True
    # todo fix content type json

    def __init__(self, ctl: EthearnalJobPostController):
        self.ctl = ctl

    def POST(self, title=None, description=None):
        o = EthearnalJobPostModel(title, description)
        status = self.ctl.crud.create(o.to_dict(), o.title)
        if status == 201:
            self.ctl.crud.dump()
        cherrypy.response.status = status
        return ''

    def GET(self):
        js = self.ctl.crud.load()
        cherrypy.response.headers['Content-Type'] = 'application/json'
        return js

        



