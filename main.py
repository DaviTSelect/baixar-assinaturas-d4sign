#!/usr/bin/env python3

from d4sign.config import Config
from d4sign.browser import D4SignBrowser
from d4sign.downloader import Downloader
from d4sign.cache import Cache
from d4sign.processor import Processor


def main():

    config = Config.load()

    browser = D4SignBrowser(config)

    cache = Cache(
        config.cache_file
    )

    cache.load()

    try:

        browser.start()

        print("Login...")
        browser.login()

        print("Abrindo cofre...")
        browser.open_vault()

        # =========================================================
        # REMOVIDO O LOOP DE TODAS AS PASTAS E FILTROS DE NOME
        # FOCO EXCLUSIVO NO LINK ESPECÍFICO
        # =========================================================

        downloader = Downloader(
            config,
            browser,
        )

        processor = Processor(
            config,
            browser,
            downloader,
            cache,
        )

        print("\nProcessando diretamente o link/cofre específico...")
        
        # Chama o método que aponta direto para o UUID do seu link
        stats = processor.process_specific_link()

        total = stats.downloaded

        print("\n==============================")
        print("ESTATÍSTICAS DO PROCESSAMENTO")
        print("==============================")
        print(f"  Documentos: {stats.documents}")
        print(f"  Baixados:   {stats.downloaded}")
        print(f"  Cache:      {stats.cached}")
        print(f"  Erros:      {stats.errors}")

        print("\n==============================")
        print("FINALIZADO")
        print("==============================")
        print(
            f"Total baixados: {total}"
        )

    finally:

        browser.close()


if __name__ == "__main__":
    main()