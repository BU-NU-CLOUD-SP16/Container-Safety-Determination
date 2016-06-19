from abc import ABCMeta, abstractmethod


class BaseDatabase():
    __metaclass__ = ABCMeta

    @abstractmethod
    def index(self, **kwargs):
        raise NotImplementedError()

    @abstractmethod
    def search(self, **kwargs):
        raise NotImplementedError()
