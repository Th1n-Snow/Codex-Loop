# Third-Party Notices

Codex Window Sentinel's earlier interactive trigger strategy and bounded
quiet-period shutdown behavior were adapted from CCLimitPing by wavever. That
code was removed on 2026-08-30 when the trigger moved to the Codex app-server
protocol (see `docs/TUI_TRIGGER_POSTMORTEM.md`). The weekly-protection threshold
and the general idea of triggering a window with one minimal request through the
vendor's own CLI remain influenced by that project, so the notice stands:

https://github.com/wavever/CCLimitPing

CCLimitPing is licensed under the MIT License:

```text
MIT License

Copyright (c) 2026 wavever

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Bundled Windows runtime

- Python 3.13.7: Python Software Foundation license and included historical notices; see licenses/Python-3.13.7.txt.
- Qt 6.12.0 / PySide6-Essentials 6.12.0 / Shiboken6 6.12.0: used under the applicable open-source LGPL v3 terms (including GPL v3 incorporated terms), not relicensed under MIT. See licenses/LGPL-3.0.txt, licenses/GPL-3.0.txt and the bundled Qt/PySide third-party license documents. Unmodified shared libraries remain separate in _internal and may be replaced with compatible modified builds. Reverse engineering for debugging modifications to these libraries is not prohibited by this project.
- PyInstaller 6.22.3 bootloader: GPL with its distribution exception; see licenses/PyInstaller-exception.txt. The exception permits distribution of the frozen application without applying GPL to its application code.
- MSVC runtime libraries, when bundled by PyInstaller, retain Microsoft's applicable redistributable terms; Windows system components are not part of this project's MIT code.

### Corresponding dependency sources

Unmodified dependency sources and build information are published by their maintainers at:

- https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.12.0-src/
- https://download.qt.io/official_releases/qt/6.12/6.12.0/submodules/
- https://github.com/qt/pyside-pyside-setup/tree/v6.12.0
- https://github.com/qt/qtbase/tree/v6.12.0
- https://github.com/python/cpython/tree/v3.13.7
- https://github.com/pyinstaller/pyinstaller/tree/v6.22.3

The release maintainer must retain and provide the corresponding library sources alongside binary downloads as required by the applicable licenses. A link to this project's MIT source alone is not a substitute for dependency-source obligations. See docs/RELEASE_PREPARATION.md before public distribution.
