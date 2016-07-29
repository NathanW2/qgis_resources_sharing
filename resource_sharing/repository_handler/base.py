# coding=utf-8
"""This module contains the base class of repository handler."""

__author__ = 'akbargumbira@gmail.com'
__revision__ = '$Format:%H$'
__date__ = '15/03/15'


import codecs
from ConfigParser import SafeConfigParser
import urlparse

from PyQt4.QtCore import QTemporaryFile

from resource_sharing.config import COLLECTION_NOT_INSTALLED_STATUS
from resource_sharing.exception import MetadataError


class RepositoryHandlerMeta(type):
    """Handler meta class definition."""
    def __init__(cls, name, bases, dct):
        if not hasattr(cls, 'registry'):
            # This is the base class.  Create an empty registry
            cls.registry = {}
        else:
            # This is a derived class.
            # Add the class if it's not disabled
            if not cls.IS_DISABLED:
                interface_id = name.lower()
                cls.registry[interface_id] = cls

        super(RepositoryHandlerMeta, cls).__init__(name, bases, dct)


class BaseRepositoryHandler(object):
    """Abstract class of handler."""
    __metaclass__ = RepositoryHandlerMeta

    METADATA_FILE = 'metadata.ini'
    IS_DISABLED = False

    def __init__(self, url=None):
        """Constructor of the base class."""
        self._url = None
        self._metadata = None
        self._url_parse_result = None

        # Call proper setters here
        self.url = url

    def can_handle(self):
        """Checking if handler can handle this URL."""
        raise NotImplementedError

    @classmethod
    def get_handler(cls, url):
        """Get the right repository handler instance for given URL.

        :param url: The url of the repository
        :type url: str

        :return: The handler instance. None if no handler found.
        :rtype: BaseHandler, None
        """
        repo_handler = None
        for handler in cls.registry.values():
            handler_instance = handler(url)
            if handler_instance.can_handle():
                repo_handler = handler_instance
                break
        return repo_handler

    @property
    def url(self):
        """The URL to the repository.

        Example:
        - https://github.com/anitagraser/QGIS-style-repo-dummy.git
        - file://home/akbar/dev/qgis-style-repo-dummy
        """
        return self._url

    @url.setter
    def url(self, url):
        """Setter to the repository's URL."""
        self._url = url
        self._url_parse_result = urlparse.urlparse(url)

    @property
    def metadata(self):
        """Metadata content."""
        return self._metadata

    @metadata.setter
    def metadata(self, metadata):
        self._metadata = metadata

    def fetch_metadata(self):
        """Fetch the content of the metadata."""
        raise NotImplementedError

    def parse_metadata(self):
        """Parse str metadata to collection dict."""
        collections = []
        metadata_file = QTemporaryFile()
        if metadata_file.open():
            metadata_file.write(self.metadata)
            metadata_file.close()

        # TODO: Add colection only if the version is ok with user's QGIS
        try:
            parser = SafeConfigParser()
            with codecs.open(metadata_file.fileName(), 'r', encoding='utf-8') as f:
                parser.readfp(f)
            author = parser.get('general', 'author')
            email = parser.get('general', 'email')
            collections_str = parser.get('general', 'collections')
        except Exception as e:
            raise MetadataError('Error parsing metadata: %s' % e)

        collection_list = [
            collection.strip() for collection in collections_str.split(',')]
        # Read all the collections
        for collection in collection_list:
            try:
                name = parser.get(collection, 'name')
                tags = parser.get(collection, 'tags')
                description = parser.get(collection, 'description')
                qgis_min_version = parser.get(collection, 'qgis_minimum_version')
                qgis_max_version = parser.get(collection, 'qgis_maximum_version')

                # Parse the preview urls
                preview_str = parser.has_option(collection, 'preview') and parser.get(collection, 'preview') or ''
                preview_file_list = [preview.strip() for preview in preview_str.split(',') if preview.strip() != '']
                preview_list = []
                for preview in preview_file_list:
                    preview_list.append(self.preview_url(collection, preview))

            except Exception as e:
                raise MetadataError('Error parsing metadata: %s' % e)

            collection_dict = {
                'register_name': collection,
                'author': author,
                'author_email': email,
                'repository_url': self.url,
                'status': COLLECTION_NOT_INSTALLED_STATUS,
                'name': name,
                'tags': tags,
                'description': description,
                'qgis_min_version': qgis_min_version,
                'qgis_max_version': qgis_max_version,
                'preview': preview_list
            }
            collections.append(collection_dict)

        return collections

    def download_collection(self, id, register_name):
        """Download a collection given its ID.

        :param id: The ID of the collection.
        :type id: str
        """
        raise NotImplementedError

    def preview_url(self, collection_name, filename):
        """Return the endpoint URL of the preview image.

        :param collection_name: The register name of the collection.
        :type collection_name: str

        :param filename: The filename of the previe image.
        :type filename: str
        """
        raise NotImplementedError