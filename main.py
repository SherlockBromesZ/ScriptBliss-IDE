import sys
import os
import subprocess
from PyQt5.QtWidgets import (QMainWindow, QApplication, QAction, QFileDialog, QMessageBox, QLabel,
                             QTextEdit, QVBoxLayout, QWidget, QSplitter, QTreeView, QFileSystemModel, QInputDialog, QTabWidget)
from PyQt5.QtGui import QIcon, QColor, QPalette, QFont, QBrush, QFontMetrics, QPixmap,QDesktopServices
from PyQt5.QtCore import Qt, QDir, QProcess, QModelIndex, QTimer, QUrl
from PyQt5.Qsci import (QsciScintilla, QsciLexerPython, QsciLexerJava, QsciLexerHTML, QsciLexerJavaScript,
                        QsciLexerCSS, QsciLexerCPP, QsciLexerRuby)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.currentFile = ''
        self.projectPath = QDir.currentPath()
        self.process = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle("ScriptBliss")
        self.setWindowIcon(QIcon('logo.png'))
        self.setGeometry(100, 100, 1200, 800)
        self.showMaximized()

        # Set dark blue theme similar to VSCode
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(30, 30, 60))
        dark_palette.setColor(QPalette.WindowText, QColor("#e0e0ff"))
        dark_palette.setColor(QPalette.Base, QColor(20, 20, 40))
        dark_palette.setColor(QPalette.AlternateBase, QColor(40, 40, 60))
        dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
        dark_palette.setColor(QPalette.ToolTipText, Qt.white)
        dark_palette.setColor(QPalette.Text, QColor("#e0e0ff"))
        dark_palette.setColor(QPalette.Button, QColor(45, 45, 70))
        dark_palette.setColor(QPalette.ButtonText, QColor("#e0e0ff"))
        dark_palette.setColor(QPalette.BrightText, Qt.red)
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, Qt.black)
        self.setPalette(dark_palette)

        # Editor setup
        self.editor = QsciScintilla()
        self.editor.setUtf8(True)
        self.editor.setCaretForegroundColor(QColor("#ffffff"))

        # Font
        font = QFont()
        font.setFamily('Consolas')
        font.setFixedPitch(True)
        font.setPointSize(10)
        self.editor.setFont(font)
        self.editor.setMarginsFont(font)

        # Margin 0 is used for line numbers
        fontmetrics = QFontMetrics(font)
        self.editor.setMarginsFont(font)
        self.editor.setMarginWidth(0, fontmetrics.width("00000") + 6)
        self.editor.setMarginLineNumbers(0, True)
        self.editor.setMarginsBackgroundColor(QColor("#1e1e3e"))
        self.editor.setMarginsForegroundColor(QColor("#ffffff"))

        # Brace matching: enable for a LISP-like experience
        self.editor.setBraceMatching(QsciScintilla.SloppyBraceMatch)

        # Current line visible with special background color
        self.editor.setCaretLineVisible(True)
        self.editor.setCaretLineBackgroundColor(QColor("#dee8ff"))

        # Set Python lexer as default
        lexer = QsciLexerPython()
        lexer.setDefaultFont(font)
        self.editor.setLexer(lexer)

        # Explorer setup
        self.fileSystemModel = QFileSystemModel()
        self.fileSystemModel.setRootPath(self.projectPath)

        self.treeView = QTreeView()
        self.treeView.setModel(self.fileSystemModel)
        self.treeView.setRootIndex(self.fileSystemModel.index(self.projectPath))
        self.treeView.clicked.connect(self.onFileClicked)
        self.treeView.setHeaderHidden(True)
        self.treeView.setIndentation(10)

        # Set the width of the tree view and make it non-resizable
        self.treeView.setMinimumWidth(200)
        self.treeView.setMaximumWidth(200)

        # Console and output
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFont(font)
        self.console.setStyleSheet("background-color: #00091a; color: #c9dcff;")

        # Terminal integrado
        self.terminal = QTextEdit()
        self.terminal.setReadOnly(False)
        self.terminal.setFont(font)
        self.terminal.setStyleSheet("background-color: #00092a; color: #c9dcff;")
        self.terminal.keyPressEvent = self.terminalKeyPressEvent

        # Tab Widget for Output and Terminal
        self.bottomTabWidget = QTabWidget()
        self.bottomTabWidget.addTab(self.console, "Output")
        self.bottomTabWidget.addTab(self.terminal, "Terminal")
        self.bottomTabWidget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #1e1e3e;
                background-color: #1e1e3e;
            }
            QTabBar::tab {
                background-color: #1e1e3e;
                color: #e0e0ff;
                padding: 5px;
                border: 1px solid #1e1e3e;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background-color: #2e2e5e;
                border: 1px solid #2e2e5e;
                border-bottom: 1px solid #1e1e3e;
            }
            QTabBar::tab:hover {
                background-color: #2e2e5e;
            }
        """)

        # Layout setup
        splitter1 = QSplitter(Qt.Horizontal)
        splitter1.addWidget(self.treeView)
        splitter1.addWidget(self.editor)
        splitter1.setSizes([200, 1000])
        splitter1.setHandleWidth(0)  # Remove the handle to make it non-resizable

        splitter2 = QSplitter(Qt.Vertical)
        splitter2.addWidget(splitter1)
        splitter2.addWidget(self.bottomTabWidget)
        splitter2.setSizes([580, 200])
        splitter2.setHandleWidth(0)  # Remove the handle to make it non-resizable

        self.setCentralWidget(splitter2)

        self.setupMenuBar()

        # Auto-save timer
        self.autoSaveTimer = QTimer(self)
        self.autoSaveTimer.timeout.connect(self.autoSave)
        self.autoSaveTimer.start(30000)  # Auto-save a cada 30 segundos

    def setupMenuBar(self):
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #1e1e3e;
                color: #e0e0ff;
            }
            QMenuBar::item {
                background-color: #1e1e3e;
                color: #e0e0ff;
            }
            QMenuBar::item:selected {
                background-color: #2e2e5e;
            }
            QMenu {
                background-color: #1e1e3e;
                color: #e0e0ff;
            }
            QMenu::item:selected {
                background-color: #2e2e5e;
            }
        """)
        fileMenu = menubar.addMenu('&File')
        runMenu = menubar.addMenu('&Run')
        gitMenu = menubar.addMenu('&Git')
        compilerMenu = menubar.addMenu('&Compilers')

        newFile = QAction(QIcon('new.png'), 'New', self)
        newFile.setShortcut('Ctrl+N')
        newFile.setStatusTip('Create new file')
        newFile.triggered.connect(self.newFile)

        openFile = QAction(QIcon('open.png'), 'Open', self)
        openFile.setShortcut('Ctrl+O')
        openFile.setStatusTip('Open existing file')
        openFile.triggered.connect(self.openFileDialog)

        openFolder = QAction(QIcon('folder.png'), 'Open Folder', self)
        openFolder.setShortcut('Ctrl+Shift+O')
        openFolder.setStatusTip('Open folder as project')
        openFolder.triggered.connect(self.openFolderDialog)

        saveFile = QAction(QIcon('save.png'), 'Save', self)
        saveFile.setShortcut('Ctrl+S')
        saveFile.setStatusTip('Save current file')
        saveFile.triggered.connect(self.saveFileDialog)

        runAction = QAction(QIcon('run.png'), 'Run Code', self)
        runAction.setShortcut('Ctrl+R')
        runAction.setStatusTip('Run Code')
        runAction.triggered.connect(self.runCode)

        gitCommit = QAction(QIcon('commit.png'), 'Commit', self)
        gitCommit.setStatusTip('Commit changes')
        gitCommit.triggered.connect(self.gitCommit)

        gitPush = QAction(QIcon('push.png'), 'Push', self)
        gitPush.setStatusTip('Push changes')
        gitPush.triggered.connect(self.gitPush)

        gitPull = QAction(QIcon('pull.png'), 'Pull', self)
        gitPull.setStatusTip('Pull changes')
        gitPull.triggered.connect(self.gitPull)

        fileMenu.addAction(newFile)
        fileMenu.addAction(openFile)
        fileMenu.addAction(openFolder)
        fileMenu.addAction(saveFile)
        runMenu.addAction(runAction)
        gitMenu.addAction(gitCommit)
        gitMenu.addAction(gitPush)
        gitMenu.addAction(gitPull)

        # Compilers Menu
        pythonCompiler = QAction(QIcon('python.png'),'Python', self)
        pythonCompiler.setStatusTip('Download Python Compiler')
        pythonCompiler.triggered.connect(lambda: QDesktopServices.openUrl(QUrl('https://www.python.org/downloads/')))

        javaCompiler = QAction(QIcon('java.png'),'Java', self)
        javaCompiler.setStatusTip('Download Java Compiler')
        javaCompiler.triggered.connect(lambda: QDesktopServices.openUrl(QUrl('https://www.oracle.com/java/technologies/javase-jdk11-downloads.html')))

        cppCompiler = QAction(QIcon('cpp.png'),'C++', self)
        cppCompiler.setStatusTip('Download C++ Compiler')
        cppCompiler.triggered.connect(lambda: QDesktopServices.openUrl(QUrl('https://www.mingw-w64.org/downloads/')))

        rubyCompiler = QAction(QIcon('ruby.png'),'Ruby', self)
        rubyCompiler.setStatusTip('Download Ruby Compiler')
        rubyCompiler.triggered.connect(lambda: QDesktopServices.openUrl(QUrl('https://www.ruby-lang.org/en/downloads/')))

        phpCompiler = QAction(QIcon('php.png'),'PHP', self)
        phpCompiler.setStatusTip('Download PHP Compiler')
        phpCompiler.triggered.connect(lambda: QDesktopServices.openUrl(QUrl('https://www.php.net/downloads')))

        htmlEditor = QAction(QIcon('html.png'),'HTML Editor', self)
        htmlEditor.setStatusTip('Download HTML Editor')
        htmlEditor.triggered.connect(lambda: QDesktopServices.openUrl(QUrl('https://code.visualstudio.com/')))

        compilerMenu.addAction(pythonCompiler)
        compilerMenu.addAction(javaCompiler)
        compilerMenu.addAction(cppCompiler)
        compilerMenu.addAction(rubyCompiler)
        compilerMenu.addAction(phpCompiler)
        compilerMenu.addAction(htmlEditor)

    def newFile(self):
        text, ok = QInputDialog.getText(self, 'New File', 'Enter file name:')
        if ok and text:
            self.currentFile = os.path.join(self.projectPath, text)
            with open(self.currentFile, 'w') as f:
                f.write('')
            self.editor.setText("")
            self.setWindowTitle(f"ScriptBliss - {self.currentFile}")
            self.treeView.setRootIndex(self.fileSystemModel.index(self.projectPath))

    def openFileDialog(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(self, "Open File", self.projectPath,
                                                  "All Files (*);;Python Files (*.py);;Java Files (*.java);;HTML Files (*.html);;JavaScript Files (*.js);;CSS Files (*.css);;C++ Files (*.cpp);;Ruby Files (*.rb);;Image Files (*.png *.jpg *.jpeg *.bmp *.gif)", options=options)
        if fileName:
            self.loadFile(fileName)

    def openFolderDialog(self):
        folder = QFileDialog.getExistingDirectory(self, "Open Folder", QDir.currentPath())
        if folder:
            self.projectPath = folder
            self.fileSystemModel.setRootPath(folder)
            self.treeView.setRootIndex(self.fileSystemModel.index(folder))

    def loadFile(self, fileName):
        self.currentFile = fileName
        if fileName.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
            self.displayImage(fileName)
        else:
            with open(fileName, 'r') as f:
                code = f.read()
                self.editor.setText(code)
                self.setWindowTitle(f"ScriptBliss - {fileName}")

            # Set the appropriate lexer based on the file extension
            if fileName.endswith('.py'):
                lexer = QsciLexerPython()
            elif fileName.endswith('.java'):
                lexer = QsciLexerJava()
            elif fileName.endswith('.html'):
                lexer = QsciLexerHTML()
            elif fileName.endswith('.js'):
                lexer = QsciLexerJavaScript()
            elif fileName.endswith('.css'):
                lexer = QsciLexerCSS()
            elif fileName.endswith('.cpp'):
                lexer = QsciLexerCPP()
            elif fileName.endswith('.rb'):
                lexer = QsciLexerRuby()
            else:
                lexer = None

            if lexer:
                lexer.setDefaultFont(QFont("Consolas", 10))
                self.editor.setLexer(lexer)

    def displayImage(self, fileName):
        pixmap = QPixmap(fileName)
        imageWidget = QLabel()
        imageWidget.setPixmap(pixmap)
        imageWidget.setAlignment(Qt.AlignCenter)
        imageWidget.setStyleSheet("background-color: #1e1e3e;")
        self.setCentralWidget(imageWidget)

    def saveFileDialog(self):
        if self.currentFile:
            fileName = self.currentFile
        else:
            options = QFileDialog.Options()
            fileName, _ = QFileDialog.getSaveFileName(self, "Save File", self.projectPath,
                                                      "All Files (*);;Python Files (*.py);;Java Files (*.java);;HTML Files (*.html);;JavaScript Files (*.js);;CSS Files (*.css);;C++ Files (*.cpp);;Ruby Files (*.rb)", options=options)
        if fileName:
            with open(fileName, 'w') as f:
                code = self.editor.text()
                f.write(code)
            self.currentFile = fileName
            self.setWindowTitle(f"ScriptBliss - {fileName}")

    def autoSave(self):
        if self.currentFile:
            with open(self.currentFile, 'w') as f:
                code = self.editor.text()
                f.write(code)

    def runCode(self):
        if self.currentFile:
            # Limpar a saída e o terminal antes de executar o código
            self.console.clear()
            self.terminal.clear()

            if self.currentFile.endswith('.py'):
                command = f'python "{self.currentFile}"'
            elif self.currentFile.endswith('.java'):
                # Compilation
                compile_command = f'javac "{self.currentFile}"'
                self.process = QProcess()
                self.process.start(compile_command)
                self.process.waitForFinished()
                compile_output = self.process.readAllStandardOutput().data().decode()
                compile_error = self.process.readAllStandardError().data().decode()

                if compile_error:
                    self.console.append(compile_error)
                    return

                # Execution
                class_name = os.path.splitext(os.path.basename(self.currentFile))[0]
                run_command = f'java -cp "{os.path.dirname(self.currentFile)}" {class_name}'
                self.process = QProcess()
                self.process.setProcessChannelMode(QProcess.MergedChannels)
                self.process.readyReadStandardOutput.connect(self.updateConsoleOutput)
                self.process.readyReadStandardError.connect(self.updateConsoleOutput)
                self.process.start(run_command)
            elif self.currentFile.endswith('.cpp'):
                executable = self.currentFile[:-4]  # Remove a extensão .cpp
                compile_command = f'g++ "{self.currentFile}" -o "{executable}"'
                run_command = f'"{executable}"'
                self.process = QProcess()
                self.process.setProcessChannelMode(QProcess.MergedChannels)
                self.process.readyReadStandardOutput.connect(self.updateConsoleOutput)
                self.process.readyReadStandardError.connect(self.updateConsoleOutput)

                # Compilar
                self.process.start(compile_command)
                self.process.waitForFinished()
                compile_output = self.process.readAllStandardOutput().data().decode()
                compile_error = self.process.readAllStandardError().data().decode()

                if compile_error:
                    self.console.append(compile_error)
                    return

                # Executar
                self.process.start(run_command)
            elif self.currentFile.endswith('.rb'):
                command = f'ruby "{self.currentFile}"'
                self.process = QProcess()
                self.process.setProcessChannelMode(QProcess.MergedChannels)
                self.process.readyReadStandardOutput.connect(self.updateConsoleOutput)
                self.process.readyReadStandardError.connect(self.updateConsoleOutput)
                self.process.start(command)
            elif self.currentFile.endswith('.php'):
                command = f'php "{self.currentFile}"'
                self.process = QProcess()
                self.process.setProcessChannelMode(QProcess.MergedChannels)
                self.process.readyReadStandardOutput.connect(self.updateConsoleOutput)
                self.process.readyReadStandardError.connect(self.updateConsoleOutput)
                self.process.start(command)
            elif self.currentFile.endswith('.html') or self.currentFile.endswith('.js'):
                self.console.append("Cannot run HTML or JavaScript files directly.")
                return
            else:
                self.console.append("Unsupported file format for direct execution.")
                return

            self.bottomTabWidget.setCurrentIndex(0)  # Switch to Output tab

    def updateConsoleOutput(self):
        output = self.process.readAllStandardOutput().data().decode()
        error = self.process.readAllStandardError().data().decode()
        self.console.append(output + error)

    def gitCommit(self):
        message, ok = QInputDialog.getText(self, 'Git Commit', 'Enter commit message:')
        if ok and message:
            process = QProcess()
            process.start(f'git commit -am "{message}"')
            process.waitForFinished()
            output = process.readAllStandardOutput().data().decode()
            error = process.readAllStandardError().data().decode()
            self.console.append(output + '\n' + error)

    def gitPush(self):
        process = QProcess()
        process.start('git push')
        process.waitForFinished()
        output = process.readAllStandardOutput().data().decode()
        error = process.readAllStandardError().data().decode()
        self.console.append(output + '\n' + error)

    def gitPull(self):
        process = QProcess()
        process.start('git pull')
        process.waitForFinished()
        output = process.readAllStandardOutput().data().decode()
        error = process.readAllStandardError().data().decode()
        self.console.append(output + '\n' + error)

    def onFileClicked(self, index):
        if not self.fileSystemModel.isDir(index):
            fileName = self.fileSystemModel.filePath(index)
            self.loadFile(fileName)

    def terminalKeyPressEvent(self, event):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            command = self.terminal.toPlainText().splitlines()[-1]
            if self.process and self.process.state() == QProcess.Running:
                self.process.write((command + '\n').encode())
                self.bottomTabWidget.setCurrentIndex(0)  # Switch to Output tab
            else:
                process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                output, error = process.communicate()
                self.terminal.append(output.decode() + error.decode())
        else:
            QTextEdit.keyPressEvent(self.terminal, event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main = MainWindow()
    main.show()
    sys.exit(app.exec_())