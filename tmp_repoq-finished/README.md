# repoq 3.0 — Finished (ZAG + VC Certificates)

Готовый к продакшену CLI для анализа Git‑репозиториев, генерации **JSON‑LD** онтологии качества,
выпуска **сертификатов качества** (VC‑style) на Project/Module/File и упаковки **ZAG v1** артефактов (PCQ/PCE/manifest).

## Установка
```bash
pip install -e ".[full]"      # анализ/валидация/графы
pip install -e ".[sign]"      # если нужна подпись сертификатов (Ed25519)
```

## Быстрый старт
```bash
repoq full .   -o quality.jsonld --md quality.md --graphs graphs/ --ttl quality.ttl --validate-shapes   --hash sha256   --certs certs/ --cert-valid-days 180 --cert-profile STANDARD   --zag-out zag/ --zag-level module --zag-U "[0,1]" --zag-aggregator min --zag-tau 0.82   --zag-budget 1.2 --zag-kmax 8
```

## ZAG‑валидация (опционально)
Если у вас есть официальный ZAG‑kit, можно аннотировать сертификаты уровнем доверия:
```bash
repoq full . --zag-out zag/ --certs certs/ --zag-validate-kit /path/to/ZAG_v1_kit
```
В сертификаты будет добавлено `assuranceLevel: ZAG:ACCEPT|ZAG:REJECT` на основе `tools/zag_validate.py`.

См. также `.github/workflows/repoq.yml` и `repoq.yaml` для конфигурации.
