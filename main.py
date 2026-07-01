import sys

from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ChatList")
        self.resize(400, 200)

        self.label = QLabel("Минимальное приложение на PyQt6")
        self.label.setStyleSheet("font-size: 16px; padding: 20px;")

        button = QPushButton("Нажми меня")
        button.clicked.connect(self.on_button_clicked)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(self.label)
        layout.addWidget(button)
        self.setCentralWidget(container)

    def on_button_clicked(self) -> None:
        self.label.setText("Кнопка нажата!")


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
