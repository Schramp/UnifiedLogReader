#!/usr/bin/env python3
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Unified log reader
# Copyright (c) 2018  Yogesh Khatri <yogesh@swiftforensics.com> (@swiftforensics)
#
# MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Script Name  : UnifiedLogReader.py
# Author       : Yogesh Khatri
# Last Updated : 2020-01-24
# Purpose/Usage: This script will read unified logs. Tested on python 3.7
#
# Notes:
# Currently this is tested on version 17(0x11) of the tracev3 file used in
# macOS Sierra (10.12.5) and above (including Catalina 10.15). It will not
# work on Sierra (10.12) as it uses version 14(0xE), a later update will
# address this. Also tested on iOS 12.4 logs.
#

import argparse
import logging
import io
import os
import sqlite3
import sys
import time

import UnifiedLog

from UnifiedLog import Lib as UnifiedLogLib
from UnifiedLog import logger
from UnifiedLog import UnifiedLogReaderBase

class SQLiteDatabaseOutputWriter(object):
    '''Output writer that writes output to a SQLite database.'''

    _CREATE_LOGS_TABLE_QUERY = (
        'CREATE TABLE logs (SourceFile TEXT, SourceFilePos INTEGER, '
        'ContinuousTime TEXT, TimeUtc TEXT, Thread INTEGER, Type TEXT, '
        'ActivityID INTEGER, ParentActivityID INTEGER, ProcessID INTEGER, '
        'EffectiveUID INTEGER, TTL INTEGER, ProcessName TEXT, '
        'SenderName TEXT, Subsystem TEXT, Category TEXT, SignpostName TEXT, '
        'SignpostInfo TEXT, ImageOffset INTEGER, SenderUUID TEXT, '
        'ProcessImageUUID TEXT, SenderImagePath TEXT, ProcessImagePath TEXT, '
        'Message TEXT)')

    _INSERT_LOGS_VALUES_QUERY = (
        'INSERT INTO logs VALUES '
        '(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)')

    def __init__(self, path):
        '''Initializes a SQLite database output writer.

        Args:
          path (str): path of the SQLite database file.
        '''
        super(SQLiteDatabaseOutputWriter, self).__init__()
        self._connection = None
        self._path = path

    def Close(self):
        '''Closes the unified logs reader.'''
        if self._connection:
            try:
                self._connection.commit()
                self._connection.close()

            except sqlite3.Error:
                logger.exception('Unable to close database')

            self._connection = None

        self._path = None

    def Open(self):
        '''Opens the output writer.'''
        if os.path.exists(self._path):
            try:
                logger.info('Database already exists, trying to delete it.')
                os.remove(self._path)

            except (IOError, OSError):
                logger.exception(
                    'Unable to remove existing database at %s.', self._path)
                return False

        try:
            logger.info('Trying to create new database file at %s.', self._path)
            self._connection = sqlite3.connect(self._path)

            cursor = self._connection.cursor()
            cursor.execute(self._CREATE_LOGS_TABLE_QUERY)

        except sqlite3.Error:
            logger.exception('Failed to create database at %s', self._path)
            return False

        return True

    def log_entry_tuple(self, log_entry):
        time_value = UnifiedLogLib.ReadAPFSTime(log_entry.time)
        values_tuple = (
            log_entry.filename, log_entry.log_file_pos, log_entry.ct,
            time_value, log_entry.thread, log_entry.log_type,
            log_entry.act_id, log_entry.parentActivityIdentifier,
            log_entry.pid, log_entry.euid, log_entry.ttl,
            log_entry.p_name, log_entry.lib, log_entry.sub_sys,
            log_entry.cat, log_entry.signpost_name,
            log_entry.signpost_string, log_entry.imageOffset,
            '{0!s}'.format(log_entry.imageUUID),
            '{0!s}'.format(log_entry.processImageUUID),
            log_entry.senderImagePath, log_entry.processImagePath,
            log_entry.log_msg)
        return values_tuple

    def WriteLogEntries(self, logs):
        '''Writes several Unified Log entries.

        Args:
          logs (???): list of log entries:
        '''
        if self._connection:
            value_tuples = [self.log_entry_tuple(x) for x in logs]
            # TODO: cache queries to use executemany
            try:
                cursor = self._connection.cursor() 
                cursor.executemany(self._INSERT_LOGS_VALUES_QUERY, value_tuples)

            except sqlite3.Error:
                logger.exception('Error inserting data into database')
            self._connection.commit()

    def WriteLogEntry(self, log_entry):
        '''Writes a Unified Log entry.

        Args:
          log (LogEntry): log entry.
        '''
        self.WriteLogEntries([log_entry])

