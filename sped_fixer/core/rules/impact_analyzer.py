# sped_fixer/core/rules/impact_analyzer.py

class ImpactAnalyzer:
    def __init__(self, context):
        self.context = context
        self.dependency_graph = self._build_dependency_graph()

    def _build_dependency_graph(self):
        # Mapeia dependências: C100 -> C170 -> C190 -> Bloco E (E110)
        graph = {}
        for record in self.context.records:
            if record.reg == "C100":
                graph[record] = {"children": [], "impacts": ["C170", "C190", "E110"]}
            elif record.reg == "C170":
                graph[record] = {"children": [], "impacts": ["C190", "E110"]}
            elif record.reg == "C190":
                graph[record] = {"children": [], "impacts": ["E110"]}
        return graph

    def trace_impact(self, problematic_record):
        # Retorna todos os registros afetados por um erro
        impacts = []
        queue = [problematic_record]
        visited = set()

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            impacts.append(current)

            # Adiciona filhos diretos (dependências estruturais)
            for child in self.dependency_graph.get(current, {}).get("children", []):
                if child not in visited:
                    queue.append(child)

            # Adiciona registros impactados por regra de negócio
            for impacted_reg in self.dependency_graph.get(current, {}).get("impacts", []):
                for r in self.context.records:
                    if r.reg == impacted_reg and r not in visited:
                        # Para C190/E110, verifica se está relacionado ao documento
                        if impacted_reg in ["C190", "E110"]:
                            if self._is_related_to_document(r, problematic_record):
                                queue.append(r)
                        else:
                            queue.append(r)
        return impacts

    def _is_related_to_document(self, record, problematic_record):
        """Verifica se um registro de totalização (C190/E110) está relacionado ao documento com erro"""
        if record.reg == "C190":
            # C190 tem campo com chave do documento (índice varia conforme implementação)
            try:
                doc_key_c190 = record.fields[2]  # Exemplo: índice da chave no C190
                doc_key_problem = self._get_doc_key(problematic_record)
                return doc_key_c190 == doc_key_problem
            except (IndexError, AttributeError):
                return False
        elif record.reg == "E110":
            # E110 é total geral, sempre impactado
            return True
        return False

    def _get_doc_key(self, record):
        """Extrai chave do documento de um registro C100/C170"""
        if record.reg == "C100":
            return record.fields[8]  # Chave da NFe
        elif record.reg == "C170" and hasattr(record, "parent"):
            return self._get_doc_key(record.parent)
        return None