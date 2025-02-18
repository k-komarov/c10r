import logging
import os
from string import Template


class TemplateFile:
    def __init__(self, fpath, config, row={}):
        self._file = fpath
        self._row = row
        self._config = config

    @property
    def _mtime(self):
        return int(self._row.get(self._config['mtime'], 0))

    @property
    def _template(self):
        return Template(open(self._config['src']).read()).substitute(**self._row)

    @property
    def _prune_required(self):
        return self._config.getboolean('prune') and not self._row

    @property
    def _write_required(self):
        if self._config.getboolean('write') and self._row:
            return any([
                not self._file.exists(),
                self._file.exists() and not int(self._file.stat().st_mtime) == self._mtime
            ])

    def _write(self):
        if self._write_required:
            self._file.write_text(self._template)
            os.utime(self._file, (self._mtime, self._mtime))
            logging.info("Created: %s", self._file)

    def _prune(self):
        if self._prune_required:
            self._file.unlink()
            logging.info("Pruned: %s", self._file)

    def sync(self):
        logging.info(f"Syncing template: {self._file}")
        self._prune()
        self._write()

    @property
    def synced(self):
        return not self._prune_required and not self._write_required
