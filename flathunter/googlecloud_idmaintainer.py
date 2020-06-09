import logging
import firebase_admin
import traceback
import datetime
from firebase_admin import credentials
from firebase_admin import firestore

from flathunter.config import Config

class GoogleCloudIdMaintainer:
    __log__ = logging.getLogger(__name__)

    def __init__(self):
        project_id = Config().get('google_cloud_project_id')
        if project_id is None:
            raise Exception("Need to project a google_cloud_project_id in config.yaml")
        firebase_admin.initialize_app(credentials.ApplicationDefault(), {
          'projectId': project_id
        })
        self.db = firestore.client()

    def mark_processed(self, expose_id):
        self.__log__.debug('mark_processed(' + str(expose_id) + ')')
        self.db.collection(u'processed').document(str(expose_id)).set({ u'id': expose_id })

    def is_processed(self, expose_id):
        self.__log__.debug('is_processed(' + str(expose_id) + ')')
        doc = self.db.collection(u'processed').document(str(expose_id))
        return doc.get().exists

    def save_expose(self, expose):
        record = expose.copy()
        record.update({ 'created_at': datetime.datetime.now(), 'created_sort': (0 - datetime.datetime.now().timestamp()) })
        self.db.collection(u'exposes').document(str(expose[u'id'])).set(record)

    def get_exposes_since(self, min_datetime):
        res = []
        for doc in self.db.collection(u'exposes').order_by('created_sort').stream():
            if doc.to_dict()[u'created_at'] < min_datetime:
                break
            res.append(doc.to_dict())
        return res

    def get_recent_exposes(self, count, filter=None):
        res = []
        for doc in self.db.collection(u'exposes').order_by('created_sort').stream():
            expose = doc.to_dict()
            if filter is None or filter.is_interesting_expose(expose):
                res.append(expose)
                if len(res) == count:
                    break
        return res

    def set_filters_for_user(self, user_id, filters):
        self.db.collection(u'users').document(str(user_id)).set({ 'filters' : filters })

    def get_filters_for_user(self, user_id):
        doc = self.db.collection(u'users').document(str(user_id)).get()
        settings = doc.to_dict()
        if settings is None:
            return None
        if 'filters' in settings:
            return settings['filters']
        return None

    def get_user_filters(self):
        res = []
        for doc in self.db.collection(u'users').stream():
            settings = doc.to_dict()
            if 'filters' in settings:
                res.append((int(doc.id), settings['filters']))
        return res

    def get_last_run_time(self):
        for doc in self.db.collection(u'executions').order_by(u'timestamp', direction=firestore.Query.DESCENDING).limit(1).stream():
            return doc.to_dict()[u'timestamp']

    def update_last_run_time(self):
        time = datetime.datetime.now()
        self.db.collection(u'executions').add({ u'timestamp': time })
        return time
