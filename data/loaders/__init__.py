"""
ORACLE-X/N — Dataset Loaders
==============================
Loads Yelp, Goodreads, and Amazon datasets and maps users/items
onto ORACLE's Nigerian behavioral profile system.
"""
from .base_loader import BaseDatasetLoader, DatasetRecord, train_test_split_by_user
from .yelp_loader import YelpLoader
from .goodreads_loader import GoodreadsLoader
from .amazon_loader import AmazonLoader

__all__ = [
    "BaseDatasetLoader",
    "DatasetRecord",
    "train_test_split_by_user",
    "YelpLoader",
    "GoodreadsLoader",
    "AmazonLoader",
]
