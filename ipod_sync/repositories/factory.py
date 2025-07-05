"""Repository factory for creating repository instances."""
from typing import Dict, Any, Optional
from pathlib import Path

from . import Repository, PlaylistRepository
from .ipod_repository import IpodRepository
from .queue_repository import QueueRepository
from .. import config

class RepositoryFactory:
    """Factory for creating repository instances."""
    
    @staticmethod
    def create_ipod_repository(device_path: str = None) -> IpodRepository:
        """Create an iPod repository."""
        return IpodRepository(device_path or config.IPOD_DEVICE)
    
    @staticmethod
    def create_queue_repository(queue_dir: Path = None) -> QueueRepository:
        """Create a queue repository."""
        return QueueRepository(queue_dir or config.SYNC_QUEUE_DIR)
    
    @staticmethod
    def get_repository(repo_type: str, **kwargs) -> Repository:
        """Get a repository by type."""
        if repo_type == "ipod":
            return RepositoryFactory.create_ipod_repository(kwargs.get('device_path'))
        elif repo_type == "queue":
            return RepositoryFactory.create_queue_repository(kwargs.get('queue_dir'))
        else:
            raise ValueError(f"Unknown repository type: {repo_type}")

# Convenience functions
def get_ipod_repo(device_path: str = None) -> IpodRepository:
    """Get iPod repository instance."""
    return RepositoryFactory.create_ipod_repository(device_path)

def get_queue_repo(queue_dir: Path = None) -> QueueRepository:
    """Get queue repository instance.""" 
    return RepositoryFactory.create_queue_repository(queue_dir)