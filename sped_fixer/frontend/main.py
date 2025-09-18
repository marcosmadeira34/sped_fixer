import sys
import os
import requests
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QLineEdit, QTextEdit, QFileDialog, 
    QVBoxLayout, QHBoxLayout, QGroupBox, QMessageBox, QFrame, QSplitter
)
from PySide6.QtGui import QFont, QColor, QTextCharFormat, QTextCursor, QPalette, QIcon
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView

API_URL = "http://localhost:8001/fix-sped/"

class ModernSPEDComparatorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SPED  Pro")
        self.resize(1200, 800)
        self.setMinimumSize(1000, 700)
     
        # Variáveis de controle
        self.file1_path = ""
        self.file2_path = ""
        
        # Paleta de cores moderna
        self.setup_palette()
        
        # Criar interface
        self.create_widgets()
        
    def setup_palette(self):
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor("#f8f9fa"))
        palette.setColor(QPalette.WindowText, QColor("#212529"))
        palette.setColor(QPalette.Base, QColor("#ffffff"))
        palette.setColor(QPalette.AlternateBase, QColor("#f1f3f5"))
        palette.setColor(QPalette.ToolTipBase, QColor("#ffffff"))
        palette.setColor(QPalette.ToolTipText, QColor("#212529"))
        palette.setColor(QPalette.Text, QColor("#212529"))
        palette.setColor(QPalette.Button, QColor("#e9ecef"))
        palette.setColor(QPalette.ButtonText, QColor("#212529"))
        palette.setColor(QPalette.BrightText, QColor("#000000"))
        palette.setColor(QPalette.Link, QColor("#0066cc"))
        palette.setColor(QPalette.Highlight, QColor("#0066cc"))
        palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
        self.setPalette(palette)

    def create_widgets(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(20)

        # Cabeçalho moderno
        header_layout = QHBoxLayout()
        
        # Logo e título
        title_group = QVBoxLayout()
        title = QLabel("SPED - ICMS/IPI")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setStyleSheet("color: #0066cc;")
        
        subtitle = QLabel("Análise avançada de arquivos fiscais")
        subtitle.setFont(QFont("Segoe UI", 10))
        subtitle.setStyleSheet("color: #6c757d;")
        
        title_group.addWidget(title)
        title_group.addWidget(subtitle)
        header_layout.addLayout(title_group)
        header_layout.addStretch()
        
        # Indicador de status
        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(12, 12)
        self.status_indicator.setStyleSheet("background-color: #28a745; border-radius: 6px;")
        header_layout.addWidget(self.status_indicator)
        
        self.status_label = QLabel("Pronto para uso")
        self.status_label.setFont(QFont("Segoe UI", 9))
        header_layout.addWidget(self.status_label)
        
        main_layout.addLayout(header_layout)
        
        # Linha divisória
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Sunken)
        divider.setStyleSheet("background-color: #dee2e6;")
        main_layout.addWidget(divider)

        # Área principal com splitter
        main_splitter = QSplitter(Qt.Vertical)
        main_splitter.setHandleWidth(2)
        main_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #dee2e6;
            }
            QSplitter::handle:hover {
                background-color: #adb5bd;
            }
        """)
        
        # Seção de arquivos
        files_widget = QWidget()
        files_layout = QVBoxLayout(files_widget)
        files_layout.setContentsMargins(0, 0, 0, 0)
        
        file_group = QGroupBox("Seleção de Arquivos")
        file_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 12px;
                background-color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px 0 4px;
                color: #495057;
            }
        """)
        file_layout = QVBoxLayout()
        file_layout.setSpacing(16)

        # Arquivo 1
        file1_layout = QHBoxLayout()
        file1_label = QLabel("SPED Cliente:")
        file1_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        file1_label.setMinimumWidth(100)
        
        self.file1_edit = QLineEdit()
        self.file1_edit.setPlaceholderText("Clique para selecionar o arquivo...")
        self.file1_edit.setStyleSheet("""
            QLineEdit {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 8px 12px;
                background-color: #f8f9fa;
                font-size: 9pt;
            }
            QLineEdit:focus {
                border: 1px solid #0066cc;
                background-color: #ffffff;
            }
        """)
        
        file1_btn = QPushButton("Procurar")
        file1_btn.setCursor(Qt.PointingHandCursor)
        file1_btn.setStyleSheet("""
            QPushButton {
                background-color: #0066cc;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #0052a3;
            }
            QPushButton:pressed {
                background-color: #004080;
            }
        """)
        file1_btn.clicked.connect(lambda: self.browse_file(1))
        
        file1_layout.addWidget(file1_label)
        file1_layout.addWidget(self.file1_edit)
        file1_layout.addWidget(file1_btn)
        file_layout.addLayout(file1_layout)

        # Arquivo 2
        file2_layout = QHBoxLayout()
        file2_label = QLabel("SPED Contabilidade:")
        file2_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        file2_label.setMinimumWidth(100)
        
        self.file2_edit = QLineEdit()
        self.file2_edit.setPlaceholderText("Clique para selecionar o arquivo...")
        self.file2_edit.setStyleSheet(self.file1_edit.styleSheet())
        
        file2_btn = QPushButton("Procurar")
        file2_btn.setCursor(Qt.PointingHandCursor)
        file2_btn.setStyleSheet(file1_btn.styleSheet())
        file2_btn.clicked.connect(lambda: self.browse_file(2))
        
        file2_layout.addWidget(file2_label)
        file2_layout.addWidget(self.file2_edit)
        file2_layout.addWidget(file2_btn)
        file_layout.addLayout(file2_layout)

        file_group.setLayout(file_layout)
        files_layout.addWidget(file_group)
        
        # Botões de ação
        action_layout = QHBoxLayout()
        action_layout.setSpacing(12)
        
        self.compare_btn = QPushButton("Comparar Arquivos")
        self.compare_btn.setCursor(Qt.PointingHandCursor)
        self.compare_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)
        self.compare_btn.clicked.connect(self.compare_files)
        
        self.generate_btn = QPushButton("Gerar Arquivo Corrigido")
        self.generate_btn.setCursor(Qt.PointingHandCursor)
        self.generate_btn.setEnabled(False)
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #138496;
            }
            QPushButton:pressed {
                background-color: #117a8b;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.generate_btn.clicked.connect(self.generate_corrected_file)
        
        self.clear_btn = QPushButton("Limpar Logs")
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:pressed {
                background-color: #545b62;
            }
        """)
        self.clear_btn.clicked.connect(self.clear_logs)

        # NOVO BOTÃO DE IMPRESSÃO
        self.download_btn = QPushButton("Baixar Logs")
        self.download_btn.setCursor(Qt.PointingHandCursor)
        self.download_btn.setStyleSheet(self.clear_btn.styleSheet())  # Mesmo estilo do botão Limpar
        self.download_btn.clicked.connect(self.download_logs)

        action_layout.addWidget(self.compare_btn)
        action_layout.addWidget(self.generate_btn)
        action_layout.addWidget(self.clear_btn)
        action_layout.addWidget(self.download_btn)  # Adicione esta linha
        action_layout.addStretch()
        
        files_layout.addLayout(action_layout)
        
        main_splitter.addWidget(files_widget)
        
        # Área de logs com destaque
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        log_layout.setContentsMargins(0, 0, 0, 0)
        
        log_header = QHBoxLayout()
        log_title = QLabel("Logs de Comparação")
        log_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        log_title.setStyleSheet("color: #343a40;")
        
        log_options = QHBoxLayout()
        log_options.addStretch()
        
        self.log_table = QTableWidget()
        self.log_table.setColumnCount(6)
        self.log_table.setHorizontalHeaderLabels(["Arquivo", "Linha", "Registro", "Regra", "Mensagem", "Sugestão"])
        self.log_table.horizontalHeader().setStretchLastSection(True)
        self.log_table.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                background-color: #343a40;
                color: white;
                padding: 6px;
                border: none;
                border-right: 1px solid #212529;
                font-weight: bold;
            }
        """)
        self.log_table.verticalHeader().setVisible(False)
        self.log_table.setAlternatingRowColors(False)
        self.log_table.setStyleSheet("""
            QTableWidget {
                background-color: #212529;
                color: #f8f9fa;
                border: 1px solid #343a40;
                border-radius: 6px;
                gridline-color: #343a40;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 9pt;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #343a40;
            }
            QTableWidget::item:selected {
                background-color: #0066cc;
            }
            QScrollBar:vertical {
                background: #343a40;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #6c757d;
                border-radius: 6px;
                min-height: 20px;
            }
        """)

        # Configure as colunas para terem larguras adequadas
        self.log_table.setColumnWidth(0, 200)  # Arquivo
        self.log_table.setColumnWidth(1, 60)   # Linha
        self.log_table.setColumnWidth(2, 80)   # Registro
        self.log_table.setColumnWidth(3, 80)   # Regra
        self.log_table.setColumnWidth(4, 300)  # Mensagem
        self.log_table.setColumnWidth(5, 300)  # Sugestão

        log_layout.addWidget(self.log_table, 1)
        
        main_splitter.addWidget(log_widget)
        main_splitter.setSizes([300, 500])  # 30% para arquivos, 70% para logs
        
        main_layout.addWidget(main_splitter, 1)

    def browse_file(self, file_num):
        filename, _ = QFileDialog.getOpenFileName(
            self, f"Selecione o arquivo {file_num}", "", 
            "Arquivos SPED (*.txt *.sped);;Todos os arquivos (*)"
        )
        if filename:
            if file_num == 1:
                self.file1_path = filename
                self.file1_edit.setText(filename)
            else:
                self.file2_path = filename
                self.file2_edit.setText(filename)
            
            self.status_label.setText(f"Arquivo {file_num} selecionado: {os.path.basename(filename)}")
            self.status_indicator.setStyleSheet("background-color: #ffc107;")

    def compare_files(self):
        if not self.file1_path or not self.file2_path:
            QMessageBox.critical(self, "Erro", "Selecione ambos os arquivos para comparação!")
            return

        try:
            self.status_label.setText("Comparando arquivos via API...")
            self.status_indicator.setStyleSheet("background-color: #17a2b8;")

            with open(self.file1_path, "rb") as file1, open(self.file2_path, "rb") as file2:
                files = [
                    ("files", file1),
                    ("files", file2)
                ]
                data = {"sped_type": "fiscal"}
                response = requests.post(API_URL, files=files, data=data)

            if response.status_code != 200:
                raise Exception(f"Erro na API: {response.text}")

            result = response.json()
            self.display_log(result)
            self.generate_btn.setEnabled(True)
            self.status_label.setText("Comparação concluída!")
            self.status_indicator.setStyleSheet("background-color: #28a745;")

        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha na comparação: {str(e)}")
            self.status_label.setText("Erro na comparação")
            self.status_indicator.setStyleSheet("background-color: #dc3545;")

    def display_log(self, api_response):
        self.log_table.setRowCount(0)  # Limpa a tabela
        total_changed = 0

        # Linha de título do relatório
        self.log_table.insertRow(0)
        self.log_table.setItem(0, 0, QTableWidgetItem("RELATÓRIO DE COMPARAÇÃO"))
        self.log_table.setSpan(0, 0, 1, 6)

        header_item = self.log_table.item(0, 0)
        header_item.setTextAlignment(Qt.AlignCenter)
        header_item.setBackground(QColor("#212529"))
        header_item.setForeground(QColor("#ffffff"))
        header_item.setFont(QFont("Segoe UI", 10, QFont.Bold))

        row = 1  # começa depois do cabeçalho

        for file_info in api_response.get("files", []):
            # Caso de COMPARAÇÃO (similaridade + divergências)
            if "similarity" in file_info and "divergences" in file_info:
                similarity = file_info.get("similarity", 0)
                divergences = file_info.get("divergences", [])

                # Linha com a similaridade
                self.log_table.insertRow(row)
                self.log_table.setItem(row, 0, QTableWidgetItem(f"Similaridade: {similarity}%"))
                self.log_table.setSpan(row, 0, 1, 6)
                self.log_table.item(row, 0).setForeground(QColor("#00ff99"))
                row += 1

                # Divergências
                for d in divergences:
                    self.log_table.insertRow(row)
                    self.log_table.setItem(row, 0, QTableWidgetItem("Comparação"))
                    self.log_table.setItem(row, 1, QTableWidgetItem(str(d.get("line_no", ""))))
                    self.log_table.setItem(row, 2, QTableWidgetItem(str(d.get("reg", ""))))
                    self.log_table.setItem(row, 3, QTableWidgetItem(""))  # sem regra
                    self.log_table.setItem(row, 4, QTableWidgetItem(str(d.get("value_a", ""))))
                    self.log_table.setItem(row, 5, QTableWidgetItem(str(d.get("value_b", ""))))
                    row += 1

            # Caso de CORREÇÃO (erros por arquivo)
            else:
                file_name = str(file_info.get("original_name", "Desconhecido"))
                sped_type = str(file_info.get("sped_type", ""))
                issues = file_info.get("issues", [])

                # Cabeçalho do arquivo
                self.log_table.insertRow(row)
                self.log_table.setItem(row, 0, QTableWidgetItem(f"{file_name} ({sped_type})"))
                self.log_table.setSpan(row, 0, 1, 6)

                file_header_item = self.log_table.item(row, 0)
                file_header_item.setBackground(QColor("#212529"))
                file_header_item.setForeground(QColor("#ffffff"))
                file_header_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
                row += 1

                if not issues:  # caso sem problemas
                    self.log_table.insertRow(row)
                    self.log_table.setItem(row, 0, QTableWidgetItem("Nenhuma inconsistência encontrada"))
                    self.log_table.setSpan(row, 0, 1, 6)

                    no_issues_item = self.log_table.item(row, 0)
                    no_issues_item.setBackground(QColor("#212529"))
                    no_issues_item.setForeground(QColor("#ffffff"))
                    row += 1
                else:
                    for issue in issues:
                        line = str(issue.get("line_no", ""))
                        reg = str(issue.get("reg", ""))
                        rule = str(issue.get("rule_id", ""))
                        msg = str(issue.get("message", ""))
                        suggestion = str(issue.get("suggestion", ""))

                        self.log_table.insertRow(row)

                        self.log_table.setItem(row, 0, QTableWidgetItem(file_name))
                        self.log_table.setItem(row, 1, QTableWidgetItem(line))
                        self.log_table.setItem(row, 2, QTableWidgetItem(reg))
                        self.log_table.setItem(row, 3, QTableWidgetItem(rule))
                        self.log_table.setItem(row, 4, QTableWidgetItem(msg))
                        self.log_table.setItem(row, 5, QTableWidgetItem(suggestion))

                        # Formata cores
                        for col in range(6):
                            item = self.log_table.item(row, col)
                            item.setBackground(QColor("#212529"))

                            if col == 4:  # mensagem em vermelho
                                item.setForeground(QColor("#ff5555"))
                            else:
                                item.setForeground(QColor("#ffffff"))

                            if col == 1:  # coluna linha centralizada
                                item.setTextAlignment(Qt.AlignCenter)

                        total_changed += 1
                        row += 1

                # Linha em branco entre arquivos
                self.log_table.insertRow(row)
                blank_item = QTableWidgetItem("")
                blank_item.setBackground(QColor("#212529"))
                self.log_table.setItem(row, 0, blank_item)
                self.log_table.setSpan(row, 0, 1, 6)
                row += 1

        # Linha de resumo final
        self.log_table.insertRow(row)
        self.log_table.setItem(row, 0, QTableWidgetItem(f"RESUMO: Alterados: {total_changed}"))
        self.log_table.setSpan(row, 0, 1, 6)

        summary_item = self.log_table.item(row, 0)
        summary_item.setTextAlignment(Qt.AlignCenter)
        summary_item.setBackground(QColor("#212529"))
        summary_item.setForeground(QColor("#ffffff"))
        summary_item.setFont(QFont("Segoe UI", 10, QFont.Bold))

        

    def generate_corrected_file(self):
        if not self.file1_path or not self.file2_path:
            QMessageBox.critical(self, "Erro", "Selecione ambos os arquivos primeiro!")
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self, "Salvar Arquivo Corrigido", "", "Arquivos SPED (*.txt);;Todos os arquivos (*)"
        )
        if save_path:
            try:
                with open(self.file1_path, "r", encoding="latin-1") as src, open(save_path, "w", encoding="latin-1") as dst:
                    dst.write(src.read())
                
                self.log_text.append(f"""
                <div style="background-color: #28a745; color: white; padding: 8px 12px; 
                            border-radius: 4px; margin-top: 16px;">
                    Arquivo corrigido salvo em: {save_path}
                </div>
                """)
                
                self.status_label.setText(f"Arquivo salvo: {os.path.basename(save_path)}")
                self.status_indicator.setStyleSheet("background-color: #28a745;")
                QMessageBox.information(self, "Sucesso", "Arquivo corrigido gerado com sucesso!")
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Falha ao gerar arquivo: {str(e)}")
                self.status_label.setText("Erro ao gerar arquivo")
                self.status_indicator.setStyleSheet("background-color: #dc3545;")

    def download_logs(self):
        """Salva o conteúdo dos logs em um arquivo TXT"""
        if self.log_table.rowCount() == 0:
            QMessageBox.warning(self, "Aviso", "Não há logs para baixar!")
            return
        
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Salvar Logs", "", "Arquivos de Texto (*.txt);;Todos os arquivos (*)"
        )
        
        if save_path:
            try:
                with open(save_path, "w", encoding="utf-8") as f:
                    # Cabeçalho
                    f.write("RELATÓRIO DE COMPARAÇÃO\n")
                    f.write("=" * 80 + "\n\n")
                    
                    # Itera sobre as linhas da tabela
                    row = 0
                    while row < self.log_table.rowCount():
                        # Verifica se é uma linha mesclada (cabeçalho)
                        if self.log_table.columnSpan(row, 0) > 1:
                            item = self.log_table.item(row, 0)
                            f.write(item.text() + "\n")
                        else:
                            # Linha normal com dados
                            file_item = self.log_table.item(row, 0)
                            line_item = self.log_table.item(row, 1)
                            reg_item = self.log_table.item(row, 2)
                            rule_item = self.log_table.item(row, 3)
                            msg_item = self.log_table.item(row, 4)
                            suggestion_item = self.log_table.item(row, 5)
                            
                            f.write(f"Arquivo: {file_item.text()}\n")
                            f.write(f"Linha: {line_item.text()}\n")
                            f.write(f"Registro: {reg_item.text()}\n")
                            f.write(f"Regra: {rule_item.text()}\n")
                            f.write(f"Mensagem: {msg_item.text()}\n")
                            f.write(f"Sugestão: {suggestion_item.text()}\n")
                            f.write("-" * 80 + "\n")
                        
                        row += 1
                    
                    f.write("\n" + "=" * 80 + "\n")
                
                self.status_label.setText(f"Logs salvos em: {os.path.basename(save_path)}")
                self.status_indicator.setStyleSheet("background-color: #28a745;")
                QMessageBox.information(self, "Sucesso", "Logs baixados com sucesso!")
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Falha ao salvar logs: {str(e)}")
                self.status_label.setText("Erro ao salvar logs")
                self.status_indicator.setStyleSheet("background-color: #dc3545;")
    
    def clear_logs(self):
        self.log_table.setRowCount(0)  # Limpa todas as linhas da tabela
        self.status_label.setText("Logs limpos")
        self.status_indicator.setStyleSheet("background-color: #6c757d;")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = ModernSPEDComparatorApp()
    window.show()
    sys.exit(app.exec())