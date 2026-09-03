from __future__ import annotations

import json
from pathlib import Path
from typing import Dict


class Cache:
    """
    Cache dos documentos do D4Sign.

    Estrutura do JSON:

    {
        "ID_DO_PROJETO": {
            "UUID_DOCUMENTO_1": true,
            "UUID_DOCUMENTO_2": true,
            "UUID_DOCUMENTO_3": false
        }
    }

    true  = documento baixado com sucesso
    false = documento ainda não foi baixado
    """

    def __init__(self, cache_file: Path):
        self.cache_file = Path(cache_file)

        self.data: Dict[str, Dict[str, bool]] = {}

        self.load()

    # =========================================================
    # CARREGAR
    # =========================================================

    def load(self) -> None:
        """
        Recarrega o cache do arquivo JSON.
        """

        if not self.cache_file.exists():
            self.data = {}
            return

        try:
            with self.cache_file.open(
                "r",
                encoding="utf-8",
            ) as file:

                data = json.load(file)

            if not isinstance(data, dict):
                self.data = {}
                return

            resultado: Dict[str, Dict[str, bool]] = {}

            for project_id, documents in data.items():

                project_id = str(project_id).strip()

                if not isinstance(documents, dict):
                    resultado[project_id] = {}
                    continue

                resultado[project_id] = {}

                for uuid, downloaded in documents.items():

                    uuid = str(uuid).strip()

                    if not uuid:
                        continue

                    resultado[project_id][uuid] = bool(
                        downloaded
                    )

            self.data = resultado

        except (
            json.JSONDecodeError,
            OSError,
            TypeError,
            ValueError,
        ):

            print(
                f"[CACHE] Não foi possível carregar: "
                f"{self.cache_file}"
            )

            self.data = {}

    # =========================================================
    # SALVAR
    # =========================================================

    def save(self) -> None:
        """
        Salva o cache no arquivo JSON.
        """

        self.cache_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary = self.cache_file.with_suffix(
            ".tmp"
        )

        with temporary.open(
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                self.data,
                file,
                ensure_ascii=False,
                indent=4,
            )

        temporary.replace(
            self.cache_file
        )

    # =========================================================
    # NORMALIZAR PROJETO
    # =========================================================

    @staticmethod
    def _project_key(project_id) -> str:
        return str(project_id).strip()

    # =========================================================
    # NORMALIZAR UUID
    # =========================================================

    @staticmethod
    def _uuid_key(uuid: str) -> str:
        return str(uuid).strip()

    # =========================================================
    # VERIFICAR STATUS
    # =========================================================

    def is_downloaded(
        self,
        project_id,
        uuid: str,
    ) -> bool:

        project = self._project_key(
            project_id
        )

        document_uuid = self._uuid_key(
            uuid
        )

        return (
            self.data
            .get(project, {})
            .get(document_uuid, False)
            is True
        )

    # =========================================================
    # COMPATIBILIDADE COM contains()
    # =========================================================

    def contains(
        self,
        project_id,
        uuid: str,
    ) -> bool:

        return self.is_downloaded(
            project_id,
            uuid,
        )

    # =========================================================
    # REGISTRAR DOCUMENTO
    # =========================================================

    def set_status(
        self,
        project_id,
        uuid: str,
        downloaded: bool,
    ) -> None:

        project = self._project_key(
            project_id
        )

        document_uuid = self._uuid_key(
            uuid
        )

        if not document_uuid:
            return

        if project not in self.data:
            self.data[project] = {}

        self.data[project][document_uuid] = bool(
            downloaded
        )

        self.save()

    # =========================================================
    # MARCAR COMO BAIXADO
    # =========================================================

    def mark_downloaded(
        self,
        project_id,
        uuid: str,
    ) -> None:

        self.set_status(
            project_id,
            uuid,
            True,
        )

    # =========================================================
    # MARCAR COMO NÃO BAIXADO
    # =========================================================

    def mark_not_downloaded(
        self,
        project_id,
        uuid: str,
    ) -> None:

        self.set_status(
            project_id,
            uuid,
            False,
        )

    # =========================================================
    # ADICIONAR
    # =========================================================

    def add(
        self,
        project_id,
        uuid: str,
    ) -> None:

        self.mark_downloaded(
            project_id,
            uuid,
        )

    # =========================================================
    # PEGAR STATUS
    # =========================================================

    def get_status(
        self,
        project_id,
        uuid: str,
    ) -> bool:

        return self.is_downloaded(
            project_id,
            uuid,
        )

    # =========================================================
    # PEGAR DOCUMENTOS DO PROJETO
    # =========================================================

    def get_project(
        self,
        project_id,
    ) -> Dict[str, bool]:

        project = self._project_key(
            project_id
        )

        return dict(
            self.data.get(
                project,
                {}
            )
        )

    # =========================================================
    # CONTAR DOCUMENTOS
    # =========================================================

    def count(
        self,
        project_id,
    ) -> int:

        return len(
            self.get_project(
                project_id
            )
        )

    # =========================================================
    # CONTAR BAIXADOS
    # =========================================================

    def count_downloaded(
        self,
        project_id,
    ) -> int:

        documents = self.get_project(
            project_id
        )

        return sum(
            1
            for downloaded in documents.values()
            if downloaded is True
        )

    # =========================================================
    # REMOVER UUID
    # =========================================================

    def remove(
        self,
        project_id,
        uuid: str,
    ) -> bool:

        project = self._project_key(
            project_id
        )

        document_uuid = self._uuid_key(
            uuid
        )

        documents = self.data.get(
            project,
            {}
        )

        if document_uuid not in documents:
            return False

        del documents[document_uuid]

        self.save()

        return True

    # =========================================================
    # LIMPAR PROJETO
    # =========================================================

    def clear_project(
        self,
        project_id,
    ) -> None:

        project = self._project_key(
            project_id
        )

        if project in self.data:

            del self.data[project]

            self.save()

    # =========================================================
    # LIMPAR TUDO
    # =========================================================

    def clear(self) -> None:

        self.data = {}

        self.save()

    # =========================================================
    # MOSTRAR PROJETO
    # =========================================================

    def show_project(
        self,
        project_id,
    ) -> None:

        project = self._project_key(
            project_id
        )

        documents = self.get_project(
            project
        )

        print()
        print("=" * 70)
        print("CACHE DO PROJETO")
        print("=" * 70)

        print(
            f"Projeto: {project}"
        )

        print(
            f"Total: {len(documents)}"
        )

        print(
            f"Baixados: "
            f"{self.count_downloaded(project)}"
        )

        print()

        for index, (uuid, downloaded) in enumerate(
            documents.items(),
            start=1,
        ):

            status = (
                "BAIXADO"
                if downloaded
                else "PENDENTE"
            )

            print(
                f"{index:04d} - "
                f"{uuid} - "
                f"{status}"
            )

        print("=" * 70)