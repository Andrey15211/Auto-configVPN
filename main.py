import sys
from PySide6.QtWidgets import QApplication
from app_gui import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Smart Split-Tunneling Wizard")
    app.setOrganizationName("SmartVPN")
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