class FileOutputWriter(object):
    '''Output writer that writes output to a file.'''

    _HEADER_ALL = '\t'.join([
        'SourceFile', 'LogFilePos', 'ContinousTime', 'Time', 'ThreadId',
        'LogType', 'ActivityId', 'ParentActivityId', 'PID', 'EUID', 'TTL',
        'ProcessName', 'SenderName', 'Subsystem', 'Category', 'SignpostName',
        'SignpostString', 'ImageOffset', 'ImageUUID', 'ProcessImageUUID',
        'SenderImagePath', 'ProcessImagePath', 'LogMessage'])

    _HEADER_DEFAULT = (
        'Timestamp                  Thread     Type        '
        'Activity             PID    TTL  Message')

    def __init__(self, path, mode='LOG_DEFAULT', localtime=False):
        '''Initializes a file output writer.

        Args:
          path (str): path of the file.
          mode (Optional[str]): output mode, which can be LOG_DEFAULT or TSV_ALL.

        Raises:
          ValueError: if mode is unsupported.
        '''
        if mode not in ('TSV_ALL', 'LOG_DEFAULT'):
            raise ValueError('Unsupported mode')

        super(FileOutputWriter, self).__init__()
        self._file_object = None
        self._mode = mode
        self._path = path
        self._localtime = localtime

    def Close(self):
        '''Closes the unified logs reader.'''
        if self._file_object:
            self._file_object.close()
            self._file_object = None

        self._path = None

    def Open(self):
        '''Opens the output writer.

        Returns:
          bool: True if successful or False on error.
        '''
        logger.info('Creating output file %s', self._path)

        try:
            self._file_object = io.open(self._path, 'wt', encoding='utf-8')
            try:
                if self._mode == 'TSV_ALL':
                    self._file_object.write(self._HEADER_ALL + '\n')
                else:
                    self._file_object.write(self._HEADER_DEFAULT + '\n')
            except (IOError, OSError):
                logger.exception('Error writing to output file')
                return False
        except (IOError, OSError):
            logger.exception('Failed to open file %s', self._path)
            return False
        return True

    def WriteLogEntries(self, logs):
        '''Writes several Unified Log entries.

        Args:
          logs (???): list of log entries:
        '''
        for log in logs:
            self.WriteLogEntry(log)

    def WriteLogEntry(self, log_entry):
        '''Writes a Unified Log entry.

        Args:
          log (LogEntry): log entry.
        '''
        if self._file_object:
            time_value = UnifiedLogLib.ReadAPFSTime(log_entry.time)

            try:
                if self._mode == 'ALL':
                    imageUUID = '{0!s}'.format(log_entry.imageUUID).upper()
                    processImageUUID = '{0!s}'.format(
                        log_entry.processImageUUID).upper()

                    self._file_object.write((
                        u'{}\t0x{:X}\t{}\t{}\t0x{:X}\t{}\t0x{:X}\t0x{:X}\t{}\t'
                        u'{}\t{}\t({})\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t'
                        u'{}').format(
                            log_entry.filename, log_entry.log_file_pos,
                            log_entry.ct, time_value, log_entry.thread,
                            log_entry.log_type, log_entry.act_id,
                            log_entry.parentActivityIdentifier, log_entry.pid,
                            log_entry.euid, log_entry.ttl, log_entry.p_name,
                            log_entry.lib, log_entry.sub_sys, log_entry.cat,
                            log_entry.signpost_name, log_entry.signpost_string,
                            log_entry.imageOffset, imageUUID, processImageUUID,
                            log_entry.senderImagePath, log_entry.processImagePath,
                            log_entry.log_msg))

                else:
                    msg_parts = []
                    if log_entry.signpost_string:
                        msg_parts.append('[{0:s}]'.format(
                            log_entry.signpost_string))

                    msg_parts.append('{0:s}: '.format(log_entry.p_name))
                    if log_entry.lib:
                      msg_parts.append('({0:s}) '.format(log_entry.lib))

                    if log_entry.sub_sys or log_entry.cat:
                      msg_parts.append('[{0:s}:{1:s}] '.format(
                          log_entry.sub_sys, log_entry.cat))

                    msg_parts.append('{0:s} '.format(log_entry.log_msg))

                    msg = ''.join(msg_parts)
                    if self._localtime: #Use the exact format as "log show" on Mac OSx
                        timestring = time_value.astimezone().strftime('%Y-%m-%d %H:%M:%S.%f%z')
                    else: # Use the timestamp in UTC
                        timestring = str(time_value)

                    self._file_object.write((
                        u'{time:<26} {li.thread:<#10x} {li.log_type:<11} {li.act_id:<#20x} '
                        u'{li.pid:<6} {li.ttl:<4} {message}\n').format(
                            li=log_entry, time=timestring, message=msg.replace('\n',',').strip("\n ,\t")))

            except (IOError, OSError):
                logger.exception('Error writing to output file')


