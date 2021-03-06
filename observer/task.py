#!/usr/bin/env python3
"""task.py

Author: neo154
Version: 0.1.1
Date Modified: 2022-06-06

Module that describes a singular task that is to be, this is the basic structure singular tasks
that will utilize things like storage modules and other basic utilities
"""

import datetime
import logging
from logging.handlers import QueueHandler
import sys
from multiprocessing import Queue
from typing import Union, Iterable, Mapping, Any

from observer.storage import Storage

_defaultLogger = logging.getLogger(__name__)

# Trying to identify if we are running interactively
INTERACTIVE = hasattr(sys, 'ps2') | sys.__stdin__.isatty()

def _exit_code(interactive: bool, code: int=0):
    """Quick exit function for tasks"""
    if not interactive:
        sys.exit(code)
    else:
        raise RuntimeError("Cannot run!")

class BaseTask():
    """Task structure and guts for any task that is given"""

    def __init__(self, task_type: str='generic_tasktype', task_name: str='generic_taskname',
            has_mutex: bool=True, has_archive: bool=True, override: bool=False,
            run_date: datetime.datetime=datetime.datetime.now(),
            storage: Storage=Storage(), logger: logging.Logger=_defaultLogger,
            log_level: int=logging.INFO, interactive: bool=INTERACTIVE) -> None:
        """Initializer for all tasks, any logs that occur here will not be in log file for jobs"""
        self.__task_name = task_name.lower().replace(' ', '_')
        self.__task_type = task_type.lower().replace(' ', '_')
        self.__run_date = run_date
        self.__storage = storage
        self.__job_run_check = False
        self.logger = logger
        self.log_level = log_level
        self.__interactive = interactive
        self.__override = override
        self.__has_mutex = has_mutex
        self.__has_archive = has_archive

    @property
    def task_name(self) -> str:
        """
        Identifier for a  a speific job by script, class, or function

        * REQUIRED TO BE WITHOUT SPACES AND WILL GET THROWN TO LOWERCASE
        """
        return self.__task_name

    @property
    def task_type(self) -> str:
        """
        Identifier for a group of jobs, like a set of analyses or download tasks

        * REQUIRED TO BE WITHOUT SPACES AND WILL GET THROWN TO LOWERCASE
        """
        return self.__task_type

    @property
    def run_date(self) -> datetime.datetime:
        """Datetime object for the run of a job"""
        return self.__run_date

    @property
    def storage(self) -> Storage:
        """Storage object for this task"""
        return self.__storage

    @property
    def override(self) -> bool:
        """Whether or not this task will override it's previous results or checks"""
        return self.__override

    @property
    def interactive(self) -> bool:
        """Whether or not this task is running in an interactive python shell"""
        return self.__interactive

    @interactive.setter
    def interactive(self, new_mode: bool) -> None:
        """
        Setter for itneractive indicator, becareful if you are messing with this

        :param new_mode: Indicator for whether or not the job is running in interactive mode
        :returns: None
        """
        self.__interactive = new_mode

    def set_logger(self, logger: Union[logging.Logger, logging.LoggerAdapter],
            level: int) -> None:
        """
        Setter for logger

        :param logger: New logger or logger adapter with contextual information
        :param level: Integer identifying level of logging
        :returns: None
        """
        self.logger = logger
        self.set_level(level)
        self.logger.setLevel(level)
        self.storage.set_logger(self.logger)

    def set_level(self, level: int) -> None:
        """
        Sets level for logger and sub objects

        :param level: Integer identifying level of logging
        :returns: None
        """
        self.log_level = level

    def _check_condition_run(self) -> None:
        """Checks to see if a check run condition has been run"""
        if not self.__job_run_check:
            raise Exception("Has not passed job conditions check yet")

    def check_run_conditions(self, override: bool) -> None:
        """
        Checks whether or not all conditions for a run have been fulfilled

        :param override: Indicator of whether we are overriding based on previous runs data
        :returns: None
        """
        if self.__has_mutex:
            self.__storage.mutex = self.task_name
        if self.__has_archive:
            self.__storage.archive_file = self.task_name
        run = True
        self.logger.debug("Checking run conditions")
        if self.storage.archive_file is not None and self.storage.archive_file.is_file():
            self.logger.info("ARCHIVE_FILE_FOUND: %s", self.storage.archive_file)
            if not override:
                _exit_code(self.__interactive)
            else:
                self.storage.archive_file.rotate()
        for stop_file in self.storage.get_halt_list:
            self.logger.debug("Checking for stop file: '%s'", stop_file)
            if stop_file.is_file():
                self.logger.info("STOP_FILE_FOUND: %s", stop_file)
                _exit_code(self.__interactive)
        # Different so you can see all dependency files missing
        run = self.storage.check_required_files()
        if not run:
            self.logger.info("DEP_FILES_MISSING")
            _exit_code(self.__interactive)
        if self.storage.mutex is not None and self.storage.mutex.exists():
            self.logger.info("MUTEX_FOUND")
            _exit_code(self.__interactive)
        self.__job_run_check = True
        self.storage.mutex.create()
        self.logger.info("CONDITIONS_PASSED")

    def _prep_run(self, queue: Queue=None, args: Iterable[Any]=None,
            kwargs: Mapping[str, Any]=None) -> None:
        """
        Prepares for a running of main function for logging

        :params queue: Multiprocess Queue connected to logging QueueListener
        :param args: Any main method arguments
        :param kwargs: Keyword arguments for main method
        :returns: None
        """
        tmp_handler = QueueHandler(queue)
        tmp_handler.setLevel(self.log_level)
        self.logger.setLevel(self.log_level)
        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}
        # Check even if it is a logger or loggerAdapter
        if isinstance(self.logger, logging.Logger):
            self.logger.addHandler(QueueHandler(queue))
        elif isinstance(self.logger, logging.LoggerAdapter):
            self.logger.logger.setLevel(self.log_level)
            self.logger.logger.addHandler(QueueHandler(queue))
        try:
            self.main(*args, **kwargs)
        except Exception as excep:          # pylint: disable=broad-except
            self.logger.error("%s", excep)
            _exit_code(self.__interactive, 1)

    def main(self) -> None:
        """Main method or function for a task, this is a placeholder to be overwritten"""
        raise RuntimeError("Main function isn't implemented for this Task Object")
