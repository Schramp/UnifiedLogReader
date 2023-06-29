import abc
import os

from UnifiedLog import virtual_file_system, virtual_file, tracev3_file, logger, Lib as UnifiedLogLib
from scripts.UnifiedLogReader import SQLiteDatabaseOutputWriter


class OutputWriter(object):
    '''Output writer interface.'''

    @abc.abstractmethod
    def Close(self):
        '''Closes the output writer.'''

    @abc.abstractmethod
    def Open(self):
        '''Opens the output writer.

        Returns:
          bool: True if successful or False on error.
        '''

    @abc.abstractmethod
    def WriteLogEntries(self, logs):
        '''Writes several Unified Log entries.

        Args:
          logs (???): list of log entries:
        '''

    @abc.abstractmethod
    def WriteLogEntry(self, log_entry):
        '''Writes a Unified Log entry.

        Args:
          log (LogEntry): log entry.
        '''


class UnifiedLogReaderHelper(object):
    '''Unified log reader.'''

    def __init__(self):
        '''Initializes an unified log reader.'''
        super(UnifiedLogReaderHelper, self).__init__()
        self._caches = None
        self._ts_list = []
        self._uuidtext_folder_path = None
        self._vfs = virtual_file_system.VirtualFileSystem(
            virtual_file.VirtualFile)
        self.total_logs_processed = 0

    # TODO: remove log_list_process_func callback from TraceV3.Parse()
    def _ProcessLogsList(self, logs, tracev3):
        if isinstance(self._output_writer, SQLiteDatabaseOutputWriter):
            self._output_writer.WriteLogEntries(logs)
            self.total_logs_processed += len(logs)
        else:
            for log_entry in logs:
                self._output_writer.WriteLogEntry(log_entry)
                self.total_logs_processed += 1

    def _ReadTraceV3File(self, tracev3_path, output_writer):
        '''Reads a tracev3 file.

        Args:
          tracev3_path (str): path of the tracev3 file.
          output_writer (UnifiedLog.UnifiedLogReaderBase.OutputWriter): output writer.

        Returns:
          TraceV3: tracev3 file.
        '''
        file_object = virtual_file.VirtualFile(tracev3_path, 'traceV3')
        trace_file = tracev3_file.TraceV3(
            self._vfs, file_object, self._ts_list, self._uuidtext_folder_path,
            self._caches)

        # TODO: remove log_list_process_func callback from TraceV3.Parse()
        self._output_writer = output_writer
        trace_file.Parse(log_list_process_func=self._ProcessLogsList)

    def _ReadTraceV3Folder(self, tracev3_path, output_writer):
        '''Reads all the tracev3 files in the folder.

        Args:
          tracev3_path (str): path of the tracev3 folder.
          output_writer (UnifiedLog.UnifiedLogReaderBase.OutputWriter): output writer.
        '''
        for directory_entry in os.listdir(tracev3_path):
            directory_entry_path = os.path.join(tracev3_path, directory_entry)
            if os.path.isdir(directory_entry_path):
                self._ReadTraceV3Folder(directory_entry_path, output_writer)

            elif (directory_entry.lower().endswith('.tracev3') and
                  not directory_entry.startswith('._')):
                if os.path.getsize(directory_entry_path) > 0:
                    logger.info("Trying to read file - %s", directory_entry_path)
                    self._ReadTraceV3File(directory_entry_path, output_writer)
                else:
                    logger.info("Skipping empty file - %s", directory_entry_path)

    def ReadDscFiles(self, uuidtext_folder_path):
        '''Reads the dsc files.

        Args:
          uuidtext_folder_path (str): path of the uuidtext folder.
        '''
        self._caches = UnifiedLogLib.CachedFiles(self._vfs)
        self._uuidtext_folder_path = uuidtext_folder_path

        self._caches.ParseFolder(self._uuidtext_folder_path)

    def ReadTimesyncFolder(self, timesync_folder_path):
        '''Reads the timesync folder.

        Args:
          timesync_folder_path (str): path of the timesync folder.

        Returns:
          bool: True if successful or False otherwise.
        '''
        self._ts_list = []

        UnifiedLogLib.ReadTimesyncFolder(
            timesync_folder_path, self._ts_list, self._vfs)

        return bool(self._ts_list)

    def ReadTraceV3Files(self, tracev3_path, output_writer):
        '''Reads the tracev3 files.

        Args:
          tracev3_path (str): path of the tracev3 file or folder.
          output_writer (UnifiedLog.UnifiedLogReaderBase.OutputWriter): output writer.
        '''
        if os.path.isdir(tracev3_path):
            self._ReadTraceV3Folder(tracev3_path, output_writer)
        else:
            self._ReadTraceV3File(tracev3_path, output_writer)


def DecompressTraceV3Log(input_path, output_path):
    try:
        with open(input_path, 'rb') as trace_file:
            with open(output_path, 'wb') as out_file:
                return UnifiedLogLib.DecompressTraceV3(trace_file, out_file)
    except:
        logger.exception('')
