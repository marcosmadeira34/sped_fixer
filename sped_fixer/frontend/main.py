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

API_URL = "http://localhost:8001/compare-sped/"

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

            # Função para ler arquivo com várias codificações
            def read_file_with_fallback(file_path):
                encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'cp850']
                
                for encoding in encodings:
                    try:
                        with open(file_path, 'r', encoding=encoding) as f:
                            return f.read()
                    except UnicodeDecodeError:
                        continue
                
                # Se nenhuma codificação funcionar, lê como binário e decodifica com replace
                with open(file_path, 'rb') as f:
                    content = f.read()
                return content.decode('utf-8', errors='replace')

            # Lê o conteúdo dos arquivos
            content1 = read_file_with_fallback(self.file1_path)
            content2 = read_file_with_fallback(self.file2_path)

            # Cria arquivos em memória para enviar
            from io import BytesIO
            import io

            # Converte para bytes usando UTF-8
            file1_bytes = content1.encode('utf-8')
            file2_bytes = content2.encode('utf-8')

            # Cria objetos de arquivo em memória
            file1 = io.BytesIO(file1_bytes)
            file2 = io.BytesIO(file2_bytes)

            files = [
                ("cliente_file", file1),
                ("escritorio_file", file2)
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

        self.download_btn = QPushButton("Baixar Logs")
        self.download_btn.setCursor(Qt.PointingHandCursor)
        self.download_btn.setStyleSheet(self.clear_btn.styleSheet())
        self.download_btn.clicked.connect(self.download_logs)

        action_layout.addWidget(self.compare_btn)
        action_layout.addWidget(self.generate_btn)
        action_layout.addWidget(self.clear_btn)
        action_layout.addWidget(self.download_btn)
        action_layout.addStretch()
        
        files_layout.addLayout(action_layout)
        
        main_splitter.addWidget(files_widget)
        
        # Área de resultados (substitui a área de logs)
        self.results_widget = QWidget()
        self.results_layout = QVBoxLayout(self.results_widget)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        
        # Placeholder inicial
        self.results_placeholder = QLabel("Selecione os arquivos e clique em 'Comparar Arquivos'")
        self.results_placeholder.setAlignment(Qt.AlignCenter)
        self.results_placeholder.setStyleSheet("""
            font-size: 16px;
            color: #6c757d;
            padding: 40px;
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 6px;
        """)
        self.results_layout.addWidget(self.results_placeholder)
        
        main_splitter.addWidget(self.results_widget)
        main_splitter.setSizes([300, 500])
        
        main_layout.addWidget(main_splitter, 1)
        
    def display_log(self, api_response):
        # Limpa o layout de resultados
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Cabeçalho do relatório
        header = QLabel("RELATÓRIO DE ANÁLISE SPED")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            padding: 10px;
            background-color: #f8f9fa;
            border-bottom: 1px solid #dee2e6;
        """)
        self.results_layout.addWidget(header)
        
        # Container principal para as duas colunas
        columns_container = QWidget()
        columns_layout = QHBoxLayout(columns_container)
        columns_layout.setSpacing(20)
        
        # Coluna do Cliente
        cliente_column = QWidget()
        cliente_layout = QVBoxLayout(cliente_column)
        cliente_layout.setSpacing(10)
        
        cliente_header = QLabel("ARQUIVO DO CLIENTE")
        cliente_header.setStyleSheet("""
            font-weight: bold;
            font-size: 14px;
            padding: 8px;
            background-color: #e9ecef;
            border-radius: 4px;
        """)
        cliente_layout.addWidget(cliente_header)
        
        # Resumo do cliente
        resumo_cliente = api_response.get("resumo_impacto_cliente", {})
        resumo_cliente_text = QLabel(
            f"Problemas: {resumo_cliente.get('total_problemas', 0)}\n"
            f"Impacto: R$ {resumo_cliente.get('valor_impacto_estimado', 0):.2f}\n"
            f"Blocos: {', '.join(resumo_cliente.get('blocos_afetados', []))}"
        )
        resumo_cliente_text.setStyleSheet("""
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            padding: 10px;
        """)
        cliente_layout.addWidget(resumo_cliente_text)
        
        # Registros faltantes no cliente
        only_cliente = api_response.get("comparacao_detalhada", {}).get("only_cliente", [])
        if only_cliente:
            faltantes_header = QLabel("REGISTROS FALTANTES")
            faltantes_header.setStyleSheet("""
                font-weight: bold;
                font-size: 12px;
                color: #dc3545;
                padding: 5px 0;
            """)
            cliente_layout.addWidget(faltantes_header)
            
            for reg in only_cliente:
                reg_info = reg.get("record", {})
                if isinstance(reg_info, dict):
                    reg_tipo = reg_info.get("reg", "N/A")
                    reg_linha = reg_info.get("line_no", "N/A")
                else:
                    reg_tipo = "N/A"
                    reg_linha = "N/A"
                
                impacto = reg.get("impacto", 0)
                
                reg_text = QLabel(f"{reg_tipo} - Linha: {reg_linha} - R$ {impacto:.2f}")
                reg_text.setStyleSheet("""
                    background-color: #fff5f5;
                    border: 1px solid #f5c6cb;
                    border-radius: 4px;
                    padding: 8px;
                    margin: 2px 0;
                """)
                cliente_layout.addWidget(reg_text)
        
        # Problemas do cliente
        issues_cliente = api_response.get("issues_cliente", [])
        if issues_cliente:
            problemas_header = QLabel("PROBLEMAS")
            problemas_header.setStyleSheet("""
                font-weight: bold;
                font-size: 12px;
                color: #fd7e14;
                padding: 5px 0;
            """)
            cliente_layout.addWidget(problemas_header)
            
            for issue in issues_cliente:
                issue_text = QLabel(
                    f"Linha {issue.get('line_no', '')}: {issue.get('message', '')}\n"
                    f"Sugestão: {issue.get('suggestion', '')}"
                )
                issue_text.setStyleSheet("""
                    background-color: #fff8f0;
                    border: 1px solid #ffeaa7;
                    border-radius: 4px;
                    padding: 8px;
                    margin: 2px 0;
                """)
                cliente_layout.addWidget(issue_text)
        
        cliente_layout.addStretch()
        columns_layout.addWidget(cliente_column, 1)
        
        # Coluna do Escritório
        escritorio_column = QWidget()
        escritorio_layout = QVBoxLayout(escritorio_column)
        escritorio_layout.setSpacing(10)
        
        escritorio_header = QLabel("ARQUIVO DO ESCRITÓRIO")
        escritorio_header.setStyleSheet("""
            font-weight: bold;
            font-size: 14px;
            padding: 8px;
            background-color: #e9ecef;
            border-radius: 4px;
        """)
        escritorio_layout.addWidget(escritorio_header)
        
        # Resumo do escritório
        resumo_escritorio = api_response.get("resumo_impacto_escritorio", {})
        resumo_escritorio_text = QLabel(
            f"Problemas: {resumo_escritorio.get('total_problemas', 0)}\n"
            f"Impacto: R$ {resumo_escritorio.get('valor_impacto_estimado', 0):.2f}\n"
            f"Blocos: {', '.join(resumo_escritorio.get('blocos_afetados', []))}"
        )
        resumo_escritorio_text.setStyleSheet("""
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            padding: 10px;
        """)
        escritorio_layout.addWidget(resumo_escritorio_text)
        
        # Registros excedentes no escritório
        only_escritorio = api_response.get("comparacao_detalhada", {}).get("only_escritorio", [])
        if only_escritorio:
            excedentes_header = QLabel("REGISTROS À VERIFICAR")
            excedentes_header.setStyleSheet("""
                font-weight: bold;
                font-size: 12px;
                color: #28a745;
                padding: 5px 0;
            """)
            escritorio_layout.addWidget(excedentes_header)
            
            for reg in only_escritorio:
                reg_info = reg.get("record", {})
                if isinstance(reg_info, dict):
                    reg_tipo = reg_info.get("reg", "N/A")
                    reg_linha = reg_info.get("line_no", "N/A")
                else:
                    reg_tipo = "N/A"
                    reg_linha = "N/A"
                
                impacto = reg.get("impacto", 0)
                
                reg_text = QLabel(f"{reg_tipo} - Linha: {reg_linha} - R$ {impacto:.2f}")
                reg_text.setStyleSheet("""
                    background-color: #f1fff3;
                    border: 1px solid #b8e6c1;
                    border-radius: 4px;
                    padding: 8px;
                    margin: 2px 0;
                """)
                escritorio_layout.addWidget(reg_text)
        
        # Problemas do escritório
        issues_escritorio = api_response.get("issues_escritorio", [])
        if issues_escritorio:
            problemas_header = QLabel("PROBLEMAS")
            problemas_header.setStyleSheet("""
                font-weight: bold;
                font-size: 12px;
                color: #17a2b8;
                padding: 5px 0;
            """)
            escritorio_layout.addWidget(problemas_header)
            
            for issue in issues_escritorio:
                issue_text = QLabel(
                    f"Linha {issue.get('line_no', '')}: {issue.get('message', '')}\n"
                    f"Sugestão: {issue.get('suggestion', '')}"
                )
                issue_text.setStyleSheet("""
                    background-color: #e7f5f2;
                    border: 1px solid #b2dfdb;
                    border-radius: 4px;
                    padding: 8px;
                    margin: 2px 0;
                """)
                escritorio_layout.addWidget(issue_text)
        
        escritorio_layout.addStretch()
        columns_layout.addWidget(escritorio_column, 1)
        
        self.results_layout.addWidget(columns_container)
        
        # Ações recomendadas
        acoes_recomendadas = api_response.get("acao_recomendada", [])
        if acoes_recomendadas:
            acoes_header = QLabel("AÇÕES RECOMENDADAS")
            acoes_header.setStyleSheet("""
                font-weight: bold;
                font-size: 14px;
                padding: 10px;
                background-color: #f8f9fa;
                border-top: 1px solid #dee2e6;
                margin-top: 15px;
            """)
            self.results_layout.addWidget(acoes_header)
            
            for acao in acoes_recomendadas:
                acao_text = QLabel(acao.get("descricao", ""))
                acao_text.setStyleSheet("""
                    background-color: #e9ecef;
                    border: 1px solid #ced4da;
                    border-radius: 4px;
                    padding: 10px;
                    margin: 5px 0;
                """)
                self.results_layout.addWidget(acao_text)
        
        self.results_layout.addStretch()

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
        # Limpa o layout de resultados
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Restaura o placeholder
        self.results_placeholder = QLabel("Selecione os arquivos e clique em 'Comparar Arquivos'")
        self.results_placeholder.setAlignment(Qt.AlignCenter)
        self.results_placeholder.setStyleSheet("""
            font-size: 16px;
            color: #6c757d;
            padding: 40px;
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 6px;
        """)
        self.results_layout.addWidget(self.results_placeholder)
        
        self.status_label.setText("Logs limpos")
        self.status_indicator.setStyleSheet("background-color: #6c757d;")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = ModernSPEDComparatorApp()
    window.show()
    sys.exit(app.exec())