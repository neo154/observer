#!/usr/bin/env python3
"""storage.py

Author: neo154
Version: 0.0.1
Date Modified: 2022-06-05


Class and definitions for how storage is handled for the platform
"""

import datetime
from os import chdir
import tarfile
from typing import Union, List
from pathlib import Path
from logging import Logger, getLogger

from observer.storage.models import LocalFSConfig, LocalFile, StorageLocation,\
        generate_storage_location
from observer.storage.storage_config import StorageConfig

_defaultLogger = getLogger(__name__)

def _check_storage_arg(arg: Union[dict, StorageLocation]) -> StorageLocation:
    """
    Helper to resolve and check storage args

    :param arg: Storage location or dictionary
    :returns: Fully resolved StorageLocation object
    """
    if isinstance(arg, dict):
        arg = generate_storage_location(arg)
    return arg

class Storage():
    """Storage class that identifies and handles abstracted storage tasks"""

    def __init__(self, storage_config: Union[dict, StorageConfig]=None,
            report_date: datetime.datetime=datetime.datetime.now(),
            date_postfix_fmt: str="%Y_%m_%d", job_desc: str="generic",
            logger: Logger=_defaultLogger) -> None:
        self.date_postfix_fmt = date_postfix_fmt
        self.report_date_str = report_date
        self.job_desc = job_desc
        if storage_config is None:
            storage_config = {
                'base_loc': {
                    'config_type': 'local_filesystem',
                    'config': {
                        'loc': Path.cwd(),
                        'is_dir': True
                    }
                }
            }
        if not isinstance(storage_config, StorageConfig):
            storage_config = StorageConfig(**storage_config)
        self._base_loc = storage_config['base_loc']
        self._data_loc = storage_config['data_loc']
        self._tmp_loc = storage_config['tmp_loc']
        self._mutex_loc = storage_config['mutex_loc']
        self._mutex_file = None
        self._archive_loc = storage_config['archive_loc']
        self._archive_file = self.gen_location_ref(self.archive_loc,
            suffix='tar.bz2', name_prefix=self.job_desc)
        self._archive_files = storage_config['archive_files']
        self._required_files = storage_config['required_files']
        self._halt_files = storage_config['halt_files']
        self.logger = logger

    @property
    def report_date_str(self) -> str:
        """Report date string getter"""
        return self._report_date_str

    @report_date_str.setter
    def report_date_str(self, date_time: datetime.datetime) -> None:
        """
        Sets report date, really postfix, reference for all objects

        :param date_time: Datetime object use to setup postfix config
        :returns: None
        """
        self._report_date_str = date_time.strftime(self.date_postfix_fmt)

    @property
    def date_postfix_fmt(self) -> str:
        """Property declaration for postfix fmt for dates"""
        return self._date_postfix_fmt

    @date_postfix_fmt.setter
    def date_postfix_fmt(self, new_fmt: str) -> None:
        """
        Setter for date postfix format

        :new_fmt: String that will be tested as the new datetime formatter
        :returns: None
        """
        # Try
        _ = datetime.datetime.now().strftime(new_fmt)
        # If pass, set
        self._date_postfix_fmt = new_fmt

    @property
    def job_desc(self) -> str:
        """Property declaration and getter for getting job description"""
        return self._job_desc

    @job_desc.setter
    def job_desc(self, new_desc: str) -> None:
        """
        Property setter for job descriptions for file names

        :param new_desc: String that describes file
        :returns: None
        """
        self._job_desc = new_desc

    @property
    def base_loc(self) -> StorageLocation:
        """Property declaration for base storage location"""
        return self._base_loc

    @base_loc.setter
    def base_loc(self, new_loc=Union[dict, StorageLocation]) -> None:
        """
        Setter for base location configuration

        :param new_loc: StorageLocation object to replace base_loc
        :returns: None
        """
        tmp_ref = _check_storage_arg(new_loc)
        self.logger.info("Setting base loc to: %s", tmp_ref)
        self._base_loc = tmp_ref

    @property
    def data_loc(self) -> StorageLocation:
        """Property declaration and getter for data loc"""
        return self._data_loc

    @data_loc.setter
    def data_loc(self, new_loc=Union[dict, StorageLocation], sub_loc_prefix: str='data') -> None:
        """
        Setter for data location reference

        :param new_loc: New location that might be used
        :param sub_loc_prefix: Prefix for sub locations
        :returns: None
        """
        tmp_ref = _check_storage_arg(new_loc)
        self.logger.info("Setting data loc to: %s", tmp_ref)
        self._data_loc = tmp_ref.join_loc(f'{sub_loc_prefix}_{self.report_date_str}', as_dir=True)

    @property
    def tmp_loc(self) -> StorageLocation:
        """Property declration and getter for tmp location"""
        return self._tmp_loc

    @tmp_loc.setter
    def tmp_loc(self, new_loc=Union[dict, StorageLocation]) -> None:
        """
        Setter for tmp location configuration

        :param new_loc: StorageLocation object to replace tmp_loc
        :returns: None
        """
        tmp_ref = _check_storage_arg(new_loc)
        self.logger.info("Setting tmp loc to: %s", tmp_ref)
        self._tmp_loc = new_loc

    @property
    def report_loc(self) -> StorageLocation:
        """Property delcaration and getter for report base directory"""
        return self._report_dir

    @report_loc.setter
    def report_loc(
            self, new_loc=Union[dict, StorageLocation], sub_loc_prefix: str='reports') -> None:
        """
        Setter for report location reference

        :param new_loc: New location that might be used
        :param sub_loc_prefix: Prefix for sub locations
        :returns: None
        """
        tmp_ref =  _check_storage_arg(new_loc)
        self.logger.info("Setting report loc to: %s", tmp_ref)
        self._report_dir = tmp_ref.join_loc(f'{sub_loc_prefix}_{self.report_date_str}',as_dir=True)

    @property
    def archive_loc(self) -> StorageLocation:
        """Property delcaration and getter for archive location"""
        return self._archive_loc

    @archive_loc.setter
    def archive_loc(
            self, new_loc=Union[dict, StorageLocation], sub_loc_prefix: str='archive') -> None:
        """
        Setter for archive location reference

        :param new_loc: New location that might be used
        :param sub_loc_prefix: Prefix for sub locations
        :returns: None
        """
        tmp_ref = _check_storage_arg(new_loc)
        self.logger.info("Setting archive loc to: %s", tmp_ref)
        self._archive_loc =tmp_ref.join_loc(f'{sub_loc_prefix}_{self.report_date_str}',as_dir=True)
        self.archive_file = self.__get_stem_prefix(self.archive_file)

    @property
    def archive_file(self) -> StorageLocation:
        """Getter and property declaration for archive file"""
        return self._archive_file

    @archive_file.setter
    def archive_file(self, name_prefix:str) -> None:
        """
        Setter for archive file reference

        :param suffix: type of archive that is going to be created
        :returns: None
        """
        tmp_ref = self.gen_location_ref(self.archive_loc,suffix='tar.bz2',name_prefix=name_prefix)
        self.logger.info("Setting archive file reference to: %s", tmp_ref)
        self._archive_file = tmp_ref

    @property
    def mutex_loc(self) -> StorageLocation:
        """Getter and property declaration for mutex loc"""
        return self._mutex_loc

    @mutex_loc.setter
    def mutex_loc(self, new_loc=Union[dict, StorageLocation]) -> None:
        """
        Setter for mutex loc reference

        :param new_loc: New location for mutexes
        :returns: None
        """
        tmp_ref = _check_storage_arg(new_loc)
        self.logger.info("Setting mutex loc to: %s", tmp_ref)
        self._mutex_loc = tmp_ref
        self.mutex = self.__get_stem_prefix(self.mutex)

    @property
    def mutex(self) -> StorageLocation:
        """Getter and property declaration for mutex_file"""
        return self._mutex_file

    @mutex.setter
    def mutex(self, name_prefix: str) -> None:
        """
        Setter for mutex reference

        :param name_prefix: String of mutex to set for search
        :returns: None
        """
        tmp_ref = self.gen_location_ref(self.mutex_loc, suffix='mutex', name_prefix=name_prefix)
        self.logger.info("Setting mutex reference to: %s", tmp_ref)
        self._mutex_file = tmp_ref

    @property
    def get_archive_list(self) -> List[StorageLocation]:
        """List of StorageLocations/files that are to be archived at the end of the run"""
        return self._archive_files

    @property
    def get_halt_list(self) -> List[StorageLocation]:
        """List of StorageLocations/files that indicate a job should not run"""
        return self._halt_files

    @property
    def get_required_list(self) -> List[StorageLocation]:
        """List of StorageLocations/files that are required to run a job"""
        return self._required_files

    def gen_location_ref(self,
            storage_loc: StorageLocation, suffix: str, name_prefix: str=None) -> StorageLocation:
        """
        Generator for storage locations

        :returns: Storaglocation base on naming and base location
        """
        if name_prefix is None:
            name_prefix = self.job_desc
        return storage_loc.join_loc(f'{name_prefix}_{self.report_date_str}.{suffix}')

    def __get_stem_prefix(self, loc: StorageLocation) -> None:
        """Pulls location name and gets the prefix for location regeneration"""
        return loc.name.split('.')[0].replace(f'{self.report_date_str}', '')

    def __search_storage_group(self, stor_list: List[StorageLocation],
            stor_obj: StorageLocation) -> int:
        """Helper to identify index for group using UUIDs"""
        for index in range(len(stor_list)):     # pylint: disable=consider-using-enumerate
            if stor_list[index]==stor_obj:
                return index
        return -1

    def __check_storage_loc(self, loc: StorageLocation) -> None:
        """Helper to look for loc and if doesn't exist then it is created"""
        if loc.exists():
            self.logger.debug("Storage location found: %s", loc)
            return
        self.logger.info("Location not found: %s", loc)
        loc.create_loc(parents=True)

    def __check_storage_group(self, stor_list: List[StorageLocation],
            stor_obj: StorageLocation) -> bool:
        """Helper to return boolean if something exists or not in storage group"""
        return self.__search_storage_group(stor_list=stor_list, stor_obj=stor_obj) != -1

    def __add_to_group(self, stor_list: List[StorageLocation], new_loc: StorageLocation):
        """Helper to add a storage location entry to the list if it is not already there"""
        if self.__check_storage_group(stor_list=stor_list, stor_obj=new_loc):
            self.logger.warning("This location is already attached to this group, cannot add")
        else:
            stor_list.append(new_loc)

    def __delete_from_group(
            self, stor_list: List[StorageLocation], bye_loc: StorageLocation) -> None:
        """Helper to remove storage location entry from a list"""
        index = self.__search_storage_group(stor_list=stor_list, stor_obj=bye_loc)
        if index == -1:
            self.logger.warning(
                "Cannot delete storage location with UUID: '%s' not in group", bye_loc
            )
        else:
            _ = stor_list.pop(index)

    def __print_group(self, stor_list: List[StorageLocation]):
        for storage in stor_list:
            print(str(storage))

    def set_logger(self, logger: Logger) -> None:
        """
        Sets logger reference for all storage locations

        :param logger: Logger to use in the storage instance
        :returns: None
        """
        self.logger = logger

    def list_archive_files(self) -> None:
        """Prints all storage locations and details"""
        self.__print_group(self._archive_files)

    def add_to_archive_list(self, new_loc: StorageLocation) -> None:
        """
        Adds new storage location for archival list

        :param new_loc: StorageLocation based object to add to archive list
        :returns: None
        """
        self.logger.debug("Adding '%s' to archive list", new_loc.name)
        self.__add_to_group(stor_list=self._archive_files, new_loc=new_loc)

    def delete_from_archive_list(self, old_loc: StorageLocation) -> None:
        """
        Deletes storage location from archival list

        :param old_loc: Storage location to be removed from archive list
        :returns: None
        """
        self.logger.debug("Removing '%s' from archive list", old_loc.name)
        self.__delete_from_group(self._archive_files, old_loc)

    def list_required_files(self) -> None:
        """Prints all storage locations and details"""
        self.__print_group(self._required_files)

    def add_to_required_list(self, new_loc: StorageLocation) -> None:
        """
        Adds new storage location for required locations list

        :param new_loc: StorageLocation based object to add to required list
        :returns: None
        """
        self.logger.debug("Adding '%s' to required list", new_loc.name)
        self.__add_to_group(stor_list=self._required_files, new_loc=new_loc)

    def delete_from_required_list(self, old_loc: StorageLocation) -> None:
        """
        Deletes storage location from required locations list

        :param old_loc: Storage location to be removed from required list
        :returns: None
        """
        self.logger.debug("Removing '%s' from required list", old_loc.name)
        self.__delete_from_group(self._required_files, old_loc)

    def list_halt_files(self) -> None:
        """Prints all storage locations and details"""
        self.__print_group(self._halt_files)

    def add_to_halt_list(self, new_loc: StorageLocation) -> None:
        """
        Adds new storage location for halt location list

        :param new_loc: StorageLocation based object to add to halting list
        :returns: None
        """
        self.logger.debug("Adding '%s' to halt list", new_loc.name)
        self.__add_to_group(stor_list=self._halt_files, new_loc=new_loc)

    def delete_from_halt_list(self, old_loc: StorageLocation) -> None:
        """
        Deletes storage location from halt file list

        :param old_loc: Storage location to be removed from required list
        :returns: None
        """
        self.logger.debug("Removing '%s' from halt list", old_loc.name)
        self.__delete_from_group(self._halt_files, old_loc)

    def rotate_location(self, locs: Union[StorageLocation, List[StorageLocation]]) -> None:
        """
        Moves locations around from a location or list of locations

        :param locs: StorageLocations to be rotated
        :returns: None
        """
        if not isinstance(locs, list):
            locs = [locs]
        for item in locs:
            item.rotate(logger=self.logger)

    def create_archive(self, archive_files: List[StorageLocation]=None,
            archive_loc: StorageLocation=None, cleanup: bool=False) -> None:
        """
        Creates archive locations either from a new list of archive files and archive location
        or using internally managed as defaults

        :param archive_files: List of storage locations for files that are to be stored
        :param archive_loc: Storage location to create
        :param cleanup: Boolean of whether to delete all archived files or not
        :returns: None
        """
        if archive_files is None:
            archive_files = self._archive_files
        if archive_loc is None:
            archive_loc = self.archive_file
        if not self.check_archive_files(archive_files=archive_files):
            raise RuntimeError("Not all archive files exist, cannot create archive")
        self.logger.info("Creating archive: %s", archive_loc.name)
        orig_path = Path.cwd()
        if isinstance(self.tmp_loc, LocalFile):
            tmp_dir = self.tmp_loc.absolute_path
        else:
            tmp_dir = Path.cwd().absolute().joinpath('tmp')
            tmp_dir.mkdir()
        tmp_archive_file = tmp_dir.joinpath(f'{archive_loc.name}_tmp.tar.bz2')
        tmp_archive_loc = LocalFile(LocalFSConfig(loc=tmp_archive_file))
        if tmp_archive_file.exists():
            self.logger.error("Temporary archive file already exists, probable issue")
        with tarfile.open(tmp_archive_file, 'w|bz2') as new_archive:
            for new_file in archive_files:
                self.logger.debug("Archive '%s' adding file '%s'", archive_loc.name, new_file.name)
                tmp_ref = new_file.get_archive_ref()
                chdir(tmp_ref.parent)
                new_archive.add(tmp_ref.name, recursive=True)
        chdir(orig_path)
        tmp_archive_loc.move(archive_loc, logger=self.logger)
        if cleanup:
            self.logger.info("Running cleanup")
            for new_file in archive_files:
                new_file.delete(logger=self.logger)

    def create_mutex(self) -> None:
        """
        Creates mutex to stop other instances of same the job from starting

        :returns: None
        """
        self.logger.info("Creating mutex")
        self.mutex.create()

    def cleanup_mutex(self) -> None:
        """
        Removes mutex file

        :returns: None
        """
        self.logger.info("Cleaning up mutex file")
        self.mutex.delete(logger=self.logger)

    def check_archive_files(self, archive_files: List[StorageLocation]=None) -> bool:
        """
        Runs a check for all archive files that are required for creation

        :returns: Boolean of whether or not archivefiles exist or not
        """
        if archive_files is None:
            archive_files = self.get_archive_list()
        for archive_file in archive_files:
            if not archive_file.exists():
                return False
        return True

    def check_required_files(self) -> bool:
        """
        Runs a check for all required files before a run of a job or certain operations

        :returns: Boolean of whether check passes or not
        """
        passes = True
        for required_file in self._required_files:
            if not required_file.exists():
                self.logger.warning("Required file not found: %s", required_file)
                passes = False
            else:
                self.logger.debug("Required file was found: %s", required_file)
        return passes

    def check_required_locations(self) -> None:
        """
        Checks for the existence and attempts to setup storage locations for data and
        storage locations that are required for job runs

        :returns: None
        """
        self.logger.info("Running checks and adjustments for job environment")
        self.__check_storage_loc(self.base_loc)
        self.__check_storage_loc(self.data_loc)
        self.__check_storage_loc(self.tmp_loc)
        self.__check_storage_loc(self.report_loc)
        self.__check_storage_loc(self.archive_loc)
        self.__check_storage_loc(self.mutex_loc)
        self.logger.info("Environment setup")
