"""
module: html_printer
public function: send_to_print()

    This module can print HTML-like text to a default printer and save it to
a PDF file. Just import and call the public function send_to_print(). The
documents are queued and printed when the printer is released.
    There is only one "object" here: it is required for signal processing in
the QT library. Improvements are required. No error handling is performed.
"""

from collections import deque

from PySide2.QtCore import QMarginsF, Slot, Signal, QObject
from PySide2.QtGui import QPageSize, QPageLayout
from PySide2.QtPrintSupport import QPrinter, QPrinterInfo
from PySide2.QtWebEngineWidgets import QWebEnginePage


class _State(QObject):
    docs = deque()
    in_progress = False
    next_task_signal = Signal()


def _next_task():
    print('INFO: Signal received: request for a new task.')
    if _print_manager.docs:
        _print_manager.in_progress = True
        task = _print_manager.docs.popleft()
        _print_worker(task)
    else:
        _print_manager.in_progress = False


_print_manager = _State()
# noinspection PyUnresolvedReferences
_print_manager.next_task_signal.connect(_next_task)


def send_to_print(html_text: str, file_path: str = ''):
    task = {'html_text': html_text, 'file_path': file_path}
    _print_manager.docs.append(task)
    if not _print_manager.in_progress:
        # noinspection PyUnresolvedReferences
        _print_manager.next_task_signal.emit()


def _print_worker(task: dict):

    @Slot()
    def _load_started():
        """ Slot for QWebEnginePage.loadStarted signal """
        print('INFO: Document loading started.')

    @Slot(int)
    def _load_progress(progress: int):
        """ Slot for QWebEnginePage.loadProgress signal """
        print('INFO: Progress - {}%'.format(progress))

    @Slot(bool)
    def _load_finished_for_pdf(ok: bool):
        """ Slot for QWebEnginePage.loadFinished signal """
        if ok:
            ps = QPageSize(QPageSize.A4)
            pl = QPageLayout(ps, QPageLayout.Portrait, QMarginsF())
            page.printToPdf(task['file_path'], pl)
        else:
            print('ERROR: Document loading failed.')

    @Slot(bool)
    def _load_finished_for_printer(ok: bool):
        """ Slot for QWebEnginePage.loadFinished signal """
        if ok:
            page.print(printer, _after_printing)
        else:
            print('ERROR: Document loading failed.')

    @Slot(str, bool)
    def _pdf_printing_finished(path: str, ok: bool):
        """ Slot for QWebEnginePage.pdfPrintingFinished signal """
        if ok:
            print('INFO: Document successfully saved to {}.'.format(path))
        else:
            print('ERROR: Document saved to PDF failed.')
        nonlocal page
        del page
        # noinspection PyUnresolvedReferences
        _print_manager.next_task_signal.emit()

    def _after_printing(ok: bool):
        """ Call-back function for QWebEnginePage.print() """
        if ok:
            print('INFO: Document successfully printed.')
        else:
            print('ERROR: Document printing failed.')
        nonlocal page
        del page
        nonlocal printer
        del printer
        # noinspection PyUnresolvedReferences
        _print_manager.next_task_signal.emit()

    page = QWebEnginePage()
    page.loadStarted.connect(_load_started)
    page.loadProgress.connect(_load_progress)
    page.pdfPrintingFinished.connect(_pdf_printing_finished)

    if task['file_path']:
        page.loadFinished.connect(_load_finished_for_pdf)
    else:
        page.loadFinished.connect(_load_finished_for_printer)
        printer = QPrinter(QPrinterInfo.defaultPrinter())
        printer.setResolution(600)  # !!! Must have. May be 300, 600.

    page.setHtml(task['html_text'])
