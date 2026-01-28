import abc
from collections import Counter

from listenbrainz.mbid_mapping_writer.job_queue import JobItem


class BaseHandler(abc.ABC):

    def __init__(self, name, external_service_queue):
        """
            A base class that abstracts common functionality for working with metadata service crawler.

            Args:
                name: the name of crawler service
                external_service_queue: the name of the queue to which the associated seeder writes to
        """
        self.metrics = Counter()
        self.name = name
        self.external_service_queue = external_service_queue

    @abc.abstractmethod
    def get_items_from_listen(self, listen) -> list[JobItem]:
        """ Convert a listen to job items to be enqueued to the crawler. """
        pass

    @abc.abstractmethod
    def get_items_from_seeder(self, message) -> list[JobItem]:
        """ Convert a message from the seeder to job items to be enqueued to the crawler. """
        pass

    @abc.abstractmethod
    def get_seed_ids(self) -> list[str]:
        """ Query the external metadata service to discover newly added items. """
        pass

    @abc.abstractmethod
    def process(self, item_ids: list[str]) -> list[JobItem]:
        """ Processes the list of items (example: album ids or track ids) received from the crawler.

            During processing new items maybe found for processing, for example discovering a new artist
            and then their albums.

            Returns a list of job items to be enqueued to the crawler for processing in the future.
        """
        pass
