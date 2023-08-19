import abc

from listenbrainz.mbid_mapping_writer.job_queue import JobItem


class BaseHandler(abc.ABC):

    @abc.abstractmethod
    def get_name(self) -> str:
        """ Return the name of the handler """
        pass

    @abc.abstractmethod
    def get_external_service_queue_name(self) -> str:
        """ Returns the name of the queue to which the associated seeder writes """
        pass

    @abc.abstractmethod
    def get_items_from_listen(self, listen) -> list[JobItem]:
        """ Convert a listen to job items to be enqueued to the crawler. """
        pass

    @abc.abstractmethod
    def get_items_from_seeder(self, message) -> list[JobItem]:
        """ Convert a message from the seeder to job items to be enqueued to the crawler. """
        pass

    @abc.abstractmethod
    def update_metrics(self) -> dict:
        """ Reports a dict of metrics about the processing """
        pass

    @abc.abstractmethod
    def process_items(self, items: list[JobItem]) -> list[JobItem]:
        """ Processes the list of items (example: album ids) received from the crawler.

            During processing new items maybe found for processing, for example discovering a new artist
            and then their albums.

            Returns a list of job items to be enqueued to the crawler for processing in the future.
        """
        pass

