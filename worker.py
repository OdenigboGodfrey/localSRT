from PyQt6.QtCore import QThread, pyqtSignal
from core import process_srt_job_with_progress
import copy
from shared import progress_store


class Worker(QThread):
    progress = pyqtSignal(dict)

    def __init__(self, path, chunk, model):
        super().__init__()
        self.path = path
        self.chunk = chunk
        self.model = model

    def run(self):

        def callback(state):
            # ALWAYS emit a copy, it's thread-safe
            self.progress.emit(copy.deepcopy(state))

        process_srt_job_with_progress(
            self.path,
            self.chunk,
            self.model,
            progress=progress_store,
            progress_callback=callback
        )