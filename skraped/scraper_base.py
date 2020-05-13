import logging
import requests
from bs4 import BeautifulSoup

lgr = logging.getLogger(__name__)


class ScraperBase():
    """Base class implementing core scraping functionality"""

    def __init__(self, config={}):
        self.config = config

    def run_scraper(self):
        """Entry Point to the execution of all scrape scources defined in the config"""
        scraper_classes = self.config.sources
        for scraper_class in scraper_classes:
            class_instance = self.get_class_instance(
                scraper_class, config=self.config)
            self.call_class_method(class_instance, 'run_scraper')
            # TODO: Need to Architect fully the full flow of the data from each scraper and how it will be
            # Aggregated into the csv file output

    @staticmethod
    def call_class_method(class_instance, function_name, **kwargs):
        """Calls calls a function from the passed in class instance"""
        try:
            if class_instance is not None and function_name:
                return getattr(class_instance, function_name)(**kwargs)
        except AttributeError:
            lgr.warning(f'method {function_name} does not exist in {class_instance}')
        return None

    @staticmethod
    def get_class_instance(class_name, **kwargs):
        """Retrieves a class instance to be used for running individual scrapers"""
        if class_name in globals() and hasattr(globals()[class_name], '__class__'):
            try:
                return globals()[class_name](**kwargs)
            except TypeError:
                lgr.warning(f'{class_name} cannot be retrieved.')
        return None