def Main():
    '''The main program function.

    Returns:
      bool: True if successful or False if not.
    '''
    description = (
        'UnifiedLogReader is a tool to read macOS Unified Logging tracev3 files.\n'
        'This is version {0:s} tested on macOS 10.12.5 - 10.15, iOS 12 and iOS 14.\n\n'
        'Notes:\n-----\n'
        'If you have a .logarchive, then point uuidtext_path to the .logarchive folder, \n'
        'the timesync folder is within the logarchive folder').format(UnifiedLog.__version__)

    arg_parser = argparse.ArgumentParser(
        description=description, formatter_class=argparse.RawTextHelpFormatter)
    arg_parser.add_argument('uuidtext_path', help='Path to uuidtext folder (/var/db/uuidtext)')
    arg_parser.add_argument('timesync_path', help='Path to timesync folder (/var/db/diagnostics/timesync)')
    arg_parser.add_argument('tracev3_path', help='Path to either tracev3 file or folder to recurse (/var/db/diagnostics)')
    arg_parser.add_argument('output_path', help='An existing folder where output will be saved')

    arg_parser.add_argument(
         '-f', '--output_format', action='store', choices=(
             'SQLITE', 'TSV_ALL', 'LOG_DEFAULT'),
         metavar='FORMAT', default='LOG_DEFAULT', help=(
             'Output format: SQLITE, TSV_ALL, LOG_DEFAULT  (Default is LOG_DEFAULT)'), type=str.upper)

    arg_parser.add_argument('-l', '--log_level', help='Log levels: INFO, DEBUG, WARNING, ERROR (Default is INFO)')
    arg_parser.add_argument('-t', '--localtime', help='mimic OSX behaviour using localtime to ease comparison with diffing tool',
                            default=False , type=bool)

    args = arg_parser.parse_args()

    output_path = args.output_path.rstrip('\\/')
    uuidtext_folder_path = args.uuidtext_path.rstrip('\\/')
    timesync_folder_path = args.timesync_path.rstrip('\\/')
    tracev3_path = args.tracev3_path.rstrip('\\/')

    if not os.path.exists(uuidtext_folder_path):
        print(f'Exiting..UUIDTEXT Path not found {uuidtext_folder_path}')
        return

    if not os.path.exists(timesync_folder_path):
        print(f'Exiting..TIMESYNC Path not found {timesync_folder_path}')
        return

    if not os.path.exists(tracev3_path):
        print(f'Exiting..traceV3 Path not found {tracev3_path}')
        return

    if not os.path.exists(output_path):
        print (f'Creating output folder {output_path}')
        os.makedirs(output_path)

    log_file_path = os.path.join(output_path, "Log." + time.strftime("%Y%m%d-%H%M%S") + ".txt")

    # log
    if args.log_level:
        args.log_level = args.log_level.upper()
        if not args.log_level in ['INFO','DEBUG','WARNING','ERROR','CRITICAL']:
            print("Invalid input type for log level. Valid values are INFO, DEBUG, WARNING, ERROR")
            return
        else:
            if args.log_level == "INFO": args.log_level = logging.INFO
            elif args.log_level == "DEBUG": args.log_level = logging.DEBUG
            elif args.log_level == "WARNING": args.log_level = logging.WARNING
            elif args.log_level == "ERROR": args.log_level = logging.ERROR
            elif args.log_level == "CRITICAL": args.log_level = logging.CRITICAL
    else:
        args.log_level = logging.INFO

    log_level = args.log_level #logging.DEBUG
    log_console_handler = logging.StreamHandler()
    log_console_handler.setLevel(log_level)
    log_console_format  = logging.Formatter('%(levelname)s - %(message)s')
    log_console_handler.setFormatter(log_console_format)
    logger.addHandler(log_console_handler)

    #log file
    log_file_handler = logging.FileHandler(log_file_path)
    log_file_handler.setFormatter(log_console_format)
    logger.addHandler(log_file_handler)
    logger.setLevel(log_level)

    unified_log_reader = UnifiedLogReaderBase.UnifiedLogReaderHelper()

    if not unified_log_reader.ReadTimesyncFolder(timesync_folder_path):
        logger.error('Failed to get any timesync entries')
        return False

    if args.output_format == 'SQLITE':
        database_path = os.path.join(output_path, 'unifiedlogs.sqlite')
        output_writer = SQLiteDatabaseOutputWriter(database_path)

    elif args.output_format in ('TSV_ALL', 'LOG_DEFAULT'):
        file_path = os.path.join(output_path, 'logs.txt')
        output_writer = FileOutputWriter(
            file_path, mode=args.output_format, localtime=args.localtime)

    if not output_writer.Open():
        return False

    time_processing_started = time.time()
    logger.info('Started processing')

    unified_log_reader.ReadDscFiles(uuidtext_folder_path)
    unified_log_reader.ReadTraceV3Files(tracev3_path, output_writer)

    output_writer.Close()

    time_processing_ended = time.time()
    run_time = time_processing_ended - time_processing_started
    logger.info("Finished in time = {}".format(time.strftime('%H:%M:%S', time.gmtime(run_time))))
    logger.info("{} Logs processed".format(unified_log_reader.total_logs_processed))
    logger.info("Review the Log file and report any ERRORs or EXCEPTIONS to the developers")

    return True


if __name__ == "__main__":
    if not Main():
        sys.exit(1)
    else:
        sys.exit(0)
